from django import forms

from .features import FEATURES
from .models import Garage

_INPUT = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#FFCD11]"
_SELECT = _INPUT + " bg-white"

# Choix tri-état pour chaque option : suit le plan, forcé activé, forcé désactivé.
_FEAT_CHOICES = [("auto", "Selon le plan"), ("on", "Activé"), ("off", "Désactivé")]
_FEAT_SELECT = ("border border-gray-300 rounded-lg px-2 py-1 text-xs bg-white "
                "focus:outline-none focus:ring-2 focus:ring-[#FFCD11]")


class _FeatureFieldsMixin:
    """Ajoute un champ tri-état par option (feat_<clé>) et calcule les surcharges."""

    def add_feature_fields(self, overrides=None):
        overrides = overrides or {}
        for key, label in FEATURES.items():
            initial = "auto"
            if key in overrides:
                initial = "on" if overrides[key] else "off"
            self.fields[f"feat_{key}"] = forms.ChoiceField(
                label=label,
                required=False,
                choices=_FEAT_CHOICES,
                initial=initial,
                widget=forms.Select(attrs={"class": _FEAT_SELECT}),
            )

    def get_feature_overrides(self):
        overrides = {}
        for key in FEATURES:
            val = self.cleaned_data.get(f"feat_{key}", "auto")
            if val == "on":
                overrides[key] = True
            elif val == "off":
                overrides[key] = False
            # "auto" -> on n'enregistre rien (on suit le plan)
        return overrides


_METIER_CHECK = "h-4 w-4 rounded accent-[#FFCD11]"


class _MetierFieldsMixin:
    """Ajoute une case a cocher par metier (section d'atelier) : metier_<CODE>."""

    def add_metier_fields(self, garage=None):
        from workshops.models import DEFAULT_SECTIONS, WorkshopSection
        has_sections = False
        active_codes = set()
        if garage is not None and getattr(garage, "pk", None):
            qs = WorkshopSection.objects.filter(garage=garage)
            has_sections = qs.exists()
            active_codes = set(qs.filter(is_active=True).values_list("code", flat=True))
        for code, name, color, icon, order in DEFAULT_SECTIONS:
            # Creation (aucune section encore) : tout coche par defaut.
            # Edition : suit l'etat actif de la section existante.
            initial = True if not has_sections else (code in active_codes)
            self.fields[f"metier_{code}"] = forms.BooleanField(
                label=f"{icon} {name}",
                required=False,
                initial=initial,
                widget=forms.CheckboxInput(attrs={"class": _METIER_CHECK}),
            )

    def get_active_metiers(self):
        from workshops.models import DEFAULT_SECTIONS
        return {
            code for code, *_rest in DEFAULT_SECTIONS
            if self.cleaned_data.get(f"metier_{code}")
        }


class GarageCreateForm(_FeatureFieldsMixin, _MetierFieldsMixin, forms.Form):
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
    ifu = forms.CharField(max_length=50, required=False, label="IFU", widget=forms.TextInput(attrs={"class": _INPUT}))
    rccm = forms.CharField(max_length=50, required=False, label="RCCM", widget=forms.TextInput(attrs={"class": _INPUT}))
    signature = forms.ImageField(required=False, label="Signature")
    cachet = forms.ImageField(required=False, label="Cachet / Tampon")
    faest_supplier_enabled = forms.BooleanField(required=False, label="Approvisionnement FAEST activé")

    # Compte administrateur du garage
    admin_username = forms.CharField(max_length=150, label="Identifiant admin", widget=forms.TextInput(attrs={"class": _INPUT}))
    admin_first_name = forms.CharField(max_length=150, required=False, label="Prénom admin", widget=forms.TextInput(attrs={"class": _INPUT}))
    admin_last_name = forms.CharField(max_length=150, required=False, label="Nom admin", widget=forms.TextInput(attrs={"class": _INPUT}))
    admin_password = forms.CharField(
        min_length=8, label="Mot de passe admin",
        widget=forms.PasswordInput(attrs={"class": _INPUT}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_feature_fields()
        self.add_metier_fields()

    def clean_admin_username(self):
        from accounts.models import User
        username = self.cleaned_data["admin_username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username


class GarageEditForm(_FeatureFieldsMixin, _MetierFieldsMixin, forms.ModelForm):
    class Meta:
        model = Garage
        fields = (
            "name", "city", "address", "phone", "whatsapp_number", "email",
            "ifu", "rccm",
            "plan", "is_active", "trial_ends_at", "faest_supplier_enabled",
            "logo", "signature", "cachet",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT}),
            "city": forms.TextInput(attrs={"class": _INPUT}),
            "address": forms.TextInput(attrs={"class": _INPUT}),
            "phone": forms.TextInput(attrs={"class": _INPUT}),
            "whatsapp_number": forms.TextInput(attrs={"class": _INPUT}),
            "email": forms.EmailInput(attrs={"class": _INPUT}),
            "ifu": forms.TextInput(attrs={"class": _INPUT}),
            "rccm": forms.TextInput(attrs={"class": _INPUT}),
            "plan": forms.Select(attrs={"class": _SELECT}),
            "trial_ends_at": forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        overrides = self.instance.feature_overrides if self.instance and self.instance.pk else None
        self.add_feature_fields(overrides)
        self.add_metier_fields(self.instance)

    def save(self, commit=True):
        garage = super().save(commit=False)
        garage.feature_overrides = self.get_feature_overrides()
        if commit:
            garage.save()
        return garage
