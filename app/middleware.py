from django.contrib.sessions.models import Session
from django.utils import timezone
from django.urls import reverse

from .models import AccessLog


class AccessLogMiddleware:
    """
    Registra acesso real do usuário autenticado com o evento atual.
    Evita excesso de logs criando no máximo 1 registro por sessão
    a cada 5 minutos.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return response

        if request.path.startswith("/admin/"):
            return response

        if request.path.startswith("/static/") or request.path.startswith("/media/"):
            return response

        if not request.session.session_key:
            request.session.save()

        now = timezone.now()
        session_key = request.session.session_key
        event = getattr(user, "event_user", None)

        # Sem evento vinculado, não registra no dashboard de evento
        if not event:
            return response

        throttle_key = f"last_accesslog_event_{event.id}"
        last_access_value = request.session.get(throttle_key)

        should_create = True

        if last_access_value:
            try:
                last_dt = timezone.datetime.fromisoformat(last_access_value)
                if timezone.is_naive(last_dt):
                    last_dt = timezone.make_aware(last_dt, timezone.get_current_timezone())

                diff_seconds = (now - last_dt).total_seconds()
                if diff_seconds < 300:  # 5 min
                    should_create = False
            except Exception:
                should_create = True

        if should_create:
            session_obj = Session.objects.filter(session_key=session_key).first()
            ip = self._get_client_ip(request)

            AccessLog.objects.create(
                user=user,
                event=event,
                session=session_obj,
                ip_address=ip,
            )

            request.session[throttle_key] = now.isoformat()

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

# event filter persistence middleware
EVENT_FILTER_PARAM = 'e'
EVENT_FILTER_SESSION_KEY = 'selected_event_id'
 
class EventFilterPersistenceMiddleware:
 
    def __init__(self, get_response):
        self.get_response = get_response
 
    def __call__(self, request):
        # Partidas exigem uma seleção explícita, inclusive após limpar o evento.
        if request.path_info in (reverse('games'), reverse('matches_manage')):
            return self.get_response(request)
        if (
            request.method == 'GET'
            and request.user.is_authenticated
            and (request.user.is_staff or getattr(request.user, 'type', None) == 0)
        ):
            e = request.GET.get(EVENT_FILTER_PARAM)
            if e:
                request.session[EVENT_FILTER_SESSION_KEY] = e
            else:
                saved = request.session.get(EVENT_FILTER_SESSION_KEY)
                if saved:
                    mutable_get = request.GET.copy()
                    mutable_get[EVENT_FILTER_PARAM] = saved
                    request.GET = mutable_get
 
        return self.get_response(request)