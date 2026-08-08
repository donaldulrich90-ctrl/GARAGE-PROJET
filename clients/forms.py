from django import forms

from catalog.models import VehicleMake, VehicleModel

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
        fields = [
            'client', 'plate_number',
            'make_ref', 'model_ref',
            'make', 'model',
            'year', 'fuel_type',
            'vin', 'mileage', 'color',
            'is_in_garage', 'stored_since', 'notes',
        ]
        help_texts = {
            'is_in_garage': "Le n° du tableau à clés est attribué et libéré automatiquement selon cette case.",
        }
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'year': forms.NumberInput(attrs={'min': 1970, 'max': 2030}),
            'stored_since': forms.DateInput(attrs={'type': 'date'}),
            'make': forms.TextInput(attrs={'placeholder': "Optionnel si la marque catalogue est choisie"}),
            'model': forms.TextInput(attrs={'placeholder': "Optionnel si le modèle catalogue est choisi"}),
        }
        labels = {
            'make_ref': "Marque (catalogue)",
            'model_ref': "Modèle (catalogue)",
            'make': "Marque libre",
            'model': "Modèle libre",
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['client'].queryset = Client.objects.for_garage(garage)

        # Le champ catalogue est prioritaire ; les champs libres deviennent optionnels.
        self.fields['make'].required = False
        self.fields['model'].required = False
        self.fields['make_ref'].queryset = VehicleMake.objects.all().order_by('name')
        self.fields['make_ref'].required = False
        self.fields['model_ref'].required = False

        # Restreindre les modèles à la marque déjà choisie (POST ou instance).
        make_id = None
        if self.data.get('make_ref'):
            try:
                make_id = int(self.data.get('make_ref'))
            except (TypeError, ValueError):
                make_id = None
        elif self.instance and self.instance.make_ref_id:
            make_id = self.instance.make_ref_id

        if make_id:
            self.fields['model_ref'].queryset = VehicleModel.objects.filter(make_id=make_id).order_by('name')
        else:
            self.fields['model_ref'].queryset = VehicleModel.objects.none()

        # Ajouter data-make pour permettre le filtrage JS côté client.
        model_choices = [('', '---------')]
        for m in VehicleModel.objects.all().select_related('make').order_by('make__name', 'name'):
            model_choices.append((m.pk, f"{m.name}"))
        # On garde le queryset ci-dessus pour la validation ; le JS gérera l'affichage.
        _style(self)
        # Attributs data-* pour le JS de cascade côté template.
        self.fields['make_ref'].widget.attrs['data-role'] = 'make-select'
        self.fields['model_ref'].widget.attrs['data-role'] = 'model-select'

    def clean(self):
        cleaned = super().clean()
        # Au moins une source pour la marque/modèle doit être renseignée.
        if not cleaned.get('make_ref') and not cleaned.get('make'):
            self.add_error('make_ref', "Choisissez une marque du catalogue ou saisissez une marque libre.")
        if not cleaned.get('model_ref') and not cleaned.get('model'):
            self.add_error('model_ref', "Choisissez un modèle du catalogue ou saisissez un modèle libre.")
        # Le modèle doit correspondre à la marque du catalogue si les deux sont choisis.
        make_ref = cleaned.get('make_ref')
        model_ref = cleaned.get('model_ref')
        if make_ref and model_ref and model_ref.make_id != make_ref.pk:
            self.add_error('model_ref', "Le modèle choisi n'appartient pas à cette marque.")
        return cleaned
