from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0006_alter_garage_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="garage",
            name="feature_overrides",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Surcharge par garage (ex: messaging=true, hr=false). Vide = on suit le plan.",
                verbose_name="Options forcées (surcharge)",
            ),
        ),
    ]
