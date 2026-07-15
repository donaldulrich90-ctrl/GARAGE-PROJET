from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clients', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VehicleTax',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tax_type', models.CharField(
                    choices=[
                        ('vignette', 'Vignette automobile'),
                        ('taxe_stationnement', 'Taxe de stationnement'),
                        ('patente', 'Patente transport'),
                        ('timbre', 'Droit de timbre'),
                        ('autre', 'Autre'),
                    ],
                    default='vignette', max_length=30, verbose_name='Type de taxe',
                )),
                ('description', models.CharField(blank=True, max_length=200, verbose_name='Description (si Autre)')),
                ('fiscal_year', models.PositiveIntegerField(verbose_name='Année fiscale')),
                ('amount', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='Montant (FCFA)')),
                ('due_date', models.DateField(verbose_name='Date limite de paiement')),
                ('payment_date', models.DateField(blank=True, null=True, verbose_name='Date de paiement effectif')),
                ('is_paid', models.BooleanField(default=False, verbose_name='Payé')),
                ('receipt_number', models.CharField(blank=True, max_length=80, verbose_name='N° quittance')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('document', models.FileField(blank=True, null=True, upload_to='taxes/', verbose_name='Document (scan quittance)')),
                ('garage', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='vehicletaxes',
                    to='tenants.garage',
                )),
                ('vehicle', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='taxes',
                    to='clients.vehicle',
                    verbose_name='Véhicule',
                )),
            ],
            options={
                'verbose_name': 'Taxe véhicule',
                'verbose_name_plural': 'Taxes véhicules',
                'ordering': ['-fiscal_year', 'due_date'],
            },
        ),
    ]
