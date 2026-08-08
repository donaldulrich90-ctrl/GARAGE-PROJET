from django.contrib import admin

from .models import CatalogPart, PartCategory, VehicleMake, VehicleModel


@admin.register(VehicleMake)
class VehicleMakeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class VehicleModelInline(admin.TabularInline):
    model = VehicleModel
    extra = 1
    prepopulated_fields = {"slug": ("name",)}


VehicleMakeAdmin.inlines = [VehicleModelInline]


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ("make", "name", "year_from", "year_to")
    list_filter = ("make",)
    search_fields = ("name", "make__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("make",)


@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CatalogPart)
class CatalogPartAdmin(admin.ModelAdmin):
    list_display = ("reference", "name", "category", "is_universal")
    list_filter = ("category", "is_universal", "compatible_models__make")
    search_fields = ("reference", "name")
    autocomplete_fields = ("category", "compatible_models")
    filter_horizontal = ("compatible_models",)
