"""Published examples for the exact models used in the prototype."""

REFERENCES = [
    dict(equipment_type='Excavadora', brand='CAT', model='320', unit='hrs', interval=500,
         scope='Aceite y filtro de motor, según prefijo de serie.',
         source='https://www.cat.com/en_ID/support/caterpillar-service-center/cat-320-320GC-323-maintenance-and-service.html'),
    dict(equipment_type='Excavadora', brand='Komatsu', model='PC210-10M0', unit='hrs', interval=250,
         scope='Primer servicio programado en KomCare. La pauta incluye hitos posteriores.',
         source='https://www.komatsu.com/content/dam/komatsu/websites/south-africa/documents/brochures/komcare-pc210-10m0.pdf'),
    dict(equipment_type='Cargador frontal', brand='Volvo', model='L120H', unit='hrs', interval=1000,
         scope='Aceite de motor con VDS-4.5 y filtro de alto rendimiento, o 12 meses, lo que ocurra primero.',
         source='https://www.volvoce.com/en-us/about-us/news/2021/volvo-construction-equipment-extends-oil-change-intervals-to-1000-hours/'),
    dict(equipment_type='Camioneta', brand='Toyota', model='Hilux', unit='km', interval=10000,
         scope='Pauta chilena de la mantención de 10.000 km.',
         source='https://tienda.toyota.cl/index.php?controller=product&id_product=442&id_product_attribute=5615&rewrite=mantencion-hilux'),
    dict(equipment_type='Minicargador', brand='Bobcat', model='S650', unit='hrs', interval=500,
         scope='Aceite y filtro de motor Bobcat Tier 4, o 12 meses. Confirma la variante y la pauta de uso severo.',
         source='https://assets.bobcat.com/parts-accessories/service-maintenance-schedules/ss-ssl-sf-mf-exmf-t4-b-0315.pdf'),
    dict(equipment_type='Retroexcavadora', brand='JCB', model='3CX Compact', unit='hrs', interval=500,
         scope='Intervalo de servicio publicado para la variante Compact.',
         source='https://www.jcb.com/en-US/products/machines/backhoe-loaders/3cx-compact/'),
    dict(equipment_type='Compresor', brand='Atlas Copco', model='XAS 38', unit='hrs', interval=250,
         scope='Aceite y filtro del motor, o un año. Primer cambio a las 50 horas.',
         source='https://www.atlascopco.com/content/dam/atlas-copco/local-countries/france/documents/power-technique-france/ape/page-web-liens-utiles-compresseurs/petits-compresseurs-2-%C3%A0-5m%C2%B3/manuels-d%27utilisateurs/Manuel%20Utilisateur%20XAS%2038-48.pdf'),
    dict(equipment_type='Plataforma tijera', brand='Genie', model='GS3246', unit='hrs', interval=250,
         scope='Filtro de retorno hidráulico en el manual 48339. Las inspecciones por calendario siguen su propia pauta.',
         source='https://manuals.genielift.com/Parts%20And%20Service%20Manuals/data/Service/Scissors/48339.pdf'),
]


def service_reference(kind, brand, model, unit):
    def normalize(value):
        return ''.join(character for character in value.casefold() if character.isalnum())

    key = tuple(map(normalize, (kind, brand, model, unit)))
    for item in REFERENCES:
        reference_key = tuple(map(normalize, (item['equipment_type'], item['brand'], item['model'], item['unit'])))
        if key == reference_key:
            return item
    return None
