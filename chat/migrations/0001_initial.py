import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventory", "0009_supplier_independent_global"),
        ("tenants", "0007_garage_feature_overrides"),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("garage", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="supplier_conversations", to="tenants.garage")),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversations", to="inventory.supplier")),
            ],
            options={
                "verbose_name": "Conversation",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("from_supplier", models.BooleanField(default=False)),
                ("body", models.TextField(blank=True, verbose_name="Message")),
                ("image", models.ImageField(blank=True, null=True, upload_to="chat/%Y/%m/", verbose_name="Photo")),
                ("read_by_supplier", models.BooleanField(default=False)),
                ("read_by_garage", models.BooleanField(default=False)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chat.conversation")),
                ("sender", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chat_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Message",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="conversation",
            constraint=models.UniqueConstraint(fields=("supplier", "garage"), name="unique_conversation_supplier_garage"),
        ),
    ]
