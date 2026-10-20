from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

def enforce_csrf(request):
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied('Token CSRF inválido. Recarga la página.')

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get('access_token')
        if not token: return None
        validated = self.get_validated_token(token)
        user = self.get_user(validated)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            enforce_csrf(request)
        return user, validated
