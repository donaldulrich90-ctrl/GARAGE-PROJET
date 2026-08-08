from django import forms

from catalog.models import CatalogPart
from inventory.models import Supplier, SupplierPart, SupplierStockMovement

_INPUT = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"


def _style(form):
    for field in form.fields.values():
        w = field.widget
        if not isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault("class", _INPUT + (" bg-white" if isinstance(w, forms.Select) else ""))


class SupplierProfileForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "phone", "email", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class SupplierPartOwnForm(forms.ModelForm):
    """Formulaire utilisé par le fournisseur pour ajouter/éditer une de ses offres."""

    class Meta:
        model = SupplierPart
        fields = ["catalog_part", "g_code", "unit_price", "quantity_available", "lead_time_days", "supplier_reference", "notes"]
        help_texts = {
            "g_code": "Code OEM / fabricant obligatoire — garantit la compatibilité de la pièce lors de l'achat.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["catalog_part"].queryset = CatalogPart.objects.select_related("category").order_by("name")
        self.fields["g_code"].required = True
        _style(self)

    def clean_g_code(self):
        g = (self.cleaned_data.get("g_code") or "").strip().upper()
        if not g:
            raise forms.ValidationError("Le G-CODE est obligatoire.")
        return g


class SupplierStockMovementForm(forms.ModelForm):
    class Meta:
        model = SupplierStockMovement
        fields = ["supplier_part", "movement_type", "quantity", "unit_price", "destination_garage", "reason"]

    def __init__(self, *args, supplier=None, **kwargs):
        super().__init__(*args, **kwargs)
        if supplier:
            self.fields["supplier_part"].queryset = SupplierPart.objects.filter(supplier=supplier).select_related("catalog_part").order_by("catalog_part__name")
        self.fields["destination_garage"].required = False
        _style(self)

    def clean_quantity(self):
        q = self.cleaned_data["quantity"]
        if q < 0:
            raise forms.ValidationError("La quantité doit être positive.")
        return q


class OrderRejectionForm(forms.Form):
    reason = forms.CharField(
        label="Motif de rejet",
        widget=forms.Textarea(attrs={"class": _INPUT, "rows": 2, "placeholder": "Rupture de stock, tarif révisé, …"}),
        max_length=200,
        required=True,
    )
