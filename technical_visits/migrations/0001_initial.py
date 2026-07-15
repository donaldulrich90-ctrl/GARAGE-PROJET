from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clients', '0001_initial'),
        ('tenants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TechnicalVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('visit_type', models.CharField(choices=[('periodic', 'Périodique'), ('pre_sale', 'Avant-vente'), ('voluntary', 'Volontaire'), ('post_accident', 'Après accident')], default='periodic', max_length=20, verbose_name='Type de visite')),
                ('visit_date', models.DateField(verbose_name='Date de la visite')),
                ('expiry_date', models.DateField(verbose_name="Date d'expiration")),
                ('result', models.CharField(choices=[('passed', 'Admis'), ('failed', 'Refusé'), ('conditional', 'Admis sous réserve')], default='passed', max_length=20, verbose_name='Résultat')),
                ('inspection_center', models.CharField(max_length=150, verbose_name='Centre de contrôle')),
                ('certificate_number', models.CharField(blank=True, max_length=80, verbose_name='N° certificat / PV')),
                ('observations', models.TextField(blank=True, verbose_name='Observations')),
                ('defects', models.JSONField(blank=True, default=list, verbose_name='Défauts constatés')),
                ('cost', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='Coût (FCFA)')),
                ('document', models.FileField(blank=True, null=True, upload_to='technical_visits/', verbose_name='Document (scan PV)')),
                ('reminder_sent', models.BooleanField(default=False, verbose_name='Rappel envoyé')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='technical_visits_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('garage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='technicalvisits', to='tenants.garage')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='technical_visits', to='clients.vehicle', verbose_name='Véhicule')),
            ],
            options={
                'verbose_name': 'Visite technique',
                'verbose_name_plural': 'Visites techniques',
                'ordering': ['-visit_date'],
            },
        ),
    ]
