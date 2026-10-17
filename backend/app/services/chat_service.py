from __future__ import annotations

import json
import os
import time

from fastapi import HTTPException, status
from openai import OpenAI

from app.models.schemas import ChatMode, ChatResponse, Message, Source, ToolCallRecord
from app.services.graph_service import format_graph_context, retrieve_graph
from app.services.rag_service import CRITIC_INSTRUCTIONS
from app.services.retrieval_service import format_context, retrieve
from app.services.scene_retrieval import (
    all_scene_context,
    format_scene_context,
    retrieve_scenes_graph,
    retrieve_scenes_vector,
)
from app.services.tmdb_service import AVAILABLE_FUNCTIONS, TMDB_TOOL_SCHEMA

MODEL = "gpt-4o-mini"

SCENE_MODES = ("scene_vector", "scene_graph", "scene_full")

# Shared by every scene mode so that the conditions differ only in what context they get.
SCENE_ANSWER_FORMAT = (
    "Answer in three labelled parts:\n"
    "Observed in the film: facts taken from the scene notes, each followed by the scene or event id "
    "it comes from, e.g. (s03.e1). Use document excerpts or graph facts only for credits and background.\n"
    "Interpretation: readings of meaning or intent. Say whose reading it is (an interpretation record "
    "in the notes, or your own) and which observed facts it rests on. Write 'none' if not asked.\n"
    "Not covered: anything the question asks that the notes do not show. Do not fill gaps from "
    "general knowledge of the film; if the notes do not cover the question, say so here."
)


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not set.",
        )
    return OpenAI(api_key=api_key)


def _system_prompt(
    mode: ChatMode,
    rag_context: str | None,
    graph_context: str | None = None,
    scene_context: str | None = None,
) -> str:
    if mode in SCENE_MODES:
        blocks = [scene_context]
        if graph_context:
            blocks.append(graph_context)
        if rag_context:
            blocks.append(f"Document excerpts:\n{rag_context}")
        return f"{CRITIC_INSTRUCTIONS} {SCENE_ANSWER_FORMAT}\n\n" + "\n\n".join(blocks)
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
    if mode == "graph":
        return (
            f"{CRITIC_INSTRUCTIONS} Answer only from the knowledge-graph facts below. "
            "Combine facts across edges when the question needs it, and name the facts you used. "
            "If the facts do not contain the answer, say that the knowledge graph does not cover it "
            "instead of answering from general knowledge.\n\n"
            f"{graph_context}"
        )
    if mode == "graph_rag":
        return (
            f"{CRITIC_INSTRUCTIONS} Use the knowledge-graph facts for names, credits and "
            "relationships, and the document excerpts for plot, style and themes. "
            "If neither covers the question, say so.\n\n"
            f"{graph_context}\n\nDocument excerpts:\n{rag_context}"
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
    graph_context = None
    scene_context = None

    # Conditions of docs/scene_knowledge_design.md:
    # A = rag, B = scene_vector, C = graph_rag, D = scene_graph, E = scene_full.
    if mode in ("rag", "rag_tmdb", "graph_rag", *SCENE_MODES):
        sources = retrieve(user_message)
        rag_context = format_context(sources)
    if mode in ("graph", "graph_rag", "scene_graph"):
        graph_sources = retrieve_graph(user_message)
        graph_context = format_graph_context(graph_sources)
        sources = graph_sources + sources
    if mode in SCENE_MODES:
        if mode == "scene_vector":
            scene_sources = retrieve_scenes_vector(user_message)
            scene_context = format_scene_context(scene_sources)
        elif mode == "scene_graph":
            scene_sources = retrieve_scenes_graph(user_message)
            scene_context = format_scene_context(scene_sources)
        else:
            scene_context, scene_sources = all_scene_context()
        sources = scene_sources + sources

    messages: list[dict] = [
        {"role": "system", "content": _system_prompt(mode, rag_context, graph_context, scene_context)},
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
