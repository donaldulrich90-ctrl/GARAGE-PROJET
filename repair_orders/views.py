from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from core.views import GarageRequiredMixin
from inventory.models import Part, StockMovement
from invoicing.models import Invoice

from .forms import RepairOrderForm, RepairOrderPartForm, RepairOrderTaskForm
from .models import RepairOrder, RepairOrderPart, RepairOrderTask

STATUS_NEXT = {
    RepairOrder.STATUS_RECEIVED: RepairOrder.STATUS_DIAGNOSIS,
    RepairOrder.STATUS_DIAGNOSIS: RepairOrder.STATUS_IN_PROGRESS,
    RepairOrder.STATUS_IN_PROGRESS: RepairOrder.STATUS_READY,
    RepairOrder.STATUS_READY: RepairOrder.STATUS_DELIVERED,
}


class OrderListView(GarageRequiredMixin, ListView):
    model = RepairOrder
    template_name = 'repair_orders/order_list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        qs = super().get_queryset().select_related('vehicle', 'client', 'assigned_mechanic')
        status = self.request.GET.get('status', '')
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = (
                qs.filter(reference__icontains=q)
                | qs.filter(vehicle__plate_number__icontains=q)
                | qs.filter(client__full_name__icontains=q)
                | qs.filter(client_complaint__icontains=q)
                | qs.filter(diagnosis_notes__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = RepairOrder.STATUS_CHOICES
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class OrderDetailView(GarageRequiredMixin, DetailView):
    model = RepairOrder
    template_name = 'repair_orders/order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['task_form'] = RepairOrderTaskForm(garage=self.garage)
        ctx['part_form'] = RepairOrderPartForm(garage=self.garage)
        ctx['next_status'] = STATUS_NEXT.get(self.object.status)
        ctx['next_status_label'] = dict(RepairOrder.STATUS_CHOICES).get(
            STATUS_NEXT.get(self.object.status), ''
        )
        ctx['invoices'] = self.object.invoices.all()
        return ctx


class OrderCreateView(GarageRequiredMixin, CreateView):
    model = RepairOrder
    form_class = RepairOrderForm
    template_name = 'repair_orders/order_form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def get_initial(self):
        initial = super().get_initial()
        initial['status'] = RepairOrder.STATUS_RECEIVED
        return initial

    def get_success_url(self):
        messages.success(self.request, f"Ordre {self.object.reference} créé.")
        return reverse('order_detail', args=[self.object.pk])


class OrderUpdateView(GarageRequiredMixin, UpdateView):
    model = RepairOrder
    form_class = RepairOrderForm
    template_name = 'repair_orders/order_form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def get_success_url(self):
        messages.success(self.request, "Ordre mis à jour.")
        return reverse('order_detail', args=[self.object.pk])


class ChangeStatusView(GarageRequiredMixin, View):
    def post(self, request, pk, status):
        order = get_object_or_404(RepairOrder.objects.for_garage(self.garage), pk=pk)
        valid = [s[0] for s in RepairOrder.STATUS_CHOICES]
        if status in valid:
            order.status = status
            if status == RepairOrder.STATUS_DELIVERED:
                order.delivered_at = timezone.now()
            order.save()
            messages.success(request, f"Statut : {order.get_status_display()}")
        return redirect('order_detail', pk=pk)


class AddTaskView(GarageRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(RepairOrder.objects.for_garage(self.garage), pk=pk)
        form = RepairOrderTaskForm(request.POST, garage=self.garage)
        if form.is_valid():
            task = form.save(commit=False)
            task.repair_order = order
            task.save()
            messages.success(request, "Tâche ajoutée.")
        else:
            messages.error(request, "Formulaire invalide.")
        return redirect('order_detail', pk=pk)


class DeleteTaskView(GarageRequiredMixin, View):
    def post(self, request, order_pk, pk):
        order = get_object_or_404(RepairOrder.objects.for_garage(self.garage), pk=order_pk)
        task = get_object_or_404(RepairOrderTask, pk=pk, repair_order=order)
        task.delete()
        messages.success(request, "Tâche supprimée.")
        return redirect('order_detail', pk=order_pk)


class AddPartView(GarageRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(RepairOrder.objects.for_garage(self.garage), pk=pk)
        form = RepairOrderPartForm(request.POST, garage=self.garage)
        if form.is_valid():
            part = form.cleaned_data['part']
            quantity = form.cleaned_data['quantity']
            if part.quantity_in_stock < quantity:
                messages.error(request, f"Stock insuffisant pour {part.name} (disponible : {part.quantity_in_stock}).")
                return redirect('order_detail', pk=pk)
            unit_price = form.cleaned_data.get('unit_price') or part.unit_price
            RepairOrderPart.objects.create(
                repair_order=order,
                part=part,
                quantity=quantity,
                unit_price=unit_price,
            )
            part.quantity_in_stock -= quantity
            part.save(update_fields=['quantity_in_stock', 'updated_at'])
            StockMovement.objects.create(
                garage=self.garage,
                part=part,
                movement_type=StockMovement.MOVEMENT_OUT,
                quantity=quantity,
                reason=f"OR {order.reference}",
            )
            messages.success(request, f"{quantity} x {part.name} ajouté.")
        else:
            messages.error(request, "Formulaire invalide.")
        return redirect('order_detail', pk=pk)


class RemovePartView(GarageRequiredMixin, View):
    def post(self, request, order_pk, pk):
        order = get_object_or_404(RepairOrder.objects.for_garage(self.garage), pk=order_pk)
        op = get_object_or_404(RepairOrderPart, pk=pk, repair_order=order)
        part = op.part
        qty = op.quantity
        op.delete()
        part.quantity_in_stock += qty
        part.save(update_fields=['quantity_in_stock', 'updated_at'])
        StockMovement.objects.create(
            garage=self.garage,
            part=part,
            movement_type=StockMovement.MOVEMENT_IN,
            quantity=qty,
            reason=f"Retrait OR {order.reference}",
        )
        messages.success(request, "Pièce retirée de l'OR, stock restitué.")
        return redirect('order_detail', pk=order_pk)


class ProformaPrintView(GarageRequiredMixin, TemplateView):
    template_name = 'repair_orders/proforma_print.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        order = get_object_or_404(RepairOrder.objects.for_garage(self.garage), pk=self.kwargs['pk'])
        ctx['order'] = order
        ctx['garage'] = self.garage
        ctx['today'] = timezone.now().date()
        return ctx


class CreateInvoiceView(GarageRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(RepairOrder.objects.for_garage(self.garage), pk=pk)
        if order.invoices.exists():
            messages.warning(request, "Une facture existe déjà pour cet ordre.")
        else:
            Invoice.objects.create(garage=self.garage, repair_order=order)
            messages.success(request, "Facture créée.")
        return redirect('order_detail', pk=pk)
