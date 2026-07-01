from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

# Project app labels to track — excludes django internals and core itself
_TRACKED_APPS = {
    "tenants", "accounts", "clients", "inventory",
    "repair_orders", "invoicing", "expenses", "billing", "hr",
}


def _should_track(sender):
    """Return True only for project-owned models, never for AuditLog itself."""
    meta = getattr(sender, "_meta", None)
    if meta is None:
        return False
    if meta.app_label == "core" and sender.__name__ == "AuditLog":
        return False
    return meta.app_label in _TRACKED_APPS


def _get_garage(instance):
    """Best-effort: pull garage from instance or its user FK."""
    garage = getattr(instance, "garage", None)
    if garage is not None:
        return garage
    # accounts.User has garage as nullable FK
    garage_id = getattr(instance, "garage_id", None)
    if garage_id:
        from tenants.models import Garage
        return Garage.objects.filter(pk=garage_id).first()
    return None


def _get_ip(request):
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")
    return ip or None


def _record(sender, instance, action):
    from core.middleware import get_current_request, get_current_user
    from core.models import AuditLog

    user = get_current_user()
    request = get_current_request()

    garage = _get_garage(instance)
    if garage is None and user and hasattr(user, "garage") and user.garage_id:
        garage = user.garage

    authenticated_user = user if (user and getattr(user, "is_authenticated", False)) else None

    AuditLog.objects.create(
        garage=garage,
        user=authenticated_user,
        action=action,
        model_name=sender.__name__,
        object_id=str(instance.pk) if instance.pk is not None else "",
        object_repr=str(instance)[:500],
        ip_address=_get_ip(request),
    )


@receiver(post_save)
def on_post_save(sender, instance, created, raw, **kwargs):
    if raw:
        return
    if not _should_track(sender):
        return
    action = "create" if created else "update"
    _record(sender, instance, action)


@receiver(post_delete)
def on_post_delete(sender, instance, **kwargs):
    if not _should_track(sender):
        return
    _record(sender, instance, "delete")
