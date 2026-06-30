from django.contrib import admin

from .models import Employee, Payroll

admin.site.register(Employee)
admin.site.register(Payroll)
