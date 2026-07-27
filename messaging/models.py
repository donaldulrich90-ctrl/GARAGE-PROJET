from django.conf import settings
from django.db import models

from core.models import TenantModel


class MessageTemplate(TenantModel):
    SOURCE_SYSTEM = 'system'
    SOURCE_CUSTOM = 'custom'
    SOURCE_CHOICES = [
        (SOURCE_SYSTEM, 'Système'),
        (SOURCE_CUSTOM, 'Personnalisé'),
    ]

    name = models.CharField('Nom', max_length=100)
    body = models.TextField('Contenu')
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_CUSTOM)

    class Meta:
        ordering = ['source', 'name']
        verbose_name = 'Template message'
        verbose_name_plural = 'Templates messages'

    def __str__(self):
        return self.name

    @property
    def is_system(self):
        return self.source == self.SOURCE_SYSTEM


class BroadcastCampaign(TenantModel):
    FILTER_ALL = 'all'
    FILTER_INSURANCE = 'insurance'
    FILTER_VT = 'vt'
    FILTER_INACTIVE = 'inactive'
    FILTER_MANUAL = 'manual'
    FILTER_CHOICES = [
        (FILTER_ALL, 'Tous les clients'),
        (FILTER_INSURANCE, 'Assurance expirant ce mois'),
        (FILTER_VT, 'Visite technique expirant ce mois'),
        (FILTER_INACTIVE, 'Clients sans visite depuis X mois'),
        (FILTER_MANUAL, 'Sélection manuelle'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_SENT = 'sent'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Brouillon'),
        (STATUS_SENT, 'Envoyé'),
    ]

    name = models.CharField('Nom de la campagne', max_length=150, blank=True)
    body = models.TextField('Message')
    filter_type = models.CharField(max_length=20, choices=FILTER_CHOICES, default=FILTER_ALL)
    filter_value = models.CharField(
        max_length=50,
        blank=True,
        help_text='Nombre de mois pour le filtre "clients inactifs"',
    )
    recipients = models.ManyToManyField(
        'clients.Client',
        blank=True,
        related_name='broadcast_campaigns',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    sent_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='broadcast_campaigns',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Campagne broadcast'
        verbose_name_plural = 'Campagnes broadcast'

    def __str__(self):
        return self.name or f"Campagne du {self.created_at:%d/%m/%Y}"


class WhatsAppLog(TenantModel):
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_SENT, 'Envoyé'),
        (STATUS_FAILED, 'Échoué'),
    ]

    SRC_INDIVIDUAL = 'individual'
    SRC_BROADCAST = 'broadcast'
    SRC_AUTO = 'auto'
    SRC_CHOICES = [
        (SRC_INDIVIDUAL, 'Individuel'),
        (SRC_BROADCAST, 'Broadcast'),
        (SRC_AUTO, 'Automatique'),
    ]

    client = models.ForeignKey(
        'clients.Client',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='whatsapp_logs',
    )
    campaign = models.ForeignKey(
        BroadcastCampaign,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='logs',
    )
    template = models.ForeignKey(
        MessageTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='logs',
    )
    DIRECTION_OUT = 'out'
    DIRECTION_IN = 'in'
    DIRECTION_CHOICES = [
        (DIRECTION_OUT, 'Sortant'),
        (DIRECTION_IN, 'Entrant'),
    ]

    phone = models.CharField('Téléphone', max_length=30)
    body = models.TextField('Message')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SENT)
    source = models.CharField(max_length=20, choices=SRC_CHOICES, default=SRC_INDIVIDUAL)
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, default=DIRECTION_OUT)
    wa_message_id = models.CharField('ID message WA', max_length=128, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Message WhatsApp'
        verbose_name_plural = 'Messages WhatsApp'

    def __str__(self):
        return f"WA {self.phone} — {self.created_at:%d/%m/%Y %H:%M}"
