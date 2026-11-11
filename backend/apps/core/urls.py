from django.urls import path
from . import views as v

urlpatterns = [
    path("dashboard/", v.UserDashboard.as_view()),
    path("admin/stats/", v.AdminStats.as_view()),
    path("admin/analytics/", v.AdminAnalytics.as_view()),
    path("admin/feed/", v.AdminFeed.as_view()),
    path("admin/system/", v.AdminSystem.as_view()),
    path("admin/system/reindex-failed/", v.ReindexFailed.as_view()),
    path("admin/audit/", v.AuditList.as_view()),
    path("admin/rag/settings/", v.RagSettings.as_view()),
    path("admin/rag/health/", v.RagHealth.as_view()),
    path("admin/rag/test/", v.RagTest.as_view()),
]
