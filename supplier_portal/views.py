from datetime import timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from inventory import services as order_services
from inventory.models import SupplierOrder, SupplierPart, SupplierStockMovement

from .decorators import SupplierRequiredMixin, supplier_required
from .forms import (
    OrderRejectionForm,
    SupplierPartOwnForm,
    SupplierProfileForm,
    SupplierStockMovementForm,
)


class DashboardView(SupplierRequiredMixin, TemplateView):
    template_name = "supplier_portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        supplier = self.supplier
        offers = SupplierPart.objects.filter(supplier=supplier).select_related("catalog_part")
        recent_out = SupplierStockMovement.objects.filter(
            supplier_part__supplier=supplier,
            movement_type=SupplierStockMovement.MOVEMENT_OUT,
            created_at__gte=timezone.now() - timedelta(days=30),
        )
        ctx.update({
            "supplier": supplier,
            "offer_count": offers.count(),
            "total_stock": offers.aggregate(t=Sum("quantity_available"))["t"] or 0,
            "recent_out_count": recent_out.count(),
            "recent_out_total": recent_out.aggregate(t=Sum(F("quantity") * F("unit_price")))["t"] or 0,
            "low_stock": offers.filter(quantity_available__lte=2).order_by("quantity_available")[:10],
            "recent_movements": SupplierStockMovement.objects.filter(
                supplier_part__supplier=supplier
            ).select_related("supplier_part__catalog_part", "destination_garage").order_by("-created_at")[:10],
        })
        return ctx


class MyOffersListView(SupplierRequiredMixin, ListView):
    template_name = "supplier_portal/offer_list.html"
    context_object_name = "offers"
    paginate_by = 50

    def get_queryset(self):
        qs = SupplierPart.objects.filter(supplier=self.supplier).select_related("catalog_part", "catalog_part__category")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(catalog_part__name__icontains=q) | qs.filter(catalog_part__reference__icontains=q)
        return qs.order_by("catalog_part__name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class MyOfferCreateView(SupplierRequiredMixin, CreateView):
    template_name = "supplier_portal/offer_form.html"
    form_class = SupplierPartOwnForm
    success_url = reverse_lazy("supplier_portal:offer_list")

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        # Le SupplierPart hérite du garage — mais dans le portail fournisseur,
        # le supplier n'est rattaché qu'à un seul garage (le sien à l'origine).
        form.instance.garage = self.supplier.garage
        messages.success(self.request, "Pièce ajoutée à votre stock.")
        return super().form_valid(form)


class MyOfferUpdateView(SupplierRequiredMixin, UpdateView):
    template_name = "supplier_portal/offer_form.html"
    form_class = SupplierPartOwnForm
    success_url = reverse_lazy("supplier_portal:offer_list")

    def get_queryset(self):
        return SupplierPart.objects.filter(supplier=self.supplier)

    def form_valid(self, form):
        messages.success(self.request, "Pièce mise à jour.")
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
        ctx["types"] = SupplierStockMovement.MOVEMENT_CHOICES
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
        with transaction.atomic():
            self.object = form.save()
            self.object.apply_to_stock()
        messages.success(self.request, "Mouvement enregistré et stock mis à jour.")
        return redirect(self.success_url)


class ProfileView(SupplierRequiredMixin, UpdateView):
    template_name = "supplier_portal/profile.html"
    form_class = SupplierProfileForm
    success_url = reverse_lazy("supplier_portal:profile")

    def get_object(self, queryset=None):
        return self.supplier

    def form_valid(self, form):
        messages.success(self.request, "Profil mis à jour.")
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
        ctx["statuses"] = SupplierOrder.STATUS_CHOICES
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
        "Commande validée. Le stock a été décrémenté et la commission plateforme est enregistrée.",
    )


@supplier_required
def order_reject(request, pk):
    if request.method != "POST":
        return redirect("supplier_portal:order_detail", pk=pk)
    reason = request.POST.get("reason", "").strip()
    return _post_action(
        request, pk,
        lambda o: order_services.reject_order(o, reason=reason),
        "Commande rejetée.",
    )


@supplier_required
def order_ship(request, pk):
    if request.method != "POST":
        return redirect("supplier_portal:order_detail", pk=pk)
    return _post_action(
        request, pk, order_services.ship_order,
        "Commande marquée expédiée.",
    )
