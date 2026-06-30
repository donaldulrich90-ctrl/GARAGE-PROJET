from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.db.models import Sum

from core.models import TimeStampedModel

PLAN_PRICES_FCFA = {
    "starter": 60_000,
    "pro": 120_000,
    "business": 240_000,
}

PLAN_CHOICES = [
    ("starter", "Starter"),
    ("pro", "Pro"),
    ("business", "Business"),
]


class Subscription(TimeStampedModel):
    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        ("trial", "Essai"),
        ("active", "Actif"),
        ("expired", "Expiré"),
        ("cancelled", "Annulé"),
    ]

    garage = models.OneToOneField(
        "tenants.Garage",
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name="Garage",
    )
    plan = models.CharField("Plan", max_length=20, choices=PLAN_CHOICES, default="starter")
    status = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, default=STATUS_TRIAL)
    start_date = models.DateField("Date de début")
    end_date = models.DateField("Date d'expiration")

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"
        ordering = ["end_date"]

    def __str__(self):
        return f"{self.garage.name} — {self.get_plan_display()} ({self.get_status_display()})"

    @property
    def price_fcfa(self):
        return PLAN_PRICES_FCFA.get(self.plan, 0)

    @property
    def days_until_expiry(self):
        return (self.end_date - date.today()).days

    @property
    def is_expiring_soon(self):
        d = self.days_until_expiry
        return self.status == self.STATUS_ACTIVE and 0 <= d <= 30

    @property
    def total_paid(self):
        result = self.payments.aggregate(total=Sum("amount"))["total"]
        return int(result) if result else 0

    @property
    def balance_due(self):
        return max(0, self.price_fcfa - self.total_paid)

    def sync_status(self):
        """Passe à expiré si la date de fin est dépassée."""
        if self.status == self.STATUS_ACTIVE and self.end_date < date.today():
            self.status = self.STATUS_EXPIRED
            self.save(update_fields=["status", "updated_at"])

    def renew(self, plan=None):
        """Prolonge d'un an à partir de la date de fin actuelle (ou aujourd'hui si expiré)."""
        if plan and plan in dict(PLAN_CHOICES):
            self.plan = plan
        base = max(self.end_date, date.today())
        self.start_date = base
        self.end_date = base + timedelta(days=365)
        self.status = self.STATUS_ACTIVE
        self.save()


class SubscriptionPayment(TimeStampedModel):
    METHOD_CASH = "cash"
    METHOD_MOBILE = "mobile_money"
    METHOD_BANK = "bank_transfer"

    METHOD_CHOICES = [
        ("cash", "Espèces"),
        ("mobile_money", "Mobile Money"),
        ("bank_transfer", "Virement bancaire"),
    ]

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Abonnement",
    )
    amount = models.DecimalField("Montant (FCFA)", max_digits=12, decimal_places=0)
    method = models.CharField("Méthode", max_length=20, choices=METHOD_CHOICES)
    paid_at = models.DateField("Date de paiement")
    note = models.CharField("Note", max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Enregistré par",
    )

    class Meta:
        verbose_name = "Paiement abonnement"
        verbose_name_plural = "Paiements abonnements"
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.subscription.garage.name} — {self.amount} FCFA le {self.paid_at}"
