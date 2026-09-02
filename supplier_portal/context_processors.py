from django.db.models import F


def supplier_alerts(request):
    """Alertes visibles dans le portail, sans envoi WhatsApp ou SMS."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not getattr(user, "supplier_id", None):
        return {"supplier_low_stock_count": 0, "supplier_pending_order_count": 0}

    from inventory.models import SupplierOrder, SupplierPart

    supplier = user.supplier
    return {
        "supplier_low_stock_count": SupplierPart.objects.filter(
            supplier=supplier,
            quantity_available__lte=F("alert_threshold"),
        ).count(),
        "supplier_pending_order_count": SupplierOrder.objects.filter(
            supplier=supplier,
            status=SupplierOrder.STATUS_SUBMITTED,
        ).count(),
    }
