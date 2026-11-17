import {test,expect} from '@playwright/test';
import {mock} from './support/mock.js';

test('general registry lists equipment and edits the chosen record',async({page})=>{
  const errors=await mock(page);await page.goto('/#detail');
  await expect(page.getByRole('heading',{name:'FICHAS TÉCNICAS E HISTORIALES'})).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.locator('main tbody tr')).toHaveCount(3);
  await page.getByLabel('Buscar ficha por código, nombre o serie').fill('TR-02');
  const row=page.locator('main tbody tr');
  await expect(row).toHaveCount(1);
  await row.getByRole('button',{name:'Completar datos'}).click();
  const edit=page.getByRole('dialog',{name:'Completar ficha · TR-02'});
  await expect(edit.getByLabel('Código de equipo *',{exact:true})).toHaveValue('TR-02');
  await edit.getByRole('button',{name:'Cancelar',exact:true}).click();
  await row.getByRole('button',{name:'Ver ficha e historial'}).click();
  const detail=page.getByRole('dialog',{name:'Ficha e historial · TR-02'});
  await expect(detail.getByRole('heading',{name:/TR-02 \/ Camión/})).toBeVisible();
  await expect(detail.getByLabel('Seleccionar ficha de equipo')).toHaveCount(0);
  await detail.getByRole('button',{name:'Volver al listado'}).click();
  await expect(page.getByLabel('Buscar ficha por código, nombre o serie')).toHaveValue('TR-02');
  await page.screenshot({path:`test-results/technical-registry-${test.info().project.name}.png`,fullPage:true});
  expect(errors).toEqual([]);
});

test('fleet opens a maintenance window exclusively for the chosen equipment',async({page})=>{
  const errors=await mock(page);await page.goto('/#fleet');
  await page.getByLabel('Filtrar región de flota').selectOption('Arica y Parinacota');
  if(test.info().project.name==='desktop'){
    await page.locator('.desktop-table').getByRole('button',{name:'Registrar mantención',exact:true}).click();
  }else{
    await page.locator('.mobile-card').click();
    await page.getByRole('dialog').getByRole('button',{name:'Registrar mantención',exact:true}).click();
  }
  const service=page.getByRole('dialog',{name:'Registrar mantención · TR-02'});
  await expect(service.getByLabel('Equipo *',{exact:true})).toHaveValue('2');
  await expect(service.getByLabel('Equipo *',{exact:true})).toBeDisabled();
  await service.getByRole('button',{name:'Volver a la ficha'}).click();
  const detail=page.getByRole('dialog',{name:'Ficha e historial · TR-02'});
  await expect(detail.getByRole('heading',{name:/TR-02 \/ Camión/})).toBeVisible();
  await page.screenshot({path:`test-results/exclusive-equipment-${test.info().project.name}.png`,fullPage:true});
  await detail.getByRole('button',{name:'Volver al listado'}).click();
  await expect(page).toHaveURL(/#fleet$/);
  await expect(page.getByLabel('Filtrar región de flota')).toHaveValue('Arica y Parinacota');
  expect(errors).toEqual([]);
});

test('registry pagination and saving completed data target only the selected equipment',async({page})=>{
  await mock(page);
  const equipment=Array.from({length:32},(_,i)=>({id:i+1,code:`F-${i+1}`,name:'Equipo',equipment_type:'Camión',brand:'Marca',model:'Modelo',serial_number:`SER-${i+1}`,region:'Tarapacá',commune:'Iquique',active:true,meter_initialized:true,unit:'km',interval:250,initial_value:0,initial_service_value:0,current_value:100,status:'operational'}));
  await page.route('**/api/equipment/',route=>route.fulfill({json:equipment}));
  await page.goto('/#detail');
  await expect(page.locator('main tbody tr')).toHaveCount(15);
  await page.getByRole('button',{name:'Página siguiente',exact:true}).click();
  await expect(page.locator('main tbody tr').first()).toContainText('F-16');
  await page.getByRole('button',{name:'Completar datos'}).first().click();
  const dialog=page.getByRole('dialog',{name:'Completar ficha · F-16'});
  await dialog.getByLabel('Responsable',{exact:true}).fill('Responsable de prueba');
  let saved;
  await page.route('**/api/equipment/16/',route=>{
    saved=route.request().postDataJSON();
    Object.assign(equipment[15],saved);
    return route.fulfill({json:equipment[15]});
  });
  await page.getByRole('dialog').getByRole('button',{name:'Guardar cambios'}).click();
  await expect(page.getByRole('status')).toContainText('F-16');
  expect(saved.responsible).toBe('Responsable de prueba');
  expect(equipment[14].responsible).toBeUndefined();
  await page.getByRole('dialog').getByRole('button',{name:'Volver al listado'}).click();
  await expect(page.getByRole('navigation',{name:'Paginación de fichas'})).toContainText('Página 2 de 3');
});
