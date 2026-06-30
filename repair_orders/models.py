from django.conf import settings
from django.db import models

from core.models import TenantModel, gen_reference


class RepairOrder(TenantModel):
    """
    Cœur du système : un ordre de réparation (OR) suit un véhicule
    de la réception à la livraison.
    """

    STATUS_RECEIVED = "received"
    STATUS_DIAGNOSIS = "diagnosis"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_READY = "ready"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_RECEIVED, "Reçu"),
        (STATUS_DIAGNOSIS, "Diagnostic"),
        (STATUS_IN_PROGRESS, "En cours"),
        (STATUS_READY, "Prêt"),
        (STATUS_DELIVERED, "Livré"),
        (STATUS_CANCELLED, "Annulé"),
    ]

    reference = models.CharField(max_length=20, unique=True, blank=True)
    vehicle = models.ForeignKey(
        "clients.Vehicle", on_delete=models.CASCADE, related_name="repair_orders"
    )
    client = models.ForeignKey(
        "clients.Client", on_delete=models.CASCADE, related_name="repair_orders"
    )
    assigned_mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="repair_orders",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    mileage_at_reception = models.PositiveIntegerField(default=0)
    client_complaint = models.TextField("Motif / plainte client", blank=True)
    diagnosis_notes = models.TextField("Notes de diagnostic", blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    expected_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return self.reference or f"OR #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = gen_reference("OR")
        super().save(*args, **kwargs)

    @property
    def total_labor(self):
        return sum(task.cost for task in self.tasks.all())

    @property
    def total_parts(self):
        return sum(p.quantity * p.unit_price for p in self.parts_used.all())

    @property
    def total_cost(self):
        return self.total_labor + self.total_parts


class RepairOrderTask(models.Model):
    """Tâche de main d'œuvre réalisée dans le cadre d'un OR."""

    repair_order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, related_name="tasks")
    description = models.CharField(max_length=200)
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    cost = models.DecimalField("Coût main d'œuvre (FCFA)", max_digits=12, decimal_places=2, default=0)
    is_done = models.BooleanField(default=False)

    def __str__(self):
        return self.description


class RepairOrderPart(models.Model):
    """Pièce consommée sur un OR, avec prix figé au moment de l'utilisation."""

    repair_order = models.ForeignKey(
        RepairOrder, on_delete=models.CASCADE, related_name="parts_used"
    )
    part = models.ForeignKey("inventory.Part", on_delete=models.PROTECT, related_name="usages")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.part.name}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price
