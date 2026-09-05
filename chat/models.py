"""Messagerie directe entre un fournisseur et un garage.

Un fil de discussion unique par couple (fournisseur, garage). Les
mécaniciens (et tout le staff du garage) échangent avec le fournisseur,
texte et/ou photo.
"""
from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Conversation(TimeStampedModel):
    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    garage = models.ForeignKey(
        "tenants.Garage",
        on_delete=models.CASCADE,
        related_name="supplier_conversations",
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Conversation"
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "garage"],
                name="unique_conversation_supplier_garage",
            ),
        ]

    def __str__(self):
        return f"{self.supplier.name} ↔ {self.garage.name}"


class ChatMessage(TimeStampedModel):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_messages",
    )
    # Côté émetteur : True = fournisseur, False = garage (mécanicien/staff).
    from_supplier = models.BooleanField(default=False)
    body = models.TextField("Message", blank=True)
    image = models.ImageField("Photo", upload_to="chat/%Y/%m/", null=True, blank=True)
    read_by_supplier = models.BooleanField(default=False)
    read_by_garage = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Message"

    def __str__(self):
        who = "Fournisseur" if self.from_supplier else "Garage"
        return f"{who} #{self.pk}"
