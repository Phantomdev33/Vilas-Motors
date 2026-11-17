"""Eventos normalizados FMB120. No decodifica TCP ni cambia el GPS físico."""
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Equipment, Sensor, Reading, IgnitionEvent, GPSMeterState
from .services import audit, reconcile_alert


@transaction.atomic
def ingest_ignition(sensor, event_id, recorded_at, ignition, simulated=False):
    equipment = Equipment.objects.select_for_update().get(pk=sensor.equipment_id)
    sensor = Sensor.objects.select_for_update().get(pk=sensor.pk)
    if not sensor.active or not equipment.active or sensor.model != 'Teltonika FMB120' or sensor.sensor_type != 'GPS':
        raise ValidationError('Se requiere un GPS FMB120 activo vinculado a un equipo activo.')
    existing = IgnitionEvent.objects.filter(sensor=sensor, event_id=event_id).first()
    same_time = IgnitionEvent.objects.filter(sensor=sensor, recorded_at=recorded_at).first()
    if existing or same_time:
        existing = existing or same_time
        if existing.recorded_at != recorded_at or existing.ignition != ignition or existing.simulated != simulated:
            raise ValidationError('El evento o su fecha ya existe con otros datos.')
        return existing, False
    state = GPSMeterState.objects.filter(sensor=sensor).first()
    latest = equipment.readings.order_by('-recorded_at', '-id').first()
    event = IgnitionEvent.objects.create(sensor=sensor, event_id=event_id,
        recorded_at=recorded_at, ignition=ignition, simulated=simulated)
    # Un paquete atrasado se conserva para auditoría, pero no altera el medidor.
    if (state and recorded_at <= state.last_at) or (latest and recorded_at <= latest.recorded_at):
        event.outcome = 'late'
        event.save(update_fields=['outcome'])
        audit(None, 'gps_late_event', event)
        return event, True
    if state is None:
        GPSMeterState.objects.create(sensor=sensor, last_at=recorded_at, ignition=ignition,
            baseline_value=equipment.current_value)
        audit(None, 'gps_anchor', event)
        return event, True
    start = state.last_at
    # Una lectura manual posterior recalibra la referencia; no se suma dos veces.
    if latest and latest.recorded_at > start:
        state.baseline_value = latest.value
        state.counted_seconds = 0
        start = latest.recorded_at
    elapsed = int((recorded_at - start).total_seconds())
    full_gap = (recorded_at - state.last_at).total_seconds()
    if full_gap > settings.GPS_MAX_EVENT_GAP_SECONDS:
        state.skipped_seconds += elapsed
        event.outcome = 'gap'
    else:
        event.outcome = 'estimated'
        event.counted_seconds = elapsed if state.ignition else 0
        state.counted_seconds += event.counted_seconds
    state.last_at, state.ignition = recorded_at, ignition
    state.save()
    if event.counted_seconds and equipment.unit == 'hrs' and equipment.meter_initialized:
        value = (state.baseline_value + Decimal(state.counted_seconds) / Decimal(3600)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if value > equipment.current_value:
            event.reading = Reading.objects.create(equipment=equipment, sensor=sensor, value=value,
                recorded_at=recorded_at, source='sensor',
                note=('SIMULACIÓN · ' if simulated else '')+'Horas estimadas por encendido GPS Teltonika FMB120; no es una lectura física del motor.')
            # La propiedad current_value pudo consultarse antes de crear la lectura.
            for key in ('current_value','remaining','progress','status'):
                equipment.__dict__.pop(key, None)
            reconcile_alert(equipment)
    event.save(update_fields=['outcome','counted_seconds','reading'])
    audit(None, 'gps_simulated_event' if simulated else 'gps_ignition_event', event)
    return event, True
