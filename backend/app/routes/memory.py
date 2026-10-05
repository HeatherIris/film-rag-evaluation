from fastapi import APIRouter, Response, status

from app.models.schemas import MemoryList
from app.services import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{conversation_id}", response_model=MemoryList)
def list_memory(conversation_id: str) -> MemoryList:
    return MemoryList(items=memory_service.list_for_conversation(conversation_id))


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: str) -> Response:
    memory_service.delete_memory(memory_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
