from django import forms

from core.i18n import tr
from .models import ChatMessage


class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["body", "image"]
        widgets = {
            "body": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Votre message…",
                "class": "flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none",
            }),
            "image": forms.ClearableFileInput(attrs={
                "accept": "image/*",
                "class": "text-xs",
            }),
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("body") and not cleaned.get("image"):
            raise forms.ValidationError(tr(
                "Écris un message ou joins une photo.",
                "Write a message or attach a photo.",
            ))
        return cleaned
