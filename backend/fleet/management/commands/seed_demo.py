import hashlib
import os
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from fleet.models import User, Equipment, Reading, Maintenance, Supply, Gateway, Sensor
from fleet.services import reconcile_alert

class Command(BaseCommand):
    help = 'Carga exclusivamente datos ficticios, sin sobrescribir registros existentes.'
    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG: raise CommandError('Los datos de demostración solo se cargan con DJANGO_DEBUG=true.')
        password = os.getenv('DEMO_PASSWORD', 'VilasDemo2026!')
        people = [('admin@vilasmotor.cl','Alex','Morgan','admin'), ('james@vilasmotor.cl','James','Pérez','planner'),
                  ('ayudante@vilasmotor.cl','Jamie','Cruz','helper'), ('jefe@vilasmotor.cl','Elías','Ríos','chief')]
        for email, first, last, role in people:
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(username=email, email=email, password=password, first_name=first, last_name=last,
                    role=role, is_staff=role=='admin', is_superuser=role=='admin')
        planner = User.objects.get(email='james@vilasmotor.cl')
        fixtures = [('EX-01','CAT 320','Excavadora','CAT','320',4280,4000,250,'hrs'),
                    ('LD-02','Volvo L120H','Cargador frontal','Volvo','L120H',6100,6100-500,500,'hrs'),
                    ('DT-03','Volvo FMX','Camión tolva','Volvo','FMX',48920,40000,10000,'km'),
                    ('GH-04','Montacargas','Grúa horquilla','CAT','140',3090,2650,500,'hrs'),
                    ('EX-05','Komatsu PC210','Excavadora','Komatsu','PC210',2120,2000,250,'hrs'),
                    ('WL-06','Cargador frontal','Cargador frontal','CAT','950M',3340,3250,250,'hrs')]
        gateway, _ = Gateway.objects.get_or_create(identifier='GW-NORTE-01', defaults={'model':'Gateway piloto', 'last_connection':timezone.now()})
        for index,(code,name,kind,brand,model,current,baseline,interval,unit) in enumerate(fixtures):
            eq, created = Equipment.objects.get_or_create(code=code, defaults={'name':name,'equipment_type':kind,'brand':brand,'model':model,
                'serial_number':f'DEMO-{code}-2026','region':'Tarapacá','commune':'Alto Hospicio','location':'Faena Norte · Zona A',
                'responsible':'James Pérez','unit':unit,'interval':interval,'initial_value':current-100,'initial_service_value':baseline})
            if created:
                for offset in range(5, -1, -1):
                    Reading.objects.create(equipment=eq, value=Decimal(current)-Decimal(offset)*10,
                        recorded_at=timezone.now()-timedelta(days=offset, minutes=10), source='ocr' if offset%2 else 'manual',
                        confidence=98 if offset%2 else None, note='Dato ficticio de demostración', created_by=planner)
                Maintenance.objects.create(equipment=eq, service_type='Preventiva · Servicio de motor', interval=interval, value=current,
                    scheduled_at=timezone.now()+timedelta(days=index), workshop='Maestranza Vila · Taller Central',
                    work_order=f'OT-2026-{index+1:03}', status='scheduled', created_by=planner, description='Programación de demostración.')
                token = secrets.token_urlsafe(32)
                Sensor.objects.create(equipment=eq, gateway=gateway, identifier=f'CAM-{code}', token_hash=hashlib.sha256(token.encode()).hexdigest())
            reconcile_alert(eq, planner)
        for code, description, unit in [('OIL-15W40','Aceite de motor · SAE 15W-40','litros'),('CAT-1R1808','Filtro de aceite de motor','unidad'),('GREASE-EP2','Grasa multipropósito','kg')]:
            Supply.objects.get_or_create(code=code, defaults={'description':description,'unit':unit})
        self.stdout.write(self.style.SUCCESS('Datos ficticios cargados. Se conservaron todos los registros existentes.'))
        self.stdout.write('Cuentas demo: admin@vilasmotor.cl, james@vilasmotor.cl, ayudante@vilasmotor.cl, jefe@vilasmotor.cl')
        self.stdout.write('Contraseña inicial: la variable DEMO_PASSWORD o la documentada en README.md.')
