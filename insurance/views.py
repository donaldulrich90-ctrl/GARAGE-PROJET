from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InsuranceClaimForm, InsuranceForm
from .models import Insurance, InsuranceClaim


@login_required
def insurance_list(request):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')

    qs = Insurance.objects.for_garage(garage).select_related('vehicle', 'vehicle__client')

    today = date.today()
    status_filter = request.GET.get('status', '')
    vehicle_filter = request.GET.get('vehicle', '')
    company_filter = request.GET.get('company', '').strip()

    if status_filter == 'expired':
        qs = qs.filter(end_date__lt=today)
    elif status_filter == 'expiring':
        qs = qs.filter(end_date__gte=today, end_date__lte=today + timedelta(days=30))
    elif status_filter == 'active':
        qs = qs.filter(start_date__lte=today, end_date__gte=today)

    if vehicle_filter:
        qs = qs.filter(vehicle_id=vehicle_filter)
    if company_filter:
        qs = qs.filter(insurance_company__icontains=company_filter)

    from clients.models import Vehicle
    vehicles = Vehicle.objects.for_garage(garage).order_by('plate_number')

    return render(request, 'insurance/list.html', {
        'insurances': qs,
        'status_filter': status_filter,
        'vehicle_filter': vehicle_filter,
        'company_filter': company_filter,
        'vehicles': vehicles,
    })


@login_required
def insurance_detail(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    insurance = get_object_or_404(Insurance, pk=pk, garage=garage)
    claims = insurance.claims.all()
    return render(request, 'insurance/detail.html', {'insurance': insurance, 'claims': claims})


@login_required
def insurance_create(request):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')

    vehicle_pk = request.GET.get('vehicle')
    initial = {}
    if vehicle_pk:
        initial['vehicle'] = vehicle_pk

    if request.method == 'POST':
        form = InsuranceForm(request.POST, request.FILES, garage=garage)
        if form.is_valid():
            insurance = form.save(commit=False)
            insurance.garage = garage
            insurance.created_by = request.user
            insurance.save()
            messages.success(request, 'Police d\'assurance enregistrée.')
            return redirect('insurance_detail', pk=insurance.pk)
    else:
        form = InsuranceForm(initial=initial, garage=garage)

    return render(request, 'insurance/form.html', {'form': form, 'action': 'Ajouter'})


@login_required
def insurance_update(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    insurance = get_object_or_404(Insurance, pk=pk, garage=garage)

    if request.method == 'POST':
        form = InsuranceForm(request.POST, request.FILES, instance=insurance, garage=garage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Police d\'assurance mise à jour.')
            return redirect('insurance_detail', pk=insurance.pk)
    else:
        form = InsuranceForm(instance=insurance, garage=garage)

    return render(request, 'insurance/form.html', {'form': form, 'insurance': insurance, 'action': 'Modifier'})


@login_required
def insurance_delete(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    insurance = get_object_or_404(Insurance, pk=pk, garage=garage)
    if request.method == 'POST':
        insurance.delete()
        messages.success(request, 'Police d\'assurance supprimée.')
        return redirect('insurance_list')
    return render(request, 'insurance/confirm_delete.html', {'insurance': insurance})


@login_required
def claim_list(request):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    claims = InsuranceClaim.objects.for_garage(garage).select_related(
        'insurance', 'insurance__vehicle',
    )
    return render(request, 'insurance/claims/list.html', {'claims': claims})


@login_required
def claim_create(request, insurance_pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    insurance = get_object_or_404(Insurance, pk=insurance_pk, garage=garage)

    if request.method == 'POST':
        form = InsuranceClaimForm(request.POST, request.FILES, garage=garage)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.garage = garage
            claim.insurance = insurance
            claim.save()
            messages.success(request, 'Sinistre déclaré.')
            return redirect('claim_detail', pk=claim.pk)
    else:
        form = InsuranceClaimForm(garage=garage)

    return render(request, 'insurance/claims/form.html', {
        'form': form, 'insurance': insurance, 'action': 'Déclarer',
    })


@login_required
def claim_detail(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    claim = get_object_or_404(InsuranceClaim, pk=pk, garage=garage)
    return render(request, 'insurance/claims/detail.html', {'claim': claim})


@login_required
def claim_update(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    claim = get_object_or_404(InsuranceClaim, pk=pk, garage=garage)

    if request.method == 'POST':
        form = InsuranceClaimForm(request.POST, request.FILES, instance=claim, garage=garage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sinistre mis à jour.')
            return redirect('claim_detail', pk=claim.pk)
    else:
        form = InsuranceClaimForm(instance=claim, garage=garage)

    return render(request, 'insurance/claims/form.html', {
        'form': form, 'claim': claim, 'insurance': claim.insurance, 'action': 'Modifier',
    })
