from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from fleet.models import Equipment, Reading, Maintenance, User
from fleet.services import audit, reconcile_alert


class Command(BaseCommand):
    help = 'Agrega equipos SIM exclusivos del prototipo sin modificar registros existentes.'

    @transaction.atomic
    def handle(self, *args, **options):
        user = User.objects.filter(is_active=True, role='admin').first()
        if not user:
            raise CommandError('Se requiere un administrador existente para registrar la carga.')
        regions = [('Arica y Parinacota', 'Arica'), ('Tarapac\u00e1', 'Alto Hospicio'),
                   ('Antofagasta', 'Calama'), ('Atacama', 'Copiap\u00f3'), ('Coquimbo', 'La Serena')]
        types = [('Gr\u00faa horquilla', 'Komatsu', 'FG25', 'hrs', 250),
                 ('Cami\u00f3n tolva', 'Volvo', 'FMX', 'km', 10000),
                 ('Excavadora', 'CAT', '320', 'hrs', 250),
                 ('Cargador frontal', 'Volvo', 'L120H', 'hrs', 500),
                 ('Gr\u00faa m\u00f3vil', 'Liebherr', 'LTM', 'hrs', 250)]
        created_count = 0
        for index in range(10):
            code = f'SIM-{index + 1:03}'
            if Equipment.objects.filter(code=code).exists():
                continue
            kind, brand, model, unit, interval = types[index % 5]
            region, commune = regions[index % 5]
            fraction = [Decimal('0.4'), Decimal('0.9'), Decimal('1'), Decimal('1.12'), Decimal('0.3')][index % 5]
            baseline = interval * 10
            current = Decimal(baseline) + Decimal(interval) * fraction
            equipment = Equipment.objects.create(
                code=code, name=f'{kind} {brand} {model}', equipment_type=kind,
                brand=brand, model=model, serial_number=f'PROTOTIPO-{code}',
                region=region, commune=commune, location=f'Faena simulada {index + 1}',
                responsible='Responsable simulado', unit=unit, interval=interval,
                initial_value=current - 20, initial_service_value=baseline,
                import_notes='DATOS SIMULADOS - Prototipo acad\u00e9mico. Ubicaci\u00f3n y registros ficticios.',
                updated_by=user,
            )
            for days in range(3, -1, -1):
                Reading.objects.create(equipment=equipment, value=current - days * 5,
                    recorded_at=timezone.now() - timedelta(days=days), source='manual',
                    note='Lectura simulada para prototipo acad\u00e9mico.', created_by=user)
            Maintenance.objects.create(equipment=equipment, interval=interval, value=current,
                service_type='Preventiva simulada', scheduled_at=timezone.now() + timedelta(days=index),
                status='in_progress' if index in (4, 9) else 'scheduled',
                workshop='Taller simulado', work_order=f'SIM-OT-{index + 1:03}',
                description='Mantenci\u00f3n ficticia del prototipo.', created_by=user)
            reconcile_alert(equipment, user)
            audit(user, 'prototype_import', equipment, 'Carga de datos simulados SIM.')
            created_count += 1
        self.stdout.write(f'Creados: {created_count}. Equipos SIM totales: {Equipment.objects.filter(code__startswith="SIM-").count()}.')
