import {test,expect} from '@playwright/test';

import {mock} from './support/mock.js';

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
  await page.getByLabel('Filtrar fuente',{exact:true}).selectOption('photo');
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
