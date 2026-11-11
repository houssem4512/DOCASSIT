from .models import AuditLog


def log(request, action, detail=""):
    user = getattr(request, "user", None)
    ip = request.META.get("REMOTE_ADDR") if request else None
    AuditLog.objects.create(user=user if user and user.is_authenticated else None,
                            action=action, detail=str(detail)[:255], ip=ip)
