import threading

_thread_locals = threading.local()


def get_current_user():
    return getattr(_thread_locals, "user", None)


def get_current_request():
    return getattr(_thread_locals, "request", None)


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, "user", None)
        _thread_locals.request = request
        try:
            return self.get_response(request)
        finally:
            # Nettoyer le thread-local en fin de requête : évite qu'un utilisateur
            # (ou une requête) ne « fuite » sur la requête suivante servie par le
            # même thread — ce qui fausserait l'attribution des entrées d'audit.
            _thread_locals.user = None
            _thread_locals.request = None
