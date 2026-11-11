from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    documents_count = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "language",
                  "is_active", "date_joined", "last_login", "documents_count", "password"]
        read_only_fields = ["date_joined", "last_login"]

    def get_documents_count(self, obj):
        return obj.documents.count() if hasattr(obj, "documents") else 0

    def create(self, data):
        pw = data.pop("password", None)
        u = User(**data)
        u.set_password(pw or get_random_string(12))
        u.save()
        return u

    def update(self, inst, data):
        pw = data.pop("password", None)
        for k, v in data.items():
            setattr(inst, k, v)
        if pw:
            inst.set_password(pw)
        inst.save()
        return inst


class ProfileSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = UserSerializer.Meta.read_only_fields + ["role", "is_active", "username"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password", "language"]

    def create(self, data):
        return User.objects.create_user(**data)
