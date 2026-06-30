from django.contrib import admin

from core.admin import TenantScopedAdmin
from .models import RepairOrder, RepairOrderTask, RepairOrderPart


class RepairOrderTaskInline(admin.TabularInline):
    model = RepairOrderTask
    extra = 0


class RepairOrderPartInline(admin.TabularInline):
    model = RepairOrderPart
    extra = 0


@admin.register(RepairOrder)
class RepairOrderAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = (
        "reference", "vehicle", "client", "status",
        "assigned_mechanic", "total_cost", "garage",
    )
    list_filter = ("status", "garage")
    search_fields = ("reference", "vehicle__plate_number", "client__full_name")
    inlines = [RepairOrderTaskInline, RepairOrderPartInline]
    readonly_fields = ("reference",)
