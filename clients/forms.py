from django import forms

from .models import Client, Vehicle

_INPUT = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500'


def _style(form):
    for field in form.fields.values():
        w = field.widget
        if not isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault('class', _INPUT + (' bg-white' if isinstance(w, forms.Select) else ''))


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['client_type', 'full_name', 'phone', 'whatsapp_number', 'email', 'address', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['client', 'plate_number', 'make', 'model', 'year', 'fuel_type', 'vin', 'mileage', 'color', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'year': forms.NumberInput(attrs={'min': 1970, 'max': 2030}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['client'].queryset = Client.objects.for_garage(garage)
        _style(self)
