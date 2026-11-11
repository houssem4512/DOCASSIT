"""
============================================================================
rag/embeddings.py — Multilingual embedding model (LangChain interface)
============================================================================
WHY THIS EXISTS
---------------
Embeddings turn text into vectors so we can do similarity search. For an
Arabic / French / English project, the model MUST be multilingual — a common
mistake is using `all-MiniLM-L6-v2` which is English-only and silently
returns garbage for Arabic.

CHOSEN MODEL
------------
Default: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
    - 384-dimensional vectors
    - ~120 MB on disk
    - Trained on 50+ languages including Arabic, French, English
    - Fast on CPU (no GPU required for inference)

This is the BASELINE for the fine-tuning comparison (Phase E of the roadmap).
After fine-tuning, point `EMBEDDING_MODEL` env var at the local path, e.g.
`./models/docassist-ft`, and this same wrapper will load the fine-tuned model.

LAZY LOADING
------------
The model is heavy (~120 MB download + ~2 sec load time). We don't want to
block Django startup or the Celery worker. So we lazy-load: the model is
fetched on the first call to `embed_query` / `embed_documents` and cached
as a module-level singleton thereafter.
"""
from __future__ import annotations
from functools import lru_cache

from django.conf import settings
from langchain_core.embeddings import Embeddings


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    """
    Load (and cache) the sentence-transformers model.
    `lru_cache(maxsize=1)` ensures we only load ONCE per process — every
    call to `STEmbeddings()` shares the same underlying model.
    """
    from sentence_transformers import SentenceTransformer  # heavy import
    return SentenceTransformer(model_name)


class STEmbeddings(Embeddings):
    """
    LangChain `Embeddings` adapter around sentence-transformers.

    LangChain calls `embed_query(text)` for the question and
    `embed_documents(texts)` for the chunks. Both must return float vectors
    of the same dimensionality (384 for the default MiniLM).
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL

    def _model(self):
        return _load_model(self.model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # `normalize_embeddings=True` so cosine similarity = dot product —
        # Chroma defaults to L2 but normalised vectors make the two equivalent,
        # which is what we want for semantic similarity.
        return self._model().encode(
            texts, normalize_embeddings=True, show_progress_bar=False,
        ).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model().encode(
            [text], normalize_embeddings=True, show_progress_bar=False,
        )[0].tolist()

    def dimension(self) -> int:
        """Convenience: returns the vector dimension (384 for the default model).
        Useful for sanity-checks in the health endpoint."""
        return len(self.embed_query("test"))


# Module-level singleton used by `rag/vectorstore.py` and `rag/my_engine.py`.
_embeddings: STEmbeddings | None = None


def get_embeddings() -> STEmbeddings:
    """Return the shared embeddings instance (singleton)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = STEmbeddings()
    return _embeddings
