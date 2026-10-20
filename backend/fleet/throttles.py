import hashlib
from rest_framework.throttling import SimpleRateThrottle
from .models import Sensor

class DeviceTelemetryThrottle(SimpleRateThrottle):
    """Keep device traffic separate from the anonymous login quota."""
    scope = 'telemetry'
    rate = '120/min'
    def get_cache_key(self, request, view):
        header = request.headers.get('Authorization', '')
        sensor = None
        if header.startswith('Device '):
            token_hash = hashlib.sha256(header[7:].encode()).hexdigest()
            sensor = Sensor.objects.filter(token_hash=token_hash, active=True).values_list('pk', flat=True).first()
        identity = f'device:{sensor}' if sensor else f'anonymous:{self.get_ident(request)}'
        return self.cache_format % {'scope': self.scope, 'ident': identity}
