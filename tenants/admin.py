from django.contrib import admin

from .models import Garage


@admin.register(Garage)
class GarageAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "plan", "is_active", "faest_supplier_enabled")
    list_filter = ("plan", "is_active", "faest_supplier_enabled")
    search_fields = ("name", "city", "phone", "email")
