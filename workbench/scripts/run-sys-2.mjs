// SYS-2 commissioned exact-source authoring and actual packaged app-local play.
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/sys-2',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
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


const itemPath=id=>`roguelike/data/items/tools/${id}.json`,room='roguelike/data/layouts/sys2_light_room.json';
async function variant(id,source,name,radius,fuel,mass){
 const path=itemPath(id),fresh=!(await exists(path));await open(fresh?itemPath(source):path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name:'Properties',exact:true}).click();await fill('Item name',name);await fill('Item weight (kg)',mass);
 await fill('Item description',id==='watch_lantern'?'A heavy broad-wicked lantern. Its bright pool reaches far; the oil goes quickly.':'A short rush for testing a few breaths of light.');
 await fill('Mechanical light reach (tiles)',radius);await fill('Held fuel (charged phases)',fuel);
 await page.getByLabel('Mechanical light reach (tiles)',{exact:true}).filter({visible:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,id+'-controls.png')});
 await apply(path);const before=hash(await readFile(resolve(root,path)));await begin();await apply(path);assert.equal(before,hash(await readFile(resolve(root,path))));
 await fill('Mechanical light reach (tiles)',0);await eb('Validate draft').click();await idle();const invalid=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!invalid.valid);
 await b('Undo item').click();await editIdle();assert.equal(await page.getByLabel('Mechanical light reach (tiles)',{exact:true}).filter({visible:true}).inputValue(),String(radius));
 (receipt.invalidAndNoop??=[]).push({path,rejected:true,undo:true,unchanged:before});
}
async function makeRoom(){
 if(await exists(room)){await open(room);return;}
 await open(template);await begin();await eb('Save as new variant').click();await fill('New variant ID','sys2_light_room');await eb('Source').click();
 const grid=Array.from({length:13},(_,y)=>Array.from({length:25},(_,x)=>x===0||y===0||x===24||y===12?'#':'.'));
 for(const cx of [9,14])for(let y=5;y<=7;y++)for(let x=cx-1;x<=cx+1;x++)grid[y][x]='~';
 grid[6][9]=grid[6][14]='.';grid[9][3]='<';
 const geometry={id:'sys2_light_room',width:25,height:13,layers:grid.map(r=>r.join('')),legend:{'#':'wall','.':'floor','<':'stairs_up','~':'deep_water'},player_start:{x:3,y:6},special_tiles:[]};
 await editor().locator('textarea.source-editor').fill(JSON.stringify(geometry,null,2));await editIdle();await b('Authored layout').click();
 for(const [id,x,y] of [['short_rushlight',3,6],['watch_lantern',4,6]]){await select('Placement kind','item');await select('Placement item',id);await b('Place item').click();await cell(x,y);}
 for(const [id,x,y] of [['heath_stalker',9,6],['highland_bandit',14,6]]){await select('Placement kind','creature');await select('Placement creature',id);await b('Place creature').click();await cell(x,y);}
 await apply(room);
}
async function selectInventory(id){let o=await observe();if(!o.inventory_open)o=await key('i');const n=o.inventory_rows.findIndex(r=>!r.header&&r.item_id===id);assert(n>=0,id);while(o.inventory_selected!==n)o=await key(o.inventory_selected<n?'down':'up');return o;}
async function witness(radius,fuel){
 let o=await key(',');assert(o.inventory.some(i=>i.item_id==='short_rushlight'));
 const before=o.turn;await selectInventory('short_rushlight');o=await key('e');assert.equal(o.turn,before+1);await key('escape');o=await observe();
 const i=o.inventory.find(i=>i.item_id==='short_rushlight');assert.equal(i.held_light.radius,radius);assert.equal(i.burn_turns,fuel);assert.equal(i.turns_lit,1);
 const pair=o.illumination.sight.find(s=>s.observer==='highland_bandit'&&s.target==='heath_stalker');assert.equal(pair.seen,radius>=6);
 const prey=o.actors.find(a=>a.id==='heath_stalker');assert.equal(o.illumination.lit[prey.y][prey.x],radius>=6);
 const state={radius,fuel,lit:o.illumination.lit,pair,owned:i,turn:o.turn,captured:(await status()).captured};
 await key('f5');o=await key('f9');assert.equal(o.inventory.find(i=>i.item_id==='short_rushlight').turns_lit,1);assert.deepEqual(o.illumination.lit,state.lit);
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,`reach-${radius}.png`));
 for(let n=1;n<fuel;n++)o=await key('.');assert(!o.inventory.some(i=>i.item_id==='short_rushlight'));assert(!o.light);assert(!o.illumination.sight.find(s=>s.observer==='highland_bandit'&&s.target==='heath_stalker').seen);
 state.expired={turn:o.turn,inventory:o.inventory,light:o.light};return state;
}
async function stop(){await b('Stop').click();await until(async()=>(await status()).status==='stopped');}
try{
 const env={...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9592 --remote-debugging-address=127.0.0.1'};
 spawn('cscript.exe',['//nologo',resolve('Launch Workbench.vbs')],{cwd:output,windowsHide:true,stdio:'ignore',env});
 await until(async()=>{try{return (await (await fetch('http://127.0.0.1:9592/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9592');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);
 const pid=Number(execFileSync('powershell.exe',['-NoProfile','-Command',"(Get-CimInstance Win32_Process -Filter \"name='resonance-workbench.exe'\" | Where-Object { $_.CommandLine -notlike '*--test*' } | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId"],{encoding:'utf8',windowsHide:true}).trim());
 child={pid};page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();

 if(process.env.SYS2_RUNTIME_ONLY!=='1'){
  await phase('Publish ordinary watch lantern and short-rush reuse configuration');
  await variant('watch_lantern','oil_lantern','Watch Lantern',9,420,.8);
  await variant('short_rushlight','tallow_torch','Short Rushlight',3,8,.1);await makeRoom();
  await open(room);await start('latest');const captured=(await status()).captured.manifest_sha256;receipt.narrow=await witness(3,8);
  await open(itemPath('short_rushlight'));await begin();await page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name:'Properties',exact:true}).click();await fill('Mechanical light reach (tiles)',6);await fill('Held fuel (charged phases)',5);await apply(itemPath('short_rushlight'));
  await open(room);await start('reset');assert.equal((await status()).captured.manifest_sha256,captured);receipt.capturedReset=await witness(3,8);
  await start('latest');receipt.editedConsumer=await witness(6,5);await stop();
  await open(itemPath('short_rushlight'));await begin();await page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name:'Properties',exact:true}).click();await fill('Mechanical light reach (tiles)',2);
  await open(room);await start('latest');receipt.dirtyExcluded=await witness(6,5);await stop();
  await open(itemPath('short_rushlight'));await begin();await page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name:'Properties',exact:true}).click();assert.equal(await page.getByLabel('Mechanical light reach (tiles)',{exact:true}).filter({visible:true}).inputValue(),'2');await b('Undo item').click();await editIdle();
 }else{await open(room);await start('latest');receipt.finalRuntime=await witness(6,5);await stop();}
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,p);
 receipt.unchanged_sources=baseline;assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('SYS-2 native flow passed');
}catch(error){receipt.failure=String(error.stack||error);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
