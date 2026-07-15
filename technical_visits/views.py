from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TechnicalVisitForm
from .models import TechnicalVisit


@login_required
def visit_list(request):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')

    qs = TechnicalVisit.objects.for_garage(garage).select_related('vehicle', 'vehicle__client')

    today = date.today()
    status_filter = request.GET.get('status', '')
    vehicle_filter = request.GET.get('vehicle', '')
    result_filter = request.GET.get('result', '')

    if status_filter == 'expired':
        qs = qs.filter(expiry_date__lt=today)
    elif status_filter == 'expiring':
        qs = qs.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30))
    elif status_filter == 'valid':
        qs = qs.filter(expiry_date__gt=today + timedelta(days=30))

    if vehicle_filter:
        qs = qs.filter(vehicle_id=vehicle_filter)
    if result_filter:
        qs = qs.filter(result=result_filter)

    from clients.models import Vehicle
    vehicles = Vehicle.objects.for_garage(garage).order_by('plate_number')

    return render(request, 'technical_visits/list.html', {
        'visits': qs,
        'status_filter': status_filter,
        'vehicle_filter': vehicle_filter,
        'result_filter': result_filter,
        'vehicles': vehicles,
        'result_choices': TechnicalVisit.RESULT_CHOICES,
    })


@login_required
def visit_detail(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    visit = get_object_or_404(TechnicalVisit, pk=pk, garage=garage)
    return render(request, 'technical_visits/detail.html', {'visit': visit})


@login_required
def visit_create(request):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')

    vehicle_pk = request.GET.get('vehicle')
    initial = {}
    if vehicle_pk:
        initial['vehicle'] = vehicle_pk

    if request.method == 'POST':
        form = TechnicalVisitForm(request.POST, request.FILES, garage=garage)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.garage = garage
            visit.created_by = request.user
            visit.save()
            messages.success(request, 'Visite technique enregistrée.')
            return redirect('visit_detail', pk=visit.pk)
    else:
        form = TechnicalVisitForm(initial=initial, garage=garage)

    return render(request, 'technical_visits/form.html', {'form': form, 'action': 'Ajouter'})


@login_required
def visit_update(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    visit = get_object_or_404(TechnicalVisit, pk=pk, garage=garage)

    if request.method == 'POST':
        form = TechnicalVisitForm(request.POST, request.FILES, instance=visit, garage=garage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Visite technique mise à jour.')
            return redirect('visit_detail', pk=visit.pk)
    else:
        form = TechnicalVisitForm(instance=visit, garage=garage)

    return render(request, 'technical_visits/form.html', {'form': form, 'visit': visit, 'action': 'Modifier'})


@login_required
def visit_delete(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    visit = get_object_or_404(TechnicalVisit, pk=pk, garage=garage)
    if request.method == 'POST':
        visit.delete()
        messages.success(request, 'Visite technique supprimée.')
        return redirect('visit_list')
    return render(request, 'technical_visits/confirm_delete.html', {'visit': visit})
