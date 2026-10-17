# Scene-level Knowledge Layer: Design

Status: code implemented and tested on a fictional demo film (`backend/tests/`). The scene notes for
*The Handmaiden* and the question set are not written yet, so no results exist. Annotation steps: `docs/annotation_guide.md`.

## 1. Why

The current graph (`graph_build.py`) only holds film metadata: credits, cast, genre, filmography.
That answers questions such as "who edited both films", but not the questions this assistant was
started for: what happens in a scene, who does what, how two distant scenes relate, and what a
shot or gesture might mean.

| Layer | Example question | What it needs |
| --- | --- | --- |
| L1 Facts | Who shot *The Handmaiden*? | metadata (current graph, TMDB) |
| L2 Scene recall | When Part 2 shows an event already seen in Part 1, what does it reveal that Part 1 hid? | scene-level records, links between scenes |
| L3 Interpretation | Why is this scene shown twice from different sides? | L2 evidence plus attributed readings |

L2 is the target of this design. L3 is supported only as attributed claims that point to L2 evidence;
the assistant does not produce "the" meaning of a scene.

Research question:

> Can scene-level structured knowledge improve the accuracy and traceability of detailed film
> question answering, and when does a graph structure help beyond plain retrieval over the same notes?

## 2. Pilot film: *The Handmaiden*

- Already in the knowledge base (`data/rag/The_Handmaiden.md`).
- Its three-part structure retells events from a second character's point of view. The same event appears
  in two distant scenes, which is exactly the kind of cross-scene link a graph can encode and text
  similarity can miss.
- 12–15 key scenes, annotated by me from my own viewing. Time stamps are approximate.

Copyright: the repository stores only my own short notes, time positions and citations.
No video, subtitles, or script text.

## 3. Data model

Scene notes are written by hand as Markdown from a fixed template (easier to write than JSON) and
parsed without any LLM into JSON (`scripts/scenes_check.py` → `results/scenes_<film>.json`).

```
data/scenes/
├── _template/{film.md, scene.md}
└── the_handmaiden/
    ├── film.md      canonical character / object names and aliases
    └── s01.md ...   one file per scene
```

A scene file has a front-matter block (`scene_id`, `part`, `start`, `end`, `pov`, `location`, `verified`,
`verified_on`) and these sections:

| Section | Content |
| --- | --- |
| Description | 3–6 sentences in my own words; the only input of the extraction experiment |
| Characters | names, mapped to canonical names via `film.md` |
| Events | `e1 \| agent \| observable action \| objects: a, b \| uncertain` |
| Objects | objects in the scene |
| Dialogue summary | paraphrase, no long quotes |
| Camera | framing, movement, light, sound I noticed |
| Links | `e1 retells s09.e2 \| unverified \| note: ...` |
| Interpretations | `c1 \| attributed to \| reading \| supports: s03.e1, s09.e2` |

Link predicates:

| Predicate | Meaning |
| --- | --- |
| `retells` | scene B shows the same event as scene A from another point of view |
| `same_object` | an object in scene B is the same physical object as in scene A |
| `follows_from` | an event in B is a consequence of an event in A |
| `contradicts` | B reveals that what A showed (or implied) was false |

Links are written in the later scene and point back; retrieval follows them in both directions.
Unverified links are flagged in the prompt and counted separately. Interpretations are never graph
edges between facts; each one must cite the events it rests on.

`backend/app/services/scene_store.py` parses and validates the files (unknown names, objects not listed,
links to missing scenes or events, interpretations without evidence, verified without a date).

## 4. Pipeline

1. **Gold notes**: I write the scene records and links by hand.
2. **Automatic extraction**: give an LLM my prose scene descriptions (not the JSON) and ask it for the
   same schema. Compare with the gold notes: missed events, invented events, wrong or invented links.
   This is the "LLM-based KG construction" part, measured against a reference rather than assumed to work.
3. **Graph**: load scene, event, character, object nodes and links next to the existing metadata graph.
4. **Retrieval**: entity and object matching plus vector search over event text; graph expansion
   along `retells` / `same_object` / `follows_from`; return scene ids as evidence.
5. **Answer format**: three labelled parts: *Observed in the film* (with scene ids and time),
   *Interpretation* (with attribution), *Not covered by the notes*.

## 5. Experiment

### Conditions

Modes in `chat_service.py`: A `rag`, B `scene_vector`, C `graph_rag`, D `scene_graph`, E `scene_full`.
All scene modes share one answer format (Observed in the film / Interpretation / Not covered) and also
receive the document excerpts, so the conditions differ only in how scene knowledge is selected.
`scene_graph` = vector seeds + scenes sharing a named object (or all named characters) + one hop along links.

| | Metadata only | + verified scene notes |
| --- | --- | --- |
| Vector RAG | A | B |
| Hybrid graph | C | D |
| Full context (all notes in the prompt, no retrieval) | – | E |

E matters most. With 15 scenes, every note fits in the prompt, so retrieval is not needed and E is the
likely upper bound. A graph is only worth arguing for if it helps where E stops working. To test that,
repeat B / D / E after adding distractor material (the other films' documents and scene notes from a
second film) and report how each condition degrades.

### Questions (about 40, written before running any system)

| Type | Count | Example shape |
| --- | --- | --- |
| L1 metadata | 6 | credits, years |
| L2 single scene | 10 | what happens / who is present |
| L2 cross-scene | 12 | the event shown again later, the object's first appearance |
| L3 interpretation | 6 | why / what might it mean |
| Unanswerable from the notes | 6 | the system should say it does not know |

### Measures

- Answer correctness against a reference answer (manual rubric: correct / partial / wrong).
- Evidence correctness: are the cited scene ids the ones that support the answer?
- Abstention: correct "not covered" on unanswerable questions; false abstentions elsewhere.
- Error location for every wrong answer: missing knowledge / retrieval miss / wrong extraction or link /
  correct evidence but wrong answer.
- Latency and prompt size.

With about 40 questions on one film, results are case studies, not statistically significant claims.
Report per-question tables and error categories.

## 6. Milestones

1. Annotate 12–15 scenes and the links; write the 40 questions and references.
2. Load scenes into the graph; add vector index over events; condition E.
3. Run A–E once, fill the result table, write up errors.
4. LLM extraction vs gold notes.
5. Distractor/scale run.

## 7. Related work to read

- MovieGraphs (Vicol et al., CVPR 2018): graph annotations of human-centric situations in 7,637 clips from 51 films.
- MovieNet (Huang et al., ECCV 2020): multimodal movie understanding dataset (scenes, characters, places, actions).
- MovieQA (Tapaswi et al., CVPR 2016): question answering over films from plots, subtitles, scripts and video.
- DrVideo (Ma et al., CVPR 2025): turns long video into a text document, retrieves key frames, adds detail back.
- VideoStir (Fu et al., ACL 2026): clip-level spatio-temporal graph with multi-hop retrieval for long video.

## 8. What can be claimed now

- Built: a metadata knowledge graph from the film documents, graph and graph + RAG modes, RDF export.
- Designed, not built: scene-level layer and the experiment above.
- Not claimed: video understanding, automatic graph construction from full films, any accuracy improvement.
