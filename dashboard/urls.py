from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="dashboard_home"),
    path("nouveau-diagnostic/", views.DiagnosticOrderSelectView.as_view(), name="dashboard_diag_select"),
]
