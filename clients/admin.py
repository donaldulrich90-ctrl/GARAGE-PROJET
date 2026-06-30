from django.contrib import admin

from core.admin import TenantScopedAdmin
from .models import Client, Vehicle


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 0


@admin.register(Client)
class ClientAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ("full_name", "phone", "client_type", "garage")
    list_filter = ("client_type", "garage")
    search_fields = ("full_name", "phone", "email")
    inlines = [VehicleInline]


@admin.register(Vehicle)
class VehicleAdmin(TenantScopedAdmin, admin.ModelAdmin):
    list_display = ("plate_number", "make", "model", "client", "mileage", "garage")
    list_filter = ("make", "fuel_type", "garage")
    search_fields = ("plate_number", "vin", "client__full_name")
