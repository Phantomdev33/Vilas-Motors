"""Configuración PostgreSQL local o remota sin conexiones durante el arranque."""

from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict


def database_config(env, base_dir):
    url = env.get('DATABASE_URL', '').strip()
    if url:
        # libpq interpreta los escapes de contraseña y las opciones de la URI.
        try:
            if not url.startswith(('postgres://', 'postgresql://')):
                raise ValueError
            params = conninfo_to_dict(url)
            if not all(params.get(key) for key in ('host', 'dbname', 'user')):
                raise ValueError
            if not 1 <= int(params.get('port', '5432')) <= 65535:
                raise ValueError
        except (ProgrammingError, ValueError):
            # El mensaje de libpq puede incluir la URI y su contraseña.
            raise ValueError('DATABASE_URL debe ser una URI PostgreSQL válida.') from None

        connection = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': params.pop('dbname'),
            'USER': params.pop('user'),
            'PASSWORD': params.pop('password', ''),
            'HOST': params.pop('host'),
            'PORT': params.pop('port', '5432'),
        }
        params.setdefault('sslmode', 'require')
    elif env.get('DATABASE_ENGINE') == 'sqlite':
        return {'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': base_dir / 'db.sqlite3',
        }}
    else:
        if (env.get('DJANGO_DEBUG', 'false').lower() != 'true'
                and not env.get('POSTGRES_HOST')):
            raise ValueError('Configura DATABASE_URL o POSTGRES_HOST para el despliegue.')
        connection = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.get('POSTGRES_DB', 'vilas_motor'),
            'USER': env.get('POSTGRES_USER', 'vilas'),
            'PASSWORD': env.get('POSTGRES_PASSWORD', ''),
            'HOST': env.get('POSTGRES_HOST', '127.0.0.1'),
            'PORT': env.get('POSTGRES_PORT', '5432'),
        }
        params = {}
        sslmode = env.get('POSTGRES_SSLMODE', '').strip()
        if sslmode:
            params['sslmode'] = sslmode
        elif connection['HOST'].endswith(('.supabase.com', '.supabase.co')):
            params['sslmode'] = 'require'

    params.setdefault('connect_timeout', 10)
    connection['OPTIONS'] = params
    connection['CONN_MAX_AGE'] = 0
    # Compatible también con el pooler en modo transacción.
    connection['DISABLE_SERVER_SIDE_CURSORS'] = True
    if str(connection['PORT']) == '6543':
        params['prepare_threshold'] = None
    return {'default': connection}
