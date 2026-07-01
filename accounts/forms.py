from django import forms
from django.contrib.auth.forms import UserCreationForm

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
        fields = ("name", "city", "address", "phone", "whatsapp_number", "email", "ifu", "rccm", "logo", "signature", "cachet")
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT}),
            "city": forms.TextInput(attrs={"class": _INPUT}),
            "address": forms.TextInput(attrs={"class": _INPUT}),
            "phone": forms.TextInput(attrs={"class": _INPUT}),
            "whatsapp_number": forms.TextInput(attrs={"class": _INPUT}),
            "email": forms.EmailInput(attrs={"class": _INPUT}),
            "ifu": forms.TextInput(attrs={"class": _INPUT}),
            "rccm": forms.TextInput(attrs={"class": _INPUT}),
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
