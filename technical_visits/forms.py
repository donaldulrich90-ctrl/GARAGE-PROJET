from django import forms

from clients.models import Vehicle

from .models import TechnicalVisit


class TechnicalVisitForm(forms.ModelForm):
    class Meta:
        model = TechnicalVisit
        fields = [
            'vehicle', 'visit_type', 'visit_date', 'expiry_date',
            'result', 'inspection_center', 'certificate_number',
            'observations', 'cost', 'document',
        ]
        widgets = {
            'visit_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'observations': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['vehicle'].queryset = Vehicle.objects.for_garage(garage)
        self.fields['vehicle'].label = 'Véhicule'
        self.fields['cost'].label = 'Coût (FCFA)'
