from django.db import models

from core.models import TenantModel, gen_reference


class Quote(TenantModel):
    """Devis envoyé au client avant ou pendant la réparation."""

    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Brouillon"),
        (STATUS_SENT, "Envoyé"),
        (STATUS_ACCEPTED, "Accepté"),
        (STATUS_REJECTED, "Refusé"),
    ]

    reference = models.CharField(max_length=20, unique=True, blank=True)
    repair_order = models.ForeignKey(
        "repair_orders.RepairOrder", on_delete=models.CASCADE, related_name="quotes"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference or f"Devis #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = gen_reference("DEV")
        super().save(*args, **kwargs)

    @property
    def total(self):
        return sum(line.line_total for line in self.lines.all())


class QuoteLine(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return self.description


class Invoice(TenantModel):
    """Facture finale, liée à un OR (et optionnellement à un devis accepté)."""

    STATUS_UNPAID = "unpaid"
    STATUS_PARTIAL = "partial"
    STATUS_PAID = "paid"

    STATUS_CHOICES = [
        (STATUS_UNPAID, "Non payée"),
        (STATUS_PARTIAL, "Partiellement payée"),
        (STATUS_PAID, "Payée"),
    ]

    reference = models.CharField(max_length=20, unique=True, blank=True)
    repair_order = models.ForeignKey(
        "repair_orders.RepairOrder", on_delete=models.CASCADE, related_name="invoices"
    )
    quote = models.ForeignKey(
        Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNPAID)
    issued_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference or f"Facture #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = gen_reference("FACT")
        super().save(*args, **kwargs)

    @property
    def total(self):
        ro = self.repair_order
        return ro.total_cost if ro else 0

    @property
    def amount_paid(self):
        return sum(p.amount for p in self.payments.all())

    @property
    def balance_due(self):
        return self.total - self.amount_paid


class Payment(models.Model):
    METHOD_CASH = "cash"
    METHOD_MOBILE_MONEY = "mobile_money"
    METHOD_BANK = "bank_transfer"

    METHOD_CHOICES = [
        (METHOD_CASH, "Espèces"),
        (METHOD_MOBILE_MONEY, "Mobile Money"),
        (METHOD_BANK, "Virement bancaire"),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_CASH)
    paid_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"{self.amount} FCFA - {self.invoice.reference}"
