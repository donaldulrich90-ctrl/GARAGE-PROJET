from django.apps import AppConfig


class WorkshopsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workshops'
    verbose_name = 'Sections atelier'

    def ready(self):
        from django.db.models.signals import post_save

        def _create_default_sections(sender, instance, created, **kwargs):
            if not created:
                return
            from workshops.models import WorkshopSection, DEFAULT_SECTIONS
            for code, name, color, icon, order in DEFAULT_SECTIONS:
                WorkshopSection.objects.get_or_create(
                    garage=instance,
                    code=code,
                    defaults={
                        'name': name,
                        'color': color,
                        'icon': icon,
                        'display_order': order,
                    },
                )

        from tenants.models import Garage
        post_save.connect(_create_default_sections, sender=Garage, weak=False)
