"""Mide consultas GET en una base local aislada; nunca imprime SQL ni secretos."""
import json
import os
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
os.environ['DJANGO_SETTINGS_MODULE']='config.prototype'
import django
django.setup()
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from fleet.models import User,Equipment
client=APIClient();client.force_authenticate(User.objects.filter(role='admin').first())
equipment=Equipment.objects.filter(readings__isnull=False).distinct().first()
paths=['/api/equipment/','/api/readings/','/api/alerts/',f'/api/equipment/{equipment.pk}/history/']
results={}
with override_settings(ALLOWED_HOSTS=['testserver'],SECURE_SSL_REDIRECT=False):
    for path in paths:
        with CaptureQueriesContext(connection) as queries:
            response=client.get(path)
        assert response.status_code==200,(path,response.status_code)
        results[path]=len(queries)
css=sum(f.stat().st_size for f in (root/'frontend'/'dist'/'assets').glob('*.css'))
results['css_bytes']=css
print(json.dumps(results))
