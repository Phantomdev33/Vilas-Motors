from django.utils import timezone
from .models import Alert, AuditLog

LABELS = {'operational': 'Operativo', 'upcoming': 'Próximo a mantención', 'required': 'Mantención requerida', 'overdue': 'Mantención vencida'}

def audit(user, action, instance, description=''):
    AuditLog.objects.create(user=user, action=action, entity=instance.__class__.__name__, entity_id=str(instance.pk), description=description)

def reconcile_alert(equipment, user=None, maintenance=None):
    current = Alert.objects.filter(equipment=equipment, active=True).first()
    if equipment.status == 'operational' or not equipment.active:
        if current:
            current.active = False
            current.attended_at = timezone.now()
            current.maintenance = maintenance
            current.save()
            audit(user, 'alert_attended', current)
    else:
        message = f'{equipment.code}: {LABELS[equipment.status]}. Próxima mantención: {equipment.next_service:,.0f} {equipment.unit}.'
        if current:
            if current.severity != equipment.status or current.message != message:
                current.severity, current.message = equipment.status, message
                current.save()
                audit(user, 'alert_updated', current)
        else:
            alert = Alert.objects.create(equipment=equipment, severity=equipment.status, message=message)
            audit(user, 'alert_created', alert)
