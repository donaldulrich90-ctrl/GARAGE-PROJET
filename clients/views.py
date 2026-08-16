from datetime import date, timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Case, CharField, OuterRef, Q, Subquery, Value, When
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from core.views import GarageRequiredMixin

from catalog.models import VehicleModel as CatalogModel

from .forms import ClientForm, VehicleForm
from .models import Client, Vehicle, VehiclePhoto


def _make_model_json():
    """Retourne un dict {make_id: [[model_id, model_name], ...]} pour la cascade côté formulaire."""
    result = {}
    for m in CatalogModel.objects.all().order_by('name').values('id', 'name', 'make_id'):
        result.setdefault(str(m['make_id']), []).append([m['id'], m['name']])
    return result


class ClientListView(GarageRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
            )
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
        from technical_visits.models import TechnicalVisit
        from insurance.models import Insurance

        qs = super().get_queryset().select_related('client')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(plate_number__icontains=q) |
                Q(make__icontains=q) |
                Q(model__icontains=q) |
                Q(vin__icontains=q) |
                Q(client__full_name__icontains=q)
            )

        today = date.today()
        threshold = today + timedelta(days=30)

        latest_vt = TechnicalVisit.objects.filter(
            vehicle=OuterRef('pk'), garage=self.garage
        ).order_by('-expiry_date').values('expiry_date')[:1]

        latest_ins = Insurance.objects.filter(
            vehicle=OuterRef('pk'), garage=self.garage
        ).order_by('-end_date').values('end_date')[:1]

        qs = qs.annotate(
            latest_vt_expiry=Subquery(latest_vt),
            latest_ins_end=Subquery(latest_ins),
            vt_color=Case(
                When(latest_vt_expiry__lt=today, then=Value('red')),
                When(latest_vt_expiry__lte=threshold, then=Value('orange')),
                When(latest_vt_expiry__isnull=False, then=Value('green')),
                default=Value('none'),
                output_field=CharField(),
            ),
            ins_color=Case(
                When(latest_ins_end__lt=today, then=Value('red')),
                When(latest_ins_end__lte=threshold, then=Value('orange')),
                When(latest_ins_end__isnull=False, then=Value('green')),
                default=Value('none'),
                output_field=CharField(),
            ),
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
        ctx['technical_visits'] = self.object.technical_visits.all()
        ctx['vehicle_insurances'] = self.object.insurances.select_related().prefetch_related('claims').all()
        ctx['photos'] = self.object.photos.all()
        from diagnostics.models import DiagnosticReport
        ctx['vehicle_diagnostics'] = (
            DiagnosticReport.objects.for_garage(self.garage)
            .filter(repair_order__vehicle=self.object)
            .select_related('technician', 'repair_order')
            .prefetch_related('codes')
            .order_by('-scan_date')
        )
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['make_model_map'] = _make_model_json()
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        files = self.request.FILES.getlist("photos")
        if files:
            with transaction.atomic():
                for f in files:
                    VehiclePhoto.objects.create(
                        garage=self.object.garage,
                        vehicle=self.object,
                        image=f,
                    )
        return response

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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['make_model_map'] = _make_model_json()
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        files = self.request.FILES.getlist("photos")
        if files:
            with transaction.atomic():
                for f in files:
                    VehiclePhoto.objects.create(
                        garage=self.object.garage,
                        vehicle=self.object,
                        image=f,
                    )
        return response

    def get_success_url(self):
        messages.success(self.request, "Véhicule mis à jour.")
        return reverse('vehicle_detail', args=[self.object.pk])


class KeyBoardView(GarageRequiredMixin, TemplateView):
    """Vue du tableau à clés physique : un emplacement numéroté par véhicule présent au garage."""
    template_name = 'clients/key_board.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        size = self.garage.key_board_size
        occupied = {
            v.key_token: v
            for v in Vehicle.objects.filter(
                garage=self.garage, is_in_garage=True, key_token__isnull=False,
            ).select_related('client')
        }
        slots = [{'number': n, 'vehicle': occupied.get(n)} for n in range(1, size + 1)]
        overflow = sorted(
            (v for tok, v in occupied.items() if tok > size),
            key=lambda v: v.key_token,
        )
        ctx['slots'] = slots
        ctx['overflow'] = overflow
        ctx['occupied_count'] = len(occupied)
        ctx['total_slots'] = size
        return ctx


class VehicleKeyTagPrintView(GarageRequiredMixin, DetailView):
    """Étiquette imprimable à accrocher à la clé du véhicule."""
    model = Vehicle
    template_name = 'clients/vehicle_keytag_print.html'
    context_object_name = 'vehicle'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['garage'] = self.garage
        return ctx
