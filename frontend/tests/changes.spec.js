import {test,expect} from '@playwright/test';

const permissions=Object.fromEntries(['equipment','reading','maintenance','supply','alert','user','audit'].map(k=>[k,'CRUD']));
const equipment=[
  {id:1,code:'XLS-0002',name:'GRÚA HORQUILLA',equipment_type:'Grúa horquilla',brand:'KOMATSU',model:'FG20T',serial_number:null,region:'',commune:'',active:true,meter_initialized:false,status:'pending',unit:'hrs',interval:250,current_value:'0',initial_value:0,initial_service_value:0,next_service:'250',last_service_value:0,remaining:250,progress:0},
  {id:2,code:'TR-02',name:'Camión',equipment_type:'Camión',active:true,meter_initialized:true,status:'operational',unit:'km',interval:10000,current_value:1000,next_service:10000,remaining:9000,progress:10},
  {id:3,code:'EX-03',name:'Excavadora',equipment_type:'Excavadora',active:true,meter_initialized:true,status:'upcoming',unit:'hrs',interval:250,current_value:240,next_service:250,remaining:10,progress:96},
];
const maintenances=[{id:1,equipment:2,equipment_code:'TR-02',equipment_name:'Camión',scheduled_at:'2025-08-01T12:00:00Z',completed_at:null,status:'in_progress',service_type:'Preventiva',value:1000,interval:10000,unit:'km',next_service:11000,registered_by:'Ana',workshop:'Luis',supplies:[]}];
async function mock(page,loggedIn=true){
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
    else if(path==='maintenances/')body=maintenances;
    else if(path==='readings/')body=[{id:1,equipment:2,equipment_code:'TR-02',equipment_name:'Camión',recorded_at:'2025-08-01T12:00:00Z',source:'manual',evidence:'/photo.jpg',value:1000,registered_by:'Ana'},{id:2,equipment:3,equipment_code:'EX-03',recorded_at:'2026-01-01T12:00:00Z',source:'manual',evidence:null,value:240,registered_by:'Ana'}];
    else if(path==='report/')body={equipment,date:'2026-11-03'};
    else if(path.endsWith('/history/'))body={equipment:equipment[0],readings:[],maintenances:[],alerts:[],sensors:[],changes:[{id:1,action:'imported',user_name:'Sistema',created_at:'2026-11-03T12:00:00Z'}]};
    return route.fulfill({json:body});
  });
  return errors;
}
test('fleet buttons filter availability and pending equipment',async({page},info)=>{
  const errors=await mock(page);await page.goto('/');
  await page.locator('.fleet-filters').getByRole('button',{name:/En mantención/}).click();
  const table=page.locator('.desktop-table:visible, .mobile-equipment:visible');
  await expect(table.getByText(/TR-02 · Camión/)).toBeVisible();
  await expect(table.getByText(/XLS-0002/)).toHaveCount(0);
  await page.locator('.fleet-filters').getByRole('button',{name:/Equipos activos/}).click();
  await expect(table.getByText(/XLS-0002 · GRÚA/)).toBeVisible();
  await page.screenshot({path:`test-results/updated-fleet-${info.project.name}.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  expect(errors).toEqual([]);
});
test('photo filter finds historic manual photos and year filter works',async({page})=>{
  const errors=await mock(page);await page.goto('/#readings');
  await page.getByLabel('Filtrar fuente',{exact:true}).selectOption('ocr');
  await expect(page.getByAltText('Foto del horómetro')).toBeVisible();
  await expect(page.getByText('Sin foto histórica')).toHaveCount(0);
  await page.getByLabel('Filtrar por año').selectOption('2026');
  await expect(page.getByAltText('Foto del horómetro')).toHaveCount(0);
  expect(errors).toEqual([]);
});
test('maintenance list, units and date controls',async({page},info)=>{
  const errors=await mock(page);await page.goto('/#maintenance');
  await expect(page.getByRole('heading',{name:'REGISTRO DE MANTENCIONES',exact:true})).toBeVisible();
  await expect(page.getByText('Próxima: 11.000 km')).toBeVisible();
  await page.getByLabel('Filtrar por año').selectOption('2025');
  await page.screenshot({path:`test-results/updated-maintenance-${info.project.name}.png`,fullPage:true});
  await page.goto('/#calendar');
  await page.getByLabel('Mes del calendario').fill('2030-12');
  await expect(page.getByRole('heading',{name:'diciembre de 2030'})).toBeVisible();
  await page.getByLabel('Fecha del informe diario').fill('2025-08-01');
  await expect(page.getByRole('heading',{name:'agosto de 2025'})).toBeVisible();
  expect(errors).toEqual([]);
});
test('password recovery and captcha render separately',async({page},info)=>{
  const errors=await mock(page,false);await page.goto('/');
  await expect(page.getByLabel('Código de verificación',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Recuperar mi contraseña',exact:true}).click();
  await expect(page.getByLabel('Correo de recuperación')).toBeVisible();
  await expect(page.getByRole('button',{name:'Ingresar',exact:true})).toBeHidden();
  await page.goto('/?reset=uid&token=secret');
  await expect(page.getByLabel('Nueva contraseña',{exact:true})).toHaveAttribute('minlength','13');
  await expect(page.getByLabel('Confirmar nueva contraseña',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Correo de recuperación')).toHaveCount(0);
  await page.screenshot({path:`test-results/updated-reset-${info.project.name}.png`,fullPage:true});
  expect(errors).toEqual([]);
});
