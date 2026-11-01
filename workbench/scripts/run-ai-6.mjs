// Commissioned AI-6 correction authoring in production main; only named new examples/rooms
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/ai-6',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
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


async function creature(source,id,name,engagement){
 const path=base+id+'.json',fresh=!(await exists(path));await open(fresh?source:path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);if(source.endsWith('hollow_revenant.json'))await select('Creature AI','composite');await select('Behaviour recipe','territorial_guard');}
 await fill('Creature name',name);await fill('Creature description','Old bones stand watch beside a worn patch of stone.');await fill('Speed',1);
 await select('Territorial engagement',engagement);await fill('Defended radius (tiles)',4);await fill('Maximum excursion radius (tiles)',6);await fill('Pursuit opportunity budget',32);
 assert(await page.getByLabel('Wander radius',{exact:true}).filter({visible:true}).isDisabled());
 await page.screenshot({path:resolve(output,id+'-controls.png')});await apply(path);return path;
}
async function room(source,id,actor,store=false){
 const path='roguelike/data/layouts/'+id+'.json',fresh=!(await exists(path));await open(fresh?source:path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await b('Authored layout').click();
 if(!store){await fill('Arrival X',5);await fill('Arrival Y',5);await b('Apply arrival').click();await editIdle();}
 await select('Active layer','specials');await select('Placed record','0');await select('Marker creature ID',actor);await fill('Creature source X',store?17:10);await fill('Creature source Y',5);await b('Apply creature edit').click();await editIdle();
 await apply(path,fresh);return path;
}
async function stop(){await b('Stop').click();await until(async()=>(await status()).status==='stopped');}
async function witness(room,withdraw){
 await open(room);await start('latest');await key('right');let rows=[];
 for(let n=0;n<14;n++){
  await key('.');await new Promise(r=>setTimeout(r,90));let t=(await status()).tactics;rows.push(t);
  const a=t.actors[0];if(a.recent.some(r=>r.action==='melee'&&r.result?.committed)){
   if(withdraw){if(a.state.phase==='withdraw'){const pos=a.position;await key('.');await new Promise(r=>setTimeout(r,90));const next=(await status()).tactics;rows.push(next);assert.notDeepEqual(next.actors[0].position,pos);assert(next.actors[0].recent.some(r=>r.reason==='withdrawal'&&r.action==='move'));break;}}
   else {assert.equal(a.state.phase,'approach');break;}
  }
 }
 assert(rows.some(t=>t.actors[0].recent.some(r=>r.action==='melee'&&r.result?.committed)));
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,(withdraw?'withdraw':'direct')+'.png'));
 receipt[withdraw?'withdraw':'direct']={rows,capture:(await status()).captured};await stop();
}
try{
 child=spawn(exe,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9585 --remote-debugging-address=127.0.0.1'}});
 await until(async()=>{assert.equal(child.exitCode,null);try{return (await (await fetch('http://127.0.0.1:9585/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9585');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();
 const primary=base+'barrow_sentinel.json',variant=base+'barrow_watcher.json',direct='roguelike/data/layouts/ai6_sentinel_post.json',withdraw='roguelike/data/layouts/ai6_watcher_post.json',store='roguelike/data/layouts/barrow_ward_store_b.json';
 if(process.env.AI6_RUNTIME_ONLY!=='1'){
  await phase('create both ordinary new-ID engagements through actual packaged controls');
  await creature(base+'hollow_revenant.json','barrow_sentinel','Barrow Sentinel','direct_melee');
  await open(primary);await begin();await select('Territorial engagement','strike_and_withdraw');await b('Undo creature').click();await editIdle();assert.equal(await page.getByLabel('Territorial engagement',{exact:true}).filter({visible:true}).inputValue(),'direct_melee');await b('Redo creature').click();await editIdle();await select('Territorial engagement','direct_melee');await apply(primary);
  await creature(primary,'barrow_watcher','Barrow Watcher','strike_and_withdraw');
  await phase('publish matched saved rooms and guarded store preserving original');
  await room('roguelike/data/layouts/ai1_skirmisher_room.json','ai6_sentinel_post','barrow_sentinel');
  await room(direct,'ai6_watcher_post','barrow_watcher');
  await room('roguelike/data/layouts/barrow_ward_store_a.json','barrow_ward_store_b','barrow_sentinel',true);
  await phase('add guarded store to equal-weight 0.35 new-world assignment through controls');
  await b('World assignment').click();await idle();await begin();if(await b('Add this room').isEnabled()){await b('Add this room').click();await editIdle();}
  const doc=await apply('roguelike/data/generation/authored_submap_selection.json');const policy=JSON.parse(doc.raw);assert.equal(policy.authored_chance,.35);assert.deepEqual(policy.candidates,[{layout_id:'barrow_ward_store_a',weight:1},{layout_id:'barrow_ward_store_b',weight:1}]);
 }
 if(process.env.AI6_RUNTIME_ONLY==='1'){await open(primary);await begin();await page.getByRole('group',{name:'Fixed territorial post',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,'final-territorial-controls.png')});}
 await phase('actual saved-room direct melee and qualifying hit/withdrawal share fixed objective');await witness(direct,false);await witness(withdraw,true);
 if(process.env.AI6_RUNTIME_ONLY!=='1'){
  await phase('saved radius revision changes acquisition; Reset keeps old capture, latest saved excludes dirty dependencies');
  await open(direct);await start('latest');const old=(await status()).captured.manifest_sha256;await key('right');await key('.');assert.equal((await status()).tactics.actors[0].objective.phase,'engaged');
  await open(primary);await begin();await fill('Defended radius (tiles)',3);await apply(primary);await open(direct);
  await start('reset');assert.equal((await status()).captured.manifest_sha256,old);await key('right');await key('.');assert.equal((await status()).tactics.actors[0].objective.phase,'engaged');receipt.reset=await status();
  await start('latest');const latest=(await status()).captured.manifest_sha256;assert.notEqual(latest,old);await key('right');await key('.');assert.equal((await status()).tactics.actors[0].objective.phase,'guard');receipt.revised=await status();
  await open(primary);await begin();await fill('Defended radius (tiles)',2);await open(direct);await start('latest');assert.equal((await status()).captured.manifest_sha256,latest);receipt.dirty_dependency=await status();await stop();
  await open(primary);await begin();await fill('Defended radius (tiles)',4);await apply(primary);
 }
 await open(store);await start('latest');receipt.store=await status();await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,'store-arrival.png'));await stop();
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,`preserve ${p}`);
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('source preserved; native authoring/lifecycle complete');
}catch(error){receipt.failure=String(error.stack||error);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child&&child.exitCode===null){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
