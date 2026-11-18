import hashlib
import io
import uuid
from datetime import datetime, timedelta, time
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import OuterRef, Subquery, DecimalField, IntegerField, Q, Exists, Prefetch
from django.db.models.functions import Coalesce
from django.http import HttpResponse, FileResponse, Http404
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.static import serve
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from .authentication import enforce_csrf
from .models import User, Equipment, Reading, Maintenance, Supply, Alert, AuditLog, Sensor
from .permissions import RolePermission
from .serializers import UserSerializer, EquipmentSerializer, ReadingSerializer, MaintenanceSerializer, SupplySerializer, AlertSerializer, AuditSerializer, SensorSerializer
from .services import audit, reconcile_alert, LABELS
from .throttles import DeviceTelemetryThrottle
from .captcha import challenge, verify
from .sms import SMSUnavailable, check_challenge, start_challenge
from .service_references import REFERENCES

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache


@method_decorator(never_cache, name='dispatch')
class CSRFView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def get(self, request): return Response({'csrfToken': get_token(request)})

class CaptchaView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def get(self, request):
        response = Response(challenge())
        response['Cache-Control'] = 'no-store'
        return response

class CaptchaProtectedView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method != 'POST':
            return
        enforce_csrf(request)
        with transaction.atomic():
            error = verify(request)
        if error:
            raise ValidationError({'captcha': error})

class LoginView(CaptchaProtectedView):
    permission_classes = [AllowAny]
    authentication_classes = []
    @transaction.atomic
    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        password = request.data.get('password', '')
        if not isinstance(password, str) or len(password) > 1024:
            return Response({'detail': 'Credenciales incorrectas.'}, status=401)
        user = User.objects.select_for_update().filter(email__iexact=email).first()
        if user and user.is_active and user.locked_until and user.locked_until > timezone.now():
            return Response({'detail': 'Acceso bloqueado temporalmente. Intenta nuevamente en 15 minutos.'}, status=429)
        if user and user.locked_until:
            user.failed_attempts = 0
            user.locked_until = None
            user.save(update_fields=['failed_attempts', 'locked_until'])
        authenticated = authenticate(request, username=user.username if user else email, password=password)
        if not authenticated or not user or not user.is_active:
            if user and user.is_active:
                user.failed_attempts += 1
                if user.failed_attempts >= 5: user.locked_until = timezone.now() + timedelta(minutes=15)
                user.save(update_fields=['failed_attempts', 'locked_until'])
            return Response({'detail': 'Correo o contraseña incorrectos.'}, status=401)
        if not user.phone:
            return Response({'detail': 'Pide a un administrador que registre tu número de celular.'}, status=403)
        user.password = authenticated.password
        try:
            challenge_id = start_challenge(user, 'login')
        except SMSUnavailable:
            return Response({'detail': 'El envío de SMS no está disponible. Intenta nuevamente.'}, status=503)
        if not challenge_id:
            return Response({'detail': 'Espera un minuto antes de solicitar otro código.'}, status=429)
        user.failed_attempts, user.locked_until = 0, None
        user.save(update_fields=['failed_attempts', 'locked_until'])
        response = Response({'challenge_id': challenge_id}, status=202)
        response['Cache-Control'] = 'no-store'
        return response


class SMSConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def verify_code(self, request, purpose):
        enforce_csrf(request)
        return check_challenge(request.data.get('challenge_id'), purpose, request.data.get('code'))

    def invalid_code(self):
        return Response({'detail': 'Código incorrecto, vencido o agotado. Puedes solicitar otro.'}, status=400)


class LoginVerifyView(SMSConfirmView):
    @transaction.atomic
    def post(self, request):
        user, sms = self.verify_code(request, 'login')
        if not user:
            return self.invalid_code()
        if user.locked_until and user.locked_until > timezone.now():
            return self.invalid_code()
        sms.used = True
        sms.save(update_fields=['used'])
        user.failed_attempts, user.locked_until, user.last_login = 0, None, timezone.now()
        user.save(update_fields=['failed_attempts', 'locked_until', 'last_login'])
        response = Response(UserSerializer(user).data)
        token = AccessToken.for_user(user)
        token['sms_access'] = str(user.access_version)
        response.set_cookie('access_token', str(token), httponly=True, secure=not settings.DEBUG, samesite='Lax', max_age=7200)
        audit(user, 'login', user)
        return response

class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        enforce_csrf(request)
        response = Response({'detail': 'Sesión cerrada.'})
        response.delete_cookie('access_token', samesite='Lax')
        return response

class ServiceReferencesView(APIView):
    def get(self, request):
        return Response(REFERENCES)

class PasswordResetView(CaptchaProtectedView):
    permission_classes = [AllowAny]
    authentication_classes = []
    @transaction.atomic
    def post(self, request):
        email = str(request.data.get('email', '')).strip()
        user = User.objects.select_for_update().filter(email__iexact=email, is_active=True).first()
        challenge_id = None
        if user and user.phone:
            try:
                challenge_id = start_challenge(user, 'reset')
            except SMSUnavailable:
                pass
        response = Response({
            'challenge_id': challenge_id or uuid.uuid4(),
            'detail': 'Si tu cuenta está activa y tiene un celular registrado, recibirás un código por SMS. Espera un minuto antes de solicitar otro.',
        }, status=202)
        response['Cache-Control'] = 'no-store'
        return response


class PasswordResetConfirmView(SMSConfirmView):
    @transaction.atomic
    def post(self, request):
        user, sms = self.verify_code(request, 'reset')
        if not user:
            return self.invalid_code()
        password = request.data.get('password', '')
        if not isinstance(password, str) or len(password) > 1024:
            raise ValidationError('Contraseña inválida.')
        try: validate_password(password, user)
        except DjangoValidationError as exc: raise ValidationError({'password': list(exc.messages)})
        user.set_password(password)
        user.failed_attempts, user.locked_until = 0, None
        user.save(update_fields=['password', 'failed_attempts', 'locked_until'])
        sms.used = True
        sms.save(update_fields=['used'])
        audit(user, 'password_reset', user)
        return Response({'detail': 'Contraseña actualizada. Ya puedes ingresar.'})

class AuditedViewSet(viewsets.ModelViewSet):
    permission_classes = [RolePermission]
    def perform_create(self, serializer):
        instance = serializer.save()
        audit(self.request.user, 'created', instance)
    def perform_update(self, serializer):
        instance = serializer.save()
        audit(self.request.user, 'updated', instance)

class EquipmentViewSet(AuditedViewSet):
    queryset = Equipment.objects.select_related('updated_by').annotate(
        _service_interval=Coalesce(Subquery(Maintenance.objects.filter(equipment=OuterRef('pk'), status='completed').order_by('-value', '-id').values('interval')[:1]), 'interval', output_field=IntegerField()),
        _current_value=Coalesce(Subquery(Reading.objects.filter(equipment=OuterRef('pk')).order_by('-recorded_at', '-id').values('value')[:1]), 'initial_value', output_field=DecimalField()),
        _last_service_value=Coalesce(Subquery(Maintenance.objects.filter(equipment=OuterRef('pk'), status='completed').order_by('-value', '-id').values('value')[:1]), 'initial_service_value', output_field=DecimalField()))
    serializer_class = EquipmentSerializer
    permission_module = 'equipment'
    @transaction.atomic
    def perform_create(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        audit(self.request.user, 'created', instance)
        reconcile_alert(instance, self.request.user)
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        Equipment.objects.select_for_update().get(pk=kwargs['pk'])
        return super().update(request, *args, **kwargs)
    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        audit(self.request.user, 'updated', instance)
        for key in ('_current_value', '_last_service_value', '_service_interval', 'service_interval', 'current_value', 'last_service_value', 'next_service', 'remaining', 'progress', 'status'):
            instance.__dict__.pop(key, None)
        reconcile_alert(serializer.instance, self.request.user)
    @transaction.atomic
    def perform_destroy(self, instance):
        Equipment.objects.select_for_update().get(pk=instance.pk)
        instance.active = False
        instance.updated_by = self.request.user
        instance.save(update_fields=['active', 'updated_by', 'updated_at'])
        audit(self.request.user, 'deactivated', instance)
        reconcile_alert(instance, self.request.user)
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        equipment = self.get_object()
        from .models import GPSMeterState
        from .models import IgnitionEvent
        gps_states = GPSMeterState.objects.filter(sensor__equipment=equipment).select_related('sensor').annotate(
            simulated_events=Exists(IgnitionEvent.objects.filter(sensor_id=OuterRef('sensor_id'),simulated=True)))
        gps = [{'device':g.sensor.identifier, 'model':g.sensor.model, 'last_at':g.last_at, 'ignition':g.ignition, 'counted_seconds':g.counted_seconds, 'skipped_seconds':g.skipped_seconds, 'simulated':g.simulated_events} for g in gps_states]
        return Response({'gps':gps, 'changes': AuditSerializer(AuditLog.objects.filter(entity='Equipment', entity_id=str(equipment.pk)).select_related('user'), many=True).data, 'equipment': self.get_serializer(equipment).data,
            'readings': ReadingSerializer(equipment.readings.select_related('created_by'), many=True, context={'request': request}).data,
            'maintenances': MaintenanceSerializer(equipment.maintenances.select_related('created_by').prefetch_related('supplies__supply'), many=True).data,
            'alerts': AlertSerializer(equipment.alerts.all(), many=True).data,
            'sensors': SensorSerializer(equipment.sensors.all(), many=True).data})

class ReadingViewSet(AuditedViewSet):
    queryset = Reading.objects.select_related('equipment', 'created_by').all()
    serializer_class = ReadingSerializer
    permission_module = 'reading'
    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('equipment'): qs = qs.filter(equipment_id=self.request.query_params['equipment'])
        return qs
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        equipment_id = request.data.get('equipment')
        try: Equipment.objects.select_for_update().get(pk=equipment_id)
        except (Equipment.DoesNotExist, ValueError, TypeError): raise ValidationError({'equipment': 'Equipo inválido.'})
        client_id = request.data.get('client_id')
        if client_id:
            try: client_id = uuid.UUID(str(client_id))
            except ValueError: raise ValidationError({'client_id': 'Identificador inválido.'})
            existing = Reading.objects.filter(client_id=client_id).first()
            if existing:
                if existing.created_by_id != request.user.pk or str(existing.equipment_id) != str(equipment_id):
                    raise PermissionDenied('El identificador pertenece a otro registro.')
                return Response(self.get_serializer(existing).data, status=200)
        return super().create(request, *args, **kwargs)
    def perform_create(self, serializer):
        reading = serializer.save(created_by=self.request.user, source='manual')
        audit(self.request.user, 'created', reading)
        reconcile_alert(reading.equipment, self.request.user)
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        reading = self.get_object()
        Equipment.objects.select_for_update().get(pk=reading.equipment_id)
        return super().update(request, *args, **kwargs)
    def perform_update(self, serializer):
        super().perform_update(serializer)
        reconcile_alert(serializer.instance.equipment, self.request.user)
    @transaction.atomic
    def perform_destroy(self, instance):
        Equipment.objects.select_for_update().get(pk=instance.equipment_id)
        equipment = instance.equipment
        if instance.source != 'manual':
            raise ValidationError('Conserva las lecturas GPS e históricas para mantener la trazabilidad.')
        if equipment.maintenances.filter(status='completed', value__gt=equipment.initial_value).exists():
            raise ValidationError('Esta lectura forma parte de un historial con mantenciones. Conserva el registro y corrige su valor.')
        audit(self.request.user, 'deleted', instance)
        instance.delete()
        reconcile_alert(equipment, self.request.user)

class MaintenanceViewSet(AuditedViewSet):
    @action(detail=False, methods=['get'], url_path='service-types')
    def service_types(self, request):
        from .maintenance_types import SERVICE_TYPES, LEGACY_SERVICE_TYPES
        return Response({'options': [{'value': value, 'label': value} for value in SERVICE_TYPES],
                         'aliases': LEGACY_SERVICE_TYPES})

    queryset = Maintenance.objects.select_related('equipment', 'created_by').prefetch_related('supplies__supply').all()
    serializer_class = MaintenanceSerializer
    permission_module = 'maintenance'
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try: Equipment.objects.select_for_update().get(pk=request.data.get('equipment'))
        except (Equipment.DoesNotExist, ValueError, TypeError): raise ValidationError({'equipment': 'Equipo inválido.'})
        return super().create(request, *args, **kwargs)
    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        audit(self.request.user, 'created', instance)
        reconcile_alert(instance.equipment, self.request.user, instance if instance.status == 'completed' else None)
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        Equipment.objects.select_for_update().get(pk=self.get_object().equipment_id)
        return super().update(request, *args, **kwargs)
    def perform_update(self, serializer):
        super().perform_update(serializer)
        reconcile_alert(serializer.instance.equipment, self.request.user, serializer.instance)
    @transaction.atomic
    def perform_destroy(self, instance):
        Equipment.objects.select_for_update().get(pk=instance.equipment_id)
        instance.status = 'cancelled'
        instance.save(update_fields=['status'])
        audit(self.request.user, 'cancelled', instance)
        reconcile_alert(instance.equipment, self.request.user)

class UserViewSet(AuditedViewSet):
    queryset = User.objects.all().order_by('first_name')
    serializer_class = UserSerializer
    permission_module = 'user'
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        User.objects.select_for_update().get(pk=self.get_object().pk)
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk: raise ValidationError('No puedes desactivar tu propia cuenta.')
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        audit(self.request.user, 'deactivated', instance)

class SupplyViewSet(AuditedViewSet):
    queryset = Supply.objects.all().order_by('code')
    serializer_class = SupplySerializer
    permission_module = 'supply'
    def perform_destroy(self, instance):
        instance.active = False
        instance.save(update_fields=['active'])
        audit(self.request.user, 'deactivated', instance)

class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Alert.objects.prefetch_related(Prefetch('equipment',queryset=EquipmentViewSet.queryset.all()))
    serializer_class = AlertSerializer
    permission_classes = [RolePermission]
    permission_module = 'alert'

class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').all()[:1000]
    serializer_class = AuditSerializer
    permission_classes = [RolePermission]
    permission_module = 'audit'

class TelemetryView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [DeviceTelemetryThrottle]
    @transaction.atomic
    def post(self, request):
        token = request.headers.get('Authorization', '')
        if not token.startswith('Device '): return Response({'detail': 'Token de dispositivo requerido.'}, status=401)
        token_hash = hashlib.sha256(token[7:].encode()).hexdigest()
        sensor = Sensor.objects.select_related('equipment').filter(token_hash=token_hash, active=True).first()
        if not sensor: return Response({'detail': 'Dispositivo no autorizado.'}, status=401)
        from .gps import ingest_ignition
        from .gps_serializers import IgnitionInputSerializer
        serializer = IgnitionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event, created = ingest_ignition(sensor, **serializer.validated_data)
        return Response({'id':event.pk, 'event_id':event.event_id, 'outcome':event.outcome,
            'counted_seconds':event.counted_seconds, 'reading':event.reading_id,
            'simulated':event.simulated}, status=201 if created else 200)


def report_rows(day):
    cutoff = timezone.make_aware(datetime.combine(day, time.max))
    rows = []
    equipment = Equipment.objects.filter(active=True).filter(
        Q(created_at__lte=cutoff) | Exists(Reading.objects.filter(equipment=OuterRef('pk'), recorded_at__lte=cutoff))
        | Exists(Maintenance.objects.filter(equipment=OuterRef('pk'), completed_at__lte=cutoff))).annotate(
        report_interval=Coalesce(Subquery(Maintenance.objects.filter(equipment=OuterRef('pk'), status='completed', completed_at__lte=cutoff).order_by('-value', '-id').values('interval')[:1]), 'interval', output_field=IntegerField()),
        report_value=Coalesce(Subquery(Reading.objects.filter(equipment=OuterRef('pk'), recorded_at__lte=cutoff).order_by('-recorded_at', '-id').values('value')[:1]), 'initial_value', output_field=DecimalField()),
        report_baseline=Coalesce(Subquery(Maintenance.objects.filter(equipment=OuterRef('pk'), status='completed', completed_at__lte=cutoff).order_by('-value', '-id').values('value')[:1]), 'initial_service_value', output_field=DecimalField()))
    for eq in equipment:
        value = eq.report_value
        baseline = eq.report_baseline
        next_value = baseline + eq.report_interval
        remaining = next_value - value
        state = 'overdue' if remaining < 0 else 'required' if remaining == 0 else 'upcoming' if remaining <= Decimal(eq.report_interval)*Decimal('0.15') else 'operational'
        if not eq.meter_initialized:
            state = 'pending'
        rows.append({'id': eq.id, 'code': eq.code, 'name': eq.name, 'current_value': str(value), 'next_service': str(next_value),
                     'remaining': str(remaining), 'unit': eq.unit, 'status': state, 'status_label': LABELS[state]})
    return rows

class ReportView(APIView):
    def get(self, request):
        try: day = datetime.strptime(request.query_params.get('date', timezone.localdate().isoformat()), '%Y-%m-%d').date()
        except ValueError: raise ValidationError('Fecha inválida. Usa AAAA-MM-DD.')
        rows = report_rows(day)
        output = request.query_params.get('format', 'json')
        # DRF reserves ?format for renderer negotiation: exports use ?export.
        output = request.query_params.get('export', output)
        headers = ['Equipo', 'Nombre', 'Lectura actual', 'Próxima mantención', 'Restante', 'Unidad', 'Estado']
        values = [[r['code'], r['name'], *(['Pendiente'] * 3 if r['status'] == 'pending' else [float(r['current_value']), float(r['next_service']), float(r['remaining'])]), r['unit'], r['status_label']] for r in rows]
        if output == 'xlsx':
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill
            from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
            wb = Workbook(); ws = wb.active; ws.title = 'Estado de la flota'
            ws.append([f"Vila's Motor · Informe diario · {day}"]); ws.append(headers)
            for row in values:
                ws.append([ILLEGAL_CHARACTERS_RE.sub('', v) if isinstance(v, str) else v for v in row])
                for cell in ws[ws.max_row]:
                    if isinstance(cell.value, str): cell.data_type = 's'
            for cell in ws[2]: cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid', fgColor='173F2B')
            for col in 'ABCDEFG': ws.column_dimensions[col].width = 26
            buffer = io.BytesIO(); wb.save(buffer); buffer.seek(0)
            return FileResponse(buffer, as_attachment=True, filename=f'flota-{day}.xlsx')
        if output == 'pdf':
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from xml.sax.saxutils import escape
            buffer = io.BytesIO(); styles = getSampleStyleSheet()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=25, rightMargin=25)
            table_values = [headers] + [[Paragraph(escape(str(v)), styles['BodyText']) for v in row] for row in values]
            table = Table(table_values, colWidths=[60, 145, 105, 115, 75, 45, 185], repeatRows=1)
            table.setStyle(TableStyle([('BACKGROUND', (0,0),(-1,0), colors.HexColor('#173F2B')), ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                ('VALIGN',(0,0),(-1,-1),'TOP'), ('FONTSIZE',(0,0),(-1,-1),8), ('BOTTOMPADDING',(0,0),(-1,-1),9),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#F5F7F8')]), ('GRID',(0,0),(-1,-1),0.3,colors.lightgrey)]))
            doc.build([Paragraph(f"Vila's Motor · Informe diario de máquinas · {day}", styles['Heading1']), Spacer(1,16), table])
            buffer.seek(0)
            return FileResponse(buffer, as_attachment=True, filename=f'flota-{day}.pdf')
        return Response({'date': day.isoformat(), 'equipment': rows})

class ProtectedMediaView(APIView):
    permission_classes = [RolePermission]
    permission_module = 'reading'
    def get(self, request, path):
        if path.startswith('mongo/'):
            if not Reading.objects.filter(evidence=path).exists():
                raise Http404
            from .image_storage import ReadingImageStorage
            try:
                file = ReadingImageStorage().open(path)
            except FileNotFoundError:
                raise Http404 from None
            response = FileResponse(file, content_type=file.content_type)
            response['Cache-Control'] = 'private, no-store'
            response['X-Content-Type-Options'] = 'nosniff'
            return response
        return serve(request, path, document_root=settings.MEDIA_ROOT)
