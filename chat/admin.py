from django.contrib import admin

from .models import ChatMessage, Conversation


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("created_at", "sender", "from_supplier", "body", "image")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "garage", "updated_at")
    search_fields = ("supplier__name", "garage__name")
    inlines = [ChatMessageInline]
