"""Catalogue des options (features) et matrice par plan d'abonnement.

Utilisé par le back-office super-admin et par le "gating" des modules :
    garage.has_feature("hr")  ->  True/False
    "hr" in garage.active_features  (dans les templates)
"""

# Clé technique -> libellé affiché. Ajoutez/retirez selon vos modules.
FEATURES = {
    "repair_orders":    "Ordres de réparation",
    "inventory":        "Stock / Pièces",
    "invoicing":        "Facturation & Caisse",
    "expenses":         "Dépenses",
    "hr":               "Ressources humaines",
    "technical_visits": "Visites techniques",
    "insurance":        "Assurances",
    "taxes":            "Taxes & Impôts",
    "messaging":        "Messagerie WhatsApp",
    "key_board":        "Tableau à clés",
    "supplier_market":  "Marketplace fournisseurs",
    "workshops":        "Sections atelier",
    "diagnostics":      "Diagnostics DTC",
    "reports":          "Rapports avancés",
}

# Options ACTIVÉES PAR DÉFAUT pour chaque plan (modifiable librement).
#   Starter  : l'essentiel de l'exploitation d'un garage.
#   Pro      : Starter + suivi, RH, communication et rapports.
#   Business : tout, y compris les modules avancés (marketplace, ateliers, diagnostics).
PLAN_FEATURES = {
    "starter": {
        "repair_orders", "inventory", "invoicing", "expenses", "key_board",
    },
    "pro": {
        "repair_orders", "inventory", "invoicing", "expenses", "key_board",
        "hr", "technical_visits", "insurance", "taxes", "messaging", "reports",
    },
    "business": set(FEATURES.keys()),  # tout
}


def default_features_for_plan(plan):
    """Ensemble des options activées par défaut pour un plan donné."""
    return set(PLAN_FEATURES.get(plan, set()))
