from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Conversation, Document, Message
from rag.engine import get_engine
from .models import AppSetting, AuditLog
from .permissions import IsAdminRole
from .utils import log

User = get_user_model()
DEFAULT_RAG_CONFIG = {
    "llm_model": "your-llm-name", "embedding_model": "multilingual-e5-large",
    "vector_store": "faiss", "chunk_size": 800, "chunk_overlap": 120, "top_k": 5,
    "languages": ["ar", "fr", "en"], "enabled": True,
}


def by_language(qs):
    d = {"ar": 0, "fr": 0, "en": 0}
    for r in qs.values("language").annotate(n=Count("id")):
        d[r["language"]] = r["n"]
    return d


class UserDashboard(APIView):
    def get(self, request):
        docs = Document.objects.filter(owner=request.user)
        convs = Conversation.objects.filter(owner=request.user)
        return Response({
            "documents": docs.count(),
            "ready": docs.filter(status="ready").count(),
            "conversations": convs.count(),
            "questions": Message.objects.filter(conversation__owner=request.user, role="user").count(),
            "storage": docs.aggregate(s=Sum("size"))["s"] or 0,
            "by_language": by_language(docs),
            "recent_documents": list(docs.order_by("-created_at").values("id", "title", "language", "status", "size", "created_at")[:5]),
            "recent_conversations": list(convs.order_by("-updated_at").values("id", "title", "updated_at")[:5]),
        })


class AdminStats(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        today = timezone.now().date()
        days = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            days.append({"date": d.isoformat(),
                         "uploads": Document.objects.filter(created_at__date=d).count(),
                         "questions": Message.objects.filter(role="user", created_at__date=d).count()})
        return Response({
            "users": User.objects.count(), "active_users": User.objects.filter(is_active=True).count(),
            "admins": User.objects.filter(role="admin").count(),
            "documents": Document.objects.count(), "conversations": Conversation.objects.count(),
            "questions": Message.objects.filter(role="user").count(),
            "storage": Document.objects.aggregate(s=Sum("size"))["s"] or 0,
            "by_language": by_language(Document.objects),
            "by_status": {r["status"]: r["n"] for r in Document.objects.values("status").annotate(n=Count("id"))},
            "activity": days,
            "top_users": list(User.objects.annotate(n=Count("documents")).order_by("-n").values("id", "username", "n")[:5]),
        })


class AuditList(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        rows = AuditLog.objects.select_related("user")[:200]
        return Response([{"id": r.id, "user": r.user.username if r.user else "—", "action": r.action,
                          "detail": r.detail, "ip": r.ip, "created_at": r.created_at} for r in rows])


class RagSettings(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        obj = AppSetting.objects.filter(key="rag").first()
        return Response({**DEFAULT_RAG_CONFIG, **(obj.value if obj else {})})

    def put(self, request):
        obj, _ = AppSetting.objects.get_or_create(key="rag")
        obj.value = {**DEFAULT_RAG_CONFIG, **request.data}
        obj.save()
        log(request, "rag.config", "RAG settings updated")
        return Response(obj.value)


class RagHealth(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(get_engine().health())


class RagTest(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        q = request.data.get("query", "")
        language = request.data.get("language")  # FIX: forward language so the LLM answers in the right tongue
        return Response(get_engine().answer(q, request.user, language=language))


# ======================= extra admin dashboards =======================
import os
import platform
import shutil
import sys
import time

import django
from django.conf import settings
from django.db.models import Q
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncDate

PROCESS_START = time.time()


def _dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


class AdminAnalytics(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        n = max(7, min(int(request.query_params.get("days", 30)), 90))
        today = timezone.localdate()
        days = [today - timedelta(days=i) for i in range(n - 1, -1, -1)]
        start = days[0]

        def per_day(qs, field="created_at"):
            rows = (qs.filter(**{f"{field}__date__gte": start}).annotate(d=TruncDate(field))
                    .values("d").order_by().annotate(n=Count("id")))
            return {r["d"]: r["n"] for r in rows}

        up, qu = per_day(Document.objects), per_day(Message.objects.filter(role="user"))
        su = per_day(User.objects, "date_joined")
        act = {}
        for r in (AuditLog.objects.filter(created_at__date__gte=start, user__isnull=False)
                  .annotate(d=TruncDate("created_at")).values("d", "user").distinct()):
            act[r["d"]] = act.get(r["d"], 0) + 1
        series = [{"date": d.isoformat(), "uploads": up.get(d, 0), "questions": qu.get(d, 0),
                   "signups": su.get(d, 0), "active": act.get(d, 0)} for d in days]

        msgs = Message.objects.filter(role="user", created_at__date__gte=start)
        hourly = [0] * 24
        for r in msgs.annotate(h=ExtractHour("created_at")).values("h").order_by().annotate(n=Count("id")):
            hourly[r["h"]] = r["n"]
        weekday = [0] * 7  # Mon..Sun ; Django: 1=Sunday
        for r in msgs.annotate(w=ExtractWeekDay("created_at")).values("w").order_by().annotate(n=Count("id")):
            weekday[(r["w"] + 5) % 7] = r["n"]

        types = {}
        for f in Document.objects.values_list("file", flat=True):
            ext = os.path.splitext(f)[1].lower().lstrip(".") or "other"
            types[ext] = types.get(ext, 0) + 1
        qlang = {"ar": 0, "fr": 0, "en": 0}
        for r in Message.objects.filter(role="user").values("language").order_by().annotate(n=Count("id")):
            qlang[r["language"]] = r["n"]

        docs, ready = Document.objects.count(), Document.objects.filter(status="ready").count()
        answers = Message.objects.filter(role="assistant").count()
        sourced = Message.objects.filter(role="assistant").exclude(sources=[]).count()
        users = max(1, User.objects.count())
        return Response({
            "days": n, "series": series, "hourly": hourly, "weekday": weekday,
            "file_types": types, "question_languages": qlang,
            "storage_by_user": list(User.objects.annotate(s=Sum("documents__size"), n=Count("documents"))
                                    .order_by("-s").values("username", "s", "n")[:8]),
            "kpi": {
                "avg_doc_size": int((Document.objects.aggregate(s=Sum("size"))["s"] or 0) / max(1, docs)),
                "questions_per_user": round(Message.objects.filter(role="user").count() / users, 1),
                "docs_per_user": round(docs / users, 1),
                "success_rate": round(100 * ready / docs) if docs else 0,
                "sourced_rate": round(100 * sourced / answers) if answers else 0,
            },
        })


class AdminFeed(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        now = timezone.now()
        w, pw = now - timedelta(days=7), now - timedelta(days=14)

        def cmp(qs, f="created_at"):
            return {"week": qs.filter(**{f + "__gte": w}).count(),
                    "prev": qs.filter(**{f + "__gte": pw, f + "__lt": w}).count()}

        events = AuditLog.objects.select_related("user")[:12]
        return Response({
            "users": cmp(User.objects, "date_joined"), "documents": cmp(Document.objects),
            "questions": cmp(Message.objects.filter(role="user")),
            "logins": cmp(AuditLog.objects.filter(action="auth.login")),
            "recent_users": list(User.objects.order_by("-date_joined").values("id", "username", "role", "date_joined")[:6]),
            "failed_documents": list(Document.objects.filter(status="failed")
                                     .values("id", "title", "error", "owner__username", "created_at")[:6]),
            "events": [{"id": e.id, "user": e.user.username if e.user else "—", "action": e.action,
                        "detail": e.detail, "created_at": e.created_at} for e in events],
        })


class AdminSystem(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        db = settings.DATABASES["default"]["NAME"]
        media = settings.MEDIA_ROOT
        disk = shutil.disk_usage(str(settings.BASE_DIR))
        return Response({
            "python": sys.version.split()[0], "django": django.get_version(), "os": platform.system() + " " + platform.release(),
            "uptime": int(time.time() - PROCESS_START), "server_time": timezone.now(),
            "db_size": os.path.getsize(db) if os.path.exists(str(db)) else 0,
            "media_size": _dir_size(media) if os.path.exists(str(media)) else 0,
            "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
            "engine": settings.RAG_ENGINE, "rag": get_engine().health(),
            "debug": settings.DEBUG, "max_upload_mb": settings.MAX_UPLOAD_MB,
            "extensions": settings.ALLOWED_EXTENSIONS,
            "status": {r["status"]: r["n"] for r in Document.objects.values("status").order_by().annotate(n=Count("id"))},
        })


class ReindexFailed(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        from apps.documents.views import ingest
        docs = list(Document.objects.filter(status="failed"))
        for d in docs:
            ingest(d, request)
        log(request, "system.reindex", f"{len(docs)} documents")
        return Response({"count": len(docs)})
