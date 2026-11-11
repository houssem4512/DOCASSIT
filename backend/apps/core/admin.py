from django.contrib import admin
from .models import AuditLog, AppSetting
admin.site.register(AuditLog)
admin.site.register(AppSetting)
