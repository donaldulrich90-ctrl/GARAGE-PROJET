from django.contrib import admin

from .models import VehicleTax


@admin.register(VehicleTax)
class VehicleTaxAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'tax_type', 'fiscal_year', 'amount', 'due_date', 'is_paid', 'garage')
    list_filter = ('tax_type', 'is_paid', 'fiscal_year')
    search_fields = ('vehicle__plate_number', 'receipt_number')
