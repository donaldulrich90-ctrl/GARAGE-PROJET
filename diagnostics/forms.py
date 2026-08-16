from django import forms
from django.forms import inlineformset_factory

from accounts.models import User

from .models import DiagnosticCode, DiagnosticReport

_INPUT = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400'


def _style(form):
    for field in form.fields.values():
        w = field.widget
        if not isinstance(w, (forms.CheckboxInput, forms.FileInput)):
            w.attrs.setdefault('class', _INPUT + (' bg-white' if isinstance(w, forms.Select) else ''))


class DiagnosticReportForm(forms.ModelForm):
    class Meta:
        model = DiagnosticReport
        fields = [
            'scan_date', 'mileage', 'scanner_name', 'technician',
            'summary', 'observations', 'recommendations', 'original_file',
        ]
        widgets = {
            'scan_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'summary': forms.Textarea(attrs={'rows': 3}),
            'observations': forms.Textarea(attrs={'rows': 4}),
            'recommendations': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if garage:
            self.fields['technician'].queryset = User.objects.filter(
                garage=garage,
                role__in=[User.ROLE_MECHANIC, User.ROLE_ADMIN],
            )
        self.fields['technician'].required = False
        self.fields['mileage'].required = False
        self.fields['scanner_name'].required = False
        self.fields['summary'].required = False
        self.fields['observations'].required = False
        self.fields['recommendations'].required = False
        self.fields['original_file'].required = False
        _style(self)


class DiagnosticCodeForm(forms.ModelForm):
    class Meta:
        model = DiagnosticCode
        fields = ['code', 'module_system', 'description', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


DiagnosticCodeFormSet = inlineformset_factory(
    DiagnosticReport,
    DiagnosticCode,
    form=DiagnosticCodeForm,
    extra=1,
    can_delete=True,
)
