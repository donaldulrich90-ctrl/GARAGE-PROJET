from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clients', '0001_initial'),
        ('repair_orders', '0001_initial'),
        ('tenants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Insurance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('insurance_company', models.CharField(max_length=150, verbose_name="Compagnie d'assurance")),
                ('policy_number', models.CharField(max_length=80, verbose_name='N° de police')),
                ('insurance_type', models.CharField(choices=[('liability', 'Responsabilité civile (RC)'), ('comprehensive', 'Tous risques'), ('third_party_fire_theft', 'Tiers + Vol + Incendie'), ('fleet', 'Flotte')], default='liability', max_length=30, verbose_name="Type d'assurance")),
                ('start_date', models.DateField(verbose_name='Date de début')),
                ('end_date', models.DateField(verbose_name='Date de fin')),
                ('premium_amount', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='Prime (FCFA)')),
                ('coverage_details', models.TextField(blank=True, verbose_name='Détails de couverture')),
                ('agent_name', models.CharField(blank=True, max_length=100, verbose_name='Agent / Courtier')),
                ('agent_phone', models.CharField(blank=True, max_length=30, verbose_name='Téléphone agent')),
                ('document', models.FileField(blank=True, null=True, upload_to='insurance/', verbose_name='Document (attestation)')),
                ('reminder_sent', models.BooleanField(default=False, verbose_name='Rappel envoyé')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='insurances_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('garage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='insurances', to='tenants.garage')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='insurances', to='clients.vehicle', verbose_name='Véhicule')),
            ],
            options={
                'verbose_name': 'Assurance',
                'verbose_name_plural': 'Assurances',
                'ordering': ['-end_date'],
            },
        ),
        migrations.CreateModel(
            name='InsuranceClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('claim_number', models.CharField(max_length=80, verbose_name='N° de déclaration')),
                ('claim_date', models.DateField(verbose_name='Date du sinistre')),
                ('claim_type', models.CharField(choices=[('accident', 'Accident'), ('theft', 'Vol'), ('fire', 'Incendie'), ('natural_disaster', 'Catastrophe naturelle'), ('vandalism', 'Vandalisme'), ('other', 'Autre')], default='accident', max_length=20, verbose_name='Type de sinistre')),
                ('description', models.TextField(verbose_name='Description du sinistre')),
                ('estimated_cost', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='Coût estimé (FCFA)')),
                ('approved_amount', models.DecimalField(blank=True, decimal_places=0, max_digits=12, null=True, verbose_name='Montant approuvé (FCFA)')),
                ('status', models.CharField(choices=[('declared', 'Déclaré'), ('under_review', 'En examen'), ('approved', 'Approuvé'), ('rejected', 'Rejeté'), ('paid', 'Payé')], default='declared', max_length=20, verbose_name='Statut')),
                ('documents', models.FileField(blank=True, null=True, upload_to='insurance/claims/', verbose_name='Documents justificatifs')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('garage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='insuranceclaims', to='tenants.garage')),
                ('insurance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='claims', to='insurance.insurance', verbose_name="Police d'assurance")),
                ('repair_order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='insurance_claims', to='repair_orders.repairorder', verbose_name='Ordre de réparation')),
            ],
            options={
                'verbose_name': 'Sinistre',
                'verbose_name_plural': 'Sinistres',
                'ordering': ['-claim_date'],
            },
        ),
    ]
