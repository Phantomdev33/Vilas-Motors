"""Prototipo acad?mico aislado. Nunca utiliza la base remota."""
from .settings import *
DEBUG = True
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'prototype.sqlite3'}}
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
MEDIA_ROOT = BASE_DIR / 'prototype-media'
