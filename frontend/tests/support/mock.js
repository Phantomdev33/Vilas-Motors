const permissions=Object.fromEntries(['equipment','reading','maintenance','supply','alert','user','audit'].map(k=>[k,'CRUD']));
const equipment=[
  {id:1,code:'XLS-0002',name:'GRÚA HORQUILLA',equipment_type:'Grúa horquilla',brand:'KOMATSU',model:'FG20T',serial_number:null,region:'Tarapacá',commune:'Alto Hospicio',active:true,meter_initialized:false,status:'pending',unit:'hrs',interval:250,current_value:'0',initial_value:0,initial_service_value:0,next_service:'250',last_service_value:0,remaining:250,progress:0},
  {id:2,code:'TR-02',name:'Camión',equipment_type:'Camión',region:'Arica y Parinacota',commune:'Arica',active:true,meter_initialized:true,status:'operational',unit:'km',interval:10000,current_value:1000,next_service:10000,remaining:9000,progress:10},
  {id:3,code:'EX-03',name:'Excavadora',equipment_type:'Excavadora',region:'Tarapacá',commune:'Alto Hospicio',active:true,meter_initialized:true,status:'upcoming',unit:'hrs',interval:250,current_value:240,next_service:250,remaining:10,progress:96},
];
const maintenances=[{id:1,equipment:2,equipment_code:'TR-02',equipment_name:'Camión',scheduled_at:'2025-08-01T12:00:00Z',completed_at:null,status:'in_progress',service_type:'Preventiva',value:1000,interval:10000,unit:'km',next_service:11000,registered_by:'Ana',workshop:'Luis',supplies:[]}];
export async function mock(page,loggedIn=true){
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/**',async route=>{
    const path=new URL(route.request().url()).pathname.replace('/api/','');
    let body=[];
    if(path==='auth/csrf/')body={csrfToken:'test-token'};
    else if(path==='auth/captcha/')body={id:'test-captcha',image:'data:image/svg+xml;base64,'+Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="240" height="72"><text x="15" y="40">ABC234</text></svg>').toString('base64')};
    else if(path==='auth/me/'){
      if(!loggedIn)return route.fulfill({status:401,json:{detail:'Sin sesión'}});
      body={id:1,first_name:'Ana',last_name:'Prueba',role:'admin',permissions};
    }
    else if(path==='equipment/')body=equipment;
    else if(path==='users/')body=[{id:1,first_name:'Ana',last_name:'Prueba',email:'ana@example.com',role:'admin',is_active:true,last_login:'2026-11-03T12:00:00Z'}];
    else if(path==='alerts/')body=[{id:1,equipment:3,equipment_code:'EX-03',equipment_name:'Excavadora',equipment_type:'Excavadora',severity:'upcoming',active:true,unit:'hrs',current_value:240,remaining:10,progress:96}];
    else if(path==='maintenances/service-types/')body={options:[{value:'Preventiva',label:'Preventiva'},{value:'Correctiva',label:'Correctiva'},{value:'Preventiva · Servicio de motor',label:'Preventiva · Servicio de motor'}],aliases:{'Preventiva simulada':'Preventiva'}};
    else if(path==='supplies/')body=[{id:1,active:true,description:'Aceite de motor',unit:'litros'}];
    else if(path==='maintenances/')body=maintenances;
    else if(path==='readings/')body=[{id:1,equipment:2,equipment_code:'TR-02',equipment_name:'Camión',recorded_at:'2025-08-01T12:00:00Z',source:'manual',evidence:'/assets/excavator.jpg',value:1000,registered_by:'Ana'},{id:2,equipment:3,equipment_code:'EX-03',recorded_at:'2026-01-01T12:00:00Z',source:'manual',evidence:null,value:240,registered_by:'Ana'}];
    else if(path==='report/')body={equipment,date:'2026-11-03'};
    else if(path.endsWith('/history/'))body={equipment:equipment.find(e=>e.id===Number(path.split('/')[1]))||equipment[0],readings:[],maintenances:[],alerts:[],sensors:[],changes:[{id:1,action:'imported',user_name:'Sistema',created_at:'2026-11-03T12:00:00Z'}]};
    return route.fulfill({json:body});
  });
  return errors;
}
