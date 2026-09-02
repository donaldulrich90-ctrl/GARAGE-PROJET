from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

from core.i18n import tr


def supplier_required(view_func):
    """Restreint l'accès aux comptes fournisseurs (User.role == supplier + supplier lié)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            return redirect("login")
        if not getattr(u, "is_supplier", False) or u.supplier_id is None:
            messages.error(request, tr(
                "Accès réservé aux comptes fournisseurs.",
                "Access is restricted to supplier accounts.",
            ))
            return redirect("post_login_redirect")
        if not u.supplier.garage.is_active:
            messages.error(request, tr(
                "Le compte du garage associé est désactivé.",
                "The associated garage account is disabled.",
            ))
            logout(request)
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return _wrapped


class SupplierRequiredMixin:
    """Version CBV du décorateur."""

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            return redirect("login")
        if not getattr(u, "is_supplier", False) or u.supplier_id is None:
            messages.error(request, tr(
                "Accès réservé aux comptes fournisseurs.",
                "Access is restricted to supplier accounts.",
            ))
            return redirect("post_login_redirect")
        if not u.supplier.garage.is_active:
            messages.error(request, tr(
                "Le compte du garage associé est désactivé.",
                "The associated garage account is disabled.",
            ))
            logout(request)
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)

    @property
    def supplier(self):
        return self.request.user.supplier
