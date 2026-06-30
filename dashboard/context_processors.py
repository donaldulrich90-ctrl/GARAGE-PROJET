from django.db.models import F


def stock_alerts(request):
    if (
        request.user.is_authenticated
        and getattr(request.user, "garage", None) is not None
    ):
        from inventory.models import Part
        count = Part.objects.for_garage(request.user.garage).filter(
            quantity_in_stock__lte=F("alert_threshold")
        ).count()
        return {"low_stock_count": count}
    return {"low_stock_count": 0}
