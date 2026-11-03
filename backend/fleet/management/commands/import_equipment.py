import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from fleet.models import Equipment, User, AuditLog
from fleet.services import audit, reconcile_alert


class Command(BaseCommand):
    help = 'Importa todas las filas de Equipos.xlsx, conservando duplicados físicos y el historial anterior.'

    def add_arguments(self, parser):
        parser.add_argument('--replace', action='store_true', help='Desactiva equipos ajenos a este catálogo.')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--actor', help='Correo del usuario que ejecuta la importación; por defecto se registra Sistema.')

    @transaction.atomic
    def handle(self, *args, **options):
        source = Path(__file__).resolve().parents[2] / 'data' / 'equipment_catalog.json'
        rows = json.loads(source.read_text(encoding='utf-8'))
        actor = None
        if options['actor']:
            actor = User.objects.filter(email__iexact=options['actor'], role='admin', is_active=True).first()
            if actor is None:
                raise CommandError('El actor debe ser un administrador activo.')
        created = existing = deactivated = 0
        codes = [r['code'] for r in rows]
        if len(set(codes)) != len(codes) or not rows:
            raise CommandError('Catálogo vacío o con códigos repetidos.')
        if options['replace']:
            for equipment in Equipment.objects.select_for_update().filter(active=True).exclude(code__in=codes):
                equipment.active = False
                equipment.updated_by = actor
                equipment.save(update_fields=['active', 'updated_by', 'updated_at'])
                audit(actor, 'deactivated', equipment, 'Reemplazo de catálogo por Equipos.xlsx; se conserva el historial.')
                reconcile_alert(equipment, actor)
                deactivated += 1
        existing_codes = set(Equipment.objects.filter(code__in=codes).values_list('code', flat=True))
        pending = []
        for row in rows:
            if row['code'] in existing_codes:
                existing += 1
                continue
            unit = 'km' if any(word in row['equipment_type'] for word in ('CAMION', 'CAMIONETA', 'MINIBUS', 'TRACTO')) else 'hrs'
            pending.append(Equipment(code=row['code'], **{
                'name': row['equipment_type'], 'equipment_type': row['equipment_type'],
                'brand': row['brand'], 'model': row['model'], 'serial_number': None,
                'region': '', 'commune': '', 'unit': unit, 'interval': 10000 if unit == 'km' else 250,
                'meter_initialized': False, 'updated_by': actor,
                'import_notes': f"Equipos.xlsx · Hoja1 · fila {row['row']}. Código interno generado para la importación. Serie, patente, región, comuna, responsable, lecturas e intervalo por confirmar. Unidad sugerida según tipo; confirmar antes de operar.",
            }))
        Equipment.objects.bulk_create(pending)
        AuditLog.objects.bulk_create([AuditLog(user=actor, action='imported', entity='Equipment', entity_id=str(item.pk), description=item.import_notes) for item in pending])
        created = len(pending)
        if options['dry_run']:
            transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f"{'SIMULACIÓN: ' if options['dry_run'] else ''}{len(rows)} filas; {created} creados; {existing} existentes conservados; {deactivated} anteriores desactivados."))
