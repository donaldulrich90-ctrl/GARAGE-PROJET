from django.contrib import admin

from .models import DiagnosticCode, DiagnosticReport


class DiagnosticCodeInline(admin.TabularInline):
    model = DiagnosticCode
    extra = 1


@admin.register(DiagnosticReport)
class DiagnosticReportAdmin(admin.ModelAdmin):
    list_display = ['reference', 'repair_order', 'scan_date', 'technician', 'garage']
    list_filter = ['garage']
    search_fields = ['reference']
    inlines = [DiagnosticCodeInline]
