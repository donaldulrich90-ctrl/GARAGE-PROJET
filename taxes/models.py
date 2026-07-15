from datetime import date

from django.db import models

from core.models import TenantModel


class VehicleTax(TenantModel):
    TAX_VIGNETTE = 'vignette'
    TAX_STATIONNEMENT = 'taxe_stationnement'
    TAX_PATENTE = 'patente'
    TAX_TIMBRE = 'timbre'
    TAX_AUTRE = 'autre'
    TAX_TYPE_CHOICES = [
        (TAX_VIGNETTE, 'Vignette automobile'),
        (TAX_STATIONNEMENT, 'Taxe de stationnement'),
        (TAX_PATENTE, 'Patente transport'),
        (TAX_TIMBRE, 'Droit de timbre'),
        (TAX_AUTRE, 'Autre'),
    ]

    vehicle = models.ForeignKey(
        'clients.Vehicle',
        on_delete=models.CASCADE,
        related_name='taxes',
        verbose_name='Véhicule',
    )
    tax_type = models.CharField(
        max_length=30, choices=TAX_TYPE_CHOICES, default=TAX_VIGNETTE,
        verbose_name='Type de taxe',
    )
    description = models.CharField(
        max_length=200, blank=True,
        verbose_name='Description (si Autre)',
    )
    fiscal_year = models.PositiveIntegerField(verbose_name='Année fiscale')
    amount = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name='Montant (FCFA)',
    )
    due_date = models.DateField(verbose_name='Date limite de paiement')
    payment_date = models.DateField(
        null=True, blank=True,
        verbose_name='Date de paiement effectif',
    )
    is_paid = models.BooleanField(default=False, verbose_name='Payé')
    receipt_number = models.CharField(
        max_length=80, blank=True,
        verbose_name='N° quittance',
    )
    notes = models.TextField(blank=True, verbose_name='Notes')
    document = models.FileField(
        upload_to='taxes/', blank=True, null=True,
        verbose_name='Document (scan quittance)',
    )

    class Meta:
        ordering = ['-fiscal_year', 'due_date']
        verbose_name = 'Taxe véhicule'
        verbose_name_plural = 'Taxes véhicules'

    def __str__(self):
        return f"{self.get_tax_type_display()} {self.fiscal_year} — {self.vehicle.plate_number}"

    @property
    def status(self):
        if self.is_paid:
            return 'paid'
        if self.due_date < date.today():
            return 'overdue'
        return 'pending'

    @property
    def days_until_due(self):
        return (self.due_date - date.today()).days
