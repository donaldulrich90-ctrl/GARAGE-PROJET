import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repair_orders', '0001_initial'),
        ('workshops', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='repairordertask',
            name='section',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tasks',
                to='workshops.workshopsection',
                verbose_name='Section atelier',
            ),
        ),
        migrations.AddField(
            model_name='repairorderpart',
            name='section',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='parts_used',
                to='workshops.workshopsection',
                verbose_name='Section atelier',
            ),
        ),
    ]
