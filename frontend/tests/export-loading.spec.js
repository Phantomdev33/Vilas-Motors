import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

for(const format of ['pdf','xlsx']){
  test(`export ${format} shows loading until browser download starts`,async({page})=>{
    const errors=await mock(page);
    let release;const ready=new Promise(resolve=>{release=resolve;});
    let requests=0;
    await page.route('**/api/report/**',async route=>{
      if(new URL(route.request().url()).searchParams.get('export')!==format)return route.fallback();
      requests++;await ready;
      await route.fulfill({status:200,contentType:format==='pdf'?'application/pdf':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',body:format==='pdf'?'%PDF-1.4\n%%EOF':'simulated spreadsheet'});
    });
    await page.goto('/#calendar');
    await page.getByRole('button',{name:format==='pdf'?'Exportar PDF':'Exportar Excel',exact:true}).click();
    const loading=page.getByRole('dialog',{name:format==='pdf'?'Preparando archivo PDF':'Preparando archivo Excel',exact:true});
    await expect(loading).toBeVisible();
    await expect(loading.getByRole('status')).toContainText('La descarga comenzará automáticamente');
    await page.keyboard.press('Escape');
    await expect(loading).toBeVisible();
    await page.screenshot({path:`test-results/export-loading-${format}-${test.info().project.name}.png`,fullPage:true});
    const event=page.waitForEvent('download');release();
    const download=await event;
    expect(download.suggestedFilename()).toMatch(new RegExp(`^flota-.*\\.${format}$`));
    await expect(loading).toHaveCount(0);
    expect(requests).toBe(1);
    expect(errors).toEqual([]);
  });
}

test('failed exports clear loading show an error and can be retried',async({page})=>{
  await mock(page);
  let failed=true;
  await page.route('**/api/report/**',route=>{
    if(!new URL(route.request().url()).searchParams.get('export'))return route.fallback();
    return failed?route.fulfill({status:500,json:{detail:'Error de prueba'}}):route.fulfill({status:200,contentType:'application/pdf',body:'%PDF-1.4\n%%EOF'});
  });
  await page.goto('/#calendar');
  await page.getByRole('button',{name:'Exportar PDF',exact:true}).click();
  const error=page.getByRole('dialog',{name:'No se pudo preparar el archivo',exact:true});
  await expect(error.getByRole('alert')).toContainText('No se pudo generar el archivo');
  await expect(page.getByRole('dialog',{name:'Preparando archivo PDF',exact:true})).toHaveCount(0);
  failed=false;
  const event=page.waitForEvent('download');
  await error.getByRole('button',{name:'Reintentar',exact:true}).click();
  await event;
  await expect(error).toHaveCount(0);
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('reading edit button is visible with icon and opens the selected reading',async({page})=>{
  const errors=await mock(page);await page.goto('/#readings');
  const edit=page.locator('.readings-table tbody tr').first().getByRole('button',{name:'Editar',exact:true});
  await expect(edit).toHaveClass(/reading-edit-button/);
  await expect(edit.locator('svg')).toHaveCount(1);
  expect(await edit.evaluate(button=>parseFloat(getComputedStyle(button).minHeight))).toBeGreaterThanOrEqual(40);
  await edit.click();
  const modal=page.getByRole('dialog',{name:'Editar lectura',exact:true});
  await expect(modal.getByLabel('Equipo *',{exact:true})).toHaveValue('2');
  await expect(modal.getByLabel('Valor de horómetro *',{exact:true})).toHaveValue('1000');
  expect(errors).toEqual([]);
});
