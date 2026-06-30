from django.db import models

from core.models import TenantModel


class Expense(TenantModel):
    CAT_LOCATION = "location"
    CAT_FOOD = "nourriture"
    CAT_CONSUMABLES = "consommables"
    CAT_SALARY = "salaires"
    CAT_TAX = "impots"
    CAT_OTHER = "autres"

    CATEGORY_CHOICES = [
        (CAT_LOCATION, "Loyer / Location"),
        (CAT_FOOD, "Nourriture"),
        (CAT_CONSUMABLES, "Consommables garage"),
        (CAT_SALARY, "Salaires"),
        (CAT_TAX, "Impôts / Taxes"),
        (CAT_OTHER, "Autres"),
    ]

    METHOD_CASH = "cash"
    METHOD_MOBILE = "mobile_money"
    METHOD_BANK = "bank_transfer"

    METHOD_CHOICES = [
        (METHOD_CASH, "Espèces"),
        (METHOD_MOBILE, "Mobile Money"),
        (METHOD_BANK, "Virement bancaire"),
    ]

    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_CASH)
    employee = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="salary_expenses",
        help_text="Renseigner uniquement pour les salaires.",
    )
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_expenses",
    )

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_category_display()} — {self.amount} FCFA ({self.date})"
