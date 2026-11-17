import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('equipment pages contain 15 rows; filters reset the page and create lives in toolbar',async({page})=>{
  const errors=await mock(page);
  const equipment=Array.from({length:33},(_,i)=>({id:i+1,code:`EQ-${String(i+1).padStart(3,'0')}`,name:'Camión de prueba',equipment_type:'Camión',brand:'Marca',model:'Modelo',active:i!==32,region:i===31?'Especial':'Norte',commune:'Comuna',unit:'km',current_value:100,status:'operational',interval:250}));
  await page.route('**/api/equipment/',route=>route.fulfill({json:equipment}));
  await page.goto('/#equipment');
  const rows=page.locator('.page-equipment .vm-table tbody tr');
  await expect(rows).toHaveCount(15);
  await expect(page.getByRole('button',{name:'Plantilla de migración'})).toHaveCount(0);
  await expect(page.locator('.page-equipment>.toolbar').getByRole('button',{name:'Crear equipo',exact:true})).toBeVisible();
  const pagination=page.getByRole('navigation',{name:'Paginación de equipos'});
  await pagination.getByRole('button',{name:'Página siguiente',exact:true}).click();
  await expect(rows.first()).toContainText('EQ-016');
  await pagination.getByRole('button',{name:'Página siguiente',exact:true}).click();
  await expect(rows).toHaveCount(2);
  await page.getByLabel('Filtrar región',{exact:true}).selectOption('Especial');
  await expect(rows).toHaveCount(1);
  await expect(pagination).toContainText('Página 1 de 1');
  await page.getByLabel('Filtrar región',{exact:true}).selectOption('');
  await page.getByLabel('Mostrar equipos anteriores / inactivos').check();
  await expect(pagination).toContainText('de 33 equipos');
  await page.getByLabel('Mostrar equipos anteriores / inactivos').uncheck();
  const first=rows.first();
  await expect(first.getByRole('button',{name:'Consultar',exact:true}).locator('svg')).toHaveCount(1);
  await first.getByRole('button',{name:'Editar',exact:true}).click();
  await expect(page.getByLabel('Código de equipo *',{exact:true})).toHaveValue('EQ-001');
  await page.getByRole('button',{name:'Cancelar',exact:true}).click();
  await first.getByRole('button',{name:'Desactivar',exact:true}).click();
  await expect(page.getByRole('dialog')).toContainText('EQ-001');
  await page.getByRole('button',{name:'Mantener activo'}).click();
  await page.screenshot({path:`test-results/equipment-paginated-${test.info().project.name}.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  expect(errors).toEqual([]);
});

test('read only equipment access retains consult without mutation actions',async({page})=>{
  await mock(page);
  await page.route('**/api/auth/me/',route=>route.fulfill({json:{id:1,role:'chief',first_name:'Jefe',permissions:{equipment:'R',maintenance:'R',reading:'R'}}}));
  await page.goto('/#equipment');
  await expect(page.getByRole('button',{name:'Consultar',exact:true})).toHaveCount(3);
  await expect(page.getByRole('button',{name:'Crear equipo',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Editar',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Desactivar',exact:true})).toHaveCount(0);
});
