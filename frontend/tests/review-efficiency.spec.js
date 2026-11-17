import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('calendar panel is horizontally centered and stays compact',async({page})=>{
  const errors=await mock(page);await page.goto('/#calendar');
  const main=await page.locator('.main-content').boundingBox();
  const calendar=await page.locator('.compact-calendar-panel').boundingBox();
  expect(Math.abs((calendar.x+calendar.width/2)-(main.x+main.width/2))).toBeLessThan(3);
  expect(calendar.height).toBeLessThan(650);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:`test-results/centered-calendar-${test.info().project.name}.png`,fullPage:true});
  expect(errors).toEqual([]);
});

test('maintenance type catalog loads only when editing or entering a form',async({page})=>{
  const errors=await mock(page);let catalogRequests=0;
  page.on('request',request=>{if(request.url().includes('/api/maintenances/service-types/'))catalogRequests++;});
  await page.goto('/#maintenance');
  await expect(page.getByRole('heading',{name:'REGISTRO DE MANTENCIONES',exact:true})).toBeVisible();
  expect(catalogRequests).toBe(0);
  await page.getByRole('button',{name:'Editar / Completar',exact:true}).first().click();
  await expect(page.getByLabel('Tipo de mantención *',{exact:true})).toBeEnabled();
  expect(catalogRequests).toBe(1);
  expect(errors).toEqual([]);
});
