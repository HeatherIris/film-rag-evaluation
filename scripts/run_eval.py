"""Run every question in a question CSV through the selected modes and write a CSV to grade by hand.

    python scripts/run_eval.py data/eval/handmaiden_questions.csv
    python scripts/run_eval.py data/eval/handmaiden_questions.csv --modes scene_vector scene_graph
    python scripts/run_eval.py data/eval/handmaiden_questions.csv --retrieval-only   # no chat calls

Default modes are the five conditions of docs/scene_knowledge_design.md:
A rag, B scene_vector, C graph_rag, D scene_graph, E scene_full.

evidence_recall is computed automatically: the share of scenes in the question's `evidence` column
that the mode put in front of the model. Everything else (correctness, abstention, error location)
is left empty for you to fill in; then run scripts/summarize_eval.py on the graded file.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.scene_retrieval import (  # noqa: E402
    all_scene_context,
    retrieve_scenes_graph,
    retrieve_scenes_vector,
    retrieved_scene_ids,
)

DEFAULT_MODES = ["rag", "scene_vector", "graph_rag", "scene_graph", "scene_full"]
CONDITION = {"rag": "A", "scene_vector": "B", "graph_rag": "C", "scene_graph": "D", "scene_full": "E"}
GRADING_COLUMNS = ["correctness", "evidence_ok", "abstention_ok", "error_location", "grader_notes"]
QUESTION_COLUMNS = ["qid", "type", "question", "reference_answer", "evidence", "answerable"]


def read_questions(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    missing = [column for column in QUESTION_COLUMNS if rows and column not in rows[0]]
    if missing:
        sys.exit(f"{path}: missing columns {missing}")
    rows = [row for row in rows if row["qid"].strip() and not row["question"].startswith("<")]
    ids = [row["qid"] for row in rows]
    if len(ids) != len(set(ids)):
        sys.exit(f"{path}: duplicate qid values")
    return rows


def evidence_scenes(value: str) -> set[str]:
    return {ref.strip().split(".", 1)[0] for ref in value.replace(",", ";").split(";") if ref.strip()}


def recall(expected: set[str], got: list[str]) -> str:
    if not expected:
        return ""
    return f"{len(expected & set(got)) / len(expected):.2f}"


def retrieval_only_sources(mode: str, question: str):
    if mode == "scene_vector":
        return retrieve_scenes_vector(question)
    if mode == "scene_graph":
        return retrieve_scenes_graph(question)
    if mode == "scene_full":
        return all_scene_context()[1]
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("questions", type=Path)
    parser.add_argument("--modes", nargs="+", default=DEFAULT_MODES)
    parser.add_argument("--retrieval-only", action="store_true", help="only run scene retrieval, no answers")
    parser.add_argument("--limit", type=int, default=0, help="only the first N questions")
    args = parser.parse_args()

    questions = read_questions(args.questions)
    if args.limit:
        questions = questions[: args.limit]
    if not questions:
        sys.exit("no questions (rows starting with '<' are treated as template placeholders)")

    if not args.retrieval_only:
        from app.services.chat_service import generate_reply

    out_dir = ROOT / "results" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    suffix = "_retrieval" if args.retrieval_only else ""
    out_path = out_dir / f"{args.questions.stem}_{stamp}{suffix}.csv"

    columns = QUESTION_COLUMNS + ["mode", "condition", "answer", "retrieved_scenes", "evidence_recall", "latency_ms", "error"] + GRADING_COLUMNS
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for question in questions:
            expected = evidence_scenes(question["evidence"])
            for mode in args.modes:
                row = {column: question.get(column, "") for column in QUESTION_COLUMNS}
                row.update(mode=mode, condition=CONDITION.get(mode, ""))
                try:
                    if args.retrieval_only:
                        sources = retrieval_only_sources(mode, question["question"])
                        answer, latency = "", ""
                    else:
                        reply = generate_reply(history=[], user_message=question["question"], mode=mode)
                        sources, answer, latency = reply.sources, reply.answer, reply.latency_ms
                    scenes = retrieved_scene_ids(sources)
                    row.update(
                        answer=answer,
                        retrieved_scenes=";".join(scenes),
                        evidence_recall=recall(expected, scenes) if mode.startswith("scene") else "",
                        latency_ms=latency,
                    )
                except Exception as exc:  # keep going; the error is recorded in the row
                    row.update(error=str(exc))
                writer.writerow(row)
                handle.flush()
                status = row["error"][:60] if row.get("error") else f"recall={row['evidence_recall'] or '-'}"
                print(f"{question['qid']:<6} {mode:<13} {status}")

    print(f"\nwrote {out_path.relative_to(ROOT)}")
    if not args.retrieval_only:
        print("grade it (columns " + ", ".join(GRADING_COLUMNS) + "), then run scripts/summarize_eval.py on it")


if __name__ == "__main__":
    main()
