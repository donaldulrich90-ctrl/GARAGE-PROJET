import json

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from core.views import GarageRequiredMixin
from inventory.models import Part, StockMovement

from .forms import PaymentForm, ProformaForm, ProformaLineFormSet
from .models import Invoice, Payment, ProformaInvoice


# ─── Factures (liées aux ordres de réparation) ──────────────────────────────

def _sync_invoice_status(invoice):
    if invoice.balance_due <= 0:
        invoice.status = Invoice.STATUS_PAID
    elif invoice.amount_paid > 0:
        invoice.status = Invoice.STATUS_PARTIAL
    else:
        invoice.status = Invoice.STATUS_UNPAID
    invoice.save(update_fields=["status", "updated_at"])


class InvoiceListView(GarageRequiredMixin, ListView):
    model = Invoice
    template_name = "invoicing/invoice_list.html"
    context_object_name = "invoices"

    def get_queryset(self):
        qs = super().get_queryset().select_related("repair_order__vehicle", "repair_order__client")
        status = self.request.GET.get("status", "")
        q = self.request.GET.get("q", "").strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = (
                qs.filter(reference__icontains=q)
                | qs.filter(repair_order__vehicle__plate_number__icontains=q)
                | qs.filter(repair_order__client__full_name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Invoice.STATUS_CHOICES
        ctx["status_filter"] = self.request.GET.get("status", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


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
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.save()
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
