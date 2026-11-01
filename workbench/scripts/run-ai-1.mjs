// Commissioned AI-1 authoring in production main; only named new examples/rooms
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/ai-1',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
await mkdir(settings,{recursive:true});
await writeFile(resolve(settings,'project.json'),JSON.stringify({version:1,project_root:root}));
const base='roguelike/data/entities/creatures/',template='roguelike/docs/examples/g17_authored_creature_room.json';
const exe=resolve('src-tauri/target/release/resonance-workbench.exe'),hash=b=>createHash('sha256').update(b).digest('hex');
const receipt={output,root,started_utc:new Date().toISOString(),package_sha256:hash(await readFile(exe)),checks:[],publications:[],errors:[]};
const baseline={};for(const p of [base+'hollow_revenant.json',template])baseline[p]=hash(await readFile(resolve(root,p)));
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
async function validate(){await editIdle();await idle();await eb('Validate draft').click();await idle();const r=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(r.valid&&r.review_token,JSON.stringify(r));return r;}
async function begin(){if(await eb('Begin edit').count())await eb('Begin edit').click();}
async function apply(path,variant=false){await editIdle();await idle();if(await eb('Validate draft').isDisabled()){const doc=await opened(path);(receipt.reopened??=[]).push({path,sha256:doc.sha256});return doc;}const r=await validate();await eb(await eb('Review & apply').count()?'Review & apply':'Apply variant').click();await b('Confirm apply one file').click();await idle();await page.getByText(/Saved and byte-checked reopen:/).waitFor({timeout:60000});const doc=await opened(path);receipt.publications.push({path,sha256:doc.sha256,definition:JSON.parse(doc.raw),review:r});return doc;}
async function creature(source,id,name,trigger,distance,hold,budget){
 const path=base+id+'.json',fresh=!(await exists(path));await open(fresh?source:path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await fill('Creature name',name);if(fresh)await select('Creature AI','composite');
 await select('Withdrawal trigger',trigger);await fill('Desired retreat distance (tiles)',distance);await fill('Full hold opportunities',hold);await fill('Withdrawal opportunity budget',budget);
 await page.screenshot({path:resolve(output,id+'-controls.png')});
 await apply(path);return path;
}
async function cell(x,y){const map=page.getByTestId('layout-map').filter({visible:true});await map.scrollIntoViewIfNeeded();const p=await map.evaluate((el,[x,y])=>{const c=JSON.parse(el.dataset.camera),r=el.getBoundingClientRect();return {x:r.x+c.x+(x+.5)*16*c.scale,y:r.y+c.y+(y+.5)*16*c.scale};},[x,y]);await page.mouse.click(p.x,p.y);await editIdle();}
async function rectangle(x1,y1,x2,y2){await b('Fill · R').click();const map=page.getByTestId('layout-map').filter({visible:true});await map.scrollIntoViewIfNeeded();const points=await map.evaluate((el,coords)=>{const c=JSON.parse(el.dataset.camera),r=el.getBoundingClientRect();return coords.map(([x,y])=>({x:r.x+c.x+(x+.5)*16*c.scale,y:r.y+c.y+(y+.5)*16*c.scale}));},[[x1,y1],[x2,y2]]);await page.mouse.move(points[0].x,points[0].y);await page.mouse.down();await page.mouse.move(points[1].x,points[1].y,{steps:5});await page.mouse.up();await editIdle();}
async function room(source,id,actor,geometry){
 const path='roguelike/data/layouts/'+id+'.json',fresh=!(await exists(path));await open(fresh?source:path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await b('Authored layout').click();
 if(geometry&&fresh){await fill('Room width',17);await fill('Room height',11);await select('Resize fill glyph','#');await b('Apply resize (top-left anchor)').click();await editIdle();await select('Active layer','terrain');await select('Terrain brush','.');await rectangle(1,1,15,9);await select('Terrain brush','<');await b('Pencil · B').click();await cell(2,8);await fill('Arrival X',6);await fill('Arrival Y',5);await b('Apply arrival').click();await editIdle();}
 await select('Active layer','specials');await select('Placed record','0');await select('Marker creature ID',actor);await fill('Creature source X',10);await fill('Creature source Y',5);await b('Apply creature edit').click();await editIdle();
 await apply(path,fresh);return path;
}
async function status(){const s=await ipc('room_test_action',{action:'status'});assert(!s.error,JSON.stringify(s));return s;}
async function observe(){return JSON.parse(await readFile(resolve(session.state_root,'observation.json'),'utf8'));}
async function start(action='test'){
 const previous=session?.session_id;await b(action==='test'?'Test room':action==='reset'?'Reset current test':'Test latest saved version').click();
 session=await until(async()=>{const s=await status();assert.notEqual(s.status,'failed',s.diagnostics||JSON.stringify(s));assert(!s.last_action_error&&!s.error,JSON.stringify(s));return s.status==='running'&&!s.preparing&&s.session_id!==previous?s:null;});eventId=0;
 await until(async()=>{try{return await observe();}catch{return null;}});return session;
}
async function key(key,capture=false){const id=++eventId,path=resolve(session.state_root,'event.json'),tmp=path+'.tmp';await writeFile(tmp,JSON.stringify({id,key,capture}));await until(async()=>{try{await rename(tmp,path);return true;}catch(e){if(!['EPERM','EACCES','EBUSY'].includes(e.code))throw e;return false;}});return until(async()=>{const s=await status();assert.notEqual(s.status,'failed',s.diagnostics||JSON.stringify(s));try{const o=await observe();return o.applied===id?o:null;}catch{return null;}});}
async function witness(label){
 const rows=[],savedPhases=new Set();
 for(let n=0;n<24;n++){
  await key('.');await new Promise(r=>setTimeout(r,100));const s=await status(),o=await observe();
  rows.push({turn:o.turn,player:o.player,hp:o.hp,tactics:s.tactics,logs:o.logs});
  const ai=s.tactics?.actors?.[0];
  if(ai&&['withdraw','hold'].includes(ai.state.phase)&&!savedPhases.has(ai.state.phase)){
   const expected=structuredClone(ai.state),profile=structuredClone(ai.profile),turn=o.turn;
   await key('f5');await new Promise(r=>setTimeout(r,150));await key('f9');await new Promise(r=>setTimeout(r,150));
   const loaded=await status(),actor=loaded.tactics?.actors?.[0];assert.deepEqual(actor?.state,expected);assert.deepEqual(actor?.profile,profile);assert.equal(loaded.tactics?.turn,turn);
   (receipt.persistence??=[]).push({label,phase:ai.state.phase,turn,state:actor.state,profile:actor.profile});savedPhases.add(ai.state.phase);
  }
  if(ai?.recent?.some(r=>r.phase_before==='return'&&r.action==='melee'&&r.result?.committed))break;
 }
 receipt[label]={capture:(await status()).captured,rows};
 const phases=rows.flatMap(r=>r.tactics?.actors?.[0]?.recent||[]).map(r=>r.phase);
 for(const p of ['withdraw','hold','return'])assert(phases.includes(p),`${label} missing ${p}`);
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,label+'.png'));
 await writeFile(resolve(output,label+'.json'),JSON.stringify(receipt[label],null,2));
}
try{
 child=spawn(exe,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9581 --remote-debugging-address=127.0.0.1'}});
 await until(async()=>{assert.equal(child.exitCode,null);try{return (await (await fetch('http://127.0.0.1:9581/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9581');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();
 let short=base+'grave_skirmisher.json',wide=base+'grave_harrier.json',shortRoom='roguelike/data/layouts/ai1_skirmisher_room.json',wideRoom='roguelike/data/layouts/ai1_harrier_room.json';
 if(process.env.AI1_RUNTIME_ONLY!=='1'){
  await phase('create short composite variant using controls; publish/reopen, tune same ID and duplicate');
  short=await creature(base+'hollow_revenant.json','grave_skirmisher','Grave Skirmisher','hit',2,2,6);
  await open(short);await begin();await fill('Full hold opportunities',1);await b('Undo creature').click();await editIdle();assert.equal(await page.getByLabel('Full hold opportunities',{exact:true}).inputValue(),'2');await b('Redo creature').click();await editIdle();await apply(short);
  wide=await creature(short,'grave_harrier','Grave Harrier','committed_attack',4,3,8);
  await phase('place each saved ID in matched reusable authored rooms through layout controls');
  shortRoom=await room(template,'ai1_skirmisher_room','grave_skirmisher',true);
  wideRoom=await room(shortRoom,'ai1_harrier_room','grave_harrier',false);
 }else await phase('read-only final runtime pass over previously control-authored saved examples');
 await phase('packaged actual-game short and wide approach/strike/withdraw/hold/return witnesses');
 await open(shortRoom);await start('test');await witness('short_cycle');
 await start('reset');receipt.reset=await status();assert.equal(receipt.reset.captured.manifest_sha256,receipt.short_cycle.capture.manifest_sha256);
 await b('Stop').click();await until(async()=>(await status()).status==='stopped');
 await open(wideRoom);await start('latest');await witness('wide_cycle');
 // A parked, dirty dependency is excluded by reset/latest-saved capture.
 await open(wide);await begin();await fill('Full hold opportunities',9);
 await open(wideRoom);await start('latest');receipt.dirty_dependency=await status();
 assert.equal(receipt.dirty_dependency.captured.manifest_sha256,receipt.wide_cycle.capture.manifest_sha256);
 await b('Stop').click();await until(async()=>(await status()).status==='stopped');
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,`preserve ${p}`);
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('exact source/template preserved; reset, stop and latest-saved lifecycle established');
}catch(error){receipt.failure=String(error.stack||error);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child&&child.exitCode===null){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
