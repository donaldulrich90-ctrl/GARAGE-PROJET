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


# ─────────────────────────────────────────────────────────────────────────────
# Sélecteur de période pour la grande courbe « Production du garage ».
# clé GET (?g=) -> (nb de jours OU 'year', granularité, libellé)
# ─────────────────────────────────────────────────────────────────────────────
CHART_PERIODS = {
    "7": (7, "day", "7 jours"),
    "30": (30, "day", "30 jours"),
    "90": (90, "month", "3 mois"),
    "year": ("year", "month", "Cette année"),
}
CHART_DEFAULT = "30"


# ─────────────────────────────────────────────────────────────────────────────
# Mapping DOCUMENTÉ statut RepairOrder -> étape visuelle du workflow atelier.
#
# ⚠️ Le modèle RepairOrder ne définit que 6 statuts :
#     received, diagnosis, in_progress, ready, delivered, cancelled.
# Il n'existe PAS de statut distinct « Attente client » ni « Contrôle ».
# On NE fabrique donc pas ces colonnes : le pipeline atelier affiche les 4
# étapes réelles où un véhicule est physiquement pris en charge. Les statuts
# delivered / cancelled sortent du pipeline (le véhicule a quitté l'atelier).
#
# Si un jour de nouveaux statuts sont ajoutés au modèle, il suffit de compléter
# cette liste : plusieurs statuts internes peuvent être regroupés sous une même
# étape visuelle en réutilisant la même clé.
# ─────────────────────────────────────────────────────────────────────────────
WORKFLOW_STEPS_DEF = [
    ("reception", "Réception", [RepairOrder.STATUS_RECEIVED]),
    ("diagnostic", "Diagnostic", [RepairOrder.STATUS_DIAGNOSIS]),
    ("reparation", "En réparation", [RepairOrder.STATUS_IN_PROGRESS]),
    ("pret", "Prêt", [RepairOrder.STATUS_READY]),
]


def _chart_bounds(period_key, today):
    """Renvoie (start_date, end_date, granularity) pour la clé de période."""
    days, granularity, _label = CHART_PERIODS[period_key]
    if days == "year":
        start = today.replace(month=1, day=1)
    else:
        start = today - timedelta(days=days - 1)
    return start, today, granularity


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

    # ── Production du jour (facturée, PAS les paiements) ───────────────────────
    production_jour = (
        Invoice.objects.for_garage(garage).filter(issued_at=today)
        .aggregate(t=Sum('total_snapshot'))['t']
    ) or Decimal('0')

    production_hier = (
        Invoice.objects.for_garage(garage).filter(issued_at=yesterday)
        .aggregate(t=Sum('total_snapshot'))['t']
    ) or Decimal('0')

    # Variation vs hier — uniquement si la veille a des données (pas d'artifice)
    production_var_pct = None
    production_var_dir = None
    if production_hier and production_hier > 0:
        delta = (production_jour - production_hier) / production_hier * 100
        production_var_pct = abs(round(delta, 1))
        production_var_dir = 'up' if delta > 0 else ('down' if delta < 0 else 'flat')

    # ── Encaissé aujourd'hui (paiements réellement reçus) ──────────────────────
    encaisse_jour = (
        Payment.objects.filter(invoice__garage=garage, paid_at__date=today)
        .aggregate(t=Sum('amount'))['t']
    ) or Decimal('0')

    # ── Reste à encaisser (comptable : dû sur toutes les factures non soldées) ─
    unpaid_qs = Invoice.objects.for_garage(garage).exclude(status=Invoice.STATUS_PAID)
    total_invoiced_unpaid = (
        unpaid_qs.aggregate(t=Sum('total_snapshot'))['t']
    ) or Decimal('0')
    total_paid_on_unpaid = (
        Payment.objects.filter(invoice__in=unpaid_qs)
        .aggregate(t=Sum('amount'))['t']
    ) or Decimal('0')
    reste_global = total_invoiced_unpaid - total_paid_on_unpaid
    unpaid_invoices_count = unpaid_qs.count()

    # ── Véhicules à l'atelier / prêts ──────────────────────────────────────────
    base_qs = RepairOrder.objects.for_garage(garage)
    vehicles_atelier = base_qs.exclude(
        status__in=[RepairOrder.STATUS_DELIVERED, RepairOrder.STATUS_CANCELLED]
    ).count()
    vehicles_prets = base_qs.filter(status=RepairOrder.STATUS_READY).count()

    # ── OR en retard (livraison prévue dépassée ET non livré/annulé) ───────────
    or_en_retard = base_qs.filter(
        expected_at__lt=now,
        expected_at__isnull=False,
    ).exclude(
        status__in=[RepairOrder.STATUS_DELIVERED, RepairOrder.STATUS_CANCELLED]
    ).count()

    # ── Workflow atelier — 1 seule requête groupée par statut ──────────────────
    status_counts = {
        row['status']: row['n']
        for row in base_qs.values('status').annotate(n=Count('id'))
    }
    workflow_steps = [
        {'key': key, 'label': label, 'count': sum(status_counts.get(s, 0) for s in statuses)}
        for key, label, statuses in WORKFLOW_STEPS_DEF
    ]
    delivered_today = base_qs.filter(
        status=RepairOrder.STATUS_DELIVERED, delivered_at__date=today
    ).count()

    # ── KPIs par section (mois en cours) — service central partagé ─────────────
    # section_kpis : trié par production décroissante → utilisé pour le CLASSEMENT.
    section_kpis = get_section_kpis(garage, start_date=month_start, end_date=today)

    # section_cards : TOUTES les sections actives (ordre d'affichage), zéro-remplies
    # si aucune activité ce mois-ci, pour une grille de cartes stable.
    from workshops.models import WorkshopSection
    kpi_by_section = {k['section_id']: k for k in section_kpis}
    section_cards = []
    for sec in WorkshopSection.objects.for_garage(garage).filter(is_active=True).order_by('display_order', 'name'):
        k = kpi_by_section.get(sec.pk)
        section_cards.append({
            'section': sec,
            'production': k['production'] if k else Decimal('0'),
            'encaisse': k['encaisse'] if k else Decimal('0'),
            'reste': k['reste'] if k else Decimal('0'),
            'or_count': k['or_count'] if k else 0,
            'interventions': k['interventions'] if k else 0,
            'part_ca': k['part_ca'] if k else 0,
        })

    # ── Grande courbe : production par section, période sélectionnable ─────────
    chart_period = request.GET.get('g', CHART_DEFAULT)
    if chart_period not in CHART_PERIODS:
        chart_period = CHART_DEFAULT
    chart_start, chart_end, chart_gran = _chart_bounds(chart_period, today)
    chart_data = get_chart_data(garage, start_date=chart_start, end_date=chart_end, granularity=chart_gran)
    chart_period_choices = [(k, v[2]) for k, v in CHART_PERIODS.items()]

    # ── OR en cours (table, 10 max) — pas de N+1 grâce aux prefetch ────────────
    open_orders = list(
        base_qs
        .exclude(status__in=[RepairOrder.STATUS_DELIVERED, RepairOrder.STATUS_CANCELLED])
        .select_related('vehicle', 'client', 'assigned_mechanic')
        .prefetch_related('tasks__section', 'parts_used')
        .annotate(
            task_total=Count('tasks', distinct=True),
            task_done=Count('tasks', filter=Q(tasks__is_done=True), distinct=True),
        )
        .order_by('expected_at', '-received_at')[:10]
    )

    for order in open_orders:
        # Sections distinctes ayant travaillé sur l'OR (via prefetch, sans requête).
        # NB : pas de préfixe '_' → les templates Django interdisent l'accès aux
        # attributs commençant par un underscore.
        seen = {}
        for task in order.tasks.all():
            if task.section_id and task.section_id not in seen:
                seen[task.section_id] = task.section
        order.sections_worked = sorted(seen.values(), key=lambda s: s.display_order)
        # Montant = coût réel (main d'œuvre + pièces), calculé depuis le prefetch
        order.amount_total = order.total_cost
        # Progression = tâches terminées / total (jamais basée sur le montant)
        order.progress_pct = (
            int(round(order.task_done / order.task_total * 100))
            if order.task_total else 0
        )

    # ── Alertes VT & assurances ────────────────────────────────────────────────
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

    # ── Stock faible — MÊME règle que le module Stock (pièces sous le seuil) ────
    from django.db.models import F
    from inventory.models import Part
    low_stock_count = Part.objects.for_garage(garage).filter(
        quantity_in_stock__lte=F('alert_threshold')
    ).count()

    # ── Diagnostics récents (5 derniers) — annotés pour éviter N+1 ─────────────
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
        "production_var_pct": production_var_pct,
        "production_var_dir": production_var_dir,
        "encaisse_jour": encaisse_jour,
        "reste_global": reste_global,
        "unpaid_invoices_count": unpaid_invoices_count,
        "vehicles_atelier": vehicles_atelier,
        "vehicles_prets": vehicles_prets,
        "or_en_retard": or_en_retard,
        # Workflow
        "workflow_steps": workflow_steps,
        "delivered_today": delivered_today,
        # Sections du mois
        "section_kpis": section_kpis,
        "section_cards": section_cards,
        # Grande courbe
        "chart_data_json": json.dumps(chart_data),
        "chart_period": chart_period,
        "chart_period_choices": chart_period_choices,
        # OR en cours
        "open_orders": open_orders,
        # Alertes
        "low_stock_count": low_stock_count,
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
