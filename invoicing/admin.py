from django.contrib import admin

from core.admin import TenantScopedAdmin
from .models import Quote, QuoteLine, Invoice, Payment


class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Quote)
class QuoteAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ("reference", "repair_order", "status", "total", "garage")
    list_filter = ("status", "garage")
    inlines = [QuoteLineInline]
    readonly_fields = ("reference",)


@admin.register(Invoice)
class InvoiceAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = (
        "reference", "repair_order", "status",
        "total", "amount_paid", "balance_due", "garage",
    )
    list_filter = ("status", "garage")
    inlines = [PaymentInline]
    readonly_fields = ("reference",)
