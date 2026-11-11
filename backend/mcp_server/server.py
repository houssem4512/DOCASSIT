"""
============================================================================
mcp_server/server.py — Model Context Protocol server exposing 3 tools
============================================================================
WHY THIS EXISTS
---------------
Requirement: "Tool Calling / MCP."

The Model Context Protocol (MCP) is Anthropic's open standard for exposing
tools, prompts, and resources to LLM clients (Claude Desktop, Cursor, etc.).
This module exposes the DocAssist RAG engine as 3 MCP tools so any external
MCP-compatible client can ingest documents, search by language, and ask
questions with citations — without going through the Django HTTP API.

THE 3 TOOLS (matches the project brief exactly)
-----------------------------------------------
1. ingest_document(file_path, language=None) → {status, pages, language, error}
   Read a file from disk and add it to the vector index. `language` is
   auto-detected if omitted.

2. search_by_language(query, language, k=5) → list of passages
   Semantic search restricted to chunks in a specific language (ar/fr/en).
   This is the headline feature: ask in Arabic, retrieve French passages.

3. answer_with_citations(query, language=None) → {answer, language, sources}
   Full RAG: retrieve → generate → cite. Returns the answer + the source
   passages used.

RUNNING
-------
Stdio transport (standard for local MCP servers):
    python -m mcp_server.server

Inspect / test interactively with the official MCP Inspector:
    mcp dev backend/mcp_server/server.py

Connect from Claude Desktop (add to `claude_desktop_config.json`):
    {
      "mcpServers": {
        "docassist": {
          "command": "python",
          "args": ["-m", "mcp_server.server"],
          "cwd": "/path/to/docassist/backend"
        }
      }
    }

WHY THE TOOLS DELEGATE TO `get_engine()`
----------------------------------------
The MCP server and the Django API share the same engine — there's a single
source of truth for ingest/search/answer logic. Updates to `rag/my_engine.py`
automatically benefit both interfaces.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

# Ensure the backend/ directory is on sys.path when run as `python -m mcp_server.server`
# or via `mcp dev server.py` (which spawns a fresh Python process).
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Bootstrap Django (so we can use ORM + settings inside tools)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402
try:
    django.setup()
except Exception:
    pass  # already setup or running outside Django context — tool calls will fail loudly

from mcp.server.fastmcp import FastMCP  # noqa: E402

from rag.engine import get_engine  # noqa: E402
from rag.extractors import extract  # noqa: E402
from rag.my_engine import _detect_language_better  # noqa: E402

mcp = FastMCP("docassist")


@mcp.tool()
def ingest_document(file_path: str, language: str | None = None) -> dict:
    """
    Ingest a document file (PDF/DOCX/TXT/MD) into the DocAssist vector index.

    Args:
        file_path: Absolute or relative path to the file on disk.
        language:  Optional language override ("ar", "fr", "en").
                   If omitted, the language is auto-detected from the text.

    Returns:
        {"status": "ready"|"failed", "pages": int, "language": str, "error": str|null}
    """
    p = Path(file_path).expanduser().resolve()
    if not p.exists():
        return {"status": "failed", "pages": 0, "language": "en", "error": f"File not found: {p}"}

    result = extract(p)
    if result.get("error"):
        return {"status": "failed", "pages": 0, "language": "en", "error": result["error"]}

    text = result["text"]
    detected = language or _detect_language_better(text)

    # Use the engine's chunker + embeddings + vectorstore directly.
    # We don't have a Django Document row here (file is outside the upload flow),
    # so we use doc_id=0 and a synthetic title from the filename.
    from rag.chunker import chunk as chunk_fn
    from rag.vectorstore import get_store

    docs = chunk_fn(
        text,
        doc_id=0,  # MCP ingest bypasses the Django Document model
        language=detected,
        title=p.stem,
        page_texts=result.get("page_texts"),
    )
    if not docs:
        return {"status": "failed", "pages": result.get("pages", 0),
                "language": detected, "error": "Chunking produced 0 chunks"}

    store = get_store()
    ids = [f"mcp_{p.stem}_{i}" for i in range(len(docs))]
    store.add_documents(docs, ids=ids)

    return {
        "status": "ready",
        "pages": result.get("pages", len(docs)),
        "language": detected,
        "error": None,
        "chunks_indexed": len(docs),
    }


@mcp.tool()
def search_by_language(query: str, language: str, k: int = 5) -> list:
    """
    Semantic search restricted to documents in a specific language.

    Use this when you want to search Arabic documents with an English query,
    or French documents with an Arabic query — the matching is semantic
    (vector-based), not keyword-based.

    Args:
        query:    The search query (any language).
        language: Filter to chunks in this language — "ar", "fr", or "en".
        k:        Number of top results to return (default 5, max 20).

    Returns:
        List of {"document_id", "title", "page", "snippet", "score"} objects,
        sorted by similarity descending. `score` is in [0, 1].
    """
    if language not in ("ar", "fr", "en"):
        return [{"error": f"language must be ar, fr, or en — got '{language}'"}]
    k = max(1, min(int(k), 20))
    engine = get_engine()
    # user=None is fine: search doesn't actually use the user when language filter is set
    return engine.search(query, user=None, language=language, top_k=k)


@mcp.tool()
def answer_with_citations(query: str, language: str | None = None) -> dict:
    """
    Answer a question using the indexed documents, with citations.

    Pipeline: detect question language (if not given) → retrieve top-k chunks
    (cross-lingual) → generate answer in the question's language → attach sources.

    Args:
        query:    The question (any language).
        language: Force the answer language ("ar", "fr", "en").
                  If omitted, the language is auto-detected from the question.

    Returns:
        {
            "answer":   str,         # the generated answer (or a notice if LLM_PROVIDER=none)
            "language": str,         # the answer language
            "sources":  [            # the passages used to generate the answer
                {"document_id", "title", "page", "snippet", "score"}
            ]
        }
    """
    engine = get_engine()
    return engine.answer(query, user=None, language=language)


@mcp.tool()
def list_indexed_languages() -> dict:
    """
    Bonus tool: report how many chunks are indexed per language.
    Useful for MCP clients to discover the corpus before querying.
    """
    from rag.vectorstore import get_store
    try:
        store = get_store()
        col = store._collection
        ar = col.count(where={"language": "ar"})
        fr = col.count(where={"language": "fr"})
        en = col.count(where={"language": "en"})
        return {"ar": ar, "fr": fr, "en": en, "total": ar + fr + en}
    except Exception as e:
        return {"error": str(e)}


@mcp.resource("docassist://health")
def health_resource() -> str:
    """MCP resource exposing the engine's health status (read by MCP clients)."""
    h = get_engine().health()
    return "\n".join(f"{k}: {v}" for k, v in h.items())


def main():
    """Entry point — runs the MCP server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
