"""
Services métier pour les commandes fournisseur.

Ces fonctions encapsulent les transitions de statut et les effets de bord
(stock, mouvements, création de Part garage à la livraison).
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.i18n import tr

from .models import (
    Part,
    StockMovement,
    SupplierOrder,
    SupplierOrderLine,
    SupplierPart,
    SupplierStockMovement,
)


class OrderTransitionError(Exception):
    pass


@transaction.atomic
def submit_order(order: SupplierOrder) -> SupplierOrder:
    if not order.can_submit():
        raise OrderTransitionError(tr(
            "Impossible de soumettre cette commande (statut ou lignes).",
            "This order cannot be submitted (status or lines).",
        ))
    order.recompute_total()
    order.status = SupplierOrder.STATUS_SUBMITTED
    order.submitted_at = timezone.now()
    order.save()
    return order


@transaction.atomic
def validate_order(order: SupplierOrder, supplier_note: str = "") -> SupplierOrder:
    """Le fournisseur valide la commande. Verrouille la commission et décrémente le stock fournisseur."""
    order = SupplierOrder.objects.select_for_update().select_related("garage", "supplier").get(pk=order.pk)
    if not order.can_validate():
        raise OrderTransitionError(tr(
            "Cette commande ne peut pas être validée.",
            "This order cannot be approved.",
        ))
    lines = list(order.lines.select_related("supplier_part", "supplier_part__catalog_part"))
    part_ids = [line.supplier_part_id for line in lines if line.supplier_part_id]
    locked_parts = {
        part.pk: part
        for part in SupplierPart.objects.select_for_update().filter(pk__in=part_ids)
    }
    # Vérifier le stock disponible
    for line in lines:
        sp = locked_parts.get(line.supplier_part_id)
        if sp is None:
            continue
        if sp.quantity_available < line.quantity:
            raise OrderTransitionError(tr(
                f"Stock insuffisant pour {line.catalog_name} : disponible {sp.quantity_available}, demandé {line.quantity}.",
                f"Insufficient stock for {line.catalog_name}: {sp.quantity_available} available, {line.quantity} requested.",
            ))
    # Décrémenter + journaliser les sorties
    for line in lines:
        sp = locked_parts.get(line.supplier_part_id)
        if sp is None:
            continue
        SupplierStockMovement.objects.create(
            supplier_part=sp,
            movement_type=SupplierStockMovement.MOVEMENT_OUT,
            quantity=line.quantity,
            unit_price=line.unit_price,
            destination_garage=order.garage,
            sale_reference=order.reference,
            customer_name=order.garage.name,
            payment_method=SupplierStockMovement.PAYMENT_CREDIT,
            source_order=order,
            reason=f"Commande {order.reference} validée",
        ).apply_to_stock()
    order.recompute_total()
    order.snapshot_commission()
    order.status = SupplierOrder.STATUS_VALIDATED
    order.validated_at = timezone.now()
    if supplier_note:
        order.supplier_note = supplier_note
    order.save()
    return order


@transaction.atomic
def reject_order(order: SupplierOrder, reason: str) -> SupplierOrder:
    if not order.can_reject():
        raise OrderTransitionError(tr(
            "Cette commande ne peut pas être rejetée.",
            "This order cannot be rejected.",
        ))
    order.status = SupplierOrder.STATUS_REJECTED
    order.rejected_at = timezone.now()
    order.rejection_reason = reason or "Sans motif"
    order.save()
    return order


@transaction.atomic
def ship_order(order: SupplierOrder) -> SupplierOrder:
    if not order.can_ship():
        raise OrderTransitionError(tr(
            "Cette commande ne peut pas être marquée expédiée.",
            "This order cannot be marked as shipped.",
        ))
    order.status = SupplierOrder.STATUS_SHIPPED
    order.shipped_at = timezone.now()
    order.save()
    return order


@transaction.atomic
def deliver_order(order: SupplierOrder) -> SupplierOrder:
    """Le garage confirme la réception. Crée les Part manquants et enregistre l'entrée en stock."""
    if not order.can_deliver():
        raise OrderTransitionError(tr(
            "Cette commande ne peut pas être marquée livrée.",
            "This order cannot be marked as delivered.",
        ))
    garage = order.garage
    for line in order.lines.select_related("supplier_part", "supplier_part__catalog_part"):
        sp = line.supplier_part
        catalog_part = sp.catalog_part if sp else None
        # Trouver ou créer une Part garage rattachée au catalogue
        part = None
        if catalog_part:
            part = Part.objects.filter(garage=garage, catalog_part=catalog_part).first()
        if part is None:
            # Créer la Part au vol
            part = Part.objects.create(
                garage=garage,
                reference=(catalog_part.reference if catalog_part else line.catalog_reference) or f"AUTO-{line.pk}",
                name=line.catalog_name or (catalog_part.name if catalog_part else "Pièce"),
                catalog_part=catalog_part,
                supplier=order.supplier,
                unit_price=line.unit_price,
                quantity_in_stock=0,
            )
        # Incrémenter le stock du garage + journaliser
        part.quantity_in_stock = part.quantity_in_stock + line.quantity
        part.unit_price = line.unit_price  # dernier prix connu
        part.save(update_fields=["quantity_in_stock", "unit_price", "updated_at"])
        StockMovement.objects.create(
            garage=garage,
            part=part,
            movement_type=StockMovement.MOVEMENT_IN,
            quantity=line.quantity,
            reason=f"Livraison commande {order.reference}",
        )
    order.status = SupplierOrder.STATUS_DELIVERED
    order.delivered_at = timezone.now()
    order.save()
    return order


@transaction.atomic
def cancel_order(order: SupplierOrder) -> SupplierOrder:
    if not order.can_cancel():
        raise OrderTransitionError(tr(
            "Cette commande ne peut plus être annulée.",
            "This order can no longer be cancelled.",
        ))
    order.status = SupplierOrder.STATUS_CANCELLED
    order.cancelled_at = timezone.now()
    order.save()
    return order


def add_line_from_supplier_part(order: SupplierOrder, supplier_part: SupplierPart, quantity: int) -> SupplierOrderLine:
    """Ajoute (ou incrémente) une ligne pour l'offre fournisseur donnée."""
    if order.status != SupplierOrder.STATUS_DRAFT:
        raise OrderTransitionError(tr(
            "On ne peut ajouter des lignes qu'à une commande en brouillon.",
            "Lines can only be added to a draft order.",
        ))
    if supplier_part.supplier_id != order.supplier_id:
        raise OrderTransitionError(tr(
            "Cette offre n'appartient pas au fournisseur de la commande.",
            "This offer does not belong to the order supplier.",
        ))
    line = order.lines.filter(supplier_part=supplier_part).first()
    if line:
        line.quantity = line.quantity + quantity
        line.save()
    else:
        line = SupplierOrderLine.objects.create(
            order=order,
            supplier_part=supplier_part,
            catalog_reference=supplier_part.catalog_part.reference,
            catalog_name=supplier_part.catalog_part.name,
            g_code=supplier_part.g_code,
            unit_price=supplier_part.unit_price,
            quantity=quantity,
        )
    order.recompute_total()
    order.save(update_fields=["total_amount", "updated_at"])
    return line
