from django.urls import path
from . import views as v

urlpatterns = [
    path("notifications/", v.NotificationList.as_view()),
    path("notifications/read-all/", v.mark_all_read),
    path("notifications/<int:pk>/read/", v.mark_read),
    path("notifications/<int:pk>/", v.delete_notification),
    path("admin/notifications/broadcast/", v.Broadcast.as_view()),
]
