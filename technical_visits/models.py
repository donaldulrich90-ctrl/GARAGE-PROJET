from django.conf import settings
from django.db import models

from core.models import TenantModel


class TechnicalVisit(TenantModel):
    VISIT_PERIODIC = 'periodic'
    VISIT_PRE_SALE = 'pre_sale'
    VISIT_VOLUNTARY = 'voluntary'
    VISIT_POST_ACCIDENT = 'post_accident'
    VISIT_TYPE_CHOICES = [
        (VISIT_PERIODIC, 'Périodique'),
        (VISIT_PRE_SALE, 'Avant-vente'),
        (VISIT_VOLUNTARY, 'Volontaire'),
        (VISIT_POST_ACCIDENT, 'Après accident'),
    ]

    RESULT_PASSED = 'passed'
    RESULT_FAILED = 'failed'
    RESULT_CONDITIONAL = 'conditional'
    RESULT_CHOICES = [
        (RESULT_PASSED, 'Admis'),
        (RESULT_FAILED, 'Refusé'),
        (RESULT_CONDITIONAL, 'Admis sous réserve'),
    ]

    vehicle = models.ForeignKey(
        'clients.Vehicle',
        on_delete=models.CASCADE,
        related_name='technical_visits',
        verbose_name='Véhicule',
    )
    visit_type = models.CharField(
        max_length=20, choices=VISIT_TYPE_CHOICES, default=VISIT_PERIODIC,
        verbose_name='Type de visite',
    )
    visit_date = models.DateField(verbose_name='Date de la visite')
    expiry_date = models.DateField(verbose_name="Date d'expiration")
    result = models.CharField(
        max_length=20, choices=RESULT_CHOICES, default=RESULT_PASSED,
        verbose_name='Résultat',
    )
    inspection_center = models.CharField(max_length=150, verbose_name='Centre de contrôle')
    certificate_number = models.CharField(
        max_length=80, blank=True, verbose_name='N° certificat / PV',
    )
    observations = models.TextField(blank=True, verbose_name='Observations')
    defects = models.JSONField(default=list, blank=True, verbose_name='Défauts constatés')
    cost = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name='Coût (FCFA)',
    )
    document = models.FileField(
        upload_to='technical_visits/', blank=True, null=True,
        verbose_name='Document (scan PV)',
    )
    reminder_sent = models.BooleanField(default=False, verbose_name='Rappel envoyé')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='technical_visits_created',
        verbose_name='Créé par',
    )

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Visite technique'
        verbose_name_plural = 'Visites techniques'

    def __str__(self):
        return f"VT {self.vehicle.plate_number} — {self.visit_date}"

    @property
    def status_color(self):
        from datetime import date, timedelta
        today = date.today()
        if self.expiry_date < today:
            return 'red'
        if self.expiry_date <= today + timedelta(days=30):
            return 'orange'
        return 'green'
