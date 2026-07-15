from django.contrib import admin

from core.admin import TenantScopedAdmin

from .models import BroadcastCampaign, MessageTemplate, WhatsAppLog


@admin.register(MessageTemplate)
class MessageTemplateAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ('name', 'source', 'garage', 'created_at')
    list_filter = ('source',)
    search_fields = ('name',)


@admin.register(WhatsAppLog)
class WhatsAppLogAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ('phone', 'client', 'source', 'status', 'created_at', 'garage')
    list_filter = ('status', 'source')
    search_fields = ('phone', 'body', 'client__full_name')
    readonly_fields = ('phone', 'body', 'status', 'source', 'error', 'client', 'campaign', 'template')


@admin.register(BroadcastCampaign)
class BroadcastCampaignAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ('name', 'filter_type', 'status', 'sent_count', 'created_at', 'garage')
    list_filter = ('status', 'filter_type')
    search_fields = ('name',)
