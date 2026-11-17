from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import User, Equipment


class MaintenanceTypesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='types', email='types@example.com', role='admin')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.equipment = Equipment.objects.create(code='TYPE-1', name='Prueba', equipment_type='Camion')

    def save_type(self, value):
        return self.client.post('/api/maintenances/', {'equipment': self.equipment.pk,
            'service_type': value, 'value': 0, 'interval': 250,
            'scheduled_at': timezone.now().isoformat(), 'workshop': 'Taller', 'status': 'scheduled'}, format='json')

    def test_catalog_options_are_accepted(self):
        response = self.client.get('/api/maintenances/service-types/')
        self.assertEqual(response.status_code, 200)
        for option in response.data['options']:
            self.assertEqual(self.save_type(option['value']).status_code, 201)

    def test_free_text_is_rejected(self):
        response = self.save_type('Tipo inventado')
        self.assertEqual(response.status_code, 400)
        self.assertIn('service_type', response.data)

    def test_corrective_maintenance_is_accepted(self):
        response = self.save_type('Correctiva')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['service_type'], 'Correctiva')

    def test_legacy_simulated_type_is_normalized(self):
        response = self.save_type('Preventiva simulada')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['service_type'], 'Preventiva')
