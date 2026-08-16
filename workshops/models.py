from django.db import models

from core.models import TenantModel


DEFAULT_SECTIONS = [
    ('MECANIQUE', 'Mécanique', '#3B82F6', '🔧', 1),
    ('ELECTRICITE', 'Électricité automobile', '#F59E0B', '⚡', 2),
    ('CLIMATISATION', 'Froid & Climatisation', '#06B6D4', '❄️', 3),
    ('TOLERIE_PEINTURE', 'Tôlerie & Peinture', '#8B5CF6', '🎨', 4),
]


class WorkshopSection(TenantModel):
    name = models.CharField('Nom', max_length=100)
    code = models.SlugField('Code', max_length=50)
    description = models.TextField('Description', blank=True)
    icon = models.CharField('Icône', max_length=10, blank=True)
    color = models.CharField('Couleur graphique', max_length=10, default='#6B7280')
    is_active = models.BooleanField('Active', default=True)
    display_order = models.PositiveSmallIntegerField("Ordre d'affichage", default=0)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Section atelier'
        verbose_name_plural = 'Sections atelier'
        constraints = [
            models.UniqueConstraint(
                fields=['garage', 'code'],
                name='unique_section_code_per_garage',
            )
        ]

    def __str__(self):
        return self.name
