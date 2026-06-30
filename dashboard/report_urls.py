from django.urls import path

from . import report_views

urlpatterns = [
    path("", report_views.BilanView.as_view(), name="bilan"),
]
