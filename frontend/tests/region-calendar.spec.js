import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

for(const [screen,regionLabel,typeLabel] of [
  ['fleet','Filtrar región de flota','Filtrar tipo de equipo'],
  ['equipment','Filtrar región','Filtrar tipo de vehículo'],
  ['detail','Filtrar región de fichas','Filtrar tipo de ficha'],
  ['readings','Filtrar región de lecturas','Filtrar tipo de lecturas'],
  ['maintenance','Filtrar región de mantenciones','Filtrar tipo de mantenciones'],
  ['alerts','Filtrar región de alertas','Filtrar tipo de alertas'],
]){
  test(`types cascade from region in ${screen} and invalid selection clears`,async({page})=>{
    const errors=await mock(page);await page.goto(`/#${screen}`);
    const region=page.getByLabel(regionLabel,{exact:true}),type=page.getByLabel(typeLabel,{exact:true});
    await expect(type.locator('option')).toHaveCount(4);
    await type.selectOption('Camión');
    await region.selectOption('Tarapacá');
    await expect(type).toHaveValue('');
    await expect(type.locator('option')).toHaveCount(3);
    await expect(type.getByRole('option',{name:'Camión',exact:true})).toHaveCount(0);
    await type.selectOption('Excavadora');
    await region.selectOption('Arica y Parinacota');
    await expect(type).toHaveValue('');
    await expect(type.locator('option')).toHaveCount(2);
    await expect(type.getByRole('option',{name:'Camión',exact:true})).toHaveCount(1);
    await region.selectOption('');
    await expect(type.locator('option')).toHaveCount(4);
    expect(errors).toEqual([]);
  });
}

test('compact calendar opens a paginated daily detail without stretching the month',async({page})=>{
  const errors=await mock(page);
  const records=Array.from({length:33},(_,i)=>({id:i+1,equipment:2,equipment_code:'TR-02',service_type:i%2?'Correctiva':'Preventiva',scheduled_at:'2026-11-17T12:00:00Z',completed_at:i%4===0?'2026-11-17T13:00:00Z':null,status:['completed','scheduled','in_progress','cancelled'][i%4],workshop:'Taller simulado',work_order:`OT-${i+1}`,description:'Actividad simulada del día'}));
  await page.route('**/api/maintenances/',route=>route.fulfill({json:records}));
  await page.goto('/#calendar');
  await page.getByLabel('Mes del calendario').fill('2026-11');
  await expect(page.locator('.weekly-panel')).toHaveCount(0);
  const day=page.getByRole('button',{name:'2026-11-17: 33 registros',exact:true});
  const size=await day.boundingBox();
  expect(Math.abs(size.width-size.height)).toBeLessThan(2);
  expect(size.height).toBeLessThan(55);
  const grid=await page.locator('.compact-calendar').boundingBox();
  expect(grid.height).toBeLessThan(410);
  await expect(page.getByRole('button',{name:'2026-11-18: 0 registros',exact:true})).toBeDisabled();
  await page.screenshot({path:`test-results/compact-calendar-${test.info().project.name}.png`,fullPage:true});
  await day.click();
  const dialog=page.getByRole('dialog',{name:/Mantenciones del/});
  await expect(dialog).toContainText('33 registros');
  await expect(dialog.locator('.calendar-day-record')).toHaveCount(15);
  await dialog.getByRole('button',{name:'Siguiente',exact:true}).click();
  await expect(dialog.locator('.calendar-day-record')).toHaveCount(15);
  await dialog.getByRole('button',{name:'Siguiente',exact:true}).click();
  await expect(dialog.locator('.calendar-day-record')).toHaveCount(3);
  await page.screenshot({path:`test-results/calendar-day-detail-${test.info().project.name}.png`,fullPage:true});
  await dialog.getByRole('button',{name:'Ver ficha del equipo',exact:true}).first().click();
  await expect(page.getByRole('dialog',{name:'Ficha e historial · TR-02'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  expect(errors).toEqual([]);
});
