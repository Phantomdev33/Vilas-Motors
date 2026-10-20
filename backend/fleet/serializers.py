from decimal import Decimal
import uuid
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from .models import User, Equipment, Reading, Maintenance, Supply, MaintenanceSupply, Alert, Sensor, AuditLog
from .services import LABELS

def validate_image(value):
    if value and value.size > 10 * 1024 * 1024:
        raise serializers.ValidationError('La imagen no puede superar 10 MB.')
    return value

class UserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source='get_role_display', read_only=True)
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'role_label', 'region', 'is_active', 'last_login', 'password']
        read_only_fields = ['last_login']
    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exclude(pk=getattr(self.instance, 'pk', None)).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value
    def validate(self, attrs):
        password = attrs.get('password')
        if not self.instance and not password:
            raise serializers.ValidationError({'password': 'Ingresa una contraseña inicial.'})
        if password:
            try: validate_password(password, self.instance or User(email=attrs.get('email', ''), first_name=attrs.get('first_name', '')))
            except DjangoValidationError as exc: raise serializers.ValidationError({'password': list(exc.messages)})
        if self.instance and self.instance == self.context['request'].user:
            if attrs.get('is_active') is False or attrs.get('role', self.instance.role) != self.instance.role:
                raise serializers.ValidationError('No puedes desactivar tu propia cuenta ni cambiar tu propio rol.')
        return attrs
    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(username=uuid.uuid4().hex, password=password, **validated_data)
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance

class EquipmentSerializer(serializers.ModelSerializer):
    current_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    last_service_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    next_service = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    progress = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_label = serializers.SerializerMethodField()
    photo = serializers.ImageField(required=False, validators=[validate_image])
    class Meta:
        model = Equipment
        fields = '__all__'
        read_only_fields = ['created_at']
    def get_status_label(self, obj): return LABELS[obj.status]
    def validate(self, attrs):
        initial = attrs.get('initial_value', getattr(self.instance, 'initial_value', 0))
        service = attrs.get('initial_service_value', getattr(self.instance, 'initial_service_value', 0))
        if service > initial:
            raise serializers.ValidationError({'initial_service_value': 'No puede superar la lectura inicial.'})
        if self.instance and (self.instance.readings.exists() or self.instance.maintenances.exists()):
            for field in ('initial_value', 'initial_service_value', 'unit'):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError({field: 'El equipo tiene historial; registra una lectura o mantención para actualizarlo.'})
        return attrs

class ReadingSerializer(serializers.ModelSerializer):
    equipment_code = serializers.CharField(source='equipment.code', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    registered_by = serializers.SerializerMethodField()
    evidence = serializers.ImageField(required=False, validators=[validate_image])
    class Meta:
        model = Reading
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'sensor']
    def get_registered_by(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else 'Dispositivo'
    def validate(self, attrs):
        equipment = attrs.get('equipment', getattr(self.instance, 'equipment', None))
        value = attrs.get('value', getattr(self.instance, 'value', None))
        moment = attrs.get('recorded_at', getattr(self.instance, 'recorded_at', timezone.now()))
        if not equipment.active: raise serializers.ValidationError({'equipment': 'El equipo está inactivo.'})
        if moment > timezone.now(): raise serializers.ValidationError({'recorded_at': 'La lectura no puede estar en el futuro.'})
        if self.instance and equipment.pk != self.instance.equipment_id:
            raise serializers.ValidationError({'equipment': 'No puedes reasignar una lectura histórica.'})
        if self.instance:
            for field in ('client_id', 'source'):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError({field: 'La identificación y la fuente originales se conservan.'})
        qs = equipment.readings.exclude(pk=getattr(self.instance, 'pk', None))
        before = qs.filter(recorded_at__lte=moment).order_by('-recorded_at', '-id').first()
        after = qs.filter(recorded_at__gt=moment).order_by('recorded_at', 'id').first()
        minimum = before.value if before else equipment.initial_value
        if value < minimum or (after and value > after.value):
            raise serializers.ValidationError({'value': f'Lectura fuera de secuencia. Debe ser ≥ {minimum}' + (f' y ≤ {after.value}.' if after else '.')})
        completed = equipment.maintenances.filter(status='completed', completed_at__lte=moment).order_by('-value').first()
        if completed and value < completed.value:
            raise serializers.ValidationError({'value': 'No puede ser inferior al horómetro de la mantención completada.'})
        confidence = attrs.get('confidence')
        if confidence is not None and not (0 <= confidence <= 100):
            raise serializers.ValidationError({'confidence': 'Debe estar entre 0 y 100.'})
        return attrs

class SupplySerializer(serializers.ModelSerializer):
    class Meta:
        model = Supply
        fields = '__all__'

class MaintenanceSupplySerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='supply.description', read_only=True)
    code = serializers.CharField(source='supply.code', read_only=True)
    unit = serializers.CharField(source='supply.unit', read_only=True)
    class Meta:
        model = MaintenanceSupply
        fields = ['supply', 'quantity', 'description', 'code', 'unit']
    def validate_quantity(self, value):
        if value <= 0: raise serializers.ValidationError('La cantidad debe ser positiva.')
        return value

class MaintenanceSerializer(serializers.ModelSerializer):
    equipment_code = serializers.CharField(source='equipment.code', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    supplies = MaintenanceSupplySerializer(many=True, required=False)
    class Meta:
        model = Maintenance
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']
    def validate(self, attrs):
        equipment = attrs.get('equipment', getattr(self.instance, 'equipment', None))
        if not equipment.active: raise serializers.ValidationError({'equipment': 'El equipo está inactivo.'})
        if self.instance and equipment.pk != self.instance.equipment_id:
            raise serializers.ValidationError({'equipment': 'No puedes reasignar una mantención.'})
        if attrs.get('status', getattr(self.instance, 'status', 'scheduled')) == 'completed':
            value = attrs.get('value', getattr(self.instance, 'value', 0))
            other = equipment.maintenances.filter(status='completed').exclude(pk=getattr(self.instance, 'pk', None)).order_by('-value').first()
            baseline = other.value if other else equipment.initial_service_value
            if value < baseline or value > equipment.current_value:
                raise serializers.ValidationError({'value': f'Debe estar entre {baseline} y la lectura actual ({equipment.current_value}).'})
            completed_at = attrs.get('completed_at', getattr(self.instance, 'completed_at', None))
            if not completed_at:
                attrs['completed_at'] = timezone.now()
            elif completed_at > timezone.now():
                raise serializers.ValidationError({'completed_at': 'La finalización no puede estar en el futuro.'})
        supplies = attrs.get('supplies', [])
        ids = [item['supply'].pk for item in supplies]
        if len(ids) != len(set(ids)): raise serializers.ValidationError({'supplies': 'No repitas un mismo insumo.'})
        return attrs
    def create(self, validated_data):
        supplies = validated_data.pop('supplies', [])
        instance = Maintenance.objects.create(**validated_data)
        for item in supplies: MaintenanceSupply.objects.create(maintenance=instance, **item)
        return instance
    def update(self, instance, validated_data):
        supplies = validated_data.pop('supplies', None)
        instance = super().update(instance, validated_data)
        if supplies is not None:
            instance.supplies.all().delete()
            for item in supplies: MaintenanceSupply.objects.create(maintenance=instance, **item)
        return instance

class AlertSerializer(serializers.ModelSerializer):
    equipment_code = serializers.CharField(source='equipment.code', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    equipment_type = serializers.CharField(source='equipment.equipment_type', read_only=True)
    current_value = serializers.DecimalField(source='equipment.current_value', max_digits=12, decimal_places=2, read_only=True)
    next_service = serializers.DecimalField(source='equipment.next_service', max_digits=12, decimal_places=2, read_only=True)
    remaining = serializers.DecimalField(source='equipment.remaining', max_digits=12, decimal_places=2, read_only=True)
    progress = serializers.IntegerField(source='equipment.progress', read_only=True)
    unit = serializers.CharField(source='equipment.unit', read_only=True)
    severity_label = serializers.SerializerMethodField()
    class Meta:
        model = Alert
        fields = '__all__'
        read_only_fields = ['equipment', 'maintenance', 'active', 'severity', 'message', 'attended_at']
    def get_severity_label(self, obj): return LABELS.get(obj.severity, obj.severity)

class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        exclude = ['token_hash']

class AuditSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    class Meta:
        model = AuditLog
        fields = '__all__'
    def get_user_name(self, obj): return obj.user.get_full_name() if obj.user else 'Sistema / dispositivo'
