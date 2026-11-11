# Lexia — Arabic · French · English Document Assistant

A trilingual RAG document assistant. React (Vite) frontend + Django REST backend + a full AI layer (LangChain + LangGraph + Chroma + sentence-transformers + MCP).

> **New:** The AI layer is now built in. The project runs out of the box with **zero API keys** — upload, chunk, embed, and search all work immediately. Set `LLM_PROVIDER=openai` or `ollama` to enable generated answers with citations. See [`AI_INTEGRATION_GUIDE.md`](./AI_INTEGRATION_GUIDE.md) for the full walkthrough of every added module.

---

## Quick start

### 1. Backend (Django, port 8000)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # admin/admin123 and demo/demo1234
python manage.py runserver
```

### 2. Frontend (React, port 5173)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 (the dev server proxies `/api` and `/media` to Django).
To point at another backend, set `VITE_API_URL=http://host:8000/api`.

### 3. (optional) Seed the sample docs
```bash
cd backend && python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> from apps.documents.models import Document
>>> from pathlib import Path
>>> u = get_user_model().objects.get(username="demo")
>>> for f in sorted(Path("sample_docs").glob("*.txt")):
...     d = Document.objects.create(owner=u, title=f.stem, file=f"sample_docs/{f.name}")
...     print(d.title)
# Then visit /documents, click each → "Reindex" to embed them.
# Or upload them via the UI at /upload.
```

### 4. (optional) Enable a real LLM

**Easiest way — put your key in `backend/.env`:**
```bash
cd backend
cp .env.example .env       # Windows: copy .env.example .env
# Edit .env in your text editor and fill in your key
```
```env
# In backend/.env:
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
```
Then just `python manage.py runserver` — the `.env` file is loaded automatically.

**Or set env vars per terminal session:**
```bash
# Option A — Groq (free cloud, recommended):
#   Get a free key at https://console.groq.com/keys (no credit card needed)
export LLM_PROVIDER=groq
export GROQ_API_KEY=gsk_...
python manage.py runserver

# Option B — OpenAI (paid, best quality):
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
python manage.py runserver

# Option C — Ollama (free, local, offline):
ollama pull qwen2.5:7b && ollama serve
export LLM_PROVIDER=ollama
python manage.py runserver
```

Compare providers head-to-head:
```bash
python bench/compare_providers.py --preset
```

---

## Project structure

```
docassist/
├── README.md                       ← you are here
├── AI_INTEGRATION_GUIDE.md         ← NEW: full walkthrough of every AI module
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt            ← UPDATED: full AI stack
│   │
│   ├── config/
│   │   └── settings.py             ← UPDATED: LLM_PROVIDER, EMBEDDING_MODEL, etc.
│   │
│   ├── rag/                        ← NEW: the AI layer (10 modules)
│   │   ├── README.md
│   │   ├── engine.py               (BaseRAGEngine contract — unchanged)
│   │   ├── extractors.py           (PDF / DOCX / TXT extraction)
│   │   ├── chunker.py              (LangChain RecursiveCharacterTextSplitter)
│   │   ├── embeddings.py           (sentence-transformers multilingual)
│   │   ├── vectorstore.py          (Chroma persistent vector DB)
│   │   ├── llm.py                  (OpenAI / Ollama / Stub provider factory)
│   │   ├── prompts.py              (trilingual RAG prompts)
│   │   ├── chain.py                (LangChain LCEL chain)
│   │   ├── graph.py                (LangGraph state machine + tool calling)
│   │   └── my_engine.py            (real BaseRAGEngine implementation)
│   │
│   ├── mcp_server/                 ← NEW: MCP server with 3 tools
│   │   ├── README.md
│   │   └── server.py               (ingest_document, search_by_language, answer_with_citations)
│   │
│   ├── bench/                      ← NEW: benchmarking harness
│   │   ├── README.md
│   │   ├── eval.jsonl              (15 trilingual queries)
│   │   ├── retrieval_eval.py       (Recall@k, MRR, nDCG)
│   │   ├── generation_eval.py      (RAGAS faithfulness/relevancy/precision)
│   │   └── run_all.sh
│   │
│   ├── finetune/                   ← NEW: embedding fine-tuning + comparison
│   │   ├── README.md
│   │   ├── triples.jsonl           (starter training triples)
│   │   ├── train.py                (sentence-transformers fine-tune)
│   │   └── build_triples.py        (auto-generate triples from indexed docs)
│   │
│   ├── sample_docs/                ← NEW: 15 trilingual demo documents
│   │   ├── en_01..en_05.txt
│   │   ├── fr_01..fr_05.txt
│   │   └── ar_01..ar_05.txt
│   │
│   └── apps/                       ← unchanged (accounts, documents, notifications, core)
│
└── frontend/                       ← unchanged (React + Vite)
    └── src/
        ├── App.jsx
        ├── api.js
        ├── i18n.js                 (EN / FR / AR dictionaries, RTL)
        ├── components/             (Layout, Aurora, Cover, charts, ui)
        └── pages/                  (Login, Home, Documents, Upload, Search, Chat,
                                    History, Notifications, Settings,
                                    AdminOverview, AdminAnalytics, AdminUsers,
                                    AdminDocs, AdminModel, AdminSystem,
                                    AdminAudit, AdminBroadcast)
```

---

## Interfaces
**User space:** login/register with animated cover · dashboard · documents · upload (drag & drop, progress) · semantic search · chat assistant with sources · history · notifications · settings.
**Admin space (separate console, no user pages):** overview (KPIs with week-over-week deltas, sparklines, activity chart, live feed, recent sign-ups, failed-document alert) · analytics (7/30/90 days, peak hours, weekday, file types, question languages, storage by user) · users · all documents · RAG model console · system health (uptime, disk, DB size, re-index failed) · audit log · announcements · settings.
**Extras:** English / French / Arabic UI with automatic RTL, dark / light theme, animated aurora background, responsive layout.

---

## AI layer

The RAG engine plugs into the existing `BaseRAGEngine` contract (5 methods: `health`, `ingest`, `delete`, `search`, `answer`). The real implementation lives in `backend/rag/my_engine.py` and is already activated by default.

**Pipeline:**
```
upload → extractors.extract(path)
       → chunker.chunk(text, doc_id, language, title)
       → vectorstore.add_documents(chunks)

search → vectorstore.similarity_search_with_score(query, filter={language, doc_id})
       → map to {document_id, title, page, snippet, score}

answer → graph.run(question, language, document_ids, history)
       → retrieve node (cross-lingual similarity_search)
       → generate node (trilingual prompt + LLM)
       → cite node (format sources list)
```

**Key features:**
- **Trilingual embeddings** — `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, supports ar+fr+en)
- **Cross-lingual retrieval** — Arabic query can retrieve French passages (the project's headline feature)
- **LangGraph state machine** — explicit `retrieve → generate → cite` nodes + optional `decide` node for tool calling
- **MCP server** — 3 tools (`ingest_document`, `search_by_language`, `answer_with_citations`) accessible from Claude Desktop / Cursor
- **Benchmarking** — Recall@k, MRR, nDCG (retrieval) + RAGAS faithfulness/relevancy (generation)
- **Fine-tuning** — fine-tune the embedding model and compare before/after with `bash bench/run_all.sh baseline|finetuned`

See [`AI_INTEGRATION_GUIDE.md`](./AI_INTEGRATION_GUIDE.md) for the full module-by-module explanation.

---

## Configuration

All AI settings are env vars (defaults shown):

| Variable | Default | What it does |
|---|---|---|
| `RAG_ENGINE` | `rag.my_engine.MyRAGEngine` | Engine class path |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Embedding model |
| `LLM_PROVIDER` | `none` | `none` / `groq` / `openai` / `ollama` |
| `GROQ_API_KEY` | `""` | Required when `LLM_PROVIDER=groq` (free at console.groq.com) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model (also: `qwen-2.5-32b`, `llama-3.1-8b-instant`) |
| `OPENAI_API_KEY` | `""` | Required when `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama model name |
| `CHROMA_DIR` | `backend/chroma_db` | Vector DB path |
| `USE_LANGGRAPH` | `1` | `1` = LangGraph state machine, `0` = plain LangChain chain |
| `ENABLE_TOOL_CALLING` | `1` | `1` = LLM decides whether to retrieve |

---

## Running the MCP server

```bash
cd backend
python -m mcp_server.server            # stdio transport
mcp dev backend/mcp_server/server.py   # open the MCP Inspector
```

Connect from Claude Desktop — see [`backend/mcp_server/README.md`](./backend/mcp_server/README.md).

---

## Running the benchmark

```bash
cd backend
bash bench/run_all.sh baseline         # baseline metrics

# After fine-tuning:
python finetune/train.py --epochs 3
EMBEDDING_MODEL=./models/docassist-ft bash bench/run_all.sh finetuned
```

Results land in `backend/bench/results_*_baseline.json` and `..._finetuned.json`.

---

## API summary
`POST /api/auth/login|register/` · `GET/PATCH /api/auth/me/` · `/api/documents/` · `/api/conversations/` (+ `POST :id/ask/`) · `/api/search/?q=` · `/api/notifications/` · `/api/dashboard/` · `/api/admin/{users,stats,analytics,feed,system,audit,rag/*,notifications/broadcast}/`
Auth uses DRF token (`Authorization: Token <key>`).

---

## Mapping to the project requirements

| Requirement | Where it lives |
|---|---|
| RAG + metadata + citations | `rag/my_engine.py` + `Document.language` + `Message.sources` + `Chat.jsx` citation UI |
| Tool Calling / MCP | `mcp_server/server.py` (3 tools) + `rag/graph.py` (`bind_tools`) |
| LangChain / LangGraph | `rag/chain.py` + `rag/graph.py` |
| Benchmarking | `bench/retrieval_eval.py` + `bench/generation_eval.py` (RAGAS) |
| Web interface | React + Django (existing) |
| Trilingual search across languages | `rag/prompts.py` + `rag/my_engine.py` (cross-lingual retrieval) |
| Fine-tuning before/after | `finetune/train.py` + `bench/run_all.sh baseline\|finetuned` |
| MCP tools named exactly | `ingest_document`, `search_by_language`, `answer_with_citations` in `mcp_server/server.py` |

---

## Production notes
Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, restrict `CORS_ALLOW_ALL_ORIGINS`, switch to PostgreSQL (and consider pgvector instead of Chroma), run indexing in a task queue (Celery) for large files, and serve `npm run build` output behind nginx.
