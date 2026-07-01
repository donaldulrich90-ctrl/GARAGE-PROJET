import uuid

from django.conf import settings
from django.db import models


class TenantQuerySet(models.QuerySet):
    def for_garage(self, garage):
        return self.filter(garage=garage)


class TenantManager(models.Manager):
    """
    Manager qui permet de filtrer facilement par garage (tenant).
    Usage : Vehicle.objects.for_garage(garage).all()
    """

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_garage(self, garage):
        return self.get_queryset().for_garage(garage)


class TenantModel(models.Model):
    """
    Classe de base abstraite pour tout modele appartenant a un garage.
    Garantit l'isolation des donnees entre garages (tenants) au niveau
    base de donnees partagee + colonne garage_id (pas de schema separe).
    """

    garage = models.ForeignKey(
        "tenants.Garage",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Pour les modeles qui n'appartiennent pas directement a un garage."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def gen_reference(prefix: str) -> str:
    """Genere une reference courte et unique (ex: OR-3F2A9C1B)."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


class AuditLog(models.Model):
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_CHOICES = [
        (ACTION_CREATE, "Création"),
        (ACTION_UPDATE, "Modification"),
        (ACTION_DELETE, "Suppression"),
    ]

    garage = models.ForeignKey(
        "tenants.Garage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        verbose_name="Garage",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        verbose_name="Utilisateur",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    model_name = models.CharField(max_length=100, verbose_name="Modèle")
    object_id = models.CharField(max_length=50, blank=True, verbose_name="ID objet")
    object_repr = models.CharField(max_length=500, verbose_name="Représentation")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Entrée journal"
        verbose_name_plural = "Journal d'activité"

    def __str__(self):
        return f"{self.action} {self.model_name} #{self.object_id} par {self.user}"
