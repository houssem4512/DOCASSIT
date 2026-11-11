import os

from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminRole
from apps.core.utils import log
from apps.notifications.models import Notification
from rag.engine import detect_language, get_engine
from .models import Conversation, Document, Message
from .serializers import ConversationSerializer, DocumentSerializer, MessageSerializer


def ingest(doc, request):
    doc.status = "processing"
    doc.save(update_fields=["status"])
    try:
        r = get_engine().ingest(doc)
        doc.status, doc.pages = r["status"], r.get("pages", 0)
        doc.language = r.get("language", doc.language)
        doc.error = r.get("error") or ""
    except Exception as e:  # engine errors must never break upload
        doc.status, doc.error = "failed", str(e)[:250]
    doc.save()
    ok = doc.status == "ready"
    Notification.objects.create(
        user=doc.owner, kind="success" if ok else "error",
        title="Document ready" if ok else "Indexing failed",
        body=doc.title if ok else f"{doc.title}: {doc.error}")


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = Document.objects.select_related("owner")
        u = self.request.user
        if not (u.role == "admin" and self.request.query_params.get("scope") == "all"):
            qs = qs.filter(owner=u)
        q = self.request.query_params
        if q.get("language"):
            qs = qs.filter(language=q["language"])
        if q.get("status"):
            qs = qs.filter(status=q["status"])
        if q.get("q"):
            qs = qs.filter(title__icontains=q["q"])
        return qs

    def perform_create(self, serializer):
        f = self.request.FILES.get("file")
        if not f:
            raise ValidationError({"file": "No file provided."})
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise ValidationError({"file": f"Unsupported type {ext}. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"})
        if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise ValidationError({"file": f"Max size is {settings.MAX_UPLOAD_MB} MB."})
        title = serializer.validated_data.get("title") or os.path.splitext(f.name)[0]
        doc = serializer.save(owner=self.request.user, title=title, size=f.size,
                              language=serializer.validated_data.get("language") or detect_language(title))
        log(self.request, "document.upload", doc.title)
        ingest(doc, self.request)

    def perform_destroy(self, doc):
        try:
            get_engine().delete(doc)
        finally:
            log(self.request, "document.delete", doc.title)
            doc.file.delete(save=False)
            doc.delete()

    @action(detail=True, methods=["post"])
    def reindex(self, request, pk=None):
        doc = self.get_object()
        ingest(doc, request)
        return Response(self.get_serializer(doc).data)


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(owner=self.request.user).prefetch_related("messages", "documents")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def ask(self, request, pk=None):
        conv = self.get_object()
        question = (request.data.get("question") or "").strip()
        if not question:
            raise ValidationError({"question": "Question is empty."})
        doc_ids = list(conv.documents.values_list("id", flat=True))
        history = [{"role": m.role, "content": m.content} for m in list(conv.messages.all())[-10:]]
        um = Message.objects.create(conversation=conv, role="user", content=question, language=detect_language(question))
        if conv.messages.count() == 1:
            conv.title = question[:60]
            conv.save()
        try:
            r = get_engine().answer(question, request.user, document_ids=doc_ids or None, history=history,
                                    language=request.data.get("language"))
        except Exception as e:
            r = {"answer": f"Engine error: {e}", "language": "en", "sources": []}
        am = Message.objects.create(conversation=conv, role="assistant", content=r["answer"],
                                    language=r.get("language", "en"), sources=r.get("sources", []))
        conv.save()
        log(request, "chat.ask", question[:80])
        return Response({"user_message": MessageSerializer(um).data, "assistant_message": MessageSerializer(am).data,
                         "title": conv.title})


class SearchView(APIView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response([])
        lang = request.query_params.get("language") or None
        log(request, "search", q[:80])
        return Response(get_engine().search(q, request.user, language=lang))
