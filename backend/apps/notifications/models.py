from django.conf import settings
from django.db import models


class Notification(models.Model):
    KINDS = [("info", "info"), ("success", "success"), ("warning", "warning"), ("error", "error")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=140)
    body = models.TextField(blank=True)
    kind = models.CharField(max_length=10, choices=KINDS, default="info")
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
