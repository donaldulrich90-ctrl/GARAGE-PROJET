from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from core.views import GarageRequiredMixin
from expenses.models import Expense

from .forms import EmployeeForm, PayrollForm
from .models import Employee, Payroll


class EmployeeListView(GarageRequiredMixin, ListView):
    model = Employee
    template_name = "hr/employee_list.html"
    context_object_name = "employees"

    def get_queryset(self):
        return Employee.objects.for_garage(self.garage).order_by("last_name", "first_name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_payroll"] = sum(
            e.monthly_pay for e in ctx["employees"] if e.is_active
        )
        return ctx


class EmployeeCreateView(GarageRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = "hr/employee_form.html"

    def form_valid(self, form):
        form.instance.garage = self.garage
        messages.success(self.request, "Employé ajouté.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("employee_list")


class EmployeeUpdateView(GarageRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = "hr/employee_form.html"

    def get_queryset(self):
        return Employee.objects.for_garage(self.garage)

    def form_valid(self, form):
        messages.success(self.request, "Fiche mise à jour.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("employee_list")


class EmployeeDeleteView(GarageRequiredMixin, DeleteView):
    model = Employee
    template_name = "hr/employee_confirm_delete.html"
    success_url = reverse_lazy("employee_list")

    def get_queryset(self):
        return Employee.objects.for_garage(self.garage)

    def form_valid(self, form):
        messages.success(self.request, "Fiche supprimée.")
        return super().form_valid(form)


class EmployeeDetailView(GarageRequiredMixin, DetailView):
    model = Employee
    template_name = "hr/employee_detail.html"
    context_object_name = "employee"

    def get_queryset(self):
        return Employee.objects.for_garage(self.garage)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["payrolls"] = self.object.payrolls.order_by("-month")
        ctx["payroll_form"] = PayrollForm()
        return ctx


class GeneratePayrollView(GarageRequiredMixin, View):
    """Generate a payroll entry for one employee for the selected month."""

    def post(self, request, pk):
        employee = get_object_or_404(Employee.objects.for_garage(self.garage), pk=pk)
        form = PayrollForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Date invalide.")
            return redirect("employee_detail", pk=pk)

        raw_month = form.cleaned_data["month"]
        month_date = date(raw_month.year, raw_month.month, 1)
        notes = form.cleaned_data.get("notes", "")

        if Payroll.objects.filter(employee=employee, month=month_date).exists():
            messages.warning(request, f"Un bulletin existe déjà pour {month_date.strftime('%B %Y')}.")
            return redirect("employee_detail", pk=pk)

        expense = Expense.objects.create(
            garage=self.garage,
            date=month_date,
            amount=employee.monthly_pay,
            category=Expense.CAT_SALARY,
            description=f"Salaire {employee.full_name} — {month_date.strftime('%B %Y')}",
            payment_method=Expense.METHOD_CASH,
            recorded_by=request.user,
        )

        payroll = Payroll.objects.create(
            garage=self.garage,
            employee=employee,
            month=month_date,
            amount=employee.monthly_pay,
            expense=expense,
            notes=notes,
        )

        messages.success(request, f"Bulletin de paie {payroll.reference} généré et dépense enregistrée.")
        return redirect("employee_detail", pk=pk)


class GenerateBulkPayrollView(GarageRequiredMixin, View):
    """Generate payroll for ALL active employees for a given month."""

    def get(self, request):
        return redirect("employee_list")

    def post(self, request):
        form = PayrollForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Date invalide.")
            return redirect("employee_list")

        raw_month = form.cleaned_data["month"]
        month_date = date(raw_month.year, raw_month.month, 1)
        notes = form.cleaned_data.get("notes", "")

        employees = Employee.objects.for_garage(self.garage).filter(is_active=True)
        created_count = 0
        skipped_count = 0

        for emp in employees:
            if Payroll.objects.filter(employee=emp, month=month_date).exists():
                skipped_count += 1
                continue

            expense = Expense.objects.create(
                garage=self.garage,
                date=month_date,
                amount=emp.monthly_pay,
                category=Expense.CAT_SALARY,
                description=f"Salaire {emp.full_name} — {month_date.strftime('%B %Y')}",
                payment_method=Expense.METHOD_CASH,
                recorded_by=request.user,
            )
            Payroll.objects.create(
                garage=self.garage,
                employee=emp,
                month=month_date,
                amount=emp.monthly_pay,
                expense=expense,
                notes=notes,
            )
            created_count += 1

        msg = f"{created_count} bulletin(s) généré(s)"
        if skipped_count:
            msg += f", {skipped_count} déjà existant(s) ignoré(s)"
        messages.success(request, msg + ".")
        return redirect("employee_list")


class PayslipPrintView(GarageRequiredMixin, TemplateView):
    template_name = "hr/payslip_print.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        payroll = get_object_or_404(
            Payroll.objects.select_related("employee"),
            pk=self.kwargs["pk"],
            garage=self.garage,
        )
        ctx["payroll"] = payroll
        ctx["employee"] = payroll.employee
        ctx["garage"] = self.garage
        ctx["today"] = timezone.now().date()
        return ctx
