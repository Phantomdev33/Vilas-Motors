"""Comprobación de solo lectura del catálogo y reportes de demostración."""
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.test import override_settings
from rest_framework.test import APIClient
from fleet.models import Equipment,User

client=APIClient()
client.force_authenticate(User.objects.filter(role='admin',is_active=True).first())
with override_settings(ALLOWED_HOSTS=['testserver'],SECURE_SSL_REDIRECT=False):
    response=client.get('/api/report/')
    assert response.status_code==200
    assert len(response.data['equipment'])==50
    print('Informe: 50 equipos, correcto.')
    response=client.get(f'/api/equipment/{Equipment.objects.order_by("code").first().pk}/history/')
    assert response.status_code==200 and len(response.data['gps'])==1
    print('Ficha con historial GPS simulado: correcta.')
    for format,signature in [('pdf',b'%PDF'),('xlsx',b'PK')]:
        response=client.get('/api/report/',{'export':format})
        assert response.status_code==200
        data=b''.join(response.streaming_content)
        assert data.startswith(signature)
        print(f'Exportacion {format}: correcta ({len(data)} bytes).')
