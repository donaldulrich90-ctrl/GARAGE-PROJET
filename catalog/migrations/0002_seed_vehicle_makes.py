"""Remplit le catalogue avec une large liste de marques de véhicules.

Migration de données idempotente : elle peut être rejouée sans créer de
doublons (get_or_create sur le nom). Les modèles/années sont ajoutés
ensuite par les garages selon leurs besoins.
"""
from django.db import migrations
from django.utils.text import slugify


MAKES = [
    "Toyota", "Nissan", "Mitsubishi", "Honda", "Mazda", "Suzuki", "Isuzu",
    "Daihatsu", "Subaru", "Lexus", "Infiniti", "Hyundai", "Kia", "SsangYong",
    "Mercedes-Benz", "BMW", "Audi", "Volkswagen", "Opel", "Porsche", "MAN",
    "Peugeot", "Renault", "Citroën", "DS", "Dacia", "Fiat", "Alfa Romeo",
    "Ford", "Chevrolet", "Jeep", "Dodge", "GMC", "Land Rover", "Jaguar",
    "Volvo", "Škoda", "SEAT", "MG", "Mini", "Iveco", "Scania", "DAF",
    "Tata", "Mahindra", "Chery", "Geely", "Great Wall", "Haval", "JAC",
    "Foton", "BYD", "Changan", "DFSK", "Baic", "Hino", "King Long",
]


def seed_makes(apps, schema_editor):
    VehicleMake = apps.get_model("catalog", "VehicleMake")
    for name in MAKES:
        VehicleMake.objects.get_or_create(
            name=name, defaults={"slug": slugify(name)},
        )


def unseed(apps, schema_editor):
    # On ne supprime rien : des données garage peuvent déjà y être rattachées.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_makes, unseed),
    ]
