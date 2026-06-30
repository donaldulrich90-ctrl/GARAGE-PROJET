"""
Script de démo : crée un garage pilote, un admin, des clients/véhicules,
un fournisseur FAEST, des pièces et un OR complet avec devis/facture.
Usage : python manage.py shell < seed_demo.py
"""
import django

from accounts.models import User
from clients.models import Client, Vehicle
from inventory.models import Part, Supplier
from invoicing.models import Invoice, Quote, QuoteLine
from repair_orders.models import RepairOrder, RepairOrderPart, RepairOrderTask
from tenants.models import Garage

garage, _ = Garage.objects.get_or_create(
    name="Garage Wayalghin Auto",
    defaults={"city": "Ouagadougou", "phone": "+22670000000", "faest_supplier_enabled": True},
)

admin_user, created = User.objects.get_or_create(
    username="admin_wayalghin",
    defaults={"garage": garage, "role": User.ROLE_ADMIN, "is_staff": True, "first_name": "Admin"},
)
if created:
    admin_user.set_password("garage1234")
    admin_user.save()

client, _ = Client.objects.get_or_create(
    garage=garage, full_name="Issa Compaoré", defaults={"phone": "+22671111111"}
)
vehicle, _ = Vehicle.objects.get_or_create(
    garage=garage, plate_number="11-BF-2024",
    defaults={"client": client, "make": "Toyota", "model": "Hilux", "year": 2015, "mileage": 145000},
)

faest, _ = Supplier.objects.get_or_create(
    garage=garage, name="FAEST - Faso Équipements Store", defaults={"is_faest": True}
)
part, _ = Part.objects.get_or_create(
    garage=garage, reference="FLT-001",
    defaults={"name": "Filtre à huile", "supplier": faest, "unit_price": 8000, "quantity_in_stock": 1, "alert_threshold": 3},
)

order, _ = RepairOrder.objects.get_or_create(
    garage=garage, vehicle=vehicle, client=client,
    defaults={"client_complaint": "Vidange + bruit moteur", "mileage_at_reception": 145000},
)
RepairOrderTask.objects.get_or_create(
    repair_order=order, description="Vidange complète", defaults={"cost": 5000, "is_done": True}
)
RepairOrderPart.objects.get_or_create(
    repair_order=order, part=part, defaults={"quantity": 1, "unit_price": part.unit_price}
)

quote, _ = Quote.objects.get_or_create(garage=garage, repair_order=order)
QuoteLine.objects.get_or_create(quote=quote, description="Vidange + filtre", defaults={"quantity": 1, "unit_price": 13000})

invoice, _ = Invoice.objects.get_or_create(garage=garage, repair_order=order, defaults={"quote": quote})

print("Données de démo créées avec succès.")
print(f"Connexion admin : admin_wayalghin / garage1234 (garage: {garage.name})")
