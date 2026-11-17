import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

for (const screen of ['fleet','equipment','readings','detail','maintenance','calendar','alerts','users','rentals']) {
  test(`dark design preserves ${screen} on desktop and mobile`, async ({page}, info) => {
    const errors = await mock(page);
    await page.goto(`/#${screen}`);
    await expect(page.locator('main h1')).toBeVisible();
    if (screen === 'detail') await expect(page.getByText('Cargando historial…')).toHaveCount(0);
    if (screen === 'calendar') await page.getByLabel('Mes del calendario').fill('2025-08');
    if (screen === 'fleet') {
      await expect(page.getByRole('img',{name:'0% de los equipos activos están operativos'})).toBeVisible();
      await page.getByLabel('Filtrar región de flota').selectOption('Arica y Parinacota');
      await expect(page.locator('.desktop-table:visible, .mobile-equipment:visible').getByText('TR-02 · Camión')).toBeVisible();
      await expect(page.locator('.desktop-table:visible, .mobile-equipment:visible').getByText(/EX-03/)).toHaveCount(0);
      await page.getByLabel('Filtrar región de flota').selectOption('');
    }
    if (screen === 'rentals') {
      await expect(page.getByText('MÓDULO EN PREPARACIÓN')).toBeVisible();
      await expect(page.getByRole('button',{name:/Nuevo arriendo/})).toHaveCount(0);
    }
    const colors = await page.locator('select').evaluateAll(nodes => nodes.map(node => getComputedStyle(node).backgroundColor));
    expect(colors).not.toContain('rgb(255, 255, 255)');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
    await page.screenshot({path:`.runtime/design-review/${screen}-${info.project.name}.png`,fullPage:true});
    expect(errors).toEqual([]);
  });
}

test('equipment form retains its unit and local fleet search replaces header search',async({page},info)=>{
  const errors=await mock(page);
  await page.goto('/#equipment');
  await page.getByRole('button',{name:'Crear equipo',exact:true}).click();
  await expect(page.getByLabel('Intervalo de servicio (hrs) *',{exact:true})).toBeVisible();
  await page.screenshot({path:`.runtime/design-review/editor-${info.project.name}.png`,fullPage:true});
  await page.goto('/#fleet');
  await expect(page.locator('.topbar .global-search')).toHaveCount(0);
  await expect(page.getByLabel('Buscar equipo en la flota',{exact:true})).toHaveCount(0);
  await page.getByLabel('Buscar código o modelo',{exact:true}).fill('EX-03');
  await expect(page.locator('.desktop-table:visible, .mobile-equipment:visible').getByText('EX-03 · Excavadora')).toBeVisible();
  expect(errors).toEqual([]);
});
