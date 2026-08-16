import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing', '0002_proformainvoice'),
        ('workshops', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='total_snapshot',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Total figé au moment de la création de la facture, pour reporting par section.',
                max_digits=12,
                null=True,
                verbose_name='Total figé',
            ),
        ),
        migrations.CreateModel(
            name='InvoiceSectionBreakdown',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('labor_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="Main d'œuvre")),
                ('parts_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Pièces')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Total section')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='section_breakdowns', to='invoicing.invoice')),
                ('section', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='invoice_breakdowns',
                    to='workshops.workshopsection',
                    verbose_name='Section',
                )),
            ],
            options={
                'verbose_name': 'Répartition facture/section',
                'verbose_name_plural': 'Répartitions facture/section',
            },
        ),
        migrations.CreateModel(
            name='PaymentSectionAllocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Montant alloué')),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='section_allocations', to='invoicing.payment')),
                ('section', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='payment_allocations',
                    to='workshops.workshopsection',
                    verbose_name='Section',
                )),
            ],
            options={
                'verbose_name': 'Allocation paiement/section',
                'verbose_name_plural': 'Allocations paiement/section',
            },
        ),
    ]
