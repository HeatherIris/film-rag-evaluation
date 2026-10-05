from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import generate_reply
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    conversation = conversation_service.get(payload.conversation_id)
    generated = generate_reply(
        history=conversation.messages,
        user_message=payload.message,
        mode=payload.mode,
    )
    stored = conversation_service.add_turn(
        conversation_id=payload.conversation_id,
        user_content=payload.message,
        assistant_content=generated.answer,
        mode=payload.mode,
    )
    generated.message_id = stored.message_id
    return generated
