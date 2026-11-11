from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.notifications.models import Notification


class Command(BaseCommand):
    help = "Create demo admin and user accounts"

    def handle(self, *a, **kw):
        U = get_user_model()
        if not U.objects.filter(username="admin").exists():
            U.objects.create_superuser("admin", "admin@example.com", "admin123", role="admin", first_name="Admin")
        if not U.objects.filter(username="demo").exists():
            u = U.objects.create_user("demo", "demo@example.com", "demo1234", first_name="Demo")
            Notification.objects.create(user=u, title="Welcome", body="Upload your first document to get started.", kind="info")
        self.stdout.write(self.style.SUCCESS("admin/admin123  and  demo/demo1234 ready"))
