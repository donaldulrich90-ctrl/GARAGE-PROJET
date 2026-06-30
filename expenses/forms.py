from django import forms

from accounts.models import User
from .models import Expense

_INPUT = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ("date", "category", "amount", "payment_method", "description", "employee")
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": _INPUT}),
            "category": forms.Select(attrs={"class": _INPUT}),
            "amount": forms.NumberInput(attrs={"class": _INPUT, "placeholder": "Montant en FCFA"}),
            "payment_method": forms.Select(attrs={"class": _INPUT}),
            "description": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Description (optionnel)"}),
            "employee": forms.Select(attrs={"class": _INPUT}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage is not None:
            self.fields["employee"].queryset = User.objects.filter(garage=garage)
        else:
            self.fields["employee"].queryset = User.objects.none()
        self.fields["employee"].required = False
        self.fields["employee"].empty_label = "— (non lié à un employé)"
