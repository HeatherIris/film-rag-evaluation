from fastapi import APIRouter

from app.models.schemas import (
    ConversationCreate,
    ConversationCreated,
    ConversationDetail,
    ConversationList,
)
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ConversationList)
def list_conversations() -> ConversationList:
    return ConversationList(items=conversation_service.list())


@router.post("", response_model=ConversationCreated)
def create_conversation(payload: ConversationCreate) -> ConversationCreated:
    return conversation_service.create(payload.title)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str) -> ConversationDetail:
    return conversation_service.get(conversation_id)
