from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Equipment, Reading, Maintenance, Supply, MaintenanceSupply, Alert, Sensor, Gateway, AuditLog
@admin.register(User)
class FleetUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Vila’s Motor', {'fields': ('role', 'region', 'failed_attempts', 'locked_until')}),)
for model in (Equipment, Reading, Maintenance, Supply, MaintenanceSupply, Alert, Sensor, Gateway): admin.site.register(model)
@admin.register(AuditLog)
class AuditAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'entity', 'entity_id')
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
