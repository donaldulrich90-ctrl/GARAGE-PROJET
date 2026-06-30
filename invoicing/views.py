from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from core.views import GarageRequiredMixin

from .forms import PaymentForm
from .models import Invoice, Payment


def _sync_invoice_status(invoice):
    if invoice.balance_due <= 0:
        invoice.status = Invoice.STATUS_PAID
    elif invoice.amount_paid > 0:
        invoice.status = Invoice.STATUS_PARTIAL
    else:
        invoice.status = Invoice.STATUS_UNPAID
    invoice.save(update_fields=['status', 'updated_at'])


class InvoiceListView(GarageRequiredMixin, ListView):
    model = Invoice
    template_name = 'invoicing/invoice_list.html'
    context_object_name = 'invoices'

    def get_queryset(self):
        qs = super().get_queryset().select_related('repair_order__vehicle', 'repair_order__client')
        status = self.request.GET.get('status', '')
        q = self.request.GET.get('q', '').strip()
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
        ctx['status_choices'] = Invoice.STATUS_CHOICES
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class InvoiceDetailView(GarageRequiredMixin, DetailView):
    model = Invoice
    template_name = 'invoicing/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['payment_form'] = PaymentForm()
        ctx['payments'] = self.object.payments.order_by('-paid_at')
        return ctx


class InvoicePrintView(GarageRequiredMixin, TemplateView):
    template_name = 'invoicing/invoice_print.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoice = get_object_or_404(Invoice.objects.for_garage(self.garage), pk=self.kwargs['pk'])
        ctx['invoice'] = invoice
        ctx['order'] = invoice.repair_order
        ctx['garage'] = self.garage
        ctx['payments'] = invoice.payments.order_by('paid_at')
        return ctx


class PaymentReceiptView(GarageRequiredMixin, TemplateView):
    template_name = 'invoicing/payment_receipt.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoice = get_object_or_404(Invoice.objects.for_garage(self.garage), pk=self.kwargs['pk'])
        payment = get_object_or_404(Payment, pk=self.kwargs['payment_pk'], invoice=invoice)
        ctx['invoice'] = invoice
        ctx['payment'] = payment
        ctx['order'] = invoice.repair_order
        ctx['garage'] = self.garage
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
        return redirect('invoice_detail', pk=pk)
