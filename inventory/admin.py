from django.contrib import admin

from core.admin import TenantScopedAdmin
from .models import (
    Part, StockMovement, Supplier, SupplierExpense, SupplierOrder, SupplierOrderLine,
    SupplierPart, SupplierStockMovement,
)


@admin.register(Supplier)
class SupplierAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ("name", "is_faest", "phone", "garage")
    list_filter = ("is_faest", "garage")


@admin.register(SupplierExpense)
class SupplierExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "supplier", "category", "amount", "payment_method", "recorded_by")
    list_filter = ("category", "payment_method", "supplier")
    search_fields = ("supplier__name", "description", "reference")


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


@admin.register(SupplierPart)
class SupplierPartAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ("supplier", "catalog_part", "g_code", "unit_price", "quantity_available", "lead_time_days", "garage")
    list_filter = ("supplier", "garage")
    search_fields = ("catalog_part__name", "catalog_part__reference", "g_code", "supplier_reference")


@admin.register(SupplierStockMovement)
class SupplierStockMovementAdmin(admin.ModelAdmin):
    list_display = ("sale_reference", "supplier_part", "movement_type", "quantity", "unit_price", "customer_name", "destination_garage", "created_at")
    list_filter = ("movement_type", "supplier_part__supplier")
    search_fields = ("supplier_part__catalog_part__name",)


class SupplierOrderLineInline(admin.TabularInline):
    model = SupplierOrderLine
    extra = 0
    readonly_fields = ("catalog_reference", "catalog_name", "line_total_display")

    def line_total_display(self, obj):
        return f"{obj.line_total} FCFA" if obj.pk else "—"
    line_total_display.short_description = "Total ligne"


@admin.register(SupplierOrder)
class SupplierOrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "garage", "supplier", "status",
        "total_amount", "commission_rate", "commission_amount", "validated_at",
    )
    list_filter = ("status", "supplier", "garage")
    search_fields = ("reference",)
    readonly_fields = ("reference", "total_amount", "commission_rate", "commission_amount",
                       "submitted_at", "validated_at", "rejected_at", "shipped_at", "delivered_at", "cancelled_at")
    inlines = [SupplierOrderLineInline]
