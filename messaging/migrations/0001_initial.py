from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants', '0003_ifu_rccm_signature_cachet'),
        ('clients', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100, verbose_name='Nom')),
                ('body', models.TextField(verbose_name='Contenu')),
                ('source', models.CharField(
                    choices=[('system', 'Système'), ('custom', 'Personnalisé')],
                    default='custom',
                    max_length=10,
                )),
                ('garage', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)ss',
                    to='tenants.garage',
                )),
            ],
            options={
                'verbose_name': 'Template message',
                'verbose_name_plural': 'Templates messages',
                'ordering': ['source', 'name'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='BroadcastCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(blank=True, max_length=150, verbose_name='Nom de la campagne')),
                ('body', models.TextField(verbose_name='Message')),
                ('filter_type', models.CharField(
                    choices=[
                        ('all', 'Tous les clients'),
                        ('insurance', 'Assurance expirant ce mois'),
                        ('vt', 'Visite technique expirant ce mois'),
                        ('inactive', 'Clients sans visite depuis X mois'),
                        ('manual', 'Sélection manuelle'),
                    ],
                    default='all',
                    max_length=20,
                )),
                ('filter_value', models.CharField(
                    blank=True,
                    help_text='Nombre de mois pour le filtre "clients inactifs"',
                    max_length=50,
                )),
                ('status', models.CharField(
                    choices=[('draft', 'Brouillon'), ('sent', 'Envoyé')],
                    default='draft',
                    max_length=10,
                )),
                ('sent_count', models.PositiveIntegerField(default=0)),
                ('garage', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)ss',
                    to='tenants.garage',
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='broadcast_campaigns',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('recipients', models.ManyToManyField(
                    blank=True,
                    related_name='broadcast_campaigns',
                    to='clients.client',
                )),
            ],
            options={
                'verbose_name': 'Campagne broadcast',
                'verbose_name_plural': 'Campagnes broadcast',
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WhatsAppLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('phone', models.CharField(max_length=30, verbose_name='Téléphone')),
                ('body', models.TextField(verbose_name='Message')),
                ('status', models.CharField(
                    choices=[('sent', 'Envoyé'), ('failed', 'Échoué')],
                    default='sent',
                    max_length=10,
                )),
                ('source', models.CharField(
                    choices=[('individual', 'Individuel'), ('broadcast', 'Broadcast'), ('auto', 'Automatique')],
                    default='individual',
                    max_length=20,
                )),
                ('error', models.TextField(blank=True)),
                ('garage', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)ss',
                    to='tenants.garage',
                )),
                ('client', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='whatsapp_logs',
                    to='clients.client',
                )),
                ('campaign', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='logs',
                    to='messaging.broadcastcampaign',
                )),
                ('template', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='logs',
                    to='messaging.messagetemplate',
                )),
            ],
            options={
                'verbose_name': 'Message WhatsApp',
                'verbose_name_plural': 'Messages WhatsApp',
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
    ]
