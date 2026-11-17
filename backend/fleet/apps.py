from django.apps import AppConfig
from django.contrib.admin import apps as admin_apps


class FleetAdminConfig(admin_apps.AdminConfig):
    default = False
    default_site = 'fleet.admin_site.SMSAdminSite'


class FleetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fleet'
