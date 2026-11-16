import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('fleet paginates by 15 and resets after filtering',async({page})=>{
  await mock(page);
  const equipment=Array.from({length:32},(_,i)=>({id:i+1,code:`EQ-${String(i+1).padStart(3,'0')}`,name:'Equipo simulado',equipment_type:'Camion',region:i===31?'Especial':'Norte',active:true,status:'operational',current_value:100,unit:'km',progress:10,remaining:900,next_service:1000}));
  await page.route('**/api/equipment/',route=>route.fulfill({json:equipment}));
  await page.goto('/');
  const rows=page.locator('.desktop-table:visible tbody tr, .mobile-equipment:visible .mobile-card');
  await expect(rows).toHaveCount(15);
  await expect(page.getByRole('button',{name:'Volver arriba'})).toHaveCount(0);
  await page.getByRole('button',{name:'P\u00e1gina siguiente',exact:true}).click();
  await expect(rows).toHaveCount(15);
  await expect(rows.first()).toContainText('EQ-016');
  await page.getByRole('button',{name:'P\u00e1gina siguiente',exact:true}).click();
  await expect(rows).toHaveCount(2);
  await page.getByLabel('Filtrar regi\u00f3n de flota').selectOption('Especial');
  await expect(rows).toHaveCount(1);
  await expect(page.getByRole('navigation',{name:'Paginaci\u00f3n de flota'})).toContainText('1 de 1');
});

test('maintenance is tied to the detail equipment; errors stay in modal and success stays on detail',async({page})=>{
  const errors=await mock(page);
  await page.goto('/#detail');
  await page.getByRole('button',{name:'Registrar mantenci\u00f3n',exact:true}).click();
  const dialog=page.getByRole('dialog');
  await expect(dialog.getByLabel('Equipo *',{exact:true})).toBeDisabled();
  await expect(dialog.getByLabel('Equipo *',{exact:true})).toHaveValue('1');
  await dialog.getByLabel('Responsable *',{exact:true}).fill('Taller de prueba');
  await dialog.getByLabel('Descripci\u00f3n del trabajo *',{exact:true}).fill('Servicio simulado');
  let body;
  await page.route('**/api/maintenances/',route=>{
    if(route.request().method()==='POST'){body=route.request().postDataJSON();return route.fulfill({status:400,json:{detail:'Error de prueba'}});}
    return route.fallback();
  });
  await dialog.getByRole('button',{name:'Programar',exact:true}).click();
  await expect(dialog.getByRole('alert')).toContainText('Error de prueba');
  expect(body.equipment).toBe(1);
  await page.route('**/api/maintenances/',route=>route.request().method()==='POST'?route.fulfill({status:201,json:{id:99}}):route.fallback());
  await dialog.getByRole('button',{name:'Programar',exact:true}).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.locator('.maintenance-toast')).toContainText('XLS-0002');
  await expect(page).toHaveURL(/#detail$/);
  expect(errors).toEqual([]);
});
