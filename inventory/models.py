from django.db import models

from core.models import TenantModel, TimeStampedModel


class Supplier(TenantModel):
    """
    Fournisseur de pièces pour un garage. Le flag is_faest distingue
    FAEST comme fournisseur natif intégré à la plateforme (canal de vente
    privilégié), des autres fournisseurs locaux du garage.
    """

    name = models.CharField(max_length=150)
    is_faest = models.BooleanField(
        "Fournisseur FAEST",
        default=False,
        help_text="Cocher uniquement pour le fournisseur officiel FASO ÉQUIPEMENTS STORE.",
    )
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Part(TenantModel):
    """Pièce détachée en stock chez un garage."""

    reference = models.CharField("Référence pièce", max_length=80)
    name = models.CharField("Désignation", max_length=150)
    category = models.CharField(max_length=80, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="parts"
    )
    unit_price = models.DecimalField("Prix unitaire (FCFA)", max_digits=12, decimal_places=2, default=0)
    quantity_in_stock = models.PositiveIntegerField(default=0)
    alert_threshold = models.PositiveIntegerField(
        "Seuil d'alerte", default=2, help_text="Alerte de réapprovisionnement sous ce seuil."
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["garage", "reference"],
                name="unique_part_reference_per_garage",
            )
        ]

    def __str__(self):
        return f"{self.reference} - {self.name}"

    @property
    def needs_reorder(self):
        return self.quantity_in_stock <= self.alert_threshold


class StockMovement(TenantModel):
    """Historique des entrées / sorties de stock pour traçabilité."""

    MOVEMENT_IN = "in"
    MOVEMENT_OUT = "out"
    MOVEMENT_CHOICES = [
        (MOVEMENT_IN, "Entrée"),
        (MOVEMENT_OUT, "Sortie"),
    ]

    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_CHOICES)
    quantity = models.PositiveIntegerField()
    reason = models.CharField(
        max_length=150,
        blank=True,
        help_text="Ex: utilisé sur OR-1234, réapprovisionnement FAEST, inventaire...",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} x {self.part}"
