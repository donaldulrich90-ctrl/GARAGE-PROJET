from django.urls import path

from . import views

urlpatterns = [
    path('<int:order_pk>/nouveau/', views.DiagnosticCreateView.as_view(), name='diagnostic_create'),
    path('<int:pk>/', views.DiagnosticDetailView.as_view(), name='diagnostic_detail'),
    path('<int:pk>/modifier/', views.DiagnosticUpdateView.as_view(), name='diagnostic_update'),
    path('<int:pk>/imprimer/', views.DiagnosticPrintView.as_view(), name='diagnostic_print'),
]
