from django import forms

from .models import Part, Supplier

_INPUT = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500'


def _style(form):
    for field in form.fields.values():
        w = field.widget
        if not isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault('class', _INPUT + (' bg-white' if isinstance(w, forms.Select) else ''))


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'is_faest', 'phone', 'email', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = ['reference', 'name', 'category', 'supplier', 'unit_price', 'quantity_in_stock', 'alert_threshold']

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['supplier'].queryset = Supplier.objects.for_garage(garage)
        self.fields['supplier'].required = False
        _style(self)
