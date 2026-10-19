# Notes for Claude

Film-domain assistant (FastAPI + React) used as a research prototype: metadata knowledge graph, and a
scene-level knowledge layer built from hand-written, human-verified scene notes.

Start of every session: read `docs/ROADMAP.md` (progress checklist and decisions, in Chinese) and tell the
user which unchecked item comes next. Detailed procedures are in `docs/annotation_guide.md`; the experiment
design is in `docs/scene_knowledge_design.md`. Reply to the user in Chinese.

## Rules for scene notes (`data/scenes/`) and questions (`data/eval/`)

These files are the gold reference of the experiment. Their content must come from the user's own viewing.

- Never add, remove, merge or reword events, links, interpretations, descriptions or reference answers,
  and never use your own knowledge of the film to fill them in. Formatting fixes only, and only when asked.
- Never set `verified: yes` or `verified_on`.
- Never generate Events from a Description: that is what `scripts/extract_scenes.py` measures.
- Never change questions or reference answers after seeing system outputs.
- Translation from the user's Chinese drafts: sentence by sentence, no rewording; say so in the commit message.
- Show the diff and let the user commit changes to these directories.
- No subtitles, script text, long quotes or screenshots in the repository.

## Commands

```bash
pip install -r backend/requirements.txt
cd backend && python -m pytest -q tests          # fictional demo film, no API key
python scripts/scenes_check.py decision_to_leave    # validate scene notes
python scripts/graph_demo.py                     # metadata graph retrieval demo
python scripts/run_eval.py data/eval/<file>.csv [--retrieval-only]
python scripts/summarize_eval.py results/eval/<graded file>.csv
python scripts/extract_scenes.py decision_to_leave
cd frontend && npx tsc -b                        # type check
```

Answer modes (`backend/app/models/schemas.py`): llm, rag (A), rag_tmdb, graph, graph_rag (C),
scene_vector (B), scene_graph (D), scene_full (E). Adding a mode means updating the schema, `chat_service.py`,
`frontend/src/types/index.ts`, `ModeSelector.tsx` and `EvaluationPage.tsx`.

## Honesty

No accuracy results exist yet. Do not write or imply improvements in README, commit messages or
application text until `summarize_eval.py` output supports them.
