from django import forms
from django.contrib.auth.forms import UserCreationForm

from core.i18n import tr
from inventory.models import Supplier
from tenants.models import Garage
from .models import User

_INPUT = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"

STAFF_ROLE_CHOICES = [
    (User.ROLE_RECEPTION, "Réceptionniste"),
    (User.ROLE_MECHANIC, "Mécanicien"),
    (User.ROLE_CASHIER, "Caissier"),
    (User.ROLE_STOREKEEPER, "Magasinier"),
]


class GarageSettingsForm(forms.ModelForm):
    class Meta:
        model = Garage
        fields = ("name", "city", "address", "phone", "whatsapp_number", "email", "ifu", "rccm", "key_board_size", "logo", "signature", "cachet")
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT}),
            "city": forms.TextInput(attrs={"class": _INPUT}),
            "address": forms.TextInput(attrs={"class": _INPUT}),
            "phone": forms.TextInput(attrs={"class": _INPUT}),
            "whatsapp_number": forms.TextInput(attrs={"class": _INPUT}),
            "email": forms.EmailInput(attrs={"class": _INPUT}),
            "ifu": forms.TextInput(attrs={"class": _INPUT}),
            "rccm": forms.TextInput(attrs={"class": _INPUT}),
            "key_board_size": forms.NumberInput(attrs={"class": _INPUT, "min": 1}),
        }


class UserCreateForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=STAFF_ROLE_CHOICES,
        widget=forms.Select(attrs={"class": _INPUT}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role")
        widgets = {
            "username": forms.TextInput(attrs={"class": _INPUT}),
            "first_name": forms.TextInput(attrs={"class": _INPUT}),
            "last_name": forms.TextInput(attrs={"class": _INPUT}),
            "email": forms.EmailInput(attrs={"class": _INPUT}),
            "phone": forms.TextInput(attrs={"class": _INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("password1", "password2"):
            self.fields[field_name].widget.attrs["class"] = _INPUT


class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=STAFF_ROLE_CHOICES,
        widget=forms.Select(attrs={"class": _INPUT}),
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role")
        widgets = {
            "username": forms.TextInput(attrs={"class": _INPUT}),
            "first_name": forms.TextInput(attrs={"class": _INPUT}),
            "last_name": forms.TextInput(attrs={"class": _INPUT}),
            "email": forms.EmailInput(attrs={"class": _INPUT}),
            "phone": forms.TextInput(attrs={"class": _INPUT}),
        }


class SupplierUserCreateForm(UserCreationForm):
    """Crée en une seule opération la fiche fournisseur et son compte portail."""

    supplier_name = forms.CharField(label="Nom commercial", max_length=150)
    supplier_contact_name = forms.CharField(label="Personne à contacter", max_length=150, required=False)
    supplier_phone = forms.CharField(label="Téléphone fournisseur", max_length=30, required=False)
    supplier_email = forms.EmailField(label="Email fournisseur", required=False)
    supplier_city = forms.CharField(label="Ville", max_length=100, required=False)
    supplier_address = forms.CharField(label="Adresse", max_length=255, required=False)
    supplier_ifu = forms.CharField(label="IFU", max_length=50, required=False)
    supplier_rccm = forms.CharField(label="RCCM", max_length=50, required=False)
    supplier_website = forms.URLField(label="Site web", required=False)
    supplier_logo = forms.ImageField(label="Logo du fournisseur", required=False)
    supplier_notes = forms.CharField(
        label="Notes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")
        widgets = {
            "username": forms.TextInput(attrs={"class": _INPUT}),
            "first_name": forms.TextInput(attrs={"class": _INPUT}),
            "last_name": forms.TextInput(attrs={"class": _INPUT}),
            "email": forms.EmailInput(attrs={"class": _INPUT}),
            "phone": forms.TextInput(attrs={"class": _INPUT}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.garage = garage
        for field_name in ("password1", "password2"):
            self.fields[field_name].widget.attrs["class"] = _INPUT
        for field_name, field in self.fields.items():
            if field_name not in ("password1", "password2"):
                field.widget.attrs.setdefault("class", _INPUT)
        bilingual_labels = {
            "supplier_name": ("Nom commercial", "Business name"),
            "supplier_contact_name": ("Personne à contacter", "Contact person"),
            "supplier_phone": ("Téléphone fournisseur", "Supplier phone"),
            "supplier_email": ("Email fournisseur", "Supplier email"),
            "supplier_city": ("Ville", "City"),
            "supplier_address": ("Adresse", "Address"),
            "supplier_ifu": ("IFU", "Tax ID (IFU)"),
            "supplier_rccm": ("RCCM", "Business registry (RCCM)"),
            "supplier_website": ("Site web", "Website"),
            "supplier_logo": ("Logo du fournisseur", "Supplier logo"),
            "supplier_notes": ("Notes", "Notes"),
            "username": ("Identifiant", "Username"),
            "first_name": ("Prénom", "First name"),
            "last_name": ("Nom", "Last name"),
            "email": ("E-mail du compte", "Account email"),
            "phone": ("Téléphone du compte", "Account phone"),
            "password1": ("Mot de passe", "Password"),
            "password2": ("Confirmation du mot de passe", "Password confirmation"),
        }
        for field_name, texts in bilingual_labels.items():
            self.fields[field_name].label = tr(*texts)

    def clean_supplier_name(self):
        name = self.cleaned_data["supplier_name"].strip()
        if self.garage and Supplier.objects.filter(garage=self.garage, name__iexact=name).exists():
            raise forms.ValidationError(tr(
                "Un fournisseur portant ce nom existe déjà. Modifiez sa fiche au lieu de créer un doublon.",
                "A supplier with this name already exists. Edit that profile instead of creating a duplicate.",
            ))
        return name

    def save(self, garage, commit=True):
        supplier = Supplier(
            garage=garage,
            name=self.cleaned_data["supplier_name"],
            contact_name=self.cleaned_data.get("supplier_contact_name", ""),
            phone=self.cleaned_data.get("supplier_phone", ""),
            email=self.cleaned_data.get("supplier_email", ""),
            city=self.cleaned_data.get("supplier_city", ""),
            address=self.cleaned_data.get("supplier_address", ""),
            ifu=self.cleaned_data.get("supplier_ifu", ""),
            rccm=self.cleaned_data.get("supplier_rccm", ""),
            website=self.cleaned_data.get("supplier_website", ""),
            logo=self.cleaned_data.get("supplier_logo"),
            notes=self.cleaned_data.get("supplier_notes", ""),
        )
        user = super().save(commit=False)
        user.garage = None
        user.role = User.ROLE_SUPPLIER
        user.is_staff = False
        user.is_superuser = False
        if commit:
            supplier.save()
            user.supplier = supplier
            user.save()
        else:
            user.supplier = supplier
        return user


class AdminSetPasswordForm(forms.Form):
    password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={"class": _INPUT}),
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={"class": _INPUT}),
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned
