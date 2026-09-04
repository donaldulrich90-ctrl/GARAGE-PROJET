# Generated for SupplierInvoice + SupplierInvoiceLine (facturation fournisseur).

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0007_supplier_address_supplier_city_supplier_contact_name_and_more'),
        ('tenants', '0007_garage_feature_overrides'),
    ]

    operations = [
        migrations.CreateModel(
            name='SupplierInvoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reference', models.CharField(blank=True, editable=False, max_length=30, unique=True)),
                ('issued_at', models.DateField(default=django.utils.timezone.localdate, verbose_name="Date d'émission")),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='Échéance')),
                ('status', models.CharField(choices=[('draft', 'Brouillon'), ('sent', 'Envoyée'), ('paid', 'Payée')], default='draft', max_length=20)),
                ('notes', models.TextField(blank=True, verbose_name='Notes / conditions')),
                ('garage', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='supplier_invoices', to='tenants.garage', verbose_name='Garage (client)')),
                ('order', models.ForeignKey(blank=True, help_text="Commande d'origine (si la facture en découle).", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='inventory.supplierorder')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='inventory.supplier')),
            ],
            options={
                'verbose_name': 'Facture fournisseur',
                'verbose_name_plural': 'Factures fournisseur',
                'ordering': ['-issued_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='SupplierInvoiceLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('description', models.CharField(max_length=200, verbose_name='Désignation')),
                ('g_code', models.CharField(blank=True, max_length=80, verbose_name='G-CODE')),
                ('unit_price', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Prix unitaire (FCFA)')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Quantité')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='inventory.supplierinvoice')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
