# Film Intelligence Assistant

A full-stack film-domain AI assistant built with React, FastAPI, retrieval-augmented generation, TMDB tool calling, persistent conversation memory, and an evaluation workspace for comparing different answer-generation strategies.

This project started as a university film assistant prototype and has since been restructured into a modular AI application for experimenting with domain-specific retrieval, tool use, memory, and evaluation.

## Current Capabilities

### Film-domain question answering

The assistant supports three answer modes:

- **LLM only** — answers using the language model without retrieval or external tools.
- **RAG** — retrieves relevant chunks from a local film knowledge base before generating an answer.
- **RAG + TMDB** — combines retrieval with live movie metadata from the TMDB API.

The current retrieval pipeline uses:

- Markdown film documents
- paragraph-aware chunking
- OpenAI `text-embedding-3-small`
- cosine similarity with NumPy
- top-k retrieval
- no external vector database

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
                           LLM         RAG         TMDB
                                        |
                                        v
                                  Film Knowledge Base
```

The React app talks to FastAPI over `/api`. Chat, memory, and evaluation share the same generation services. Conversations and memories are written to SQLite. RAG reads `data/rag/` markdown files; TMDB is called only in `rag_tmdb` mode.

## Project Structure

```text
film-rag-evaluation/
├── frontend/                 # React + TypeScript + Vite UI
├── backend/                  # FastAPI app, retrieval, TMDB, SQLite
├── data/rag/                 # film knowledge-base documents
├── notebooks/                # original coursework assistant notebook
├── docs/                     # original written report
├── results/                  # reserved for later evaluation artifacts
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
- batch evaluation datasets
- GraphRAG
- richer memory, including automatic summaries
