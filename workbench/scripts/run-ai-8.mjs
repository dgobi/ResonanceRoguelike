// AI-8 commissioned exact-source authoring and actual packaged app-local play.
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/ai-8',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
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

const actorSpecs=[
 ['barrow_alarm_sentinel','Barrow Alarm Sentinel','territorial_guard',true,false],
 ['barrow_alarm_skirmisher','Barrow Alarm Skirmisher','strike_and_withdraw',false,true],
 ['barrow_alarm_runner','Barrow Alarm Runner','strike_and_withdraw',true,false],
 ['barrow_alarm_watch','Barrow Alarm Watch','territorial_guard',true,true],
];
async function check(label,value){const control=page.getByLabel(label,{exact:true}).filter({visible:true});await control.setChecked(value);await editIdle();}
async function creature([id,name,recipe,call,answer]){
 const path=base+id+'.json',fresh=!(await exists(path));await open(fresh?base+'hollow_revenant.json':path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);await select('Creature AI','composite');await select('Behaviour recipe',recipe);}
 await fill('Creature name',name);await fill('Creature description','A hollow figure listens among the old stores.');await fill('Speed',1);
 await fill('Faction label','hollow');await b('Clear hostiles').click();await editIdle();await fill('Add hostile faction','player');await b('Add hostile').click();await editIdle();
 await check('Call on hostile sight',call);await check('Investigate allied alarm',answer);
 await page.getByRole('group',{name:'Enemy response components',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,id+'-controls.png')});
 await apply(path);const doc=await opened(path),raw=JSON.parse(doc.raw);assert.equal(raw.ai_profile.recipe,recipe);assert.equal(raw.perception.faction,'hollow');
 assert.deepEqual(raw.enemy_responses.modules.map(m=>m.id).sort(),[...(call?['alarm_call_on_sight']:[]),...(answer?['investigate_allied_alarm']:[])].sort());
 return path;
}
function layout(id,reverse=false,natural=false){
 const rows=Array.from({length:15},(_,y)=>Array.from({length:25},(_,x)=>x===0||x===24||y===0||y===14?'#':'.'));
 const wall=reverse?14:12;for(let y=1;y<=8;y++)rows[y][wall]='#';rows[5][wall]='+';rows[12][3]='<';
 return {id,width:25,height:15,layers:rows.map(r=>r.join('')),legend:{'#':'wall','.':'floor','+':'door_closed','<':'stairs_up'},player_start:natural?{x:3,y:12}:reverse?{x:8,y:5}:{x:5,y:5},special_tiles:[
  {type:'creature',x:reverse?12:9,y:5,creature_id:reverse?'barrow_alarm_runner':'barrow_alarm_sentinel'},
  {type:'creature',x:reverse?16:17,y:5,creature_id:reverse?'barrow_alarm_watch':'barrow_alarm_skirmisher'},
  {type:'item',x:20,y:4,item_id:'faceted_ward'},
  {type:'item',x:4,y:12,item_id:'letter',text_id:'barrow_ward_store_note_a'},
  {type:'container',x:8,y:11,decor_id:'crate',loot_pools:[]}]};
}
async function room(id,reverse=false,natural=false){
 const path='roguelike/data/layouts/'+id+'.json',fresh=!(await exists(path));await open(fresh?'roguelike/data/layouts/barrow_ward_store_b.json':path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await b('Source').click();await fill('Draft JSON',JSON.stringify(layout(id,reverse,natural),null,2));await apply(path,fresh);return path;
}
async function stop(){await b('Stop').click();await until(async()=>(await status()).status==='stopped');}
async function witness(id){
 await open('roguelike/data/layouts/'+id+'.json');await start('latest');receipt[id]={initial:await status(),phases:[]};
 for(let n=0;n<5;n++){await key('.');receipt[id].phases.push(await status());}
 const phases=receipt[id].phases,tactics=phases.map(p=>p.tactics.actors);
 assert(tactics.some(rows=>rows.some(a=>a.response_trace.some(t=>t.reason==='emitted'))),'real emitted call');
 assert(tactics.some(rows=>rows.some(a=>a.response_trace.some(t=>t.reason==='accepted'))),'real receipt');
 assert(tactics.some(rows=>rows.some(a=>a.recent.some(t=>t.reason==='alarm_investigating'))),'real investigation step');
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,id+'.png'));await stop();
}
try{
 const env={...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9588 --remote-debugging-address=127.0.0.1'};
 spawn('cscript.exe',['//nologo',resolve('Launch Workbench.vbs')],{cwd:output,windowsHide:true,stdio:'ignore',env});
 await until(async()=>{try{return (await (await fetch('http://127.0.0.1:9588/json/list')).json()).length;}catch{return false;}});
 const pid=Number(execFileSync('powershell.exe',['-NoProfile','-Command',"(Get-Process resonance-workbench | Sort-Object StartTime -Descending | Select-Object -First 1).Id"],{encoding:'utf8',windowsHide:true}).trim());child={pid};receipt.launch={entry:'workbench/Launch Workbench.vbs',pid};
 browser=await chromium.connectOverCDP('http://127.0.0.1:9588');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();
 if(process.env.AI8_RUNTIME_ONLY!=='1'){
  await phase('publish four reusable component combinations through the packaged creature controls');
  for(const spec of actorSpecs)await creature(spec);
  await phase('publish two Test rooms and one ordinary barrow variant');
  await room('ai8_alarm_crossing');await room('ai8_alarm_reverse',true);await room('barrow_ward_store_c',false,true);
 }
 await phase('actual game call, receipt and delayed physical investigation on both host recipes');
 await witness('ai8_alarm_crossing');await witness('ai8_alarm_reverse');
 if(process.env.AI8_RUNTIME_ONLY!=='1'){
  await phase('module participation edit, undo/redo, save, captured reset and latest saved dependency');
  const path=base+'barrow_alarm_sentinel.json',roomPath='roguelike/data/layouts/ai8_alarm_crossing.json';
  await open(roomPath);await start('latest');const captured=(await status()).captured.manifest_sha256;
  await open(path);await begin();await check('Call on hostile sight',false);await b('Undo creature').click();await editIdle();assert(await page.getByLabel('Call on hostile sight',{exact:true}).filter({visible:true}).isChecked());await b('Redo creature').click();await editIdle();await apply(path);
  await open(roomPath);await start('reset');assert.equal((await status()).captured.manifest_sha256,captured);receipt.reset=await status();
  await start('latest');assert.notEqual((await status()).captured.manifest_sha256,captured);for(let i=0;i<4;i++)await key('.');receipt.disabled=await status();assert(!receipt.disabled.tactics.actors.some(a=>a.response_trace.some(t=>t.reason==='emitted'||t.reason==='accepted')));
  await open(path);await begin();await check('Call on hostile sight',true);await open(roomPath);await start('latest');for(let i=0;i<3;i++)await key('.');receipt.dirty=await status();assert(!receipt.dirty.tactics.actors.some(a=>a.response_trace.some(t=>t.reason==='emitted')));await stop();
  await open(path);await begin();await apply(path);
  // Invalid explicit faction is rejected by the game-owned validator; undo restores exact bytes.
  await begin();await fill('Faction label','player');await eb('Validate draft').click();await idle();const invalid=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!invalid.valid);receipt.invalid=invalid;await b('Undo creature').click();await editIdle();
  await witness('ai8_alarm_crossing');
 }
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,`preserve ${p}`);
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('native component authoring and room lifecycle passed');
}catch(error){receipt.failure=String(error.stack||error);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}



