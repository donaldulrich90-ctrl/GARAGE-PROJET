from datetime import date, timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from core.views import GarageRequiredMixin
from expenses.models import Expense
from invoicing.models import Payment
from repair_orders.models import RepairOrder


def _get_date_range(periode):
    today = timezone.now().date()
    if periode == "semaine":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif periode == "mois":
        start = today.replace(day=1)
        end = date(today.year, today.month % 12 + 1, 1) - timedelta(days=1) if today.month < 12 else date(today.year, 12, 31)
    elif periode == "annee":
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
    else:
        start = today
        end = today
    return start, end


PERIODE_LABELS = {
    "jour": "Aujourd'hui",
    "semaine": "Cette semaine",
    "mois": "Ce mois",
    "annee": "Cette année",
}


class BilanView(GarageRequiredMixin, TemplateView):
    template_name = "dashboard/bilan.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        periode = self.request.GET.get("periode", "mois")
        if periode not in PERIODE_LABELS:
            periode = "mois"

        start, end = _get_date_range(periode)

        recettes = (
            Payment.objects.filter(invoice__garage=self.garage, paid_at__date__gte=start, paid_at__date__lte=end)
            .aggregate(total=Sum("amount"))["total"] or 0
        )

        depenses_qs = Expense.objects.for_garage(self.garage).filter(date__gte=start, date__lte=end)
        depenses_total = depenses_qs.aggregate(total=Sum("amount"))["total"] or 0
        depenses_by_cat = (
            depenses_qs.values("category").annotate(total=Sum("amount")).order_by("-total")
        )
        depenses_by_cat_list = [
            {"category": Expense(category=row["category"]).get_category_display(), "total": row["total"]}
            for row in depenses_by_cat
        ]

        salaires = (
            depenses_qs.filter(category=Expense.CAT_SALARY)
            .aggregate(total=Sum("amount"))["total"] or 0
        )

        orders_qs = RepairOrder.objects.for_garage(self.garage).filter(received_at__date__gte=start, received_at__date__lte=end)
        orders_by_status = []
        for code, label in RepairOrder.STATUS_CHOICES:
            count = orders_qs.filter(status=code).count()
            if count:
                orders_by_status.append({"status": label, "count": count})
        orders_total = orders_qs.count()

        solde = recettes - depenses_total

        ctx.update({
            "periode": periode,
            "periode_label": PERIODE_LABELS[periode],
            "periode_choices": list(PERIODE_LABELS.items()),
            "start": start,
            "end": end,
            "recettes": recettes,
            "depenses_total": depenses_total,
            "depenses_by_cat": depenses_by_cat_list,
            "salaires": salaires,
            "solde": solde,
            "orders_total": orders_total,
            "orders_by_status": orders_by_status,
            "today": timezone.now().date(),
        })
        return ctx
