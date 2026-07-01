from django.db import models
from django.utils.text import slugify

from core.models import TimeStampedModel


class Garage(TimeStampedModel):
    """Un garage client de la plateforme SaaS = un tenant."""

    PLAN_CHOICES = [
        ("starter", "Starter"),
        ("pro", "Pro"),
        ("business", "Business"),
    ]

    name = models.CharField("Nom du garage", max_length=150)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    city = models.CharField("Ville", max_length=100, blank=True)
    phone = models.CharField("Téléphone", max_length=30, blank=True)
    whatsapp_number = models.CharField("Numéro WhatsApp", max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="starter")
    is_active = models.BooleanField(default=True)
    trial_ends_at = models.DateField(null=True, blank=True)

    logo = models.ImageField(
        "Logo",
        upload_to="garages/logos/",
        null=True,
        blank=True,
        help_text="Logo affiché dans l'interface du garage.",
    )

    ifu = models.CharField("IFU", max_length=50, blank=True, help_text="Identifiant Fiscal Unique")
    rccm = models.CharField("RCCM", max_length=50, blank=True, help_text="Registre du Commerce et du Crédit Mobilier")
    signature = models.ImageField(
        "Signature",
        upload_to="garages/signatures/",
        null=True,
        blank=True,
        help_text="Image de la signature (PNG transparent recommandé).",
    )
    cachet = models.ImageField(
        "Cachet / Tampon",
        upload_to="garages/cachets/",
        null=True,
        blank=True,
        help_text="Image du cachet ou tampon officiel.",
    )

    # Levier commercial : lien direct avec FAEST comme fournisseur intégré
    faest_supplier_enabled = models.BooleanField(
        "Approvisionnement FAEST activé",
        default=False,
        help_text="Permet à ce garage de commander des pièces directement via FAEST depuis la plateforme.",
    )

    class Meta:
        verbose_name = "Garage"
        verbose_name_plural = "Garages"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
