from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


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
