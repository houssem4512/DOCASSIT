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
1. ingest_document(file_path, language=None) -> dict
   Read a file from disk and add it to the vector index.

2. search_by_language(query, language, k=5) -> list
   Semantic search restricted to chunks in a specific language (ar/fr/en).
   This is the headline feature: ask in Arabic, retrieve French passages.

3. answer_with_citations(query, language=None) -> dict
   Full RAG: retrieve -> generate -> cite.

RUNNING
-------
    python -m mcp_server.server
    mcp dev backend/mcp_server/server.py
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
    pass  # already setup or running outside Django context

# MCP version compatibility: MCP 2.x renamed FastMCP to MCPServer.
# This try/except makes the file work with both MCP 1.x and 2.x.
try:
    from mcp.server.fastmcp import FastMCP  # MCP 1.x
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP  # MCP 2.x (FastMCP was renamed)

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
        {"status": "ready"|"failed", "pages": int, "language": str,
         "error": str|null, "chunks_indexed": int}
    """
    p = Path(file_path).expanduser().resolve()
    if not p.exists():
        return {"status": "failed", "pages": 0, "language": "en",
                "error": f"File not found: {p}"}

    result = extract(p)
    if result.get("error"):
        return {"status": "failed", "pages": 0, "language": "en",
                "error": result["error"]}

    text = result["text"]
    detected = language or _detect_language_better(text)

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
    return engine.search(query, user=None, language=language, top_k=k)


@mcp.tool()
def answer_with_citations(query: str, language: str | None = None) -> dict:
    """
    Answer a question using the indexed documents, with citations.

    Pipeline: detect question language (if not given) -> retrieve top-k chunks
    (cross-lingual) -> generate answer in the question's language -> attach sources.

    Args:
        query:    The question (any language).
        language: Force the answer language ("ar", "fr", "en").
                  If omitted, the language is auto-detected from the question.

    Returns:
        {
            "answer":   str,    # the generated answer (or a notice if LLM_PROVIDER=none)
            "language": str,    # the answer language
            "sources":  list    # the passages used to generate the answer
        }
    """
    engine = get_engine()
    return engine.answer(query, user=None, language=language)


@mcp.tool()
def list_indexed_languages() -> dict:
    """
    Bonus tool: report how many chunks are indexed per language.
    Useful for MCP clients to discover the corpus before querying.

    Chroma 1.x compatibility note:
      Older Chroma (<0.5) supported `collection.count(where=...)`.
      Newer Chroma (>=1.0) removed the `where` argument from `count()`.
      We use `collection.get(where=...)` and count the returned IDs instead —
      this works on both old and new Chroma versions.
    """
    from rag.vectorstore import get_store
    try:
        store = get_store()
        col = store._collection
        ar = len(col.get(where={"language": "ar"})["ids"])
        fr = len(col.get(where={"language": "fr"})["ids"])
        en = len(col.get(where={"language": "en"})["ids"])
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