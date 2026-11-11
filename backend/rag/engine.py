"""
==========================================================================
 RAG INTEGRATION POINT  --  plug your Arabic / French / English model here
==========================================================================
1. Subclass BaseRAGEngine and implement the methods below.
2. Point settings.RAG_ENGINE (or env var RAG_ENGINE) to your class, e.g.
       RAG_ENGINE=rag.my_engine.MyRAGEngine
The rest of the application (API, UI, notifications, audit) already calls
these methods; nothing else needs to change.
"""
import re
from django.conf import settings
from django.utils.module_loading import import_string


def detect_language(text: str) -> str:
    """Tiny heuristic: 'ar', 'fr' or 'en'. Replace with langdetect/fastText if you wish."""
    if not text:
        return "en"
    arabic = len(re.findall(r"[\u0600-\u06FF]", text))
    if arabic > max(3, len(text) * 0.2):
        return "ar"
    if re.search(r"[àâçéèêëîïôûùüÿœ]|\b(le|la|les|des|une|est|pour|dans|avec)\b", text.lower()):
        return "fr"
    return "en"


class BaseRAGEngine:
    def health(self) -> dict:
        """-> {"connected": bool, "model": str, "embedding_model": str, "vector_store": str, "detail": str}"""
        raise NotImplementedError

    def ingest(self, document) -> dict:
        """Parse, chunk, embed and index `document.file`.
        -> {"status": "ready"|"failed", "pages": int, "language": "ar"|"fr"|"en", "error": str|None}"""
        raise NotImplementedError

    def delete(self, document) -> None:
        """Remove the document's vectors from the index."""
        raise NotImplementedError

    def search(self, query, user, document_ids=None, language=None, top_k=5) -> list:
        """-> [{"document_id": int, "title": str, "page": int, "snippet": str, "score": float}]"""
        raise NotImplementedError

    def answer(self, question, user, document_ids=None, history=None, language=None) -> dict:
        """`history` = [{"role": "user"|"assistant", "content": str}].
        -> {"answer": str, "language": "ar"|"fr"|"en",
            "sources": [{"document_id": int, "title": str, "page": int, "snippet": str, "score": float}]}"""
        raise NotImplementedError


class PlaceholderEngine(BaseRAGEngine):
    """Demo engine so the UI works before your model exists."""

    def health(self):
        return {"connected": False, "model": "not connected", "embedding_model": "not connected",
                "vector_store": "not connected",
                "detail": "Placeholder engine active. Implement rag/engine.py::BaseRAGEngine."}

    def ingest(self, document):
        return {"status": "ready", "pages": 0, "language": detect_language(document.title), "error": None}

    def delete(self, document):
        return None

    def search(self, query, user, document_ids=None, language=None, top_k=5):
        from apps.documents.models import Document
        qs = Document.objects.filter(owner=user, title__icontains=query)
        if document_ids:
            qs = qs.filter(id__in=document_ids)
        return [{"document_id": d.id, "title": d.title, "page": 1,
                 "snippet": "[Placeholder] Title match only. Connect your RAG model for passage-level search.",
                 "score": 0.0} for d in qs[:top_k]]

    def answer(self, question, user, document_ids=None, history=None, language=None):
        lang = language or detect_language(question)
        msg = {
            "en": "The RAG model is not connected yet. Your question was received; plug your engine into backend/rag/engine.py to get real answers.",
            "fr": "Le modèle RAG n'est pas encore connecté. Votre question a bien été reçue ; branchez votre moteur dans backend/rag/engine.py pour obtenir de vraies réponses.",
            "ar": "نموذج RAG غير متصل بعد. تم استلام سؤالك؛ قم بربط محركك في backend/rag/engine.py للحصول على إجابات حقيقية.",
        }[lang]
        return {"answer": msg, "language": lang, "sources": []}


_engine = None


def get_engine() -> BaseRAGEngine:
    global _engine
    if _engine is None:
        _engine = import_string(settings.RAG_ENGINE)()
    return _engine
