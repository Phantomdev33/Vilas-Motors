from django.core.management.base import BaseCommand
from django.db import transaction
from fleet.models import Reading
from fleet.image_storage import ReadingImageStorage
from fleet.services import audit


class Command(BaseCommand):
    help='Copia evidencias MANUALES locales a MongoDB. No borra archivos ni toca equipos, lecturas GPS u otros datos.'

    def add_arguments(self,parser):
        parser.add_argument('--apply',action='store_true')

    def handle(self,*args,**options):
        rows=Reading.objects.filter(source='manual').exclude(evidence='').exclude(evidence__startswith='mongo/')
        self.stdout.write(f'Evidencias locales manuales pendientes: {rows.count()}')
        if not options['apply']:
            self.stdout.write('Vista previa; usa --apply tras configurar y comprobar MongoDB.')
            return
        storage=ReadingImageStorage()
        for pk in rows.values_list('pk',flat=True).iterator():
            uploaded=None
            try:
                with transaction.atomic():
                    reading=Reading.objects.select_for_update().get(pk=pk)
                    if not reading.evidence or reading.evidence.name.startswith('mongo/'):
                        continue
                    with reading.evidence.open('rb') as original:
                        uploaded=storage.save(original.name,original)
                    reading.evidence=uploaded
                    reading.save(update_fields=['evidence'])
                    audit(None,'manual_image_migrated',reading,'Evidencia copiada a MongoDB; original local conservado.')
            except Exception:
                if uploaded:
                    storage.delete(uploaded)
                raise
            self.stdout.write(f'Lectura {pk}: evidencia copiada.')
