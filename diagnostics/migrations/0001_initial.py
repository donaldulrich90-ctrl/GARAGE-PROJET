import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('repair_orders', '0001_initial'),
        ('tenants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DiagnosticReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reference', models.CharField(blank=True, max_length=20, unique=True, verbose_name='Référence')),
                ('scan_date', models.DateTimeField(verbose_name='Date du scan')),
                ('mileage', models.PositiveIntegerField(blank=True, null=True, verbose_name='Kilométrage')),
                ('scanner_name', models.CharField(blank=True, max_length=100, verbose_name='Outil de diagnostic')),
                ('summary', models.TextField(blank=True, verbose_name='Résumé')),
                ('observations', models.TextField(blank=True, verbose_name='Observations du technicien')),
                ('recommendations', models.TextField(blank=True, verbose_name='Recommandations')),
                ('original_file', models.FileField(blank=True, null=True, upload_to='diagnostics/%Y/%m/', verbose_name='Fichier scanner original')),
                ('garage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='diagnosticreports', to='tenants.garage')),
                ('repair_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='diagnostic_reports', to='repair_orders.repairorder', verbose_name='Ordre de réparation')),
                ('technician', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='diagnostic_reports', to=settings.AUTH_USER_MODEL, verbose_name='Technicien')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='diagnostics_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
            ],
            options={
                'verbose_name': 'Rapport de diagnostic',
                'verbose_name_plural': 'Rapports de diagnostic',
                'ordering': ['-scan_date'],
            },
        ),
        migrations.CreateModel(
            name='DiagnosticCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, verbose_name='Code DTC')),
                ('module_system', models.CharField(blank=True, max_length=100, verbose_name='Calculateur / Système')),
                ('description', models.CharField(blank=True, max_length=255, verbose_name='Description')),
                ('status', models.CharField(
                    choices=[
                        ('present', 'Présent'),
                        ('stored', 'Mémorisé'),
                        ('history', 'Historique'),
                        ('pending', 'En attente'),
                        ('info', 'Information'),
                    ],
                    default='present',
                    max_length=20,
                    verbose_name='Statut',
                )),
                ('diagnostic_report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='codes', to='diagnostics.diagnosticreport', verbose_name='Rapport de diagnostic')),
            ],
            options={
                'verbose_name': 'Code défaut (DTC)',
                'verbose_name_plural': 'Codes défauts (DTC)',
                'ordering': ['code'],
            },
        ),
    ]
