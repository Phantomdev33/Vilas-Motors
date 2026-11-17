"""Escenario local repetible: no configura ni contacta dispositivos reales."""
import hashlib
import secrets
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from fleet.models import Equipment, Sensor
from fleet.gps import ingest_ignition


class Command(BaseCommand):
    help = 'Simula encendido GPS FMB120 solo para equipos SIM, conservando eventos e historial.'

    def add_arguments(self, parser):
        parser.add_argument('--equipment', help='Codigo SIM; por defecto todos los SIM activos.')
        parser.add_argument('--scenario', default='demo-v1', help='Identificador repetible del escenario.')
        parser.add_argument('--session-seconds',type=int,default=3600,help='Unidad temporal del escenario; 3600 representa horas, 10 permite una prueba corta.')

    @transaction.atomic
    def handle(self, *args, **options):
        step=options['session_seconds']
        if not 1<=step<=86400:
            raise CommandError('--session-seconds debe estar entre 1 y 86400.')
        rows=Equipment.objects.filter(active=True, code__startswith='SIM-').order_by('code')
        if options['equipment']:
            rows=rows.filter(code=options['equipment'])
        if not rows.exists():
            raise CommandError('No hay equipos SIM activos. Carga primero load_prototype.')
        total=0
        for equipment in rows:
            identifier=f'SIM-FMB120-{equipment.code}'
            other=equipment.sensors.filter(active=True,sensor_type='GPS').exclude(identifier=identifier)
            if other.exists():
                raise CommandError(f'{equipment.code} tiene otro GPS activo; no se modifica.')
            sensor,_=Sensor.objects.get_or_create(identifier=identifier,defaults={
                'equipment':equipment,'sensor_type':'GPS','model':'Teltonika FMB120',
                'token_hash':hashlib.sha256(secrets.token_bytes(32)).hexdigest()})
            prefix=f"{options['scenario']}:{equipment.code}:"
            previous=sensor.ignition_events.filter(event_id__startswith=prefix).order_by('recorded_at').first()
            start=previous.recorded_at if previous else timezone.now()-timedelta(hours=5)
            latest=equipment.readings.order_by('-recorded_at').first()
            if not previous and latest and start<=latest.recorded_at:
                start=latest.recorded_at+timedelta(seconds=1)
            if start+timedelta(seconds=step*4)>timezone.now():
                self.stdout.write(f'{equipment.code}: sin ventana historica suficiente; usa otro escenario con --session-seconds 10 o espera. No se inventan fechas futuras.')
                continue
            for index,(hours,on) in enumerate([(0,True),(2,False),(3,True),(4,False)]):
                _,created=ingest_ignition(sensor,prefix+str(index),start+timedelta(seconds=step*hours),on,simulated=True)
                total+=int(created)
            seconds=sensor.meter_state.counted_seconds
            self.stdout.write(f'{equipment.code}: {seconds/3600:.4f} horas estimadas simuladas desde la referencia; '+('lecturas hrs generadas.' if equipment.unit=='hrs' else 'eventos conservados sin convertir kilometros a horas.'))
        self.stdout.write(self.style.SUCCESS(f'Eventos nuevos: {total}. Repetir el mismo escenario no duplica eventos ni lecturas.'))
