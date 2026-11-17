import {useRegionTypes} from './EquipmentFilters';
import React,{useState,useEffect} from 'react';
import {Search,ArrowUpRight,Pencil,ChevronLeft,ChevronRight,X} from 'lucide-react';

export default function TechnicalRegistry({equipment,can,navigate}){
  const [search,setSearch]=useState(''),[region,setRegion]=useState(''),[type,setType]=useState(''),[vehicle,setVehicle]=useState(''),[inactive,setInactive]=useState(false),[page,setPage]=useState(0);
  useEffect(()=>setPage(0),[search,region,type,vehicle,inactive]);
  const pool=equipment.filter(e=>inactive||e.active);
  const types=useRegionTypes(pool,region,type,setType);
  const matching=equipment.filter(e=>(inactive||e.active)&&`${e.code} ${e.name} ${e.serial_number||''}`.toLowerCase().includes(search.toLowerCase())&&(!region||e.region===region)&&(!type||e.equipment_type===type));
  const selectedVehicle=matching.some(e=>String(e.id)===vehicle)?vehicle:'';
  useEffect(()=>{if(vehicle&&!selectedVehicle)setVehicle('');},[vehicle,selectedVehicle]);
  const rows=matching.filter(e=>!selectedVehicle||String(e.id)===selectedVehicle);
  const count=Math.max(1,Math.ceil(rows.length/15)),index=Math.min(page,count-1),visible=rows.slice(index*15,(index+1)*15);
  return <><div className="page-heading"><div><h1>FICHAS TÉCNICAS E HISTORIALES</h1><p>Consulta todos los equipos y completa los datos de cada ficha.</p></div></div>
    <div className="toolbar"><label className="search-control"><Search size={15}/><input aria-label="Buscar ficha por código, nombre o serie" placeholder="Buscar código, nombre o serie" value={search} onChange={e=>setSearch(e.target.value)}/></label>
      <select aria-label="Filtrar región de fichas" value={region} onChange={e=>setRegion(e.target.value)}><option value="">Todas las regiones</option>{[...new Set(pool.map(e=>e.region).filter(Boolean))].sort().map(r=><option key={r}>{r}</option>)}</select>
      <select aria-label="Filtrar tipo de ficha" value={type} onChange={e=>setType(e.target.value)}><option value="">Todos los tipos de vehículo</option>{types.map(t=><option key={t}>{t}</option>)}</select>
      <select aria-label="Filtrar vehículo de fichas" value={selectedVehicle} disabled={!matching.length} onChange={e=>setVehicle(e.target.value)}><option value="">{matching.length?'Todos los vehículos coincidentes':'Sin vehículos coincidentes'}</option>{matching.map(e=><option key={e.id} value={String(e.id)}>{e.code} · {e.name}</option>)}</select>
      <button className="vm-button" onClick={()=>{setSearch('');setRegion('');setType('');setVehicle('');setInactive(false);setPage(0);}}><X size={14}/>Limpiar filtros</button>
      <label><input type="checkbox" checked={inactive} onChange={e=>setInactive(e.target.checked)}/> Mostrar equipos anteriores / inactivos</label>
    </div>
    <section className="panel"><div className="table-responsive"><table className="vm-table"><thead><tr><th>EQUIPO</th><th>DATOS DE LA FICHA</th><th>UBICACIÓN</th><th>ACCIONES</th></tr></thead><tbody>{visible.map(e=>{
      const missing=[!e.serial_number&&'serie',!e.brand&&'marca',!e.model&&'modelo',!e.region&&'región',!e.commune&&'comuna',!e.meter_initialized&&'lecturas iniciales'].filter(Boolean);
      return <tr key={e.id}><td><strong>{e.code} · {e.name}</strong><small>{e.equipment_type}{!e.active?' · Inactivo':''}</small></td><td>{missing.length?<><span className="orange-text">Datos por completar</span><small>{missing.join(', ')}</small></>:<span className="green-text">Datos principales completos</span>}<small>Serie: {e.serial_number||'Pendiente'}</small></td><td>{e.region||'Sin región'}<small>{e.commune||'Sin comuna'}</small></td><td><div className="equipment-row-actions"><button className="vm-button equipment-consult" onClick={()=>navigate('detail',e.id)}><ArrowUpRight size={14}/>Ver ficha e historial</button>{can('equipment','U')&&<button className="vm-button equipment-edit" onClick={()=>navigate('equipment-edit',e.id)}><Pencil size={14}/>Completar datos</button>}</div></td></tr>;
    })}</tbody></table></div>{!rows.length&&<div className="empty-state">No hay equipos para los filtros seleccionados.</div>}
      {rows.length>0&&<nav className="fleet-pagination" aria-label="Paginación de fichas"><span>{index*15+1}–{Math.min((index+1)*15,rows.length)} de {rows.length} equipos</span><div><button className="vm-button" aria-label="Página anterior" disabled={!index} onClick={()=>setPage(index-1)}><ChevronLeft size={14}/>Anterior</button><span>Página {index+1} de {count}</span><button className="vm-button" aria-label="Página siguiente" disabled={index+1===count} onClick={()=>setPage(index+1)}>Siguiente<ChevronRight size={14}/></button></div></nav>}
    </section></>;
}
