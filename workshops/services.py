"""Service central pour calculs financiers par section."""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction


# ─── Ventilation d'un OR par section ─────────────────────────────────────────

def get_order_section_breakdown(repair_order):
    """
    Renvoie un dict {section_id_or_None: dict_données} pour un OR.
    La clé None représente les tâches/pièces sans section ('Non attribué').
    """
    result = {}

    def _init(key, section):
        result[key] = {
            'section': section,
            'labor': Decimal('0'),
            'parts': Decimal('0'),
            'task_count': 0,
            'done_count': 0,
            'mechanics': set(),
            'tasks': [],
            'parts_list': [],
        }

    for task in repair_order.tasks.select_related('section', 'mechanic').all():
        key = task.section_id
        if key not in result:
            _init(key, task.section)
        result[key]['labor'] += task.cost
        result[key]['task_count'] += 1
        if task.is_done:
            result[key]['done_count'] += 1
        if task.mechanic:
            result[key]['mechanics'].add(task.mechanic)
        result[key]['tasks'].append(task)

    for op in repair_order.parts_used.select_related('section', 'part').all():
        key = op.section_id
        if key not in result:
            _init(key, op.section)
        result[key]['parts'] += op.line_total
        result[key]['parts_list'].append(op)

    for key in result:
        result[key]['total'] = result[key]['labor'] + result[key]['parts']
        result[key]['mechanics'] = list(result[key]['mechanics'])

    return result


def get_order_section_breakdown_list(repair_order):
    """Renvoie la même ventilation sous forme de liste ordonnée."""
    raw = get_order_section_breakdown(repair_order)
    items = list(raw.values())
    items.sort(key=lambda x: (x['section'].display_order if x['section'] else 999, x['section'].name if x['section'] else ''))
    return items


# ─── Snapshot facture ─────────────────────────────────────────────────────────

@transaction.atomic
def create_invoice_breakdown(invoice):
    """
    Crée les lignes InvoiceSectionBreakdown et met à jour total_snapshot sur Invoice.
    Appelé à la création d'une facture.
    """
    from invoicing.models import InvoiceSectionBreakdown

    InvoiceSectionBreakdown.objects.filter(invoice=invoice).delete()

    breakdown_data = get_order_section_breakdown(invoice.repair_order)
    total = Decimal('0')

    for section_id, data in breakdown_data.items():
        InvoiceSectionBreakdown.objects.create(
            invoice=invoice,
            section=data['section'],
            labor_amount=data['labor'],
            parts_amount=data['parts'],
            total_amount=data['total'],
        )
        total += data['total']

    invoice.total_snapshot = total
    invoice.save(update_fields=['total_snapshot', 'updated_at'])
    return total


def backfill_invoice_breakdown(invoice):
    """
    Rétro-remplit le breakdown pour une facture existante.
    Si aucune donnée de section disponible, crée une ligne unique section=None.
    """
    from invoicing.models import InvoiceSectionBreakdown

    if InvoiceSectionBreakdown.objects.filter(invoice=invoice).exists():
        return

    breakdown_data = get_order_section_breakdown(invoice.repair_order)

    if breakdown_data:
        total = Decimal('0')
        for section_id, data in breakdown_data.items():
            InvoiceSectionBreakdown.objects.create(
                invoice=invoice,
                section=data['section'],
                labor_amount=data['labor'],
                parts_amount=data['parts'],
                total_amount=data['total'],
            )
            total += data['total']
        invoice.total_snapshot = total
    else:
        ro = invoice.repair_order
        total = ro.total_cost if ro else Decimal('0')
        InvoiceSectionBreakdown.objects.create(
            invoice=invoice,
            section=None,
            labor_amount=ro.total_labor if ro else Decimal('0'),
            parts_amount=ro.total_parts if ro else Decimal('0'),
            total_amount=total,
        )
        invoice.total_snapshot = total

    invoice.save(update_fields=['total_snapshot', 'updated_at'])


# ─── Allocations de paiement ─────────────────────────────────────────────────

@transaction.atomic
def create_payment_allocations(payment):
    """
    Crée les PaymentSectionAllocation proportionnellement aux InvoiceSectionBreakdown.
    Le dernier enregistrement absorbe l'arrondi (somme exacte = payment.amount).
    """
    from invoicing.models import InvoiceSectionBreakdown, PaymentSectionAllocation

    PaymentSectionAllocation.objects.filter(payment=payment).delete()

    breakdowns = list(InvoiceSectionBreakdown.objects.filter(invoice=payment.invoice))

    if not breakdowns:
        PaymentSectionAllocation.objects.create(
            payment=payment, section=None, amount=payment.amount
        )
        return

    invoice_total = sum(bd.total_amount for bd in breakdowns)

    if invoice_total == 0:
        PaymentSectionAllocation.objects.create(
            payment=payment, section=None, amount=payment.amount
        )
        return

    allocated = Decimal('0')
    for i, bd in enumerate(breakdowns):
        if i == len(breakdowns) - 1:
            alloc_amount = payment.amount - allocated
        else:
            alloc_amount = (bd.total_amount / invoice_total * payment.amount).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        PaymentSectionAllocation.objects.create(
            payment=payment,
            section=bd.section,
            amount=alloc_amount,
        )
        allocated += alloc_amount


# ─── KPIs par section ────────────────────────────────────────────────────────

def get_section_kpis(garage, start_date=None, end_date=None, section_id=None):
    """
    Renvoie une liste de dicts KPI par section pour la période donnée.
    Inclut production facturée, encaissé, reste, OR, interventions, part_ca.
    """
    from invoicing.models import InvoiceSectionBreakdown, PaymentSectionAllocation
    from repair_orders.models import RepairOrderTask
    from django.db.models import Count, Sum

    bd_qs = InvoiceSectionBreakdown.objects.filter(invoice__garage=garage)
    if start_date:
        bd_qs = bd_qs.filter(invoice__issued_at__gte=start_date)
    if end_date:
        bd_qs = bd_qs.filter(invoice__issued_at__lte=end_date)
    if section_id:
        bd_qs = bd_qs.filter(section_id=section_id)

    production_map = {}
    for bd in bd_qs.select_related('section'):
        key = bd.section_id
        if key not in production_map:
            production_map[key] = {'section': bd.section, 'production': Decimal('0'), 'invoice_ids': set()}
        production_map[key]['production'] += bd.total_amount
        production_map[key]['invoice_ids'].add(bd.invoice_id)

    alloc_qs = PaymentSectionAllocation.objects.filter(payment__invoice__garage=garage)
    if start_date:
        alloc_qs = alloc_qs.filter(payment__paid_at__date__gte=start_date)
    if end_date:
        alloc_qs = alloc_qs.filter(payment__paid_at__date__lte=end_date)
    if section_id:
        alloc_qs = alloc_qs.filter(section_id=section_id)

    encaisse_map = {}
    for alloc in alloc_qs.select_related('section'):
        key = alloc.section_id
        encaisse_map.setdefault(key, Decimal('0'))
        encaisse_map[key] += alloc.amount

    task_qs = RepairOrderTask.objects.filter(repair_order__garage=garage)
    if start_date:
        task_qs = task_qs.filter(repair_order__received_at__date__gte=start_date)
    if end_date:
        task_qs = task_qs.filter(repair_order__received_at__date__lte=end_date)
    if section_id:
        task_qs = task_qs.filter(section_id=section_id)

    task_counts = {
        row['section_id']: row['count']
        for row in task_qs.values('section_id').annotate(count=Count('id'))
    }
    or_counts = {
        row['section_id']: row['count']
        for row in task_qs.values('section_id').annotate(count=Count('repair_order_id', distinct=True))
    }

    all_keys = set(list(production_map.keys()) + list(encaisse_map.keys()))
    total_production = sum(v['production'] for v in production_map.values())

    result = []
    for key in all_keys:
        p_data = production_map.get(key, {})
        production = p_data.get('production', Decimal('0'))
        encaisse = encaisse_map.get(key, Decimal('0'))
        result.append({
            'section': p_data.get('section'),
            'section_id': key,
            'production': production,
            'encaisse': encaisse,
            'reste': production - encaisse,
            'or_count': or_counts.get(key, 0),
            'interventions': task_counts.get(key, 0),
            'part_ca': round(production / total_production * 100, 1) if total_production else 0,
        })

    result.sort(key=lambda x: x['production'], reverse=True)
    return result


# ─── Données graphiques Chart.js ─────────────────────────────────────────────

def get_chart_data(garage, start_date, end_date, granularity='month'):
    """
    Renvoie les données Chart.js pour les 4 graphiques de la page bilan.
    granularity: 'day' | 'month'
    """
    from invoicing.models import InvoiceSectionBreakdown, PaymentSectionAllocation
    from workshops.models import WorkshopSection
    from django.db.models import Sum
    from django.db.models.functions import TruncDay, TruncMonth

    sections = list(
        WorkshopSection.objects.for_garage(garage).filter(is_active=True).order_by('display_order', 'name')
    )

    trunc_fn = TruncDay if granularity == 'day' else TruncMonth

    # Production par section + période
    prod_qs = (
        InvoiceSectionBreakdown.objects.filter(
            invoice__garage=garage,
            invoice__issued_at__gte=start_date,
            invoice__issued_at__lte=end_date,
        )
        .annotate(period=trunc_fn('invoice__issued_at'))
        .values('period', 'section_id')
        .annotate(total=Sum('total_amount'))
        .order_by('period')
    )

    date_fmt = '%d/%m' if granularity == 'day' else '%m/%Y'
    prod_lookup = {}
    periods_set = set()
    for row in prod_qs:
        if row['period']:
            p = row['period'].strftime(date_fmt)
            periods_set.add(p)
            prod_lookup[(p, row['section_id'])] = float(row['total'] or 0)

    # Encaissements par section + période
    pay_qs = (
        PaymentSectionAllocation.objects.filter(
            payment__invoice__garage=garage,
            payment__paid_at__date__gte=start_date,
            payment__paid_at__date__lte=end_date,
        )
        .annotate(period=trunc_fn('payment__paid_at'))
        .values('period', 'section_id')
        .annotate(total=Sum('amount'))
        .order_by('period')
    )

    pay_lookup = {}
    for row in pay_qs:
        if row['period']:
            p = row['period'].strftime(date_fmt)
            periods_set.add(p)
            pay_lookup[(p, row['section_id'])] = float(row['total'] or 0)

    periods = sorted(periods_set)

    production_datasets = []
    payment_datasets = []
    bar_labels = []
    bar_production = []
    bar_encaisse = []
    donut_labels = []
    donut_data = []
    donut_colors = []

    for s in sections:
        prod_series = [prod_lookup.get((p, s.pk), 0) for p in periods]
        pay_series = [pay_lookup.get((p, s.pk), 0) for p in periods]
        total_prod = sum(prod_series)
        total_pay = sum(pay_series)

        color = s.color
        production_datasets.append({
            'label': s.name,
            'data': prod_series,
            'borderColor': color,
            'backgroundColor': color + '22',
            'tension': 0.4,
            'fill': False,
        })
        payment_datasets.append({
            'label': s.name,
            'data': pay_series,
            'borderColor': color,
            'backgroundColor': color + '22',
            'tension': 0.4,
            'fill': False,
        })
        bar_labels.append(s.name)
        bar_production.append(total_prod)
        bar_encaisse.append(total_pay)

        if total_prod > 0:
            donut_labels.append(s.name)
            donut_data.append(total_prod)
            donut_colors.append(color)

    return {
        'labels': periods,
        'production_datasets': production_datasets,
        'payment_datasets': payment_datasets,
        'bar_labels': bar_labels,
        'bar_production': bar_production,
        'bar_encaisse': bar_encaisse,
        'donut_labels': donut_labels,
        'donut_data': donut_data,
        'donut_colors': donut_colors,
    }
