from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from core.views import GarageRequiredMixin

from .forms import PartForm, SupplierForm
from .models import Part, Supplier


class PartListView(GarageRequiredMixin, ListView):
    model = Part
    template_name = 'inventory/part_list.html'
    context_object_name = 'parts'

    def get_queryset(self):
        qs = super().get_queryset().select_related('supplier')
        q = self.request.GET.get('q', '').strip()
        alert = self.request.GET.get('alert', '')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(reference__icontains=q) | qs.filter(category__icontains=q)
        if alert:
            qs = [p for p in qs if p.needs_reorder]
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['alert_filter'] = self.request.GET.get('alert', '')
        return ctx


class PartCreateView(GarageRequiredMixin, CreateView):
    model = Part
    form_class = PartForm
    template_name = 'inventory/part_form.html'
    success_url = reverse_lazy('part_list')

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def form_valid(self, form):
        messages.success(self.request, "Pièce ajoutée.")
        return super().form_valid(form)


class PartUpdateView(GarageRequiredMixin, UpdateView):
    model = Part
    form_class = PartForm
    template_name = 'inventory/part_form.html'
    success_url = reverse_lazy('part_list')

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def form_valid(self, form):
        messages.success(self.request, "Pièce mise à jour.")
        return super().form_valid(form)


class SupplierListView(GarageRequiredMixin, ListView):
    model = Supplier
    template_name = 'inventory/supplier_list.html'
    context_object_name = 'suppliers'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class SupplierCreateView(GarageRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'
    success_url = reverse_lazy('supplier_list')

    def form_valid(self, form):
        messages.success(self.request, "Fournisseur ajouté.")
        return super().form_valid(form)


class SupplierUpdateView(GarageRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'
    success_url = reverse_lazy('supplier_list')

    def form_valid(self, form):
        messages.success(self.request, "Fournisseur mis à jour.")
        return super().form_valid(form)
