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
test('password recovery uses an SMS code after the captcha',async({page},info)=>{
  const errors=await mock(page,false);await page.goto('/');
  await page.route('**/api/auth/reset/',route=>route.fulfill({status:202,json:{challenge_id:'reset-sms',detail:'Revisa tu celular.'}}));
  await page.route('**/api/auth/reset/confirm/',route=>{
    expect(route.request().postDataJSON()).toEqual({challenge_id:'reset-sms',code:'012345',password:'SecureDemo2026!'});
    return route.fulfill({json:{detail:'Contraseña actualizada.'}});
  });
  await expect(page.getByLabel('Código de verificación',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'¿Olvidaste tu contraseña?'}).click();
  await page.getByLabel('Correo electrónico').fill('ana@example.cl');
  await expect(page.getByRole('button',{name:'Ingresar',exact:true})).toBeHidden();
  await page.getByLabel('Código de verificación',{exact:true}).fill('ABC234');
  await page.getByRole('button',{name:'Enviar código SMS'}).click();
  await page.getByLabel('Código SMS').fill('012345');
  await expect(page.getByLabel('Nueva contraseña',{exact:true})).toHaveAttribute('minlength','13');
  await page.getByLabel('Nueva contraseña',{exact:true}).fill('SecureDemo2026!');
  await page.getByLabel('Confirmar nueva contraseña',{exact:true}).fill('SecureDemo2026!');
  await page.screenshot({path:`test-results/updated-reset-${info.project.name}.png`,fullPage:true});
  await page.getByRole('button',{name:'Guardar contraseña'}).click();
  await expect(page.getByText(/Contraseña actualizada/)).toBeVisible();
  expect(errors).toEqual([]);
});

test('an equipment editor can apply a matching manufacturer reference',async({page})=>{
  await mock(page);
  await page.route('**/api/service-references/',route=>route.fulfill({json:[
    {equipment_type:'Camioneta',brand:'Toyota',model:'Hilux',unit:'km',interval:10000,scope:'Servicio de 10.000 km.',source:'https://toyota.cl/'},
  ]}));
  await page.goto('/#equipment');
  await page.getByRole('button',{name:'Crear equipo',exact:true}).click();
  await page.getByLabel('Tipo *',{exact:true}).selectOption('Camioneta');
  await page.getByRole('button',{name:'Usar intervalo de Toyota Hilux'}).click();
  await expect(page.getByLabel('Intervalo de servicio (km) *',{exact:true})).toHaveValue('10000');
});

test('login opens the fleet only after verifying the SMS code',async({page})=>{
  await mock(page,false);
  let verified=false;
  await page.route('**/api/auth/me/',route=>verified
    ? route.fulfill({json:{id:1,first_name:'Ana',role:'admin',permissions:{equipment:'R'}}})
    : route.fulfill({status:401,json:{detail:'Sin sesión'}}));
  await page.route('**/api/auth/login/',route=>route.fulfill({status:202,json:{challenge_id:'login-sms'}}));
  await page.route('**/api/auth/login/verify/',route=>{
    expect(route.request().postDataJSON()).toEqual({challenge_id:'login-sms',code:'012345'});
    verified=true;
    return route.fulfill({json:{id:1}});
  });
  await page.goto('/');
  await page.getByLabel('Correo electrónico').fill('ana@example.cl');
  await page.getByLabel('Contraseña',{exact:true}).fill('SecureDemo2026!');
  await page.getByLabel('Código de verificación',{exact:true}).fill('ABC234');
  await page.getByRole('button',{name:'Ingresar',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Verificación por SMS'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'ESTADO DE LA FLOTA'})).toHaveCount(0);
  await page.getByLabel('Código SMS').fill('012345');
  await page.getByRole('button',{name:'Verificar código'}).click();
  await expect(page.getByRole('heading',{name:'ESTADO DE LA FLOTA'})).toBeVisible();
});
