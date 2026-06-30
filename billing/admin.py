from datetime import date, timedelta

from django.contrib import admin, messages

from .models import PLAN_CHOICES, Subscription, SubscriptionPayment


class SubscriptionPaymentInline(admin.TabularInline):
    model = SubscriptionPayment
    extra = 1
    fields = ("paid_at", "amount", "method", "note", "recorded_by")
    readonly_fields = ("recorded_by",)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if not obj.pk:
                obj.recorded_by = request.user
            obj.save()
        formset.save_m2m()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "garage",
        "plan",
        "status",
        "end_date",
        "days_until_expiry",
        "total_paid",
        "balance_due",
    )
    list_filter = ("plan", "status")
    search_fields = ("garage__name", "garage__city")
    readonly_fields = ("created_at", "updated_at", "total_paid", "balance_due", "days_until_expiry")
    inlines = [SubscriptionPaymentInline]
    actions = ["renouveler_1_an", "marquer_expire", "marquer_actif"]

    fieldsets = (
        ("Garage", {"fields": ("garage",)}),
        ("Abonnement", {"fields": ("plan", "status", "start_date", "end_date")}),
        ("Récapitulatif paiements", {"fields": ("total_paid", "balance_due"), "classes": ("collapse",)}),
        ("Dates système", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Jours restants")
    def days_until_expiry(self, obj):
        d = obj.days_until_expiry
        if d < 0:
            return f"Expiré ({abs(d)}j)"
        if d <= 30:
            return f"⚠️ {d}j"
        return f"{d}j"

    @admin.display(description="Payé (FCFA)")
    def total_paid(self, obj):
        return f"{obj.total_paid:,} FCFA"

    @admin.display(description="Solde dû (FCFA)")
    def balance_due(self, obj):
        b = obj.balance_due
        return f"{b:,} FCFA" if b > 0 else "—"

    @admin.action(description="Renouveler pour 1 an")
    def renouveler_1_an(self, request, queryset):
        for sub in queryset:
            sub.renew()
        self.message_user(request, f"{queryset.count()} abonnement(s) renouvelé(s).", messages.SUCCESS)

    @admin.action(description="Marquer comme expiré")
    def marquer_expire(self, request, queryset):
        queryset.update(status=Subscription.STATUS_EXPIRED)
        self.message_user(request, f"{queryset.count()} abonnement(s) marqué(s) expiré(s).", messages.WARNING)

    @admin.action(description="Marquer comme actif")
    def marquer_actif(self, request, queryset):
        queryset.update(status=Subscription.STATUS_ACTIVE)
        self.message_user(request, f"{queryset.count()} abonnement(s) activé(s).", messages.SUCCESS)
