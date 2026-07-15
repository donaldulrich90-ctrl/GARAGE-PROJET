from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from clients.models import Vehicle
from inventory.models import Part
from invoicing.models import Invoice
from repair_orders.models import RepairOrder


@login_required
def home(request):
    user = request.user
    garage = user.garage

    if user.is_superuser and garage is None:
        from tenants.models import Garage

        context = {
            "is_platform_view": True,
            "total_garages_active": Garage.objects.filter(is_active=True).count(),
            "total_garages": Garage.objects.count(),
        }
        return render(request, "dashboard/platform_home.html", context)

    orders = RepairOrder.objects.for_garage(garage)
    parts = Part.objects.for_garage(garage)

    today = date.today()
    threshold = today + timedelta(days=30)

    from technical_visits.models import TechnicalVisit
    from insurance.models import Insurance

    vt_expiring = TechnicalVisit.objects.for_garage(garage).filter(
        expiry_date__gte=today, expiry_date__lte=threshold
    ).count()
    vt_expired = TechnicalVisit.objects.for_garage(garage).filter(
        expiry_date__lt=today
    ).count()

    ins_expiring = Insurance.objects.for_garage(garage).filter(
        end_date__gte=today, end_date__lte=threshold
    ).count()
    ins_expired = Insurance.objects.for_garage(garage).filter(
        end_date__lt=today
    ).count()

    context = {
        "is_platform_view": False,
        "garage": garage,
        "orders_open": orders.exclude(
            status__in=[RepairOrder.STATUS_DELIVERED, RepairOrder.STATUS_CANCELLED]
        ).count(),
        "orders_ready": orders.filter(status=RepairOrder.STATUS_READY).count(),
        "vehicles_count": Vehicle.objects.for_garage(garage).count(),
        "low_stock_parts": [p for p in parts if p.needs_reorder],
        "unpaid_invoices": Invoice.objects.for_garage(garage).exclude(
            status=Invoice.STATUS_PAID
        ),
        "recent_orders": orders[:10],
        "vt_expiring": vt_expiring,
        "vt_expired": vt_expired,
        "ins_expiring": ins_expiring,
        "ins_expired": ins_expired,
    }
    return render(request, "dashboard/home.html", context)
