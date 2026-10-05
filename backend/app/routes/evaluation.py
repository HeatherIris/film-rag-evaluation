from fastapi import APIRouter

from app.models.schemas import EvaluationCompareRequest, EvaluationCompareResponse
from app.services.evaluation_service import compare_modes

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/compare", response_model=EvaluationCompareResponse)
def compare(payload: EvaluationCompareRequest) -> EvaluationCompareResponse:
    return compare_modes(payload.question, payload.modes)
