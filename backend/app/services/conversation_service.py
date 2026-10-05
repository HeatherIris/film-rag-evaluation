from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from fastapi import HTTPException, status

from app.db import get_connection
from app.models.schemas import (
    ChatMode,
    ConversationCreated,
    ConversationDetail,
    ConversationSummary,
    Message,
)
from app.services.memory_service import extract_and_store_memories


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ConversationService:
    def __init__(self) -> None:
        self._lock = Lock()

    def create(self, title: str) -> ConversationCreated:
        conversation_id = _new_id("conv")
        created_at = _now()
        with self._lock:
            conn = get_connection()
            conn.execute(
                """
                INSERT INTO conversations (conversation_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, title, created_at, created_at),
            )
            conn.commit()
            conn.close()
        return ConversationCreated(
            conversation_id=conversation_id,
            title=title,
            created_at=created_at,
        )

    def list(self) -> list[ConversationSummary]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT conversation_id, title, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            """
        ).fetchall()
        conn.close()
        return [
            ConversationSummary(
                conversation_id=row["conversation_id"],
                title=row["title"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def get(self, conversation_id: str) -> ConversationDetail:
        conn = get_connection()
        conversation = conn.execute(
            "SELECT conversation_id, title FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if conversation is None:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation not found: {conversation_id}",
            )
        rows = conn.execute(
            """
            SELECT message_id, role, content, mode, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()
        conn.close()
        return ConversationDetail(
            conversation_id=conversation["conversation_id"],
            title=conversation["title"],
            messages=[
                Message(
                    message_id=row["message_id"],
                    role=row["role"],
                    content=row["content"],
                    created_at=row["created_at"],
                    mode=row["mode"],
                )
                for row in rows
            ],
        )

    def add_turn(
        self,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
        mode: ChatMode,
    ) -> Message:
        with self._lock:
            conn = get_connection()
            exists = conn.execute(
                "SELECT conversation_id FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if exists is None:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation not found: {conversation_id}",
                )

            now = _now()
            user_id = _new_id("msg")
            assistant_id = _new_id("msg")
            assistant_at = _now()
            conn.execute(
                """
                INSERT INTO messages (message_id, conversation_id, role, content, mode, created_at)
                VALUES (?, ?, 'user', ?, ?, ?)
                """,
                (user_id, conversation_id, user_content, mode, now),
            )
            conn.execute(
                """
                INSERT INTO messages (message_id, conversation_id, role, content, mode, created_at)
                VALUES (?, ?, 'assistant', ?, ?, ?)
                """,
                (assistant_id, conversation_id, assistant_content, mode, assistant_at),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                (assistant_at, conversation_id),
            )
            conn.commit()
            conn.close()

        extract_and_store_memories(conversation_id, user_content)

        return Message(
            message_id=assistant_id,
            role="assistant",
            content=assistant_content,
            created_at=assistant_at,
            mode=mode,
        )


conversation_service = ConversationService()
