from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import User,Equipment,Reading,Maintenance,Supply,MaintenanceSupply,Alert


class QueryEfficiencyTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='query-admin',email='queries@example.com',role='admin')
        self.client=APIClient();self.client.force_authenticate(self.user)

    def test_alert_list_uses_two_queries_independent_of_count(self):
        for i in range(24):
            equipment=Equipment.objects.create(code=f'Q-{i}',name='Prueba',equipment_type='Camion',initial_value=240,interval=250)
            Reading.objects.create(equipment=equipment,value=240)
            Alert.objects.create(equipment=equipment,severity='upcoming',message='Simulado')
        with self.assertNumQueries(2):
            response=self.client.get('/api/alerts/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.data),24)
        self.assertEqual(Decimal(response.data[0]['current_value']),Decimal(240))

    def test_history_queries_do_not_grow_with_readings_and_service_supplies(self):
        equipment=Equipment.objects.create(code='HISTORY',name='Prueba',equipment_type='Camion')
        supply=Supply.objects.create(code='TEST-OIL',description='Aceite',unit='litros')
        Reading.objects.create(equipment=equipment,value=0,created_by=self.user)
        path=f'/api/equipment/{equipment.pk}/history/'
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as first:
            self.client.get(path)
        # Agregar registros no debe crear consultas individuales para cada autor/insumo.
        for i in range(20):
            Reading.objects.create(equipment=equipment,value=i+1,created_by=self.user)
            service=Maintenance.objects.create(equipment=equipment,value=i,interval=250,scheduled_at=timezone.now()-timedelta(days=1),status='scheduled',workshop='Taller',created_by=self.user)
            MaintenanceSupply.objects.create(maintenance=service,supply=supply,quantity=1)
        with CaptureQueriesContext(connection) as second:
            response=self.client.get(path)
        self.assertLessEqual(len(second),len(first)+2)
        self.assertLessEqual(len(second),10)
        self.assertEqual(len(response.data['readings']),21)
        self.assertEqual(len(response.data['maintenances']),20)
