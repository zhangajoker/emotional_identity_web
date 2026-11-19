from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from auth import get_current_user
from db import get_connection


router = APIRouter(prefix="/api/social", tags=["情绪空间"])


class PostCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    mood: str | None = Field(default=None, max_length=20)
    visibility: Literal["private", "public"] = "private"

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("动态内容不能为空")
        return value

    @field_validator("mood")
    @classmethod
    def normalize_mood(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        return value or None


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("评论内容不能为空")
        return value


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=64)
    bio: str = Field(default="", max_length=500)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("显示名称不能为空")
        return value

    @field_validator("bio")
    @classmethod
    def normalize_bio(cls, value: str) -> str:
        return value.strip()


def _ensure_post_access(
    conn,
    post_id: int,
    viewer_id: int,
) -> dict:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, user_id, visibility
            FROM posts
            WHERE id = %s
              AND deleted_at IS NULL
            LIMIT 1
            """,
            (post_id,),
        )
        post = cursor.fetchone()

    if post is None:
        raise HTTPException(status_code=404, detail="动态不存在")

    if post["visibility"] == "private" and post["user_id"] != viewer_id:
        raise HTTPException(status_code=404, detail="动态不存在")

    return post


def _post_rows(
    conn,
    viewer_id: int,
    where_sql: str,
    where_params: list,
    limit: int,
) -> list[dict]:
    sql = f"""
        SELECT
            p.id,
            p.user_id,
            p.content,
            p.mood,
            p.visibility,
            p.created_at,
            p.updated_at,
            u.username,
            u.display_name,
            COALESCE(profile.avatar_url, '') AS avatar_url,
            (
                SELECT COUNT(*)
                FROM post_reactions AS reaction_count
                WHERE reaction_count.post_id = p.id
            ) AS reaction_count,
            (
                SELECT COUNT(*)
                FROM post_comments AS comment_count
                WHERE comment_count.post_id = p.id
                  AND comment_count.deleted_at IS NULL
            ) AS comment_count,
            EXISTS(
                SELECT 1
                FROM post_reactions AS my_reaction
                WHERE my_reaction.post_id = p.id
                  AND my_reaction.user_id = %s
            ) AS liked_by_me
        FROM posts AS p
        JOIN users AS u ON u.id = p.user_id
        LEFT JOIN user_profiles AS profile
            ON profile.user_id = p.user_id
        WHERE {where_sql}
        ORDER BY p.id DESC
        LIMIT %s
    """

    with conn.cursor() as cursor:
        cursor.execute(
            sql,
            [viewer_id, *where_params, limit],
        )
        rows = cursor.fetchall()

    for row in rows:
        row["liked_by_me"] = bool(row["liked_by_me"])
        row["reaction_count"] = int(row["reaction_count"])
        row["comment_count"] = int(row["comment_count"])

    return rows


@router.get("/feed")
def get_feed(
    limit: int = Query(default=20, ge=1, le=50),
    before_id: int | None = Query(default=None, ge=1),
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        conditions = [
            "p.deleted_at IS NULL",
            "(p.visibility = 'public' OR p.user_id = %s)",
        ]
        params = [user["id"]]

        if before_id is not None:
            conditions.append("p.id < %s")
            params.append(before_id)

        rows = _post_rows(
            conn,
            user["id"],
            " AND ".join(conditions),
            params,
            limit,
        )

        return {
            "status": "success",
            "data": rows,
            "next_cursor": rows[-1]["id"] if rows else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"读取动态列表失败: {exc}")
        raise HTTPException(status_code=500, detail="无法读取动态")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.get("/users/{target_user_id}/posts")
def get_user_posts(
    target_user_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    before_id: int | None = Query(default=None, ge=1),
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        conditions = [
            "p.deleted_at IS NULL",
            "p.user_id = %s",
            "(p.visibility = 'public' OR p.user_id = %s)",
        ]
        params = [target_user_id, user["id"]]

        if before_id is not None:
            conditions.append("p.id < %s")
            params.append(before_id)

        rows = _post_rows(
            conn,
            user["id"],
            " AND ".join(conditions),
            params,
            limit,
        )

        return {
            "status": "success",
            "data": rows,
            "next_cursor": rows[-1]["id"] if rows else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"读取用户动态失败: {exc}")
        raise HTTPException(status_code=500, detail="无法读取用户动态")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.post("/posts", status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO posts (
                    user_id,
                    content,
                    mood,
                    visibility
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user["id"],
                    payload.content,
                    payload.mood,
                    payload.visibility,
                ),
            )
            post_id = cursor.lastrowid

        rows = _post_rows(
            conn,
            user["id"],
            "p.id = %s AND p.deleted_at IS NULL",
            [post_id],
            1,
        )

        return {
            "status": "success",
            "data": rows[0],
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"发布动态失败: {exc}")
        raise HTTPException(status_code=500, detail="发布动态失败")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.get("/posts/{post_id}")
def get_post(
    post_id: int,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        rows = _post_rows(
            conn,
            user["id"],
            """
            p.id = %s
            AND p.deleted_at IS NULL
            AND (p.visibility = 'public' OR p.user_id = %s)
            """,
            [post_id, user["id"]],
            1,
        )

        if not rows:
            raise HTTPException(status_code=404, detail="动态不存在")

        return {
            "status": "success",
            "data": rows[0],
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"读取动态失败: {exc}")
        raise HTTPException(status_code=500, detail="无法读取动态")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE posts
                SET deleted_at = UTC_TIMESTAMP()
                WHERE id = %s
                  AND user_id = %s
                  AND deleted_at IS NULL
                """,
                (post_id, user["id"]),
            )
            affected_rows = cursor.rowcount

        if affected_rows == 0:
            raise HTTPException(status_code=404, detail="动态不存在")

        return {"status": "success", "message": "动态已删除"}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"删除动态失败: {exc}")
        raise HTTPException(status_code=500, detail="删除动态失败")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.get("/posts/{post_id}/comments")
def get_comments(
    post_id: int,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        _ensure_post_access(conn, post_id, user["id"])

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.post_id,
                    c.user_id,
                    c.content,
                    c.created_at,
                    u.username,
                    u.display_name,
                    COALESCE(profile.avatar_url, '') AS avatar_url
                FROM post_comments AS c
                JOIN users AS u ON u.id = c.user_id
                LEFT JOIN user_profiles AS profile
                    ON profile.user_id = c.user_id
                WHERE c.post_id = %s
                  AND c.deleted_at IS NULL
                ORDER BY c.id ASC
                LIMIT 100
                """,
                (post_id,),
            )
            rows = cursor.fetchall()

        return {
            "status": "success",
            "data": rows,
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"读取评论失败: {exc}")
        raise HTTPException(status_code=500, detail="无法读取评论")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.post(
    "/posts/{post_id}/comments",
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: int,
    payload: CommentCreate,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        _ensure_post_access(conn, post_id, user["id"])

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO post_comments (
                    post_id,
                    user_id,
                    content
                )
                VALUES (%s, %s, %s)
                """,
                (post_id, user["id"], payload.content),
            )
            comment_id = cursor.lastrowid

            cursor.execute(
                """
                SELECT
                    c.id,
                    c.post_id,
                    c.user_id,
                    c.content,
                    c.created_at,
                    u.username,
                    u.display_name,
                    COALESCE(profile.avatar_url, '') AS avatar_url
                FROM post_comments AS c
                JOIN users AS u ON u.id = c.user_id
                LEFT JOIN user_profiles AS profile
                    ON profile.user_id = c.user_id
                WHERE c.id = %s
                """,
                (comment_id,),
            )
            comment = cursor.fetchone()

        return {
            "status": "success",
            "data": comment,
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"发布评论失败: {exc}")
        raise HTTPException(status_code=500, detail="发布评论失败")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.post("/posts/{post_id}/like")
def like_post(
    post_id: int,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        _ensure_post_access(conn, post_id, user["id"])

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT IGNORE INTO post_reactions (
                    post_id,
                    user_id,
                    reaction_type
                )
                VALUES (%s, %s, 'like')
                """,
                (post_id, user["id"]),
            )
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM post_reactions
                WHERE post_id = %s
                """,
                (post_id,),
            )
            reaction_count = cursor.fetchone()["COUNT(*)"]

        return {
            "status": "success",
            "liked_by_me": True,
            "reaction_count": int(reaction_count),
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"点赞失败: {exc}")
        raise HTTPException(status_code=500, detail="点赞失败")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.delete("/posts/{post_id}/like")
def unlike_post(
    post_id: int,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        _ensure_post_access(conn, post_id, user["id"])

        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM post_reactions
                WHERE post_id = %s
                  AND user_id = %s
                """,
                (post_id, user["id"]),
            )
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM post_reactions
                WHERE post_id = %s
                """,
                (post_id,),
            )
            reaction_count = cursor.fetchone()["COUNT(*)"]

        return {
            "status": "success",
            "liked_by_me": False,
            "reaction_count": int(reaction_count),
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"取消点赞失败: {exc}")
        raise HTTPException(status_code=500, detail="取消点赞失败")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.get("/profiles/me")
def get_my_profile(user: dict = Depends(get_current_user)):
    return get_profile(user["id"], user)


@router.patch("/profiles/me")
def update_my_profile(
    payload: ProfileUpdate,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET display_name = %s
                WHERE id = %s
                """,
                (payload.display_name, user["id"]),
            )
            cursor.execute(
                """
                INSERT INTO user_profiles (user_id, bio)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE bio = VALUES(bio)
                """,
                (user["id"], payload.bio),
            )

        return get_profile(
            user["id"],
            {
                **user,
                "display_name": payload.display_name,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"更新个人资料失败: {exc}")
        raise HTTPException(status_code=500, detail="更新个人资料失败")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.get("/profiles/{target_user_id}")
def get_profile(
    target_user_id: int,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.id,
                    u.username,
                    u.display_name,
                    COALESCE(profile.bio, '') AS bio,
                    COALESCE(profile.avatar_url, '') AS avatar_url,
                    (
                        SELECT COUNT(*)
                        FROM posts
                        WHERE posts.user_id = u.id
                          AND posts.deleted_at IS NULL
                          AND (
                              posts.visibility = 'public'
                              OR posts.user_id = %s
                          )
                    ) AS post_count
                FROM users AS u
                LEFT JOIN user_profiles AS profile
                    ON profile.user_id = u.id
                WHERE u.id = %s
                  AND u.is_active = 1
                LIMIT 1
                """,
                (user["id"], target_user_id),
            )
            profile = cursor.fetchone()

        if profile is None:
            raise HTTPException(status_code=404, detail="用户不存在")

        profile["post_count"] = int(profile["post_count"])
        return {"status": "success", "data": profile}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"读取个人资料失败: {exc}")
        raise HTTPException(status_code=500, detail="无法读取个人资料")
    finally:
        if conn is not None and conn.open:
            conn.close()
