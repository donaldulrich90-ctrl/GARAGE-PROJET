from django import forms

from .models import WorkshopSection

_INPUT = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400'


def _style(form):
    for field in form.fields.values():
        w = field.widget
        if not isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault('class', _INPUT + (' bg-white' if isinstance(w, forms.Select) else ''))


class WorkshopSectionForm(forms.ModelForm):
    class Meta:
        model = WorkshopSection
        fields = ['name', 'code', 'description', 'icon', 'color', 'is_active', 'display_order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.garage = garage
        self.fields['description'].required = False
        self.fields['icon'].required = False
        _style(self)

    def validate_unique(self):
        super().validate_unique()

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get('code')
        if code and self.garage:
            qs = WorkshopSection.objects.filter(garage=self.garage, code=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('code', f'Une section avec le code « {code} » existe déjà dans ce garage.')
        return cleaned
