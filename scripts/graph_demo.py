"""Print graph statistics and the facts retrieved for a few sample questions. No API key needed."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.graph_build import build_triples  # noqa: E402
from app.services.graph_service import find_entities, format_graph_context, retrieve_graph  # noqa: E402

QUESTIONS = [
    "Which editor worked on both The Handmaiden and Decision to Leave?",
    "Who shot Stoker, and did that cinematographer work with Park Chan-wook again?",
    "Which films in the knowledge base star Humphrey Bogart?",
    "Who composed the music for Decision to Leave?",
    "What does the final beach scene in Decision to Leave mean?",
]


def main() -> None:
    questions = sys.argv[1:] or QUESTIONS
    triples = build_triples()
    nodes = {t.subject for t in triples} | {t.object for t in triples if t.predicate != "release_year"}
    print(f"{len(triples)} triples, {len(nodes)} nodes")
    for predicate, count in Counter(t.predicate for t in triples).most_common():
        print(f"  {predicate:<20} {count}")

    for question in questions:
        print("\n" + "=" * 80)
        print(f"Q: {question}")
        print(f"Matched entities: {find_entities(question) or 'none'}")
        print(format_graph_context(retrieve_graph(question)[:15]))


if __name__ == "__main__":
    main()
