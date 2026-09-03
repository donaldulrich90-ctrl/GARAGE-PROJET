"""Filtres d'affichage partagés du tableau de bord."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

# Espace insécable — évite qu'un montant soit coupé en fin de ligne.
_NBSP = " "


@register.filter(name="fcfa")
def fcfa(value):
    """
    Formate un montant en séparant les milliers par une espace insécable,
    sans décimales. Ex : 485000 -> "485 000". Le suffixe « FCFA » reste à
    la charge du template pour rester flexible.

    Logique unique de formatage des montants (ne pas dupliquer ailleurs).
    """
    if value is None or value == "":
        return "0"
    try:
        number = int(round(float(Decimal(str(value)))))
    except (TypeError, ValueError, InvalidOperation):
        return value
    grouped = f"{abs(number):,}".replace(",", _NBSP)
    return f"-{grouped}" if number < 0 else grouped
