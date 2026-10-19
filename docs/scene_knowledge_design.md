# Scene-level Knowledge Layer: Design

Status: the code is written and tested on a small fictional film (`backend/tests/`). I have not yet
written the scene notes for *Decision to Leave* or the question set, so there are no results yet.
The manual steps are described in `docs/annotation_guide.md`.

## 1. Why

The current graph (`graph_build.py`) only contains film metadata: credits, cast, genre and filmography.
It can answer questions such as "who edited both films". It cannot answer the questions I started this
assistant for: what happens in a scene, who does what, how two distant scenes are connected, and what a
shot or gesture might mean.

I divide film questions into three levels:

| Level | Example question | What it needs |
| --- | --- | --- |
| L1 Facts | Who shot *Decision to Leave*? | metadata (current graph, TMDB) |
| L2 Scene recall | Where did this object first appear, and what happened to it then? | scene notes and links between scenes |
| L3 Interpretation | Why does the film bring this object back at the end? | L2 evidence plus readings with a named source |

This design targets L2. L3 is only supported as readings that name their source and point to L2
evidence. The assistant should not claim to give "the" meaning of a scene.

Research question:

> Can structured scene-level knowledge make detailed film questions easier to answer correctly and to
> trace back to evidence? And when does a graph help more than plain retrieval over the same notes?

## 2. Pilot film: *Decision to Leave*

- It is already in the knowledge base (`data/rag/Decision_to_leave.md`).
- The film has two parts. The first part follows one case. The second part starts about a year later
  with a new case. Words, objects and places from the first part come back in the second part, often
  with a different meaning. To answer questions about them, the system has to connect scenes that are
  far apart in the film. Text similarity may miss these connections, and an explicit link can keep them.
- I will annotate 12–15 key scenes from my own viewing. Time stamps are approximate.

Copyright: the repository only stores my own short notes, time positions and citations.
It does not store video, subtitles or script text.

## 3. Data model

I write scene notes by hand in Markdown, using a fixed template. This is easier than writing JSON.
A script then turns them into JSON without using an LLM
(`scripts/scenes_check.py` → `results/scenes_<film>.json`).

```
data/scenes/
├── _template/{film.md, scene.md}
└── decision_to_leave/
    ├── film.md      canonical names of characters and objects, with aliases
    └── s01.md ...   one file per scene
```

Each scene file starts with a header (`scene_id`, `part`, `start`, `end`, `pov`, `location`, `verified`,
`verified_on`) and has these sections:

| Section | Content |
| --- | --- |
| Description | 3–6 sentences in my own words. This is the only input of the extraction experiment. |
| Characters | names, mapped to canonical names through `film.md` |
| Events | `e1 \| agent \| observable action \| objects: a, b \| uncertain` |
| Objects | objects in the scene |
| Dialogue summary | paraphrase only, no long quotes |
| Camera | framing, movement, light and sound that I noticed |
| Links | `e1 refers_back_to s04.e2 \| unverified \| note: ...` |
| Interpretations | `c1 \| attributed to \| reading \| supports: s03.e1, s09.e2` |

Link types:

| Link | Meaning |
| --- | --- |
| `same_object` | an object in scene B is the same physical object as in scene A |
| `refers_back_to` | something said or done in scene B points back to scene A |
| `follows_from` | an event in B is a consequence of an event in A |
| `contradicts` | B shows that what A showed (or suggested) was not true |
| `retells` | B shows the same event as A from another point of view (kept for other films) |

A link is written in the later scene and points back to the earlier one. Retrieval follows links in
both directions. Links that I could not confirm are marked `unverified`; they are flagged in the prompt
and counted separately. Interpretations are never stored as links between facts, and each one must
name the events it is based on.

`backend/app/services/scene_store.py` reads and checks the files. It reports unknown names, objects that
are not listed, links to missing scenes or events, interpretations without evidence, and scenes marked
as verified without a date.

## 4. Pipeline

1. **Reference notes.** I write the scene records and links by hand.
2. **Automatic extraction.** An LLM receives my written scene descriptions (not the JSON) and is asked
   for the same structure. I compare its output with my notes: which events it misses, which it invents,
   and which links are wrong. This is the "LLM-based knowledge graph construction" part. It is measured
   against a reference instead of being assumed to work.
3. **Graph.** Scenes, events, characters, objects and links are loaded next to the existing metadata graph.
4. **Retrieval.** Names and objects in the question are matched, events are searched by vector similarity,
   and the graph is expanded by one step along the links. Scene ids are returned as evidence.
5. **Answer format.** Three labelled parts: *Observed in the film* (with scene ids and times),
   *Interpretation* (with its source) and *Not covered by the notes*.

## 5. Experiment

### Conditions

Modes in `chat_service.py`: A `rag`, B `scene_vector`, C `graph_rag`, D `scene_graph`, E `scene_full`.
All scene modes use the same answer format and also receive the document excerpts, so they only differ
in how scene knowledge is selected. `scene_graph` starts from the vector results, adds scenes that share
a named object (or all named characters), and then follows links one step.

| | Metadata only | + verified scene notes |
| --- | --- | --- |
| Vector RAG | A | B |
| Graph + RAG | C | D |
| Full context (all notes in the prompt, no retrieval) | – | E |

E is the most important comparison. With about 15 scenes, all notes fit into the prompt, so retrieval may
not be needed at all, and E may give the best answers. A graph is only worth using if it helps when E
stops working. To test this, I will run B, D and E again after adding distractor material (documents
about the other films and scene notes from a second film) and see how each condition changes.

### Questions (about 40, written before running any system)

| Type | Count | Example shape |
| --- | --- | --- |
| L1 metadata | 6 | credits, years |
| L2 single scene | 10 | what happens, who is present |
| L2 cross-scene | 12 | where an object first appeared, what a later line refers back to |
| L3 interpretation | 6 | why, what it might mean |
| Not answerable from the notes | 6 | the system should say that it does not know |

### Measures

- Answer correctness against a reference answer (graded by hand: correct / partial / wrong).
- Evidence: do the cited scene ids really support the answer?
- Abstention: does the system say "not covered" when it should, and only then?
- Error location for every wrong answer: missing knowledge, retrieval miss, wrong note or link,
  or correct evidence but a wrong answer.
- Latency and prompt size.

With about 40 questions on one film, the results are a case study. They cannot support claims of
statistical significance. I will report a table per question and the error categories.

## 6. Steps

1. Annotate 12–15 scenes and their links; write the 40 questions and reference answers.
2. Load the scenes into the graph; add a vector index over events; add condition E.
3. Run A–E once, fill in the results table and write up the errors.
4. Compare LLM extraction with my notes.
5. Run the distractor experiment.

## 7. Related work to read

- MovieGraphs (Vicol et al., CVPR 2018): graph annotations of human-centred situations in 7,637 clips from 51 films.
- MovieNet (Huang et al., ECCV 2020): a multimodal dataset for film understanding (scenes, characters, places, actions).
- MovieQA (Tapaswi et al., CVPR 2016): question answering about films from plots, subtitles, scripts and video.
- DrVideo (Ma et al., CVPR 2025): turns a long video into a text document, retrieves key frames and adds detail back.
- VideoStir (Fu et al., ACL 2026): a clip-level spatio-temporal graph with multi-hop retrieval for long videos.

## 8. What can be claimed now

- Built: a metadata knowledge graph from the film documents, Graph and Graph + RAG modes, and an RDF export.
- Built and tested only on a fictional film: the scene layer and the evaluation scripts.
- Not yet done: scene notes and questions for *Decision to Leave*, and any results.
- Not claimed: video understanding, automatic graph construction from full films, or any accuracy improvement.
