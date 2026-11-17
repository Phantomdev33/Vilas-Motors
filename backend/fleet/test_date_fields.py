from datetime import timedelta, datetime, time
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Equipment,Reading,User


class DateOnlyFormTests(TestCase):
    def setUp(self):
        self.eq=Equipment.objects.create(code='DATE',name='Prueba',equipment_type='Camion',initial_value=100,initial_service_value=100)
        self.user=User.objects.create_user(username='dates',email='dates@example.com',role='admin')
        self.client=APIClient();self.client.force_authenticate(self.user)

    def test_new_manual_date_uses_today_without_creating_a_future_timestamp(self):
        response=self.client.post('/api/readings/',{'equipment':self.eq.pk,'value':101,'recorded_at':timezone.localdate().isoformat()},format='json')
        self.assertEqual(response.status_code,201)
        reading=Reading.objects.get()
        self.assertEqual(timezone.localdate(reading.recorded_at),timezone.localdate())
        self.assertLessEqual(reading.recorded_at,timezone.now())

    def test_edit_same_date_preserves_exact_original_time_and_gps_order(self):
        original=timezone.now()-timedelta(hours=2)
        reading=Reading.objects.create(equipment=self.eq,value=101,recorded_at=original)
        gps=Reading.objects.create(equipment=self.eq,value=102,recorded_at=original+timedelta(minutes=20),source='sensor')
        response=self.client.patch(f'/api/readings/{reading.pk}/',{'value':101,'recorded_at':timezone.localdate(original).isoformat()},format='json')
        self.assertEqual(response.status_code,200)
        reading.refresh_from_db();self.assertEqual(reading.recorded_at,original)
        gps.refresh_from_db();self.assertEqual(gps.value,Decimal('102'))

    def test_future_manual_dates_are_rejected(self):
        future=(timezone.localdate()+timedelta(days=1)).isoformat()
        response=self.client.post('/api/readings/',{'equipment':self.eq.pk,'value':101,'recorded_at':future},format='json')
        self.assertEqual(response.status_code,400)

    def test_maintenance_can_start_and_complete_on_same_date_without_hours(self):
        response=self.client.post('/api/maintenances/',{'equipment':self.eq.pk,'value':100,'interval':250,'service_type':'Preventiva','workshop':'Taller','status':'completed','scheduled_at':timezone.localdate().isoformat(),'completed_at':timezone.localdate().isoformat()},format='json')
        self.assertEqual(response.status_code,201)
        maintenance=self.eq.maintenances.get()
        self.assertLessEqual(maintenance.scheduled_at,maintenance.completed_at)
        self.assertLessEqual(maintenance.completed_at,timezone.now())
