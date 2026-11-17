import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('manual entry and editing use date-only calendars and send dates without UTC shifts',async({page})=>{
  const errors=await mock(page);await page.goto('/#readings');
  await page.getByRole('button',{name:'Ingreso manual',exact:true}).click();
  const dialog=page.getByRole('dialog');
  const field=dialog.getByLabel('Fecha de lectura *',{exact:true});
  await expect(field).toHaveAttribute('type','date');
  await expect(dialog.locator('input[type="datetime-local"]')).toHaveCount(0);
  await field.fill('2026-01-02');
  await dialog.getByLabel('Equipo *',{exact:true}).selectOption('2');
  await dialog.getByLabel('Valor de horómetro *',{exact:true}).fill('1001');
  let body;
  await page.route('**/api/readings/',route=>{
    if(route.request().method()==='POST'){body=route.request().postData();return route.fulfill({status:201,json:{id:9}});}
    return route.fallback();
  });
  await dialog.getByRole('button',{name:'Guardar lectura',exact:true}).click();
  await expect(dialog).toHaveCount(0);
  expect(body).toContain('2026-01-02');
  expect(body).not.toContain('2026-01-02T');
  await page.locator('.readings-table').getByRole('button',{name:'Editar',exact:true}).first().click();
  await expect(page.getByRole('dialog').getByLabel('Fecha de lectura *',{exact:true})).toHaveAttribute('type','date');
  await page.screenshot({path:`test-results/date-only-reading-${test.info().project.name}.png`,fullPage:true});
  expect(errors).toEqual([]);
});

test('dependent selectors exclude inactive vehicles unless historical records are requested',async({page})=>{
  const errors=await mock(page);
  await page.route('**/api/equipment/',route=>route.fulfill({json:[
    {id:1,code:'OLD-01',name:'Anterior',equipment_type:'Tipo antiguo',region:'Region antigua',active:false,unit:'hrs'},
    {id:2,code:'TR-02',name:'Camión',equipment_type:'Camión',region:'Norte',active:true,unit:'km'},
    {id:3,code:'EX-03',name:'Excavadora',equipment_type:'Excavadora',region:'Norte',active:true,unit:'hrs'},
  ]}));
  await page.goto('/#readings');
  const vehicles=page.getByLabel('Filtrar lecturas por equipo');
  await expect(vehicles.locator('option')).toHaveCount(3);
  await expect(vehicles.getByRole('option',{name:/OLD-01/})).toHaveCount(0);
  await expect(page.getByLabel('Filtrar región de lecturas').getByRole('option',{name:'Region antigua'})).toHaveCount(0);
  await page.getByLabel('Mostrar equipos anteriores / inactivos').check();
  await expect(vehicles.locator('option')).toHaveCount(4);
  await vehicles.selectOption('1');
  await page.getByLabel('Mostrar equipos anteriores / inactivos').uncheck();
  await expect(vehicles).toHaveValue('');
  await expect(vehicles.locator('option')).toHaveCount(3);
  await page.getByRole('button',{name:'Ingreso manual',exact:true}).click();
  await expect(page.getByRole('dialog').getByLabel('Equipo *',{exact:true}).getByRole('option',{name:/OLD-01/})).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('maintenance calendars request only dates',async({page})=>{
  await mock(page);await page.goto('/#fleet');
  if(test.info().project.name==='desktop') await page.locator('.desktop-table').getByRole('button',{name:'Registrar mantención',exact:true}).first().click();
  else {await page.locator('.mobile-card').first().click();await page.getByRole('dialog').getByRole('button',{name:'Registrar mantención',exact:true}).click();}
  const dialog=page.getByRole('dialog');
  await expect(dialog.getByLabel('Inicio del servicio *',{exact:true})).toHaveAttribute('type','date');
  await expect(dialog.getByLabel('Fecha de finalización *',{exact:true})).toHaveAttribute('type','date');
  await expect(dialog.locator('input[type="datetime-local"]')).toHaveCount(0);
});
