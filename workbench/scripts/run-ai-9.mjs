// AI-9 commissioned exact-source authoring and actual packaged app-local play.
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/ai-9',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
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

const specs=[
 ['hollow_revenant','barrow_lane_revenant','Store Revenant','strike_and_withdraw',true,true,true,true,'It circles between the old shelves, one shoulder hanging low.'],
 ['gloam_stalker','barrow_shy_stalker','Shy Store Watcher','observation_averse',true,false,false,true,'Its pale joints fold away from the light.'],
 ['nettle_stalker','barrow_nettle_guard','Nettle Store Guard','venom_strike_and_withdraw',false,true,true,false,'Wet spines quiver along its jaw.'],
 ['patient_amber_hunter','barrow_patient_weevil','Barrow Shell Hunter','patient_venom_hunt',true,true,false,true,'A split amber shell moves between the broken stones.'],
 ['barrow_sentinel','barrow_kin_sentinel','Store Sentinel','territorial_guard',false,true,true,false,'It stands where the storeroom wall once joined the arch.'],
 ['barrow_shy_stalker','barrow_shy_listener','Shy Store Listener','observation_averse',false,true,false,true,'Its head turns toward a cry; its body keeps to shadow.'],
];
async function check(label,value){await page.getByLabel(label,{exact:true}).filter({visible:true}).setChecked(value);await editIdle();}
async function creature([source,id,name,recipe,flank,regroup,call,answer,description]){
 const path=base+id+'.json',fresh=!(await exists(path));
 const sourceBytes=await readFile(resolve(root,base+source+'.json'));baseline[base+source+'.json']=hash(sourceBytes);
 await open(fresh?base+source+'.json':path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);if(source==='hollow_revenant')await select('Creature AI','composite');await select('Behaviour recipe',recipe);}
 await fill('Creature name',name);await fill('Creature description',description);await fill('Speed',1);
 await fill('Faction label','hollow');await b('Clear hostiles').click();await editIdle();await fill('Add hostile faction','player');await b('Add hostile').click();await editIdle();
 await select('Alarm compatibility','2');await check('Call on hostile sight',call);await check('Investigate allied alarm',answer);
 await check('Seek lateral approach',flank);await check('Regroup when wounded',regroup);
 if(regroup)await fill('Regroup when wounded: wounded percent (percent HP)',50);
 if(recipe==='patient_venom_hunt')await check('Sees in dark',true);
 if(recipe==='territorial_guard')await fill('Defended radius (tiles)',2);
 await page.getByRole('group',{name:'Enemy movement components',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,id+'-controls.png')});
 await apply(path);const doc=await opened(path),raw=JSON.parse(doc.raw),original=JSON.parse(sourceBytes);
 assert.equal(raw.ai_profile.recipe,recipe);assert.equal(raw.tile,original.tile);assert.deepEqual(raw.limbs,original.limbs);
 assert.deepEqual(raw.enemy_maneuvers.modules.map(m=>m.id).sort(),[...(flank?['seek_lateral_approach']:[]),...(regroup?['regroup_when_wounded']:[])].sort());
 return path;
}
const rooms=[
 ['ai9_lateral_lane','barrow_lane_revenant',10,6,'barrow_kin_sentinel',8,5,5,5,'open'],
 ['ai9_venom_lane','barrow_nettle_guard',9,5,'barrow_patient_weevil',17,5,5,5,'divided'],
 ['ai9_shadow_lane','barrow_shy_stalker',10,5,'barrow_shy_listener',14,6,5,5,'open'],
 ['barrow_ward_store_d','barrow_lane_revenant',10,6,'barrow_kin_sentinel',8,5,3,12,'open'],
 ['barrow_ward_store_e','barrow_shy_stalker',9,5,'barrow_patient_weevil',17,5,3,12,'broken'],
];
async function room([id,first,x,y,second,bx,by,px,py,geometry]){
 const path='roguelike/data/layouts/'+id+'.json',fresh=!(await exists(path));
 await open(fresh?'roguelike/data/layouts/barrow_ward_store_c.json':path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await b('Authored layout').click();
 if(fresh&&geometry==='open'){
  await select('Active layer','terrain');await select('Terrain brush','.');await rectangle(12,4,12,8);
 }
 if(fresh&&geometry==='broken'){
  await select('Active layer','terrain');await select('Terrain brush','#');await rectangle(4,8,10,8);
  await select('Terrain brush','.');await b(/^Pencil /).click();await cell(7,8);
 }
 await fill('Arrival X',px);await fill('Arrival Y',py);await b('Apply arrival').click();await editIdle();
 await select('Active layer','specials');
 for(const [index,actor,cx,cy] of [[0,first,x,y],[1,second,bx,by]]){
  await select('Placed record',String(index));await select('Marker creature ID',actor);await fill('Creature source X',cx);await fill('Creature source Y',cy);await b('Apply creature edit').click();await editIdle();
 }
 await apply(path,fresh);const raw=JSON.parse((await opened(path)).raw);
 assert.deepEqual(raw.special_tiles.filter(r=>r.type==='creature').map(r=>r.creature_id),[first,second]);
 return path;
}
async function stop(){await b('Stop').click();await until(async()=>(await status()).status==='stopped');}
async function witness(id,phases=5){
 await open('roguelike/data/layouts/'+id+'.json');await start('test');
 const rows=[];let saved=false;
 for(let n=0;n<phases;n++){
  await key('.');const s=await status();rows.push(s);
  assert(s.tactics?.actors?.length>=1,'native actual game actors');
  if(!saved){
   const prior=s.tactics.actors.map(a=>({id:a.individual_id,state:a.state,m:a.maneuver_state,r:a.response_state}));
   await key('f5');await key('f9');const current=await status();
   assert.deepEqual(current.tactics.actors.map(a=>({id:a.individual_id,state:a.state,m:a.maneuver_state,r:a.response_state})),prior);
   saved=true;
  }
 }
 receipt[id]={phases:rows,captured:(await status()).captured,persistence:saved};
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,id+'.png'));await stop();
}
try{
 const env={...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9589 --remote-debugging-address=127.0.0.1'};
 spawn('cscript.exe',['//nologo',resolve('Launch Workbench.vbs')],{cwd:output,windowsHide:true,stdio:'ignore',env});
 await until(async()=>{try{return (await (await fetch('http://127.0.0.1:9589/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9589');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);
 const pid=Number(execFileSync('powershell.exe',['-NoProfile','-Command',"(Get-CimInstance Win32_Process -Filter \"name='resonance-workbench.exe'\" | Where-Object { $_.CommandLine -notlike '*--test*' } | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId"],{encoding:'utf8',windowsHide:true}).trim());
 child={pid};receipt.launch={entry:'workbench/Launch Workbench.vbs',pid};
 page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();
 if(process.env.AI9_RUNTIME_ONLY!=='1'){
  await phase('Create five independent family configurations through actual creature controls');
  for(const spec of specs.slice(0,5))await creature(spec);
  await phase('Create further observation-averse recombination through the same controls');await creature(specs[5]);
  await phase('Place all families in saved rooms using actual canvas and placement controls');
  for(const spec of rooms)await room(spec);
 }
 await phase('Packaged Test room, live actions and exact F5/F9 for every authored family');
 for(const [id] of rooms.slice(0,3))await witness(id);
 if(process.env.AI9_RUNTIME_ONLY!=='1'){
  await phase('Movement participation edit, undo/redo, captured Reset versus latest saved and parked dirty draft');
  const path=base+'barrow_lane_revenant.json',roomPath='roguelike/data/layouts/ai9_lateral_lane.json';
  await open(roomPath);await start('latest');const captured=(await status()).captured.manifest_sha256;
  await open(path);await begin();await check('Seek lateral approach',false);await b('Undo creature').click();await editIdle();assert(await page.getByLabel('Seek lateral approach',{exact:true}).filter({visible:true}).isChecked());
  await b('Redo creature').click();await editIdle();await apply(path);
  await open(roomPath);await start('reset');assert.equal((await status()).captured.manifest_sha256,captured);receipt.reset=await status();
  await start('latest');assert.notEqual((await status()).captured.manifest_sha256,captured);
  for(let i=0;i<6;i++)await key('.');receipt.disabled=await status();
  assert(!receipt.disabled.tactics.actors.find(a=>a.id==='barrow_lane_revenant').enemy_maneuvers.modules.some(m=>m.id==='seek_lateral_approach'));
  await open(path);await begin();await check('Seek lateral approach',true);await open(roomPath);await start('latest');for(let i=0;i<3;i++)await key('.');receipt.dirty=await status();
  assert(!receipt.dirty.tactics.actors.find(a=>a.id==='barrow_lane_revenant').enemy_maneuvers.modules.some(m=>m.id==='seek_lateral_approach'));await stop();
  await open(path);await begin();await apply(path);await begin();await fill('Regroup when wounded: rearm percent (percent HP)',40);
  await eb('Validate draft').click();await idle();receipt.invalid=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!receipt.invalid.valid);
  await b('Undo creature').click();await editIdle();await open(roomPath);await witness('ai9_lateral_lane',8);
  const enabled=receipt.ai9_lateral_lane.phases.find(s=>s.tactics.turn===receipt.disabled.tactics.turn);
  const enabledActor=enabled.tactics.actors.find(a=>a.id==='barrow_lane_revenant');
  const disabledActor=receipt.disabled.tactics.actors.find(a=>a.id==='barrow_lane_revenant');
  assert(enabledActor.recent.some(t=>t.reason==='lateral_approach'));
  assert(!disabledActor.recent.some(t=>t.reason==='lateral_approach'));
  assert.notDeepEqual(enabledActor.position,disabledActor.position,'saved component change must alter actual approach position under matched inputs');
  receipt.behaviourComparison={turn:enabled.tactics.turn,enabled:enabledActor.position,disabled:disabledActor.position};
 }
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,`preserve ${p}`);
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('AI-9 packaged authoring and saved-room lifecycle passed');
}catch(error){receipt.failure=String(error.stack||error);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
