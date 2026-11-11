"""
============================================================================
rag/chunker.py — Split extracted text into embeddable chunks with metadata
============================================================================
WHY THIS EXISTS
---------------
Embedding models have a token limit (the default MiniLM accepts ~256 tokens).
If we embed an entire 20-page PDF as one vector, retrieval is poor because a
single vector can't represent 20 pages of mixed topics. We split documents
into small overlapping chunks so each chunk is a tight semantic unit — when
the user asks a question, we retrieve the *chunks* most similar to the query,
not whole documents.

METADATA ON EVERY CHUNK
-----------------------
Every chunk carries metadata that becomes Chroma filter fields:
    {
        "doc_id":      int,    # Document.id in Django — used by `delete()` and `search(document_ids=...)`
        "language":    "ar"|"fr"|"en",
        "title":       str,    # used in the citation UI
        "source_page": int,    # the page this chunk came from (for "see p.3" citations)
        "chunk_index": int,    # ordering within the document
    }
This metadata is what makes the "search by language" requirement work:
Chroma supports `where={"language": "ar"}` filters.

CONFIG SOURCE
-------------
`chunk_size` and `chunk_overlap` are read from `AppSetting.objects.get(key="rag").value`
so they're editable at runtime from the admin panel. Fall back to settings.py defaults.
"""
from __future__ import annotations
from typing import Dict, List

from django.conf import settings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def _get_config() -> Dict:
    """Read live chunk_size / chunk_overlap from the AppSetting table.
    Falls back to defaults if the table is empty (e.g. before migrations)."""
    try:
        from apps.core.models import AppSetting
        obj = AppSetting.objects.filter(key="rag").first()
        if obj and obj.value:
            return obj.value
    except Exception:
        pass
    return {"chunk_size": 800, "chunk_overlap": 120}


def chunk(
    text: str,
    *,
    doc_id: int,
    language: str,
    title: str,
    page_texts: List[Dict] | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[Document]:
    """
    Split `text` into LangChain `Document` objects (each = page_content + metadata).

    Args:
        text:           Full extracted text (used when page_texts is None)
        doc_id:         Django Document.id
        language:       "ar" | "fr" | "en"
        title:          Document title (carried through to citations)
        page_texts:     Optional list of [{"page": int, "text": str}] from extractors.py.
                        When provided, chunks are tagged with the page they came from.
        chunk_size:     Override config (otherwise read from AppSetting)
        chunk_overlap:  Override config

    Returns:
        List[langchain_core.documents.Document] ready for `vectorstore.add_documents()`.
    """
    cfg = _get_config()
    size = chunk_size or cfg.get("chunk_size", 800)
    overlap = chunk_overlap or cfg.get("chunk_overlap", 120)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        # Separators ordered by preference. The splitter tries each in turn:
        # - "\n\n" = paragraph break (best semantic boundary)
        # - "\n"   = line break
        # - ". "   = sentence end
        # - " "    = word boundary (last resort)
        # Arabic and French both use these separators.
        separators=["\n\n", "\n", ". ", "؛ ", "، ", " ", ""],
        length_function=len,
    )

    docs: List[Document] = []
    if page_texts:
        # Page-aware chunking: each chunk knows which page it came from.
        for pt in page_texts:
            page = pt["page"]
            page_text = pt["text"]
            if not page_text.strip():
                continue
            pieces = splitter.split_text(page_text)
            for idx, piece in enumerate(pieces):
                docs.append(Document(
                    page_content=piece,
                    metadata={
                        "doc_id": doc_id,
                        "language": language,
                        "title": title,
                        "source_page": page,
                        "chunk_index": len(docs),  # global index across the document
                    },
                ))
    else:
        # Flat chunking (no page info) — used as a fallback.
        pieces = splitter.split_text(text)
        for idx, piece in enumerate(pieces):
            docs.append(Document(
                page_content=piece,
                metadata={
                    "doc_id": doc_id,
                    "language": language,
                    "title": title,
                    "source_page": 1,
                    "chunk_index": idx,
                },
            ))
    return docs
