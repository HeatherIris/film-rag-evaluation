from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ChatMode = Literal["llm", "rag", "rag_tmdb"]


class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1)


class ConversationCreated(BaseModel):
    conversation_id: str
    title: str
    created_at: datetime


class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    updated_at: datetime


class ConversationList(BaseModel):
    items: list[ConversationSummary]


class Message(BaseModel):
    message_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    mode: ChatMode | None = None


class ConversationDetail(BaseModel):
    conversation_id: str
    title: str
    messages: list[Message]


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(..., min_length=1)
    mode: ChatMode = "rag_tmdb"


class Source(BaseModel):
    filename: str
    chunk: str
    score: float


class ToolCallRecord(BaseModel):
    name: str
    arguments: dict


class ChatResponse(BaseModel):
    message_id: str
    answer: str
    mode: ChatMode
    latency_ms: int
    sources: list[Source]
    tools: list[ToolCallRecord]


MemoryType = Literal["preference", "topic", "fact", "summary"]


class Memory(BaseModel):
    memory_id: str
    conversation_id: str
    type: MemoryType
    content: str
    created_at: datetime


class MemoryList(BaseModel):
    items: list[Memory]


class EvaluationCompareRequest(BaseModel):
    question: str = Field(..., min_length=1)
    modes: list[ChatMode] = Field(..., min_length=1)


class EvaluationModeResult(BaseModel):
    mode: ChatMode
    answer: str | None = None
    latency_ms: int | None = None
    sources: list[Source] = []
    tools: list[ToolCallRecord] = []
    error: str | None = None


class EvaluationCompareResponse(BaseModel):
    question: str
    results: list[EvaluationModeResult]
