import logging

from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger('django.security.csrf')

def enforce_csrf(request):
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        logger.warning('Petición rechazada por CSRF: %s', reason)
        if reason.startswith(('Origin checking failed', 'Referer checking failed')):
            message = (
                'El dominio de esta página no está autorizado para iniciar sesión. '
                'Usa la URL principal del sitio o configura su origen en CSRF_TRUSTED_ORIGINS.'
            )
        elif reason == 'CSRF cookie not set.':
            message = (
                'No se recibió la cookie de seguridad. Permite las cookies de este sitio '
                'y recarga la página.'
            )
        else:
            message = 'El token de seguridad no coincide con la sesión. Recarga la página e intenta nuevamente.'
        raise PermissionDenied(message)

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get('access_token')
        if not token: return None
        validated = self.get_validated_token(token)
        user = self.get_user(validated)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            enforce_csrf(request)
        return user, validated
