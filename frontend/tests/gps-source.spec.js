import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('GPS estimates are labeled as simulated and cannot be edited as manual readings',async({page})=>{
  const errors=await mock(page);
  await page.route('**/api/readings/',route=>route.fulfill({json:[
    {id:1,equipment:3,equipment_code:'EX-03',equipment_name:'Excavadora',value:241,recorded_at:'2026-11-16T12:00:00Z',source:'sensor',is_estimated:true,is_simulated:true,evidence:null,registered_by:'GPS simulado'},
    {id:2,equipment:2,equipment_code:'TR-02',equipment_name:'Camión',value:1000,recorded_at:'2026-11-16T12:00:00Z',source:'manual',evidence:'/assets/excavator.jpg',registered_by:'Ana'},
  ]}));
  await page.goto('/#readings');
  await expect(page.getByLabel('Filtrar fuente').locator('option[value="ocr"]')).toHaveCount(0);
  await page.getByLabel('Filtrar fuente').selectOption('sensor');
  const row=page.locator('.readings-table tbody tr');
  await expect(row).toHaveCount(1);
  await expect(row).toContainText('GPS simulado · estimado');
  await expect(row.getByRole('button',{name:'Editar',exact:true})).toHaveCount(0);
  await page.getByLabel('Filtrar fuente').selectOption('photo');
  await expect(row).toHaveCount(1);
  await expect(row).toContainText('Manual');
  await expect(row.getByRole('button',{name:'Editar',exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});

test('equipment history explains ignition estimates and simulated device state',async({page})=>{
  const errors=await mock(page);
  await page.route('**/api/equipment/3/history/',route=>route.fulfill({json:{
    equipment:{id:3,code:'EX-03',name:'Excavadora',equipment_type:'Excavadora',active:true,unit:'hrs',interval:250,meter_initialized:true,current_value:241,last_service_value:0,next_service:250,remaining:9,progress:96,status:'upcoming'},
    gps:[{device:'SIM-FMB120-EX-03',model:'Teltonika FMB120',counted_seconds:10800,skipped_seconds:0,simulated:true,ignition:false,last_at:'2026-11-16T12:00:00Z'}],
    readings:[],maintenances:[],alerts:[],changes:[],sensors:[],
  }}));
  await page.goto('/#detail');
  await page.getByLabel('Buscar ficha por código, nombre o serie').fill('EX-03');
  await page.getByRole('button',{name:'Ver ficha e historial'}).click();
  const detail=page.getByRole('dialog',{name:'Ficha e historial · EX-03'});
  await expect(detail.getByRole('heading',{name:'GPS · Teltonika FMB120'})).toBeVisible();
  await expect(detail).toContainText('DATOS SIMULADOS');
  await expect(detail).toContainText('3 horas estimadas desde la referencia');
  await page.screenshot({path:`test-results/gps-simulation-${test.info().project.name}.png`,fullPage:true});
  expect(errors).toEqual([]);
});
