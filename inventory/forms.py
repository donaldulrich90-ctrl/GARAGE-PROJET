from django import forms

from catalog.models import CatalogPart

from .models import Part, Supplier, SupplierPart

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
        fields = ['catalog_part', 'reference', 'name', 'category', 'supplier', 'unit_price', 'quantity_in_stock', 'alert_threshold']
        help_texts = {
            'catalog_part': "Optionnel : lier la pièce à une fiche catalogue partagée.",
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['supplier'].queryset = Supplier.objects.all()
        self.fields['supplier'].required = False
        self.fields['catalog_part'].required = False
        self.fields['catalog_part'].queryset = CatalogPart.objects.select_related('category').order_by('name')
        _style(self)


# SupplierPartForm retire : la creation/edition d'offres est desormais reservee
# au portail fournisseur (voir supplier_portal.forms.SupplierPartOwnForm).
