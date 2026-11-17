import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.core.management import call_command
from django.db.models import F
from django.test import TestCase,override_settings
from .models import User,Equipment,Reading,Maintenance,Alert,Sensor,IgnitionEvent,GPSMeterState,AuditLog
from .demo_dataset import populate


class DeliveryDemoTests(TestCase):
    def setUp(self):
        self.actor=User.objects.create_user(username='delivery-admin',email='delivery@example.com',role='admin',password='DeliveryDemo2026!')

    def test_dataset_has_consistent_history_and_variety(self):
        counts=populate(self.actor)
        self.assertEqual(counts['Equipment'],50)
        self.assertEqual(Equipment.objects.filter(active=True).count(),50)
        self.assertEqual(Equipment.objects.values('equipment_type').distinct().count(),35)
        self.assertEqual(Equipment.objects.values('region').distinct().count(),5)
        self.assertGreater(counts['Reading'],400)
        self.assertGreater(counts['Maintenance'],100)
        self.assertEqual(counts['IgnitionEvent'],192)
        self.assertEqual(counts['GPSMeterState'],48)
        self.assertEqual(Alert.objects.filter(active=False).count(),48)
        self.assertEqual(Alert.objects.filter(active=True).count(),25)
        self.assertFalse(Reading.objects.filter(source='ocr').exists())
        for equipment in Equipment.objects.all():
            readings=list(equipment.readings.order_by('recorded_at'))
            values=[r.value for r in readings]
            self.assertEqual(values,sorted(values))
            self.assertTrue(equipment.import_notes.startswith('DATOS SIMULADOS'))
            if not equipment.meter_initialized:
                self.assertFalse(readings)
                self.assertFalse(equipment.maintenances.exists())
            else:
                self.assertEqual(equipment.sensors.get().meter_state.counted_seconds,10800)
                if equipment.unit=='km':self.assertFalse(equipment.readings.filter(source='sensor').exists())
                current=equipment.alerts.filter(active=True).first()
                if current:self.assertEqual(current.severity,equipment.status)
        self.assertFalse(Alert.objects.filter(active=False,attended_at__lt=F('created_at')).exists())

    def test_apply_backs_up_old_data_and_keeps_account_access(self):
        old=Equipment.objects.create(code='OLD',name='Anterior',equipment_type='Camion')
        Reading.objects.create(equipment=old,value=0,created_by=self.actor)
        AuditLog.objects.create(user=self.actor,action='user_updated',entity='User',entity_id=str(self.actor.pk))
        password=self.actor.password
        with TemporaryDirectory() as directory,override_settings(BASE_DIR=Path(directory)/'backend'):
            with patch('fleet.management.commands.prepare_delivery_demo.call_command'):
                call_command('prepare_delivery_demo',apply=True,stdout=StringIO())
            backups=list((Path(directory)/'.runtime'/'backups').glob('*.json'))
            self.assertEqual(len(backups),1)
            backup=json.loads(backups[0].read_text(encoding='utf-8'))
            self.assertTrue(any(x['model']=='fleet.equipment' and x['fields']['code']=='OLD' for x in backup))
            self.assertFalse(any(x['model']=='fleet.user' for x in backup))
        self.assertFalse(Equipment.objects.filter(code='OLD').exists())
        self.assertEqual(Equipment.objects.count(),50)
        self.actor.refresh_from_db();self.assertEqual(self.actor.password,password)
        self.assertTrue(AuditLog.objects.filter(entity='User',action='user_updated').exists())
        self.assertTrue(AuditLog.objects.filter(action='delivery_demo_reset').exists())

    def test_preview_does_not_change_existing_data(self):
        Equipment.objects.create(code='OLD',name='Anterior',equipment_type='Camion')
        call_command('prepare_delivery_demo',stdout=StringIO())
        self.assertEqual(Equipment.objects.count(),1)
        self.assertTrue(Equipment.objects.filter(code='OLD').exists())
