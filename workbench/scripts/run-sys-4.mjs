// SYS-4 commissioned exact-source authoring and actual packaged app-local play.
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/sys-4',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
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
async function apply(path,variant=false){await editIdle();await idle();if(await eb('Validate draft').isDisabled()){const doc=await opened(path);(receipt.reopened??=[]).push({path,sha256:doc.sha256});return doc;}const r=await validate();for(let attempt=0;attempt<4;attempt++){await eb(await eb('Review & apply').count()?'Review & apply':'Apply variant').click();try{await b('Confirm apply one file').waitFor({timeout:2000});break;}catch{await editIdle();await idle();}}await b('Confirm apply one file').click();await idle();await page.getByText(/Saved and byte-checked reopen:/).waitFor({timeout:60000});const doc=await opened(path);receipt.publications.push({path,sha256:doc.sha256,definition:JSON.parse(doc.raw),review:r});return doc;}
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

async function walk(x,y){
 const directions=[[1,0,'right'],[-1,0,'left'],[0,1,'down'],[0,-1,'up']];
 for(let n=0;n<100;n++){
  const o=await observe();if(o.player[0]===x&&o.player[1]===y)return o;
  const q=[[...o.player,[]]],seen=new Set([o.player.join(',')]);let route;
  for(let j=0;j<q.length;j++){const [a,c,p]=q[j];if(a===x&&c===y){route=p;break;}for(const [dx,dy,k] of directions){const nx=a+dx,ny=c+dy,id=`${nx},${ny}`;if(seen.has(id)||!o.walkable[ny]?.[nx]||o.actors.some(a=>a.x===nx&&a.y===ny)||o.containers.some(a=>a.x===nx&&a.y===ny))continue;seen.add(id);q.push([nx,ny,[...p,k]]);}}
  assert(route?.length,`No route to ${x},${y}`);await key(route[0]);
 }throw Error('bounded walk exhausted');
}
async function selectInventory(id){let o=await observe();if(!o.inventory_open)o=await key('i');const n=o.inventory_rows.findIndex(r=>!r.header&&r.item_id===id);assert(n>=0,id);while(o.inventory_selected!==n)o=await key(o.inventory_selected<n?'down':'up');return o;}
async function menu(n){for(let i=0;i<n;i++)await key('down');return key('return');}

const profile='roguelike/data/access_profiles/woven_lashings.json',room='roguelike/data/layouts/sys4_access_room.json';
async function source(value){await eb('Source').click();await editor().locator('textarea.source-editor').fill(JSON.stringify(value,null,2));await editIdle();}
async function makeProfile(){
 const fresh=!(await exists(profile));await open(fresh?'roguelike/data/access_profiles/pale_lashings.json':profile);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID','woven_lashings');}
 await fill('Fastening name','Woven lashings');await fill('Careful work steps',2);await apply(profile);
 await begin();await fill('Careful work steps',0);await eb('Validate draft').click();await idle();
 const invalid=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!invalid.valid);
 await b('Undo fastening').click();await editIdle();await page.screenshot({path:resolve(output,'profile-controls.png')});
}
async function makeRoom(){
 const fresh=!(await exists(room));await open(fresh?template:room);await begin();if(fresh){await eb('Save as new variant').click();await fill('New variant ID','sys4_access_room');}
 const raw=JSON.parse(await readFile(resolve(root,'roguelike/data/layouts/barrow_bound_store.json'),'utf8'));
 raw.id='sys4_access_room';delete raw.description;raw.special_tiles=[];
 await source(raw);await b('Authored layout').click();
 for(const [id,x,y] of [['crude_blade',4,12],['etching_wash',5,12],['bile_coating',6,12]]){
  await select('Placement kind','item');await select('Placement item',id);await b('Place item').click();await cell(x,y);
 }
 await select('Placement kind','container');await select('Placement container','bound_coffer');await select('Placement fastening profile','woven_lashings');await b('Place container').click();await cell(7,5);
 await cell(7,5);await b('Add existing pool').click();await select('Loot pool 1','bound_coffer_stores');await b('Apply container edit').click();await editIdle();
 await select('Placement kind','screen');await select('Placement fastening profile','woven_lashings');await b('Place screen').click();await cell(11,6);
 await select('Placement kind','decor');await select('Placement decor','campfire_lit');await b('Place decor').click();await cell(14,6);
 await select('Placement kind','creature');await select('Placement creature','hollow_revenant');await b('Place creature').click();await cell(18,2);
 await apply(room);await begin();await b('Authored layout').click();
 await select('Placement kind','screen');await select('Placement fastening profile','woven_lashings');await b('Place screen').click();await cell(3,12);
 await eb('Validate draft').click();await idle();const invalid=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!invalid.valid);
 await b('Undo canvas').click();await editIdle();await page.screenshot({path:resolve(output,'host-placement.png')});
}
async function interact(x,y){let o=await key('e');while(o.interaction.cursor[0]!==x)o=await key(o.interaction.cursor[0]<x?'right':'left');while(o.interaction.cursor[1]!==y)o=await key(o.interaction.cursor[1]<y?'down':'up');return key('return');}
async function accessMethod(x,y,method){let o=await interact(x,y);assert(o.vessel_menu,JSON.stringify(o.logs));const n=o.vessel_menu.options.findIndex(s=>s.startsWith(method));assert(n>=0,method);o=await menu(n);if(method==='Dissolution'){assert(o.vessel_menu.options.every(s=>s.includes('spend whole dose')));o=await menu(0);}return o;}
async function freezeTargets(){
 // Existing disclosed native diagnostic: inert extended-HP target for geometry.
 // Living tactical claims are measured separately in the ordinary-world runs.
 const id=++eventId;await writeFile(resolve(session.state_root,'event.json'),JSON.stringify({id,fixture:'coating-contact-targets'}));
 await until(async()=>{const o=await observe();return o.applied===id&&o.fixture_applied;});
}
async function acquire(){
 await freezeTargets();let o=await observe();
 if(o.light){await selectInventory('tallow_torch');await key('e');await key('escape');assert(!(await observe()).light);}
 for(const tile of o.floor){await walk(tile.x,tile.y);await key(',');}
 await selectInventory('crude_blade');await key('e');await key('escape');return observe();
}
async function witness(method='Careful',steps=2){
 await phase(`Actual game witness: ${method}, captured ${steps} steps`);
 await acquire();let o=await observe();const coffer=o.access_objects.find(r=>r.host==='container'),screen=o.access_objects.find(r=>r.host==='screen');
 assert.equal(screen.profile.work_steps,steps);assert.equal(coffer.profile.id,screen.profile.id);
 const original=o.containers.find(c=>c.x===coffer.x&&c.y===coffer.y).items.map(i=>i.instance);
 await walk(coffer.x-1,coffer.y);let turn=(await observe()).turn;
 if(method==='Careful')for(let n=0;n<steps;n++){o=await accessMethod(coffer.x,coffer.y,n?'Continue':'Careful');assert.equal(o.turn,turn+n+1);}
 else o=await accessMethod(coffer.x,coffer.y,method);
 assert.equal(o.access_objects.find(r=>r.host==='container').completed_by,method==='Careful'?'careful':method==='Quick force'?'force':'dissolution');
 assert.deepEqual(o.containers.find(c=>c.x===coffer.x&&c.y===coffer.y).items.map(i=>i.instance),original);
 o=await interact(coffer.x,coffer.y);assert.deepEqual(o.interaction.selection.items.map(i=>i.instance),original);
 for(let i=0;i<original.length;i++)await key('down');o=await key('return');assert(original.every(id=>o.inventory.some(i=>i.instance===id)));
 await walk(screen.x-1,screen.y);o=await observe();const before={turn:o.turn,lit:o.illumination.lit[screen.y][screen.x-1],visible:o.visible_tiles[screen.y][screen.x+3]};
 assert(!o.walkable[screen.y][screen.x]);assert(!before.lit);assert(!before.visible);
 if(method==='Careful')for(let n=0;n<steps;n++)o=await accessMethod(screen.x,screen.y,n?'Continue':'Careful');
 else o=await accessMethod(screen.x,screen.y,method);
 assert(o.walkable[screen.y][screen.x]);assert(o.illumination.lit[screen.y][screen.x-1]);assert(o.visible_tiles[screen.y][screen.x+3]);
 assert.equal(o.turn-before.turn,method==='Careful'?steps:1);
 const salvage=o.floor.find(t=>t.x===screen.x&&t.y===screen.y)?.items??[];
 assert.equal(salvage.length,method==='Careful'?1:0);if(salvage.length)assert.equal(salvage[0].item_id,'wood_bundle');
 await key('right');o=await observe();assert.deepEqual(o.player,[screen.x,screen.y]);if(salvage.length){await key(',');}
 await key('f5');o=await key('f9');assert(o.access_objects.every(r=>r.completed_by));assert(o.walkable[screen.y][screen.x]);
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,`screen-${method.replaceAll(' ','-')}-${steps}-${Date.now()}.png`));
 return {method,steps,setup:'Authored test supplies; existing inert-target diagnostic. Actual action/transfer/geometry/light/save handlers. Not ordinary acquisition or tactical safety.',before,after:await observe(),captured:(await status()).captured};
}
async function stop(){await b('Stop').click();await until(async()=>(await status()).status==='stopped');}
try{
 const env={...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9594 --remote-debugging-address=127.0.0.1'};
 spawn('cscript.exe',['//nologo',resolve('Launch Workbench.vbs')],{cwd:output,windowsHide:true,stdio:'ignore',env});
 await until(async()=>{try{return (await (await fetch('http://127.0.0.1:9594/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9594');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);
 const pid=Number(execFileSync('powershell.exe',['-NoProfile','-Command',"(Get-CimInstance Win32_Process -Filter \"name='resonance-workbench.exe'\" | Where-Object { $_.CommandLine -notlike '*--test*' } | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId"],{encoding:'utf8',windowsHide:true}).trim());
 child={pid};page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();
 if(process.env.SYS4_RUNTIME_ONLY!=='1'){
  await phase('Packaged create/edit/publish profile and both host placements');await makeProfile();await makeRoom();
  await open(room);await start('latest');const captured=(await status()).captured.manifest_sha256;receipt.careful=await witness();
  await open(profile);await begin();await fill('Careful work steps',3);await apply(profile);
  await open(room);await start('reset');assert.equal((await status()).captured.manifest_sha256,captured);receipt.reset=await witness();
  await start('latest');receipt.revised=await witness('Careful',3);await stop();
  await open(profile);await begin();await fill('Careful work steps',4);
  await open(room);await start('latest');receipt.dirtyExcluded=await witness('Careful',3);await stop();
  await open(profile);await begin();await b('Undo fastening').click();await editIdle();await fill('Careful work steps',2);await apply(profile);
 }else{await open(room);await start('latest');receipt.careful=await witness();await stop();}
 for(const method of ['Quick force','Dissolution']){await open(room);await start('latest');receipt[method]=await witness(method);await stop();}
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,p);
 receipt.unchanged_sources=baseline;assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('SYS-4 packaged authoring/runtime passed');
}catch(error){receipt.failure=String(error.stack||error);receipt.failureText=await page?.locator('body').innerText().catch(()=>null);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}

