import hashlib
import hmac
import json as json_module

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from clients.models import Client

from .models import WhatsAppLog
from .services import _api_configured, build_wame_url, send_whatsapp_api


@login_required
@require_POST
def log_and_redirect(request, client_pk):
    """Enregistre l'envoi WhatsApp : via API Cloud si configurée, sinon retourne l'URL wa.me."""
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

    if _api_configured():
        success, result = send_whatsapp_api(phone, body)
        WhatsAppLog.objects.create(
            garage=garage,
            client=client,
            phone=phone,
            body=body,
            source=WhatsAppLog.SRC_INDIVIDUAL,
            direction=WhatsAppLog.DIRECTION_OUT,
            status=WhatsAppLog.STATUS_SENT if success else WhatsAppLog.STATUS_FAILED,
            wa_message_id=result if success else '',
            error='' if success else result,
        )
        if success:
            return JsonResponse({'sent': True})
        return JsonResponse({'error': f"Erreur envoi WhatsApp : {result}"}, status=500)

    # Fallback wa.me
    WhatsAppLog.objects.create(
        garage=garage,
        client=client,
        phone=phone,
        body=body,
        source=WhatsAppLog.SRC_INDIVIDUAL,
        direction=WhatsAppLog.DIRECTION_OUT,
    )
    return JsonResponse({'url': build_wame_url(phone, body)})


@csrf_exempt
def whatsapp_webhook(request):
    """
    Webhook Meta WhatsApp Cloud — accessible sans authentification, CSRF exempt.
    GET  : vérification du webhook (hub.verify_token).
    POST : réception des messages entrants (signature HMAC vérifiée).
    """
    if request.method == 'GET':
        verify_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', '')
        hub_token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')
        if verify_token and hub_token == verify_token:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse('Forbidden', status=403)

    if request.method == 'POST':
        app_secret = getattr(settings, 'WHATSAPP_APP_SECRET', '')
        if app_secret:
            sig_header = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
            expected = 'sha256=' + hmac.new(
                app_secret.encode(),
                request.body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(sig_header, expected):
                return HttpResponse('', status=200)

        try:
            payload = json_module.loads(request.body)
        except Exception:
            return HttpResponse('', status=200)

        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                for msg in value.get('messages', []):
                    msg_id = msg.get('id', '')
                    from_number = msg.get('from', '')
                    text = msg.get('text', {}).get('body', '')

                    if not from_number:
                        continue

                    if msg_id and WhatsAppLog.objects.filter(wa_message_id=msg_id).exists():
                        continue

                    # Rapprochement client par les 8 derniers chiffres du numéro
                    suffix = from_number[-8:]
                    client = Client.objects.filter(
                        Q(phone__endswith=suffix) | Q(whatsapp_number__endswith=suffix)
                    ).select_related('garage').first()

                    if client is None:
                        continue

                    WhatsAppLog.objects.create(
                        garage=client.garage,
                        client=client,
                        phone=from_number,
                        body=text,
                        direction=WhatsAppLog.DIRECTION_IN,
                        source=WhatsAppLog.SRC_INDIVIDUAL,
                        status=WhatsAppLog.STATUS_SENT,
                        wa_message_id=msg_id,
                    )

        return HttpResponse('', status=200)

    return HttpResponse('', status=405)


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
    """Historique de tous les messages WhatsApp (sortants + entrants)."""
    garage = request.user.garage
    if not garage:
        return redirect('dashboard_home')

    qs = WhatsAppLog.objects.for_garage(garage).select_related('client', 'template')

    status_filter = request.GET.get('status', '')
    source_filter = request.GET.get('source', '')
    direction_filter = request.GET.get('direction', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if source_filter:
        qs = qs.filter(source=source_filter)
    if direction_filter:
        qs = qs.filter(direction=direction_filter)

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))

    total = qs.count()
    outgoing = qs.filter(direction=WhatsAppLog.DIRECTION_OUT).count()
    incoming = qs.filter(direction=WhatsAppLog.DIRECTION_IN).count()
    sent = qs.filter(status=WhatsAppLog.STATUS_SENT).count()

    return render(request, 'messaging/history.html', {
        'page_obj': page,
        'status_filter': status_filter,
        'source_filter': source_filter,
        'direction_filter': direction_filter,
        'status_choices': WhatsAppLog.STATUS_CHOICES,
        'source_choices': WhatsAppLog.SRC_CHOICES,
        'direction_choices': WhatsAppLog.DIRECTION_CHOICES,
        'total': total,
        'outgoing': outgoing,
        'incoming': incoming,
        'sent': sent,
        'failed': total - sent,
    })
