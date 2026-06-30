from django import forms

from .models import Employee, Payroll


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["first_name", "last_name", "post", "employee_type", "phone", "start_date", "monthly_pay", "is_active", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class PayrollForm(forms.Form):
    month = forms.DateField(
        widget=forms.DateInput(attrs={"type": "month"}),
        label="Mois de paie",
        input_formats=["%Y-%m"],
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Notes (optionnel)",
    )
