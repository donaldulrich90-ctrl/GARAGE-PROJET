from django.db import migrations

DEFAULT_SECTIONS = [
    ('MECANIQUE', 'Mécanique', '#3B82F6', '🔧', 1),
    ('ELECTRICITE', 'Électricité automobile', '#F59E0B', '⚡', 2),
    ('CLIMATISATION', 'Froid & Climatisation', '#06B6D4', '❄️', 3),
    ('TOLERIE_PEINTURE', 'Tôlerie & Peinture', '#8B5CF6', '🎨', 4),
]


def create_default_sections(apps, schema_editor):
    Garage = apps.get_model('tenants', 'Garage')
    WorkshopSection = apps.get_model('workshops', 'WorkshopSection')

    for garage in Garage.objects.all():
        for code, name, color, icon, order in DEFAULT_SECTIONS:
            WorkshopSection.objects.get_or_create(
                garage=garage,
                code=code,
                defaults={
                    'name': name,
                    'color': color,
                    'icon': icon,
                    'display_order': order,
                },
            )


def remove_default_sections(apps, schema_editor):
    WorkshopSection = apps.get_model('workshops', 'WorkshopSection')
    codes = [s[0] for s in DEFAULT_SECTIONS]
    WorkshopSection.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_sections, remove_default_sections),
    ]
