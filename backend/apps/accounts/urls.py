from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views as v

router = DefaultRouter()
router.register("admin/users", v.AdminUserViewSet, basename="admin-users")

urlpatterns = [
    path("auth/register/", v.Register.as_view()),
    path("auth/login/", v.Login.as_view()),
    path("auth/me/", v.Me.as_view()),
    path("", include(router.urls)),
]
