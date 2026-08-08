from django.db import models, transaction
from django.db.models import Max

from core.models import TenantModel


class Client(TenantModel):
    """Client final d'un garage (particulier ou entreprise)."""

    TYPE_INDIVIDUAL = "individual"
    TYPE_COMPANY = "company"
    TYPE_CHOICES = [
        (TYPE_INDIVIDUAL, "Particulier"),
        (TYPE_COMPANY, "Entreprise"),
    ]

    client_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_INDIVIDUAL)
    full_name = models.CharField("Nom / Raison sociale", max_length=150)
    phone = models.CharField(max_length=30)
    whatsapp_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Vehicle(TenantModel):
    """Véhicule appartenant à un client, suivi par le garage."""

    FUEL_CHOICES = [
        ("petrol", "Essence"),
        ("diesel", "Diesel"),
        ("hybrid", "Hybride"),
        ("electric", "Électrique"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField("Immatriculation", max_length=30)
    make = models.CharField("Marque", max_length=60, blank=True, help_text="Renseigné automatiquement si une marque du catalogue est choisie.")
    model = models.CharField("Modèle", max_length=60, blank=True, help_text="Renseigné automatiquement si un modèle du catalogue est choisi.")
    make_ref = models.ForeignKey(
        "catalog.VehicleMake",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="vehicles",
        verbose_name="Marque (catalogue)",
    )
    model_ref = models.ForeignKey(
        "catalog.VehicleModel",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="vehicles",
        verbose_name="Modèle (catalogue)",
    )
    year = models.PositiveIntegerField(null=True, blank=True)
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES, default="petrol")
    vin = models.CharField("Numéro de châssis (VIN)", max_length=50, blank=True)
    mileage = models.PositiveIntegerField("Kilométrage actuel", default=0)
    color = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    arrival_number = models.PositiveIntegerField("N° d'arrivée", null=True, blank=True, editable=False)
    key_tag = models.CharField("Repère de clé", max_length=50, blank=True, help_text="Étiquette physique de la clé, ex: A-12")
    key_token = models.PositiveIntegerField(
        "N° tableau à clés",
        null=True,
        blank=True,
        editable=False,
        help_text="Numéro attribué automatiquement, imprimé sur l'étiquette et affecté à un emplacement du tableau à clés.",
    )
    is_in_garage = models.BooleanField("Actuellement au garage", default=True)
    stored_since = models.DateField("Depuis le", null=True, blank=True)

    class Meta:
        ordering = ["plate_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["garage", "plate_number"],
                name="unique_plate_per_garage",
            )
        ]

    def __str__(self):
        return f"{self.plate_number} - {self.make} {self.model}"

    def save(self, *args, **kwargs):
        # Synchronisation catalogue → champs texte (compat historique et affichage).
        if self.make_ref_id and not self.make:
            self.make = self.make_ref.name
        if self.model_ref_id and not self.model:
            self.model = self.model_ref.name
        with transaction.atomic():
            if self.pk is None and self.arrival_number is None:
                max_num = (
                    Vehicle.objects.select_for_update()
                    .filter(garage=self.garage)
                    .aggregate(Max("arrival_number"))["arrival_number__max"]
                ) or 0
                self.arrival_number = max_num + 1

            if self.is_in_garage:
                if self.key_token is None:
                    used = set(
                        Vehicle.objects.select_for_update()
                        .filter(garage=self.garage, is_in_garage=True, key_token__isnull=False)
                        .exclude(pk=self.pk)
                        .values_list("key_token", flat=True)
                    )
                    token = 1
                    while token in used:
                        token += 1
                    self.key_token = token
            else:
                # Le véhicule quitte le garage : on libère son emplacement
                # sur le tableau à clés pour un prochain véhicule.
                self.key_token = None

            super().save(*args, **kwargs)


class VehiclePhoto(TenantModel):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="vehicles/%Y/%m/")
    caption = models.CharField("Légende", max_length=120, blank=True)
    taken_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-taken_at"]

    def __str__(self):
        return f"Photo de {self.vehicle.plate_number}"
