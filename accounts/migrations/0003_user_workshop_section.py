import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_supplier_alter_user_garage_alter_user_id_and_more'),
        ('workshops', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='workshop_section',
            field=models.ForeignKey(
                blank=True,
                help_text='Section à laquelle ce technicien est rattaché (facultatif).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_users',
                to='workshops.workshopsection',
                verbose_name='Section atelier',
            ),
        ),
    ]
