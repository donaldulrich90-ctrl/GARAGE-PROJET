import uuid

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
