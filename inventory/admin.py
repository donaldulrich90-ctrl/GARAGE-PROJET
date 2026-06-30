from django.contrib import admin

from core.admin import TenantScopedAdmin
from .models import Supplier, Part, StockMovement


@admin.register(Supplier)
class SupplierAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ("name", "is_faest", "phone", "garage")
    list_filter = ("is_faest", "garage")


@admin.register(Part)
class PartAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = (
        "reference", "name", "supplier", "unit_price",
        "quantity_in_stock", "needs_reorder", "garage",
    )
    list_filter = ("supplier", "garage")
    search_fields = ("reference", "name")

    @admin.display(boolean=True, description="À réapprovisionner")
    def needs_reorder(self, obj):
        return obj.needs_reorder


@admin.register(StockMovement)
class StockMovementAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ("part", "movement_type", "quantity", "reason", "created_at", "garage")
    list_filter = ("movement_type", "garage")
