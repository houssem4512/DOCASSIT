from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminRole
from apps.core.utils import log
from apps.notifications.models import Notification
from .serializers import ProfileSerializer, RegisterSerializer, UserSerializer

User = get_user_model()


def auth_payload(user):
    token, _ = Token.objects.get_or_create(user=user)
    return {"token": token.key, "user": UserSerializer(user).data}


class Register(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        Notification.objects.create(user=user, title="Welcome", kind="info",
                                    body="Your account is ready. Upload your first document to get started.")
        request.user = user
        log(request, "auth.register", user.username)
        return Response(auth_payload(user), status=201)


class Login(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        user = authenticate(username=request.data.get("username"), password=request.data.get("password"))
        if not user or not user.is_active:
            return Response({"detail": "Invalid username or password."}, status=400)
        request.user = user
        log(request, "auth.login", user.username)
        return Response(auth_payload(user))


class Me(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        s = ProfileSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class AdminUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by("-date_joined")

    def perform_destroy(self, inst):
        log(self.request, "user.delete", inst.username)
        inst.delete()
