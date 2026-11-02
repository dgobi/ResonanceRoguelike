// Commissioned AI-6 correction authoring in production main; only named new examples/rooms
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/ai-7',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
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



async function creature(source,id,name,order){
 const path=base+id+'.json',fresh=!(await exists(path));await open(fresh?source:path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);if(source.endsWith('hollow_revenant.json'))await select('Creature AI','composite');await select('Behaviour recipe','protective_escort');}
 await fill('Creature name',name);await fill('Creature description','A quiet figure keeps a place beside you.');await fill('Speed',1);
 await fill('Faction label','player');await b('Clear hostiles').click();await editIdle();await fill('Add hostile faction','hollow');await b('Add hostile').click();await editIdle();
 await select('Initial escort order',order);await fill('Follow spacing (tiles)',order==='hold'?1:2);await fill('Protection radius (tiles)',order==='hold'?3:4);await fill('Escort maximum excursion (tiles)',6);await fill('Escort pursuit opportunities',order==='hold'?12:18);
 assert(await page.getByLabel('Wander radius',{exact:true}).filter({visible:true}).isDisabled());
 await page.getByRole('group',{name:'Protective escort',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,id+'-controls.png')});await apply(path);return path;
}
function definition(id,actor,threat){
 const rows=Array.from({length:11},(_,y)=>Array.from({length:17},(_,x)=>x===0||x===16||y===0||y===10?'#':'.'));
 if(!threat){for(let y=2;y<9;y++)rows[y][8]='#';rows[5][8]='+';for(const y of [4,6])for(let x=4;x<=7;x++)rows[y][x]='#';}
 else {for(let y=2;y<8;y++)rows[y][9]='#';rows[5][9]='.';}
 return {id,width:17,height:11,layers:rows.map(r=>r.join('')),legend:{'#':'wall','.':'floor','+':'door_closed','<':'stairs_up'},player_start:{x:5,y:5},special_tiles:[{type:'creature',x:6,y:5,creature_id:actor},...(threat?[{type:'creature',x:12,y:5,creature_id:'barrow_sentinel'}]:[])]};
}
async function room(id,actor,threat){
 const path='roguelike/data/layouts/'+id+'.json',fresh=!(await exists(path));await open(fresh?'roguelike/data/layouts/ai6_sentinel_post.json':path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await b('Source').click();await fill('Draft JSON',JSON.stringify(definition(id,actor,threat),null,2));await apply(path,fresh);return path;
}
async function stop(){await b('Stop').click();await until(async()=>(await status()).status==='stopped');}
async function order(hold){await key('e');await key('return');if(hold)await key('down');await key('return');}
async function witness(path,hold=false){
 await open(path);await start('latest');const initial=await status();await order(hold);await key('right');await key('right');await key('.');
 await key(undefined,true);const s=await status();receipt[hold?'threat':'lane']={initial,after:s,observation:await observe()};await copyFile(resolve(session.state_root,'frame.png'),resolve(output,hold?'hold-threat.png':'follow-lane.png'));await stop();
}
try{
 const launched=Date.now();
 const env={...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9586 --remote-debugging-address=127.0.0.1'};
 const launcher=spawn('cscript.exe',['//nologo',resolve('Launch Workbench.vbs')],{cwd:output,windowsHide:true,stdio:'ignore',env});
 await until(async()=>{try{return (await (await fetch('http://127.0.0.1:9586/json/list')).json()).length;}catch{return false;}});
 const pid=Number(execFileSync('powershell.exe',['-NoProfile','-Command',"(Get-Process resonance-workbench | Sort-Object StartTime -Descending | Select-Object -First 1).Id"],{encoding:'utf8',windowsHide:true}).trim());child={pid,exitCode:null};receipt.launch={entry:'workbench/Launch Workbench.vbs',pid,started:launched};
 browser=await chromium.connectOverCDP('http://127.0.0.1:9586');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();
 const primary=base+'ash_escort.json',variant=base+'stone_escort.json',lane='roguelike/data/layouts/ai7_escort_lane.json',threat='roguelike/data/layouts/ai7_escort_threat.json';
 if(process.env.AI7_RUNTIME_ONLY!=='1'){
  await phase('duplicate ordinary sources and publish both player-aligned recipe configurations');
  await creature(base+'hollow_revenant.json','ash_escort','Ash Escort','follow');
  await open(primary);await begin();await select('Initial escort order','hold');await b('Undo creature').click();await editIdle();assert.equal(await page.getByLabel('Initial escort order',{exact:true}).filter({visible:true}).inputValue(),'follow');await b('Redo creature').click();await editIdle();await select('Initial escort order','follow');await apply(primary);
  await creature(primary,'stone_escort','Stone Escort','hold');
  await phase('publish two isolated authored rooms through supported Source and review controls');await room('ai7_escort_lane','ash_escort',false);await room('ai7_escort_threat','stone_escort',true);
 }
 await phase('launch latest saved rooms and issue ordinary local paid orders');await witness(lane);await witness(threat,true);
 if(process.env.AI7_RUNTIME_ONLY!=='1'){
  await phase('saved initial-order tuning changes game response; Reset freezes old capture and latest excludes dirty draft');
  await open(lane);await start('latest');const old=(await status()).captured.manifest_sha256;await key('left');await key('left');await key('left');await new Promise(r=>setTimeout(r,150));const follow=await status();receipt.savedFollow=follow;
  await open(primary);await begin();await select('Initial escort order','hold');await apply(primary);await open(lane);
  await start('reset');assert.equal((await status()).captured.manifest_sha256,old);receipt.reset=await status();assert.equal(receipt.reset.tactics.actors[0].escort.order,'follow');
  await start('latest');const latest=(await status()).captured.manifest_sha256;assert.notEqual(latest,old);await key('left');await key('left');await key('left');await new Promise(r=>setTimeout(r,150));receipt.revised=await status();assert.equal(receipt.revised.tactics.actors[0].escort.order,'hold');assert.notDeepEqual(receipt.revised.tactics.actors[0].position,follow.tactics.actors[0].position);
  await open(primary);await begin();await select('Initial escort order','follow');await open(lane);await start('latest');assert.equal((await status()).captured.manifest_sha256,latest);receipt.dirtyDependency=await status();await stop();
  await open(primary);await begin();await apply(primary);
 }
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,`preserve ${p}`);
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('source preserved; native authoring and room lifecycle complete');
}catch(error){receipt.failure=String(error.stack||error);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
