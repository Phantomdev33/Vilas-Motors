"""Selecciona 50 equipos activos variados; conserva intactos los historiales."""
import argparse
import os
from pathlib import Path
import re
import sys
import unicodedata
from collections import defaultdict, Counter

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.db import transaction
from fleet.models import Equipment, AuditLog


def normalized(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', value.upper()) if not unicodedata.combining(c))
    value = value.replace('HORQULLA', 'HORQUILLA').replace('RETRO EXCAVADORA', 'RETROEXCAVADORA')
    return re.sub(r'\b0+(\d)', r'\1', re.sub(r'(?<=\d)(?=[A-Z])', ' ', value)).strip()


def family(equipment):
    kind = normalized(equipment.equipment_type)
    for prefix in ('GRUA HORQUILLA', 'GENERADOR', 'ALZA HOMBRE', 'PLATAFORMA TIJERA'):
        if kind.startswith(prefix):
            return prefix
    return kind


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
with transaction.atomic():
    active = list(Equipment.objects.select_for_update().filter(active=True).order_by('code'))
    if len(active) < 50:
        raise RuntimeError('Hay menos de 50 activos; no se reactivan registros automaticamente.')
    selected = [e for e in active if e.code.startswith('SIM-')]
    if len(selected) > 50:
        raise RuntimeError('Mas de 50 equipos SIM: revisar seleccion.')
    selected_ids = {e.pk for e in selected}
    families = defaultdict(list)
    for e in active:
        if e.pk not in selected_ids:
            families[family(e)].append(e)
    covered = {family(e) for e in selected}
    # Primero una muestra de cada familia que aun no este representada.
    for key in sorted(families):
        if key not in covered and len(selected) < 50:
            e = families[key].pop(0)
            selected.append(e)
            covered.add(key)
    # Luego variantes distintas, repartidas entre familias, antes de duplicados.
    types = {normalized(e.equipment_type) for e in selected}
    for distinct_only in (True, False):
        while len(selected) < 50:
            added = False
            for key in sorted(families):
                candidates = families[key]
                candidate = next((e for e in candidates if not distinct_only or normalized(e.equipment_type) not in types), None)
                if candidate is None:
                    continue
                candidates.remove(candidate)
                selected.append(candidate)
                types.add(normalized(candidate.equipment_type))
                added = True
                if len(selected) == 50:
                    break
            if not added:
                break
    assert len(selected) == 50
    selected_ids = {e.pk for e in selected}
    removed = [e for e in active if e.pk not in selected_ids]
    print('Activos antes:', len(active), 'Seleccionados:', len(selected), 'A desactivar:', len(removed))
    print('Familias:', len({family(e) for e in selected}), 'Tipos normalizados:', len(types))
    print('Distribucion:', dict(sorted(Counter(family(e) for e in selected).items())))
    if args.apply:
        changed = Equipment.objects.filter(pk__in=[e.pk for e in removed], active=True).update(active=False)
        AuditLog.objects.bulk_create([AuditLog(action='prototype_limit', entity='Equipment', entity_id=str(e.pk),
            description='Desactivado para limitar el prototipo a 50 equipos activos; historial conservado.') for e in removed])
        assert changed == len(removed)
        assert Equipment.objects.filter(active=True).count() == 50
        print('Aplicado. Activos: 50. Total conservado:', Equipment.objects.count())
    else:
        print('Vista previa; no se guardaron cambios.')
