from datetime import date

from django.conf import settings
from django.db import models

from core.models import TenantModel


class Insurance(TenantModel):
    TYPE_LIABILITY = 'liability'
    TYPE_COMPREHENSIVE = 'comprehensive'
    TYPE_THIRD_PARTY = 'third_party_fire_theft'
    TYPE_FLEET = 'fleet'
    INSURANCE_TYPE_CHOICES = [
        (TYPE_LIABILITY, 'Responsabilité civile (RC)'),
        (TYPE_COMPREHENSIVE, 'Tous risques'),
        (TYPE_THIRD_PARTY, 'Tiers + Vol + Incendie'),
        (TYPE_FLEET, 'Flotte'),
    ]

    vehicle = models.ForeignKey(
        'clients.Vehicle',
        on_delete=models.CASCADE,
        related_name='insurances',
        verbose_name='Véhicule',
    )
    insurance_company = models.CharField(max_length=150, verbose_name="Compagnie d'assurance")
    policy_number = models.CharField(max_length=80, verbose_name='N° de police')
    insurance_type = models.CharField(
        max_length=30, choices=INSURANCE_TYPE_CHOICES, default=TYPE_LIABILITY,
        verbose_name="Type d'assurance",
    )
    start_date = models.DateField(verbose_name='Date de début')
    end_date = models.DateField(verbose_name='Date de fin')
    premium_amount = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name='Prime (FCFA)',
    )
    coverage_details = models.TextField(blank=True, verbose_name='Détails de couverture')
    agent_name = models.CharField(max_length=100, blank=True, verbose_name='Agent / Courtier')
    agent_phone = models.CharField(max_length=30, blank=True, verbose_name='Téléphone agent')
    document = models.FileField(
        upload_to='insurance/', blank=True, null=True,
        verbose_name='Document (attestation)',
    )
    reminder_sent = models.BooleanField(default=False, verbose_name='Rappel envoyé')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='insurances_created',
        verbose_name='Créé par',
    )

    class Meta:
        ordering = ['-end_date']
        verbose_name = 'Assurance'
        verbose_name_plural = 'Assurances'

    def __str__(self):
        return f"{self.insurance_company} — {self.vehicle.plate_number}"

    @property
    def is_active(self):
        today = date.today()
        return self.start_date <= today <= self.end_date

    @property
    def status_color(self):
        from datetime import timedelta
        today = date.today()
        if self.end_date < today:
            return 'red'
        if self.end_date <= today + timedelta(days=30):
            return 'orange'
        return 'green'


class InsuranceClaim(TenantModel):
    TYPE_ACCIDENT = 'accident'
    TYPE_THEFT = 'theft'
    TYPE_FIRE = 'fire'
    TYPE_NATURAL = 'natural_disaster'
    TYPE_VANDALISM = 'vandalism'
    TYPE_OTHER = 'other'
    CLAIM_TYPE_CHOICES = [
        (TYPE_ACCIDENT, 'Accident'),
        (TYPE_THEFT, 'Vol'),
        (TYPE_FIRE, 'Incendie'),
        (TYPE_NATURAL, 'Catastrophe naturelle'),
        (TYPE_VANDALISM, 'Vandalisme'),
        (TYPE_OTHER, 'Autre'),
    ]

    STATUS_DECLARED = 'declared'
    STATUS_REVIEW = 'under_review'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_PAID = 'paid'
    STATUS_CHOICES = [
        (STATUS_DECLARED, 'Déclaré'),
        (STATUS_REVIEW, 'En examen'),
        (STATUS_APPROVED, 'Approuvé'),
        (STATUS_REJECTED, 'Rejeté'),
        (STATUS_PAID, 'Payé'),
    ]

    insurance = models.ForeignKey(
        Insurance,
        on_delete=models.CASCADE,
        related_name='claims',
        verbose_name='Police d\'assurance',
    )
    repair_order = models.ForeignKey(
        'repair_orders.RepairOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='insurance_claims',
        verbose_name='Ordre de réparation',
    )
    claim_number = models.CharField(max_length=80, verbose_name='N° de déclaration')
    claim_date = models.DateField(verbose_name='Date du sinistre')
    claim_type = models.CharField(
        max_length=20, choices=CLAIM_TYPE_CHOICES, default=TYPE_ACCIDENT,
        verbose_name='Type de sinistre',
    )
    description = models.TextField(verbose_name='Description du sinistre')
    estimated_cost = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name='Coût estimé (FCFA)',
    )
    approved_amount = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True,
        verbose_name='Montant approuvé (FCFA)',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DECLARED,
        verbose_name='Statut',
    )
    documents = models.FileField(
        upload_to='insurance/claims/', blank=True, null=True,
        verbose_name='Documents justificatifs',
    )
    notes = models.TextField(blank=True, verbose_name='Notes')

    class Meta:
        ordering = ['-claim_date']
        verbose_name = 'Sinistre'
        verbose_name_plural = 'Sinistres'

    def __str__(self):
        return f"Sinistre {self.claim_number} — {self.insurance.vehicle.plate_number}"
