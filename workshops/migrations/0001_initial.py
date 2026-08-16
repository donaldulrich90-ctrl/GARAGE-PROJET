import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkshopSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100, verbose_name='Nom')),
                ('code', models.SlugField(max_length=50, verbose_name='Code')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('icon', models.CharField(blank=True, max_length=10, verbose_name='Icône')),
                ('color', models.CharField(default='#6B7280', max_length=10, verbose_name='Couleur graphique')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('display_order', models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")),
                ('garage', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='workshopsections',
                    to='tenants.garage',
                )),
            ],
            options={
                'verbose_name': 'Section atelier',
                'verbose_name_plural': 'Sections atelier',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.AddConstraint(
            model_name='workshopsection',
            constraint=models.UniqueConstraint(
                fields=['garage', 'code'],
                name='unique_section_code_per_garage',
            ),
        ),
    ]
