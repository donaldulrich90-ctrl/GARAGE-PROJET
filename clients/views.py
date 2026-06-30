from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.views import GarageRequiredMixin

from .forms import ClientForm, VehicleForm
from .models import Client, Vehicle


class ClientListView(GarageRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(full_name__icontains=q) | qs.filter(phone__icontains=q) | qs.filter(email__icontains=q)
        return qs.order_by('full_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ClientDetailView(GarageRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'


class ClientCreateView(GarageRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('client_list')

    def form_valid(self, form):
        messages.success(self.request, "Client créé avec succès.")
        return super().form_valid(form)


class ClientUpdateView(GarageRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'

    def get_success_url(self):
        messages.success(self.request, "Client mis à jour.")
        return reverse('client_detail', args=[self.object.pk])


class VehicleListView(GarageRequiredMixin, ListView):
    model = Vehicle
    template_name = 'clients/vehicle_list.html'
    context_object_name = 'vehicles'

    def get_queryset(self):
        qs = super().get_queryset().select_related('client')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = (
                qs.filter(plate_number__icontains=q)
                | qs.filter(make__icontains=q)
                | qs.filter(model__icontains=q)
                | qs.filter(vin__icontains=q)
                | qs.filter(client__full_name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class VehicleDetailView(GarageRequiredMixin, DetailView):
    model = Vehicle
    template_name = 'clients/vehicle_detail.html'
    context_object_name = 'vehicle'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['repair_orders'] = self.object.repair_orders.select_related('assigned_mechanic').order_by('-received_at')
        return ctx


class VehicleCreateView(GarageRequiredMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'clients/vehicle_form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def get_initial(self):
        initial = super().get_initial()
        client_pk = self.kwargs.get('client_pk') or self.request.GET.get('client')
        if client_pk:
            initial['client'] = client_pk
        return initial

    def get_success_url(self):
        messages.success(self.request, "Véhicule ajouté.")
        return reverse('vehicle_detail', args=[self.object.pk])


class VehicleUpdateView(GarageRequiredMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'clients/vehicle_form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def get_success_url(self):
        messages.success(self.request, "Véhicule mis à jour.")
        return reverse('vehicle_detail', args=[self.object.pk])
