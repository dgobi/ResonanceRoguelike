// SYS-1 commissioned exact-source authoring and actual packaged app-local play.
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/sys-1',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
await mkdir(settings,{recursive:true});
await writeFile(resolve(settings,'project.json'),JSON.stringify({version:1,project_root:root}));
const base='roguelike/data/entities/creatures/',template='roguelike/docs/examples/g17_authored_creature_room.json';
const exe=resolve('src-tauri/target/release/resonance-workbench.exe'),hash=b=>createHash('sha256').update(b).digest('hex');
const receipt={output,root,started_utc:new Date().toISOString(),package_sha256:hash(await readFile(exe)),checks:[],publications:[],errors:[]};
const baseline={};for(const p of [base+'hollow_revenant.json','roguelike/data/layouts/barrow_ward_store_a.json',template])baseline[p]=hash(await readFile(resolve(root,p)));
let child,browser,page,session,eventId=0;
const b=name=>page.getByRole('button',{name,exact:true}).filter({visible:true}),editor=()=>page.locator('[data-testid="authoring"]:visible'),eb=name=>editor().getByRole('button',{name,exact:true});
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'),null,{timeout:60000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==='true'));
const fill=async(label,value)=>{await page.getByLabel(label,{exact:true}).filter({visible:true}).fill(String(value));await editIdle();};
const select=async(label,value)=>{await page.getByLabel(label,{exact:true}).filter({visible:true}).selectOption(value);await editIdle();};
const exists=async path=>access(resolve(root,path)).then(()=>true,()=>false);
async function phase(text){receipt.checks.push(text);console.log(text);await writeFile(resolve(output,'progress.json'),JSON.stringify(receipt,null,2));}
async function until(fn,timeout=90000){const start=Date.now();for(;;){const v=await fn();if(v)return v;assert(Date.now()-start<timeout,'Timed out');await new Promise(r=>setTimeout(r,100));}}
async function open(path){await idle();await select('Category / route','');await fill('Search ID, name or path',path);await page.locator(`[data-asset="${path}"]`).click();await page.waitForFunction(path=>[...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.offsetParent&&e.querySelector('.filepath')?.textContent===path),path);await idle();}
async function opened(path){for(let i=0;i<8;i++){await idle();const r=await ipc('open_document',{asset:path});if(r.result)return r.result;assert.equal(r.error?.code,'BUSY',JSON.stringify(r));await new Promise(r=>setTimeout(r,100));}throw Error('Open remained busy');}
async function validate(){await editIdle();await idle();await eb('Validate draft').click();await idle();const r=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(r.valid&&r.review_token,JSON.stringify(r.diagnostics));return r;}
async function begin(){if(await eb('Begin edit').count())await eb('Begin edit').click();}
async function apply(path,variant=false){await editIdle();await idle();if(await eb('Validate draft').isDisabled()){const doc=await opened(path);(receipt.reopened??=[]).push({path,sha256:doc.sha256});return doc;}const r=await validate();await eb(await eb('Review & apply').count()?'Review & apply':'Apply variant').click();await b('Confirm apply one file').click();await idle();await page.getByText(/Saved and byte-checked reopen:/).waitFor({timeout:60000});const doc=await opened(path);receipt.publications.push({path,sha256:doc.sha256,definition:JSON.parse(doc.raw),review:r});return doc;}
async function cell(x,y){const map=page.getByTestId('layout-map').filter({visible:true});await map.scrollIntoViewIfNeeded();const p=await map.evaluate((el,[x,y])=>{const c=JSON.parse(el.dataset.camera),r=el.getBoundingClientRect();return {x:r.x+c.x+(x+.5)*16*c.scale,y:r.y+c.y+(y+.5)*16*c.scale};},[x,y]);await page.mouse.click(p.x,p.y);await editIdle();}
async function rectangle(x1,y1,x2,y2){await b(/^Fill /).click();const map=page.getByTestId('layout-map').filter({visible:true});await map.scrollIntoViewIfNeeded();const points=await map.evaluate((el,coords)=>{const c=JSON.parse(el.dataset.camera),r=el.getBoundingClientRect();return coords.map(([x,y])=>({x:r.x+c.x+(x+.5)*16*c.scale,y:r.y+c.y+(y+.5)*16*c.scale}));},[[x1,y1],[x2,y2]]);await page.mouse.move(points[0].x,points[0].y);await page.mouse.down();await page.mouse.move(points[1].x,points[1].y,{steps:5});await page.mouse.up();await editIdle();}
async function status(){const s=await ipc('room_test_action',{action:'status'});assert(!s.error,JSON.stringify(s));return s;}
async function observe(){return JSON.parse(await readFile(resolve(session.state_root,'observation.json'),'utf8'));}
async function start(action='test'){
 const previous=session?.session_id;await b(action==='test'?'Test room':action==='reset'?'Reset current test':'Test latest saved version').click();
 session=await until(async()=>{const s=await status();assert.notEqual(s.status,'failed',s.diagnostics||JSON.stringify(s));assert(!s.last_action_error&&!s.error,JSON.stringify({status:s.status,last_action_error:s.last_action_error,error:s.error,diagnostics:s.diagnostics}));return s.status==='running'&&!s.preparing&&s.session_id!==previous?s:null;});eventId=0;
 await until(async()=>{try{return await observe();}catch{return null;}});return session;
}
async function key(key,capture=false){const id=++eventId,path=resolve(session.state_root,'event.json'),tmp=path+'.tmp';await writeFile(tmp,JSON.stringify({id,key,capture}));await until(async()=>{try{await rename(tmp,path);return true;}catch(e){if(!['EPERM','EACCES','EBUSY'].includes(e.code))throw e;return false;}});return until(async()=>{const s=await status();assert.notEqual(s.status,'failed',s.diagnostics||JSON.stringify(s));try{const o=await observe();return o.applied===id?o:null;}catch{return null;}});}

const itemPath=id=>`roguelike/data/items/components/${id}.json`,room='roguelike/data/layouts/sys1_preparation_room.json',recipe='roguelike/data/recipes/resonant_bone_tincture.json';
const specs=[['copper_steeping_kettle','copper steeping kettle',1000,.9,true],['waxed_water_flask','waxed water flask',2000,.2,false],['small_steeping_cup','small steeping cup',150,.25,true]];
async function check(label,value){await page.getByLabel(label,{exact:true}).filter({visible:true}).setChecked(value);await editIdle();}
async function vessel([id,name,capacity,weight,heat]){
 const path=itemPath(id),fresh=!(await exists(path));await open(fresh?itemPath('clay_pot'):path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name:'Properties',exact:true}).click();await fill('Item name',name);await fill('Item weight (kg)',weight);
 await fill('Item description',id==='copper_steeping_kettle'?'A broad copper kettle. Heavy empty, roomy over a fire.':id==='waxed_water_flask'?'A light waxed carrier. Holds water; keep it away from fire.':'A small cup for measured work. Too small for a full quarter-litre batch.');
 await fill('Capacity (mL)',capacity);await check('Heat-suitable vessel',heat);
 await page.getByLabel('Capacity (mL)',{exact:true}).filter({visible:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,id+'-controls.png')});
 await apply(path);const d=JSON.parse((await opened(path)).raw);assert.equal(d.vessel.capacity_ml,capacity);
 const noOpBefore=hash(await readFile(resolve(root,path)));await begin();await apply(path);
 assert.equal(hash(await readFile(resolve(root,path))),noOpBefore);(receipt.noops??=[]).push({path,sha256:noOpBefore});
 await fill('Capacity (mL)',0);await eb('Validate draft').click();await idle();
 const invalid=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!invalid.valid);
 await b('Undo item').click();await editIdle();assert.equal(await page.getByLabel('Capacity (mL)',{exact:true}).filter({visible:true}).inputValue(),String(capacity));
 assert.equal(hash(await readFile(resolve(root,path))),noOpBefore);(receipt.invalidVessels??=[]).push({path,rejected:true,undo_restored:true});
}
async function makeRoom(){
 if(await exists(room)){await open(room);return;}
 await open(template);await begin();await eb('Save as new variant').click();await fill('New variant ID','sys1_preparation_room');
 await eb('Source').click();
 // Room geometry entered through the packaged source editor. Item placements
 // and all vessel/recipe properties below use their supported controls.
 const geometry={id:'sys1_preparation_room',width:13,height:9,layers:['#############','#...........#','#...........#','#...........#','#.....~.....#','#...........#','#.<.........#','#...........#','#############'],legend:{'#':'wall','.':'floor','<':'stairs_up','~':'shallow_water'},player_start:{x:3,y:6},special_tiles:[]};
 await editor().locator('textarea.source-editor').fill(JSON.stringify(geometry,null,2));await editIdle();await b('Authored layout').click();
 const ids=['clay_pot','copper_steeping_kettle','waxed_water_flask','small_steeping_cup','resonant_bone_fragment','resonant_bone_fragment'];
 for(let i=0;i<ids.length;i++){await select('Placement kind','item');await select('Placement item',ids[i]);await b('Place item').click();await cell(i+2,3);}
 await select('Placement kind','decor');await select('Placement decor','campfire_lit');await b('Place decor').click();await cell(6,6);
 await apply(room);
}
async function walk(x,y){
 const directions=[[1,0,'right'],[-1,0,'left'],[0,1,'down'],[0,-1,'up']];
 for(let n=0;n<100;n++){
  const o=await observe();if(o.player[0]===x&&o.player[1]===y)return o;
  const q=[[...o.player,[]]],seen=new Set([o.player.join(',')]);let route;
  for(let j=0;j<q.length;j++){const [a,c,p]=q[j];if(a===x&&c===y){route=p;break;}for(const [dx,dy,k] of directions){const nx=a+dx,ny=c+dy,id=`${nx},${ny}`;if(seen.has(id)||!o.walkable[ny]?.[nx]||o.actors.some(a=>a.x===nx&&a.y===ny))continue;seen.add(id);q.push([nx,ny,[...p,k]]);}}
  assert(route?.length,`No route to ${x},${y}`);await key(route[0]);
 }throw Error('bounded walk exhausted');
}
async function selectInventory(id){let o=await observe();if(!o.inventory_open)o=await key('i');const n=o.inventory_rows.findIndex(r=>!r.header&&r.item_id===id);assert(n>=0,id);while(o.inventory_selected!==n)o=await key(o.inventory_selected<n?'down':'up');return o;}
async function menu(n){for(let i=0;i<n;i++)await key('down');return key('return');}
async function water(id,action,choice=0){await selectInventory(id);await key('e');await menu(action);if(action===0){await menu(0);return menu(choice);}return observe();}
async function craft(id='resonant_bone_tincture',vessel='clay_pot'){
 let o=await observe();if(o.inventory_open)await key('escape');o=await key('c');const n=o.craft.rows.findIndex(r=>r.id===id);assert(n>=0);while(o.craft.selected!==n)o=await key(o.craft.selected<n?'down':'up');o=await key('return');
 if(o.craft.choosing){const p=o.craft.prompts[o.craft.choice_index],v=p.options.findIndex(i=>i.item_id===vessel);assert(v>=0);for(let i=0;i<v;i++)await key('down');o=await key('return');}
 return o;
}
async function acquire(){
 let o=await observe();for(const tile of o.floor.filter(r=>r.items.some(i=>['clay_pot',...specs.map(s=>s[0]),'resonant_bone_fragment'].includes(i.item_id)))){await walk(tile.x,tile.y);await key(',');}
 await walk(39,22);return observe(); // room origin (33,17), adjacent to water (39,21) and fire (39,23)
}
async function witness(vessel='clay_pot',batch=250){
 await acquire();let o=await water(vessel,0);assert.equal(o.inventory.find(i=>i.item_id===vessel).vessel.water_ml,batch);
 o=await craft('resonant_bone_tincture',vessel);assert.equal(o.mode,'PLACEMENT_CURSOR',JSON.stringify(o.logs));o=await key('return');
 assert.equal(o.processing.length,1);assert.equal(o.processing[0].turns_remaining,34);assert(!o.inventory.some(i=>i.item_id===vessel));
 const id=o.processing[0].vessel_job.vessel.vessel.id;await key('f5');o=await key('f9');assert.equal(o.processing[0].vessel_job.vessel.vessel.id,id);
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,`${vessel}-busy.png`));
 for(let i=0;i<34;i++)o=await key('.');assert.equal(o.processing.length,0);
 const delivered=o.floor.flatMap(r=>r.items);assert.equal(delivered.filter(i=>i.item_id==='resonant_bone_tincture').length,1);assert(delivered.some(i=>i.vessel?.id===id));
 return {vessel,batch,id,final:o,captured:(await status()).captured};
}
async function stop(){await b('Stop').click();await until(async()=>(await status()).status==='stopped');}
try{
 const env={...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9591 --remote-debugging-address=127.0.0.1'};
 spawn('cscript.exe',['//nologo',resolve('Launch Workbench.vbs')],{cwd:output,windowsHide:true,stdio:'ignore',env});
 await until(async()=>{try{return (await (await fetch('http://127.0.0.1:9591/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9591');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);
 const pid=Number(execFileSync('powershell.exe',['-NoProfile','-Command',"(Get-CimInstance Win32_Process -Filter \"name='resonance-workbench.exe'\" | Where-Object { $_.CommandLine -notlike '*--test*' } | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId"],{encoding:'utf8',windowsHide:true}).trim());
 child={pid};page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();
 if(process.env.SYS1_RUNTIME_ONLY!=='1'){
  await phase('Author three vessel variants through packaged Item controls');for(const s of specs)await vessel(s);await makeRoom();
 }
 await phase('Packaged saved room: acquire, measured fill, actual selected vessel and processing');
 await open(room);await start('latest');receipt.clay=await witness();await stop();
 await open(room);await start('latest');await acquire();let o=await water('copper_steeping_kettle',0,1);
 assert.equal(o.inventory.find(i=>i.item_id==='copper_steeping_kettle').vessel.water_ml,1000);
 await selectInventory('copper_steeping_kettle');await key('e');await menu(1);await menu(0);o=await menu(0);
 assert.equal(o.inventory.find(i=>i.item_id==='clay_pot').vessel.water_ml,250);
 assert.equal(o.inventory.find(i=>i.item_id==='copper_steeping_kettle').vessel.water_ml,750);receipt.transfer=o;
 o=await water('waxed_water_flask',0);const before=o;
 o=await craft('resonant_bone_tincture','waxed_water_flask');assert.equal(o.turn,before.turn);assert.equal(o.inventory.find(i=>i.item_id==='waxed_water_flask').vessel.water_ml,250);assert(o.logs.some(s=>s.includes('heatproof')));receipt.unsuitable=o;
 await stop();
 if(process.env.SYS1_RUNTIME_ONLY!=='1'){
  await phase('Recipe batch edit, undo/redo, captured Reset and excluded dirty draft');
  await open(room);await start('latest');const captured=(await status()).captured.manifest_sha256;
  await open(recipe);await begin();await b('Requirements').click();await fill('Batch water (mL)',125);
  await b('Undo recipe').click();await editIdle();assert.equal(await page.getByLabel('Batch water (mL)',{exact:true}).inputValue(),'250');await b('Redo recipe').click();await editIdle();await apply(recipe);
  await open(room);await start('reset');assert.equal((await status()).captured.manifest_sha256,captured);receipt.resetOriginal=await witness('clay_pot',250);await start('latest');assert.notEqual((await status()).captured.manifest_sha256,captured);
  receipt.changedBatch=await witness('small_steeping_cup',125);await stop();
  await open(recipe);await begin();await b('Requirements').click();await fill('Batch water (mL)',250);await apply(recipe);
  await begin();await fill('Batch water (mL)',200);await open(room);await start('latest');receipt.dirtyExcluded=await witness('clay_pot',250);await stop();
  await open(recipe);await begin();await b('Requirements').click();assert.equal(await page.getByLabel('Batch water (mL)',{exact:true}).inputValue(),'200');
  await b('Undo recipe').click();await editIdle();assert.equal(await page.getByLabel('Batch water (mL)',{exact:true}).inputValue(),'250');
  await fill('Batch water (mL)',0);await eb('Validate draft').click();await idle();receipt.invalid=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!receipt.invalid.valid);await b('Undo recipe').click();await editIdle();
 }
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,p);
 receipt.unchanged_sources=baseline;
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('SYS-1 native flow passed');
}catch(error){receipt.failure=String(error.stack||error);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
