import json
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from django.views.generic import TemplateView

from core.views import GarageRequiredMixin
from expenses.models import Expense
from invoicing.models import Payment
from repair_orders.models import RepairOrder
from workshops.services import get_chart_data, get_section_kpis


def _get_date_range(periode, date_from_str='', date_to_str=''):
    today = timezone.now().date()
    if periode == 'semaine':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif periode == 'mois':
        start = today.replace(day=1)
        end = (date(today.year, today.month % 12 + 1, 1) - timedelta(days=1)
               if today.month < 12 else date(today.year, 12, 31))
    elif periode == 'annee':
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
    elif periode == 'custom':
        try:
            from datetime import datetime
            start = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else today.replace(day=1)
            end = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else today
        except ValueError:
            start = today.replace(day=1)
            end = today
    else:  # jour
        start = today
        end = today
    return start, end


def _get_granularity(start, end):
    delta = (end - start).days
    if delta <= 31:
        return 'day'
    return 'month'


PERIODE_LABELS = {
    'jour': "Aujourd'hui",
    'semaine': 'Cette semaine',
    'mois': 'Ce mois',
    'annee': 'Cette année',
    'custom': 'Période personnalisée',
}


class BilanView(GarageRequiredMixin, TemplateView):
    template_name = 'dashboard/bilan.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
        garage = self.garage

        periode = request.GET.get('periode', 'mois')
        if periode not in PERIODE_LABELS:
            periode = 'mois'

        date_from_str = request.GET.get('date_from', '')
        date_to_str = request.GET.get('date_to', '')
        section_filter_id = request.GET.get('section', '')

        start, end = _get_date_range(periode, date_from_str, date_to_str)
        granularity = _get_granularity(start, end)

        section_filter = None
        if section_filter_id:
            try:
                from workshops.models import WorkshopSection
                section_filter = WorkshopSection.objects.for_garage(garage).get(pk=int(section_filter_id))
            except Exception:
                section_filter_id = ''

        # ─── Recettes encaissées ─────────────────────────────────────────────
        pay_qs = Payment.objects.filter(
            invoice__garage=garage,
            paid_at__date__gte=start,
            paid_at__date__lte=end,
        )
        recettes = pay_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # ─── Production facturée (total_snapshot) ───────────────────────────
        from invoicing.models import Invoice, InvoiceSectionBreakdown
        inv_qs = Invoice.objects.for_garage(garage).filter(issued_at__gte=start, issued_at__lte=end)
        production = inv_qs.aggregate(total=Sum('total_snapshot'))['total'] or Decimal('0')

        # ─── Reste à encaisser ───────────────────────────────────────────────
        from invoicing.models import PaymentSectionAllocation
        reste = production - recettes

        # ─── Dépenses ────────────────────────────────────────────────────────
        depenses_qs = Expense.objects.for_garage(garage).filter(date__gte=start, date__lte=end)
        depenses_total = depenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        depenses_by_cat = (
            depenses_qs.values('category').annotate(total=Sum('amount')).order_by('-total')
        )
        depenses_by_cat_list = [
            {'category': Expense(category=row['category']).get_category_display(), 'total': row['total']}
            for row in depenses_by_cat
        ]
        salaires = (
            depenses_qs.filter(category=Expense.CAT_SALARY)
            .aggregate(total=Sum('amount'))['total'] or Decimal('0')
        )

        # ─── Ordres de réparation ─────────────────────────────────────────────
        orders_qs = RepairOrder.objects.for_garage(garage).filter(
            received_at__date__gte=start, received_at__date__lte=end
        )
        orders_by_status = []
        for code, label in RepairOrder.STATUS_CHOICES:
            count = orders_qs.filter(status=code).count()
            if count:
                orders_by_status.append({'status': label, 'count': count})
        orders_total = orders_qs.count()
        panier_moyen = (production / orders_total) if orders_total else Decimal('0')

        solde = recettes - depenses_total

        # ─── KPIs par section ────────────────────────────────────────────────
        section_kpis = get_section_kpis(
            garage,
            start_date=start,
            end_date=end,
            section_id=int(section_filter_id) if section_filter_id else None,
        )

        # ─── Données graphiques Chart.js ─────────────────────────────────────
        chart_data = get_chart_data(garage, start, end, granularity)

        # ─── Sections disponibles (filtre) ───────────────────────────────────
        from workshops.models import WorkshopSection
        all_sections = list(WorkshopSection.objects.for_garage(garage).filter(is_active=True).order_by('display_order', 'name'))

        ctx.update({
            'periode': periode,
            'periode_label': PERIODE_LABELS[periode],
            'periode_choices': list(PERIODE_LABELS.items()),
            'start': start,
            'end': end,
            'date_from': date_from_str,
            'date_to': date_to_str,
            'section_filter_id': section_filter_id,
            'all_sections': all_sections,

            # KPIs globaux
            'recettes': recettes,
            'production': production,
            'reste': reste,
            'depenses_total': depenses_total,
            'depenses_by_cat': depenses_by_cat_list,
            'salaires': salaires,
            'solde': solde,
            'orders_total': orders_total,
            'orders_by_status': orders_by_status,
            'panier_moyen': panier_moyen,
            'today': timezone.now().date(),

            # Sections
            'section_kpis': section_kpis,

            # Graphiques
            'chart_labels_json': json.dumps(chart_data['labels']),
            'chart_production_datasets_json': json.dumps(chart_data['production_datasets']),
            'chart_payment_datasets_json': json.dumps(chart_data['payment_datasets']),
            'chart_bar_labels_json': json.dumps(chart_data['bar_labels']),
            'chart_bar_production_json': json.dumps(chart_data['bar_production']),
            'chart_bar_encaisse_json': json.dumps(chart_data['bar_encaisse']),
            'chart_donut_labels_json': json.dumps(chart_data['donut_labels']),
            'chart_donut_data_json': json.dumps(chart_data['donut_data']),
            'chart_donut_colors_json': json.dumps(chart_data['donut_colors']),
        })
        return ctx
