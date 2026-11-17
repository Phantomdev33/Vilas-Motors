import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('manual reading opens on demand and retains errors until successful save',async({page})=>{
  const errors=await mock(page);
  await page.goto('/#readings');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button',{name:'Ingreso manual',exact:true}).click();
  const dialog=page.getByRole('dialog');
  await dialog.getByLabel('Equipo *',{exact:true}).selectOption('2');
  await dialog.getByLabel('Valor de horómetro *',{exact:true}).fill('1010');
  let data;
  await page.route('**/api/readings/',route=>{
    if(route.request().method()==='POST'){data=route.request().postData();return route.fulfill({status:400,json:{detail:'Lectura inválida de prueba'}});}
    return route.fallback();
  });
  await dialog.getByRole('button',{name:'Guardar lectura'}).click();
  await expect(dialog.getByRole('alert')).toContainText('Lectura inválida de prueba');
  await expect(dialog.getByLabel('Valor de horómetro *',{exact:true})).toHaveValue('1010');
  expect(data).toContain('1010');
  await page.screenshot({path:`test-results/reading-modal-${test.info().project.name}.png`,fullPage:true});
  await page.route('**/api/readings/',route=>route.request().method()==='POST'?route.fulfill({status:201,json:{id:10}}):route.fallback());
  await dialog.getByRole('button',{name:'Guardar lectura'}).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole('status')).toContainText('Lectura registrada');
  await expect(page).toHaveURL(/#readings$/);
  await page.getByRole('button',{name:'Editar',exact:true}).first().click();
  await expect(page.getByRole('dialog',{name:'Editar lectura'})).toBeVisible();
  await expect(page.getByRole('dialog').getByLabel('Equipo *',{exact:true})).toBeDisabled();
  expect(errors).toEqual([]);
});

test('older backend missing catalog still offers Correctiva',async({page})=>{
  await mock(page);
  await page.route('**/api/maintenances/service-types/',route=>route.fulfill({status:404,json:{detail:'No encontrado.'}}));
  await page.goto('/#detail');
  await page.getByRole('button',{name:'Ver ficha e historial',exact:true}).first().click();
  await page.getByRole('button',{name:'Registrar mantención',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:/Registrar mantenci/});
  await dialog.getByLabel('Tipo de mantención *',{exact:true}).selectOption('Correctiva');
  await expect(dialog.getByRole('alert')).toHaveCount(0);
  await dialog.getByLabel('Responsable *',{exact:true}).fill('Taller');
  await dialog.getByLabel('Descripción del trabajo *',{exact:true}).fill('Reparación correctiva');
  let body;
  await page.route('**/api/maintenances/',route=>{
    if(route.request().method()==='POST'){body=route.request().postDataJSON();return route.fulfill({status:201,json:{id:100}});}
    return route.fallback();
  });
  await dialog.getByRole('button',{name:'Programar',exact:true}).click();
  await expect(dialog).toHaveCount(0);
  expect(body.service_type).toBe('Correctiva');
});
