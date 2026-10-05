# Film RAG Evaluation

## Overview

This project originated as a film-focused AI assistant coursework notebook. It combines:

- OpenAI-based language model interaction (Assistants API, `gpt-4o-mini`)
- Retrieval-Augmented Generation over film-related markdown documents
- TMDB API integration for live movie metadata
- tool / function calling so the assistant can request TMDB details
- domain-specific film questions about Park Chan-wook, selected films, and film noir

The current repository is being prepared as an **evaluation-oriented RAG project**. The notebook already runs a RAG + TMDB assistant; a systematic evaluation harness is **not** implemented yet.

## Current Capabilities

Features that exist in `notebooks/Film_Assistant.ipynb` today:

- Load `OPENAI_API_KEY` and `TMDB_API_KEY` from environment variables
- Create an OpenAI assistant with `file_search` and a `get_movie_details_tmdb` function tool
- Upload local RAG documents into an OpenAI vector store and attach it to the assistant
- Search TMDB by title and return director, release date, genres, overview, runtime, and ratings
- Run a conversation thread, poll for `requires_action`, execute the local TMDB function, and print the assistant reply
- Include sample film-analysis questions and saved example responses in the notebook

This repository does **not** yet compute evaluation metrics, comparison tables, or retrieval scores.

## Architecture

```
User Question
    ↓
Film AI Assistant
    ↓
┌──────────────┬──────────────┐
│ RAG / KB     │ TMDB API     │
│ film docs    │ movie data   │
└──────────────┴──────────────┘
        ↓
     LLM Answer
```

The assistant is instructed to query the vector store first (`file_search`), then fall back to TMDB when the knowledge base is insufficient or when up-to-date movie data is needed.

## Project Structure

```
film-rag-evaluation/
├── notebooks/Film_Assistant.ipynb   # original coursework assistant
├── data/rag/                        # film knowledge-base documents
├── docs/film-assistant-report.pdf   # original written report
├── results/                         # reserved for future evaluation outputs
├── .env.example                     # environment variable names only
├── .gitignore
├── requirements.txt
└── README.md
```

- `notebooks/` — runnable assistant notebook
- `data/rag/` — markdown sources used for RAG (Park Chan-wook, *Decision to Leave*, *The Handmaiden*, *Stoker*, film noir)
- `docs/` — coursework report PDF
- `results/` — empty placeholder for later evaluation artifacts

## Setup

1. Create and activate a local virtual environment from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy the example environment file and set real keys **outside Git** (export them, or keep a local `.env` that is gitignored):

```bash
cp .env.example .env
export OPENAI_API_KEY="your-openai-key"
export TMDB_API_KEY="your-tmdb-key"
```

3. Open `notebooks/Film_Assistant.ipynb` in Jupyter or VS Code/Cursor from the project root or the `notebooks/` folder. The notebook looks for `data/rag/` locally and only tries Google Drive if those files are missing.

Running the assistant cells calls OpenAI and TMDB and will incur API usage.

## Security

API credentials are loaded from environment variables (`OPENAI_API_KEY`, `TMDB_API_KEY`) and must not be hardcoded or committed. `.gitignore` excludes `.env`. `.env.example` contains placeholders only.

## Future Work

The following items are **planned**, not implemented:

- evaluation dataset
- LLM-only vs RAG vs RAG+TMDB comparison
- retrieval relevance
- groundedness / hallucination analysis
- latency comparison
- result visualization
