import hashlib
import io
import uuid
from datetime import timedelta
from decimal import Decimal
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from unittest.mock import patch
from .test_support import MemoryImageCollection
from django.utils import timezone
from rest_framework.test import APIClient
from .models import User, Equipment, Reading, Maintenance, Alert, AuditLog, Sensor
from .services import reconcile_alert

class FleetAPITests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin',email='admin@test.cl',password='SecureDemo2026!',role='admin')
        self.planner = User.objects.create_user(username='planner',email='planner@test.cl',password='SecureDemo2026!',role='planner')
        self.helper = User.objects.create_user(username='helper',email='helper@test.cl',password='SecureDemo2026!',role='helper')
        self.chief = User.objects.create_user(username='chief',email='chief@test.cl',password='SecureDemo2026!',role='chief')
        self.eq = Equipment.objects.create(code='EX-01',name='CAT 320',equipment_type='Excavadora',brand='CAT',model='320',
            serial_number='TEST-01',region='Tarapacá',commune='Alto Hospicio',interval=250,initial_value=4000,initial_service_value=4000)
        self.client = APIClient(); self.client.force_authenticate(self.planner)
    def reading(self,value,**extra):
        return self.client.post('/api/readings/',{'equipment':self.eq.pk,'value':value,**extra},format='json')
    def maintenance(self,**extra):
        return self.client.post('/api/maintenances/',{'equipment':self.eq.pk,'value':4250,'interval':250,
            'scheduled_at':timezone.now().isoformat(),'service_type':'Preventiva','workshop':'Taller Central','status':'completed',**extra},format='json')
    def test_reading_updates_state_and_audit(self):
        response=self.reading(4240)
        self.assertEqual(response.status_code,201)
        self.eq.refresh_from_db(); self.assertEqual(self.eq.remaining,Decimal(10)); self.assertEqual(self.eq.status,'upcoming')
        self.assertEqual(Alert.objects.filter(active=True).count(),1)
        self.assertTrue(AuditLog.objects.filter(user=self.planner,entity='Reading').exists())
    def test_decreasing_empty_and_non_numeric_readings_rejected(self):
        self.assertEqual(self.reading(4200).status_code,201)
        for value in [4199,'', 'no-numérico',-1]:
            self.assertEqual(self.reading(value).status_code,400)
        self.assertEqual(Reading.objects.count(),1)
    def test_future_reading_rejected(self):
        self.assertEqual(self.reading(4200,recorded_at=(timezone.now()+timedelta(days=1)).isoformat()).status_code,400)
    def test_duplicate_sync_is_idempotent(self):
        client_id=str(uuid.uuid4())
        self.assertEqual(self.reading(4200,client_id=client_id).status_code,201)
        self.assertEqual(self.reading(4200,client_id=client_id).status_code,200)
        self.assertEqual(Reading.objects.count(),1)
    def test_duplicate_identifier_cannot_be_reused_by_other_user(self):
        client_id=str(uuid.uuid4());self.reading(4200,client_id=client_id)
        self.client.force_authenticate(self.helper)
        self.assertEqual(self.reading(4200,client_id=client_id).status_code,403)
    def test_alerts_do_not_duplicate(self):
        self.reading(4240);self.reading(4245);self.reading(4251)
        self.assertEqual(Alert.objects.filter(active=True).count(),1)
        self.assertEqual(Alert.objects.get(active=True).severity,'overdue')
    def test_completed_maintenance_resets_interval_and_closes_alert(self):
        self.reading(4250)
        original=Alert.objects.get(active=True)
        original_message=original.message
        result=self.maintenance()
        self.assertEqual(result.status_code,201)
        self.eq.refresh_from_db();self.assertEqual(self.eq.next_service,Decimal(4500));self.assertEqual(self.eq.status,'operational')
        self.assertEqual(Alert.objects.filter(active=True).count(),0)
        self.assertIsNotNone(Alert.objects.get().attended_at)
        original.refresh_from_db()
        self.assertFalse(original.active)
        self.assertEqual(original.message,original_message)
        self.assertEqual(original.maintenance_id,result.data['id'])
        self.assertTrue(AuditLog.objects.filter(entity='Alert',entity_id=str(original.pk),action='alert_attended',user=self.planner).exists())
        self.assertEqual(self.reading(4490).status_code,201)
        self.assertEqual(Alert.objects.filter(active=True).count(),1)
        self.assertEqual(Alert.objects.count(),2)
        original.refresh_from_db()
        self.assertFalse(original.active)
        self.assertEqual(original.maintenance_id,result.data['id'])
    def test_draft_and_schedule_do_not_reset_interval(self):
        self.reading(4250)
        for state in ['draft','scheduled']:
            self.assertEqual(self.maintenance(status=state).status_code,201)
        self.eq.refresh_from_db();self.assertEqual(self.eq.next_service,Decimal(4250));self.assertEqual(self.eq.status,'required')
        self.assertTrue(Alert.objects.get(active=True))
    def test_maintenance_cannot_exceed_current_reading(self):
        self.assertEqual(self.maintenance().status_code,400)
    def test_helper_cannot_change_equipment_or_create_users(self):
        self.client.force_authenticate(self.helper)
        self.assertEqual(self.client.patch(f'/api/equipment/{self.eq.id}/',{'name':'Changed'},format='json').status_code,403)
        self.assertEqual(self.client.post('/api/users/',{},format='json').status_code,403)
        self.assertEqual(self.reading(4100).status_code,201)
    def test_chief_is_read_only(self):
        self.client.force_authenticate(self.chief)
        self.assertEqual(self.client.get('/api/equipment/').status_code,200)
        self.assertEqual(self.client.get('/api/users/').status_code,200)
        self.assertEqual(self.reading(4100).status_code,403)
        self.assertEqual(self.maintenance().status_code,403)
    def test_planner_cannot_deactivate_equipment(self):
        self.assertEqual(self.client.delete(f'/api/equipment/{self.eq.pk}/').status_code,403)
    def test_admin_deactivation_preserves_history(self):
        self.reading(4240);self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f'/api/equipment/{self.eq.pk}/').status_code,204)
        self.eq.refresh_from_db();self.assertFalse(self.eq.active);self.assertEqual(self.eq.readings.count(),1)
        self.assertEqual(self.eq.alerts.count(),1)
    def test_telemetry_requires_device_token_and_ignition_events(self):
        sensor=Sensor.objects.create(equipment=self.eq,identifier='TEST-GPS',token_hash=hashlib.sha256(b'device-secret').hexdigest())
        self.client.force_authenticate(None)
        self.assertEqual(self.reading(4100).status_code,401)
        body={'event_id':'on','recorded_at':(timezone.now()-timedelta(hours=3)).isoformat(),'ignition':True}
        self.assertEqual(self.client.post('/api/telemetry/',body,format='json').status_code,401)
        self.client.credentials(HTTP_AUTHORIZATION='Device device-secret')
        self.assertEqual(self.client.post('/api/telemetry/',body,format='json').status_code,201)
        off={'event_id':'off','recorded_at':(timezone.now()-timedelta(hours=1)).isoformat(),'ignition':False}
        self.assertEqual(self.client.post('/api/telemetry/',off,format='json').status_code,201)
        self.assertEqual(Reading.objects.get().sensor,sensor)
        self.assertEqual(self.client.post('/api/telemetry/',{'value':4099},format='json').status_code,400)
    @patch('fleet.image_storage.image_collection')
    def test_photo_is_saved_and_requires_authentication_to_view(self,collection):
        collection.return_value=MemoryImageCollection()
        buffer=io.BytesIO();Image.new('RGB',(20,20),'white').save(buffer,format='PNG')
        photo=SimpleUploadedFile('meter.png',buffer.getvalue(),content_type='image/png')
        response=self.client.post('/api/readings/',{'equipment':self.eq.pk,'value':4100,'evidence':photo},format='multipart')
        self.assertEqual(response.status_code,201)
        path=response.data['evidence'].replace('http://testserver','')
        self.assertEqual(self.client.get(path).status_code,200)
        self.client.force_authenticate(None);self.assertEqual(self.client.get(path).status_code,401)
    def test_daily_report_uses_historical_reading_and_exports(self):
        yesterday=timezone.now()-timedelta(days=1)
        self.reading(4100,recorded_at=yesterday.isoformat());self.reading(4240)
        response=self.client.get('/api/report/',{'date':timezone.localtime(yesterday).date().isoformat()})
        self.assertEqual(response.status_code,200);self.assertEqual(Decimal(response.data['equipment'][0]['current_value']),Decimal(4100))
        for output in ['pdf','xlsx']:
            response=self.client.get('/api/report/',{'export':output});self.assertEqual(response.status_code,200)
            content=b''.join(response.streaming_content);self.assertTrue(content.startswith(b'%PDF' if output=='pdf' else b'PK'))
    def test_daily_report_query_count_is_bounded(self):
        for i in range(30):
            Equipment.objects.create(code=f'REPORT-{i}',name='Carga',equipment_type='Generador',brand='CAT',model='G',serial_number=f'R-{i}',region='Norte',commune='Iquique')
        with self.assertNumQueries(1):
            response=self.client.get('/api/report/')
        self.assertEqual(len(response.data['equipment']),31)

    def test_equipment_list_query_count_is_bounded(self):
        for i in range(30):
            Equipment.objects.create(code=f'LOAD-{i}',name='Carga',equipment_type='Generador',brand='CAT',model='G',serial_number=f'S-{i}',region='Norte',commune='Iquique')
        with self.assertNumQueries(1):
            response=self.client.get('/api/equipment/')
        self.assertEqual(len(response.data),31)

class AuthenticationTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='test',email='test@vilas.cl',password='SecureDemo2026!',role='planner',phone='+56912345678')
        self.client=APIClient(enforce_csrf_checks=True)
        response=self.client.get('/api/auth/csrf/');self.csrf=response.data['csrfToken']
    def login(self,password):
        from .models import CaptchaChallenge
        captcha = CaptchaChallenge.objects.create(answer_hash=hashlib.sha256(b'ABC234').hexdigest(), expires_at=timezone.now()+timedelta(minutes=5))
        return self.client.post('/api/auth/login/',{'email':self.user.email,'password':password,'captcha_id':str(captcha.pk),'captcha_answer':'ABC234'},format='json',HTTP_X_CSRFTOKEN=self.csrf)
    def test_login_requires_csrf_and_sets_http_only_cookie(self):
        import re
        from contextlib import redirect_stdout
        from io import StringIO
        from django.test import override_settings
        self.assertEqual(self.client.post('/api/auth/login/',{},format='json').status_code,403)
        console = StringIO()
        with override_settings(DEBUG=True, SMS_BACKEND='console'), redirect_stdout(console):
            response = self.login('SecureDemo2026!')
        self.assertEqual(response.status_code, 202)
        self.assertNotIn('access_token', response.cookies)
        self.assertIn(self.client.get('/api/auth/me/').status_code, (401, 403))
        sent = re.search(r'\[SMS simulado\].*ingresar: (\d{6})\.', console.getvalue())
        self.assertIsNotNone(sent)
        body = {'challenge_id': str(response.data['challenge_id']), 'code': sent.group(1)}
        self.assertEqual(self.client.post('/api/auth/login/verify/', body, format='json').status_code, 403)
        response = self.client.post('/api/auth/login/verify/', body, format='json', HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies['access_token']['httponly'])
        self.assertEqual(self.client.get('/api/auth/me/').status_code,200)
        self.assertEqual(self.client.post('/api/readings/',{},format='json').status_code,403)
        self.assertEqual(self.client.post('/api/auth/login/verify/', body, format='json', HTTP_X_CSRFTOKEN=self.csrf).status_code, 400)
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertIn(self.client.get('/api/auth/me/').status_code, (401, 403))
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])
        self.assertIn(self.client.get('/api/auth/me/').status_code, (401, 403))

    def test_disabled_account_cannot_start_or_complete_login_after_admin_reactivation(self):
        from unittest.mock import patch
        with patch('fleet.sms.send_code') as send_code:
            response = self.login('SecureDemo2026!')
            self.assertEqual(response.status_code, 202)
            body = {'challenge_id': str(response.data['challenge_id']), 'code': send_code.call_args.args[1]}
            admin = User.objects.create_superuser(username='admin', email='admin@vilas.cl', password='SecureDemo2026!')
            admin_client = APIClient()
            admin_client.force_authenticate(admin)
            url = f'/api/users/{self.user.pk}/'
            self.assertEqual(admin_client.patch(url, {'is_active': False}, format='json').status_code, 200)
            self.assertEqual(self.login('SecureDemo2026!').status_code, 401)
            send_code.assert_called_once()
            self.assertEqual(admin_client.patch(url, {'is_active': True}, format='json').status_code, 200)
            self.assertEqual(self.client.post('/api/auth/login/verify/', body, format='json', HTTP_X_CSRFTOKEN=self.csrf).status_code, 400)

    def test_sms_code_expires_and_locks_after_five_attempts(self):
        from unittest.mock import patch
        from .models import SMSChallenge
        url = '/api/auth/login/verify/'
        with patch('fleet.sms.send_code') as send_code:
            response = self.login('SecureDemo2026!')
            first_id = response.data['challenge_id']
            code = send_code.call_args.args[1]
            wrong_code = '000000' if code != '000000' else '111111'
            for _ in range(5):
                result = self.client.post(url, {'challenge_id': str(first_id), 'code': wrong_code}, format='json', HTTP_X_CSRFTOKEN=self.csrf)
                self.assertEqual(result.status_code, 400)
            self.assertEqual(self.client.post(url, {'challenge_id': str(first_id), 'code': code}, format='json', HTTP_X_CSRFTOKEN=self.csrf).status_code, 400)
            self.assertEqual(self.login('SecureDemo2026!').status_code, 429)
            SMSChallenge.objects.filter(pk=first_id).update(sent_at=timezone.now() - timedelta(minutes=2))
            response = self.login('SecureDemo2026!')
            self.assertEqual(response.status_code, 202)
            second_id = response.data['challenge_id']
            SMSChallenge.objects.filter(pk=second_id).update(sent_at=timezone.now() - timedelta(minutes=5))
            self.assertEqual(self.client.post(url, {'challenge_id': str(second_id), 'code': send_code.call_args.args[1]}, format='json', HTTP_X_CSRFTOKEN=self.csrf).status_code, 400)

    def test_django_admin_uses_the_verified_application_session(self):
        from unittest.mock import patch
        self.user.role = 'admin'
        self.user.is_staff = True
        self.user.save(update_fields=['role', 'is_staff'])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        with patch('fleet.sms.send_code') as send_code:
            response = self.login('SecureDemo2026!')
        body = {'challenge_id': str(response.data['challenge_id']), 'code': send_code.call_args.args[1]}
        response = self.client.post('/api/auth/login/verify/', body, format='json', HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/admin/').status_code, 200)
    def test_five_failed_attempts_lock_account(self):
        for _ in range(5):self.assertEqual(self.login('wrong').status_code,401)
        self.assertEqual(self.login('SecureDemo2026!').status_code,429)
        self.user.refresh_from_db();self.assertIsNotNone(self.user.locked_until)
    def test_passwords_are_hashed(self):
        self.assertNotEqual(self.user.password,'SecureDemo2026!');self.assertTrue(self.user.check_password('SecureDemo2026!'))
    def test_admin_cannot_disable_self_and_weak_password_rejected(self):
        self.user.role='admin';self.user.save();self.client.force_authenticate(self.user)
        self.assertEqual(self.client.patch(f'/api/users/{self.user.pk}/',{'is_active':False},format='json').status_code,400)
        response=self.client.post('/api/users/',{'email':'new@test.cl','password':'password','first_name':'New','role':'helper'},format='json')
        self.assertEqual(response.status_code,400)
