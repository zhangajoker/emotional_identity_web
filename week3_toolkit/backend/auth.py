import hashlib
import os
import re
import secrets
import time
from collections import deque
from threading import Lock
from urllib.parse import quote

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from pymysql.err import IntegrityError

from db import get_connection
from email_service import EmailConfigurationError, send_email


router = APIRouter(prefix="/api/auth", tags=["认证"])

SESSION_COOKIE = "emotion_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
# 密码限流
LOGIN_WINDOW_SECONDS = 10 * 60
LOGIN_MAX_FAILURES = 5

_failed_logins: dict[str, deque[float]] = {}
_failed_logins_lock = Lock()
#
password_hasher = PasswordHasher()
DUMMY_PASSWORD_HASH = password_hasher.hash(secrets.token_urlsafe(32))


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    display_name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[\w\u4e00-\u9fff]+", value):
            raise ValueError("用户名只能包含文字、字母、数字和下划线")
        return value

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("显示名称不能为空")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class EmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("邮箱格式不正确")
        return value


class TokenRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)


class PublicUser(BaseModel):
    id: int
    username: str
    display_name: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _public_user(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "display_name": row["display_name"],
    }


def _issue_session(conn, user_id: int, response: Response) -> None:
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO auth_sessions (user_id, token_hash, expires_at)
            VALUES (%s, %s, DATE_ADD(UTC_TIMESTAMP(), INTERVAL 7 DAY))
            """,
            (user_id, token_hash),
        )

    response.set_cookie(
        key=SESSION_COOKIE,
        value=raw_token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

# 限流函数
def _normalize_login_username(username: str) -> str:
    return username.strip().lower()


def _check_login_limit(username: str) -> None:
    now = time.monotonic()
    key = _normalize_login_username(username)

    with _failed_logins_lock:
        attempts = _failed_logins.get(key)

        if attempts is None:
            return

        while (
            attempts
            and now - attempts[0] >= LOGIN_WINDOW_SECONDS
        ):
            attempts.popleft()

        if not attempts:
            _failed_logins.pop(key, None)
            return

        if len(attempts) >= LOGIN_MAX_FAILURES:
            retry_after = max(
                1,
                int(LOGIN_WINDOW_SECONDS - (now - attempts[0])),
            )
            raise HTTPException(
                status_code=429,
                detail="登录尝试次数过多，请稍后再试",
                headers={"Retry-After": str(retry_after)},
            )


def _record_login_failure(username: str) -> None:
    key = _normalize_login_username(username)

    with _failed_logins_lock:
        attempts = _failed_logins.setdefault(key, deque())
        attempts.append(time.monotonic())


def _clear_login_failures(username: str) -> None:
    key = _normalize_login_username(username)

    with _failed_logins_lock:
        _failed_logins.pop(key, None)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, display_name, password_hash)
                VALUES (%s, %s, %s)
                """,
                (
                    payload.username,
                    payload.display_name,
                    password_hasher.hash(payload.password),
                ),
            )
            user_id = cursor.lastrowid

        _issue_session(conn, user_id, response)
        return {
            "status": "success",
            "user": {
                "id": user_id,
                "username": payload.username,
                "display_name": payload.display_name,
            },
        }
    except IntegrityError:
        raise HTTPException(status_code=409, detail="这个用户名已经被使用")
    except HTTPException:
        raise
    except Exception as exc:
        print(f"注册失败: {exc}")
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    conn = None
    try:
        username = _normalize_login_username(payload.username)
        _check_login_limit(username)

        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, password_hash, is_active
                FROM users
                WHERE username = %s
                LIMIT 1
                """,
                (username,),
            )
            user = cursor.fetchone()

        if user is None:
            try:
                password_hasher.verify(
                    DUMMY_PASSWORD_HASH,
                    payload.password,
                )
            except VerificationError:
                pass
            _record_login_failure(username)
            raise HTTPException(
                status_code=401,
                detail="用户名或密码错误",
            )

        try:
            password_hasher.verify(user["password_hash"], payload.password)
        except VerificationError:
            _record_login_failure(username)
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not user["is_active"]:
            _record_login_failure(username)
            raise HTTPException(status_code=403, detail="账号已停用")

        if password_hasher.check_needs_rehash(user["password_hash"]):
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (password_hasher.hash(payload.password), user["id"]),
                )
        _clear_login_failures(username)
        _issue_session(conn, user["id"], response)
        return {
            "status": "success",
            "user": _public_user(user),
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"登录失败: {exc}")
        raise HTTPException(status_code=500, detail="登录失败，请稍后重试")
    finally:
        if conn is not None and conn.open:
            conn.close()


def get_current_user(request: Request) -> dict:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=401, detail="请先登录")

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.username, u.display_name
                FROM auth_sessions AS s
                JOIN users AS u ON u.id = s.user_id
                WHERE s.token_hash = %s
                  AND s.revoked_at IS NULL
                  AND s.expires_at > UTC_TIMESTAMP()
                  AND u.is_active = 1
                LIMIT 1
                """,
                (_hash_token(raw_token),),
            )
            user = cursor.fetchone()

        if user is None:
            raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth_sessions
                SET last_seen_at = UTC_TIMESTAMP()
                WHERE token_hash = %s
                """,
                (_hash_token(raw_token),),
            )

        return _public_user(user)
    except HTTPException:
        raise
    except Exception as exc:
        print(f"读取登录用户失败: {exc}")
        raise HTTPException(status_code=500, detail="无法读取登录状态")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "user": user,
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    raw_token = request.cookies.get(SESSION_COOKIE)
    conn = None

    try:
        if raw_token:
            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE auth_sessions
                    SET revoked_at = UTC_TIMESTAMP()
                    WHERE token_hash = %s
                      AND revoked_at IS NULL
                    """,
                    (_hash_token(raw_token),),
                )
    except Exception as exc:
        print(f"退出登录失败: {exc}")
    finally:
        if conn is not None and conn.open:
            conn.close()

    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    return {"status": "success", "message": "已退出登录"}


def _app_base_url() -> str:
    return os.environ.get(
        "APP_BASE_URL",
        "http://127.0.0.1:5173",
    ).rstrip("/")


@router.post("/email/request")
def request_email_binding(
    payload: EmailRequest,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id
                FROM user_emails
                WHERE email = %s
                  AND user_id <> %s
                LIMIT 1
                """,
                (payload.email, user["id"]),
            )
            if cursor.fetchone() is not None:
                raise HTTPException(
                    status_code=409,
                    detail="这个邮箱已经绑定其他账号",
                )

            cursor.execute(
                """
                SELECT email, verified_at
                FROM user_emails
                WHERE user_id = %s
                LIMIT 1
                """,
                (user["id"],),
            )
            current_email = cursor.fetchone()

            if (
                current_email
                and current_email["email"] == payload.email
                and current_email["verified_at"] is not None
            ):
                return {
                    "status": "success",
                    "message": "这个邮箱已经完成验证",
                }

            cursor.execute(
                """
                SELECT id
                FROM email_verification_tokens
                WHERE user_id = %s
                  AND created_at >
                      DATE_SUB(UTC_TIMESTAMP(), INTERVAL 60 SECOND)
                LIMIT 1
                """,
                (user["id"],),
            )
            if cursor.fetchone() is not None:
                raise HTTPException(
                    status_code=429,
                    detail="请等待 60 秒后再重新发送",
                )

            cursor.execute(
                """
                UPDATE email_verification_tokens
                SET used_at = UTC_TIMESTAMP()
                WHERE user_id = %s
                  AND used_at IS NULL
                """,
                (user["id"],),
            )

            raw_token = secrets.token_urlsafe(32)
            cursor.execute(
                """
                INSERT INTO email_verification_tokens (
                    user_id,
                    email,
                    token_hash,
                    expires_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    DATE_ADD(UTC_TIMESTAMP(), INTERVAL 24 HOUR)
                )
                """,
                (
                    user["id"],
                    payload.email,
                    _hash_token(raw_token),
                ),
            )
            token_id = cursor.lastrowid

        verify_url = (
            f"{_app_base_url()}/verify-email"
            f"?token={quote(raw_token, safe='')}"
        )
        content = (
            f"{user['display_name']}，你好：\n\n"
            "你正在为情绪感知空间绑定这个邮箱。\n"
            "请点击下面的链接完成验证，链接 24 小时内有效：\n\n"
            f"{verify_url}\n\n"
            "如果这不是你的操作，请忽略这封邮件。\n"
        )

        try:
            send_email(
                payload.email,
                "验证你的情绪感知空间邮箱",
                content,
            )
        except EmailConfigurationError as exc:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE email_verification_tokens
                    SET used_at = UTC_TIMESTAMP()
                    WHERE id = %s
                    """,
                    (token_id,),
                )
            raise HTTPException(
                status_code=503,
                detail="邮件服务尚未配置，请联系管理员",
            ) from exc
        except Exception as exc:
            print(f"发送邮箱验证邮件失败: {exc}")
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE email_verification_tokens
                    SET used_at = UTC_TIMESTAMP()
                    WHERE id = %s
                    """,
                    (token_id,),
                )
            raise HTTPException(
                status_code=502,
                detail="验证邮件发送失败，请稍后重试",
            ) from exc

        return {
            "status": "success",
            "message": "验证邮件已发送",
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"请求邮箱验证失败: {exc}")
        raise HTTPException(
            status_code=500,
            detail="无法发送验证邮件",
        )
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.get("/email/me")
def get_my_email(user: dict = Depends(get_current_user)):
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT email, verified_at
                FROM user_emails
                WHERE user_id = %s
                LIMIT 1
                """,
                (user["id"],),
            )
            email = cursor.fetchone()

        if email is None:
            return {
                "status": "success",
                "data": {
                    "email": None,
                    "verified": False,
                },
            }

        return {
            "status": "success",
            "data": {
                "email": email["email"],
                "verified": email["verified_at"] is not None,
            },
        }
    except Exception as exc:
        print(f"读取绑定邮箱失败: {exc}")
        raise HTTPException(
            status_code=500,
            detail="无法读取邮箱信息",
        )
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.post("/email/verify")
def verify_email(payload: TokenRequest):
    conn = None

    try:
        conn = get_connection()
        token_hash = _hash_token(payload.token)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    token.id,
                    token.user_id,
                    token.email,
                    u.username
                FROM email_verification_tokens AS token
                JOIN users AS u ON u.id = token.user_id
                WHERE token.token_hash = %s
                  AND token.used_at IS NULL
                  AND token.expires_at > UTC_TIMESTAMP()
                  AND u.is_active = 1
                LIMIT 1
                """,
                (token_hash,),
            )
            token = cursor.fetchone()

            if token is None:
                raise HTTPException(
                    status_code=400,
                    detail="验证链接无效或已过期",
                )

            cursor.execute(
                """
                SELECT user_id
                FROM user_emails
                WHERE email = %s
                  AND user_id <> %s
                LIMIT 1
                """,
                (token["email"], token["user_id"]),
            )
            if cursor.fetchone() is not None:
                raise HTTPException(
                    status_code=409,
                    detail="这个邮箱已经绑定其他账号",
                )

            cursor.execute(
                """
                INSERT INTO user_emails (
                    user_id,
                    email,
                    verified_at
                )
                VALUES (%s, %s, UTC_TIMESTAMP())
                ON DUPLICATE KEY UPDATE
                    email = VALUES(email),
                    verified_at = VALUES(verified_at)
                """,
                (token["user_id"], token["email"]),
            )
            cursor.execute(
                """
                UPDATE email_verification_tokens
                SET used_at = UTC_TIMESTAMP()
                WHERE user_id = %s
                  AND used_at IS NULL
                """,
                (token["user_id"],),
            )

        return {
            "status": "success",
            "message": "邮箱验证成功",
            "email": token["email"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"邮箱验证失败: {exc}")
        raise HTTPException(
            status_code=500,
            detail="邮箱验证失败",
        )
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.post("/password/forgot")
def request_password_reset(payload: EmailRequest):
    generic_response = {
        "status": "success",
        "message": (
            "如果该邮箱已绑定账号，重置邮件会很快发送。"
        ),
    }
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    email.user_id,
                    u.username
                FROM user_emails AS email
                JOIN users AS u ON u.id = email.user_id
                WHERE email.email = %s
                  AND email.verified_at IS NOT NULL
                  AND u.is_active = 1
                LIMIT 1
                """,
                (payload.email,),
            )
            user = cursor.fetchone()

            if user is None:
                return generic_response

            cursor.execute(
                """
                SELECT id
                FROM password_reset_tokens
                WHERE user_id = %s
                  AND created_at >
                      DATE_SUB(UTC_TIMESTAMP(), INTERVAL 60 SECOND)
                LIMIT 1
                """,
                (user["user_id"],),
            )
            if cursor.fetchone() is not None:
                return generic_response

            raw_token = secrets.token_urlsafe(32)
            cursor.execute(
                """
                INSERT INTO password_reset_tokens (
                    user_id,
                    token_hash,
                    expires_at
                )
                VALUES (
                    %s,
                    %s,
                    DATE_ADD(UTC_TIMESTAMP(), INTERVAL 30 MINUTE)
                )
                """,
                (
                    user["user_id"],
                    _hash_token(raw_token),
                ),
            )

        reset_url = (
            f"{_app_base_url()}/reset-password"
            f"?token={quote(raw_token, safe='')}"
        )
        content = (
            f"{user['username']}，你好：\n\n"
            "你正在申请重置情绪感知空间的登录密码。\n"
            "请点击下面的链接设置新密码，链接 30 分钟内有效：\n\n"
            f"{reset_url}\n\n"
            "如果这不是你的操作，请忽略这封邮件，"
            "你的密码不会发生变化。\n"
        )

        send_email(
            payload.email,
            "重置你的情绪感知空间密码",
            content,
        )
        return generic_response
    except EmailConfigurationError:
        print("密码重置邮件未发送：SMTP 配置缺失")
        return generic_response
    except Exception as exc:
        print(f"发送密码重置邮件失败: {exc}")
        return generic_response
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.post("/password/reset")
def reset_password(payload: PasswordResetRequest):
    conn = None

    try:
        conn = get_connection()
        token_hash = _hash_token(payload.token)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    token.id,
                    token.user_id,
                    u.username
                FROM password_reset_tokens AS token
                JOIN users AS u ON u.id = token.user_id
                WHERE token.token_hash = %s
                  AND token.used_at IS NULL
                  AND token.expires_at > UTC_TIMESTAMP()
                  AND u.is_active = 1
                LIMIT 1
                """,
                (token_hash,),
            )
            token = cursor.fetchone()

            if token is None:
                raise HTTPException(
                    status_code=400,
                    detail="重置链接无效或已过期",
                )

            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s
                """,
                (
                    password_hasher.hash(payload.new_password),
                    token["user_id"],
                ),
            )
            cursor.execute(
                """
                UPDATE password_reset_tokens
                SET used_at = UTC_TIMESTAMP()
                WHERE user_id = %s
                  AND used_at IS NULL
                """,
                (token["user_id"],),
            )
            cursor.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = UTC_TIMESTAMP()
                WHERE user_id = %s
                  AND revoked_at IS NULL
                """,
                (token["user_id"],),
            )

        _clear_login_failures(token["username"])
        return {
            "status": "success",
            "message": "密码已重置，请使用新密码登录",
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"重置密码失败: {exc}")
        raise HTTPException(
            status_code=500,
            detail="密码重置失败",
        )
    finally:
        if conn is not None and conn.open:
            conn.close()
