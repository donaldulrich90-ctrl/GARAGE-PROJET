from django.conf import settings
from django.db import models

from core.models import TenantModel, gen_reference


class DiagnosticReport(TenantModel):
    STATUS_PRESENT = 'present'
    STATUS_STORED = 'stored'
    STATUS_HISTORY = 'history'
    STATUS_PENDING = 'pending'
    STATUS_INFO = 'info'

    repair_order = models.ForeignKey(
        'repair_orders.RepairOrder',
        on_delete=models.CASCADE,
        related_name='diagnostic_reports',
        verbose_name='Ordre de réparation',
    )
    reference = models.CharField('Référence', max_length=20, unique=True, blank=True)
    scan_date = models.DateTimeField('Date du scan')
    mileage = models.PositiveIntegerField('Kilométrage', null=True, blank=True)
    scanner_name = models.CharField('Outil de diagnostic', max_length=100, blank=True)
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='diagnostic_reports',
        verbose_name='Technicien',
    )
    summary = models.TextField('Résumé', blank=True)
    observations = models.TextField('Observations du technicien', blank=True)
    recommendations = models.TextField('Recommandations', blank=True)
    original_file = models.FileField(
        'Fichier scanner original',
        upload_to='diagnostics/%Y/%m/',
        null=True,
        blank=True,
        help_text='PDF ou image provenant de l\'outil de diagnostic.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='diagnostics_created',
        verbose_name='Créé par',
    )

    class Meta:
        ordering = ['-scan_date']
        verbose_name = 'Rapport de diagnostic'
        verbose_name_plural = 'Rapports de diagnostic'

    def __str__(self):
        return self.reference or f'Diag #{self.pk}'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = gen_reference('DIAG')
        super().save(*args, **kwargs)

    @property
    def vehicle(self):
        return self.repair_order.vehicle

    @property
    def dtc_count(self):
        return self.codes.count()


class DiagnosticCode(models.Model):
    STATUS_PRESENT = 'present'
    STATUS_STORED = 'stored'
    STATUS_HISTORY = 'history'
    STATUS_PENDING = 'pending'
    STATUS_INFO = 'info'

    STATUS_CHOICES = [
        (STATUS_PRESENT, 'Présent'),
        (STATUS_STORED, 'Mémorisé'),
        (STATUS_HISTORY, 'Historique'),
        (STATUS_PENDING, 'En attente'),
        (STATUS_INFO, 'Information'),
    ]

    STATUS_COLORS = {
        STATUS_PRESENT: 'red',
        STATUS_STORED: 'orange',
        STATUS_HISTORY: 'gray',
        STATUS_PENDING: 'yellow',
        STATUS_INFO: 'blue',
    }

    diagnostic_report = models.ForeignKey(
        DiagnosticReport,
        on_delete=models.CASCADE,
        related_name='codes',
        verbose_name='Rapport de diagnostic',
    )
    code = models.CharField('Code DTC', max_length=20)
    module_system = models.CharField('Calculateur / Système', max_length=100, blank=True)
    description = models.CharField('Description', max_length=255, blank=True)
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default=STATUS_PRESENT)

    class Meta:
        ordering = ['code']
        verbose_name = 'Code défaut (DTC)'
        verbose_name_plural = 'Codes défauts (DTC)'

    def __str__(self):
        return f'{self.code} — {self.description}'

    @property
    def status_color(self):
        return self.STATUS_COLORS.get(self.status, 'gray')
