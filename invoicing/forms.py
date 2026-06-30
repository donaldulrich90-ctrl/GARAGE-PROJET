from django import forms
from django.forms import inlineformset_factory

from inventory.models import Part
from .models import Payment, ProformaInvoice, ProformaInvoiceLine

_INPUT = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#FFCD11]"
_SELECT = _INPUT + " bg-white"


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "method", "note"]
        widgets = {"note": forms.TextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            w.attrs.setdefault("class", _INPUT + (" bg-white" if isinstance(w, forms.Select) else ""))


class ProformaForm(forms.ModelForm):
    class Meta:
        model = ProformaInvoice
        fields = ("client", "client_name", "notes")
        widgets = {
            "client": forms.Select(attrs={"class": _SELECT}),
            "client_name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ou saisir un nom libre"}),
            "notes": forms.Textarea(attrs={"class": _INPUT, "rows": 2, "placeholder": "Remarques, conditions…"}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            from clients.models import Client
            self.fields["client"].queryset = Client.objects.for_garage(garage).order_by("full_name")
        self.fields["client"].required = False
        self.fields["client"].empty_label = "— Sélectionner un client —"
        self.fields["client_name"].required = False

    def clean(self):
        cd = super().clean()
        if not cd.get("client") and not cd.get("client_name"):
            raise forms.ValidationError("Indiquez un client existant ou saisissez un nom.")
        return cd


class ProformaLineForm(forms.ModelForm):
    class Meta:
        model = ProformaInvoiceLine
        fields = ("part", "description", "quantity", "unit_price")
        widgets = {
            "part": forms.Select(attrs={"class": _SELECT + " part-select"}),
            "description": forms.TextInput(attrs={"class": _INPUT}),
            "quantity": forms.NumberInput(attrs={"class": _INPUT, "min": 1}),
            "unit_price": forms.NumberInput(attrs={"class": _INPUT, "step": "1", "min": 0}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields["part"].queryset = Part.objects.for_garage(garage).order_by("reference")
        self.fields["part"].required = False
        self.fields["part"].empty_label = "— Article libre (sans stock) —"
        self.fields["description"].required = True

    def clean(self):
        cd = super().clean()
        if cd.get("part") and not cd.get("description"):
            cd["description"] = str(cd["part"])
        return cd


ProformaLineFormSet = inlineformset_factory(
    ProformaInvoice,
    ProformaInvoiceLine,
    form=ProformaLineForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
