from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utilisateur custom. Lié à un garage (sauf le staff plateforme = superuser
    sans garage, qui voit tout via l'admin Django).
    """

    ROLE_ADMIN = "admin"
    ROLE_RECEPTION = "reception"
    ROLE_MECHANIC = "mechanic"
    ROLE_CASHIER = "cashier"
    ROLE_STOREKEEPER = "storekeeper"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Administrateur garage"),
        (ROLE_RECEPTION, "Réceptionniste"),
        (ROLE_MECHANIC, "Mécanicien"),
        (ROLE_CASHIER, "Caissier"),
        (ROLE_STOREKEEPER, "Magasinier"),
    ]

    garage = models.ForeignKey(
        "tenants.Garage",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
        help_text="Vide pour le staff plateforme (superuser).",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        garage_name = self.garage.name if self.garage else "Plateforme"
        return f"{self.get_full_name() or self.username} ({garage_name})"

    @property
    def is_garage_admin(self):
        return self.role == self.ROLE_ADMIN
