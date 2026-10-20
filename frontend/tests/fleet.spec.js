import {test,expect} from '@playwright/test';
async function login(page,email='james@vilasmotor.cl'){
  await page.goto('/');await page.getByLabel('Correo electrónico',{exact:true}).fill(email);await page.getByLabel('Contraseña',{exact:true}).fill('VilasDemo2026!');
  await page.getByRole('button',{name:'Ingresar',exact:true}).click();await expect(page.getByRole('heading',{name:'ESTADO DE LA FLOTA',exact:true})).toBeVisible();
}
test('login, equipment history, calendar and exports',async({page},testInfo)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');await page.screenshot({path:`test-results/login-${testInfo.project.name}.png`,fullPage:true});
  await login(page);await expect(page.locator('.desktop-table:visible, .mobile-equipment:visible').getByText('EX-01 · CAT 320',{exact:true})).toBeVisible();
  await page.screenshot({path:`test-results/fleet-${testInfo.project.name}.png`,fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);expect(overflow).toBe(false);
  await page.goto('/#detail');await expect(page.getByRole('heading',{name:'FICHA TÉCNICA DE EQUIPO'})).toBeVisible();await expect(page.getByRole('heading',{name:'Cronología de lecturas'})).toBeVisible();
  await page.goto('/#calendar');await expect(page.getByRole('heading',{name:'CALENDARIO DE MANTENCIÓN'})).toBeVisible();
  const dl=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar Excel',exact:true}).click();const result=await dl;expect(result.suggestedFilename()).toMatch(/\.xlsx$/);
  expect(errors).toEqual([]);
});
test('chief has no write actions and helper cannot manage users',async({page})=>{
  await login(page,'jefe@vilasmotor.cl');await expect(page.getByRole('button',{name:'Registrar lectura',exact:true})).toHaveCount(0);
  await page.goto('/#equipment');await expect(page.getByRole('button',{name:'Crear equipo',exact:true})).toHaveCount(0);
  await page.goto('/#users');await expect(page.getByRole('heading',{name:'USUARIOS Y ROLES'})).toBeVisible();await expect(page.getByRole('button',{name:'Crear usuario',exact:true})).toHaveCount(0);
});
test('planner can register a reading and rejects a decreasing value',async({page})=>{
  await login(page);await page.goto('/#readings');await expect(page.getByRole('heading',{name:'Ingreso manual'})).toBeVisible();
  await page.getByLabel('Equipo *',{exact:true}).selectOption({label:'WL-06 · Cargador frontal'});
  await page.getByLabel('Valor de horómetro *').fill('1');await page.getByRole('button',{name:'Guardar lectura',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('fuera de secuencia');
  const current=await page.getByLabel('Valor de horómetro *').getAttribute('placeholder');
  await page.getByLabel('Valor de horómetro *').fill(String(Number(current)+1));await page.getByRole('button',{name:'Guardar lectura',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('guardado correctamente');
});
test('admin creates equipment, completes service and preserves history on deactivation',async({page},testInfo)=>{
  await login(page,'admin@vilasmotor.cl');
  await page.goto('/#equipment');await page.getByRole('button',{name:'Crear equipo',exact:true}).click();
  const code=`QA-${testInfo.project.name}-${Date.now().toString().slice(-7)}`;
  await page.getByLabel('Código de equipo *').fill(code);await page.getByLabel('Nombre / Modelo visible *').fill('Equipo de prueba automática');
  await page.getByLabel('Marca *',{exact:true}).fill('CAT');await page.getByLabel('Modelo *',{exact:true}).fill('320');
  await page.getByLabel('Número de serie *').fill(code);await page.getByLabel('Lectura inicial *').fill('250');
  await page.getByLabel('Última mantención inicial *').fill('0');await page.getByRole('button',{name:'Guardar cambios',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('guardado correctamente');
  await page.goto('/#maintenance');await page.getByLabel('Equipo *',{exact:true}).selectOption({label:`${code} · Equipo de prueba automática`});
  await page.getByLabel('Maestro / Taller *').fill('Taller QA');await page.getByLabel('Descripción del trabajo *').fill('Cambio de aceite y filtro · Prueba automática.');
  await page.getByRole('button',{name:'Guardar registro completado',exact:true}).click();await expect(page.getByRole('status')).toContainText('guardado correctamente');
  await page.goto('/#detail');const options=await page.getByRole('combobox',{name:'Seleccionar ficha de equipo'}).locator('option').allTextContents();expect(options).toContain(`${code} · Equipo de prueba automática`);
  await page.getByRole('combobox',{name:'Seleccionar ficha de equipo'}).selectOption({label:`${code} · Equipo de prueba automática`});
  await expect(page.getByText('Operativo',{exact:false}).first()).toBeVisible();
  await page.getByRole('tab',{name:'Mantenciones',exact:true}).click();await expect(page.getByText('Completada',{exact:true})).toBeVisible();
  await page.goto('/#equipment');await page.getByPlaceholder('Buscar código o modelo').fill(code);await page.getByRole('button',{name:'Desactivar',exact:true}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Desactivar equipo',exact:true}).click();await expect(page.getByRole('status')).toContainText('desactivado');
  await expect(page.getByText('CAT 320 · Inactivo',{exact:true})).toBeVisible();
});
test('offline reading is retained and synchronized after reconnecting',async({page,context})=>{
  await login(page);await page.goto('/#readings');await page.getByLabel('Equipo *',{exact:true}).selectOption({label:'WL-06 · Cargador frontal'});
  const current=Number(await page.getByLabel('Valor de horómetro *').getAttribute('placeholder'));
  await context.setOffline(true);await page.getByLabel('Valor de horómetro *').fill(String(current+1));await page.getByRole('button',{name:'Guardar lectura',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('guardada en este dispositivo');
  await context.setOffline(false);await expect(page.getByRole('status')).toContainText('sincronizadas correctamente');
  await expect(page.getByLabel('Valor de horómetro *')).toHaveAttribute('placeholder',`${current+1}.00`);
});
