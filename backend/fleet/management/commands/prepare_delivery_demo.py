import json
from pathlib import Path
from django.conf import settings
from django.core import serializers
from django.core.management import call_command
from django.core.management.base import BaseCommand,CommandError
from django.db import connection,transaction
from django.utils import timezone
from fleet.models import User,Equipment,AuditLog
from fleet.demo_dataset import OPERATIONAL,populate,TYPES


class Command(BaseCommand):
    help='Reemplaza el catálogo operacional por 50 equipos completamente simulados; preserva usuarios y respalda antes de borrar.'

    def add_arguments(self,parser):
        parser.add_argument('--apply',action='store_true')

    def handle(self,*args,**options):
        actor=User.objects.filter(role='admin',is_active=True).first()
        if not actor: raise CommandError('Se requiere una cuenta administradora activa existente.')
        tables=set(connection.introspection.table_names())
        models=[m for m in OPERATIONAL if m._meta.db_table in tables]
        before={m.__name__:m.objects.count() for m in models}
        self.stdout.write('Actual: '+json.dumps(before))
        self.stdout.write(f'Propuesta: 50 equipos SIM activos, {len(TYPES)} tipos, 5 regiones, 48 historiales y 2 fichas pendientes; usuarios intactos.')
        if not options['apply']:
            self.stdout.write('Vista previa. No se borraron ni escribieron datos.')
            return
        backup_dir=settings.BASE_DIR.parent/'.runtime'/'backups'
        backup_dir.mkdir(parents=True,exist_ok=True)
        backup=backup_dir/f'operational-before-demo-{timezone.now().strftime("%Y%m%d-%H%M%S-%f")}.json'
        objects=[]
        for model in reversed(models):objects.extend(model.objects.all())
        objects.extend(AuditLog.objects.all())
        # No contiene usuarios, contraseñas, claves MongoDB ni variables de entorno.
        payload=serializers.serialize('json',objects)
        with backup.open('x',encoding='utf-8') as file:file.write(payload)
        if len(json.loads(backup.read_text(encoding='utf-8')))!=len(objects):
            raise CommandError('El respaldo no pudo verificarse; no se cambia la base.')
        self.stdout.write('Respaldo verificado: '+str(backup))
        call_command('migrate',interactive=False,verbosity=0)
        with transaction.atomic():
            list(Equipment.objects.select_for_update().values_list('pk',flat=True))
            for model in OPERATIONAL:model.objects.all().delete()
            AuditLog.objects.filter(entity__in=[m.__name__ for m in OPERATIONAL]).delete()
            counts=populate(actor)
            if counts['Equipment']!=50 or Equipment.objects.exclude(code__startswith='SIM-').exists():
                raise CommandError('La validación del catálogo falló; la transacción se revierte.')
            AuditLog.objects.create(user=actor,action='delivery_demo_reset',entity='Prototype',entity_id='delivery',description='Datos operacionales reemplazados por simulación. Respaldo: '+backup.name)
        self.stdout.write(self.style.SUCCESS('Demostración preparada: '+json.dumps(counts)))
        self.stdout.write('Cuentas, contraseñas y archivos de imágenes anteriores conservados. No se eliminaron documentos MongoDB.')
