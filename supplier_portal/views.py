import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from core.i18n import (
    EXPENSE_CATEGORY_LABELS,
    MOVEMENT_LABELS,
    ORDER_STATUS_LABELS,
    PAYMENT_LABELS,
    PERIOD_LABELS,
    tr,
    translated_choices,
    translated_label,
)
from inventory import services as order_services
from inventory.models import SupplierExpense, SupplierOrder, SupplierPart, SupplierStockMovement

from .decorators import SupplierRequiredMixin, supplier_required
from .forms import (
    OrderRejectionForm,
    SupplierExpenseForm,
    SupplierPartOwnForm,
    SupplierProfileForm,
    SupplierStockMovementForm,
)


PERIOD_CODES = tuple(PERIOD_LABELS)


def _period_choices():
    return translated_choices(PERIOD_LABELS)


def _period_bounds(period):
    today = timezone.localdate()
    if period == "semaine":
        return today - timedelta(days=today.weekday()), today
    if period == "mois":
        return today.replace(day=1), today
    return today, today


def _sales_queryset(supplier):
    return SupplierStockMovement.objects.filter(
        supplier_part__supplier=supplier,
        movement_type=SupplierStockMovement.MOVEMENT_OUT,
    ).select_related("supplier_part__catalog_part", "destination_garage", "source_order")


def _sales_total(queryset):
    amount = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    return queryset.aggregate(
        total=Coalesce(
            Sum(amount),
            Decimal("0.00"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
    )["total"]


def _period_summary(supplier, period):
    start, end = _period_bounds(period)
    sales = _sales_queryset(supplier).filter(created_at__date__range=(start, end))
    expenses = SupplierExpense.objects.filter(supplier=supplier, date__range=(start, end))
    revenue = _sales_total(sales)
    expense_total = expenses.aggregate(
        total=Coalesce(
            Sum("amount"),
            Decimal("0.00"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
    )["total"]
    return {
        "period": period,
        "label": translated_label(period, PERIOD_LABELS),
        "start": start,
        "end": end,
        "revenue": revenue,
        "expenses": expense_total,
        "net": revenue - expense_total,
        "units_sold": sales.aggregate(total=Coalesce(Sum("quantity"), 0))["total"],
        "sales_count": sales.count(),
    }


class DashboardView(SupplierRequiredMixin, TemplateView):
    template_name = "supplier_portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        supplier = self.supplier
        offers = SupplierPart.objects.filter(supplier=supplier).select_related("catalog_part")
        low_stock = offers.filter(quantity_available__lte=F("alert_threshold")).order_by("quantity_available")
        stock_value_expr = ExpressionWrapper(
            F("quantity_available") * F("unit_price"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
        ctx.update({
            "supplier": supplier,
            "offer_count": offers.count(),
            "total_stock": offers.aggregate(t=Sum("quantity_available"))["t"] or 0,
            "stock_value": offers.aggregate(
                total=Coalesce(
                    Sum(stock_value_expr),
                    Decimal("0.00"),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )["total"],
            "low_stock": low_stock[:10],
            "low_stock_count": low_stock.count(),
            "pending_order_count": SupplierOrder.objects.filter(
                supplier=supplier,
                status=SupplierOrder.STATUS_SUBMITTED,
            ).count(),
            "period_summaries": [
                _period_summary(supplier, "jour"),
                _period_summary(supplier, "semaine"),
                _period_summary(supplier, "mois"),
            ],
            "recent_sales": _sales_queryset(supplier).order_by("-created_at")[:8],
            "recent_movements": SupplierStockMovement.objects.filter(
                supplier_part__supplier=supplier
            ).select_related("supplier_part__catalog_part", "destination_garage").order_by("-created_at")[:10],
        })
        return ctx


class MyOffersListView(SupplierRequiredMixin, ListView):
    template_name = "supplier_portal/offer_list.html"
    context_object_name = "offers"
    paginate_by = 50

    def get_queryset(self):
        qs = SupplierPart.objects.filter(supplier=self.supplier).select_related("catalog_part", "catalog_part__category")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(catalog_part__name__icontains=q) | qs.filter(catalog_part__reference__icontains=q)
        return qs.order_by("catalog_part__name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class MyOfferCreateView(SupplierRequiredMixin, CreateView):
    template_name = "supplier_portal/offer_form.html"
    form_class = SupplierPartOwnForm
    success_url = reverse_lazy("supplier_portal:offer_list")

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        # Le SupplierPart hérite du garage — mais dans le portail fournisseur,
        # le supplier n'est rattaché qu'à un seul garage (le sien à l'origine).
        form.instance.garage = self.supplier.garage
        messages.success(self.request, tr(
            "Pièce ajoutée à votre stock.", "Part added to your stock."
        ))
        return super().form_valid(form)


class MyOfferUpdateView(SupplierRequiredMixin, UpdateView):
    template_name = "supplier_portal/offer_form.html"
    form_class = SupplierPartOwnForm
    success_url = reverse_lazy("supplier_portal:offer_list")

    def get_queryset(self):
        return SupplierPart.objects.filter(supplier=self.supplier)

    def form_valid(self, form):
        messages.success(self.request, tr("Pièce mise à jour.", "Part updated."))
        return super().form_valid(form)


class MyOfferDeleteView(SupplierRequiredMixin, DeleteView):
    template_name = "supplier_portal/offer_confirm_delete.html"
    success_url = reverse_lazy("supplier_portal:offer_list")

    def get_queryset(self):
        return SupplierPart.objects.filter(supplier=self.supplier)


class MovementListView(SupplierRequiredMixin, ListView):
    template_name = "supplier_portal/movement_list.html"
    context_object_name = "movements"
    paginate_by = 50

    def get_queryset(self):
        qs = SupplierStockMovement.objects.filter(
            supplier_part__supplier=self.supplier
        ).select_related("supplier_part__catalog_part", "destination_garage")
        mtype = self.request.GET.get("type", "")
        if mtype:
            qs = qs.filter(movement_type=mtype)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["selected_type"] = self.request.GET.get("type", "")
        ctx["types"] = translated_choices(MOVEMENT_LABELS)
        return ctx


class MovementCreateView(SupplierRequiredMixin, CreateView):
    template_name = "supplier_portal/movement_form.html"
    form_class = SupplierStockMovementForm
    success_url = reverse_lazy("supplier_portal:movement_list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["supplier"] = self.supplier
        return kw

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()
                self.object.apply_to_stock()
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, tr(
            "Mouvement enregistré et stock mis à jour.",
            "Movement recorded and stock updated.",
        ))
        return redirect(self.success_url)


class SalesListView(SupplierRequiredMixin, ListView):
    template_name = "supplier_portal/sale_list.html"
    context_object_name = "sales"
    paginate_by = 50

    def get_queryset(self):
        qs = _sales_queryset(self.supplier)
        period = self.request.GET.get("period", "mois")
        if period not in PERIOD_CODES:
            period = "mois"
        start, end = _period_bounds(period)
        qs = qs.filter(created_at__date__range=(start, end))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(sale_reference__icontains=q)
                | Q(customer_name__icontains=q)
                | Q(destination_garage__name__icontains=q)
                | Q(supplier_part__catalog_part__name__icontains=q)
                | Q(supplier_part__catalog_part__reference__icontains=q)
            )
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        period = self.request.GET.get("period", "mois")
        if period not in PERIOD_CODES:
            period = "mois"
        ctx.update({
            "period": period,
            "period_choices": _period_choices(),
            "q": self.request.GET.get("q", ""),
            "sales_total": _sales_total(self.object_list),
            "units_total": self.object_list.aggregate(total=Coalesce(Sum("quantity"), 0))["total"],
        })
        return ctx


class ExpenseListView(SupplierRequiredMixin, ListView):
    template_name = "supplier_portal/expense_list.html"
    context_object_name = "expenses"
    paginate_by = 50

    def get_queryset(self):
        qs = SupplierExpense.objects.filter(supplier=self.supplier).select_related("recorded_by")
        period = self.request.GET.get("period", "mois")
        if period in PERIOD_CODES:
            start, end = _period_bounds(period)
            qs = qs.filter(date__range=(start, end))
        category = self.request.GET.get("category", "")
        if category:
            qs = qs.filter(category=category)
        return qs.order_by("-date", "-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "period": self.request.GET.get("period", "mois"),
            "period_choices": _period_choices(),
            "selected_category": self.request.GET.get("category", ""),
            "categories": translated_choices(EXPENSE_CATEGORY_LABELS),
            "expense_total": self.object_list.aggregate(
                total=Coalesce(
                    Sum("amount"),
                    Decimal("0.00"),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )["total"],
        })
        return ctx


class ExpenseCreateView(SupplierRequiredMixin, CreateView):
    template_name = "supplier_portal/expense_form.html"
    form_class = SupplierExpenseForm
    success_url = reverse_lazy("supplier_portal:expense_list")

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        form.instance.recorded_by = self.request.user
        messages.success(self.request, tr("Dépense enregistrée.", "Expense recorded."))
        return super().form_valid(form)


class ExpenseUpdateView(SupplierRequiredMixin, UpdateView):
    template_name = "supplier_portal/expense_form.html"
    form_class = SupplierExpenseForm
    success_url = reverse_lazy("supplier_portal:expense_list")

    def get_queryset(self):
        return SupplierExpense.objects.filter(supplier=self.supplier)

    def form_valid(self, form):
        messages.success(self.request, tr("Dépense mise à jour.", "Expense updated."))
        return super().form_valid(form)


class ExpenseDeleteView(SupplierRequiredMixin, DeleteView):
    template_name = "supplier_portal/expense_confirm_delete.html"
    success_url = reverse_lazy("supplier_portal:expense_list")

    def get_queryset(self):
        return SupplierExpense.objects.filter(supplier=self.supplier)

    def form_valid(self, form):
        messages.success(self.request, tr("Dépense supprimée.", "Expense deleted."))
        return super().form_valid(form)


class ReportView(SupplierRequiredMixin, TemplateView):
    template_name = "supplier_portal/report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        period = self.request.GET.get("period", "jour")
        if period not in PERIOD_CODES:
            period = "jour"
        start, end = _period_bounds(period)
        summary = _period_summary(self.supplier, period)
        sales = _sales_queryset(self.supplier).filter(created_at__date__range=(start, end))
        expenses = SupplierExpense.objects.filter(supplier=self.supplier, date__range=(start, end))
        amount = ExpressionWrapper(
            F("quantity") * F("unit_price"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )

        sales_by_product = sales.values(
            "supplier_part__catalog_part__reference",
            "supplier_part__catalog_part__name",
        ).annotate(
            units=Sum("quantity"),
            revenue=Sum(amount),
        ).order_by("-revenue")[:15]

        expenses_by_category = []
        for row in expenses.values("category").annotate(total=Sum("amount")).order_by("-total"):
            expenses_by_category.append({
                "category": translated_label(row["category"], EXPENSE_CATEGORY_LABELS),
                "total": row["total"],
            })

        daily = {}
        for row in sales.annotate(day=TruncDate("created_at")).values("day").annotate(total=Sum(amount), units=Sum("quantity")):
            daily[row["day"]] = {"date": row["day"], "sales": row["total"] or 0, "expenses": 0, "units": row["units"] or 0}
        for row in expenses.values("date").annotate(total=Sum("amount")):
            daily.setdefault(row["date"], {"date": row["date"], "sales": 0, "expenses": 0, "units": 0})
            daily[row["date"]]["expenses"] = row["total"] or 0
        for row in daily.values():
            row["net"] = row["sales"] - row["expenses"]

        ctx.update({
            "supplier": self.supplier,
            "summary": summary,
            "period": period,
            "period_choices": _period_choices(),
            "sales_by_product": sales_by_product,
            "expenses_by_category": expenses_by_category,
            "daily_rows": sorted(daily.values(), key=lambda row: row["date"], reverse=True),
            "recent_sales": sales.order_by("-created_at")[:20],
            "recent_expenses": expenses.order_by("-date", "-created_at")[:20],
            "orders_count": SupplierOrder.objects.filter(
                supplier=self.supplier,
                validated_at__date__range=(start, end),
            ).count(),
        })
        return ctx


def _csv_safe(value):
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


@supplier_required
def report_export_csv(request):
    period = request.GET.get("period", "jour")
    if period not in PERIOD_CODES:
        period = "jour"
    start, end = _period_bounds(period)
    supplier = request.user.supplier
    summary = _period_summary(supplier, period)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="rapport-fournisseur-{period}-{end}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow([tr("Rapport fournisseur", "Supplier report"), _csv_safe(supplier.name)])
    writer.writerow([tr("Période", "Period"), start.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y")])
    writer.writerow([tr("Chiffre d'affaires", "Revenue"), summary["revenue"]])
    writer.writerow([tr("Dépenses", "Expenses"), summary["expenses"]])
    writer.writerow([tr("Résultat net", "Net result"), summary["net"]])
    writer.writerow([])
    writer.writerow([tr("VENTES", "SALES")])
    writer.writerow([
        tr("Date", "Date"), tr("Référence", "Reference"), tr("Pièce", "Part"),
        tr("Client", "Customer"), tr("Quantité", "Quantity"),
        tr("Prix unitaire", "Unit price"), tr("Total", "Total"),
        tr("Paiement", "Payment"),
    ])
    for sale in _sales_queryset(supplier).filter(created_at__date__range=(start, end)).order_by("-created_at"):
        writer.writerow([
            sale.created_at.strftime("%d/%m/%Y %H:%M"),
            _csv_safe(sale.sale_reference),
            _csv_safe(sale.supplier_part.catalog_part.name),
            _csv_safe(sale.customer_name or getattr(sale.destination_garage, "name", "")),
            sale.quantity,
            sale.unit_price or 0,
            sale.line_total,
            translated_label(sale.payment_method, PAYMENT_LABELS) if sale.payment_method else "",
        ])
    writer.writerow([])
    writer.writerow([tr("DÉPENSES", "EXPENSES")])
    writer.writerow([
        tr("Date", "Date"), tr("Catégorie", "Category"),
        tr("Description", "Description"), tr("Référence", "Reference"),
        tr("Montant", "Amount"), tr("Paiement", "Payment"),
    ])
    for expense in SupplierExpense.objects.filter(supplier=supplier, date__range=(start, end)).order_by("-date"):
        writer.writerow([
            expense.date.strftime("%d/%m/%Y"),
            translated_label(expense.category, EXPENSE_CATEGORY_LABELS),
            _csv_safe(expense.description),
            _csv_safe(expense.reference),
            expense.amount,
            translated_label(expense.payment_method, PAYMENT_LABELS),
        ])
    return response


class ProfileView(SupplierRequiredMixin, UpdateView):
    template_name = "supplier_portal/profile.html"
    form_class = SupplierProfileForm
    success_url = reverse_lazy("supplier_portal:profile")

    def get_object(self, queryset=None):
        return self.supplier

    def form_valid(self, form):
        messages.success(self.request, tr("Profil mis à jour.", "Profile updated."))
        return super().form_valid(form)


@supplier_required
def post_login_redirect(request):
    """Redirige les fournisseurs vers leur portail, les garages vers leur dashboard."""
    return redirect("supplier_portal:dashboard")


# ── Commandes reçues ──────────────────────────────────────────────────────────

class OrderInboxView(SupplierRequiredMixin, ListView):
    template_name = "supplier_portal/order_list.html"
    context_object_name = "orders"
    paginate_by = 30

    def get_queryset(self):
        qs = SupplierOrder.objects.filter(supplier=self.supplier).select_related("garage")
        status = self.request.GET.get("status", "")
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["statuses"] = translated_choices(ORDER_STATUS_LABELS)
        ctx["pending_count"] = SupplierOrder.objects.filter(
            supplier=self.supplier, status=SupplierOrder.STATUS_SUBMITTED,
        ).count()
        return ctx


class OrderDetailView(SupplierRequiredMixin, DetailView):
    template_name = "supplier_portal/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return SupplierOrder.objects.filter(supplier=self.supplier).select_related("garage")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lines"] = self.object.lines.select_related("supplier_part__catalog_part").all()
        ctx["rejection_form"] = OrderRejectionForm()
        return ctx


def _post_action(request, pk, action, success_msg):
    order = get_object_or_404(SupplierOrder, pk=pk, supplier=request.user.supplier)
    try:
        action(order)
        messages.success(request, success_msg)
    except order_services.OrderTransitionError as e:
        messages.error(request, str(e))
    return redirect("supplier_portal:order_detail", pk=order.pk)


@supplier_required
def order_validate(request, pk):
    if request.method != "POST":
        return redirect("supplier_portal:order_detail", pk=pk)
    supplier_note = request.POST.get("supplier_note", "").strip()
    return _post_action(
        request, pk,
        lambda o: order_services.validate_order(o, supplier_note=supplier_note),
        tr(
            "Commande validée. Le stock a été décrémenté et la commission plateforme est enregistrée.",
            "Order approved. Stock was deducted and the platform commission was recorded.",
        ),
    )


@supplier_required
def order_reject(request, pk):
    if request.method != "POST":
        return redirect("supplier_portal:order_detail", pk=pk)
    reason = request.POST.get("reason", "").strip()
    return _post_action(
        request, pk,
        lambda o: order_services.reject_order(o, reason=reason),
        tr("Commande rejetée.", "Order rejected."),
    )


@supplier_required
def order_ship(request, pk):
    if request.method != "POST":
        return redirect("supplier_portal:order_detail", pk=pk)
    return _post_action(
        request, pk, order_services.ship_order,
        tr("Commande marquée expédiée.", "Order marked as shipped."),
    )
