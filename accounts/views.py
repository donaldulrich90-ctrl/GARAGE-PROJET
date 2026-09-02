from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from core.i18n import tr
from .forms import (
    AdminSetPasswordForm,
    GarageSettingsForm,
    SupplierUserCreateForm,
    UserCreateForm,
    UserEditForm,
)
from .models import User


@login_required
def post_login_redirect(request):
    """Redirige l'utilisateur après login selon son rôle."""
    u = request.user
    if getattr(u, "is_supplier", False) and u.supplier_id:
        return redirect("supplier_portal:dashboard")
    if u.garage_id is None:
        # Staff plateforme (superuser) : envoyer sur l'admin Django.
        return redirect("/admin/")
    return redirect("dashboard_home")


@login_required
def password_change(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Mot de passe modifié avec succès.")
            return redirect("password_change")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "accounts/password_change.html", {"form": form})


@login_required
def garage_settings(request):
    if not request.user.is_garage_admin:
        messages.error(request, "Accès réservé à l'administrateur du garage.")
        return redirect("dashboard_home")
    garage = request.user.garage
    if request.method == "POST":
        form = GarageSettingsForm(request.POST, request.FILES, instance=garage)
        if form.is_valid():
            form.save()
            messages.success(request, "Informations du garage mises à jour.")
            return redirect("garage_settings")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = GarageSettingsForm(instance=garage)
    return render(request, "accounts/garage_settings.html", {"form": form, "garage": garage})


def _require_garage_admin(request):
    """Returns a redirect response if not a garage admin, else None."""
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_garage_admin:
        messages.error(request, "Accès réservé à l'administrateur du garage.")
        return redirect("dashboard_home")
    return None


def _users_for_garage(garage):
    return User.objects.filter(Q(garage=garage) | Q(supplier__garage=garage)).distinct()


@login_required
def user_list(request):
    guard = _require_garage_admin(request)
    if guard:
        return guard
    staff = _users_for_garage(request.user.garage).select_related("supplier").order_by("role", "username")
    return render(request, "accounts/user_list.html", {"staff": staff})


@login_required
def user_create(request):
    guard = _require_garage_admin(request)
    if guard:
        return guard
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.garage = request.user.garage
            user.is_staff = False
            user.is_superuser = False
            user.save()
            messages.success(request, f"Compte de {user.get_full_name() or user.username} créé.")
            return redirect("user_list")
    else:
        form = UserCreateForm()
    return render(request, "accounts/user_form.html", {"form": form, "action": "Créer"})


@login_required
def user_edit(request, pk):
    guard = _require_garage_admin(request)
    if guard:
        return guard
    target = get_object_or_404(User, pk=pk, garage=request.user.garage)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            if target.pk == request.user.pk and form.cleaned_data.get("role") != User.ROLE_ADMIN:
                messages.error(request, "Vous ne pouvez pas modifier votre propre rôle d'administrateur.")
                return redirect("user_edit", pk=pk)
            form.save()
            messages.success(request, "Compte mis à jour.")
            return redirect("user_list")
    else:
        form = UserEditForm(instance=target)
    return render(request, "accounts/user_form.html", {
        "form": form,
        "action": "Modifier",
        "target": target,
    })


@login_required
def user_set_password(request, pk):
    guard = _require_garage_admin(request)
    if guard:
        return guard
    target = get_object_or_404(_users_for_garage(request.user.garage), pk=pk)
    if target.pk == request.user.pk:
        return redirect("password_change")
    if request.method == "POST":
        form = AdminSetPasswordForm(request.POST)
        if form.is_valid():
            target.set_password(form.cleaned_data["password1"])
            target.save()
            messages.success(request, f"Mot de passe de {target.get_full_name() or target.username} réinitialisé.")
            return redirect("user_list")
    else:
        form = AdminSetPasswordForm()
    return render(request, "accounts/user_set_password.html", {"form": form, "target": target})


@login_required
def supplier_user_create(request):
    """L'admin garage crée un compte fournisseur pour un de ses fournisseurs."""
    guard = _require_garage_admin(request)
    if guard:
        return guard
    if request.method == "POST":
        form = SupplierUserCreateForm(request.POST, request.FILES, garage=request.user.garage)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(garage=request.user.garage)
            messages.success(
                request,
                tr(
                    f"Compte fournisseur créé pour {user.supplier.name} (identifiant : {user.username}).",
                    f"Supplier account created for {user.supplier.name} (username: {user.username}).",
                ),
            )
            return redirect("user_list")
    else:
        form = SupplierUserCreateForm(garage=request.user.garage)
    return render(request, "accounts/supplier_user_form.html", {
        "form": form,
        "action": tr(
            "Créer le fournisseur et son compte",
            "Create supplier and account",
        ),
    })


@login_required
def user_delete(request, pk):
    guard = _require_garage_admin(request)
    if guard:
        return guard
    target = get_object_or_404(_users_for_garage(request.user.garage), pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect("user_list")
    if request.method == "POST":
        name = target.get_full_name() or target.username
        target.delete()
        messages.success(request, f"Compte de {name} supprimé.")
        return redirect("user_list")
    return render(request, "accounts/user_confirm_delete.html", {"target": target})
