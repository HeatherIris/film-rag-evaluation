# Film Intelligence Assistant

A full-stack film-domain AI assistant built with React, FastAPI, retrieval-augmented generation, a small film knowledge graph, TMDB tool calling, persistent conversation memory, and an evaluation workspace for comparing different answer-generation strategies.

This project started as a university film assistant prototype and has since been restructured into a modular AI application for experimenting with domain-specific retrieval, tool use, memory, and evaluation.

## Current Capabilities

### Film-domain question answering

The assistant supports five answer modes:

- **LLM only** — answers using the language model without retrieval or external tools.
- **RAG** — retrieves relevant chunks from a local film knowledge base before generating an answer.
- **RAG + TMDB** — combines retrieval with live movie metadata from the TMDB API.
- **Graph** — answers only from facts retrieved from the film knowledge graph, and says so when the graph does not cover the question.
- **Graph + RAG** — gives the model both graph facts (credits, relationships) and document chunks (plot, style, themes).

The current retrieval pipeline uses:

- Markdown film documents
- paragraph-aware chunking
- OpenAI `text-embedding-3-small`
- cosine similarity with NumPy
- top-k retrieval
- no external vector database

### Film knowledge graph

`backend/app/services/graph_build.py` turns the structured parts of the markdown files into subject–predicate–object triples:

- the "Basic Information" list of each film page (director, writers, cast, crew, companies, genre, language, source novel)
- the filmography, screenwriting, producer and collaborator lists on the Park Chan-wook page
- the representative-films list on the film noir page (year, director, stars)

Plot, theme and analysis paragraphs are not converted; they stay in the vector index. The current graph has 179 triples and 127 nodes.

`backend/app/services/graph_service.py` does the retrieval:

1. Match node names (and known spelling variants) in the question.
2. Collect the matched nodes' edges (hop 1) and the edges of their neighbours (hop 2).
3. Nodes with more than 30 edges (currently only Park Chan-wook) are treated as hubs: they are not expanded to a second hop, and their own edges rank low, so one mention does not fill the context with the whole filmography.
4. Edges touching a node shared by two matched entities rank first, e.g. the editor of both films in "Which editor worked on both *The Handmaiden* and *Decision to Leave*?".
5. The top 40 facts are passed to the model with their source file.

Two scripts work without an API key:

```bash
python scripts/graph_demo.py                       # graph statistics and retrieved facts for sample questions
python scripts/graph_demo.py "Who shot Stoker?"    # or your own questions
python scripts/export_ttl.py                       # writes results/film_graph.ttl and runs one SPARQL query
```

Known limitations:

- The graph is small and built from five hand-written documents; the field-to-predicate mapping is written by hand.
- Entity matching is exact string matching on node names, not entity linking. Questions that do not name an entity retrieve nothing from the graph.
- Spelling variants are merged with a manual alias table (`ALIASES` in `graph_build.py`), e.g. `Jo Yeong-wook` → `Cho Young-wuk`, `Jeong Seo-kyeong` → `Jeong Seo-kyung`.
- The hub threshold (30) and the 40-fact limit were chosen by inspecting a few questions, not tuned.
- No accuracy comparison between Graph, Graph + RAG and RAG has been run yet.

### TMDB tool integration

For movie metadata queries, the assistant can call TMDB to retrieve information such as:

- title
- director
- release date
- genres
- runtime
- rating
- plot overview

Tool calling is handled through the backend and is available in `rag_tmdb` mode.

### Persistent conversations

Conversation state is stored in SQLite.

Stored data includes:

- conversations
- user messages
- assistant messages
- selected answer mode
- timestamps

Conversation history remains available after backend restarts.

### Memory

The assistant includes a simple persistent memory layer.

Current memory types:

- `preference`
- `topic`
- `fact`
- `summary`

Memory extraction is intentionally conservative. The system does not store every message. It only records clear reusable statements such as user preferences or previously discussed topics.

Users can inspect and delete stored memories from the frontend.

### Evaluation workspace

The Evaluation page can compare the same film-domain question across:

- LLM only
- RAG
- RAG + TMDB
- Graph
- Graph + RAG

For each mode, the system records:

- generated answer
- latency
- retrieved sources
- source count
- tool calls
- errors

Each mode runs independently and evaluation runs are not stored as normal chat conversations.

Automatic groundedness, hallucination, and factual-accuracy scoring are planned but not implemented yet.

## Architecture

```text
React Frontend
      |
      v
FastAPI Backend
      |
      +-----------------------+
      |                       |
      v                       v
Conversation / Memory      AI Services
SQLite                     |
                            +-----------------------+
                            |           |           |
                            v           v           v
                           LLM      RAG / Graph     TMDB
                                        |
                                        v
                              Film Knowledge Base
                        (markdown chunks + knowledge graph)
```

The React app talks to FastAPI over `/api`. Chat, memory, and evaluation share the same generation services. Conversations and memories are written to SQLite. RAG and the knowledge graph both read `data/rag/` markdown files; TMDB is called only in `rag_tmdb` mode.

## Project Structure

```text
film-rag-evaluation/
├── frontend/                 # React + TypeScript + Vite UI
├── backend/                  # FastAPI app, retrieval, knowledge graph, TMDB, SQLite
├── data/rag/                 # film knowledge-base documents
├── scripts/                  # graph demo and RDF/Turtle export
├── notebooks/                # original coursework assistant notebook
├── docs/                     # original written report
├── results/                  # exported graph (film_graph.ttl); later evaluation artifacts
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

The original notebook remains in `notebooks/Film_Assistant.ipynb`. The running product is the FastAPI backend and React frontend.

## Setup

1. Create a virtual environment and install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. Set API keys in the environment. Do not commit them.

```bash
export OPENAI_API_KEY="your-openai-key"
export TMDB_API_KEY="your-tmdb-key"
```

`.env.example` lists the variable names only. SQLite is created automatically at `data/app.sqlite` (gitignored).

3. Start the backend:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

4. Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

Chat, retrieval, TMDB, and evaluation all require a funded OpenAI key. Missing keys or quota failures are returned as errors; the UI does not invent answers.

## Security

API credentials are loaded from environment variables (`OPENAI_API_KEY`, `TMDB_API_KEY`) and must not be hardcoded or committed. `.gitignore` excludes `.env` and SQLite database files. `.env.example` contains placeholders only.

## Future Work

The following items are planned, not implemented:

- groundedness scoring
- hallucination analysis
- automatic factual-accuracy scoring
- batch evaluation datasets, including a Graph vs RAG comparison
- LLM-based entity and relation extraction from the plot and theme paragraphs
- scene-level knowledge layer (scenes, events, cross-scene links, attributed interpretations); see [docs/scene_knowledge_design.md](docs/scene_knowledge_design.md)
- richer memory, including automatic summaries
