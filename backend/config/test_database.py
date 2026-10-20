import unittest
from pathlib import Path

from config.database import database_config


class DatabaseConfigTests(unittest.TestCase):
    def config(self, **env):
        return database_config(env, Path('/app'))['default']

    def test_supabase_url_overrides_local_settings_and_decodes_password(self):
        db = self.config(
            DATABASE_URL='postgresql://postgres.project:p%40ss%3Aword@aws-0-region.pooler.supabase.com:5432/postgres',
            POSTGRES_HOST='localhost', DATABASE_ENGINE='sqlite',
        )
        self.assertEqual(db['HOST'], 'aws-0-region.pooler.supabase.com')
        self.assertEqual(db['USER'], 'postgres.project')
        self.assertEqual(db['PASSWORD'], 'p@ss:word')
        self.assertEqual(db['OPTIONS']['sslmode'], 'require')

    def test_preserves_certificate_verification(self):
        db = self.config(DATABASE_URL=(
            'postgres://user:password@db.example:5432/postgres'
            '?sslmode=verify-full&sslrootcert=/certs/root.crt'
        ))
        self.assertEqual(db['OPTIONS']['sslmode'], 'verify-full')
        self.assertEqual(db['OPTIONS']['sslrootcert'], '/certs/root.crt')

    def test_local_postgres_does_not_require_ssl(self):
        db = self.config(POSTGRES_PORT='55432', DJANGO_DEBUG='true')
        self.assertEqual(db['HOST'], '127.0.0.1')
        self.assertEqual(db['PORT'], '55432')
        self.assertNotIn('sslmode', db['OPTIONS'])

    def test_deployment_requires_explicit_database_host(self):
        with self.assertRaisesRegex(ValueError, 'DATABASE_URL o POSTGRES_HOST'):
            self.config(DJANGO_DEBUG='false')

    def test_separate_supabase_credentials_enable_ssl(self):
        db = self.config(POSTGRES_HOST='db.project.supabase.co')
        self.assertEqual(db['OPTIONS']['sslmode'], 'require')

    def test_transaction_pooler_disables_prepared_statements(self):
        db = self.config(DATABASE_URL='postgres://u:p@pooler.example:6543/postgres')
        self.assertIsNone(db['OPTIONS']['prepare_threshold'])
        self.assertTrue(db['DISABLE_SERVER_SIDE_CURSORS'])

    def test_sqlite_remains_available_without_url(self):
        self.assertEqual(self.config(DATABASE_ENGINE='sqlite')['ENGINE'],
                         'django.db.backends.sqlite3')

    def test_invalid_urls_do_not_expose_credentials(self):
        for url in ('https://user:secret@host/db', 'postgres://user:secret@host:notaport/db',
                    'postgres://user:secret@/db'):
            with self.subTest(url=url):
                with self.assertRaises(ValueError) as caught:
                    self.config(DATABASE_URL=url)
                self.assertNotIn('secret', str(caught.exception))
