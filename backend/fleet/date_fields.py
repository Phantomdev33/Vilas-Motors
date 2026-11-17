"""Fechas operativas sin obligar al usuario a introducir horas."""
from datetime import date, datetime, time
import re
from django.utils import timezone
from rest_framework import serializers


class OperationalDateTimeField(serializers.DateTimeField):
    def __init__(self, *args, day_start=False, **kwargs):
        self.day_start = day_start
        super().__init__(*args, **kwargs)

    def to_internal_value(self, value):
        if isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
            try:
                selected = date.fromisoformat(value)
            except ValueError:
                self.fail('invalid',format='YYYY-MM-DD')
            instance = getattr(self.parent,'instance',None)
            original = getattr(instance,self.field_name,None) if instance else None
            if original and timezone.localdate(original)==selected:
                return original
            if not self.day_start and selected==timezone.localdate():
                return timezone.now()
            return timezone.make_aware(datetime.combine(selected,time.min if self.day_start else time.max))
        return super().to_internal_value(value)
