from __future__ import annotations

import os
import threading
from pathlib import Path

import numpy as np
from fastapi import HTTPException, status
from openai import OpenAI

from app.models.schemas import Source

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAG_DIR = PROJECT_ROOT / "data" / "rag"

EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 4

_lock = threading.Lock()
_chunks: list[dict] | None = None
_matrix: np.ndarray | None = None


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not set.",
        )
    return OpenAI(api_key=api_key)


def _window(text: str) -> list[str]:
    windows: list[str] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        piece = text[start:end].strip()
        if piece:
            windows.append(piece)
        if end >= len(text):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return windows


def _split_text(text: str) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(paragraph) > CHUNK_SIZE:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(_window(paragraph))
            continue
        candidate = paragraph if not buffer else f"{buffer}\n\n{paragraph}"
        if len(candidate) <= CHUNK_SIZE:
            buffer = candidate
        else:
            chunks.append(buffer)
            buffer = paragraph
    if buffer:
        chunks.append(buffer)
    return chunks


def _load_chunks() -> list[dict]:
    if not RAG_DIR.is_dir():
        raise FileNotFoundError(f"RAG data directory not found: {RAG_DIR}")
    loaded: list[dict] = []
    for path in sorted(RAG_DIR.glob("*.md")):
        for chunk in _split_text(path.read_text(encoding="utf-8")):
            loaded.append({"filename": path.name, "chunk": chunk})
    if not loaded:
        raise FileNotFoundError(f"No RAG chunks found in {RAG_DIR}")
    return loaded


def _embed(texts: list[str]) -> np.ndarray:
    client = _client()
    vectors: list[list[float]] = []
    batch_size = 64
    for i in range(0, len(texts), batch_size):
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts[i : i + batch_size],
        )
        vectors.extend([item.embedding for item in response.data])
    matrix = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    return matrix / norms


def _ensure_index() -> tuple[list[dict], np.ndarray]:
    global _chunks, _matrix
    with _lock:
        if _chunks is None or _matrix is None:
            loaded = _load_chunks()
            _matrix = _embed([item["chunk"] for item in loaded])
            _chunks = loaded
        return _chunks, _matrix


def retrieve(query: str, top_k: int = TOP_K) -> list[Source]:
    chunks, matrix = _ensure_index()
    query_vec = _embed([query])[0]
    scores = matrix @ query_vec
    k = min(top_k, len(chunks))
    top_indices = np.argsort(scores)[::-1][:k]
    return [
        Source(
            filename=chunks[i]["filename"],
            chunk=chunks[i]["chunk"],
            score=float(scores[i]),
        )
        for i in top_indices
    ]


def format_context(sources: list[Source]) -> str:
    if not sources:
        return "(No relevant knowledge-base excerpts were retrieved.)"
    parts = []
    for i, source in enumerate(sources, start=1):
        parts.append(
            f"[{i}] {source.filename} (score={source.score:.3f})\n{source.chunk}"
        )
    return "\n\n".join(parts)
