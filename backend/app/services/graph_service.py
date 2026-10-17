from __future__ import annotations

import re
import threading
from collections import defaultdict

from app.models.schemas import Source
from app.services.graph_build import ALIASES, Triple, build_triples

# Nodes with more edges than this are hubs: they are never expanded to a second hop,
# and their own edges rank low when they are mentioned in the query.
# Otherwise a question mentioning one Park Chan-wook film pulls in his whole filmography.
HUB_DEGREE = 30
MAX_FACTS = 40

# Predicates whose objects are plain values rather than entities worth matching in a query.
LITERAL_PREDICATES = {"release_year"}

_lock = threading.Lock()
_triples: list[Triple] | None = None
_edges: dict[str, list[Triple]] | None = None
_names: list[tuple[str, re.Pattern[str]]] | None = None


def _ensure_graph() -> tuple[list[Triple], dict[str, list[Triple]], list[tuple[str, re.Pattern[str]]]]:
    global _triples, _edges, _names
    with _lock:
        if _triples is None or _edges is None or _names is None:
            triples = build_triples()
            edges: dict[str, list[Triple]] = defaultdict(list)
            for triple in triples:
                edges[triple.subject].append(triple)
                if triple.predicate not in LITERAL_PREDICATES:
                    edges[triple.object].append(triple)

            surface_forms: dict[str, str] = {node: node for node in edges}
            for alias, canonical in ALIASES.items():
                if canonical in edges:
                    surface_forms[alias] = canonical
            # Longest names first so "Sympathy for Lady Vengeance" wins over "Lady Vengeance".
            names = [
                (canonical, re.compile(rf"(?<!\w){re.escape(form)}(?!\w)", re.IGNORECASE))
                for form, canonical in sorted(surface_forms.items(), key=lambda item: -len(item[0]))
                if len(form) > 2
            ]
            _triples, _edges, _names = triples, dict(edges), names
        return _triples, _edges, _names


def find_entities(query: str) -> list[str]:
    _, _, names = _ensure_graph()
    found: list[str] = []
    remaining = query
    for canonical, pattern in names:
        if pattern.search(remaining):
            if canonical not in found:
                found.append(canonical)
            remaining = pattern.sub(" ", remaining)
    return found


def _fact(triple: Triple) -> str:
    return f"{triple.subject} --{triple.predicate}--> {triple.object}"


def retrieve_graph(query: str, max_facts: int = MAX_FACTS) -> list[Source]:
    """
    Match entity names in the query, then collect their edges (hop 1) and the
    edges of their non-hub neighbours (hop 2).

    Scores: hop-1 edges of a normal seed 1.0, hop-2 edges 0.5, hop-1 edges of a
    hub seed 0.3 (a hub such as Park Chan-wook would otherwise fill the context
    with his filmography). Any edge joining two seeds scores 1.0.
    """
    _, edges, _ = _ensure_graph()
    seeds = find_entities(query)
    scored: dict[Triple, float] = {}

    for seed in seeds:
        is_hub = len(edges.get(seed, [])) > HUB_DEGREE
        for triple in edges.get(seed, []):
            joins_seeds = triple.subject in seeds and triple.object in seeds
            score = 1.0 if joins_seeds or not is_hub else 0.3
            scored[triple] = max(score, scored.get(triple, 0.0))

    for seed in seeds:
        if len(edges.get(seed, [])) > HUB_DEGREE:
            continue
        for triple in edges.get(seed, []):
            neighbour = triple.object if triple.subject == seed else triple.subject
            if neighbour in seeds or len(edges.get(neighbour, [])) > HUB_DEGREE:
                continue
            for second in edges.get(neighbour, []):
                scored[second] = max(0.5, scored.get(second, 0.0))

    # For multi-entity questions, nodes linked to two or more seeds are usually the answer
    # ("which editor worked on both films"), so their edges go first.
    seed_links: dict[str, set[str]] = defaultdict(set)
    for seed in seeds:
        for triple in edges.get(seed, []):
            seed_links[triple.object if triple.subject == seed else triple.subject].add(seed)
    shared = {node for node, linked in seed_links.items() if len(linked) > 1}

    def rank(item: tuple[Triple, float]) -> tuple[int, float, int]:
        triple, score = item
        touches_shared = triple.subject in shared or triple.object in shared
        touching = sum(1 for node in (triple.subject, triple.object) if node in seeds)
        return (-int(touches_shared and touching > 0), -score, -touching)

    ranked = sorted(scored.items(), key=rank)[:max_facts]
    return [Source(filename=triple.source, chunk=_fact(triple), score=score) for triple, score in ranked]


def format_graph_context(sources: list[Source]) -> str:
    if not sources:
        return "(No matching entities were found in the film knowledge graph.)"
    lines = [f"- {source.chunk} [source: {source.filename}, hop={'2' if source.score == 0.5 else '1'}]" for source in sources]
    return "Knowledge-graph facts (subject --predicate--> object):\n" + "\n".join(lines)
