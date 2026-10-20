import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        PLANNER = 'planner', 'Planificador'
        HELPER = 'helper', 'Ayudante'
        CHIEF = 'chief', 'Jefe de operaciones'
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.HELPER)
    region = models.CharField(max_length=100, default='Norte')
    failed_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

class Equipment(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    equipment_type = models.CharField(max_length=80)
    brand = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    serial_number = models.CharField(max_length=100, unique=True)
    region = models.CharField(max_length=100)
    commune = models.CharField(max_length=100)
    location = models.CharField(max_length=120, blank=True)
    responsible = models.CharField(max_length=120, blank=True)
    unit = models.CharField(max_length=4, choices=[('hrs', 'Horas'), ('km', 'Kilómetros')], default='hrs')
    interval = models.PositiveIntegerField(default=250)
    initial_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    initial_service_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='equipment/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['code']
        constraints = [models.CheckConstraint(condition=Q(interval__gt=0), name='positive_interval'),
            models.CheckConstraint(condition=Q(initial_value__gte=0), name='positive_initial_value'),
            models.CheckConstraint(condition=Q(initial_service_value__gte=0), name='positive_service_value')]
    @cached_property
    def current_value(self):
        if hasattr(self, '_current_value'): return self._current_value
        latest = self.readings.order_by('-recorded_at', '-id').first()
        return latest.value if latest else self.initial_value
    @cached_property
    def last_service_value(self):
        if hasattr(self, '_last_service_value'): return self._last_service_value
        latest = self.maintenances.filter(status='completed').order_by('-value', '-id').first()
        return latest.value if latest else self.initial_service_value
    @cached_property
    def next_service(self):
        return self.last_service_value + self.interval
    @cached_property
    def remaining(self):
        return self.next_service - self.current_value
    @cached_property
    def progress(self):
        return max(0, round(float((self.current_value-self.last_service_value) / self.interval * 100)))
    @cached_property
    def status(self):
        if self.remaining < 0: return 'overdue'
        if self.remaining == 0: return 'required'
        if self.remaining <= Decimal(self.interval) * Decimal('0.15'): return 'upcoming'
        return 'operational'

class Gateway(models.Model):
    identifier = models.CharField(max_length=64, unique=True)
    model = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    last_connection = models.DateTimeField(null=True)

class Sensor(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name='sensors')
    gateway = models.ForeignKey(Gateway, on_delete=models.PROTECT, null=True, blank=True)
    identifier = models.CharField(max_length=64, unique=True)
    sensor_type = models.CharField(max_length=80, default='Cámara OCR')
    model = models.CharField(max_length=100, default='Raspberry Pi Zero 2 W')
    active = models.BooleanField(default=True)
    token_hash = models.CharField(max_length=128)

class Reading(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name='readings')
    sensor = models.ForeignKey(Sensor, on_delete=models.PROTECT, null=True, blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    source = models.CharField(max_length=16, choices=[('manual', 'Manual'), ('ocr', 'OCR por foto'), ('sensor', 'Sensor')], default='manual')
    evidence = models.ImageField(upload_to='readings/%Y/%m/', blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    note = models.TextField(blank=True)
    client_id = models.UUIDField(default=uuid.uuid4, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='readings')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-recorded_at', '-id']
        constraints = [models.CheckConstraint(condition=Q(value__gte=0), name='positive_reading')]

class Maintenance(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name='maintenances')
    service_type = models.CharField(max_length=120, default='Preventiva · Servicio de motor')
    interval = models.PositiveIntegerField(default=250)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    scheduled_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=[('draft', 'Borrador'), ('scheduled', 'Programada'), ('completed', 'Completada'), ('cancelled', 'Cancelada')], default='scheduled')
    workshop = models.CharField(max_length=120)
    work_order = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-scheduled_at']
        constraints = [models.CheckConstraint(condition=Q(value__gte=0), name='positive_maintenance'),
            models.CheckConstraint(condition=Q(interval__gt=0), name='positive_maintenance_interval')]

class Supply(models.Model):
    code = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=120)
    unit = models.CharField(max_length=32)
    active = models.BooleanField(default=True)

class MaintenanceSupply(models.Model):
    maintenance = models.ForeignKey(Maintenance, on_delete=models.CASCADE, related_name='supplies')
    supply = models.ForeignKey(Supply, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['maintenance', 'supply'], name='unique_maintenance_supply'),
                      models.CheckConstraint(condition=Q(quantity__gt=0), name='positive_supply_quantity')]

class Alert(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name='alerts')
    maintenance = models.ForeignKey(Maintenance, on_delete=models.PROTECT, null=True, blank=True)
    severity = models.CharField(max_length=16)
    message = models.TextField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attended_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-active', '-created_at']
        constraints = [models.UniqueConstraint(fields=['equipment'], condition=Q(active=True), name='one_active_alert_per_equipment')]

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=64)
    entity = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']

