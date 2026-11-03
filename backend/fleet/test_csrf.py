from django.middleware.csrf import get_token
from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from .authentication import enforce_csrf


@override_settings(
    ALLOWED_HOSTS=['backend.example.com'],
    CSRF_TRUSTED_ORIGINS=['https://frontend.example.com'],
)
class CSRFProxyTests(SimpleTestCase):
    def request(self, origin='https://frontend.example.com', cookie=True, valid_token=True):
        factory = RequestFactory()
        source = factory.get('/')
        token = get_token(source)
        request = factory.post(
            '/api/auth/login/', secure=True,
            HTTP_HOST='backend.example.com', HTTP_ORIGIN=origin,
            HTTP_X_CSRFTOKEN=token if valid_token else 'x' * 32,
        )
        if cookie:
            request.COOKIES['csrftoken'] = source.META['CSRF_COOKIE']
        return request

    def test_trusted_frontend_can_send_matching_cookie_and_token(self):
        enforce_csrf(self.request())

    def test_preview_domain_requires_explicit_trust(self):
        with self.assertRaisesRegex(PermissionDenied, 'dominio'):
            enforce_csrf(self.request(origin='https://preview.example.com'))

    def test_missing_cookie_is_distinguished(self):
        with self.assertRaisesRegex(PermissionDenied, 'cookie'):
            enforce_csrf(self.request(cookie=False))

    def test_mismatched_token_is_rejected(self):
        with self.assertRaisesRegex(PermissionDenied, 'no coincide'):
            enforce_csrf(self.request(valid_token=False))
