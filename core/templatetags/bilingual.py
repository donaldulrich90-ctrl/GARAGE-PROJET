from django import template

from core.i18n import (
    EXPENSE_CATEGORY_LABELS,
    MOVEMENT_LABELS,
    ORDER_STATUS_LABELS,
    PAYMENT_LABELS,
    tr as translate_text,
    translated_label,
)

register = template.Library()


@register.simple_tag
def tr(french, english):
    return translate_text(french, english)


@register.filter
def payment_label(value):
    return translated_label(value, PAYMENT_LABELS)


@register.filter
def movement_label(value):
    return translated_label(value, MOVEMENT_LABELS)


@register.filter
def expense_category_label(value):
    return translated_label(value, EXPENSE_CATEGORY_LABELS)


@register.filter
def supplier_order_status_label(value):
    return translated_label(value, ORDER_STATUS_LABELS)
