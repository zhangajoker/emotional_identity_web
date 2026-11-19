import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from auth import get_current_user
from chat_service import (
    CRISIS_RESPONSE,
    ChatServiceError,
    detect_crisis,
    stream_chat,
)
from db import get_connection


router = APIRouter(prefix="/api/chat", tags=["情感陪伴"])


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=80)


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("消息不能为空")
        return value


def _get_session(conn, session_id: int, user_id: int) -> dict:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, user_id, title
            FROM chat_sessions
            WHERE id = %s
              AND user_id = %s
              AND deleted_at IS NULL
            LIMIT 1
            """,
            (session_id, user_id),
        )
        session = cursor.fetchone()

    if session is None:
        raise HTTPException(status_code=404, detail="对话不存在")

    return session


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _save_assistant_message(
    session_id: int,
    content: str,
    safety_flag: bool,
) -> int:
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages (
                    session_id,
                    role,
                    content,
                    safety_flag
                )
                VALUES (%s, 'assistant', %s, %s)
                """,
                (
                    session_id,
                    content,
                    int(safety_flag),
                ),
            )
            message_id = cursor.lastrowid
            cursor.execute(
                """
                UPDATE chat_sessions
                SET updated_at = UTC_TIMESTAMP()
                WHERE id = %s
                """,
                (session_id,),
            )
        return int(message_id)
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.get("/sessions")
def list_sessions(user: dict = Depends(get_current_user)):
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    session.id,
                    session.title,
                    session.created_at,
                    session.updated_at,
                    (
                        SELECT message.content
                        FROM chat_messages AS message
                        WHERE message.session_id = session.id
                        ORDER BY message.id DESC
                        LIMIT 1
                    ) AS last_message
                FROM chat_sessions AS session
                WHERE session.user_id = %s
                  AND session.deleted_at IS NULL
                ORDER BY session.updated_at DESC
                LIMIT 50
                """,
                (user["id"],),
            )
            rows = cursor.fetchall()

        return {"status": "success", "data": rows}
    except Exception as exc:
        print(f"读取聊天会话失败: {exc}")
        raise HTTPException(status_code=500, detail="无法读取对话")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreate,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        title = (payload.title or "").strip() or "新的对话"
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_sessions (user_id, title)
                VALUES (%s, %s)
                """,
                (user["id"], title[:80]),
            )
            session_id = cursor.lastrowid

        return {
            "status": "success",
            "data": {
                "id": int(session_id),
                "title": title[:80],
                "last_message": None,
            },
        }
    except Exception as exc:
        print(f"创建聊天会话失败: {exc}")
        raise HTTPException(status_code=500, detail="无法创建对话")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: int,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        _get_session(conn, session_id, user["id"])

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    role,
                    content,
                    safety_flag,
                    created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY id ASC
                LIMIT 200
                """,
                (session_id,),
            )
            rows = cursor.fetchall()

        for row in rows:
            row["safety_flag"] = bool(row["safety_flag"])

        return {"status": "success", "data": rows}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"读取聊天消息失败: {exc}")
        raise HTTPException(status_code=500, detail="无法读取消息")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    user: dict = Depends(get_current_user),
):
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE chat_sessions
                SET deleted_at = UTC_TIMESTAMP()
                WHERE id = %s
                  AND user_id = %s
                  AND deleted_at IS NULL
                """,
                (session_id, user["id"]),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="对话不存在")

        return {"status": "success", "message": "对话已删除"}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"删除聊天会话失败: {exc}")
        raise HTTPException(status_code=500, detail="删除对话失败")
    finally:
        if conn is not None and conn.open:
            conn.close()


@router.post("/sessions/{session_id}/messages/stream")
def stream_message(
    session_id: int,
    payload: ChatMessageCreate,
    user: dict = Depends(get_current_user),
):
    conn = None
    safety_flag = detect_crisis(payload.content)

    try:
        conn = get_connection()
        session = _get_session(conn, session_id, user["id"])

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages (
                    session_id,
                    role,
                    content,
                    safety_flag
                )
                VALUES (%s, 'user', %s, %s)
                """,
                (
                    session_id,
                    payload.content,
                    int(safety_flag),
                ),
            )

            if session["title"] == "新的对话":
                title = payload.content.replace("\n", " ").strip()[:30]
                cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET title = %s,
                        updated_at = UTC_TIMESTAMP()
                    WHERE id = %s
                    """,
                    (title or "新的对话", session_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET updated_at = UTC_TIMESTAMP()
                    WHERE id = %s
                    """,
                    (session_id,),
                )

            cursor.execute(
                """
                SELECT role, content
                FROM (
                    SELECT role, content, id
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY id DESC
                    LIMIT 12
                ) AS recent_messages
                ORDER BY id ASC
                """,
                (session_id,),
            )
            history = cursor.fetchall()

        messages = [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in history
        ]
    except HTTPException:
        raise
    except Exception as exc:
        print(f"准备聊天消息失败: {exc}")
        raise HTTPException(status_code=500, detail="无法发送消息")
    finally:
        if conn is not None and conn.open:
            conn.close()

    async def event_stream() -> AsyncIterator[str]:
        full_content = ""

        try:
            if safety_flag:
                full_content = CRISIS_RESPONSE
                yield _sse("delta", {"content": full_content})
            else:
                async for chunk in stream_chat(messages):
                    full_content += chunk
                    yield _sse("delta", {"content": chunk})

            message_id = await run_in_threadpool(
                _save_assistant_message,
                session_id,
                full_content,
                safety_flag,
            )
            yield _sse(
                "done",
                {
                    "message_id": message_id,
                    "safety_flag": safety_flag,
                },
            )
        except asyncio.CancelledError:
            raise
        except ChatServiceError as exc:
            print(f"情感模型调用失败: {exc}")
            yield _sse(
                "error",
                {"message": "情感模型暂时无法回应，请稍后重试"},
            )
        except Exception as exc:
            print(f"情感对话失败: {exc}")
            yield _sse(
                "error",
                {"message": "对话暂时中断，请稍后重试"},
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
