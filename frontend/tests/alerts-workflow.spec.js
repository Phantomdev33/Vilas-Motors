import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('alerts paginate by 15 and sort overdue required upcoming then resolved',async({page})=>{
  const errors=await mock(page);
  const alerts=Array.from({length:32},(_,i)=>({id:i+1,equipment:3,equipment_code:`AL-${i+1}`,equipment_name:'Excavadora',active:i<30,severity:i===0?'overdue':i===1?'required':'upcoming',unit:'hrs',current_value:240,next_service:250,remaining:10,progress:i===0?110:i===1?100:90,message:'Motivo original',attended_at:i>=30?'2026-11-16T12:00:00Z':null,maintenance:i>=30?50:null}));
  alerts[31].severity='overdue';
  await page.route('**/api/alerts/',route=>route.fulfill({json:alerts.toReversed()}));
  await page.goto('/#alerts');
  const rows=page.locator('.page-alerts tbody tr'),pagination=page.getByRole('navigation',{name:'Paginación de alertas'});
  await expect(rows).toHaveCount(15);
  await expect(rows.nth(0)).toContainText('AL-1 ·');
  await expect(rows.nth(1)).toContainText('AL-2 ·');
  await expect(rows.nth(2)).toContainText('Próximo a mantención');
  await pagination.getByRole('button',{name:'Página siguiente',exact:true}).click();
  await expect(rows).toHaveCount(15);
  await pagination.getByRole('button',{name:'Página siguiente',exact:true}).click();
  await expect(rows).toHaveCount(2);
  await expect(rows.first()).toContainText('Solucionada');
  await expect(rows.first()).toContainText('Motivo original');
  await expect(rows.first()).toContainText('Servicio asociado: #50');
  await expect(rows.getByRole('button',{name:'Registrar servicio',exact:true})).toHaveCount(0);
  await page.getByLabel('Filtrar alertas activas').selectOption('true');
  await expect(pagination).toContainText('Página 1 de 2');
  await expect(rows).toHaveCount(15);
  await page.getByLabel('Filtrar alertas activas').selectOption('false');
  await expect(rows).toHaveCount(2);
  await page.screenshot({path:`test-results/resolved-alerts-${test.info().project.name}.png`,fullPage:true});
  expect(errors).toEqual([]);
});

test('service opened from alert resolves the original notice and moves it to the end',async({page})=>{
  const errors=await mock(page);
  const alerts=[
    {id:1,equipment:3,equipment_code:'EX-03',equipment_name:'Excavadora',active:true,severity:'overdue',unit:'hrs',current_value:240,next_service:230,remaining:-10,progress:110,message:'Motivo original de EX-03'},
    {id:2,equipment:2,equipment_code:'TR-02',equipment_name:'Camión',active:true,severity:'upcoming',unit:'km',current_value:1000,next_service:1100,remaining:100,progress:90},
  ];
  await page.route('**/api/alerts/',route=>route.fulfill({json:alerts}));
  let saved;
  await page.route('**/api/maintenances/',route=>{
    if(route.request().method()==='POST'){
      saved=route.request().postDataJSON();
      Object.assign(alerts[0],{active:false,attended_at:'2026-11-16T12:00:00Z',maintenance:99});
      return route.fulfill({status:201,json:{id:99}});
    }
    return route.fallback();
  });
  await page.goto('/#alerts');
  const action=page.locator('.page-alerts tbody tr').first().getByRole('button',{name:'Registrar servicio',exact:true});
  await expect(action).toHaveClass(/primary.*alert-service-button/);
  expect(await action.evaluate(button=>parseFloat(getComputedStyle(button).minHeight))).toBeGreaterThanOrEqual(42);
  await action.click();
  await expect(page).toHaveURL(/#alerts$/);
  await expect(page.getByRole('heading',{name:'ALERTAS DE MANTENCIÓN',exact:true})).toBeVisible();
  const service=page.getByRole('dialog',{name:'Registrar mantención · EX-03'});
  await expect(service.getByLabel('Equipo *',{exact:true})).toHaveValue('3');
  await expect(service.getByLabel('Equipo *',{exact:true})).toBeDisabled();
  await page.screenshot({path:`test-results/alert-direct-service-${test.info().project.name}.png`,fullPage:true});
  await service.getByLabel('Responsable *',{exact:true}).fill('Taller');
  await service.getByLabel('Descripción del trabajo *',{exact:true}).fill('Servicio completado de prueba');
  await service.getByRole('button',{name:'Guardar registro completado',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('EX-03');
  expect(saved.equipment).toBe(3);
  expect(saved.status).toBe('completed');
  await page.getByRole('dialog').getByRole('button',{name:'Volver al listado'}).click();
  const rows=page.locator('.page-alerts tbody tr');
  await expect(rows).toHaveCount(2);
  await expect(rows.first()).toContainText('TR-02');
  await expect(rows.last()).toContainText('EX-03');
  await expect(rows.last()).toContainText('Solucionada');
  await expect(rows.last()).toContainText('Motivo original de EX-03');
  await expect(page.getByRole('button',{name:'Notificaciones: 1 alertas activas'})).toBeVisible();
  expect(errors).toEqual([]);
});
