import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from core.views import GarageRequiredMixin
from inventory.models import Part, StockMovement

from workshops.services import create_payment_allocations

from .forms import PaymentForm, ProformaForm, ProformaLineFormSet
from .models import Invoice, Payment, ProformaInvoice


# ─── Caisse unifiée ─────────────────────────────────────────────────────────

def _build_cashbook(garage, date_from=None, date_to=None, method_filter=""):
    """
    Agrège les encaissements de deux sources :
      1. ProformaInvoice au statut receipt
      2. Payment des Invoice liées aux OR
    Retourne une liste de dicts normalisés, triée par date décroissante.
    """
    entries = []

    # Source 1 : proformas payées
    proforma_qs = (
        ProformaInvoice.objects.for_garage(garage)
        .filter(status=ProformaInvoice.STATUS_RECEIPT)
        .annotate(computed_total=Sum(F("lines__quantity") * F("lines__unit_price")))
        .select_related("client")
    )
    if date_from:
        proforma_qs = proforma_qs.filter(paid_at__date__gte=date_from)
    if date_to:
        proforma_qs = proforma_qs.filter(paid_at__date__lte=date_to)
    if method_filter:
        proforma_qs = proforma_qs.filter(payment_method=method_filter)

    for p in proforma_qs:
        entries.append({
            "date": p.paid_at,
            "reference": p.reference,
            "client": p.display_client,
            "amount": p.computed_total or Decimal("0"),
            "method": p.payment_method,
            "method_label": dict(ProformaInvoice.PAYMENT_METHODS).get(p.payment_method, p.payment_method),
            "source": "vente",
            "url_detail": reverse("proforma_detail", args=[p.pk]),
        })

    # Source 2 : paiements des factures OR
    payment_qs = (
        Payment.objects.filter(invoice__garage=garage)
        .select_related("invoice__repair_order__client")
    )
    if date_from:
        payment_qs = payment_qs.filter(paid_at__date__gte=date_from)
    if date_to:
        payment_qs = payment_qs.filter(paid_at__date__lte=date_to)
    if method_filter:
        payment_qs = payment_qs.filter(method=method_filter)

    for pay in payment_qs:
        client = pay.invoice.repair_order.client if pay.invoice.repair_order else None
        entries.append({
            "date": pay.paid_at,
            "reference": pay.invoice.reference,
            "client": client.full_name if client else "—",
            "amount": pay.amount,
            "method": pay.method,
            "method_label": dict(Payment.METHOD_CHOICES).get(pay.method, pay.method),
            "source": "facture_or",
            "url_detail": reverse("invoice_detail", args=[pay.invoice.pk]),
        })

    entries.sort(key=lambda e: e["date"] or timezone.datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return entries


def _compute_kpis(entries, garage):
    """Calcule les KPIs à partir de la liste filtrée + cartes aujourd'hui/ce mois indépendantes."""
    total = sum(e["amount"] for e in entries)
    count = len(entries)
    avg = (total / count) if count else Decimal("0")

    by_method = {}
    for e in entries:
        m = e["method"]
        by_method.setdefault(m, {"label": e["method_label"], "amount": Decimal("0"), "count": 0})
        by_method[m]["amount"] += e["amount"]
        by_method[m]["count"] += 1

    for m, data in by_method.items():
        data["pct"] = int((data["amount"] / total * 100)) if total else 0

    # Cartes indépendantes du filtre période
    today = date.today()
    first_of_month = today.replace(day=1)
    all_entries = _build_cashbook(garage)
    today_total = sum(e["amount"] for e in all_entries if e["date"] and e["date"].date() == today)
    month_total = sum(e["amount"] for e in all_entries if e["date"] and e["date"].date() >= first_of_month)

    return {
        "total": total,
        "count": count,
        "avg": avg,
        "by_method": by_method,
        "today_total": today_total,
        "month_total": month_total,
    }


class InvoiceListView(GarageRequiredMixin, View):
    template_name = "invoicing/invoice_list.html"

    def get(self, request):
        date_from_str = request.GET.get("date_from", "")
        date_to_str = request.GET.get("date_to", "")
        method_filter = request.GET.get("method", "")
        period = request.GET.get("period", "")

        date_from = None
        date_to = None
        today = date.today()

        if period == "today":
            date_from = date_to = today
        elif period == "month":
            date_from = today.replace(day=1)
            date_to = today
        else:
            if date_from_str:
                try:
                    from datetime import datetime
                    date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
            if date_to_str:
                try:
                    from datetime import datetime
                    date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

        entries = _build_cashbook(self.garage, date_from=date_from, date_to=date_to, method_filter=method_filter)
        kpis = _compute_kpis(entries, self.garage)

        return render(request, self.template_name, {
            "entries": entries,
            "kpis": kpis,
            "method_choices": Payment.METHOD_CHOICES,
            "method_filter": method_filter,
            "period": period,
            "date_from": date_from_str,
            "date_to": date_to_str,
        })


# ─── Factures (liées aux ordres de réparation) ──────────────────────────────

def _sync_invoice_status(invoice):
    if invoice.balance_due <= 0:
        invoice.status = Invoice.STATUS_PAID
    elif invoice.amount_paid > 0:
        invoice.status = Invoice.STATUS_PARTIAL
    else:
        invoice.status = Invoice.STATUS_UNPAID
    invoice.save(update_fields=["status", "updated_at"])


class InvoiceDetailView(GarageRequiredMixin, DetailView):
    model = Invoice
    template_name = "invoicing/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["payment_form"] = PaymentForm()
        ctx["payments"] = self.object.payments.order_by("-paid_at")
        return ctx


class InvoicePrintView(GarageRequiredMixin, TemplateView):
    template_name = "invoicing/invoice_print.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoice = get_object_or_404(Invoice.objects.for_garage(self.garage), pk=self.kwargs["pk"])
        ctx["invoice"] = invoice
        ctx["order"] = invoice.repair_order
        ctx["garage"] = self.garage
        ctx["payments"] = invoice.payments.order_by("paid_at")
        return ctx


class PaymentReceiptView(GarageRequiredMixin, TemplateView):
    template_name = "invoicing/payment_receipt.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoice = get_object_or_404(Invoice.objects.for_garage(self.garage), pk=self.kwargs["pk"])
        payment = get_object_or_404(Payment, pk=self.kwargs["payment_pk"], invoice=invoice)
        ctx["invoice"] = invoice
        ctx["payment"] = payment
        ctx["order"] = invoice.repair_order
        ctx["garage"] = self.garage
        return ctx


class AddPaymentView(GarageRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice.objects.for_garage(self.garage), pk=pk)
        form = PaymentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                payment = form.save(commit=False)
                payment.invoice = invoice
                payment.save()
                create_payment_allocations(payment)
                _sync_invoice_status(invoice)
            messages.success(request, f"Paiement de {payment.amount} FCFA enregistré.")
        else:
            messages.error(request, "Formulaire invalide.")
        return redirect("invoice_detail", pk=pk)


# ─── Factures Proforma ───────────────────────────────────────────────────────

class ProformaListView(GarageRequiredMixin, ListView):
    model = ProformaInvoice
    template_name = "invoicing/proforma_list.html"
    context_object_name = "proformas"

    def get_queryset(self):
        qs = super().get_queryset().select_related("client")
        status = self.request.GET.get("status", "")
        q = self.request.GET.get("q", "").strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = (
                qs.filter(reference__icontains=q)
                | qs.filter(client__full_name__icontains=q)
                | qs.filter(client_name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = ProformaInvoice.STATUS_CHOICES
        ctx["status_filter"] = self.request.GET.get("status", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


def _proforma_form_context(garage):
    """Parts data as JSON for JS auto-fill in the form."""
    parts = Part.objects.for_garage(garage).order_by("reference")
    parts_json = {
        str(p.pk): {
            "reference": p.reference,
            "name": p.name,
            "price": str(p.unit_price),
            "stock": p.quantity_in_stock,
        }
        for p in parts
    }
    return parts, parts_json


class ProformaCreateView(GarageRequiredMixin, View):
    template_name = "invoicing/proforma_form.html"

    def get(self, request):
        parts, parts_json = _proforma_form_context(self.garage)
        form = ProformaForm(garage=self.garage)
        formset = ProformaLineFormSet(form_kwargs={"garage": self.garage})
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "parts_json": json.dumps(parts_json),
            "action": "Créer une proforma",
        })

    def post(self, request):
        parts, parts_json = _proforma_form_context(self.garage)
        form = ProformaForm(request.POST, garage=self.garage)
        formset = ProformaLineFormSet(request.POST, form_kwargs={"garage": self.garage})
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                proforma = form.save(commit=False)
                proforma.garage = self.garage
                proforma.save()
                formset.instance = proforma
                formset.save()
            messages.success(request, f"Proforma {proforma.reference} créée.")
            return redirect("proforma_detail", pk=proforma.pk)
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "parts_json": json.dumps(parts_json),
            "action": "Créer une proforma",
        })


class ProformaEditView(GarageRequiredMixin, View):
    template_name = "invoicing/proforma_form.html"

    def get_proforma(self):
        proforma = get_object_or_404(ProformaInvoice.objects.for_garage(self.garage), pk=self.kwargs["pk"])
        if proforma.status != ProformaInvoice.STATUS_PROFORMA:
            messages.error(self.request, "Seule une proforma (non encore convertie) peut être modifiée.")
            return None, proforma
        return proforma, None

    def get(self, request, pk):
        proforma, redirect_obj = self.get_proforma()
        if redirect_obj:
            return redirect("proforma_detail", pk=pk)
        parts, parts_json = _proforma_form_context(self.garage)
        form = ProformaForm(instance=proforma, garage=self.garage)
        formset = ProformaLineFormSet(instance=proforma, form_kwargs={"garage": self.garage})
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "parts_json": json.dumps(parts_json),
            "proforma": proforma,
            "action": "Modifier la proforma",
        })

    def post(self, request, pk):
        proforma, redirect_obj = self.get_proforma()
        if redirect_obj:
            return redirect("proforma_detail", pk=pk)
        parts, parts_json = _proforma_form_context(self.garage)
        form = ProformaForm(request.POST, instance=proforma, garage=self.garage)
        formset = ProformaLineFormSet(request.POST, instance=proforma, form_kwargs={"garage": self.garage})
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, "Proforma mise à jour.")
            return redirect("proforma_detail", pk=pk)
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "parts_json": json.dumps(parts_json),
            "proforma": proforma,
            "action": "Modifier la proforma",
        })


class ProformaDetailView(GarageRequiredMixin, DetailView):
    model = ProformaInvoice
    template_name = "invoicing/proforma_detail.html"
    context_object_name = "proforma"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["payment_methods"] = ProformaInvoice.PAYMENT_METHODS
        return ctx


class ProformaPromoteView(GarageRequiredMixin, View):
    """
    POST → avance le statut de la proforma :
      proforma → invoice (facture définitive)
      invoice  → receipt (payée, stock décrémenté)
    """

    def post(self, request, pk):
        proforma = get_object_or_404(ProformaInvoice.objects.for_garage(self.garage), pk=pk)

        if proforma.status == ProformaInvoice.STATUS_PROFORMA:
            proforma.status = ProformaInvoice.STATUS_INVOICE
            proforma.save(update_fields=["status", "updated_at"])
            messages.success(request, f"{proforma.reference} convertie en facture définitive.")

        elif proforma.status == ProformaInvoice.STATUS_INVOICE:
            payment_method = request.POST.get("payment_method", "cash")

            # Vérification stock
            stock_errors = []
            lines_with_part = list(proforma.lines.filter(part__isnull=False).select_related("part"))
            for line in lines_with_part:
                if line.part.quantity_in_stock < line.quantity:
                    stock_errors.append(
                        f"Stock insuffisant pour {line.part.reference} — {line.part.name} "
                        f"(disponible : {line.part.quantity_in_stock}, demandé : {line.quantity})"
                    )

            if stock_errors:
                for err in stock_errors:
                    messages.error(request, err)
                return redirect("proforma_detail", pk=pk)

            # Décrémentation + mouvement de stock
            with transaction.atomic():
                for line in lines_with_part:
                    line.part.quantity_in_stock -= line.quantity
                    line.part.save(update_fields=["quantity_in_stock"])
                    StockMovement.objects.create(
                        garage=proforma.garage,
                        part=line.part,
                        movement_type=StockMovement.MOVEMENT_OUT,
                        quantity=line.quantity,
                        reason=f"Vente — {proforma.reference}",
                    )
                proforma.status = ProformaInvoice.STATUS_RECEIPT
                proforma.payment_method = payment_method
                proforma.paid_at = timezone.now()
                proforma.save(update_fields=["status", "payment_method", "paid_at", "updated_at"])

            messages.success(
                request,
                f"Paiement validé. Stock mis à jour. Reçu {proforma.reference} généré."
            )

        return redirect("proforma_detail", pk=pk)


class ProformaPrintView(GarageRequiredMixin, TemplateView):
    template_name = "invoicing/proforma_print.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proforma"] = get_object_or_404(
            ProformaInvoice.objects.for_garage(self.garage), pk=self.kwargs["pk"]
        )
        ctx["garage"] = self.garage
        return ctx
