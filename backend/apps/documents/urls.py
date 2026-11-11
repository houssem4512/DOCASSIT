from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views as v

router = DefaultRouter()
router.register("documents", v.DocumentViewSet, basename="documents")
router.register("conversations", v.ConversationViewSet, basename="conversations")

urlpatterns = [path("search/", v.SearchView.as_view()), path("", include(router.urls))]
