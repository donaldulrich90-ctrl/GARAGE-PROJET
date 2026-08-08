from django.urls import path

from . import views

urlpatterns = [
    path("journal/", views.audit_log, name="audit_log"),
    path("commissions/", views.platform_commissions, name="platform_commissions"),
]
