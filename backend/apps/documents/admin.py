from django.contrib import admin
from .models import Conversation, Document, Message
admin.site.register(Document)
admin.site.register(Conversation)
admin.site.register(Message)
