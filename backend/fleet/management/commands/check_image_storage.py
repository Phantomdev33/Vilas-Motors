from django.core.management.base import BaseCommand, CommandError
from fleet.image_storage import image_collection


class Command(BaseCommand):
    help='Comprueba MongoDB para imagenes sin crear documentos ni mostrar credenciales.'

    def handle(self,*args,**options):
        try:
            image_collection().database.command('ping')
        except Exception:
            raise CommandError('No se pudo conectar a MongoDB. Revisa MONGODB_URI, permisos y acceso de red.') from None
        self.stdout.write(self.style.SUCCESS('MongoDB disponible para evidencias de lecturas.'))
