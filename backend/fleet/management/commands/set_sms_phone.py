from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fleet.models import User


class Command(BaseCommand):
    help = 'Registra el celular de una cuenta existente para habilitar el acceso por SMS.'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('phone')

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            user = User.objects.select_for_update().get(email__iexact=options['email'])
        except (User.DoesNotExist, User.MultipleObjectsReturned) as exc:
            raise CommandError('El correo debe identificar a una sola cuenta.') from exc
        try:
            user.phone = User._meta.get_field('phone').clean(options['phone'], user)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from exc
        if not user.phone:
            raise CommandError('Ingresa un número de celular.')
        user.save(update_fields=['phone'])
        self.stdout.write(self.style.SUCCESS('Celular registrado.'))
