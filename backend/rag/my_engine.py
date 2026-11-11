"""
============================================================================
rag/my_engine.py — The real trilingual RAG engine (activates the AI layer)
============================================================================
WHY THIS EXISTS
---------------
This is the file that switches the project from "placeholder UI" to "real
trilingual RAG assistant". It subclasses `BaseRAGEngine` from `rag/engine.py`
and implements all 5 methods by orchestrating the modules we built:

    ingest  → extractors.extract  → chunker.chunk       → vectorstore.add_documents
    delete  → vectorstore.delete(filter={"doc_id": ...})
    search  → vectorstore.similarity_search_with_score  (+ optional language filter)
    answer  → graph.run  (or chain.run if USE_LANGGRAPH=0)
    health  → status report for the admin panel

ACTIVATION
----------
Set in `config/settings.py` (already done):
    RAG_ENGINE = "rag.my_engine.MyRAGEngine"

Or override per-run:
    RAG_ENGINE=rag.my_engine.MyRAGEngine python manage.py runserver

ZERO-API-KEY MODE
-----------------
With `LLM_PROVIDER=none` (default), `ingest`, `delete`, and `search` work
fully. `answer` returns retrieved chunks + a notice that no LLM is configured.
Set `LLM_PROVIDER=openai` (with `OPENAI_API_KEY`) or `LLM_PROVIDER=ollama`
to get real generated answers.

CONTRACT (from rag/engine.py::BaseRAGEngine)
--------------------------------------------
    health()  -> {"connected", "model", "embedding_model", "vector_store", "detail"}
    ingest(document) -> {"status", "pages", "language", "error"}
    delete(document) -> None
    search(query, user, document_ids, language, top_k) -> [{document_id, title, page, snippet, score}]
    answer(question, user, document_ids, history, language) -> {answer, language, sources}
"""
from __future__ import annotations
import os
from typing import Optional

from django.conf import settings

from .engine import BaseRAGEngine, detect_language
from .extractors import extract
from .chunker import chunk
from .vectorstore import get_store, count as vs_count


def _detect_language_better(text: str, fallback: str = "en") -> str:
    """
    Upgrade the regex-based `detect_language` with `langdetect` when available.
    Falls back to the regex heuristic if langdetect isn't installed.
    """
    if not text or len(text.strip()) < 5:
        return fallback
    try:
        from langdetect import DetectorFactory, detect
        DetectorFactory.seed = 0  # deterministic
        code = detect(text[:2000])
        if code.startswith("ar"):
            return "ar"
        if code.startswith("fr"):
            return "fr"
        if code.startswith("en"):
            return "en"
    except Exception:
        pass
    return detect_language(text) or fallback


class MyRAGEngine(BaseRAGEngine):
    """
    Real implementation. One instance is created per process via
    `rag.engine.get_engine()` and shared across requests.
    """

    # ---------- Health ----------
    def health(self) -> dict:
        """Reported in Admin → RAG Model → health badge."""
        try:
            chunks = vs_count()
        except Exception:
            chunks = -1
        llm_label = {
            "none": "none (retrieval only)",
            "openai": settings.OPENAI_MODEL,
            "groq": settings.GROQ_MODEL,
            "ollama": settings.OLLAMA_MODEL,
        }.get(settings.LLM_PROVIDER, settings.LLM_PROVIDER)

        connected = chunks >= 0
        return {
            "connected": connected,
            "model": llm_label,
            "embedding_model": settings.EMBEDDING_MODEL,
            "vector_store": f"chroma ({chunks} chunks)",
            "detail": (
                f"LLM_PROVIDER={settings.LLM_PROVIDER}, "
                f"USE_LANGGRAPH={settings.USE_LANGGRAPH}, "
                f"ENABLE_TOOL_CALLING={settings.ENABLE_TOOL_CALLING}"
            ),
        }

    # ---------- Ingest ----------
    def ingest(self, document) -> dict:
        """
        Called by `apps/documents/views.py:ingest()` after a file is uploaded.
        Pipeline: extract text → detect language → chunk → embed → store.
        """
        try:
            path = document.file.path
        except Exception as e:
            return {"status": "failed", "pages": 0, "language": "en", "error": f"No file path: {e}"}

        result = extract(path)
        if result.get("error"):
            return {"status": "failed", "pages": 0, "language": "en", "error": result["error"]}

        text = result["text"]
        if not text.strip():
            return {"status": "failed", "pages": result.get("pages", 0),
                    "language": "en", "error": "No text could be extracted (empty or scanned PDF?)"}

        # Detect language from extracted text (more accurate than detecting from the title)
        language = _detect_language_better(text, fallback=document.language or "en")

        # Chunk with metadata
        docs = chunk(
            text,
            doc_id=document.id,
            language=language,
            title=document.title,
            page_texts=result.get("page_texts"),
        )

        if not docs:
            return {"status": "failed", "pages": result.get("pages", 0),
                    "language": language, "error": "Chunking produced 0 chunks"}

        # Embed + store
        store = get_store()
        # Use document-provided IDs so re-ingest overwrites cleanly instead of duplicating.
        ids = [f"doc{document.id}_chunk{i}" for i in range(len(docs))]
        store.add_documents(docs, ids=ids)

        return {
            "status": "ready",
            "pages": result.get("pages", len(docs)),
            "language": language,
            "error": None,
        }

    # ---------- Delete ----------
    def delete(self, document) -> None:
        """Remove all chunks belonging to this document from the vector store."""
        try:
            store = get_store()
            # Chroma supports filter deletion by metadata
            store._collection.delete(where={"doc_id": document.id})
        except Exception:
            pass  # best-effort — the DB row is being deleted anyway

    # ---------- Search ----------
    def search(self, query, user, document_ids=None, language=None, top_k=5) -> list:
        """
        Semantic passage search. Filters:
        - `document_ids` : restrict to a set of docs (used by Chat when docs are attached)
        - `language`     : restrict to chunks in that language (the "search by language" feature)

        Returns scored snippets sorted by similarity descending.
        """
        store = get_store()
        where = {}
        if language:
            where["language"] = language
        if document_ids:
            where["doc_id"] = {"$in": list(document_ids)}

        kwargs = {"k": top_k}
        if where:
            kwargs["filter"] = where

        try:
            results = store.similarity_search_with_score(query, **kwargs)
        except Exception:
            return []

        out = []
        for doc, score in results:
            # Chroma returns L2 distance (lower = closer). Convert to 0..1 similarity.
            sim = max(0.0, min(1.0, 1.0 - float(score) / 2.0))
            out.append({
                "document_id": doc.metadata.get("doc_id"),
                "title": doc.metadata.get("title", ""),
                "page": doc.metadata.get("source_page", 1),
                "snippet": doc.page_content[:300],
                "score": round(sim, 4),
            })
        # Already sorted by Chroma (lowest distance first), but be explicit:
        out.sort(key=lambda r: r["score"], reverse=True)
        return out

    # ---------- Answer (chat with citations) ----------
    def answer(self, question, user, document_ids=None, history=None, language=None) -> dict:
        """
        Trilingual chat with citations.

        Pipeline:
        1. Detect question language (if not given)
        2. Retrieve top-k chunks (cross-lingual — no language filter on retrieval)
        3. Generate answer in the question's language
        4. Attach sources
        """
        lang = language or _detect_language_better(question)

        if settings.USE_LANGGRAPH:
            from .graph import run as graph_run
            return graph_run(
                question,
                language=lang,
                document_ids=document_ids,
                history=history,
            )
        else:
            from .chain import run as chain_run
            top_k = self._top_k()
            r = chain_run(question, language=lang, document_ids=document_ids,
                          history=history, top_k=top_k)
            return {"answer": r["answer"], "language": lang, "sources": r["sources"]}

    def _top_k(self) -> int:
        try:
            from apps.core.models import AppSetting
            obj = AppSetting.objects.filter(key="rag").first()
            if obj and obj.value:
                return int(obj.value.get("top_k", 5))
        except Exception:
            pass
        return 5
