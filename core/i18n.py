"""Petits helpers bilingues pour les textes propres à Garage SaaS.

Django continue de gérer la langue active et ses formats. Ces helpers couvrent
les libellés métier français/anglais sans rendre l'application dépendante des
outils GNU gettext sur les installations Windows.
"""

from django.utils.translation import get_language


def is_english():
    return (get_language() or "fr").lower().startswith("en")


def tr(french, english):
    """Retourne le texte correspondant à la langue active de la requête."""
    return english if is_english() else french


PERIOD_LABELS = {
    "jour": ("Aujourd'hui", "Today"),
    "semaine": ("Cette semaine", "This week"),
    "mois": ("Ce mois", "This month"),
}

MOVEMENT_LABELS = {
    "in": ("Entrée / Réapprovisionnement", "Incoming / Restocking"),
    "out": ("Sortie / Vente", "Outgoing / Sale"),
    "adjust": ("Ajustement d'inventaire", "Inventory adjustment"),
}

PAYMENT_LABELS = {
    "cash": ("Espèces", "Cash"),
    "mobile_money": ("Mobile Money", "Mobile Money"),
    "bank_transfer": ("Virement bancaire", "Bank transfer"),
    "credit": ("À crédit", "Credit"),
}

EXPENSE_CATEGORY_LABELS = {
    "purchase": ("Achat de marchandises", "Inventory purchases"),
    "transport": ("Transport / Livraison", "Transport / Delivery"),
    "salary": ("Salaires", "Salaries"),
    "rent": ("Loyer", "Rent"),
    "utilities": ("Eau / Électricité / Internet", "Water / Electricity / Internet"),
    "tax": ("Taxes et impôts", "Taxes"),
    "maintenance": ("Entretien / Réparation", "Maintenance / Repairs"),
    "marketing": ("Communication / Marketing", "Communication / Marketing"),
    "other": ("Autre", "Other"),
}

ORDER_STATUS_LABELS = {
    "draft": ("Brouillon", "Draft"),
    "submitted": ("Soumise au fournisseur", "Submitted to supplier"),
    "validated": ("Validée par le fournisseur", "Approved by supplier"),
    "rejected": ("Rejetée par le fournisseur", "Rejected by supplier"),
    "shipped": ("Expédiée", "Shipped"),
    "delivered": ("Livrée / Réceptionnée", "Delivered / Received"),
    "cancelled": ("Annulée", "Cancelled"),
}


def translated_choices(mapping):
    return [(value, tr(*labels)) for value, labels in mapping.items()]


def translated_label(value, mapping):
    labels = mapping.get(value)
    return tr(*labels) if labels else value
