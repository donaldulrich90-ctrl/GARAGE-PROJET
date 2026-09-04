# Rend Supplier et SupplierPart indépendants du garage (marketplace global).
# Aucune ligne fournisseur/offre n'est supprimée : seule la colonne garage_id
# (le rattachement à un garage) est retirée. Chaque fournisseur existant devient
# un fournisseur indépendant de la plateforme.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0008_supplierinvoice_supplierinvoiceline'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='supplierpart',
            name='unique_supplier_part_per_garage',
        ),
        migrations.RemoveField(
            model_name='supplier',
            name='garage',
        ),
        migrations.RemoveField(
            model_name='supplierpart',
            name='garage',
        ),
        migrations.AddConstraint(
            model_name='supplierpart',
            constraint=models.UniqueConstraint(
                fields=['supplier', 'catalog_part'],
                name='unique_supplier_part_per_supplier',
            ),
        ),
    ]
