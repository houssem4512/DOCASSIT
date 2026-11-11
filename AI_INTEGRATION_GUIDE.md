# AI Integration Guide — DocAssist

This document explains **every file added to the original project** to build the AI layer. The original Django + React scaffolding is unchanged except for two small edits (`settings.py` defaults + one `views.py` bug fix). Everything else lives in new modules under `backend/`.

> **TL;DR** — the project now runs out of the box with **zero API keys**. Upload, search, and chunk-level retrieval work immediately. Set `LLM_PROVIDER=openai` (or `ollama`) to enable generated answers with citations.

---

## Table of contents

1. [Architecture overview](#1-architecture-overview)
2. [What was added vs. what was kept](#2-what-was-added-vs-what-was-kept)
3. [Module-by-module walkthrough](#3-module-by-module-walkthrough)
    - 3.1 [`rag/extractors.py`](#31-ragextractorspy)
    - 3.2 [`rag/chunker.py`](#32-ragchunkerpy)
    - 3.3 [`rag/embeddings.py`](#33-ragembeddingspy)
    - 3.4 [`rag/vectorstore.py`](#34-ragvectorstorepy)
    - 3.5 [`rag/llm.py`](#35-ragllmpy)
    - 3.6 [`rag/prompts.py`](#36-ragpromptspy)
    - 3.7 [`rag/chain.py`](#37-ragchainpy)
    - 3.8 [`rag/graph.py`](#38-raggraphpy)
    - 3.9 [`rag/my_engine.py`](#39-ragmy_enginepy)
    - 3.10 [`mcp_server/server.py`](#310-mcp_serverserverpy)
    - 3.11 [`bench/`](#311-bench)
    - 3.12 [`finetune/`](#312-finetune)
    - 3.13 [`sample_docs/`](#313-sample_docs)
4. [Configuration reference](#4-configuration-reference)
5. [Run modes](#5-run-modes)
6. [Mapping to the grading requirements](#6-mapping-to-the-grading-requirements)
7. [Quickstart commands](#7-quickstart-commands)

---

## 1. Architecture overview

```
                ┌─────────────────────────────────────────────┐
                │              Django REST API                │
                │   (apps/documents/views.py, apps/core/...)  │
                └────────────────┬────────────────────────────┘
                                 │ calls get_engine()
                                 ▼
                ┌─────────────────────────────────────────────┐
                │         rag/my_engine.py::MyRAGEngine       │  ← single integration point
                │   implements BaseRAGEngine (5 methods)      │
                └───┬───────────┬──────────────┬──────────────┘
                    │           │              │
                    ▼           ▼              ▼
            rag/extractors  rag/graph    rag/vectorstore
              (PDF/DOCX)   (LangGraph)     (Chroma)
                    │           │              │
                    ▼           ▼              ▼
            rag/chunker   rag/chain       rag/embeddings
              (LangChain   (LangChain      (sentence-
               splitter)    RAG chain)     transformers)
                                  │
                                  ▼
                            rag/llm
                       (OpenAI / Ollama / Stub)

  ┌─────────────────────┐         ┌────────────────────┐
  │  mcp_server/        │         │  bench/            │
  │  exposes 3 tools    │────────►│  retrieval_eval    │
  │  via FastMCP        │ shares  │  generation_eval   │
  │  (stdio transport)  │ engine  │  (RAGAS)           │
  └─────────────────────┘         └────────────────────┘

                       ┌────────────────────┐
                       │  finetune/         │
                       │  train.py          │  → produces ./models/docassist-ft
                       │  triples.jsonl     │     (EMBEDDING_MODEL=path activates it)
                       └────────────────────┘
```

---

## 2. What was added vs. what was kept

### Kept unchanged
- `backend/apps/` — all 4 apps (accounts, documents, notifications, core)
- `backend/config/urls.py`, `wsgi.py`
- `backend/rag/engine.py` — the `BaseRAGEngine` contract + `PlaceholderEngine` (kept as a fallback)
- `frontend/` — entire React app unchanged

### Modified (small edits)
| File | Change | Why |
|---|---|---|
| `backend/config/settings.py` | Added `EMBEDDING_MODEL`, `LLM_PROVIDER`, `OPENAI_*`, `OLLAMA_*`, `CHROMA_DIR`, `USE_LANGGRAPH`, `ENABLE_TOOL_CALLING` env vars. Changed `RAG_ENGINE` default to `rag.my_engine.MyRAGEngine`. | Activate the real engine + make the AI stack configurable without code changes |
| `backend/requirements.txt` | Added the full AI stack (LangChain, LangGraph, Chroma, sentence-transformers, MCP, RAGAS, torch, pypdf, etc.) | One `pip install` sets up everything |
| `backend/apps/core/views.py` | One line in `RagTest.post` — forward the `language` parameter | Without this, the admin test console answers in the wrong language |
| `README.md` | Added an "AI layer" section + quickstart | Reflect the new reality |

### Added (new files)
```
backend/
├── rag/
│   ├── __init__.py
│   ├── extractors.py            ← PDF/DOCX/TXT text extraction
│   ├── chunker.py               ← LangChain RecursiveCharacterTextSplitter + metadata
│   ├── embeddings.py            ← sentence-transformers multilingual wrapper
│   ├── vectorstore.py           ← Chroma persistent vector store
│   ├── llm.py                   ← OpenAI / Ollama / Stub provider factory
│   ├── prompts.py               ← trilingual RAG prompts (ar/fr/en)
│   ├── chain.py                 ← LangChain LCEL RAG chain
│   ├── graph.py                 ← LangGraph state machine + tool calling
│   └── my_engine.py             ← real BaseRAGEngine implementation
├── mcp_server/
│   ├── __init__.py
│   └── server.py                ← FastMCP server exposing 3 tools
├── bench/
│   ├── __init__.py
│   ├── eval.jsonl               ← 15 trilingual benchmark queries
│   ├── retrieval_eval.py        ← Recall@k, MRR, nDCG
│   ├── generation_eval.py       ← RAGAS faithfulness/relevancy/precision
│   └── run_all.sh               ← one-shot benchmark runner
├── finetune/
│   ├── __init__.py
│   ├── triples.jsonl            ← 18 starter (query, positive, negative) triples
│   ├── train.py                 ← sentence-transformers fine-tune script
│   └── build_triples.py         ← auto-generate triples from indexed chunks
└── sample_docs/                 ← 15 trilingual demo documents (5 per language)
    ├── en_01..en_05.txt
    ├── fr_01..fr_05.txt
    └── ar_01..ar_05.txt

AI_INTEGRATION_GUIDE.md          ← this file
```

---

## 3. Module-by-module walkthrough

### 3.1 `rag/extractors.py`

**Purpose:** turn an uploaded file into plain text + page count.

**Why:** embedding models can't read PDFs directly. We need plain text. We also keep page numbers so citations can say "see p.3".

**Public API:**
```python
extract(path) -> {"text": str, "pages": int, "page_texts": [{"page": int, "text": str}]}
```

**Formats:**
- `.pdf`  → `pypdf.PdfReader` (page-by-page)
- `.docx` → `python-docx` (pseudo-paginated at 500 words/page)
- `.txt`, `.md` → direct UTF-8 read
- `.png`, `.jpg` → returns error (OCR not configured)

**Never raises** — returns an `error` key instead, so `my_engine.py` can mark the document as `failed` cleanly.

---

### 3.2 `rag/chunker.py`

**Purpose:** split extracted text into embeddable chunks, each carrying metadata.

**Why:** embedding a 20-page PDF as one vector gives poor retrieval. We split into ~800-char overlapping chunks so each chunk is a tight semantic unit.

**Public API:**
```python
chunk(text, *, doc_id, language, title, page_texts=None) -> List[langchain_core.documents.Document]
```

**Metadata on every chunk** (becomes Chroma filter fields):
- `doc_id` — Django `Document.id`; used by `delete()` and `search(document_ids=...)`
- `language` — `"ar"`/`"fr"`/`"en"`; powers `search_by_language`
- `title` — surfaced in the citation UI
- `source_page` — for "see p.X" citations
- `chunk_index` — ordering within the document

**Config source:** `chunk_size` and `chunk_overlap` are read from `AppSetting.objects.get(key="rag").value` — editable live from the admin panel.

**Separators** (in order): `"\n\n"`, `"\n"`, `". "`, `"؛ "` (Arabic semicolon), `"، "` (Arabic comma), `" "`, `""`. Arabic-aware.

---

### 3.3 `rag/embeddings.py`

**Purpose:** wrap `sentence-transformers` in the LangChain `Embeddings` interface.

**Why:** LangChain requires an `Embeddings` object with `embed_query(text)` and `embed_documents(texts)`. We also need lazy loading — the model is ~120 MB and we don't want to block Django startup.

**Default model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- 384-dimensional vectors
- Supports 50+ languages including Arabic, French, English
- ~120 MB on disk
- Fast on CPU

**This is the BASELINE for the fine-tuning comparison.** After fine-tuning, set `EMBEDDING_MODEL=./models/docassist-ft` and the same wrapper loads the fine-tuned model.

**Singleton via `lru_cache`** — the model is loaded once per process and shared across all requests.

---

### 3.4 `rag/vectorstore.py`

**Purpose:** persistent Chroma vector database.

**Why Chroma:** zero setup (file-based, no separate server), integrates natively with LangChain via `langchain-chroma`, good enough for the project scale (~thousands of chunks).

**Location:** `settings.CHROMA_DIR` → `backend/chroma_db/` (add to `.gitignore`).

**Collection:** `"docs"`, schema:
```
id:          auto-generated
embedding:   384-dim float vector
document:    chunk text (searchable)
metadata:    {doc_id, language, title, source_page, chunk_index}
```

**Public API:**
- `get_store() -> Chroma` — the LangChain vector store
- `reset_store()` — drop the collection (used by benchmark scripts)
- `count() -> int` — chunk count (surfaced in the admin health endpoint)

---

### 3.5 `rag/llm.py`

**Purpose:** pluggable LLM provider so the project runs with zero API keys AND upgrades cleanly when one is added.

**Three modes** (selected by `LLM_PROVIDER` env var):

| Provider | Class | When to use |
|---|---|---|
| `none` (default) | `StubLLM` | First run. Retrieval works; chat returns retrieved context + a notice |
| `openai` | `langchain_openai.ChatOpenAI` | Production demo. Needs `OPENAI_API_KEY`. Default model `gpt-4o-mini` |
| `ollama` | `langchain_ollama.ChatOllama` | Free, offline. Install Ollama + `ollama pull qwen2.5:7b` |

**Singleton** — connection pools are cached per process.

**`StubLLM` is the killer feature for grading:** the project runs end-to-end without an API key. Upload → chunk → embed → search → retrieve all work; only the generation step is replaced with a notice. This means you can demo retrieval + citations immediately, then add an LLM when ready.

---

### 3.6 `rag/prompts.py`

**Purpose:** trilingual RAG prompt templates.

**Why:** the headline feature is "search in one language, ask in another". The prompt must instruct the LLM to answer in the user's language even when retrieved chunks are in a different language.

**Three message slots:**
1. `system` — rules in `language` (answer in this language, use only context, cite as `[title, p.X]`, say if insufficient)
2. `human` — `CONTEXT:\n{context}\n\nQUESTION:\n{question}`
3. (history messages prepended by `graph.py` for multi-turn chat)

**`format_context(chunks)`** — turns retrieved chunks into a numbered block:
```
[1] (title, p.3) <snippet>
[2] (title, p.5) <snippet>
```
The numbers let the LLM cite cleanly: "according to [2]...".

---

### 3.7 `rag/chain.py`

**Purpose:** the LangChain baseline (the "framework" requirement, plain version).

**Why:** a single LCEL chain `retriever | prompt | llm | parser` — simplest possible RAG. Used when `USE_LANGGRAPH=0`.

**Cross-lingual by design:** retrieval is NOT filtered by the question's language. An Arabic query can retrieve French passages — that's the point of multilingual embeddings.

**Public API:**
```python
run(question, *, language, document_ids, history, top_k) -> {"answer": str, "sources": list}
```

---

### 3.8 `rag/graph.py`

**Purpose:** the LangGraph state machine (the "framework" requirement, upgraded version).

**Why:** LangGraph makes the flow explicit (named nodes + edges), debuggable, and visualisable. Also enables tool calling — the LLM decides whether to retrieve.

**State machine (when `ENABLE_TOOL_CALLING=1` and `LLM_PROVIDER != "none"`):**
```
START → decide ─┬─ tool_call → retrieve → generate → cite → END
                 └─ no_tool  ──────────────────────────→ generate → cite → END
```

**State machine (default, when `LLM_PROVIDER=none`):**
```
START → retrieve → generate → cite → END
```

**Nodes:**
- `decide` — LLM with `bind_tools([search_by_language])` decides if retrieval is needed
- `retrieve` — vectorstore similarity_search (cross-lingual)
- `generate` — trilingual prompt + LLM call (with conversation history prepended)
- `cite` — format sources list for the API response

**Tool exposed:** `search_by_language(query, language, k=5)` — **the same tool the MCP server exposes**. This is intentional: the LLM tool and the MCP tool share implementation, so behavior is identical whether called by an LLM or by an external MCP client.

**`mermaid_diagram()`** — returns a Mermaid graph string for the report.

---

### 3.9 `rag/my_engine.py`

**Purpose:** the single file that activates the AI layer. Subclasses `BaseRAGEngine` and implements all 5 methods by orchestrating the modules above.

**Activation:**
```python
# config/settings.py
RAG_ENGINE = "rag.my_engine.MyRAGEngine"
```

**The 5 methods:**
| Method | Implementation |
|---|---|
| `health()` | returns `{connected, model, embedding_model, vector_store, detail}` for the admin badge |
| `ingest(document)` | `extract → detect_language → chunk → vectorstore.add_documents` |
| `delete(document)` | `vectorstore._collection.delete(where={"doc_id": ...})` |
| `search(query, user, document_ids, language, top_k)` | `similarity_search_with_score` + L2→similarity conversion |
| `answer(question, user, document_ids, history, language)` | dispatches to `graph.run` (default) or `chain.run` |

**Language detection upgrade:** `_detect_language_better()` uses `langdetect` when available, falls back to the regex heuristic in `engine.py`.

---

### 3.10 `mcp_server/server.py`

**Purpose:** expose the RAG engine as 3 MCP tools so external LLM clients (Claude Desktop, Cursor) can use it.

**The 3 tools (matches the project brief exactly):**
1. `ingest_document(file_path, language=None)` → `{status, pages, language, error, chunks_indexed}`
2. `search_by_language(query, language, k=5)` → list of `{document_id, title, page, snippet, score}`
3. `answer_with_citations(query, language=None)` → `{answer, language, sources}`

**Plus a bonus tool:** `list_indexed_languages()` → `{ar, fr, en, total}` chunk counts.

**Plus a resource:** `docassist://health` — exposes the engine health to MCP clients.

**Transport:** stdio (standard for local MCP servers).

**Run:**
```bash
python -m mcp_server.server           # run the server
mcp dev backend/mcp_server/server.py  # open the MCP Inspector
```

**Connect from Claude Desktop** (in `claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "docassist": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/docassist/backend"
    }
  }
}
```

**Why the tools delegate to `get_engine()`:** the MCP server and the Django API share a single source of truth for ingest/search/answer logic. Updates to `my_engine.py` automatically benefit both interfaces.

---

### 3.11 `bench/`

**Purpose:** benchmark retrieval and generation quality (the "Benchmarking" requirement).

**Files:**
- `eval.jsonl` — 15 trilingual queries (5 per language) with `expected_doc_ids`, `expected_keywords`, `reference_answer`
- `retrieval_eval.py` — Recall@k, MRR, nDCG@k, per language + overall
- `generation_eval.py` — generates answers, then scores them with RAGAS (`faithfulness`, `answer_relevancy`, `context_precision`)
- `run_all.sh` — convenience runner: `bash bench/run_all.sh baseline` or `bash bench/run_all.sh finetuned`

**Usage:**
```bash
cd backend
bash bench/run_all.sh baseline          # baseline numbers
# ... after fine-tuning ...
EMBEDDING_MODEL=./models/docassist-ft bash bench/run_all.sh finetuned
```

**Outputs:**
- `bench/results_retrieval_baseline.json`
- `bench/answers_baseline.json`
- `bench/results_generation_baseline.json`
- (and `_finetuned` variants)

**Compare:** the JSON files have the same shape — diff them or load into a Pandas DataFrame to produce the before/after chart.

---

### 3.12 `finetune/`

**Purpose:** fine-tune the multilingual embedding model and compare before/after (the "fine-tuning" requirement).

**Files:**
- `triples.jsonl` — 18 starter (query, positive, negative) triples across ar/fr/en
- `train.py` — fine-tunes `paraphrase-multilingual-MiniLM-L12-v2` with `MultipleNegativesRankingLoss`, saves to `./models/docassist-ft`
- `build_triples.py` — auto-generates triples from indexed chunks (for scaling up)

**Usage:**
```bash
cd backend
# (optional) generate more triples from your indexed docs:
python finetune/build_triples.py --per-language 50 --out finetune/triples_auto.jsonl

# fine-tune (3 epochs, ~15 min on a T4 GPU):
python finetune/train.py --epochs 3 --batch-size 16

# re-benchmark with the fine-tuned model:
EMBEDDING_MODEL=./models/docassist-ft bash bench/run_all.sh finetuned
```

**Loss function:** `MultipleNegativesRankingLoss` — takes (query, positive) pairs, treats all other positives in the batch as negatives. Standard for retrieval, no need to mine hard negatives manually.

**The deliverable:** `bench/results_*_baseline.json` vs `bench/results_*_finetuned.json` — a clear before/after comparison.

---

### 3.13 `sample_docs/`

15 short public-domain-style documents (5 topics × 3 languages):

| Topic | Files |
|---|---|
| History of the Internet | `en_01`, `fr_01`, `ar_01` |
| Climate change | `en_02`, `fr_02`, `ar_02` |
| Renewable energy | `en_03`, `fr_03`, `ar_03` |
| Artificial intelligence | `en_04`, `fr_04`, `ar_04` |
| Education | `en_05`, `fr_05`, `ar_05` |

Each is ~250 words. Same content across languages so cross-lingual retrieval is meaningful (an Arabic query about climate change should retrieve the French climate doc).

**Seed them into the index on first run:**
```bash
cd backend
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> from apps.documents.models import Document
>>> from rag.engine import get_engine
>>> from pathlib import Path
>>> u = get_user_model().objects.get(username="demo")
>>> for f in sorted(Path("sample_docs").glob("*.txt")):
...     d = Document.objects.create(owner=u, title=f.stem, file=f"sample_docs/{f.name}")
...     print(d.title, get_engine().ingest(d))
```

Or upload them via the UI at http://localhost:5173/upload.

---

## 4. Configuration reference

All settings are env vars read in `config/settings.py`. Defaults in parentheses.

| Variable | Default | What it does |
|---|---|---|
| `RAG_ENGINE` | `rag.my_engine.MyRAGEngine` | Dotted path to the engine class. Set to `rag.engine.PlaceholderEngine` for the demo stub |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | HuggingFace model name or local path (after fine-tuning) |
| `LLM_PROVIDER` | `none` | `none` / `groq` / `openai` / `ollama` |
| `GROQ_API_KEY` | `""` | Required when `LLM_PROVIDER=groq` — free at https://console.groq.com/keys |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model (also: `qwen-2.5-32b`, `llama-3.1-8b-instant`) |
| `OPENAI_API_KEY` | `""` | Required when `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | Any OpenAI chat model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Any model pulled via `ollama pull` |
| `CHROMA_DIR` | `backend/chroma_db` | Where the vector DB lives on disk |
| `USE_LANGGRAPH` | `1` | `1` = use the LangGraph state machine; `0` = use the plain LangChain chain |
| `ENABLE_TOOL_CALLING` | `1` | `1` = let the LLM decide whether to retrieve (requires `LLM_PROVIDER != none`) |

---

## 5. Run modes

### Mode 1 — Zero API key (default, retrieval-only)
```bash
cd backend && pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```
- ✅ Upload, chunk, embed, search — all work
- ✅ Chat returns retrieved chunks with a notice
- ❌ No real answers (LLM not configured)

### Mode 2 — With Groq (free cloud, recommended for development)
```bash
# Get a free key at https://console.groq.com/keys (no credit card needed)
export LLM_PROVIDER=groq
export GROQ_API_KEY=gsk_...
python manage.py runserver
```
- ✅ Everything works including generated answers with citations
- ✅ Free tier: 30 req/min, 14,400 req/day
- ✅ Ultra-fast inference (Groq LPU hardware)

### Mode 3 — With OpenAI (paid)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
python manage.py runserver
```
- ✅ Best answer quality

### Mode 4 — With Ollama (free, local, offline)
```bash
ollama pull qwen2.5:7b
ollama serve  # in another terminal
export LLM_PROVIDER=ollama
python manage.py runserver
```

---

## 6. Mapping to the grading requirements

| Requirement | Where it lives in the code |
|---|---|
| **Gestion documentaire: RAG, métadonnées, citations** | `rag/my_engine.py` (ingest/search/answer) + `Document.language` + `Message.sources` (existing) + citation UI in `Chat.jsx` (existing) |
| **Tool Calling / MCP** | `mcp_server/server.py` (3 MCP tools via FastMCP) + `rag/graph.py` (`search_by_language` bound to the LLM via `bind_tools`) |
| **Frameworks: LangChain et/ou LangGraph** | `rag/chain.py` (LangChain LCEL) + `rag/graph.py` (LangGraph state machine) |
| **Benchmarking: retrieval + generation** | `bench/retrieval_eval.py` (Recall@k, MRR, nDCG) + `bench/generation_eval.py` (RAGAS) |
| **Interface Web** | React + Django (unchanged) |
| **Trilingual ar/fr/en + cross-lingual search** | `rag/prompts.py` (trilingual system prompts) + `rag/my_engine.py` (cross-lingual retrieval) + `Search.jsx` language filter (existing) |
| **Fine-tuning: compare embedding before/after** | `finetune/train.py` + `bench/run_all.sh baseline|finetuned` + result JSON files |
| **MCP tools named exactly** `ingest_document`, `search_by_language`, `answer_with_citations` | `mcp_server/server.py` — exact names |

---

## 7. Quickstart commands

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# 2. Frontend (another terminal)
cd frontend
npm install
npm run dev
# open http://localhost:5173 — login admin/admin123 or demo/demo1234

# 3. (optional) seed the sample docs via the UI:
#    Upload page → drag sample_docs/*.txt → Start Upload

# 4. (optional) enable a real LLM:
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
# restart runserver

# 5. (optional) run the benchmark:
bash bench/run_all.sh baseline

# 6. (optional) fine-tune + re-benchmark:
python finetune/train.py --epochs 3
EMBEDDING_MODEL=./models/docassist-ft bash bench/run_all.sh finetuned

# 7. (optional) start the MCP server:
python -m mcp_server.server        # stdio transport
# or inspect it:
mcp dev backend/mcp_server/server.py
```
