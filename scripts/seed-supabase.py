"""Carga los datos ficticios del proyecto usando backend/.env."""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--preview', action='store_true',
        help='Ejecuta la carga en una transacción y revierte todos sus cambios.',
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    import django
    django.setup()

    from django.conf import settings
    from django.core.management import call_command
    from django.db import transaction
    from django.test.utils import override_settings
    from fleet.models import User, Equipment, Reading, Maintenance, Supply, Gateway, Sensor, Alert

    database = settings.DATABASES['default']
    host = database.get('HOST', '')
    if (database.get('ENGINE') != 'django.db.backends.postgresql'
            or not host.endswith(('.supabase.com', '.supabase.co'))):
        raise ValueError('Configura DATABASE_URL con la conexión PostgreSQL de Supabase.')

    print(f'Destino: {host} / {database["NAME"]}')
    # Solo comprueba migraciones: no altera la estructura automáticamente.
    call_command('migrate', check=True, verbosity=0)

    models = (User, Equipment, Reading, Maintenance, Supply, Gateway, Sensor, Alert)
    with transaction.atomic():
        before = {model: model.objects.count() for model in models}
        # seed_demo exige DEBUG=True. Se habilita solo en este proceso de carga;
        # no cambia .env ni la configuración de seguridad del servicio en Render.
        with override_settings(DEBUG=True):
            call_command('seed_demo')
        for model in models:
            total = model.objects.count()
            print(f'{model.__name__}: {total - before[model]} nuevos; {total} en total')
        if args.preview:
            transaction.set_rollback(True)
    print('Vista previa revertida; no se guardaron cambios.' if args.preview
          else 'Carga finalizada. Las cuentas existentes conservaron sus contraseñas.')


if __name__ == '__main__':
    main()
