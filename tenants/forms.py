from django import forms

from .models import Garage

_INPUT = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#FFCD11]"
_SELECT = _INPUT + " bg-white"


class GarageCreateForm(forms.Form):
    # Informations du garage
    name = forms.CharField(max_length=150, label="Nom du garage", widget=forms.TextInput(attrs={"class": _INPUT}))
    city = forms.CharField(max_length=100, required=False, label="Ville", widget=forms.TextInput(attrs={"class": _INPUT}))
    phone = forms.CharField(max_length=30, required=False, label="Téléphone", widget=forms.TextInput(attrs={"class": _INPUT}))
    whatsapp_number = forms.CharField(max_length=30, required=False, label="WhatsApp", widget=forms.TextInput(attrs={"class": _INPUT}))
    email = forms.EmailField(required=False, label="Email", widget=forms.EmailInput(attrs={"class": _INPUT}))
    address = forms.CharField(max_length=255, required=False, label="Adresse", widget=forms.TextInput(attrs={"class": _INPUT}))
    plan = forms.ChoiceField(choices=Garage.PLAN_CHOICES, label="Plan", widget=forms.Select(attrs={"class": _SELECT}))
    trial_ends_at = forms.DateField(
        required=False, label="Fin de période d'essai",
        widget=forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
    )
    faest_supplier_enabled = forms.BooleanField(required=False, label="Approvisionnement FAEST activé")

    # Compte administrateur du garage
    admin_username = forms.CharField(max_length=150, label="Identifiant admin", widget=forms.TextInput(attrs={"class": _INPUT}))
    admin_first_name = forms.CharField(max_length=150, required=False, label="Prénom admin", widget=forms.TextInput(attrs={"class": _INPUT}))
    admin_last_name = forms.CharField(max_length=150, required=False, label="Nom admin", widget=forms.TextInput(attrs={"class": _INPUT}))
    admin_password = forms.CharField(
        min_length=8, label="Mot de passe admin",
        widget=forms.PasswordInput(attrs={"class": _INPUT}),
    )

    def clean_admin_username(self):
        from accounts.models import User
        username = self.cleaned_data["admin_username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username


class GarageEditForm(forms.ModelForm):
    class Meta:
        model = Garage
        fields = (
            "name", "city", "address", "phone", "whatsapp_number", "email",
            "plan", "is_active", "trial_ends_at", "faest_supplier_enabled", "logo",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT}),
            "city": forms.TextInput(attrs={"class": _INPUT}),
            "address": forms.TextInput(attrs={"class": _INPUT}),
            "phone": forms.TextInput(attrs={"class": _INPUT}),
            "whatsapp_number": forms.TextInput(attrs={"class": _INPUT}),
            "email": forms.EmailInput(attrs={"class": _INPUT}),
            "plan": forms.Select(attrs={"class": _SELECT}),
            "trial_ends_at": forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
        }
