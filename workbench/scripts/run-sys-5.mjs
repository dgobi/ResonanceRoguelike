// SYS-5 commissioned exact-source authoring and actual packaged app-local play.
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/sys-5',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
await mkdir(settings,{recursive:true});
await writeFile(resolve(settings,'project.json'),JSON.stringify({version:1,project_root:root}));
const base='roguelike/data/entities/creatures/',template='roguelike/docs/examples/g17_authored_creature_room.json';
const exe=resolve('src-tauri/target/release/resonance-workbench.exe'),hash=b=>createHash('sha256').update(b).digest('hex');
const receipt={output,root,started_utc:new Date().toISOString(),package_sha256:hash(await readFile(exe)),checks:[],publications:[],errors:[]};
const baseline={};for(const p of [base+'sewer_thing.json','roguelike/data/layouts/barrow_ward_store_a.json',template])baseline[p]=hash(await readFile(resolve(root,p)));
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
  const o=await observe();assert(!o.dead,'living native journey');
  const hostile=o.actors.find(a=>a.hp>0&&['AIState.HUNTING','AIState.ATTACKING'].includes(a.ai)&&Math.max(Math.abs(a.x-o.player[0]),Math.abs(a.y-o.player[1]))<=1);
  if(hostile){await key(direction(Math.sign(hostile.x-o.player[0]),Math.sign(hostile.y-o.player[1])));continue;}
  if(o.player[0]===x&&o.player[1]===y)return o;
  const q=[[...o.player,[]]],seen=new Set([o.player.join(',')]);let route;
  for(let j=0;j<q.length;j++){const [a,c,p]=q[j];if(a===x&&c===y){route=p;break;}for(const [dx,dy,k] of directions){const nx=a+dx,ny=c+dy,id=`${nx},${ny}`;if(seen.has(id)||!o.walkable[ny]?.[nx]||o.actors.some(a=>a.x===nx&&a.y===ny)||o.containers.some(a=>a.x===nx&&a.y===ny)||o.decor.some(a=>a.x===nx&&a.y===ny))continue;seen.add(id);q.push([nx,ny,[...p,k]]);}}
  assert(route?.length,`No route to ${x},${y}`);await key(route[0]);
 }throw Error('bounded walk exhausted');
}
async function selectInventory(id){let o=await observe();if(!o.inventory_open)o=await key('i');const n=o.inventory_rows.findIndex(r=>!r.header&&r.item_id===id);assert(n>=0,id);while(o.inventory_selected!==n)o=await key(o.inventory_selected<n?'down':'up');return o;}
async function menu(n){for(let i=0;i<n;i++)await key('down');return key('return');}
function direction(dx,dy){return ({'-1,-1':'[7]','0,-1':'up','1,-1':'[9]','-1,0':'left','1,0':'right','-1,1':'[1]','0,1':'down','1,1':'[3]'})[`${dx},${dy}`];}
async function use(id){await selectInventory(id);await key('e');await key('escape');}
async function interact(x,y){let o=await key('e');while(o.interaction.cursor[0]!==x)o=await key(o.interaction.cursor[0]<x?'right':'left');while(o.interaction.cursor[1]!==y)o=await key(o.interaction.cursor[1]<y?'down':'up');return key('return');}


const eater=base+'gutter_gleaner.json',guard=base+'pale_carrion_beetle.json',meat='roguelike/data/items/butchery/gleaner_flesh.json',room='roguelike/data/layouts/sys5_scavenging_room.json';
const check=async(label,value)=>{await page.getByLabel(label,{exact:true}).filter({visible:true}).setChecked(value);await editIdle();};
async function source(value){await eb('Source').click();await editor().locator('textarea.source-editor').fill(JSON.stringify(value,null,2));await editIdle();}
async function invalid(){await eb('Validate draft').click();await idle();const r=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!r.valid,JSON.stringify(r));(receipt.rejections??=[]).push(r.diagnostics);}
async function undoCreature(){await b('Supported fields').click();await b('Undo creature').click();await editIdle();}
async function makeMeat(){
 const fresh=!(await exists(meat));await open(fresh?'roguelike/data/items/butchery/crow_meat.json':meat);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID','gleaner_flesh');}
 await page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name:'Properties',exact:true}).click();
 await fill('Item name','Gleaner Flesh');await fill('Item description','Pale strips of scavenger flesh. Kept whole, they can cook over a fire or distract a hungry creature.');await fill('Item weight (kg)',0.2);
 await apply(meat);await begin();await fill('Keyword tier 1',2);await invalid();await b('Undo item').click();await editIdle();
 await page.screenshot({path:resolve(output,'flesh-item-controls.png')});
}
async function makeEater(path,original,id,name,territorial){
 if(await exists(path)){await open(path);return;}
 const fresh=!(await exists(path));await open(fresh?base+original+'.json':path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);await select('Creature AI','composite');await select('Behaviour recipe',territorial?'territorial_guard':'strike_and_withdraw');}
 await b('Supported fields').click();await fill('Creature name',name);await fill('Creature description',territorial?'A pale, hooked beetle waits beside the old carrion drain. Its mandibles work even in complete darkness.':'A lean sewer scavenger noses along the shelving, following exposed flesh when light reaches it.');
 await fill('Sight radius',8);await check('Sees in dark',territorial);await fill('Speed',territorial?1:0.7);await check('Enable scavenging',true);await fill('Scavenging feeding opportunities',3);
 if(territorial){await select('Territorial engagement','direct_melee');await fill('Defended radius (tiles)',4);await fill('Maximum excursion radius (tiles)',6);}
 if(fresh){await select('Behaviour recipe','observation_averse');await invalid();await undoCreature();}
 if(!territorial&&fresh){
  await b('Harvest').click();await b('Add harvest profile').click();await select('Corpse decay','timed');await fill('Decay turns',150);await b('Add harvest tier').click();await fill('Cutting threshold 1',1);
  for(const [i,item] of [[1,'gleaner_flesh'],[2,'animal_bone']]){await b('Add output to tier 1').click();await select(`Harvest item 1.${i}`,item);await fill(`Minimum quantity 1.${i}`,1);await fill(`Maximum quantity 1.${i}`,i===1?2:1);}
  await check('Flesh output 1.1',true);await check('Flesh output 1.2',true);await invalid();await undoCreature();await b('Harvest').click();
 }
 await apply(path);await begin();await b('Supported fields').click();await page.screenshot({path:resolve(output,id+'-controls.png')});
}
async function makeRoom(){
 if(await exists(room)){
  await open(room);const raw=JSON.parse(await readFile(resolve(root,room),'utf8'));
  // Publish a shorter harvest approach and exposed loose food via the editor.
  const line=[...raw.layers[10]];line[7]='.';raw.layers[10]=line.join('');
  for(const [item_id,x,y] of [['gleaner_flesh',3,13],['crude_blade',4,13],['gleaner_flesh',6,4],['crow_meat',19,4]])
   if(!raw.special_tiles.some(r=>r.item_id===item_id&&r.x===x&&r.y===y))raw.special_tiles.push({type:'item',x,y,item_id});
  await begin();await source(raw);await apply(room);return;
 }
 await open(template);await begin();await eb('Save as new variant').click();await fill('New variant ID','sys5_scavenging_room');
 const grid=Array.from({length:17},(_,y)=>Array.from({length:27},(_,x)=>x===0||y===0||x===26||y===16?'#':'.'));
 for(let x=1;x<23;x++)grid[10][x]='#';grid[10][7]='.';for(let y=1;y<10;y++)grid[y][13]='#';grid[8][13]='.';grid[13][3]='<';
 await source({id:'sys5_scavenging_room',width:27,height:17,layers:grid.map(r=>r.join('')),legend:{'#':'wall','.':'floor','<':'stairs_up'},player_start:{x:3,y:13},special_tiles:[]});await b('Authored layout').click();
 for(const [kind,id,x,y] of [['item','gleaner_flesh',3,13],['item','crude_blade',4,13],['item','gleaner_flesh',6,4],['item','crow_meat',19,4],['creature','gutter_gleaner',5,4],['creature','pale_carrion_beetle',18,4],['remains','plague_crow',7,4],['remains','heath_stalker',20,4],['decor','campfire_lit',7,6]]){
  await select('Placement kind',kind);await select('Placement '+kind,id);await b('Place '+kind).click();await cell(x,y);
 }
 // Two mounted proposals must rebase to the selected source record.
 await cell(7,4);assert.equal(await page.getByLabel('Marker remains source',{exact:true}).inputValue(),'plague_crow');
 await cell(20,4);assert.equal(await page.getByLabel('Marker remains source',{exact:true}).inputValue(),'heath_stalker');
 await apply(room);await begin();await b('Authored layout').click();await select('Placement kind','remains');await select('Placement remains','plague_crow');await b('Place remains').click();await cell(3,13);
 await invalid();await b('Undo canvas').click();await editIdle();await page.screenshot({path:resolve(output,'remains-placement-controls.png')});
}
async function witness(feed){
 await phase(`Actual living hosts, captured feeding ${feed}`);let o=await observe();const first=o.scavengers;assert.equal(first.find(a=>a.id==='gutter_gleaner').config.feed_opportunities,feed);
 const offset=[o.player[0]-3,o.player[1]-13],at=(x,y)=>[x+offset[0],y+offset[1]];
 assert.equal(first.find(a=>a.id==='pale_carrion_beetle').host.recipe,'territorial_guard');
 o=await key(',');await selectInventory('gleaner_flesh');const turn=o.turn;await key('p');o=await key('escape');assert.equal(o.turn,turn);
 await key('p');o=await key('return');assert.equal(o.turn,turn+1);await key('escape');
 const placed=o.floor.find(r=>r.x===o.player[0]&&r.y===o.player[1]).items.find(i=>i.item_id==='gleaner_flesh');assert(placed?.flesh_resource?.uid);assert(!o.inventory.some(i=>i.item_id==='gleaner_flesh'));
 const loose=o.floor.filter(r=>r.y===at(0,4)[1]).flatMap(r=>r.items).filter(i=>['gleaner_flesh','crow_meat'].includes(i.item_id));assert.equal(loose.length,2);
 const partial=structuredClone(o.scavengers);await key('f5');o=await key('f9');assert.deepEqual(o.scavengers.map(a=>a.state),partial.map(a=>a.state));
 for(let n=0;n<25&&!o.scavengers.every(a=>a.state.completed===2);n++)o=await key('.');
 assert(o.scavengers.every(a=>a.state.completed===2),JSON.stringify(o.scavengers));
 assert(!o.floor.flatMap(r=>r.items).some(i=>loose.some(l=>l.flesh_resource.uid===i.flesh_resource?.uid)));
 const corpses=o.floor.flatMap(r=>r.items).filter(i=>i.item_id==='corpse');assert.equal(corpses.length,2);assert(corpses.every(i=>i.flesh_resource.state==='stripped'));
 const end=structuredClone(o);await key('f5');o=await key('f9');assert.deepEqual(o.floor.flatMap(r=>r.items).map(i=>i.flesh_resource),end.floor.flatMap(r=>r.items).map(i=>i.flesh_resource));
 await use('crude_blade');await use('leather_jack');await walk(...at(7,5));
 // Ordinary movement/combat keeps living host hostility. Only actual key input
 // and source-authored equipment are used to reach the remaining harvest.
 o=await interact(...at(7,4));await key('escape');await walk(...at(7,4));o=await key(',');
 if(o.interaction.selection){const n=o.interaction.selection.items.findIndex(i=>i.item_id==='animal_bone');assert(n>=0);while(o.interaction.selection.selected!==n)o=await key(o.interaction.selection.selected<n?'down':'up');o=await key('return');}
 await key('escape');o=await observe();assert(o.inventory.some(i=>i.item_id==='animal_bone'));assert(!o.floor.find(r=>r.x===at(7,4)[0]&&r.y===at(7,4)[1])?.items.some(i=>i.item_id==='crow_meat'));
 assert(!o.fixture_applied&&!o.dead);const harvested=structuredClone(o);
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,`feeding-${feed}-${Date.now()}.png`));
 return {feed,captured:(await status()).captured,partial,end,harvested,consumed_loose:loose,setup:'Published reusable room; living AI, ordinary inventory placement, loose meat consumed before corpse stripping, equipped blade and remaining bone harvest, paid waits and F5/F9. Diagnostic observations include unseen actors; this is not ordinary-world balance proof.'};
}
async function stop(){await b('Stop').click();await until(async()=>(await status()).status==='stopped');}
try{
 const env={...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9595 --remote-debugging-address=127.0.0.1'};
 spawn('cscript.exe',['//nologo',resolve('Launch Workbench.vbs')],{cwd:output,windowsHide:true,stdio:'ignore',env});
 await until(async()=>{try{return (await (await fetch('http://127.0.0.1:9595/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9595');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);
 const pid=Number(execFileSync('powershell.exe',['-NoProfile','-Command',"(Get-CimInstance Win32_Process -Filter \"name='resonance-workbench.exe'\" | Where-Object { $_.CommandLine -notlike '*--test*' } | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId"],{encoding:'utf8',windowsHide:true}).trim());
 child={pid};page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();

 if(process.env.SYS5_RUNTIME_ONLY!=='1'){
  await phase('Publish new flesh, both host variants, explicit harvest and native remains controls');await makeMeat();await makeEater(eater,'sewer_thing','gutter_gleaner','Gutter Gleaner',false);await makeEater(guard,'amber_sting_beetle','pale_carrion_beetle','Pale Carrion Beetle',true);await makeRoom();
  await open(eater);await begin();await b('Supported fields').click();await fill('Scavenging feeding opportunities',3);await apply(eater);
  await open(room);await start('latest');const captured=(await status()).captured.manifest_sha256;receipt.initial=await witness(3);
  await open(eater);await begin();await b('Supported fields').click();await fill('Scavenging feeding opportunities',5);await apply(eater);
  await open(room);await start('reset');assert.equal((await status()).captured.manifest_sha256,captured);receipt.reset=await witness(3);
  await start('latest');receipt.latest=await witness(5);await stop();
  await open(eater);await begin();await b('Supported fields').click();await fill('Scavenging feeding opportunities',7);
  await open(room);await start('latest');receipt.dirtyExcluded=await witness(5);await stop();
  await open(eater);await begin();await undoCreature();
 }else{await open(room);await start('latest');receipt.runtime=await witness(5);await stop();}
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,p);
 receipt.unchanged_sources=baseline;assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('SYS-5 packaged authoring/runtime passed');
}catch(error){receipt.failure=String(error.stack||error);receipt.failureText=await page?.locator('body').innerText().catch(()=>null);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
