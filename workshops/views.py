from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from core.views import GarageAdminRequiredMixin

from .forms import WorkshopSectionForm
from .models import WorkshopSection


class SectionListView(GarageAdminRequiredMixin, ListView):
    model = WorkshopSection
    template_name = 'workshops/section_list.html'
    context_object_name = 'sections'

    def get_queryset(self):
        return WorkshopSection.objects.for_garage(self.garage).order_by('display_order', 'name')


class SectionCreateView(GarageAdminRequiredMixin, CreateView):
    model = WorkshopSection
    form_class = WorkshopSectionForm
    template_name = 'workshops/section_form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def form_valid(self, form):
        form.instance.garage = self.garage
        messages.success(self.request, f"Section « {form.instance.name} » créée.")
        return super().form_valid(form)

    def get_success_url(self):
        return '/ateliers/'


class SectionUpdateView(GarageAdminRequiredMixin, UpdateView):
    model = WorkshopSection
    form_class = WorkshopSectionForm
    template_name = 'workshops/section_form.html'

    def get_queryset(self):
        return WorkshopSection.objects.for_garage(self.garage)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['garage'] = self.garage
        return kw

    def form_valid(self, form):
        messages.success(self.request, f"Section « {form.instance.name} » mise à jour.")
        return super().form_valid(form)

    def get_success_url(self):
        return '/ateliers/'


class SectionToggleView(GarageAdminRequiredMixin, View):
    def post(self, request, pk):
        section = get_object_or_404(WorkshopSection.objects.for_garage(self.garage), pk=pk)
        section.is_active = not section.is_active
        section.save(update_fields=['is_active', 'updated_at'])
        status = 'activée' if section.is_active else 'désactivée'
        messages.success(request, f"Section « {section.name} » {status}.")
        return redirect('section_list')
