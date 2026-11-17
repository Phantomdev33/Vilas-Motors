from django.conf import settings
from django.contrib.admin import AdminSite
from django.http import HttpResponseRedirect
from rest_framework.exceptions import APIException

from .authentication import CookieJWTAuthentication


class SMSAdminSite(AdminSite):
    def has_permission(self, request):
        if not hasattr(request, '_fleet_admin_user'):
            authentication = CookieJWTAuthentication()
            token = request.COOKIES.get('access_token')
            request._fleet_admin_user = None
            if token:
                try:
                    request._fleet_admin_user = authentication.get_user(authentication.get_validated_token(token))
                except APIException:
                    pass
        user = request._fleet_admin_user
        if not user or user.role != 'admin' or not user.is_staff:
            return False
        request.user = user
        return True

    def login(self, request, extra_context=None):
        if self.has_permission(request):
            return HttpResponseRedirect('../')
        return HttpResponseRedirect(settings.FRONTEND_URL)

    def logout(self, request, extra_context=None):
        response = super().logout(request, extra_context)
        response.delete_cookie('access_token', samesite='Lax')
        return response
