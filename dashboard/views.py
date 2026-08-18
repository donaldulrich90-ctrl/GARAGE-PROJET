import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import ListView

from core.views import GarageRequiredMixin
from diagnostics.models import DiagnosticReport
from invoicing.models import Invoice, Payment
from repair_orders.models import RepairOrder
from workshops.services import get_chart_data, get_section_kpis


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

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)
    now = timezone.now()
    threshold_30 = today + timedelta(days=30)

    # ── Production du jour ────────────────────────────────────────────────────
    production_jour = (
        Invoice.objects.for_garage(garage).filter(issued_at=today)
        .aggregate(t=Sum('total_snapshot'))['t']
    ) or Decimal('0')

    production_hier = (
        Invoice.objects.for_garage(garage).filter(issued_at=yesterday)
        .aggregate(t=Sum('total_snapshot'))['t']
    ) or Decimal('0')

    # ── Encaissé aujourd'hui ──────────────────────────────────────────────────
    encaisse_jour = (
        Payment.objects.filter(invoice__garage=garage, paid_at__date=today)
        .aggregate(t=Sum('amount'))['t']
    ) or Decimal('0')

    # ── Reste à encaisser (cumulatif toutes factures non soldées) ─────────────
    unpaid_qs = Invoice.objects.for_garage(garage).exclude(status=Invoice.STATUS_PAID)
    total_invoiced_unpaid = (
        unpaid_qs.aggregate(t=Sum('total_snapshot'))['t']
    ) or Decimal('0')
    total_paid_on_unpaid = (
        Payment.objects.filter(invoice__in=unpaid_qs)
        .aggregate(t=Sum('amount'))['t']
    ) or Decimal('0')
    reste_global = total_invoiced_unpaid - total_paid_on_unpaid

    # ── Véhicules à l'atelier ─────────────────────────────────────────────────
    vehicles_atelier = RepairOrder.objects.for_garage(garage).exclude(
        status__in=[RepairOrder.STATUS_DELIVERED, RepairOrder.STATUS_CANCELLED]
    ).count()

    vehicles_prets = RepairOrder.objects.for_garage(garage).filter(
        status=RepairOrder.STATUS_READY
    ).count()

    # ── OR en retard ──────────────────────────────────────────────────────────
    or_en_retard = RepairOrder.objects.for_garage(garage).filter(
        expected_at__lt=now,
        expected_at__isnull=False,
    ).exclude(
        status__in=[RepairOrder.STATUS_DELIVERED, RepairOrder.STATUS_CANCELLED]
    ).count()

    # ── Workflow par statut ───────────────────────────────────────────────────
    base_qs = RepairOrder.objects.for_garage(garage)
    workflow = {
        'received': base_qs.filter(status=RepairOrder.STATUS_RECEIVED).count(),
        'diagnosis': base_qs.filter(status=RepairOrder.STATUS_DIAGNOSIS).count(),
        'in_progress': base_qs.filter(status=RepairOrder.STATUS_IN_PROGRESS).count(),
        'ready': base_qs.filter(status=RepairOrder.STATUS_READY).count(),
    }

    # ── Sections KPI (mois en cours) ─────────────────────────────────────────
    section_kpis = get_section_kpis(garage, start_date=month_start, end_date=today)

    # ── Chart 30 jours ────────────────────────────────────────────────────────
    chart_start = today - timedelta(days=29)
    chart_data = get_chart_data(garage, start_date=chart_start, end_date=today, granularity='day')

    # ── OR en cours (table, 10 max) ───────────────────────────────────────────
    open_orders = list(
        RepairOrder.objects.for_garage(garage)
        .exclude(status__in=[RepairOrder.STATUS_DELIVERED, RepairOrder.STATUS_CANCELLED])
        .select_related('vehicle', 'client', 'assigned_mechanic')
        .prefetch_related('tasks__section')
        .annotate(
            task_total=Count('tasks', distinct=True),
            task_done=Count('tasks', filter=Q(tasks__is_done=True), distinct=True),
        )
        .order_by('expected_at', '-received_at')[:10]
    )

    # Post-process: collecter les sections uniques par OR (pas de N+1 grâce au prefetch)
    for order in open_orders:
        seen = {}
        for task in order.tasks.all():
            if task.section_id and task.section_id not in seen:
                seen[task.section_id] = task.section
        order._sections = sorted(seen.values(), key=lambda s: s.display_order)

    # ── Alertes VT & assurances ───────────────────────────────────────────────
    from technical_visits.models import TechnicalVisit
    from insurance.models import Insurance

    vt_expiring = TechnicalVisit.objects.for_garage(garage).filter(
        expiry_date__gte=today, expiry_date__lte=threshold_30
    ).count()
    vt_expired = TechnicalVisit.objects.for_garage(garage).filter(
        expiry_date__lt=today
    ).count()
    ins_expiring = Insurance.objects.for_garage(garage).filter(
        end_date__gte=today, end_date__lte=threshold_30
    ).count()
    ins_expired = Insurance.objects.for_garage(garage).filter(
        end_date__lt=today
    ).count()

    # ── Diagnostics récents (5 derniers) — annotés pour éviter N+1 ───────────
    recent_diagnostics = (
        DiagnosticReport.objects.for_garage(garage)
        .select_related('repair_order__vehicle', 'technician')
        .annotate(codes_count=Count('codes'))
        .order_by('-scan_date')[:5]
    )

    context = {
        "is_platform_view": False,
        "garage": garage,
        # KPIs
        "production_jour": production_jour,
        "production_hier": production_hier,
        "encaisse_jour": encaisse_jour,
        "reste_global": reste_global,
        "vehicles_atelier": vehicles_atelier,
        "vehicles_prets": vehicles_prets,
        "or_en_retard": or_en_retard,
        # Workflow
        "workflow": workflow,
        # Sections du mois
        "section_kpis": section_kpis,
        # Chart 30j
        "chart_data_json": json.dumps(chart_data),
        # OR en cours
        "open_orders": open_orders,
        # Alertes
        "vt_expiring": vt_expiring,
        "vt_expired": vt_expired,
        "ins_expiring": ins_expiring,
        "ins_expired": ins_expired,
        # Diagnostics récents
        "recent_diagnostics": recent_diagnostics,
    }
    return render(request, "dashboard/home.html", context)


class DiagnosticOrderSelectView(GarageRequiredMixin, ListView):
    """Sélecteur d'OR pour créer un nouveau diagnostic."""
    template_name = 'dashboard/diagnostic_order_select.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return (
            RepairOrder.objects.for_garage(self.garage)
            .exclude(status__in=[RepairOrder.STATUS_DELIVERED, RepairOrder.STATUS_CANCELLED])
            .select_related('vehicle', 'client')
            .order_by('-received_at')
        )
