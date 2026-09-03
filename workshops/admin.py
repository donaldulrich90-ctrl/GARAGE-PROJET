from django.contrib import admin

from .models import WorkshopSection


@admin.register(WorkshopSection)
class WorkshopSectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'garage', 'is_active', 'display_order']
    list_filter = ['garage', 'is_active']
    search_fields = ['name', 'code']
