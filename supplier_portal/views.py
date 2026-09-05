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
from inventory.models import (
    SupplierExpense,
    SupplierInvoice,
    SupplierInvoiceLine,
    SupplierOrder,
    SupplierPart,
    SupplierStockMovement,
)

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

    def get_queryset(self):
        qs = (
            SupplierPart.objects.filter(supplier=self.supplier)
            .select_related("catalog_part", "catalog_part__category")
            .prefetch_related("catalog_part__compatible_models__make")
        )
        q = self.request.GET.get("q", "").strip()
        cat = self.request.GET.get("category", "").strip()
        make = self.request.GET.get("make", "").strip()
        model = self.request.GET.get("model", "").strip()
        if q:
            qs = qs.filter(
                Q(g_code__icontains=q)
                | Q(catalog_part__reference__icontains=q)
                | Q(catalog_part__name__icontains=q)
                | Q(supplier_reference__icontains=q)
            )
        if cat:
            qs = qs.filter(catalog_part__category_id=cat)
        if make:
            qs = qs.filter(catalog_part__compatible_models__make_id=make)
        if model:
            qs = qs.filter(catalog_part__compatible_models__id=model)
        return qs.distinct().order_by(
            "catalog_part__category__name", "catalog_part__name"
        )

    def get_context_data(self, **kwargs):
        from catalog.models import PartCategory, VehicleMake, VehicleModel

        ctx = super().get_context_data(**kwargs)
        sup = self.supplier
        ctx["q"] = self.request.GET.get("q", "")
        ctx["selected_category"] = self.request.GET.get("category", "")
        ctx["selected_make"] = self.request.GET.get("make", "")
        ctx["selected_model"] = self.request.GET.get("model", "")
        # Les filtres ne proposent QUE ce que le fournisseur possède déjà :
        # simple, sans options vides.
        ctx["categories"] = (
            PartCategory.objects
            .filter(parts__supplier_offers__supplier=sup)
            .distinct().order_by("name")
        )
        ctx["makes"] = (
            VehicleMake.objects
            .filter(models__compatible_parts__supplier_offers__supplier=sup)
            .distinct().order_by("name")
        )
        models_qs = (
            VehicleModel.objects
            .filter(compatible_parts__supplier_offers__supplier=sup)
            .distinct().select_related("make")
        )
        if ctx["selected_make"]:
            models_qs = models_qs.filter(make_id=ctx["selected_make"])
        ctx["models"] = models_qs.order_by("make__name", "name")
        return ctx


class MyOfferCreateView(SupplierRequiredMixin, CreateView):
    template_name = "supplier_portal/offer_form.html"
    form_class = SupplierPartOwnForm
    success_url = reverse_lazy("supplier_portal:offer_list")

    def form_valid(self, form):
        form.instance.supplier = self.supplier
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


# ══════════════════════════════════════════════════════════════════════════════
#  FACTURES FOURNISSEUR
#  Le fournisseur émet des factures aux garages qu'il sert (depuis une commande
#  validée ou en saisie manuelle), puis suit leur statut (brouillon → envoyée →
#  payée). Lecture/écriture strictement limitées aux factures du fournisseur
#  connecté.
# ══════════════════════════════════════════════════════════════════════════════


def _supplier_client_garages(supplier):
    """Garages que ce fournisseur peut facturer : ceux à qui il a déjà eu
    une commande sur la plateforme. Renvoie un queryset."""
    from tenants.models import Garage

    garage_ids = set(
        SupplierOrder.objects.filter(supplier=supplier)
        .values_list("garage_id", flat=True)
    )
    return Garage.objects.filter(id__in=garage_ids).order_by("name")


def _supplier_invoices(supplier):
    return (
        SupplierInvoice.objects.filter(supplier=supplier)
        .select_related("garage", "order")
        .prefetch_related("lines")
    )


@supplier_required
def invoice_list(request):
    supplier = request.user.supplier
    status = request.GET.get("status", "").strip()
    qs = _supplier_invoices(supplier)
    if status in dict(SupplierInvoice.STATUS_CHOICES):
        qs = qs.filter(status=status)

    invoices = list(qs)
    # Total par facture (propriété non requêtable) + agrégats de tête.
    total_all = sum((inv.total for inv in invoices), Decimal("0"))
    total_unpaid = sum(
        (inv.total for inv in invoices if inv.status != SupplierInvoice.STATUS_PAID),
        Decimal("0"),
    )

    ctx = {
        "n": "invoices",
        "invoices": invoices,
        "status_filter": status,
        "status_choices": SupplierInvoice.STATUS_CHOICES,
        "total_all": total_all,
        "total_unpaid": total_unpaid,
    }
    return render(request, "supplier_portal/invoice_list.html", ctx)


@supplier_required
def invoice_from_order(request, order_pk):
    """Génère une facture brouillon pré-remplie depuis une commande validée."""
    supplier = request.user.supplier
    order = get_object_or_404(
        SupplierOrder.objects.select_related("garage").prefetch_related("lines"),
        pk=order_pk, supplier=supplier,
    )
    if request.method != "POST":
        return redirect("supplier_portal:order_detail", pk=order_pk)

    # Une seule facture par commande : rediriger vers l'existante le cas échéant.
    existing = SupplierInvoice.objects.filter(supplier=supplier, order=order).first()
    if existing:
        messages.info(request, tr(
            "Une facture existe déjà pour cette commande.",
            "An invoice already exists for this order.",
        ))
        return redirect("supplier_portal:invoice_detail", pk=existing.pk)

    with transaction.atomic():
        invoice = SupplierInvoice.objects.create(
            supplier=supplier,
            garage=order.garage,
            order=order,
            notes=tr(
                f"Facture émise pour la commande {order.reference}.",
                f"Invoice issued for order {order.reference}.",
            ),
        )
        for line in order.lines.all():
            SupplierInvoiceLine.objects.create(
                invoice=invoice,
                description=line.catalog_name or tr("Pièce", "Part"),
                g_code=line.g_code,
                unit_price=line.unit_price,
                quantity=line.quantity,
            )

    messages.success(request, tr(
        "Facture créée depuis la commande. Vérifiez les lignes puis envoyez-la.",
        "Invoice created from the order. Review the lines then send it.",
    ))
    return redirect("supplier_portal:invoice_detail", pk=invoice.pk)


@supplier_required
def invoice_create(request):
    """Création manuelle d'une facture (choix du garage client)."""
    supplier = request.user.supplier
    garages = _supplier_client_garages(supplier)

    if request.method == "POST":
        garage_id = request.POST.get("garage")
        issued_at = request.POST.get("issued_at") or None
        due_date = request.POST.get("due_date") or None
        notes = request.POST.get("notes", "").strip()

        garage = garages.filter(id=garage_id).first()
        if not garage:
            messages.error(request, tr(
                "Sélectionnez un garage client valide.",
                "Select a valid client garage.",
            ))
        else:
            invoice = SupplierInvoice(
                supplier=supplier, garage=garage, notes=notes,
            )
            if issued_at:
                invoice.issued_at = issued_at
            if due_date:
                invoice.due_date = due_date
            invoice.save()
            messages.success(request, tr(
                "Facture créée. Ajoutez maintenant les lignes.",
                "Invoice created. Now add the lines.",
            ))
            return redirect("supplier_portal:invoice_detail", pk=invoice.pk)

    ctx = {
        "n": "invoices",
        "garages": garages,
        "today": timezone.localdate(),
    }
    return render(request, "supplier_portal/invoice_manual_form.html", ctx)


@supplier_required
def invoice_detail(request, pk):
    supplier = request.user.supplier
    invoice = get_object_or_404(
        _supplier_invoices(supplier), pk=pk,
    )
    ctx = {
        "n": "invoices",
        "invoice": invoice,
        "lines": invoice.lines.all(),
        "can_edit": invoice.status == SupplierInvoice.STATUS_DRAFT,
        "status_choices": SupplierInvoice.STATUS_CHOICES,
    }
    return render(request, "supplier_portal/invoice_detail.html", ctx)


@supplier_required
def invoice_add_line(request, pk):
    supplier = request.user.supplier
    invoice = get_object_or_404(SupplierInvoice, pk=pk, supplier=supplier)
    if request.method != "POST":
        return redirect("supplier_portal:invoice_detail", pk=pk)
    if invoice.status != SupplierInvoice.STATUS_DRAFT:
        messages.error(request, tr(
            "Seules les factures en brouillon peuvent être modifiées.",
            "Only draft invoices can be edited.",
        ))
        return redirect("supplier_portal:invoice_detail", pk=pk)

    description = request.POST.get("description", "").strip()
    g_code = request.POST.get("g_code", "").strip()
    try:
        unit_price = Decimal(request.POST.get("unit_price", "0") or "0")
        quantity = int(request.POST.get("quantity", "1") or "1")
    except (ValueError, ArithmeticError):
        messages.error(request, tr("Prix ou quantité invalide.", "Invalid price or quantity."))
        return redirect("supplier_portal:invoice_detail", pk=pk)

    if not description or quantity < 1 or unit_price < 0:
        messages.error(request, tr(
            "Renseignez une désignation, une quantité ≥ 1 et un prix ≥ 0.",
            "Provide a description, a quantity ≥ 1 and a price ≥ 0.",
        ))
        return redirect("supplier_portal:invoice_detail", pk=pk)

    SupplierInvoiceLine.objects.create(
        invoice=invoice, description=description, g_code=g_code,
        unit_price=unit_price, quantity=quantity,
    )
    messages.success(request, tr("Ligne ajoutée.", "Line added."))
    return redirect("supplier_portal:invoice_detail", pk=pk)


@supplier_required
def invoice_line_delete(request, pk, line_pk):
    supplier = request.user.supplier
    invoice = get_object_or_404(SupplierInvoice, pk=pk, supplier=supplier)
    if request.method != "POST":
        return redirect("supplier_portal:invoice_detail", pk=pk)
    if invoice.status != SupplierInvoice.STATUS_DRAFT:
        messages.error(request, tr(
            "Seules les factures en brouillon peuvent être modifiées.",
            "Only draft invoices can be edited.",
        ))
        return redirect("supplier_portal:invoice_detail", pk=pk)
    SupplierInvoiceLine.objects.filter(invoice=invoice, pk=line_pk).delete()
    messages.success(request, tr("Ligne supprimée.", "Line removed."))
    return redirect("supplier_portal:invoice_detail", pk=pk)


@supplier_required
def invoice_set_status(request, pk, status):
    supplier = request.user.supplier
    invoice = get_object_or_404(SupplierInvoice, pk=pk, supplier=supplier)
    if request.method != "POST":
        return redirect("supplier_portal:invoice_detail", pk=pk)
    if status not in dict(SupplierInvoice.STATUS_CHOICES):
        messages.error(request, tr("Statut invalide.", "Invalid status."))
        return redirect("supplier_portal:invoice_detail", pk=pk)
    if status == SupplierInvoice.STATUS_SENT and not invoice.lines.exists():
        messages.error(request, tr(
            "Ajoutez au moins une ligne avant d'envoyer la facture.",
            "Add at least one line before sending the invoice.",
        ))
        return redirect("supplier_portal:invoice_detail", pk=pk)
    invoice.status = status
    invoice.save(update_fields=["status", "updated_at"])
    messages.success(request, tr("Statut mis à jour.", "Status updated."))
    return redirect("supplier_portal:invoice_detail", pk=pk)


@supplier_required
def invoice_delete(request, pk):
    supplier = request.user.supplier
    invoice = get_object_or_404(SupplierInvoice, pk=pk, supplier=supplier)
    if request.method != "POST":
        return redirect("supplier_portal:invoice_detail", pk=pk)
    if invoice.status != SupplierInvoice.STATUS_DRAFT:
        messages.error(request, tr(
            "Seules les factures en brouillon peuvent être supprimées.",
            "Only draft invoices can be deleted.",
        ))
        return redirect("supplier_portal:invoice_detail", pk=pk)
    invoice.delete()
    messages.success(request, tr("Facture supprimée.", "Invoice deleted."))
    return redirect("supplier_portal:invoice_list")


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORIQUE / JOURNAL D'ACTIVITÉ DU FOURNISSEUR
#  S'appuie sur le système d'audit global (core.AuditLog) : chaque création,
#  modification ou suppression faite par un membre de l'équipe fournisseur est
#  tracée automatiquement. Ici on la rend consultable par le fournisseur.
# ══════════════════════════════════════════════════════════════════════════════


@supplier_required
def activity_log(request):
    from django.core.paginator import Paginator
    from core.models import AuditLog

    supplier = request.user.supplier
    team_ids = list(supplier.users.values_list("id", flat=True))
    logs = (
        AuditLog.objects.filter(user_id__in=team_ids)
        .select_related("user")
        .order_by("-created_at")
    )
    action = request.GET.get("action", "").strip()
    if action in dict(AuditLog.ACTION_CHOICES):
        logs = logs.filter(action=action)

    paginator = Paginator(logs, 50)
    page = paginator.get_page(request.GET.get("page"))

    # Noms de modèles lisibles (les plus fréquents côté fournisseur)
    friendly = {
        "SupplierPart": tr("Pièce / offre", "Part / offer"),
        "SupplierInvoice": tr("Facture", "Invoice"),
        "SupplierInvoiceLine": tr("Ligne de facture", "Invoice line"),
        "SupplierOrder": tr("Commande", "Order"),
        "SupplierStockMovement": tr("Mouvement de stock", "Stock movement"),
        "SupplierExpense": tr("Dépense", "Expense"),
        "Supplier": tr("Fiche fournisseur", "Supplier profile"),
        "User": tr("Compte", "Account"),
    }
    items = list(page.object_list)
    for lg in items:
        lg.friendly_name = friendly.get(lg.model_name, lg.model_name)
    ctx = {
        "n": "activity",
        "page_obj": page,
        "logs": items,
        "action_filter": action,
        "action_choices": AuditLog.ACTION_CHOICES,
    }
    return render(request, "supplier_portal/activity_log.html", ctx)
