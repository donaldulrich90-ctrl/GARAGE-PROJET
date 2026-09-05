"""Vues de la messagerie fournisseur ↔ garage.

Côté garage : accessible à tout le staff (mécaniciens inclus).
Côté fournisseur : réservé aux comptes fournisseurs.
Un fil unique par couple (fournisseur, garage), créé à la volée.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from inventory.models import Supplier, SupplierOrder
from supplier_portal.decorators import supplier_required
from tenants.models import Garage

from .forms import ChatMessageForm
from .models import Conversation


# ---------------------------------------------------------------- côté garage

@login_required
def garage_inbox(request):
    garage = getattr(request.user, "garage", None)
    if garage is None:
        return redirect("dashboard_home")

    convs = {c.supplier_id: c for c in Conversation.objects.filter(garage=garage)}
    rows = []
    for supplier in Supplier.objects.all().order_by("name"):
        conv = convs.get(supplier.id)
        last = unread = None
        if conv:
            last = conv.messages.last()
            unread = conv.messages.filter(from_supplier=True, read_by_garage=False).count()
        rows.append({"supplier": supplier, "conversation": conv, "last": last, "unread": unread or 0})

    rows.sort(key=lambda r: (r["last"].created_at if r["last"] else r["supplier"].created_at), reverse=True)
    return render(request, "chat/garage_inbox.html", {"rows": rows, "n": "chat"})


@login_required
def garage_thread(request, supplier_pk):
    garage = getattr(request.user, "garage", None)
    if garage is None:
        return redirect("dashboard_home")
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    conv, _ = Conversation.objects.get_or_create(garage=garage, supplier=supplier)

    if request.method == "POST":
        form = ChatMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.conversation = conv
            msg.sender = request.user
            msg.from_supplier = False
            msg.read_by_garage = True
            msg.save()
            conv.save(update_fields=["updated_at"])
            return redirect("chat:garage_thread", supplier_pk=supplier.pk)
    else:
        form = ChatMessageForm()

    conv.messages.filter(from_supplier=True, read_by_garage=False).update(read_by_garage=True)
    return render(request, "chat/garage_thread.html", {
        "conversation": conv,
        "supplier": supplier,
        "chat_messages": conv.messages.select_related("sender"),
        "form": form,
        "n": "chat",
    })


# ----------------------------------------------------------- côté fournisseur

@supplier_required
def supplier_inbox(request):
    supplier = request.user.supplier

    garage_ids = set(
        SupplierOrder.objects.filter(supplier=supplier).values_list("garage_id", flat=True)
    )
    garage_ids |= set(
        Conversation.objects.filter(supplier=supplier).values_list("garage_id", flat=True)
    )
    convs = {c.garage_id: c for c in Conversation.objects.filter(supplier=supplier)}

    rows = []
    for garage in Garage.objects.filter(id__in=garage_ids).order_by("name"):
        conv = convs.get(garage.id)
        last = unread = None
        if conv:
            last = conv.messages.last()
            unread = conv.messages.filter(from_supplier=False, read_by_supplier=False).count()
        rows.append({"garage": garage, "conversation": conv, "last": last, "unread": unread or 0})

    rows.sort(key=lambda r: (r["last"].created_at if r["last"] else r["garage"].created_at), reverse=True)
    return render(request, "chat/supplier_inbox.html", {"rows": rows, "n": "chat"})


@supplier_required
def supplier_thread(request, garage_pk):
    supplier = request.user.supplier
    garage = get_object_or_404(Garage, pk=garage_pk)
    conv, _ = Conversation.objects.get_or_create(garage=garage, supplier=supplier)

    if request.method == "POST":
        form = ChatMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.conversation = conv
            msg.sender = request.user
            msg.from_supplier = True
            msg.read_by_supplier = True
            msg.save()
            conv.save(update_fields=["updated_at"])
            return redirect("chat:supplier_thread", garage_pk=garage.pk)
    else:
        form = ChatMessageForm()

    conv.messages.filter(from_supplier=False, read_by_supplier=False).update(read_by_supplier=True)
    return render(request, "chat/supplier_thread.html", {
        "conversation": conv,
        "garage": garage,
        "chat_messages": conv.messages.select_related("sender"),
        "form": form,
        "n": "chat",
    })
