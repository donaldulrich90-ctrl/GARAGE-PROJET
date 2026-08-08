"""
Catalogue de référence partagé entre tous les garages.

Ces données ne sont PAS scopées par tenant : on met en commun la connaissance
des marques, modèles et pièces standards. Chaque garage y pioche ensuite pour
enregistrer ses véhicules et alimenter son stock.
"""
from django.db import models
from django.utils.text import slugify

from core.models import TimeStampedModel


class VehicleMake(TimeStampedModel):
    name = models.CharField("Marque", max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    logo = models.ImageField("Logo", upload_to="catalog/makes/", null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Marque de véhicule"
        verbose_name_plural = "Marques de véhicules"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class VehicleModel(TimeStampedModel):
    make = models.ForeignKey(
        VehicleMake, on_delete=models.CASCADE, related_name="models",
    )
    name = models.CharField("Modèle", max_length=80)
    slug = models.SlugField(max_length=80, blank=True)
    year_from = models.PositiveIntegerField("Année début", null=True, blank=True)
    year_to = models.PositiveIntegerField("Année fin", null=True, blank=True)

    class Meta:
        ordering = ["make__name", "name"]
        verbose_name = "Modèle de véhicule"
        verbose_name_plural = "Modèles de véhicules"
        constraints = [
            models.UniqueConstraint(
                fields=["make", "slug"], name="unique_model_slug_per_make",
            ),
        ]

    def __str__(self):
        return f"{self.make.name} {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PartCategory(TimeStampedModel):
    name = models.CharField("Catégorie", max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Catégorie de pièce"
        verbose_name_plural = "Catégories de pièces"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CatalogPart(TimeStampedModel):
    """
    Fiche pièce de référence. Une même pièce peut être compatible avec
    plusieurs modèles. Chaque garage/fournisseur y rattache ensuite son
    propre prix / stock.
    """

    reference = models.CharField(
        "Référence catalogue", max_length=100, unique=True,
        help_text="Référence unique (OEM, EAN ou code interne).",
    )
    name = models.CharField("Désignation", max_length=200)
    category = models.ForeignKey(
        PartCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="parts",
    )
    compatible_models = models.ManyToManyField(
        VehicleModel, blank=True, related_name="compatible_parts",
        help_text="Modèles de véhicules pour lesquels cette pièce est adaptée.",
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="catalog/parts/", null=True, blank=True)
    is_universal = models.BooleanField(
        "Universelle", default=False,
        help_text="Cocher si compatible avec tous les modèles (ex: huile, ampoule H4).",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Pièce de référence"
        verbose_name_plural = "Pièces de référence (catalogue)"

    def __str__(self):
        return f"{self.reference} — {self.name}"
