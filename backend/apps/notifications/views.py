from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminRole
from apps.core.utils import log
from .models import Notification

FIELDS = ["id", "title", "body", "kind", "read", "created_at"]


class NotificationList(APIView):
    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        return Response({"unread": qs.filter(read=False).count(), "results": list(qs.values(*FIELDS)[:100])})


@api_view(["POST"])
def mark_read(request, pk):
    Notification.objects.filter(user=request.user, pk=pk).update(read=True)
    return Response({"ok": True})


@api_view(["POST"])
def mark_all_read(request):
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    return Response({"ok": True})


@api_view(["DELETE"])
def delete_notification(request, pk):
    Notification.objects.filter(user=request.user, pk=pk).delete()
    return Response(status=204)


class Broadcast(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        U = get_user_model()
        users = U.objects.filter(is_active=True)
        Notification.objects.bulk_create([
            Notification(user=u, title=request.data.get("title", "Announcement"),
                         body=request.data.get("body", ""), kind=request.data.get("kind", "info")) for u in users])
        log(request, "notify.broadcast", request.data.get("title", ""))
        return Response({"sent": users.count()})
