// Compatibilidad durante despliegues con una API anterior al catálogo.
export const maintenanceTypes = {
  options: ['Preventiva', 'Preventiva · Servicio de motor', 'Correctiva'].map(value=>({value,label:value})),
  aliases: {'Preventiva simulada':'Preventiva'},
};
