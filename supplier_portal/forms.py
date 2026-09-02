from django import forms

from catalog.models import CatalogPart
from core.i18n import (
    EXPENSE_CATEGORY_LABELS,
    MOVEMENT_LABELS,
    PAYMENT_LABELS,
    tr,
    translated_choices,
)
from inventory.models import Supplier, SupplierExpense, SupplierPart, SupplierStockMovement

_INPUT = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"


def _style(form):
    for field in form.fields.values():
        w = field.widget
        if not isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault("class", _INPUT + (" bg-white" if isinstance(w, forms.Select) else ""))


def _translate_labels(form, labels):
    for field_name, texts in labels.items():
        if field_name in form.fields:
            form.fields[field_name].label = tr(*texts)


class SupplierProfileForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name", "contact_name", "phone", "email", "city", "address",
            "ifu", "rccm", "website", "logo", "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _translate_labels(self, {
            "name": ("Nom commercial", "Business name"),
            "contact_name": ("Personne à contacter", "Contact person"),
            "phone": ("Téléphone", "Phone"),
            "email": ("E-mail", "Email"),
            "city": ("Ville", "City"),
            "address": ("Adresse", "Address"),
            "ifu": ("IFU", "Tax ID (IFU)"),
            "rccm": ("RCCM", "Business registry (RCCM)"),
            "website": ("Site web", "Website"),
            "logo": ("Logo", "Logo"),
            "notes": ("Notes", "Notes"),
        })
        _style(self)


class SupplierPartOwnForm(forms.ModelForm):
    """Formulaire utilisé par le fournisseur pour ajouter/éditer une de ses offres."""

    class Meta:
        model = SupplierPart
        fields = [
            "catalog_part", "g_code", "unit_price", "quantity_available",
            "alert_threshold", "lead_time_days", "supplier_reference", "notes",
        ]
        help_texts = {
            "g_code": "Code OEM / fabricant obligatoire — garantit la compatibilité de la pièce lors de l'achat.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["catalog_part"].queryset = CatalogPart.objects.select_related("category").order_by("name")
        self.fields["g_code"].required = True
        _translate_labels(self, {
            "catalog_part": ("Pièce du catalogue", "Catalog part"),
            "g_code": ("G-CODE (compatibilité)", "G-CODE (compatibility)"),
            "unit_price": ("Prix fournisseur (FCFA)", "Supplier price (FCFA)"),
            "quantity_available": ("Quantité disponible", "Available quantity"),
            "alert_threshold": ("Seuil d'alerte", "Alert threshold"),
            "lead_time_days": ("Délai de livraison (jours)", "Lead time (days)"),
            "supplier_reference": ("Référence interne", "Internal reference"),
            "notes": ("Notes", "Notes"),
        })
        self.fields["g_code"].help_text = tr(
            "Code OEM / fabricant obligatoire — garantit la compatibilité de la pièce lors de l'achat.",
            "Required OEM/manufacturer code used to guarantee part compatibility.",
        )
        _style(self)

    def clean_g_code(self):
        g = (self.cleaned_data.get("g_code") or "").strip().upper()
        if not g:
            raise forms.ValidationError(tr("Le G-CODE est obligatoire.", "G-CODE is required."))
        return g


class SupplierStockMovementForm(forms.ModelForm):
    class Meta:
        model = SupplierStockMovement
        fields = [
            "supplier_part", "movement_type", "quantity", "unit_price",
            "sale_reference", "customer_name", "destination_garage",
            "payment_method", "reason",
        ]

    def __init__(self, *args, supplier=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.supplier = supplier
        if supplier:
            self.fields["supplier_part"].queryset = SupplierPart.objects.filter(supplier=supplier).select_related("catalog_part").order_by("catalog_part__name")
        self.fields["destination_garage"].required = False
        self.fields["sale_reference"].required = False
        self.fields["customer_name"].required = False
        self.fields["payment_method"].required = False
        self.fields["movement_type"].choices = translated_choices(MOVEMENT_LABELS)
        self.fields["payment_method"].choices = [("", "---------")] + translated_choices(PAYMENT_LABELS)
        _translate_labels(self, {
            "supplier_part": ("Pièce fournisseur", "Supplier part"),
            "movement_type": ("Type de mouvement", "Movement type"),
            "quantity": ("Quantité", "Quantity"),
            "unit_price": ("Prix appliqué (FCFA)", "Applied price (FCFA)"),
            "sale_reference": ("Référence de vente", "Sale reference"),
            "customer_name": ("Client / Acheteur", "Customer / Buyer"),
            "destination_garage": ("Garage destinataire", "Destination garage"),
            "payment_method": ("Mode de paiement", "Payment method"),
            "reason": ("Motif / Observation", "Reason / Notes"),
        })
        _style(self)

    def clean_quantity(self):
        q = self.cleaned_data["quantity"]
        if q <= 0:
            raise forms.ValidationError(tr(
                "La quantité doit être supérieure à zéro.",
                "Quantity must be greater than zero.",
            ))
        return q

    def clean(self):
        cleaned = super().clean()
        part = cleaned.get("supplier_part")
        movement_type = cleaned.get("movement_type")
        quantity = cleaned.get("quantity")
        unit_price = cleaned.get("unit_price")

        if part and self.supplier and part.supplier_id != self.supplier.pk:
            self.add_error("supplier_part", tr(
                "Cette pièce n'appartient pas à votre compte fournisseur.",
                "This part does not belong to your supplier account.",
            ))
        if movement_type == SupplierStockMovement.MOVEMENT_OUT:
            if part and quantity and part.quantity_available < quantity:
                self.add_error("quantity", tr(
                    f"Stock disponible : {part.quantity_available}.",
                    f"Available stock: {part.quantity_available}.",
                ))
            if unit_price is None or unit_price <= 0:
                self.add_error("unit_price", tr(
                    "Le prix de vente doit être supérieur à zéro.",
                    "Sale price must be greater than zero.",
                ))
            if not cleaned.get("customer_name") and not cleaned.get("destination_garage"):
                self.add_error("customer_name", tr(
                    "Indiquez le client ou choisissez un garage destinataire.",
                    "Enter a customer or select a destination garage.",
                ))
            if not cleaned.get("payment_method"):
                self.add_error("payment_method", tr(
                    "Indiquez le mode de paiement.",
                    "Select a payment method.",
                ))
        return cleaned


class SupplierExpenseForm(forms.ModelForm):
    class Meta:
        model = SupplierExpense
        fields = [
            "date", "category", "amount", "payment_method",
            "reference", "description", "receipt",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(attrs={"placeholder": "Objet de la dépense"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = translated_choices(EXPENSE_CATEGORY_LABELS)
        self.fields["payment_method"].choices = translated_choices(PAYMENT_LABELS)
        self.fields["description"].widget.attrs["placeholder"] = tr(
            "Objet de la dépense", "Expense purpose"
        )
        _translate_labels(self, {
            "date": ("Date", "Date"),
            "category": ("Catégorie", "Category"),
            "amount": ("Montant (FCFA)", "Amount (FCFA)"),
            "payment_method": ("Mode de paiement", "Payment method"),
            "reference": ("Référence", "Reference"),
            "description": ("Description", "Description"),
            "receipt": ("Justificatif", "Receipt"),
        })
        _style(self)


class OrderRejectionForm(forms.Form):
    reason = forms.CharField(
        label="Motif de rejet",
        widget=forms.Textarea(attrs={"class": _INPUT, "rows": 2, "placeholder": "Rupture de stock, tarif révisé, …"}),
        max_length=200,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].label = tr("Motif de rejet", "Rejection reason")
        self.fields["reason"].widget.attrs["placeholder"] = tr(
            "Rupture de stock, tarif révisé, …",
            "Out of stock, updated price, …",
        )
