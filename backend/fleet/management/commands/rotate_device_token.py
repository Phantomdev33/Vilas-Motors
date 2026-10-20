import hashlib
import secrets
from django.core.management.base import BaseCommand, CommandError
from fleet.models import Sensor

class Command(BaseCommand):
    help = 'Genera un token de telemetría nuevo. Se muestra una sola vez y se almacena únicamente su hash.'
    def add_arguments(self, parser): parser.add_argument('identifier')
    def handle(self, *args, **options):
        try: sensor = Sensor.objects.get(identifier=options['identifier'])
        except Sensor.DoesNotExist: raise CommandError('Sensor inexistente.')
        token = secrets.token_urlsafe(32)
        sensor.token_hash = hashlib.sha256(token.encode()).hexdigest()
        sensor.save(update_fields=['token_hash'])
        self.stdout.write(token)
