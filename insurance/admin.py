from django.contrib import admin

from .models import Insurance, InsuranceClaim

admin.site.register(Insurance)
admin.site.register(InsuranceClaim)
