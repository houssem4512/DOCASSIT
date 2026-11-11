"""
============================================================================
rag/extractors.py — Multilingual text extraction from uploaded documents
============================================================================
WHY THIS EXISTS
---------------
The first step of any RAG pipeline is turning a binary file (PDF, DOCX, TXT)
into plain text the embedding model can chew on. Django stores uploaded files
in `media/documents/YYYY/MM/` and gives us `document.file.path` — this module
turns that path into `{"text": str, "pages": int}`.

SUPPORTED FORMATS
-----------------
- .pdf   → pypdf.PdfReader, page-by-page extraction (we keep page numbers for citations)
- .docx  → python-docx, paragraphs joined with newlines (1 logical "page")
- .txt   → direct UTF-8 read (1 page)
- .md    → direct UTF-8 read (1 page); Markdown is left intact (embeddings handle it fine)
- images → returns empty text (OCR not in scope; you can plug Tesseract here later)

LANGUAGE HANDLING
-----------------
This module returns text only. Language detection is done by `rag/engine.detect_language`
or `langdetect` in `rag/my_engine.py` — NOT here, so we keep extraction pure.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict


def extract(path: str | Path) -> Dict:
    """
    Extract text from a file on disk.

    Returns:
        {"text": str, "pages": int} on success
        {"text": "", "pages": 0, "error": str} on failure
    """
    p = Path(path)
    if not p.exists():
        return {"text": "", "pages": 0, "error": f"File not found: {path}"}

    ext = p.suffix.lower()
    try:
        if ext == ".pdf":
            return _extract_pdf(p)
        if ext == ".docx":
            return _extract_docx(p)
        if ext in (".txt", ".md"):
            return _extract_text(p)
        if ext in (".png", ".jpg", ".jpeg"):
            return {"text": "", "pages": 0, "error": "Image files require OCR (not configured)"}
        return {"text": "", "pages": 0, "error": f"Unsupported extension: {ext}"}
    except Exception as e:
        # Never raise — the caller (`rag/my_engine.py`) relies on a dict return
        # so it can mark the document as `failed` in the database cleanly.
        return {"text": "", "pages": 0, "error": f"{type(e).__name__}: {e}"}


def _extract_pdf(path: Path) -> Dict:
    """PDF: extract text page-by-page so we keep page numbers for citations."""
    from pypdf import PdfReader  # lazy import: pypdf is heavy
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        pages.append({"page": i, "text": txt})
    full_text = "\n\n".join(p["text"] for p in pages).strip()
    return {"text": full_text, "pages": len(pages), "page_texts": pages}


def _extract_docx(path: Path) -> Dict:
    """DOCX: join paragraphs. python-docx doesn't give page numbers, so we
    synthesize pseudo-pages of ~500 words to keep the citation page concept."""
    from docx import Document  # lazy import
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs)
    # pseudo-paginate: every ~500 words becomes a page
    words = full_text.split()
    page_count = max(1, len(words) // 500 + (1 if len(words) % 500 else 0))
    page_texts = []
    for i in range(page_count):
        chunk_words = words[i * 500:(i + 1) * 500]
        page_texts.append({"page": i + 1, "text": " ".join(chunk_words)})
    return {"text": full_text, "pages": page_count, "page_texts": page_texts}


def _extract_text(path: Path) -> Dict:
    """TXT / MD: read as UTF-8. Arabic and French both encode cleanly."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return {"text": text, "pages": 1, "page_texts": [{"page": 1, "text": text}]}


def supported_extensions() -> list:
    """Convenience for the admin UI / health endpoint."""
    return [".pdf", ".docx", ".txt", ".md"]
