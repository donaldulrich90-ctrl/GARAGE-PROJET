from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import VehicleTaxForm
from .models import VehicleTax


@login_required
def tax_list(request):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')

    qs = VehicleTax.objects.for_garage(garage).select_related('vehicle', 'vehicle__client')

    today = date.today()
    status_filter = request.GET.get('status', '')
    vehicle_filter = request.GET.get('vehicle', '')
    year_filter = request.GET.get('year', '')

    if status_filter == 'paid':
        qs = qs.filter(is_paid=True)
    elif status_filter == 'overdue':
        qs = qs.filter(is_paid=False, due_date__lt=today)
    elif status_filter == 'pending':
        qs = qs.filter(is_paid=False, due_date__gte=today)

    if vehicle_filter:
        qs = qs.filter(vehicle_id=vehicle_filter)
    if year_filter:
        qs = qs.filter(fiscal_year=year_filter)

    all_qs = VehicleTax.objects.for_garage(garage)
    stats = {
        'total': all_qs.count(),
        'paid': all_qs.filter(is_paid=True).count(),
        'overdue': all_qs.filter(is_paid=False, due_date__lt=today).count(),
        'pending': all_qs.filter(is_paid=False, due_date__gte=today).count(),
        'total_due': all_qs.filter(is_paid=False).aggregate(s=Sum('amount'))['s'] or 0,
    }

    from clients.models import Vehicle
    vehicles = Vehicle.objects.for_garage(garage).order_by('plate_number')

    years = all_qs.values_list('fiscal_year', flat=True).distinct().order_by('-fiscal_year')

    return render(request, 'taxes/list.html', {
        'taxes': qs,
        'stats': stats,
        'status_filter': status_filter,
        'vehicle_filter': vehicle_filter,
        'year_filter': year_filter,
        'vehicles': vehicles,
        'years': years,
    })


@login_required
def tax_detail(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    tax = get_object_or_404(VehicleTax, pk=pk, garage=garage)
    return render(request, 'taxes/detail.html', {'tax': tax})


@login_required
def tax_create(request):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')

    vehicle_pk = request.GET.get('vehicle')
    initial = {'fiscal_year': date.today().year}
    if vehicle_pk:
        initial['vehicle'] = vehicle_pk

    if request.method == 'POST':
        form = VehicleTaxForm(request.POST, request.FILES, garage=garage)
        if form.is_valid():
            tax = form.save(commit=False)
            tax.garage = garage
            tax.save()
            messages.success(request, 'Taxe enregistrée.')
            return redirect('taxes:tax_detail', pk=tax.pk)
    else:
        form = VehicleTaxForm(initial=initial, garage=garage)

    return render(request, 'taxes/form.html', {'form': form, 'action': 'Ajouter'})


@login_required
def tax_update(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    tax = get_object_or_404(VehicleTax, pk=pk, garage=garage)

    if request.method == 'POST':
        form = VehicleTaxForm(request.POST, request.FILES, instance=tax, garage=garage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Taxe mise à jour.')
            return redirect('taxes:tax_detail', pk=tax.pk)
    else:
        form = VehicleTaxForm(instance=tax, garage=garage)

    return render(request, 'taxes/form.html', {'form': form, 'tax': tax, 'action': 'Modifier'})


@login_required
def tax_delete(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    tax = get_object_or_404(VehicleTax, pk=pk, garage=garage)
    if request.method == 'POST':
        tax.delete()
        messages.success(request, 'Taxe supprimée.')
        return redirect('taxes:tax_list')
    return render(request, 'taxes/confirm_delete.html', {'tax': tax})


@login_required
@require_POST
def tax_mark_paid(request, pk):
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    tax = get_object_or_404(VehicleTax, pk=pk, garage=garage)
    tax.is_paid = True
    tax.payment_date = date.today()
    tax.save(update_fields=['is_paid', 'payment_date'])
    messages.success(request, 'Taxe marquée comme payée.')
    return redirect('taxes:tax_detail', pk=tax.pk)
