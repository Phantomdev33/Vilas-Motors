import React,{useState,useEffect,useRef} from 'react';
import {Bell,ChevronRight,X} from 'lucide-react';

const labels={overdue:'Mantención vencida',required:'Mantención requerida',upcoming:'Próxima mantención',pending:'Ficha pendiente'};
export default function Notifications({alerts,navigate}){
  const [open,setOpen]=useState(false),ref=useRef(null),button=useRef(null);
  const priority={overdue:0,required:1,upcoming:2,pending:3};
  const active=alerts.filter(a=>a.active).sort((a,b)=>(priority[a.severity]??4)-(priority[b.severity]??4)||b.id-a.id);
  useEffect(()=>{if(!open)return;const outside=e=>{if(!ref.current?.contains(e.target))setOpen(false);};const key=e=>{if(e.key==='Escape'){setOpen(false);button.current?.focus();}};document.addEventListener('pointerdown',outside);document.addEventListener('keydown',key);return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',key);};},[open]);
  const showAlerts=()=>{setOpen(false);navigate('alerts');};
  return <div className="notification-control" ref={ref}><button ref={button} className="icon-button notification-trigger" aria-label={`Notificaciones: ${active.length} alertas activas`} aria-expanded={open} aria-controls="notifications-panel" onClick={()=>setOpen(v=>!v)}><Bell size={18}/>{active.length>0&&<span className="notification-count" aria-hidden="true">{active.length>99?'99+':active.length}</span>}</button>
    {open&&<section id="notifications-panel" className="notifications-panel" aria-label="Notificaciones"><header><div><h2>Notificaciones</h2><p>Resumen de alertas activas</p></div><span className="notification-total">{active.length}</span><button className="icon-button" aria-label="Cerrar notificaciones" onClick={()=>setOpen(false)}><X size={16}/></button></header>
      <div className="notification-list">{active.slice(0,5).map(a=><button className="notification-item" key={a.id} onClick={showAlerts}><span className={`notification-dot ${a.severity}`}/><span><strong>{a.equipment_code}</strong><small>{labels[a.severity]||'Revisar equipo'}</small></span><ChevronRight size={15}/></button>)}{!active.length&&<p className="notifications-empty">No hay alertas activas.</p>}</div>
      <button className="vm-button notifications-view-all" onClick={showAlerts}>Ver todas las alertas{active.length>5?` (${active.length})`:''}<ChevronRight size={14}/></button>
    </section>}
  </div>;
}
