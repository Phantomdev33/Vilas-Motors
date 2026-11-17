import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('bell notification opens details then registers service for exactly that vehicle',async({page})=>{
  const errors=await mock(page);
  await page.route('**/api/alerts/',route=>route.fulfill({json:[
    {id:9,equipment:2,equipment_code:'TR-02',equipment_name:'Camión',severity:'overdue',active:true,current_value:1000,next_service:900,remaining:-100,unit:'km',message:'Aviso de camión'},
    {id:10,equipment:3,equipment_code:'EX-03',equipment_name:'Excavadora',equipment_type:'Excavadora',severity:'upcoming',active:true,current_value:240,next_service:250,remaining:10,unit:'hrs',message:'Revisar filtros de la excavadora',created_at:'2026-11-16T12:00:00Z'},
  ]}));
  await page.goto('/#fleet');
  await page.getByRole('button',{name:'Notificaciones: 2 alertas activas'}).click();
  await page.getByRole('region',{name:'Notificaciones',exact:true}).getByRole('button',{name:/EX-03/}).click();
  const detail=page.getByRole('dialog',{name:'Notificación · EX-03'});
  await expect(detail).toBeVisible();
  await expect(detail).toContainText('Revisar filtros de la excavadora');
  await expect(detail).toContainText('240 hrs');
  await expect(detail).toContainText('250 hrs');
  await expect(detail).toContainText('Tarapacá');
  await expect(page).toHaveURL(/#fleet$/);
  await page.screenshot({path:`test-results/notification-detail-${test.info().project.name}.png`,fullPage:true});
  await detail.getByRole('button',{name:'Registrar servicio',exact:true}).click();
  await expect(detail).toHaveCount(0);
  const service=page.getByRole('dialog',{name:'Registrar mantención · EX-03'});
  await expect(service.getByLabel('Equipo *',{exact:true})).toHaveValue('3');
  await expect(service.getByLabel('Equipo *',{exact:true})).toBeDisabled();
  await service.getByLabel('Responsable *',{exact:true}).fill('Taller de prueba');
  await service.getByLabel('Descripción del trabajo *',{exact:true}).fill('Revisión de filtros');
  let body;
  await page.route('**/api/maintenances/',route=>{
    if(route.request().method()==='POST'){body=route.request().postDataJSON();return route.fulfill({status:201,json:{id:100}});}
    return route.fallback();
  });
  await service.getByRole('button',{name:'Programar',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('EX-03');
  expect(body.equipment).toBe(3);
  expect(errors).toEqual([]);
});

test('read only users can view notification history without a service action',async({page})=>{
  await mock(page);
  await page.route('**/api/auth/me/',route=>route.fulfill({json:{id:1,role:'chief',first_name:'Jefe',permissions:{equipment:'R',alert:'R',maintenance:'R',reading:'R'}}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Notificaciones: 1 alertas activas'}).click();
  await page.locator('.notification-item').click();
  const detail=page.getByRole('dialog',{name:'Notificación · EX-03'});
  await expect(detail.getByRole('button',{name:'Registrar servicio',exact:true})).toHaveCount(0);
  await detail.getByRole('button',{name:'Ver ficha',exact:true}).click();
  await expect(page.getByRole('dialog',{name:'Ficha e historial · EX-03'})).toBeVisible();
});
