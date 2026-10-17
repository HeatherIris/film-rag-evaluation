"""Summarize a graded evaluation CSV by condition and question type.

    python scripts/summarize_eval.py results/eval/handmaiden_questions_20261020_1400.csv

Grading values (see docs/annotation_guide.md):
  correctness     correct | partial | wrong
  evidence_ok     yes | no            (are the cited scene ids the right ones?)
  abstention_ok   yes | no            (only for answerable=no rows: did it say "not covered"?)
  error_location  missing_knowledge | retrieval_miss | bad_note_or_link | wrong_with_evidence
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

CORRECTNESS = ("correct", "partial", "wrong")
ERRORS = ("missing_knowledge", "retrieval_miss", "bad_note_or_link", "wrong_with_evidence")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/summarize_eval.py <graded csv>")
    path = Path(sys.argv[1])
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    ungraded = [r for r in rows if not r.get("error") and r.get("correctness", "").strip() not in CORRECTNESS]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["condition"] or row["mode"], row["mode"])].append(row)

    lines = [f"# Summary of {path.name}", ""]
    if ungraded:
        lines += [f"{len(ungraded)} rows are not graded yet; they are left out of the counts.", ""]

    lines += ["## By condition", "", "| Cond. | Mode | n | correct | partial | wrong | evidence ok | mean evidence recall | abstention ok | errors (run) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for (condition, mode), items in sorted(groups.items()):
        graded = [r for r in items if r.get("correctness", "").strip() in CORRECTNESS]
        counts = Counter(r["correctness"].strip() for r in graded)
        evidence = [r for r in graded if r.get("evidence_ok", "").strip() in ("yes", "no")]
        recalls = [float(r["evidence_recall"]) for r in items if r.get("evidence_recall")]
        abstain = [r for r in items if r.get("answerable", "").strip() == "no" and r.get("abstention_ok", "").strip() in ("yes", "no")]
        mean_recall = f"{sum(recalls) / len(recalls):.2f}" if recalls else "-"
        evidence_yes = sum(r["evidence_ok"].strip() == "yes" for r in evidence)
        abstain_yes = sum(r["abstention_ok"].strip() == "yes" for r in abstain)
        run_errors = sum(bool(r.get("error")) for r in items)
        lines.append(
            f"| {condition} | {mode} | {len(graded)} | {counts['correct']} | {counts['partial']} | {counts['wrong']} | "
            f"{evidence_yes}/{len(evidence)} | {mean_recall} | {abstain_yes}/{len(abstain)} | {run_errors} |"
        )

    lines += ["", "## Correct answers by question type", ""]
    types = sorted({r["type"] for r in rows})
    lines += ["| Cond. | Mode | " + " | ".join(types) + " |", "|---|---|" + "---|" * len(types)]
    for (condition, mode), items in sorted(groups.items()):
        cells = []
        for qtype in types:
            graded = [r for r in items if r["type"] == qtype and r.get("correctness", "").strip() in CORRECTNESS]
            cells.append(f"{sum(r['correctness'].strip() == 'correct' for r in graded)}/{len(graded)}")
        lines.append(f"| {condition} | {mode} | " + " | ".join(cells) + " |")

    lines += ["", "## Where the wrong and partial answers went wrong", ""]
    lines += ["| Cond. | Mode | " + " | ".join(ERRORS) + " | not labelled |", "|---|---|" + "---|" * (len(ERRORS) + 1)]
    for (condition, mode), items in sorted(groups.items()):
        bad = [r for r in items if r.get("correctness", "").strip() in ("partial", "wrong")]
        counts = Counter(r.get("error_location", "").strip() for r in bad)
        cells = [str(counts[e]) for e in ERRORS] + [str(sum(v for k, v in counts.items() if k not in ERRORS))]
        lines.append(f"| {condition} | {mode} | " + " | ".join(cells) + " |")

    lines += ["", "n is small (one film); read these as case counts, not significance."]
    report = "\n".join(lines) + "\n"
    out = path.with_name(path.stem + "_summary.md")
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
