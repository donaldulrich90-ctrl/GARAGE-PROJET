from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "garage", "category", "amount", "payment_method", "employee", "recorded_by")
    list_filter = ("garage", "category", "payment_method")
    search_fields = ("description",)
    date_hierarchy = "date"
