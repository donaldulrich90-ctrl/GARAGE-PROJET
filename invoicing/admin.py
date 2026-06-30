from django.contrib import admin

from core.admin import TenantScopedAdmin
from .models import Invoice, Payment, ProformaInvoice, ProformaInvoiceLine, Quote, QuoteLine


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


class ProformaLineInline(admin.TabularInline):
    model = ProformaInvoiceLine
    extra = 0


@admin.register(ProformaInvoice)
class ProformaInvoiceAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ("reference", "display_client", "status", "total", "paid_at", "garage")
    list_filter = ("status", "garage")
    inlines = [ProformaLineInline]
    readonly_fields = ("reference", "paid_at")
