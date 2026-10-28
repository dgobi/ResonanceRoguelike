import assert from 'node:assert/strict';
import {createServer} from 'vite';
import {chromium} from 'playwright-core';
const server=await createServer({server:{port:1431,strictPort:true}});await server.listen();
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
try{
 const page=await browser.newPage();await page.goto('http://127.0.0.1:1431/scripts/fixtures/geometry.html');
 const field=n=>page.getByLabel(n,{exact:true}),button=n=>page.getByRole('button',{name:n,exact:true});
 const data=async()=>JSON.parse(await field('Source').inputValue());
 const change=async f=>{const r=await data();f(r);await field('Source').fill(JSON.stringify(r));};
 const value=async(n,v)=>{await page.waitForFunction(([n,v])=>document.querySelector(`[aria-label="${n}"]`)?.value===v,[n,v]);assert.equal(await field(n).inputValue(),v,n);};
 await change(r=>{r.player_start={x:4,y:3};r.layers=Array(8).fill('............');r.exit_direction='east';r.exit_x=9;r.exit_y=4;});
 for(const [n,v] of [['Room width','12'],['Room height','8'],['Arrival X','4'],['Arrival Y','3'],['Fallback exit direction','east'],['Fallback exit X','9'],['Fallback exit Y','4']])await value(n,v);
 await button('Undo').click();await value('Arrival Y','5');await value('Room width','10');await button('Redo').click();await value('Arrival Y','3');
 await field('Arrival X').fill('6');await button('Apply arrival').click();assert.deepEqual((await data()).player_start,{x:6,y:3});
 await button('Undo').click();assert.deepEqual((await data()).player_start,{x:4,y:3});await button('Redo').click();
 await field('Fallback exit X').fill('8');await button('Apply fallback return').click();let r=await data();assert.deepEqual([r.exit_direction,r.exit_x,r.exit_y],['east',8,4]);
 await field('Room width').fill('13');await field('Arrival X').fill('7');await field('Fallback exit Y').fill('5');await button('Paint').click();
 await button('Switch document').click();await button('Switch document').click();await value('Room width','13');await value('Arrival X','7');await value('Fallback exit Y','5');
 await button('Apply resize (top-left anchor)').click();r=await data();assert.equal(r.layers.length,8);assert.equal(r.layers[0].length,13);assert.equal(r.metadata.keep,'λ');
 await change(r=>{delete r.player_start;delete r.exit_direction;delete r.exit_x;delete r.exit_y;});await value('Arrival Y','0');await value('Fallback exit X','11');await value('Fallback exit Y','6');await value('Fallback exit direction','south');
 await field('Resize fill glyph').selectOption('#');await change(r=>{r.legend['#']='missing';});await value('Resize fill glyph','.');await change(r=>{delete r.legend['#'];r.layers=r.layers.map(s=>s.replaceAll('#','.'));});await value('Resize fill glyph','.');
 console.log('PASS mounted geometry: Source, Undo/Redo, companion coordinates, defaults, dimensions, pending painting/switch, fill validity');
}finally{await browser.close();await server.close();}
