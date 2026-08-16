from django import forms

from accounts.models import User
from clients.models import Client, Vehicle
from inventory.models import Part
from workshops.models import WorkshopSection

from .models import RepairOrder, RepairOrderPart, RepairOrderTask

_INPUT = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500'


def _style(form):
    for field in form.fields.values():
        w = field.widget
        if not isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault('class', _INPUT + (' bg-white' if isinstance(w, forms.Select) else ''))


class RepairOrderForm(forms.ModelForm):
    class Meta:
        model = RepairOrder
        fields = [
            'vehicle', 'client', 'assigned_mechanic', 'status',
            'mileage_at_reception', 'client_complaint', 'diagnosis_notes', 'expected_at',
        ]
        widgets = {
            'client_complaint': forms.Textarea(attrs={'rows': 3}),
            'diagnosis_notes': forms.Textarea(attrs={'rows': 3}),
            'expected_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['vehicle'].queryset = Vehicle.objects.for_garage(garage).select_related('client')
            self.fields['client'].queryset = Client.objects.for_garage(garage)
            self.fields['assigned_mechanic'].queryset = User.objects.filter(
                garage=garage, role=User.ROLE_MECHANIC
            )
        self.fields['assigned_mechanic'].required = False
        self.fields['expected_at'].required = False
        self.fields['diagnosis_notes'].required = False
        _style(self)


class RepairOrderTaskForm(forms.ModelForm):
    class Meta:
        model = RepairOrderTask
        fields = ['description', 'section', 'mechanic', 'cost', 'is_done']

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['section'].queryset = WorkshopSection.objects.for_garage(garage).filter(is_active=True)
            self.fields['mechanic'].queryset = User.objects.filter(
                garage=garage, role__in=[User.ROLE_MECHANIC, User.ROLE_ADMIN]
            )
        self.fields['mechanic'].required = False
        self.fields['section'].required = True
        self.fields['section'].empty_label = '— Choisir une section —'
        _style(self)

    def clean_section(self):
        section = self.cleaned_data.get('section')
        if not section:
            raise forms.ValidationError('La section est obligatoire pour toute nouvelle tâche.')
        return section


class RepairOrderPartForm(forms.ModelForm):
    class Meta:
        model = RepairOrderPart
        fields = ['part', 'quantity', 'unit_price', 'section']

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['part'].queryset = Part.objects.for_garage(garage)
            self.fields['section'].queryset = WorkshopSection.objects.for_garage(garage).filter(is_active=True)
        self.fields['unit_price'].required = False
        self.fields['unit_price'].help_text = "Laissez vide pour utiliser le prix catalogue."
        self.fields['section'].required = True
        self.fields['section'].empty_label = '— Choisir une section —'
        _style(self)

    def clean_section(self):
        section = self.cleaned_data.get('section')
        if not section:
            raise forms.ValidationError('La section est obligatoire pour toute nouvelle pièce.')
        return section
