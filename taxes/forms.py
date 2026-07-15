from django import forms

from clients.models import Vehicle

from .models import VehicleTax


class VehicleTaxForm(forms.ModelForm):
    class Meta:
        model = VehicleTax
        fields = [
            'vehicle', 'tax_type', 'description', 'fiscal_year',
            'amount', 'due_date', 'payment_date', 'is_paid',
            'receipt_number', 'notes', 'document',
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'description': forms.TextInput(),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['vehicle'].queryset = Vehicle.objects.for_garage(garage)
        self.fields['vehicle'].label = 'Véhicule'
        self.fields['amount'].label = 'Montant (FCFA)'
        self.fields['payment_date'].required = False
        self.fields['receipt_number'].required = False
        self.fields['description'].required = False
        self.fields['document'].required = False
