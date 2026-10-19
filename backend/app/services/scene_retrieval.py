"""
Retrieval over the scene notes in data/scenes/.

Three ways to give scene knowledge to the model, matching conditions B, D and E of
docs/scene_knowledge_design.md:

- retrieve_scenes_vector: embed every event line and scene description, return the best scenes.
- retrieve_scenes_graph: the same vector seeds, plus scenes that share a named object or all named
  characters with the question, plus scenes one link away (same_object / refers_back_to / ...).
- all_scene_context: every scene, no retrieval.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.models.schemas import Source
from app.services import retrieval_service
from app.services.scene_store import SCENES_DIR, Film, all_links, load_films, render_scene, scene_of

VECTOR_TOP_K = 4
GRAPH_SEEDS = 3
GRAPH_MAX_SCENES = 6
LINK_SCORE_FACTOR = 0.8


@dataclass
class _Index:
    signature: tuple
    films: list[Film]
    keys: list[tuple[str, str]]  # (film slug, scene id) per row of matrix
    matrix: np.ndarray | None


_lock = threading.Lock()
_index: _Index | None = None


def _signature(root: Path) -> tuple:
    if not root.is_dir():
        return ()
    return tuple(sorted((str(path), path.stat().st_mtime) for path in root.rglob("*.md")))


def _ensure_index(root: Path | None = None) -> _Index:
    """Build (or rebuild after any notes file changes) the embedding index."""
    global _index
    root = root or SCENES_DIR
    with _lock:
        signature = _signature(root)
        if _index is None or _index.signature != signature:
            films = [film for film in load_films(root) if film.scenes]
            texts: list[str] = []
            keys: list[tuple[str, str]] = []
            for film in films:
                for scene in film.scenes:
                    texts.append(f"{film.title}. {scene.description}")
                    keys.append((film.slug, scene.scene_id))
                    for event in scene.events:
                        objects = f" ({', '.join(event.objects)})" if event.objects else ""
                        texts.append(f"{film.title}. {event.agent} {event.action}{objects}")
                        keys.append((film.slug, scene.scene_id))
            matrix = retrieval_service._embed(texts) if texts else None
            _index = _Index(signature=signature, films=films, keys=keys, matrix=matrix)
        return _index


def has_scenes(root: Path | None = None) -> bool:
    return any(film.scenes for film in load_films(root or SCENES_DIR))


def _vector_scores(index: _Index, query: str) -> dict[tuple[str, str], float]:
    if index.matrix is None:
        return {}
    query_vec = retrieval_service._embed([query])[0]
    scores = index.matrix @ query_vec
    best: dict[tuple[str, str], float] = {}
    for key, score in zip(index.keys, scores):
        best[key] = max(float(score), best.get(key, -1.0))
    return best


def _film(index: _Index, slug: str) -> Film:
    return next(film for film in index.films if film.slug == slug)


def _source(index: _Index, key: tuple[str, str], score: float, why: str) -> Source:
    film = _film(index, key[0])
    scene = film.scene(key[1])
    chunk = render_scene(scene, film)
    if why:
        chunk = f"(retrieved because: {why})\n{chunk}"
    return Source(filename=f"scenes/{film.slug}/{scene.scene_id}", chunk=chunk, score=round(score, 4))


def retrieve_scenes_vector(query: str, top_k: int = VECTOR_TOP_K) -> list[Source]:
    index = _ensure_index()
    ranked = sorted(_vector_scores(index, query).items(), key=lambda item: -item[1])[:top_k]
    return [_source(index, key, score, "") for key, score in ranked]


def _mentions(film: Film, query: str) -> tuple[set[str], set[str]]:
    """Canonical object and character names mentioned in the query."""
    objects: set[str] = set()
    characters: set[str] = set()
    known_objects = {obj for scene in film.scenes for obj in scene.objects}
    for alias, canonical in sorted(film.names.items(), key=lambda item: -len(item[0])):
        if len(alias) < 3 or not re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", query, re.IGNORECASE):
            continue
        if canonical in film.characters:
            characters.add(canonical)
        elif canonical in known_objects:
            objects.add(canonical)
    for obj in known_objects:
        if len(obj) >= 3 and re.search(rf"(?<!\w){re.escape(obj)}(?!\w)", query, re.IGNORECASE):
            objects.add(obj)
    return objects, characters


def retrieve_scenes_graph(query: str, max_scenes: int = GRAPH_MAX_SCENES) -> list[Source]:
    index = _ensure_index()
    vector = _vector_scores(index, query)
    chosen: dict[tuple[str, str], tuple[float, str]] = {}

    def add(key: tuple[str, str], score: float, why: str) -> None:
        if key not in chosen or chosen[key][0] < score:
            chosen[key] = (score, why)

    for key, score in sorted(vector.items(), key=lambda item: -item[1])[:GRAPH_SEEDS]:
        add(key, score, "text similarity")

    top_score = max(vector.values(), default=1.0)
    for film in index.films:
        objects, characters = _mentions(film, query)
        for scene in film.scenes:
            key = (film.slug, scene.scene_id)
            base = vector.get(key, 0.0)
            shared_objects = objects & set(scene.objects)
            if shared_objects:
                add(key, max(base, top_score * 0.95), f"shows {', '.join(sorted(shared_objects))}")
            # A single character name matches most scenes, so only use characters in combination.
            if len(characters) >= 2 and characters <= set(scene.characters):
                add(key, max(base, top_score * 0.9), f"has {', '.join(sorted(characters))}")

    # One hop along the annotated links, in both directions.
    seeds = dict(chosen)
    for film in index.films:
        for link in all_links(film):
            ends = ((film.slug, scene_of(link.source)), (film.slug, scene_of(link.target)))
            for here, there in (ends, ends[::-1]):
                if here in seeds and there not in seeds:
                    score = seeds[here][0] * LINK_SCORE_FACTOR
                    flag = "" if link.verified else ", unverified"
                    add(there, score, f"{link.predicate} link from {here[1]}{flag}")

    ranked = sorted(chosen.items(), key=lambda item: -item[1][0])[:max_scenes]
    return [_source(index, key, score, why) for key, (score, why) in ranked]


def all_scene_context(root: Path | None = None) -> tuple[str, list[Source]]:
    root = root or SCENES_DIR
    sources = [
        Source(filename=f"scenes/{film.slug}/{scene.scene_id}", chunk=render_scene(scene, film), score=1.0)
        for film in load_films(root)
        for scene in film.scenes
    ]
    return format_scene_context(sources), sources


def format_scene_context(sources: list[Source]) -> str:
    if not sources:
        return "(No scene notes were retrieved.)"
    return "Scene notes (hand-written, cite them by scene id such as s03.e1):\n\n" + "\n\n".join(
        source.chunk for source in sources
    )


def retrieved_scene_ids(sources: list[Source]) -> list[str]:
    return [source.filename.rsplit("/", 1)[-1] for source in sources if source.filename.startswith("scenes/")]
