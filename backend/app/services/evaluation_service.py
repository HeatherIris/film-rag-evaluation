from fastapi import HTTPException
from openai import APIError, APIStatusError

from app.models.schemas import (
    ChatMode,
    EvaluationCompareResponse,
    EvaluationModeResult,
)
from app.services.chat_service import generate_reply

QUOTA_MESSAGE = "AI service is temporarily unavailable due to API quota."


def _error_text(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = exc.detail
        text = detail if isinstance(detail, str) else str(detail)
        status_code = exc.status_code
    elif isinstance(exc, APIStatusError):
        text = str(exc)
        status_code = exc.status_code or 0
    elif isinstance(exc, APIError):
        text = str(exc)
        status_code = 0
    else:
        text = str(exc)
        status_code = 0

    lowered = text.lower()
    if (
        status_code == 429
        or "quota" in lowered
        or "insufficient_quota" in lowered
        or "credit" in lowered
        or "rate limit" in lowered
    ):
        return QUOTA_MESSAGE
    return text


def compare_modes(question: str, modes: list[ChatMode]) -> EvaluationCompareResponse:
    results: list[EvaluationModeResult] = []
    seen: set[ChatMode] = set()
    for mode in modes:
        if mode in seen:
            continue
        seen.add(mode)
        try:
            reply = generate_reply(history=[], user_message=question, mode=mode)
            results.append(
                EvaluationModeResult(
                    mode=mode,
                    answer=reply.answer,
                    latency_ms=reply.latency_ms,
                    sources=reply.sources,
                    tools=reply.tools,
                )
            )
        except Exception as exc:
            results.append(EvaluationModeResult(mode=mode, error=_error_text(exc)))
    return EvaluationCompareResponse(question=question, results=results)
