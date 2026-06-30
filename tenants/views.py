from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

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
        form = GarageCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            garage = Garage.objects.create(
                name=cd["name"],
                city=cd.get("city", ""),
                phone=cd.get("phone", ""),
                whatsapp_number=cd.get("whatsapp_number", ""),
                email=cd.get("email", ""),
                address=cd.get("address", ""),
                plan=cd["plan"],
                trial_ends_at=cd.get("trial_ends_at"),
                faest_supplier_enabled=cd.get("faest_supplier_enabled", False),
            )
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
