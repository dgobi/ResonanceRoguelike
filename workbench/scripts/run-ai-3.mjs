// Commissioned AI-3 authoring in production main; only named new examples/rooms
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/ai-3',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
await mkdir(settings,{recursive:true});
await writeFile(resolve(settings,'project.json'),JSON.stringify({version:1,project_root:root}));
const base='roguelike/data/entities/creatures/',template='roguelike/docs/examples/g17_authored_creature_room.json';
const exe=resolve('src-tauri/target/release/resonance-workbench.exe'),hash=b=>createHash('sha256').update(b).digest('hex');
const receipt={output,root,started_utc:new Date().toISOString(),package_sha256:hash(await readFile(exe)),checks:[],publications:[],errors:[]};
const baseline={};for(const p of [base+'heath_stalker.json',template])baseline[p]=hash(await readFile(resolve(root,p)));
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
 session=await until(async()=>{const s=await status();assert.notEqual(s.status,'failed',s.diagnostics||JSON.stringify(s));assert(!s.last_action_error&&!s.error,JSON.stringify(s));return s.status==='running'&&!s.preparing&&s.session_id!==previous?s:null;});eventId=0;
 await until(async()=>{try{return await observe();}catch{return null;}});return session;
}
async function key(key,capture=false){const id=++eventId,path=resolve(session.state_root,'event.json'),tmp=path+'.tmp';await writeFile(tmp,JSON.stringify({id,key,capture}));await until(async()=>{try{await rename(tmp,path);return true;}catch(e){if(!['EPERM','EACCES','EBUSY'].includes(e.code))throw e;return false;}});return until(async()=>{const s=await status();assert.notEqual(s.status,'failed',s.diagnostics||JSON.stringify(s));try{const o=await observe();return o.applied===id?o:null;}catch{return null;}});}

async function creature(source,id,name,warning){
 const path=base+id+'.json',fresh=!(await exists(path));await open(fresh?source:path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await fill('Creature name',name);
 if(fresh){if(source.endsWith('heath_stalker.json'))await select('Creature AI','composite');await select('Behaviour recipe','venom_strike_and_withdraw');}
 await fill('Creature description',warning===3?'A low, bristling hunter with wet fangs and a nettled hide.':'A low hunter with drooping eyelids and dark saliva along its jaws.');
 await fill('Damage dice','1d4');await fill('Damage bonus',1);await fill('Attack verb','bites at thee');await fill('Speed',1);
 await fill('Warning (charged phases)',warning);await fill('Full paralysis (charged phases)',2);await fill('Recovery protection (charged phases)',4);
 await fill('Desired retreat distance (tiles)',3);await fill('Full hold opportunities',3);await fill('Withdrawal opportunity budget',6);
 await page.screenshot({path:resolve(output,id+'-controls.png')});await apply(path);return path;
}
async function room(source,id,actor,opening=true,rival=false){
 const path='roguelike/data/layouts/'+id+'.json',fresh=!(await exists(path));await open(fresh?source:path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await b('Authored layout').click();
 if(fresh){
  await select('Active layer','terrain');await select('Terrain brush','.');await rectangle(1,1,15,9);
  if(opening){await select('Terrain brush','#');await rectangle(8,1,8,9);await fill('Legend glyph','+');await select('Legend terrain','door_closed');await b('Set legend mapping').click();await editIdle();await select('Terrain brush','+');await b(/^Pencil /).click();await cell(8,5);}
  await fill('Arrival X',7);await fill('Arrival Y',5);await b('Apply arrival').click();await editIdle();
 }
 await select('Active layer','specials');await select('Placed record','0');await select('Marker creature ID',actor);await fill('Creature source X',10);await fill('Creature source Y',5);await b('Apply creature edit').click();await editIdle();
 await select('Placed record','1');await select('Marker item ID','measured_venom_remedy');await fill('Item source X',7);await fill('Item source Y',5);await b('Apply item edit').click();await editIdle();
 if(fresh){
  await select('Placed record','2');await fill('Container X',5);await fill('Container Y',3);await b('Apply container edit').click();await editIdle();
  if(rival){await select('Placement kind','creature');await select('Placement creature','highland_bandit');await b('Place creature').click();await cell(11,5);}
 }
 await apply(path,fresh);return path;
}
async function witness(label,treatStage='warning'){
 const rows=[];
 await key(',');await key('right');
 for(let n=0;n<20;n++){
  await key('.');await new Promise(r=>setTimeout(r,60));const o=await observe(),s=await status();rows.push({observation:o,tactics:s.tactics});
  if(s.tactics.player_condition?.dose?.stage===treatStage)break;
 }
 let s=await status();assert.equal(s.tactics.player_condition?.dose?.stage,treatStage);
 const saved=structuredClone(s.tactics.player_condition),turn=s.tactics.turn;
 await key('f5');await key('f9');await new Promise(r=>setTimeout(r,150));s=await status();assert.deepEqual(s.tactics.player_condition,saved);assert.equal(s.tactics.turn,turn);
 if(treatStage==='paralysis'){
  const before=await observe();await key('down');const after=await observe();assert.equal(after.turn,before.turn);assert.deepEqual(after.player,before.player);
 }
 await key('i');
 for(let n=0;n<30;n++){
  const o=await observe(),row=o.inventory_rows[o.inventory_selected];if(row?.item_id==='measured_venom_remedy')break;
  await key('down');
 }
 const before=await observe();assert.equal(before.inventory_rows[before.inventory_selected]?.item_id,'measured_venom_remedy');
 await key('e');await new Promise(r=>setTimeout(r,100));const after=await observe();s=await status();
 if(treatStage==='paralysis'){
  assert.equal(after.turn,before.turn);assert.deepEqual(after.inventory,before.inventory);
  assert.deepEqual(s.tactics.player_condition,saved);
  await key('escape');
  const remaining=s.tactics.player_condition.dose.remaining;
  for(let n=0;n<remaining;n++){
   const phase=s.tactics.turn;await key('.');
   s=await until(async()=>{const next=await status();return next.tactics.turn===phase+1?next:null;});
  }
  assert.equal(s.tactics.player_condition.dose.stage,'recovery');assert.equal(s.tactics.player_condition.dose.remaining,4);
 }else{
  assert.equal(after.turn,before.turn+1);assert.equal(after.inventory.filter(i=>i.item_id==='measured_venom_remedy').length,before.inventory.filter(i=>i.item_id==='measured_venom_remedy').length-1);
  assert.equal(s.tactics.player_condition.dose.stage,'recovery');assert.equal(s.tactics.player_condition.dose.remaining,3);
  await key('escape');
 }
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,label+'.png'));
 receipt[label]={capture:s.captured,rows,persistence:saved,treatment:{before,after,condition:s.tactics.player_condition}};
 await writeFile(resolve(output,label+'.json'),JSON.stringify(receipt[label],null,2));
}
try{
 child=spawn(exe,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9583 --remote-debugging-address=127.0.0.1'}});
 await until(async()=>{assert.equal(child.exitCode,null);try{return (await (await fetch('http://127.0.0.1:9583/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9583');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();

 const primary=base+'nettle_stalker.json',variant=base+'drowsing_stalker.json';
 const opening='roguelike/data/layouts/ai3_nettle_opening.json',long='roguelike/data/layouts/ai3_drowsing_opening.json',rival='roguelike/data/layouts/ai3_rival_ground.json';
 if(process.env.AI3_RUNTIME_ONLY!=='1'){
  await phase('create, tune, review and reopen matched venom sources through controls');
  await creature(base+'heath_stalker.json','nettle_stalker','Nettle Stalker',3);
  await open(primary);await begin();await fill('Warning (charged phases)',4);await b('Undo creature').click();await editIdle();assert.equal(await page.getByLabel('Warning (charged phases)',{exact:true}).inputValue(),'3');await b('Redo creature').click();await editIdle();await apply(primary);
  await open(primary);await begin();await fill('Warning (charged phases)',3);await apply(primary);
  await creature(primary,'drowsing_stalker','Drowsing Stalker',6);
  await phase('duplicate the registered treatment seed into a usable new ID');
  const treatment='roguelike/data/items/consumables/measured_venom_remedy.json';
  await open(await exists(treatment)?treatment:'roguelike/data/items/consumables/venom_treatment.json');await begin();
  if(!(await exists(treatment))){await eb('Save as new variant').click();await fill('New variant ID','measured_venom_remedy');}
  await fill('Item name','Measured Venom Remedy');await apply(treatment);
  await phase('place saved creatures, remedy and ordinary rival through room controls');
  await room('roguelike/data/layouts/ai1_skirmisher_room.json','ai3_nettle_opening','nettle_stalker');
  await room(opening,'ai3_drowsing_opening','drowsing_stalker');
  await room('roguelike/data/layouts/ai1_skirmisher_room.json','ai3_rival_ground','nettle_stalker',false,true);
 }
 await phase('packaged delivery, warning treatment, severe rejection, F5/F9 and captured lifecycle');
 await open(opening);await start();await witness('warning_treatment','warning');
 const original=receipt.warning_treatment.capture.manifest_sha256;
 await start('reset');assert.equal((await status()).captured.manifest_sha256,original);await witness('paralysis_rejection','paralysis');
 await b('Stop').click();await until(async()=>(await status()).status==='stopped');
 await open(long);await start('latest');await witness('long_warning','warning');
 await b('Stop').click();await until(async()=>(await status()).status==='stopped');
 await open(variant);await begin();await fill('Warning (charged phases)',7);
 await open(long);await start('latest');assert.equal((await status()).captured.manifest_sha256,receipt.long_warning.capture.manifest_sha256);
 receipt.dirty_dependency=await status();await b('Stop').click();await until(async()=>(await status()).status==='stopped');
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,`preserve ${p}`);
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('source preserved; reset, stop, latest saved and dirty exclusion established');
}catch(error){receipt.failure=String(error.stack||error);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child&&child.exitCode===null){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
