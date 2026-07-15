from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from clients.models import Client

from .models import WhatsAppLog
from .services import build_wame_url


@login_required
@require_POST
def log_and_redirect(request, client_pk):
    """Enregistre l'intention d'envoi WhatsApp et retourne l'URL wa.me."""
    garage = request.user.garage
    if not garage:
        return JsonResponse({'error': 'Aucun garage associé'}, status=403)

    client = get_object_or_404(Client.objects.for_garage(garage), pk=client_pk)
    body = request.POST.get('body', '').strip()

    if not body:
        return JsonResponse({'error': 'Message vide'}, status=400)

    phone = client.whatsapp_number or client.phone
    if not phone:
        return JsonResponse({'error': "Ce client n'a pas de numéro de téléphone"}, status=400)

    WhatsAppLog.objects.create(
        garage=garage,
        client=client,
        phone=phone,
        body=body,
        source=WhatsAppLog.SRC_INDIVIDUAL,
    )

    return JsonResponse({'url': build_wame_url(phone, body)})


@login_required
def broadcast(request):
    """Composition et envoi de messages en masse (Phase 3)."""
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    return render(request, 'messaging/broadcast.html', {})


@login_required
def templates_list(request):
    """Gestion des templates de messages (Phase 2)."""
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')
    return render(request, 'messaging/templates_list.html', {})


@login_required
def history(request):
    """Historique de tous les messages WhatsApp envoyés."""
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')

    qs = WhatsAppLog.objects.for_garage(garage).select_related('client', 'template')

    status_filter = request.GET.get('status', '')
    source_filter = request.GET.get('source', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if source_filter:
        qs = qs.filter(source=source_filter)

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))

    total = qs.count()
    sent = qs.filter(status=WhatsAppLog.STATUS_SENT).count()

    return render(request, 'messaging/history.html', {
        'page_obj': page,
        'status_filter': status_filter,
        'source_filter': source_filter,
        'status_choices': WhatsAppLog.STATUS_CHOICES,
        'source_choices': WhatsAppLog.SRC_CHOICES,
        'total': total,
        'sent': sent,
        'failed': total - sent,
    })
