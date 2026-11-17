import React,{useEffect,useState} from 'react';

export function useVehicleChoice(equipment){
  const [choice,setChoice]=useState('');
  const value=equipment.some(e=>String(e.id)===choice)?choice:'';
  useEffect(()=>{if(choice&&!value)setChoice('');},[choice,value]);
  return [value,setChoice];
}

export function VehicleSelect({equipment,value,onChange,label='Filtrar vehículo'}){
  return <select aria-label={label} value={value} disabled={!equipment.length} onChange={e=>onChange(e.target.value)}><option value="">{equipment.length?'Todos los vehículos coincidentes':'Sin vehículos coincidentes'}</option>{equipment.map(e=><option key={e.id} value={String(e.id)}>{e.code} · {e.name}</option>)}</select>;
}

export function useEquipmentScope(equipment){
  const [region,setRegion]=useState(''),[type,setType]=useState('');
  const candidates=equipment.filter(e=>(!region||e.region===region)&&(!type||e.equipment_type===type));
  const [vehicle,setVehicle]=useVehicleChoice(candidates);
  return {region,setRegion,type,setType,vehicle,setVehicle,candidates,
    ids:new Set(candidates.filter(e=>!vehicle||String(e.id)===vehicle).map(e=>e.id)),
    clear:()=>{setRegion('');setType('');setVehicle('');}};
}

export function EquipmentScopeFilters({equipment,scope,label}){
  return <><select aria-label={`Filtrar región de ${label}`} value={scope.region} onChange={e=>scope.setRegion(e.target.value)}><option value="">Todas las regiones</option>{[...new Set(equipment.map(e=>e.region).filter(Boolean))].sort().map(r=><option key={r}>{r}</option>)}</select><select aria-label={`Filtrar tipo de ${label}`} value={scope.type} onChange={e=>scope.setType(e.target.value)}><option value="">Todos los tipos de vehículo</option>{[...new Set(equipment.map(e=>e.equipment_type).filter(Boolean))].sort().map(t=><option key={t}>{t}</option>)}</select><VehicleSelect label={`Filtrar ${label} por equipo`} equipment={scope.candidates} value={scope.vehicle} onChange={scope.setVehicle}/></>;
}
