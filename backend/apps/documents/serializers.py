from rest_framework import serializers
from .models import Conversation, Document, Message


class DocumentSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "title", "file", "url", "language", "status", "pages", "size", "error", "owner_name", "created_at"]
        read_only_fields = ["status", "pages", "size", "error", "owner_name", "created_at"]
        extra_kwargs = {"file": {"write_only": True}, "title": {"required": False}, "language": {"required": False}}

    def get_url(self, obj):
        req = self.context.get("request")
        return req.build_absolute_uri(obj.file.url) if req and obj.file else None


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "language", "sources", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    document_ids = serializers.PrimaryKeyRelatedField(source="documents", many=True, queryset=Document.objects.all(), required=False)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "title", "document_ids", "messages", "message_count", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.messages.count()
