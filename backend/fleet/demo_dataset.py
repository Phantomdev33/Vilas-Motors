"""Datos operacionales íntegramente ficticios para la entrega académica."""
import hashlib
import secrets
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from .models import Equipment,Sensor,Reading,Maintenance,Supply,MaintenanceSupply,Alert,AuditLog,Gateway,IgnitionEvent,GPSMeterState

TYPES = [
 ('Grúa horquilla','Komatsu','FG25','hrs'),('Camión tolva','Volvo','FMX','km'),
 ('Excavadora','CAT','320','hrs'),('Cargador frontal','Volvo','L120H','hrs'),
 ('Grúa móvil','Liebherr','LTM','hrs'),('Camioneta','Toyota','Hilux','km'),
 ('Retroexcavadora','JCB','3CX','hrs'),('Camión pluma','Mercedes-Benz','Arocs','km'),
 ('Camión aljibe','Scania','P410','km'),('Minicargador','Bobcat','S650','hrs'),
 ('Generador','Cummins','C80','hrs'),('Luminaria','Atlas Copco','HiLight','hrs'),
 ('Compresor','Atlas Copco','XAS','hrs'),('Rodillo compactador','Hamm','3411','hrs'),
 ('Motoniveladora','CAT','140','hrs'),('Manipulador telescópico','Manitou','MT1840','hrs'),
 ('Minibús','Mercedes-Benz','Sprinter','km'),('Furgón','Hyundai','Staria','km'),
 ('Tracto camión','Volvo','FH','km'),('Plataforma tijera','Genie','GS3246','hrs'),
 ('Alza hombre articulado','JLG','450AJ','hrs'),('Camión combustible','Scania','P360','km'),
 ('Camión lubricador','Mercedes-Benz','Atego','km'),('Camión rescate','Iveco','Tector','km'),
 ('Camión plataforma','Volvo','VM','km'),('Soldadora','Lincoln','Vantage','hrs'),
 ('Luminaria solar','Generica','LS400','hrs'),('Miniexcavadora','Kubota','U55','hrs'),
 ('Grúa horquilla eléctrica','Toyota','8FB','hrs'),('Camión plano','Hino','500','km'),
 ('Cama baja','Generica','CB40','km'),('Semirremolque','Generica','SR30','km'),
 ('Rampla','Generica','RP30','km'),('Camión pantalla','Iveco','Daily','km'),
 ('Alza hombre telescópico','Genie','S65','hrs'),
]
REGIONS=[('Arica y Parinacota','Arica'),('Tarapacá','Alto Hospicio'),('Antofagasta','Calama'),('Atacama','Copiapó'),('Coquimbo','La Serena')]
NOTE='DATOS SIMULADOS · Prototipo académico para demostración. No corresponde a un activo real.'
OPERATIONAL=(IgnitionEvent,GPSMeterState,Alert,MaintenanceSupply,Maintenance,Reading,Sensor,Gateway,Equipment,Supply)


def populate(actor):
    now=timezone.now()
    supplies=Supply.objects.bulk_create([Supply(code=f'SIM-INS-{i+1:03}',description=name,unit=unit) for i,(name,unit) in enumerate([
      ('Aceite motor 15W40','litros'),('Filtro de aceite','unidad'),('Filtro de aire','unidad'),('Filtro combustible','unidad'),
      ('Grasa multipropósito','kg'),('Refrigerante','litros'),('Aceite hidráulico','litros'),('Correa de motor','unidad'),
      ('Pastillas de freno','juego'),('Aceite transmisión','litros'),('Manguera hidráulica','unidad'),('Batería','unidad'),
      ('Líquido de frenos','litros'),('Kit sellos','juego'),('Fusible','unidad'),('Ampolleta','unidad'),
      ('Neumático','unidad'),('Perno','unidad'),('Limpiador industrial','litros'),('Rodamiento','unidad')])])
    equipment=[]
    for i in range(50):
        kind,brand,model,unit=TYPES[i%len(TYPES)]
        region,commune=REGIONS[i%5]
        interval=10000 if unit=='km' else 250 if i%2==0 else 500
        base=Decimal(interval*10)
        pending=i>=48
        equipment.append(Equipment(code=f'SIM-{i+1:03}',name=f'{kind} {brand} {model}',equipment_type=kind,
          brand=brand,model=model,serial_number=None if pending else f'SIM-SERIE-{i+1:04}',
          region=region,commune=commune,location=f'Faena simulada {i%8+1}',responsible=f'Operador simulado {i%12+1:02}',
          unit=unit,interval=interval,initial_value=0 if pending else base-Decimal(interval)/2,
          initial_service_value=0 if pending else base-interval,meter_initialized=not pending,
          import_notes=NOTE,updated_by=actor))
    Equipment.objects.bulk_create(equipment)
    sensors=Sensor.objects.bulk_create([Sensor(equipment=e,identifier=f'SIM-FMB120-{i+1:03}',sensor_type='GPS',model='Teltonika FMB120',
      token_hash=hashlib.sha256(secrets.token_bytes(32)).hexdigest()) for i,e in enumerate(equipment)])
    readings=[];services=[];gps_rows=[];states=[];resolved=[];associations=[];logs=[]
    ratios=[Decimal(x) for x in ('0.30','0.55','0.90','1.00','1.12','0.20','0.86','1.24','0.60','0.40')]
    for i,(e,sensor) in enumerate(zip(equipment,sensors)):
        base=Decimal(e.interval*10);delta=Decimal(e.interval)*ratios[i%10]
        current=base+delta
        logs.append(AuditLog(user=actor,action='simulated_equipment_created',entity='Equipment',entity_id=str(e.pk),description=NOTE))
        if not e.meter_initialized:
            continue
        if e.meter_initialized:
            last_manual=current-(3 if e.unit=='hrs' else 0)
            for days,value in [(40,e.initial_value),(25,base-Decimal(e.interval)*Decimal('.3')),(12,base-Decimal(e.interval)*Decimal('.05')),
                (10,base),(6,base+delta/4),(4,base+delta/2),(2,base+delta*Decimal('.8')),(1,last_manual)]:
                readings.append(Reading(equipment=e,value=value.quantize(Decimal('.01')),recorded_at=now-timedelta(days=days),source='manual',note=NOTE,created_by=actor))
            closed=Maintenance(equipment=e,service_type='Preventiva · Servicio de motor',interval=e.interval,value=base,
                scheduled_at=now-timedelta(days=10,hours=2),completed_at=now-timedelta(days=10),status='completed',
                workshop='Taller simulado central',work_order=f'SIM-OT-{i+1:03}-C',description='SIMULADO · Cambio de aceite y filtros, revisión de seguridad.',created_by=actor)
            services.append(closed)
            resolved.append((e,closed,base))
            gps_readings={}
            if e.unit=='hrs':
                for hours,increment in [(6,2),(4,3)]:
                    item=Reading(equipment=e,sensor=sensor,value=last_manual+increment,recorded_at=now-timedelta(hours=hours),source='sensor',
                        note='SIMULACIÓN · Horas estimadas por encendido GPS Teltonika FMB120; no es una lectura física del motor.')
                    readings.append(item);gps_readings[hours]=item
            for index,(hours,on,seconds) in enumerate([(8,True,0),(6,False,7200),(5,True,0),(4,False,3600)]):
                gps_rows.append(IgnitionEvent(sensor=sensor,event_id=f'entrega-{e.code}-{index}',recorded_at=now-timedelta(hours=hours),ignition=on,
                    simulated=True,outcome='anchor' if index==0 else 'estimated',counted_seconds=seconds,reading=gps_readings.get(hours)))
            states.append(GPSMeterState(sensor=sensor,last_at=now-timedelta(hours=4),ignition=False,baseline_value=last_manual,counted_seconds=10800))
        status='draft' if not e.meter_initialized or i%10==8 else 'in_progress' if i%10==5 else 'cancelled' if i%10==9 else 'scheduled'
        services.append(Maintenance(equipment=e,service_type='Correctiva' if i%3==0 else 'Preventiva',interval=e.interval,value=current if e.meter_initialized else 0,
            scheduled_at=now-timedelta(days=1) if status=='in_progress' else now+timedelta(days=i%7),status=status,workshop=f'Taller simulado {i%4+1}',
            work_order=f'SIM-OT-{i+1:03}-P',description='SIMULADO · Revisión programada para demostrar el flujo de mantención.',created_by=actor))
        services.append(Maintenance(equipment=e,service_type='Preventiva · Servicio de motor',interval=e.interval,value=current if e.meter_initialized else 0,
            scheduled_at=now+timedelta(days=30+i%10),status='scheduled',workshop='Taller simulado norte',work_order=f'SIM-OT-{i+1:03}-F',
            description='SIMULADO · Próxima intervención de planificación mensual.',created_by=actor))
    Reading.objects.bulk_create(readings)
    Maintenance.objects.bulk_create(services)
    GPSMeterState.objects.bulk_create(states)
    IgnitionEvent.objects.bulk_create(gps_rows)
    for i,service in enumerate(services):
        if service.status not in ('draft','cancelled'):
            associations.append(MaintenanceSupply(maintenance=service,supply=supplies[i%len(supplies)],quantity=2))
            associations.append(MaintenanceSupply(maintenance=service,supply=supplies[(i+1)%len(supplies)],quantity=1))
        logs.append(AuditLog(user=actor,action='simulated_service_created',entity='Maintenance',entity_id=str(service.pk),description=NOTE))
    MaintenanceSupply.objects.bulk_create(associations)
    historical=[]
    for e,service,base in resolved:
        historical.append(Alert(equipment=e,maintenance=service,severity='required',message=f'SIMULADO · {e.code}: mantención anterior requerida, solucionada con {service.work_order}.',active=False,attended_at=service.completed_at))
    Alert.objects.bulk_create(historical)
    for alert in historical:
        alert.created_at=now-timedelta(days=12)
    Alert.objects.bulk_update(historical,['created_at'])
    # Las alertas actuales se calculan desde el estado que realmente producirá la API.
    active_alerts=[]
    for e in equipment:
        if e.meter_initialized:
            ratio=ratios[(int(e.code.split('-')[1])-1)%10]
            severity='overdue' if ratio>1 else 'required' if ratio==1 else 'upcoming' if ratio>=Decimal('.85') else None
            if severity:
                label={'overdue':'vencida','required':'requerida','upcoming':'próxima'}[severity]
                active_alerts.append(Alert(equipment=e,severity=severity,message=f'SIMULADO · {e.code}: mantención {label}. Próxima referencia: {e.interval*11} {e.unit}.'))
    Alert.objects.bulk_create(active_alerts)
    for alert in historical+active_alerts:
        logs.append(AuditLog(user=actor,action='alert_attended' if not alert.active else 'alert_created',entity='Alert',entity_id=str(alert.pk),description=NOTE))
    AuditLog.objects.bulk_create(logs)
    return {model.__name__:model.objects.count() for model in [Equipment,Reading,Maintenance,Supply,MaintenanceSupply,Alert,Sensor,IgnitionEvent,GPSMeterState]}
