from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from core.i18n import tr
from core.models import TenantModel, TimeStampedModel, gen_reference


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
    contact_name = models.CharField("Personne à contacter", max_length=150, blank=True)
    city = models.CharField("Ville", max_length=100, blank=True)
    address = models.CharField("Adresse", max_length=255, blank=True)
    ifu = models.CharField("IFU", max_length=50, blank=True)
    rccm = models.CharField("RCCM", max_length=50, blank=True)
    website = models.URLField("Site web", blank=True)
    logo = models.ImageField(
        "Logo",
        upload_to="suppliers/logos/",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    commission_rate = models.DecimalField(
        "Taux de commission plateforme (%)",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Laisser vide pour utiliser le taux plateforme par défaut.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def effective_commission_rate(self):
        """Taux de commission effectif : override fournisseur ou défaut plateforme."""
        from django.conf import settings
        from decimal import Decimal
        if self.commission_rate is not None:
            return self.commission_rate
        return Decimal(str(getattr(settings, "PLATFORM_COMMISSION_RATE", "5.00")))


class Part(TenantModel):
    """Pièce détachée en stock chez un garage."""

    reference = models.CharField("Référence pièce", max_length=80)
    name = models.CharField("Désignation", max_length=150)
    category = models.CharField(max_length=80, blank=True)
    catalog_part = models.ForeignKey(
        "catalog.CatalogPart",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="garage_stocks",
        verbose_name="Pièce catalogue",
        help_text="Si renseigné, la pièce est liée au catalogue de référence partagé.",
    )
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


class SupplierPart(TenantModel):
    """
    Offre d'un fournisseur pour une pièce du catalogue de référence :
    prix pratiqué + stock disponible chez le fournisseur + délai de livraison.

    Permet à un fournisseur (via l'interface garage ou un import CSV) de
    tenir à jour sa liste de prix, et au garage de comparer les fournisseurs
    pour une même pièce catalogue.
    """

    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="catalog_offers",
    )
    catalog_part = models.ForeignKey(
        "catalog.CatalogPart", on_delete=models.CASCADE, related_name="supplier_offers",
    )
    g_code = models.CharField(
        "G-CODE (code de compatibilité)",
        max_length=80,
        db_index=True,
        help_text="Code officiel de la pièce (OEM/fabricant) garantissant sa compatibilité avec le véhicule.",
    )
    unit_price = models.DecimalField(
        "Prix fournisseur (FCFA)", max_digits=12, decimal_places=2, default=0,
    )
    quantity_available = models.PositiveIntegerField(
        "Stock disponible chez le fournisseur", default=0,
    )
    alert_threshold = models.PositiveIntegerField(
        "Seuil d'alerte",
        default=5,
        help_text="Une alerte apparaît sur la plateforme lorsque le stock atteint ce seuil.",
    )
    lead_time_days = models.PositiveIntegerField(
        "Délai livraison (jours)", null=True, blank=True,
    )
    supplier_reference = models.CharField(
        "Réf. interne fournisseur", max_length=100, blank=True,
    )
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["catalog_part__name", "unit_price"]
        verbose_name = "Offre fournisseur"
        verbose_name_plural = "Offres fournisseurs"
        constraints = [
            models.UniqueConstraint(
                fields=["garage", "supplier", "catalog_part"],
                name="unique_supplier_part_per_garage",
            ),
        ]

    def __str__(self):
        return f"{self.supplier.name} — {self.catalog_part} @ {self.unit_price} FCFA"

    @property
    def needs_reorder(self):
        return self.quantity_available <= self.alert_threshold


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


class SupplierStockMovement(TimeStampedModel):
    """
    Mouvement de stock chez un fournisseur (portail fournisseur).

    Non tenant-scoped car un fournisseur gère son propre stock indépendamment
    des garages qu'il sert. Le lien vers un garage est optionnel : présent
    quand la sortie correspond à une vente à un garage précis.
    """

    MOVEMENT_IN = "in"
    MOVEMENT_OUT = "out"
    MOVEMENT_ADJUST = "adjust"
    MOVEMENT_CHOICES = [
        (MOVEMENT_IN, "Entrée / Réapprovisionnement"),
        (MOVEMENT_OUT, "Sortie / Vente"),
        (MOVEMENT_ADJUST, "Ajustement d'inventaire"),
    ]
    PAYMENT_CASH = "cash"
    PAYMENT_MOBILE_MONEY = "mobile_money"
    PAYMENT_BANK = "bank_transfer"
    PAYMENT_CREDIT = "credit"
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Espèces"),
        (PAYMENT_MOBILE_MONEY, "Mobile Money"),
        (PAYMENT_BANK, "Virement bancaire"),
        (PAYMENT_CREDIT, "À crédit"),
    ]

    supplier_part = models.ForeignKey(
        SupplierPart,
        on_delete=models.CASCADE,
        related_name="movements",
        verbose_name="Offre fournisseur",
    )
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_CHOICES)
    quantity = models.IntegerField(help_text="Positif pour entrée, positif aussi pour sortie (le signe est déduit du type).")
    unit_price = models.DecimalField(
        "Prix appliqué (FCFA)", max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Prix de vente réel (peut différer du prix catalogue).",
    )
    destination_garage = models.ForeignKey(
        "tenants.Garage",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="supplier_purchases",
        verbose_name="Garage destinataire",
        help_text="Renseigné pour une sortie vendue à un garage identifié.",
    )
    sale_reference = models.CharField("Référence de vente", max_length=50, blank=True)
    customer_name = models.CharField("Client / Acheteur", max_length=150, blank=True)
    payment_method = models.CharField(
        "Mode de paiement",
        max_length=20,
        choices=PAYMENT_CHOICES,
        blank=True,
    )
    source_order = models.ForeignKey(
        "SupplierOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="Commande d'origine",
    )
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mouvement stock fournisseur"
        verbose_name_plural = "Mouvements stock fournisseurs"

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} × {self.supplier_part}"

    @property
    def supplier(self):
        return self.supplier_part.supplier

    @property
    def line_total(self):
        return Decimal(self.quantity) * (self.unit_price or Decimal("0"))

    def save(self, *args, **kwargs):
        if self.movement_type == self.MOVEMENT_OUT and not self.sale_reference:
            self.sale_reference = gen_reference("VTE")
        super().save(*args, **kwargs)

    def apply_to_stock(self):
        """Applique le mouvement avec verrouillage pour éviter les doubles sorties."""
        with transaction.atomic():
            sp = SupplierPart.objects.select_for_update().get(pk=self.supplier_part_id)
            if self.movement_type == self.MOVEMENT_IN:
                new_quantity = sp.quantity_available + self.quantity
            elif self.movement_type == self.MOVEMENT_OUT:
                if sp.quantity_available < self.quantity:
                    raise ValidationError(tr(
                        f"Stock insuffisant pour {sp.catalog_part}: "
                        f"{sp.quantity_available} disponible(s), {self.quantity} demandé(s).",
                        f"Insufficient stock for {sp.catalog_part}: "
                        f"{sp.quantity_available} available, {self.quantity} requested.",
                    ))
                new_quantity = sp.quantity_available - self.quantity
            else:
                new_quantity = self.quantity
            sp.quantity_available = new_quantity
            sp.save(update_fields=["quantity_available", "updated_at"])
            self.supplier_part = sp


class SupplierExpense(TimeStampedModel):
    """Dépense propre au fournisseur, utilisée dans ses rapports financiers."""

    CAT_PURCHASE = "purchase"
    CAT_TRANSPORT = "transport"
    CAT_SALARY = "salary"
    CAT_RENT = "rent"
    CAT_UTILITIES = "utilities"
    CAT_TAX = "tax"
    CAT_MAINTENANCE = "maintenance"
    CAT_MARKETING = "marketing"
    CAT_OTHER = "other"
    CATEGORY_CHOICES = [
        (CAT_PURCHASE, "Achat de marchandises"),
        (CAT_TRANSPORT, "Transport / Livraison"),
        (CAT_SALARY, "Salaires"),
        (CAT_RENT, "Loyer"),
        (CAT_UTILITIES, "Eau / Électricité / Internet"),
        (CAT_TAX, "Taxes et impôts"),
        (CAT_MAINTENANCE, "Entretien / Réparation"),
        (CAT_MARKETING, "Communication / Marketing"),
        (CAT_OTHER, "Autre"),
    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="expenses",
        verbose_name="Fournisseur",
    )
    date = models.DateField(default=timezone.localdate)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CAT_OTHER)
    amount = models.DecimalField(
        "Montant (FCFA)",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_method = models.CharField(
        "Mode de paiement",
        max_length=20,
        choices=SupplierStockMovement.PAYMENT_CHOICES,
        default=SupplierStockMovement.PAYMENT_CASH,
    )
    reference = models.CharField(max_length=80, blank=True)
    description = models.CharField(max_length=255)
    receipt = models.FileField("Justificatif", upload_to="suppliers/expenses/%Y/%m/", blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplier_expenses_recorded",
    )

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Dépense fournisseur"
        verbose_name_plural = "Dépenses fournisseurs"

    def __str__(self):
        return f"{self.supplier.name} — {self.amount} FCFA — {self.date:%d/%m/%Y}"


class SupplierOrder(TimeStampedModel):
    """
    Commande passée par un garage à un fournisseur via la plateforme.
    Le paiement n'est PAS géré ici — la plateforme prélève une commission
    sur le montant validé (revenu marketplace).
    """

    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_VALIDATED = "validated"
    STATUS_REJECTED = "rejected"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Brouillon"),
        (STATUS_SUBMITTED, "Soumise au fournisseur"),
        (STATUS_VALIDATED, "Validée par le fournisseur"),
        (STATUS_REJECTED, "Rejetée par le fournisseur"),
        (STATUS_SHIPPED, "Expédiée"),
        (STATUS_DELIVERED, "Livrée / Réceptionnée"),
        (STATUS_CANCELLED, "Annulée"),
    ]

    reference = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    garage = models.ForeignKey(
        "tenants.Garage", on_delete=models.CASCADE, related_name="supplier_orders",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="orders_received",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    submitted_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Instantané au moment de la validation (verrouillé pour la facturation commission)
    total_amount = models.DecimalField("Total (FCFA)", max_digits=14, decimal_places=2, default=0)
    commission_rate = models.DecimalField("Taux commission (%)", max_digits=5, decimal_places=2, default=0)
    commission_amount = models.DecimalField("Commission plateforme (FCFA)", max_digits=14, decimal_places=2, default=0)

    garage_note = models.TextField("Note du garage", blank=True)
    supplier_note = models.TextField("Note du fournisseur", blank=True)
    rejection_reason = models.CharField("Motif de rejet", max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Commande fournisseur"
        verbose_name_plural = "Commandes fournisseur"

    def __str__(self):
        return f"{self.reference} — {self.garage.name} → {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = gen_reference("SO")
        super().save(*args, **kwargs)

    # ── Transitions de statut ─────────────────────────────────────────────────

    def can_submit(self):
        return self.status == self.STATUS_DRAFT and self.lines.exists()

    def can_validate(self):
        return self.status == self.STATUS_SUBMITTED

    def can_reject(self):
        return self.status == self.STATUS_SUBMITTED

    def can_ship(self):
        return self.status == self.STATUS_VALIDATED

    def can_deliver(self):
        return self.status in (self.STATUS_VALIDATED, self.STATUS_SHIPPED)

    def can_cancel(self):
        return self.status in (self.STATUS_DRAFT, self.STATUS_SUBMITTED)

    def recompute_total(self):
        total = sum((l.line_total for l in self.lines.all()), Decimal("0"))
        self.total_amount = total
        return total

    def snapshot_commission(self):
        """Verrouille le taux et le montant de commission au moment de la validation."""
        rate = self.supplier.effective_commission_rate()
        self.commission_rate = rate
        self.commission_amount = (self.total_amount * rate / Decimal("100")).quantize(Decimal("0.01"))


class SupplierOrderLine(TimeStampedModel):
    order = models.ForeignKey(SupplierOrder, on_delete=models.CASCADE, related_name="lines")
    supplier_part = models.ForeignKey(
        SupplierPart, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="order_lines",
    )
    # Snapshots pour intégrité même si l'offre fournisseur est supprimée
    catalog_reference = models.CharField(max_length=100, blank=True)
    catalog_name = models.CharField(max_length=200, blank=True)
    g_code = models.CharField("G-CODE", max_length=80, blank=True)
    unit_price = models.DecimalField("Prix unitaire (FCFA)", max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} × {self.catalog_name or 'pièce'} @ {self.unit_price}"

    @property
    def line_total(self):
        return (self.unit_price or Decimal("0")) * self.quantity

    def save(self, *args, **kwargs):
        if self.supplier_part and not self.catalog_name:
            self.catalog_name = self.supplier_part.catalog_part.name
            self.catalog_reference = self.supplier_part.catalog_part.reference
        if self.supplier_part and not self.g_code:
            self.g_code = self.supplier_part.g_code
        super().save(*args, **kwargs)
