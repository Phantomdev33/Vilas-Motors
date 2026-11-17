import React from 'react';
import {Wrench,ArrowUpRight,Bell} from 'lucide-react';

const labels={overdue:'Mantención vencida',required:'Mantención requerida',upcoming:'Próxima mantención',pending:'Ficha pendiente'};
const number=value=>value==null?'Sin dato':Number(value).toLocaleString('es-CL',{maximumFractionDigits:2});

export default function NotificationDetail({alert,equipment,can,Modal,onClose,onService,onHistory,onAll}){
  const unit=alert.unit||equipment?.unit||'';
  const canRegister=!!equipment?.active&&equipment.meter_initialized!==false&&alert.active;
  return <Modal title={`Notificación · ${alert.equipment_code}`} onClose={onClose}><article className="notification-detail">
    <div className="notification-detail-heading"><Bell size={24}/><div><span className={`state-badge ${alert.severity}`}>{labels[alert.severity]||alert.severity_label||'Revisar equipo'}</span><h2>{alert.equipment_code} · {alert.equipment_name||equipment?.name}</h2><p>{alert.equipment_type||equipment?.equipment_type}</p></div></div>
    {alert.message&&<p className="notification-message">{alert.message}</p>}
    <dl className="notification-metrics"><div><dt>Lectura actual</dt><dd>{number(alert.current_value)} {unit}</dd></div><div><dt>Próxima mantención</dt><dd>{number(alert.next_service)} {unit}</dd></div><div><dt>{Number(alert.remaining)<0?'Atraso':'Restante'}</dt><dd>{alert.remaining==null?'Sin dato':number(Math.abs(Number(alert.remaining)))} {unit}</dd></div></dl>
    <div className="notification-context"><p><strong>Ubicación:</strong> {[equipment?.region,equipment?.commune].filter(Boolean).join(' · ')||'Sin asignar'}</p>{alert.created_at&&<p><strong>Generada:</strong> {new Date(alert.created_at).toLocaleString('es-CL')}</p>}<p><strong>Estado:</strong> {alert.active?'Pendiente de atención':'Solucionada'}</p></div>
    {!canRegister&&<p className="muted">{!equipment?'El equipo no está disponible en el catálogo.':!equipment.active?'El equipo está inactivo; puedes consultar su historial.':equipment.meter_initialized===false?'Completa los datos iniciales del equipo antes de registrar un servicio.':'Esta alerta ya fue solucionada.'}</p>}
    <div className="form-actions"><button className="vm-button" onClick={onAll}>Ver todas las alertas</button>{equipment&&<button className="vm-button" onClick={onHistory}><ArrowUpRight size={14}/>Ver ficha</button>}{can('maintenance','C')&&<button className="vm-button primary" disabled={!canRegister} onClick={onService}><Wrench size={14}/>Registrar servicio</button>}</div>
  </article></Modal>;
}
