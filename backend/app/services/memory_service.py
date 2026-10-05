from __future__ import annotations

import re
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from fastapi import HTTPException, status

from app.db import get_connection
from app.models.schemas import Memory, MemoryType

_lock = Lock()

PREFERENCE_RE = re.compile(
    r"(?i)\b(i (?:really )?(?:like|love|prefer|enjoy|dislike|hate|don'?t like)\b[^.!?\n]{2,160})"
)
TOPIC_RE = re.compile(
    r"(?i)\b((?:we|i) (?:previously )?(?:discussed|talked about|were discussing)\b[^.!?\n]{2,160})"
)
FACT_RE = re.compile(
    r"(?i)\b(i (?:always|usually|often|never) (?:watch|prefer|revisit|avoid)\b[^.!?\n]{2,160})"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"mem_{uuid4().hex[:12]}"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .")


def extract_candidates(user_message: str) -> list[tuple[MemoryType, str]]:
    """Conservative extractors. Ordinary questions are ignored."""
    found: list[tuple[MemoryType, str]] = []
    for pattern, memory_type in (
        (PREFERENCE_RE, "preference"),
        (TOPIC_RE, "topic"),
        (FACT_RE, "fact"),
    ):
        for match in pattern.finditer(user_message):
            content = _clean(match.group(1))
            if len(content) >= 8:
                found.append((memory_type, content))
    return found


def extract_and_store_memories(conversation_id: str, user_message: str) -> list[Memory]:
    stored: list[Memory] = []
    for memory_type, content in extract_candidates(user_message):
        item = _insert_if_new(conversation_id, memory_type, content)
        if item:
            stored.append(item)
    return stored


def _insert_if_new(conversation_id: str, memory_type: MemoryType, content: str) -> Memory | None:
    with _lock:
        conn = get_connection()
        duplicate = conn.execute(
            """
            SELECT memory_id FROM memories
            WHERE conversation_id = ? AND type = ? AND lower(content) = lower(?)
            """,
            (conversation_id, memory_type, content),
        ).fetchone()
        if duplicate:
            conn.close()
            return None
        memory_id = _new_id()
        created_at = _now()
        conn.execute(
            """
            INSERT INTO memories (memory_id, conversation_id, type, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (memory_id, conversation_id, memory_type, content, created_at),
        )
        conn.commit()
        conn.close()
    return Memory(
        memory_id=memory_id,
        conversation_id=conversation_id,
        type=memory_type,
        content=content,
        created_at=created_at,
    )


def list_for_conversation(conversation_id: str) -> list[Memory]:
    conn = get_connection()
    conversation = conn.execute(
        "SELECT conversation_id FROM conversations WHERE conversation_id = ?",
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
        SELECT memory_id, conversation_id, type, content, created_at
        FROM memories
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        """,
        (conversation_id,),
    ).fetchall()
    conn.close()
    return [
        Memory(
            memory_id=row["memory_id"],
            conversation_id=row["conversation_id"],
            type=row["type"],
            content=row["content"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def delete_memory(memory_id: str) -> None:
    with _lock:
        conn = get_connection()
        cursor = conn.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
    if deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory not found: {memory_id}",
        )
