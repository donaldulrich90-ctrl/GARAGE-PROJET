from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, TemplateView

from core.views import GarageRequiredMixin
from repair_orders.models import RepairOrder

from .forms import DiagnosticCodeFormSet, DiagnosticReportForm
from .models import DiagnosticReport


class DiagnosticCreateView(GarageRequiredMixin, View):
    template_name = 'diagnostics/report_form.html'

    def get_order(self, pk):
        return get_object_or_404(RepairOrder.objects.for_garage(self.garage), pk=pk)

    def get(self, request, order_pk):
        order = self.get_order(order_pk)
        form = DiagnosticReportForm(garage=self.garage, initial={'scan_date': timezone.now()})
        formset = DiagnosticCodeFormSet()
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'order': order,
            'action': 'Nouveau diagnostic',
        })

    def post(self, request, order_pk):
        order = self.get_order(order_pk)
        form = DiagnosticReportForm(request.POST, request.FILES, garage=self.garage)
        formset = DiagnosticCodeFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                report = form.save(commit=False)
                report.garage = self.garage
                report.repair_order = order
                report.created_by = request.user
                report.save()
                formset.instance = report
                formset.save()
            messages.success(request, f'Diagnostic {report.reference} créé.')
            return redirect('order_detail', pk=order_pk)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'order': order,
            'action': 'Nouveau diagnostic',
        })


class DiagnosticDetailView(GarageRequiredMixin, DetailView):
    model = DiagnosticReport
    template_name = 'diagnostics/report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        return DiagnosticReport.objects.for_garage(self.garage).select_related(
            'repair_order__vehicle', 'repair_order__client', 'technician'
        ).prefetch_related('codes')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = self.object.repair_order
        ctx['garage'] = self.garage
        return ctx


class DiagnosticUpdateView(GarageRequiredMixin, View):
    template_name = 'diagnostics/report_form.html'

    def get_report(self, pk):
        return get_object_or_404(DiagnosticReport.objects.for_garage(self.garage), pk=pk)

    def get(self, request, pk):
        report = self.get_report(pk)
        form = DiagnosticReportForm(instance=report, garage=self.garage)
        formset = DiagnosticCodeFormSet(instance=report)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'order': report.repair_order,
            'report': report,
            'action': 'Modifier le diagnostic',
        })

    def post(self, request, pk):
        report = self.get_report(pk)
        form = DiagnosticReportForm(request.POST, request.FILES, instance=report, garage=self.garage)
        formset = DiagnosticCodeFormSet(request.POST, instance=report)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, 'Diagnostic mis à jour.')
            return redirect('order_detail', pk=report.repair_order_id)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'order': report.repair_order,
            'report': report,
            'action': 'Modifier le diagnostic',
        })


class DiagnosticPrintView(GarageRequiredMixin, TemplateView):
    template_name = 'diagnostics/report_print.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        report = get_object_or_404(
            DiagnosticReport.objects.for_garage(self.garage)
            .select_related('repair_order__vehicle__client', 'technician')
            .prefetch_related('codes'),
            pk=self.kwargs['pk'],
        )
        ctx['report'] = report
        ctx['order'] = report.repair_order
        ctx['vehicle'] = report.repair_order.vehicle
        ctx['client'] = report.repair_order.client
        ctx['garage'] = self.garage
        return ctx
