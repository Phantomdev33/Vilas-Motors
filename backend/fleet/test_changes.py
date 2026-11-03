import hashlib
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import CaptchaChallenge, Equipment, User


class ChangesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='changes', email='changes@example.cl', password='SecureDemo2026!', first_name='Ana', role='admin')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.eq = Equipment.objects.create(code='TEST', name='Prueba', equipment_type='Camión', brand='Test', model='1', serial_number='TEST', region='Tarapacá', commune='Iquique', unit='km', initial_value=1000)

    def test_password_length(self):
        with self.assertRaises(ValidationError):
            validate_password('Abcdefgh1234')
        validate_password('Abcdefgh12345!')

    def test_equipment_editor_and_history_cannot_be_forged(self):
        result = self.client.patch(f'/api/equipment/{self.eq.pk}/', {'name':'Actualizado','updated_by':999}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['updated_by'], self.user.pk)
        history = self.client.get(f'/api/equipment/{self.eq.pk}/history/').data
        self.assertEqual(history['changes'][0]['user_name'], 'Ana')

    def test_completion_before_start_rejected_and_units_returned(self):
        body = {'equipment':self.eq.pk,'value':1000,'interval':500,'scheduled_at':timezone.now().isoformat(),'completed_at':(timezone.now()-timedelta(hours=1)).isoformat(),'status':'completed','workshop':'Ana'}
        self.assertEqual(self.client.post('/api/maintenances/',body,format='json').status_code,400)
        body['status']='in_progress'
        result=self.client.post('/api/maintenances/',body,format='json')
        # A supplied completion before the start is always invalid.
        self.assertEqual(result.status_code,400)
        body['completed_at']=None
        result=self.client.post('/api/maintenances/',body,format='json')
        self.assertEqual(result.status_code,201)
        self.assertEqual(result.data['unit'],'km')
        self.assertEqual(result.data['registered_by'],'Ana')
        self.assertIsNone(result.data['completed_at'])

    def test_captcha_required_consumed_and_expired(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/auth/login/',{},format='json').status_code,400)
        item=CaptchaChallenge.objects.create(answer_hash=hashlib.sha256(b'ABC234').hexdigest(),expires_at=timezone.now()+timedelta(minutes=5))
        body={'email':self.user.email,'password':'SecureDemo2026!','captcha_id':str(item.pk),'captcha_answer':'wrong'}
        self.assertEqual(self.client.post('/api/auth/login/',body,format='json').status_code,400)
        self.assertFalse(CaptchaChallenge.objects.filter(pk=item.pk).exists())
        body['captcha_answer']='ABC234'
        self.assertEqual(self.client.post('/api/auth/login/',body,format='json').status_code,400)
        item=CaptchaChallenge.objects.create(answer_hash=hashlib.sha256(b'ABC234').hexdigest(),expires_at=timezone.now()-timedelta(seconds=1))
        body['captcha_id']=str(item.pk)
        self.assertEqual(self.client.post('/api/auth/login/',body,format='json').status_code,400)

    def test_captcha_image_has_no_answer(self):
        self.client.force_authenticate(None)
        result=self.client.get('/api/auth/captcha/')
        self.assertEqual(result.status_code,200)
        self.assertEqual(set(result.data),{'id','image'})
        self.assertTrue(result.data['image'].startswith('data:image/png;base64,'))

    def test_import_replaces_without_deleting_and_is_idempotent(self):
        from django.core.management import call_command
        from io import StringIO
        call_command('import_equipment', replace=True, stdout=StringIO())
        self.eq.refresh_from_db()
        self.assertFalse(self.eq.active)
        imported=Equipment.objects.filter(code__startswith='XLS-')
        self.assertEqual(imported.count(),394)
        self.assertFalse(imported.filter(meter_initialized=True).exists())
        self.assertFalse(imported.exclude(serial_number=None).exists())
        call_command('import_equipment', replace=True, stdout=StringIO())
        self.assertEqual(imported.count(),394)
        self.assertTrue(all(e.status=='pending' for e in imported))

    def test_service_interval_drives_next_maintenance_and_report(self):
        result=self.client.post('/api/maintenances/',{'equipment':self.eq.pk,'value':1000,'interval':500,'scheduled_at':timezone.now().isoformat(),'status':'completed','workshop':'Ana'},format='json')
        self.assertEqual(result.status_code,201)
        self.eq.refresh_from_db()
        self.assertEqual(self.eq.next_service,1500)
        self.assertEqual(Decimal(self.client.get('/api/report/').data['equipment'][0]['next_service']),Decimal(1500))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', FRONTEND_URL='https://fleet.example.cl')
    def test_password_recovery_validates_length_and_consumes_reset_link(self):
        from django.core import mail
        from urllib.parse import urlsplit, parse_qs
        self.client.force_authenticate(None)
        def captcha():
            item=CaptchaChallenge.objects.create(answer_hash=hashlib.sha256(b'ABC234').hexdigest(),expires_at=timezone.now()+timedelta(minutes=5))
            return {'captcha_id':str(item.pk),'captcha_answer':'ABC234'}
        response=self.client.post('/api/auth/reset/',{'email':self.user.email,**captcha()},format='json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(mail.outbox),1)
        query=parse_qs(urlsplit(mail.outbox[0].body.splitlines()[-1]).query)
        body={'uid':query['reset'][0],'token':query['token'][0],'password':'ShortPass12!',**captcha()}
        self.assertEqual(self.client.post('/api/auth/reset/confirm/',body,format='json').status_code,400)
        body.update(password='AnotherStrong2026!',**captcha())
        self.assertEqual(self.client.post('/api/auth/reset/confirm/',body,format='json').status_code,200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('AnotherStrong2026!'))
        body.update(captcha())
        self.assertEqual(self.client.post('/api/auth/reset/confirm/',body,format='json').status_code,400)
