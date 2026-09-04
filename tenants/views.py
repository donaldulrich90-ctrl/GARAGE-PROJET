from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction

from accounts.models import User
from .forms import GarageCreateForm, GarageEditForm
from .models import Garage


def _require_superuser(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé au staff plateforme.")
        return redirect("dashboard_home")
    return None


@login_required
def garage_list(request):
    guard = _require_superuser(request)
    if guard:
        return guard
    garages = Garage.objects.all().prefetch_related("users").order_by("name")
    return render(request, "tenants/garage_list.html", {"garages": garages})


@login_required
def garage_create(request):
    guard = _require_superuser(request)
    if guard:
        return guard
    if request.method == "POST":
        form = GarageCreateForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            garage = Garage(
                name=cd["name"],
                city=cd.get("city", ""),
                phone=cd.get("phone", ""),
                whatsapp_number=cd.get("whatsapp_number", ""),
                email=cd.get("email", ""),
                address=cd.get("address", ""),
                ifu=cd.get("ifu", ""),
                rccm=cd.get("rccm", ""),
                plan=cd["plan"],
                trial_ends_at=cd.get("trial_ends_at"),
                faest_supplier_enabled=cd.get("faest_supplier_enabled", False),
            )
            garage.feature_overrides = form.get_feature_overrides()
            if cd.get("signature"):
                garage.signature = cd["signature"]
            if cd.get("cachet"):
                garage.cachet = cd["cachet"]
            garage.save()
            User.objects.create_user(
                username=cd["admin_username"],
                first_name=cd.get("admin_first_name", ""),
                last_name=cd.get("admin_last_name", ""),
                password=cd["admin_password"],
                garage=garage,
                role=User.ROLE_ADMIN,
                is_staff=False,
                is_superuser=False,
            )
            messages.success(request, f"Garage « {garage.name} » créé avec son administrateur.")
            return redirect("garage_list")
    else:
        form = GarageCreateForm()
    return render(request, "tenants/garage_form.html", {"form": form, "action": "Créer un garage"})


@login_required
def garage_edit(request, pk):
    guard = _require_superuser(request)
    if guard:
        return guard
    garage = get_object_or_404(Garage, pk=pk)
    staff = garage.users.order_by("role", "username")
    if request.method == "POST":
        form = GarageEditForm(request.POST, request.FILES, instance=garage)
        if form.is_valid():
            form.save()
            messages.success(request, f"Garage « {garage.name} » mis à jour.")
            return redirect("garage_list")
    else:
        form = GarageEditForm(instance=garage)
    return render(request, "tenants/garage_form.html", {
        "form": form,
        "action": "Modifier le garage",
        "garage": garage,
        "staff": staff,
    })


@login_required
def garage_toggle(request, pk):
    guard = _require_superuser(request)
    if guard:
        return guard
    if request.method == "POST":
        garage = get_object_or_404(Garage, pk=pk)
        garage.is_active = not garage.is_active
        garage.save(update_fields=["is_active", "updated_at"])
        etat = "activé" if garage.is_active else "désactivé"
        messages.success(request, f"Garage « {garage.name} » {etat}.")
    return redirect("garage_list")


@login_required
def garage_supplier_create(request, pk):
    """Le super-admin crée un fournisseur (+ son compte portail) pour un garage."""
    guard = _require_superuser(request)
    if guard:
        return guard
    from accounts.forms import SupplierUserCreateForm
    garage = get_object_or_404(Garage, pk=pk)
    if request.method == "POST":
        form = SupplierUserCreateForm(request.POST, request.FILES, garage=garage)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(garage=garage)
            messages.success(
                request,
                f"Fournisseur « {user.supplier.name} » créé (compte : {user.username}) pour {garage.name}.",
            )
            return redirect("garage_edit", pk=garage.pk)
    else:
        form = SupplierUserCreateForm(garage=garage)
    return render(request, "tenants/supplier_form.html", {"form": form, "garage": garage})


# ══════════════════════════════════════════════════════════════════════════════
#  FOURNISSEURS INDÉPENDANTS (back-office plateforme)
#  Gestion des comptes fournisseurs sans passer par un garage : les fournisseurs
#  sont des entités indépendantes qui approvisionnent les garages du SaaS.
# ══════════════════════════════════════════════════════════════════════════════


@login_required
def platform_supplier_list(request):
    guard = _require_superuser(request)
    if guard:
        return guard
    from django.db.models import Count
    from inventory.models import Supplier

    q = request.GET.get("q", "").strip()
    suppliers = Supplier.objects.annotate(
        n_offers=Count("catalog_offers", distinct=True),
        n_orders=Count("orders_received", distinct=True),
    ).prefetch_related("users").order_by("name")
    if q:
        suppliers = suppliers.filter(name__icontains=q)
    return render(request, "tenants/supplier_account_list.html", {
        "suppliers": suppliers,
        "q": q,
    })


@login_required
def platform_supplier_create(request):
    """Crée un fournisseur indépendant (+ son compte portail), sans garage."""
    guard = _require_superuser(request)
    if guard:
        return guard
    from accounts.forms import SupplierUserCreateForm

    if request.method == "POST":
        form = SupplierUserCreateForm(request.POST, request.FILES, garage=None)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(garage=None)
            messages.success(
                request,
                f"Fournisseur indépendant « {user.supplier.name} » créé "
                f"(compte : {user.username}).",
            )
            return redirect("platform_supplier_list")
    else:
        form = SupplierUserCreateForm(garage=None)
    return render(request, "tenants/supplier_account_form.html", {"form": form})
