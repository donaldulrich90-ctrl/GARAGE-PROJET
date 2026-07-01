from django.urls import path

from . import views

urlpatterns = [
    path("journal/", views.audit_log, name="audit_log"),
]
