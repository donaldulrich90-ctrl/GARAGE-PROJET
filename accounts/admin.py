from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Garage", {"fields": ("garage", "role", "phone")}),
    )
    list_display = ("username", "first_name", "last_name", "garage", "role", "is_staff")
    list_filter = ("garage", "role", "is_staff")
