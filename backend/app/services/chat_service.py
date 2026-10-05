from __future__ import annotations

import json
import os
import time

from fastapi import HTTPException, status
from openai import OpenAI

from app.models.schemas import ChatMode, ChatResponse, Message, Source, ToolCallRecord
from app.services.rag_service import CRITIC_INSTRUCTIONS
from app.services.retrieval_service import format_context, retrieve
from app.services.tmdb_service import AVAILABLE_FUNCTIONS, TMDB_TOOL_SCHEMA

MODEL = "gpt-4o-mini"


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not set.",
        )
    return OpenAI(api_key=api_key)


def _system_prompt(mode: ChatMode, rag_context: str | None) -> str:
    if mode == "llm":
        return (
            f"{CRITIC_INSTRUCTIONS} Answer from general film knowledge only. "
            "Do not claim to have searched a local knowledge base or TMDB."
        )
    if mode == "rag":
        return (
            f"{CRITIC_INSTRUCTIONS} Use the local film knowledge-base excerpts below. "
            "If the documents do not cover the question, say so.\n\n"
            f"{rag_context}"
        )
    return (
        f"{CRITIC_INSTRUCTIONS} Always use the local knowledge-base excerpts first. "
        "If nothing is found or up-to-date information is required, call "
        "get_movie_details_tmdb.\n\n"
        f"{rag_context}"
    )


def _history_messages(history: list[Message]) -> list[dict]:
    return [{"role": item.role, "content": item.content} for item in history]


def generate_reply(
    history: list[Message],
    user_message: str,
    mode: ChatMode,
) -> ChatResponse:
    """
    Chat Completions stand-in for the notebook Assistants API.

    The OpenAI Assistants vector store / file_search / run-polling loop is not
    ported in this phase. RAG uses local embedding retrieval over markdown
    chunks; TMDB uses the notebook function-calling schema via Chat Completions tools.
    """
    sources: list[Source] = []
    tools_used: list[ToolCallRecord] = []
    rag_context = None

    if mode in ("rag", "rag_tmdb"):
        sources = retrieve(user_message)
        rag_context = format_context(sources)

    messages: list[dict] = [
        {"role": "system", "content": _system_prompt(mode, rag_context)},
        *_history_messages(history),
        {"role": "user", "content": user_message},
    ]

    client = _client()
    started = time.perf_counter()

    if mode == "rag_tmdb":
        answer, tools_used = _complete_with_tmdb(client, messages)
    else:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        answer = response.choices[0].message.content or ""

    latency_ms = int((time.perf_counter() - started) * 1000)
    return ChatResponse(
        message_id="",
        answer=answer,
        mode=mode,
        latency_ms=latency_ms,
        sources=sources if mode != "llm" else [],
        tools=tools_used,
    )


def _complete_with_tmdb(client: OpenAI, messages: list[dict]) -> tuple[str, list[ToolCallRecord]]:
    tools_used: list[ToolCallRecord] = []
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=[TMDB_TOOL_SCHEMA],
        tool_choice="auto",
    )
    choice = response.choices[0].message

    if not choice.tool_calls:
        return choice.content or "", tools_used

    messages.append(
        {
            "role": "assistant",
            "content": choice.content or "",
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments or "{}",
                    },
                }
                for tool_call in choice.tool_calls
            ],
        }
    )
    for tool_call in choice.tool_calls:
        name = tool_call.function.name
        raw_args = tool_call.function.arguments or "{}"
        try:
            arguments = json.loads(raw_args)
        except json.JSONDecodeError:
            arguments = {}
        tools_used.append(ToolCallRecord(name=name, arguments=arguments))

        fn = AVAILABLE_FUNCTIONS.get(name)
        if fn is None:
            output = json.dumps({"error": f"unknown function: {name}"})
        else:
            try:
                output = fn(**arguments)
            except TypeError as exc:
                output = json.dumps({"error": str(exc)})
            except RuntimeError as exc:
                output = json.dumps({"error": str(exc)})

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": output,
            }
        )

    follow_up = client.chat.completions.create(model=MODEL, messages=messages)
    return follow_up.choices[0].message.content or "", tools_used
