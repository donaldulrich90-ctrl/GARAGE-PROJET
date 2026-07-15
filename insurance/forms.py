from django import forms

from clients.models import Vehicle

from .models import Insurance, InsuranceClaim


class InsuranceForm(forms.ModelForm):
    class Meta:
        model = Insurance
        fields = [
            'vehicle', 'insurance_company', 'policy_number', 'insurance_type',
            'start_date', 'end_date', 'premium_amount',
            'coverage_details', 'agent_name', 'agent_phone', 'document',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'coverage_details': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['vehicle'].queryset = Vehicle.objects.for_garage(garage)
        self.fields['vehicle'].label = 'Véhicule'
        self.fields['premium_amount'].label = 'Prime (FCFA)'


class InsuranceClaimForm(forms.ModelForm):
    class Meta:
        model = InsuranceClaim
        fields = [
            'claim_number', 'claim_date', 'claim_type', 'description',
            'estimated_cost', 'approved_amount', 'status', 'repair_order',
            'documents', 'notes',
        ]
        widgets = {
            'claim_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            from repair_orders.models import RepairOrder
            self.fields['repair_order'].queryset = RepairOrder.objects.for_garage(garage)
        self.fields['repair_order'].required = False
        self.fields['approved_amount'].required = False
        self.fields['estimated_cost'].label = 'Coût estimé (FCFA)'
        self.fields['approved_amount'].label = 'Montant approuvé (FCFA)'
