import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('reading pages contain 15 entries and cascaded filters reset pagination',async({page})=>{
  const errors=await mock(page);
  const readings=Array.from({length:32},(_,i)=>({id:i+1,equipment:i===31?3:2,equipment_code:i===31?'EX-03':'TR-02',equipment_name:'Equipo',recorded_at:'2026-11-16T12:00:00Z',source:'manual',value:i+1000,registered_by:'Prueba',evidence:null}));
  await page.route('**/api/readings/',route=>route.fulfill({json:readings}));
  await page.goto('/#readings');
  const rows=page.locator('.readings-table tbody tr'),pagination=page.getByRole('navigation',{name:'Paginación de lecturas'});
  await expect(rows).toHaveCount(15);
  await pagination.getByRole('button',{name:'Página siguiente',exact:true}).click();
  await expect(rows).toHaveCount(15);
  await pagination.getByRole('button',{name:'Página siguiente',exact:true}).click();
  await expect(rows).toHaveCount(2);
  await page.getByLabel('Filtrar región de lecturas').selectOption('Tarapacá');
  await page.getByLabel('Filtrar tipo de lecturas').selectOption('Excavadora');
  const equipment=page.getByLabel('Filtrar lecturas por equipo');
  await expect(equipment.locator('option')).toHaveCount(2);
  await equipment.selectOption('3');
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText('EX-03');
  await expect(pagination).toContainText('Página 1 de 1');
  await page.getByLabel('Filtrar tipo de lecturas').selectOption('Grúa horquilla');
  await expect(equipment).toHaveValue('');
  await expect(rows).toHaveCount(0);
  await page.getByRole('button',{name:'Limpiar filtros',exact:true}).click();
  await expect(rows).toHaveCount(15);
  expect(errors).toEqual([]);
});

test('notification badge counts active alerts and summary links to detailed alerts',async({page})=>{
  const errors=await mock(page);
  const alerts=Array.from({length:8},(_,i)=>({id:i+1,equipment:3,equipment_code:`EX-${i+1}`,equipment_name:'Excavadora',equipment_type:'Excavadora',active:i!==7,severity:i===6?'overdue':'upcoming',unit:'hrs',current_value:240,remaining:10,progress:96,message:'Detalle extenso reservado para alertas'}));
  await page.route('**/api/alerts/',route=>route.fulfill({json:alerts}));
  await page.goto('/');
  const bell=page.getByRole('button',{name:'Notificaciones: 7 alertas activas'});
  await expect(bell.locator('.notification-count')).toHaveText('7');
  await bell.click();
  const summary=page.getByRole('region',{name:'Notificaciones',exact:true});
  await expect(summary.locator('.notification-total')).toHaveText('7');
  await expect(summary.locator('.notification-item')).toHaveCount(5);
  await expect(summary.locator('.notification-item').first()).toContainText('EX-7');
  await expect(summary.getByText('Detalle extenso reservado para alertas')).toHaveCount(0);
  await page.screenshot({path:`test-results/notifications-${test.info().project.name}.png`,fullPage:true});
  await page.keyboard.press('Escape');
  await expect(summary).toHaveCount(0);
  await bell.click();
  await summary.getByRole('button',{name:/Ver todas las alertas/}).click();
  await expect(page).toHaveURL(/#alerts$/);
  await expect(page.getByRole('heading',{name:'ALERTAS DE MANTENCIÓN',exact:true})).toBeVisible();
  await expect(page.getByRole('columnheader',{name:'CERCANÍA A MANTENCIÓN'})).toBeVisible();
  expect(errors).toEqual([]);
});

test('empty notifications show no badge and a clear empty state',async({page})=>{
  await mock(page);await page.route('**/api/alerts/',route=>route.fulfill({json:[]}));
  await page.goto('/');
  const bell=page.getByRole('button',{name:'Notificaciones: 0 alertas activas'});
  await expect(bell.locator('.notification-count')).toHaveCount(0);
  await bell.click();
  await expect(page.getByText('No hay alertas activas.',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Cerrar notificaciones',exact:true}).click();
  await expect(page.getByRole('region',{name:'Notificaciones',exact:true})).toHaveCount(0);
});
