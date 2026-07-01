from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .models import AuditLog


@login_required
def audit_log(request):
    user = request.user

    qs = AuditLog.objects.select_related("user", "garage").order_by("-created_at")

    if user.is_superuser:
        garage_filter = request.GET.get("garage", "")
        if garage_filter:
            qs = qs.filter(garage_id=garage_filter)
        from tenants.models import Garage
        garages = Garage.objects.all().order_by("name")
    else:
        if not (hasattr(user, "is_garage_admin") and user.is_garage_admin):
            return HttpResponseForbidden()
        qs = qs.filter(garage=user.garage)
        garages = []
        garage_filter = ""

    action_filter = request.GET.get("action", "")
    model_filter = request.GET.get("model", "")
    if action_filter:
        qs = qs.filter(action=action_filter)
    if model_filter:
        qs = qs.filter(model_name__icontains=model_filter)

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "core/audit_log.html", {
        "page_obj": page,
        "action_choices": AuditLog.ACTION_CHOICES,
        "action_filter": action_filter,
        "model_filter": model_filter,
        "garages": garages,
        "garage_filter": garage_filter,
    })


class GarageRequiredMixin(LoginRequiredMixin):
    """Vérifie que l'utilisateur est connecté et appartient à un garage."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if getattr(request.user, 'garage', None) is None:
            return redirect('dashboard_home')
        return super().dispatch(request, *args, **kwargs)

    @property
    def garage(self):
        return self.request.user.garage

    def get_queryset(self):
        return super().get_queryset().for_garage(self.garage)

    def form_valid(self, form):
        form.instance.garage = self.garage
        return super().form_valid(form)


class GarageAdminRequiredMixin(GarageRequiredMixin):
    """Réservé à l'administrateur du garage (role=admin)."""

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if hasattr(result, 'status_code') and result.status_code in (302, 301):
            return result
        if not request.user.is_garage_admin:
            messages.error(request, "Accès réservé à l'administrateur du garage.")
            return redirect('dashboard_home')
        return result
