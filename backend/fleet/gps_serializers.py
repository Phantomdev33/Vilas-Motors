from django.utils import timezone
from rest_framework import serializers


class IgnitionInputSerializer(serializers.Serializer):
    event_id = serializers.CharField(max_length=128)
    recorded_at = serializers.DateTimeField()
    ignition = serializers.BooleanField()

    def validate(self, attrs):
        if set(self.initial_data) - {'event_id','recorded_at','ignition'}:
            raise serializers.ValidationError('Campos admitidos: event_id, recorded_at e ignition.')
        if any(key in self.initial_data for key in ('value','confidence','evidence','source','equipment','simulated')):
            raise serializers.ValidationError('Envía solo event_id, recorded_at e ignition; no se admiten lecturas OCR ni valores de horómetro externos.')
        raw = self.initial_data.get('recorded_at','')
        if isinstance(raw,str) and not (raw.endswith('Z') or '+' in raw[10:] or '-' in raw[10:]):
            raise serializers.ValidationError({'recorded_at':'Incluye zona horaria (Z u offset).'})
        if attrs['recorded_at'] > timezone.now():
            raise serializers.ValidationError({'recorded_at':'La fecha no puede estar en el futuro.'})
        return attrs
