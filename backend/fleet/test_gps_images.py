import hashlib
import io
from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from .gps import ingest_ignition
from .models import Equipment, Sensor, Reading, IgnitionEvent, GPSMeterState, User, Alert, AuditLog
from .image_storage import ImageStoreUnavailable
from .test_support import MemoryImageCollection


class GPSIgnitionTests(TestCase):
    def setUp(self):
        self.eq=Equipment.objects.create(code='SIM-TEST',name='Prueba',equipment_type='Excavadora',initial_value=100,initial_service_value=100,unit='hrs',interval=250)
        self.sensor=Sensor.objects.create(equipment=self.eq,identifier='SIM-FMB120-TEST',token_hash=hashlib.sha256(b'gps-secret').hexdigest())
        self.start=timezone.now()-timedelta(days=3)

    def send(self,event_id,hours,on=True):
        return ingest_ignition(self.sensor,event_id,self.start+timedelta(hours=hours),on,simulated=True)

    def test_on_off_counts_only_confirmed_on_time_and_duplicates_do_not_add_hours(self):
        self.send('on',0)
        event,created=self.send('off',2,False)
        self.assertTrue(created);self.assertEqual(event.counted_seconds,7200)
        self.assertEqual(event.reading.value,Decimal('102.00'))
        duplicate,created=self.send('off',2,False)
        self.assertFalse(created);self.assertEqual(duplicate.pk,event.pk)
        self.send('off-again',3,False)
        self.send('on-again',4)
        self.send('final',5,False)
        self.assertEqual(Reading.objects.order_by('-recorded_at').first().value,Decimal('103.00'))
        self.assertEqual(Reading.objects.count(),2)
        self.assertEqual(IgnitionEvent.objects.count(),5)

    def test_late_events_are_archived_without_rewriting_readings(self):
        self.send('on',0);self.send('off',2,False)
        late,_=self.send('late',1,False)
        self.assertEqual(late.outcome,'late');self.assertEqual(Reading.objects.count(),1)
        with self.assertRaises(ValidationError): self.send('on',0,False)

    @override_settings(GPS_MAX_EVENT_GAP_SECONDS=3600)
    def test_missing_continuity_does_not_invent_hours(self):
        self.send('on',0);event,_=self.send('missing',4,False)
        self.assertEqual(event.outcome,'gap');self.assertEqual(Reading.objects.count(),0)
        self.assertEqual(GPSMeterState.objects.get().skipped_seconds,14400)

    def test_manual_reference_recalibrates_without_double_counting(self):
        self.send('on',0)
        Reading.objects.create(equipment=self.eq,value=Decimal('110'),recorded_at=self.start+timedelta(hours=1),source='manual')
        event,_=self.send('off',2,False)
        self.assertEqual(event.reading.value,Decimal('111.00'))

    def test_kilometers_are_not_replaced_by_hours(self):
        self.eq.unit='km';self.eq.save()
        self.send('on',0);self.send('off',2,False)
        self.assertEqual(Reading.objects.count(),0)
        self.assertEqual(GPSMeterState.objects.get().counted_seconds,7200)

    def test_telemetry_rejects_ocr_values_and_future_or_unzoned_events(self):
        client=APIClient()
        data={'event_id':'one','recorded_at':self.start.isoformat(),'ignition':True}
        self.assertEqual(client.post('/api/telemetry/',data,format='json').status_code,401)
        client.credentials(HTTP_AUTHORIZATION='Device gps-secret')
        self.assertEqual(client.post('/api/telemetry/',{**data,'value':123},format='json').status_code,400)
        self.assertEqual(client.post('/api/telemetry/',{**data,'confidence':99},format='json').status_code,400)
        self.assertEqual(client.post('/api/telemetry/',{**data,'recorded_at':(timezone.now()+timedelta(days=1)).isoformat()},format='json').status_code,400)
        self.assertEqual(client.post('/api/telemetry/',{**data,'recorded_at':'2026-01-01T12:00:00'},format='json').status_code,400)
        self.assertEqual(client.post('/api/telemetry/',data,format='json').status_code,201)
        self.assertEqual(client.post('/api/telemetry/',data,format='json').status_code,200)

    def test_automatic_estimates_are_labeled_and_cannot_be_edited(self):
        self.send('on',0);event,_=self.send('off',2,False)
        user=User.objects.create_user(username='gps-admin',email='gps@example.com',role='admin')
        client=APIClient();client.force_authenticate(user)
        response=client.get('/api/readings/').data[0]
        self.assertTrue(response['is_estimated']);self.assertTrue(response['is_simulated'])
        self.assertEqual(client.patch(f'/api/readings/{event.reading_id}/',{'value':102},format='json').status_code,400)


class MongoReadingImageTests(TestCase):
    def setUp(self):
        self.eq=Equipment.objects.create(code='IMG',name='Prueba',equipment_type='Camion',initial_value=100)
        self.user=User.objects.create_user(username='img-admin',email='img@example.com',role='admin')
        self.client=APIClient();self.client.force_authenticate(self.user)
        self.images=MemoryImageCollection()
        self.patcher=patch('fleet.image_storage.image_collection',return_value=self.images)
        self.patcher.start();self.addCleanup(self.patcher.stop)

    def photo(self):
        buffer=io.BytesIO();Image.new('RGB',(20,20),'white').save(buffer,format='PNG')
        return SimpleUploadedFile('foto.png',buffer.getvalue(),content_type='image/png')

    def test_photo_bytes_go_to_mongo_and_only_reference_stays_in_sql(self):
        response=self.client.post('/api/readings/',{'equipment':self.eq.pk,'value':101,'evidence':self.photo()},format='multipart')
        self.assertEqual(response.status_code,201)
        reading=Reading.objects.get();self.assertTrue(reading.evidence.name.startswith('mongo/'))
        self.assertEqual(len(self.images.documents),1)
        stored=self.images.documents[reading.evidence.name]
        self.assertTrue(bytes(stored['data']).startswith(b'\x89PNG'))
        self.assertEqual(stored['content_type'],'image/png')
        self.assertNotIn('value',stored)
        url=response.data['evidence']
        image=self.client.get(url);self.assertEqual(image.status_code,200)
        self.assertEqual(image['Cache-Control'],'private, no-store')
        self.assertEqual(b''.join(image.streaming_content),bytes(stored['data']))
        self.client.force_authenticate(None);self.assertEqual(self.client.get(url).status_code,401)

    def test_missing_mongo_configuration_does_not_silently_save_to_disk(self):
        with patch('fleet.image_storage.image_collection',side_effect=ImageStoreUnavailable()):
            response=self.client.post('/api/readings/',{'equipment':self.eq.pk,'value':101,'evidence':self.photo()},format='multipart')
        self.assertEqual(response.status_code,503);self.assertFalse(Reading.objects.exists())
        self.assertEqual(self.client.post('/api/readings/',{'equipment':self.eq.pk,'value':101},format='json').status_code,201)

    def test_no_new_ocr_readings_or_photo_extraction(self):
        response=self.client.post('/api/readings/',{'equipment':self.eq.pk,'value':101,'source':'ocr','evidence':self.photo()},format='multipart')
        self.assertEqual(response.status_code,400);self.assertFalse(self.images.documents)

    def test_legacy_local_evidence_remains_readable(self):
        with TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=directory):
            storage=FileSystemStorage();name=storage.save('readings/old.png',self.photo())
            Reading.objects.create(equipment=self.eq,value=101,evidence=name,source='manual')
            response=self.client.get('/api/media/'+name)
            self.assertEqual(response.status_code,200)
            b''.join(response.streaming_content)
