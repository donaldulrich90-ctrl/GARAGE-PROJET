from django.urls import path

from . import views

urlpatterns = [
    path("", views.EmployeeListView.as_view(), name="employee_list"),
    path("nouveau/", views.EmployeeCreateView.as_view(), name="employee_create"),
    path("<int:pk>/", views.EmployeeDetailView.as_view(), name="employee_detail"),
    path("<int:pk>/modifier/", views.EmployeeUpdateView.as_view(), name="employee_update"),
    path("<int:pk>/supprimer/", views.EmployeeDeleteView.as_view(), name="employee_delete"),
    path("<int:pk>/paie/", views.GeneratePayrollView.as_view(), name="payroll_generate"),
    path("paie/groupe/", views.GenerateBulkPayrollView.as_view(), name="payroll_bulk"),
    path("bulletin/<int:pk>/imprimer/", views.PayslipPrintView.as_view(), name="payslip_print"),
]
