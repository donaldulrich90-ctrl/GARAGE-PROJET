from django.contrib import messages
from django.db.models import Min, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from catalog.models import CatalogPart
from core.views import GarageRequiredMixin

from . import services
from .forms import PartForm, SupplierForm, SupplierPartForm
from .models import Part, Supplier, SupplierPart, SupplierOrder


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


# ── Offres fournisseurs (SupplierPart) ────────────────────────────────────────

class SupplierPartListView(GarageRequiredMixin, ListView):
    """Liste des offres (prix fournisseurs) pour les pièces catalogue."""
    model = SupplierPart
    template_name = 'inventory/supplier_part_list.html'
    context_object_name = 'offers'
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related('supplier', 'catalog_part', 'catalog_part__category')
        q = self.request.GET.get('q', '').strip()
        supplier_id = self.request.GET.get('supplier', '')
        if q:
            qs = qs.filter(catalog_part__name__icontains=q) | qs.filter(catalog_part__reference__icontains=q)
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        return qs.order_by('catalog_part__name', 'unit_price')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_supplier'] = self.request.GET.get('supplier', '')
        ctx['suppliers'] = Supplier.objects.for_garage(self.garage).order_by('name')
        return ctx


class SupplierPartCreateView(GarageRequiredMixin, CreateView):
    model = SupplierPart
    form_class = SupplierPartForm
    template_name = 'inventory/supplier_part_form.html'
    success_url = reverse_lazy('supplier_part_list')

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def get_initial(self):
        initial = super().get_initial()
        supplier_pk = self.request.GET.get('supplier')
        if supplier_pk:
            initial['supplier'] = supplier_pk
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Offre fournisseur enregistrée.")
        return super().form_valid(form)


class SupplierPartUpdateView(GarageRequiredMixin, UpdateView):
    model = SupplierPart
    form_class = SupplierPartForm
    template_name = 'inventory/supplier_part_form.html'
    success_url = reverse_lazy('supplier_part_list')

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def form_valid(self, form):
        messages.success(self.request, "Offre fournisseur mise à jour.")
        return super().form_valid(form)


class SupplierPartDeleteView(GarageRequiredMixin, DeleteView):
    model = SupplierPart
    template_name = 'inventory/supplier_part_confirm_delete.html'
    success_url = reverse_lazy('supplier_part_list')

    def form_valid(self, form):
        messages.success(self.request, "Offre supprimée.")
        return super().form_valid(form)


# ── Commandes fournisseur (garage) ────────────────────────────────────────────

class SupplierOrderListView(GarageRequiredMixin, ListView):
    model = SupplierOrder
    template_name = 'inventory/order_list.html'
    context_object_name = 'orders'
    paginate_by = 30

    def get_queryset(self):
        qs = SupplierOrder.objects.filter(garage=self.garage).select_related('supplier')
        status = self.request.GET.get('status', '')
        if status:
            qs = qs.filter(status=status)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['statuses'] = SupplierOrder.STATUS_CHOICES
        return ctx


class SupplierOrderDetailView(GarageRequiredMixin, DetailView):
    model = SupplierOrder
    template_name = 'inventory/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return SupplierOrder.objects.filter(garage=self.garage).select_related('supplier')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['lines'] = self.object.lines.select_related('supplier_part__catalog_part').all()
        return ctx


class SupplierCatalogView(GarageRequiredMixin, DetailView):
    """Parcourt les offres d'un fournisseur pour préparer une commande."""
    model = Supplier
    template_name = 'inventory/supplier_catalog.html'
    context_object_name = 'supplier'

    def get_queryset(self):
        return Supplier.objects.for_garage(self.garage)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        offers = SupplierPart.objects.filter(supplier=self.object).select_related('catalog_part', 'catalog_part__category')
        q = self.request.GET.get('q', '').strip()
        if q:
            offers = offers.filter(catalog_part__name__icontains=q) | offers.filter(catalog_part__reference__icontains=q)
        ctx['offers'] = offers.order_by('catalog_part__name')
        # Récupérer / créer une commande brouillon en cours pour ce fournisseur
        ctx['draft_order'] = SupplierOrder.objects.filter(
            garage=self.garage, supplier=self.object, status=SupplierOrder.STATUS_DRAFT
        ).first()
        ctx['q'] = q
        return ctx


def _get_or_create_draft_order(garage, supplier):
    order, _ = SupplierOrder.objects.get_or_create(
        garage=garage, supplier=supplier, status=SupplierOrder.STATUS_DRAFT,
    )
    return order


class SupplierOrderAddLineView(GarageRequiredMixin, DetailView):
    """POST : ajoute une ligne à la commande brouillon depuis une SupplierPart."""
    model = SupplierPart
    http_method_names = ['post']

    def get_queryset(self):
        return SupplierPart.objects.for_garage(self.garage).select_related('supplier', 'catalog_part')

    def post(self, request, *args, **kwargs):
        offer = self.get_object()
        try:
            qty = int(request.POST.get('quantity', '1'))
        except ValueError:
            qty = 1
        qty = max(1, qty)
        order = _get_or_create_draft_order(self.garage, offer.supplier)
        try:
            services.add_line_from_supplier_part(order, offer, qty)
            messages.success(request, f"{qty} × {offer.catalog_part.name} ajouté(s) à votre commande.")
        except services.OrderTransitionError as e:
            messages.error(request, str(e))
        return redirect('supplier_catalog', pk=offer.supplier_id)


class SupplierOrderSubmitView(GarageRequiredMixin, DetailView):
    model = SupplierOrder
    http_method_names = ['post']

    def get_queryset(self):
        return SupplierOrder.objects.filter(garage=self.garage)

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            services.submit_order(order)
            messages.success(request, f"Commande {order.reference} soumise au fournisseur.")
        except services.OrderTransitionError as e:
            messages.error(request, str(e))
        return redirect('supplier_order_detail', pk=order.pk)


class SupplierOrderCancelView(GarageRequiredMixin, DetailView):
    model = SupplierOrder
    http_method_names = ['post']

    def get_queryset(self):
        return SupplierOrder.objects.filter(garage=self.garage)

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            services.cancel_order(order)
            messages.success(request, "Commande annulée.")
        except services.OrderTransitionError as e:
            messages.error(request, str(e))
        return redirect('supplier_order_detail', pk=order.pk)


class SupplierOrderDeliverView(GarageRequiredMixin, DetailView):
    model = SupplierOrder
    http_method_names = ['post']

    def get_queryset(self):
        return SupplierOrder.objects.filter(garage=self.garage)

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            services.deliver_order(order)
            messages.success(request, "Livraison enregistrée, stock mis à jour.")
        except services.OrderTransitionError as e:
            messages.error(request, str(e))
        return redirect('supplier_order_detail', pk=order.pk)


class CatalogPartCompareView(GarageRequiredMixin, DetailView):
    """Compare les prix de tous les fournisseurs pour une pièce catalogue donnée."""
    model = CatalogPart
    template_name = 'inventory/catalog_part_compare.html'
    context_object_name = 'catalog_part'

    def get_queryset(self):
        # Non-tenant : accessible à tout garage authentifié.
        return CatalogPart.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        offers = SupplierPart.objects.for_garage(self.garage).filter(
            catalog_part=self.object
        ).select_related('supplier').order_by('unit_price')
        ctx['offers'] = offers
        ctx['best_offer'] = offers.first()
        return ctx
