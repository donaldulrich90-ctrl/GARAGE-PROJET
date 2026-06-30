from django.db import models

from core.models import TenantModel, gen_reference


class Employee(TenantModel):
    TYPE_EMPLOYEE = "employe"
    TYPE_INTERN = "stagiaire"
    TYPE_CHOICES = [
        (TYPE_EMPLOYEE, "Employé"),
        (TYPE_INTERN, "Stagiaire"),
    ]

    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    post = models.CharField(max_length=100, verbose_name="Poste")
    employee_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_EMPLOYEE, verbose_name="Type"
    )
    phone = models.CharField(max_length=30, blank=True, verbose_name="Téléphone")
    start_date = models.DateField(verbose_name="Date d'entrée")
    monthly_pay = models.DecimalField(
        max_digits=12, decimal_places=0, verbose_name="Salaire / Indemnité mensuel (FCFA)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Employé / Stagiaire"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name


class Payroll(TenantModel):
    reference = models.CharField(max_length=20, unique=True, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="payrolls", verbose_name="Employé"
    )
    month = models.DateField(verbose_name="Mois (1er du mois)")
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Montant payé (FCFA)")
    expense = models.OneToOneField(
        "expenses.Expense",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payroll_entry",
    )
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        unique_together = [("employee", "month")]
        ordering = ["-month"]
        verbose_name = "Bulletin de paie"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = gen_reference("PAY")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.full_name} — {self.month.strftime('%B %Y')}"
