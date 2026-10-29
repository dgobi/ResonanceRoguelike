// W5M packaged authoring -> real preparation -> use -> revision/cold compatibility.
import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,cp,rename,access,unlink,readdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const output=resolve('.artifacts/w5m',`native-${Date.now()}`),root=resolve(output,'project'),settings=resolve(output,'settings'),recovery=resolve(output,'recovery');
await mkdir(settings,{recursive:true});
const python=resolve('worker/runtime/python.exe');
assert.equal(spawnSync(python,['-I','-B','-c',"import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{stdio:'inherit',windowsHide:true}).status,0);
await cp(resolve('../roguelike/assets/sprites'),resolve(root,'roguelike/assets/sprites'),{recursive:true});
await mkdir(resolve(root,'roguelike/docs/examples'),{recursive:true});
for(const name of ['g17_authored_creature_room.json','g17_authored_creature_room.access.json'])await copyFile(resolve('../roguelike/docs/examples',name),resolve(root,'roguelike/docs/examples',name));
await writeFile(resolve(settings,'project.json'),JSON.stringify({version:1,project_root:root}));
const hash=b=>createHash('sha256').update(b).digest('hex'),exe=resolve('src-tauri/target/release/resonance-workbench.exe');
const receipt={output,root,checks:[],errors:[],package_sha256:hash(await readFile(exe)),started_utc:new Date().toISOString()};
let child,browser,page,session,cold,sentinel,launchCount=0;
const exited=p=>p.exitCode!==null||p.signalCode!==null;
const room='roguelike/data/layouts/w5m_equipment_room.json',template='roguelike/docs/examples/g17_authored_creature_room.json';
const eb=n=>page.locator('[data-testid="authoring"]:visible').getByRole('button',{name:n,exact:true}),b=n=>page.getByRole('button',{name:n,exact:true}).filter({visible:true});
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'),null,{timeout:90000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==='true'));
const fill=async(n,v)=>{await page.getByLabel(n,{exact:true}).filter({visible:true}).fill(v);await editIdle();};
async function phase(label){console.log(label);receipt.checks.push(label);await writeFile(resolve(output,'progress.json'),JSON.stringify(receipt,null,2));}
async function open(path){
 for(let attempt=0;attempt<5;attempt++){
  await idle();await page.getByLabel('Category / route',{exact:true}).selectOption('');await fill('Search ID, name or path',path);
  await page.locator(`[data-asset="${path}"]`).click();
  try{await page.waitForFunction(path=>[...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.offsetParent&&e.querySelector('.filepath')?.textContent===path),path,{timeout:5000});await idle();return;}
  catch(error){if(attempt===4)throw error;const footer=await page.locator('footer').innerText();assert(!/ERROR|PATH_ESCAPE|READ_ONLY/.test(footer),footer);}
 }
}
async function source(){await eb('Source').click();return page.locator('[data-testid="authoring"]:visible textarea.source-editor');}
async function validate(){await editIdle();await idle();await eb('Validate draft').click();await idle();return JSON.parse(await page.locator('[data-testid="authoring"]:visible [data-testid="draft-receipt"]').textContent());}
async function apply(variant=false){await eb(variant?'Apply variant':'Review & apply').click();await b('Confirm apply one file').click();await idle();await page.getByText(/Saved and byte-checked reopen:/).waitFor({timeout:60000});}
async function status(){const r=await ipc('room_test_action',{action:'status'});assert(!r.error,JSON.stringify(r));return r;}
async function until(fn,timeout=60000){const start=Date.now();for(;;){const v=await fn();if(v)return v;assert(Date.now()-start<timeout,'Timed out');await new Promise(r=>setTimeout(r,100));}}
async function running(previous){const began=Date.now();return until(async()=>{const s=await status();if(!s.preparing&&Date.now()-began>1000){const alert=page.getByTestId('room-test-panel').getByRole('alert');if(await alert.count())assert.fail(await alert.innerText());assert(!s.last_action_error&&!s.error,JSON.stringify(s));assert.notEqual(s.status,'failed',JSON.stringify(s));}return s.status==='running'&&!s.preparing&&s.session_id!==previous?s:null;},100000);}
async function observe(){return JSON.parse(await readFile(resolve(session.state_root,'observation.json'),'utf8'));}
let eventId=0;
async function publishEvent(command){
 const path=resolve(session.state_root,'event.json'),tmp=path+'.tmp';await writeFile(tmp,JSON.stringify(command));
 for(let attempt=0;;attempt++){try{await rename(tmp,path);return;}catch(error){if(!['EPERM','EACCES','EBUSY'].includes(error.code)||attempt>=99)throw error;await new Promise(r=>setTimeout(r,20));}}
}
async function key(key,text='',capture=false){const id=++eventId;await publishEvent({id,key,text,capture});return until(async()=>{if(!cold){const s=await status();assert.notEqual(s.status,'failed',s.diagnostics||JSON.stringify(s));}try{const o=await observe();return o.applied===id?o:null;}catch{return null;}});}
async function screenshot(name){await key(undefined,'',true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,name));}
async function saveStatus(name){const s=await status();await writeFile(resolve(output,`${name}.json`),JSON.stringify(s,null,2));return s;}
async function start(action='test'){
 const previous=session?.session_id;await b(action==='test'?'Test room':action==='reset'?'Reset current test':'Test latest saved version').click();session=await running(previous);eventId=0;
 await until(async()=>{try{return await observe();}catch{return null;}});return session;
}
const directions=[[1,0,'right'],[-1,0,'left'],[0,1,'down'],[0,-1,'up']];
async function walk(target){
 for(let step=0;step<200;step++){
  const o=await observe(),[sx,sy]=o.player;if(sx===target[0]&&sy===target[1])return o;
  const queue=[[sx,sy,[]]],seen=new Set([`${sx},${sy}`]);let path;
  for(let i=0;i<queue.length;i++){const [x,y,p]=queue[i];if(x===target[0]&&y===target[1]){path=p;break;}for(const [dx,dy,k] of directions){const nx=x+dx,ny=y+dy,id=`${nx},${ny}`;if(seen.has(id)||!o.walkable[ny]?.[nx]||o.containers.some(c=>c.x===nx&&c.y===ny)||o.decor.some(d=>d.x===nx&&d.y===ny&&['campfire_unlit','campfire_lit','street_lamp_working','crate'].includes(d.id))||o.actors.some(a=>a.x===nx&&a.y===ny))continue;seen.add(id);queue.push([nx,ny,[...p,k]]);}}
  assert(path?.length,`No path from ${o.player} to ${target}`);const after=await key(path[0]);assert.notDeepEqual(after.player,o.player,'ordinary move');assert(!after.dead);
 }throw Error('Path exceeded bound');
}
async function quitGame(){const gamePid=session.pid;await key('escape');const path=resolve(session.state_root,'event.json');await writeFile(path,JSON.stringify({id:++eventId,key:'escape'}));await until(async()=>['stopped','failed'].includes((await status()).status));assert.equal((await status()).status,'stopped');return gamePid;}
async function launch(){
 const port=9561+launchCount++;
 child=spawn(exe,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:recovery,WEBVIEW2_USER_DATA_FOLDER:resolve(output,`webview-${launchCount}`),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${port} --remote-debugging-address=127.0.0.1`}});receipt.host_pid=child.pid;
 await until(async()=>{assert(!exited(child));try{return (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP(`http://127.0.0.1:${port}`);page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(30000);page.on('pageerror',e=>receipt.errors.push(String(e.stack||e)));await page.setViewportSize({width:1600,height:1050});await page.getByTestId('startup-ready').waitFor();await idle();
}
const editor=()=>page.locator('[data-testid="authoring"]:visible');
const props=async()=>{await editor().locator('.author-tabs').getByRole('button',{name:'Properties',exact:true}).click();};
const choose=async(n,v)=>{await page.getByLabel(n,{exact:true}).filter({visible:true}).selectOption(v);await editIdle();};
async function checkedApply(variant=false){
 for(let attempt=0;attempt<5;attempt++){
  const v=await validate();assert(v.valid&&v.review_token,JSON.stringify(v));
  await editor().getByRole('button',{name:/^(Apply variant|Review & apply)$/}).click();await b('Confirm apply one file').click();await idle();
  const footer=await page.locator('footer').innerText();
  if(footer.includes('Saved and byte-checked reopen:'))return v;
  assert.match(footer,/BUSY/);
 }throw Error('Publication stayed busy');
}
async function saved(path){
 const bytes=await readFile(resolve(root,path));const r=await ipc('open_document',{asset:path});assert(r.ok,JSON.stringify(r));
 assert.equal(hash(Buffer.from(r.result.raw)),hash(bytes));assert.equal(r.result.sha256,hash(bytes));
 return {path,sha256:hash(bytes),definition:JSON.parse(bytes),raw:bytes.toString(),token:r.result.document_token};
}
async function recover(row){await b('Recover drafts').click();await page.locator(`[data-recovery-key="${row.key}"]`).click();await b('Recover selected draft').click();await page.getByRole('dialog',{name:'Recover drafts',exact:true}).waitFor({state:'hidden'});await idle();}
async function cell(x,y){const map=page.getByTestId('layout-map').filter({visible:true});await map.scrollIntoViewIfNeeded();const p=await map.evaluate((el,[x,y])=>{const c=JSON.parse(el.dataset.camera),r=el.getBoundingClientRect();return {x:r.x+c.x+(x+.5)*16*c.scale,y:r.y+c.y+(y+.5)*16*c.scale};},[x,y]);await page.mouse.click(p.x,p.y);await editIdle();}
async function place(id,x,y){await choose('Placement kind','item');await choose('Placement item',id);await b('Place item').click();await cell(x,y);}
async function selectInventory(id,instance){
 let o=await observe();if(!o.inventory_open)o=await key('i');
 const index=o.inventory_rows.findIndex(r=>!r.header&&r.item_id===id&&(!instance||r.instance===instance));assert(index>=0,JSON.stringify({id,instance,rows:o.inventory_rows}));
 while(o.inventory_selected!==index)o=await key(o.inventory_selected<index?'down':'up');return o;
}
async function equip(id,slot,instance){
 const before=await selectInventory(id,instance),selected=before.inventory_rows[before.inventory_selected].instance;
 const after=await key('return');assert.equal(after.turn,before.turn+1);assert.equal(after.action_calls,before.action_calls+1);
 assert(after.inventory.some(i=>i.instance===selected));assert.equal(after.equipment[slot]?.instance,before.equipment[slot]?.instance===selected?undefined:selected);
 receipt.actions.push({id,selected,slot,before,after});return after;
}
async function pick(id,which=0){
 let o=await observe();if(o.inventory_open)await key('escape');
 const floor=o.floor.flatMap(r=>r.items.map(i=>({...i,xy:[r.x,r.y]}))).filter(i=>i.item_id===id);const item=floor[which];assert(item,JSON.stringify({id,floor}));
 await walk(item.xy);o=await key(',');assert(o.inventory.some(i=>i.instance===item.instance),JSON.stringify(o));return item;
}
const itemPath=(id,route)=>`roguelike/data/items/${route}/${id}.json`;
async function variant(source,id,route,fields,custom){
 await open(source);await eb('Begin edit').click();await eb('Save as new variant').click();await fill('New variant ID',id);await props();
 for(const [label,value] of Object.entries(fields))await fill(label,String(value));
 await page.getByLabel('Group in inventory',{exact:true}).filter({visible:true}).setChecked(false);await editIdle();
 if(custom)await custom();
 await page.getByLabel(id==='w5m_blade'?'Base damage dice':id==='w5m_jack'?'Layer AV 2':id==='w5m_ward'?'Shield reduction':'Reduction Components',{exact:true}).filter({visible:true}).scrollIntoViewIfNeeded();
 await page.screenshot({path:resolve(output,`controls-${id}.png`)});
 const verdict=await validate();assert(verdict.valid,JSON.stringify(verdict));
 await eb('Diff').click();const diff=await editor().getByTestId('source-diff').innerText();receipt.diffs[id]=diff;
 if(id==='w5m_satchel')await editor().getByTestId('source-diff').evaluate(el=>{el.scrollTop=el.scrollHeight;});
 await page.screenshot({path:resolve(output,`diff-${id}.png`)});
 await apply();receipt.saved[id]=await saved(itemPath(id,route));return receipt.saved[id];
}
async function coldProbe(mode){
 const r=spawnSync(python,['-I','-B',resolve('scripts/equipment-persistence.py'),root,resolve(output,'compatibility'),mode],{windowsHide:true,encoding:'utf8',timeout:60000});
 await writeFile(resolve(output,`ordinary-${mode.slice(2)}.log`),r.stdout+r.stderr);assert.equal(r.status,0,r.stdout+r.stderr);
 return JSON.parse(await readFile(resolve(output,'compatibility',`${mode.slice(2)}.json`),'utf8'));
}
const portable=items=>items.map(({instance,...r})=>r);
try{
 await launch();receipt.saved={};receipt.diffs={};receipt.actions=[];
 await phase('park independent invalid text document; author four useful equipment variants through controls and reviewed single-file publication');
 const parked='roguelike/data/texts/lab/lab_note_primary_a.json';await open(parked);await eb('Begin edit').click();await (await source()).fill('{"parked":"W5M independent λ",');await editIdle();
 await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const other=(await ipc('list_recovery')).records.find(r=>r.source===parked);assert(other);const otherDraft=(await ipc('inspect_recovery',{key:other.key})).record;
 await variant(itemPath('crude_blade','weapons'),'w5m_blade','weapons',{'Item name':'W5M expedition blade','Item weight (kg)':1.2,'Base damage dice':'2d6','Base damage bonus':3,'Additional critical chance':.12});
 // A second dirty item remains independently parked while other item documents save.
 await open(itemPath('w5m_blade','weapons'));await eb('Begin edit').click();await props();await fill('Item description','Unsaved parked weapon description; never captured.');
 await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const dirtyWeapon=(await ipc('list_recovery')).records.find(r=>r.source===itemPath('w5m_blade','weapons'));const weaponDraft=(await ipc('inspect_recovery',{key:dirtyWeapon.key})).record;
 await variant(itemPath('leather_jack','armor'),'w5m_jack','armor',{'Item name':'W5M expedition jack','Item weight (kg)':2,'Layer AV 1':3},async()=>{
  await b('Add armor_layers record').click();await editIdle();await fill('Layer name 2','field lining');await fill('Layer material 2','cloth');await fill('Layer AV 2','2');
  await page.getByRole('button',{name:'up armor_layers 2',exact:true}).click();await editIdle();await page.getByRole('button',{name:'down armor_layers 1',exact:true}).click();await editIdle();
 });
 await variant(itemPath('faceted_ward','shields'),'w5m_ward','shields',{'Item name':'W5M expedition ward','Item weight (kg)':2.4,'Shield block chance':.65,'Shield reduction':4});
 await variant(itemPath('leather_satchel','equipment/satchel'),'w5m_satchel','equipment/satchel',{'Item name':'W5M expedition satchel','Item weight (kg)':.7},async()=>{
  await fill('Reduction all','.2');await choose('New reduction category','Components');await b('Add reduction').click();await editIdle();await fill('Reduction Components','.75');
  await choose('New reduction category','Tools');await b('Add reduction').click();await editIdle();await b('Remove reduction Tools').click();await editIdle();await b('Undo item').click();await editIdle();await b('Redo item').click();await editIdle();
 });
 assert(receipt.diffs.w5m_satchel.includes('+  "on_use": "equip_toggle"')||/\+.*"on_use":"equip_toggle"/.test(receipt.diffs.w5m_satchel),receipt.diffs.w5m_satchel);
 assert.equal((await ipc('inspect_recovery',{key:dirtyWeapon.key})).record.draft,weaponDraft.draft);
 await phase('equipment document dependency freshness, conflict refusal and exact invalid recovery');
 const bagPath=itemPath('w5m_satchel','equipment/satchel');await open(bagPath);await eb('Begin edit').click();await props();await fill('Item description','Equipment conflict probe');assert((await validate()).valid);
 const dep=resolve(root,itemPath('w5m_blade','weapons')),depBytes=await readFile(dep);await writeFile(dep,Buffer.concat([depBytes,Buffer.from('\n')]));
 await until(async()=>await eb('Review & apply').isDisabled(),20000);await writeFile(dep,depBytes);assert((await validate()).valid);
 await eb('Review & apply').click();const bagBytes=await readFile(resolve(root,bagPath)),competing=Buffer.concat([bagBytes,Buffer.from('\n')]);await writeFile(resolve(root,bagPath),competing);await b('Confirm apply one file').click();await idle();
 assert.match(await page.locator('footer').innerText(),/EXTERNAL_MODIFICATION_CONFLICT/);assert.deepEqual(await readFile(resolve(root,bagPath)),competing);await writeFile(resolve(root,bagPath),bagBytes);
 receipt.conflict={dependency_review_staled:true,competing_preserved:true,competing_sha256:hash(competing)};await eb('Discard / Revert').click();await b('Reload document').click();await idle();
 await eb('Begin edit').click();const invalid=receipt.saved.w5m_satchel.raw.slice(0,-2);await (await source()).fill(invalid);await editIdle();await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const recoveryRow=(await ipc('list_recovery')).records.find(r=>r.source===bagPath);child.kill();await until(async()=>exited(child));await browser.close().catch(()=>{});await launch();await recover(other);await recover(dirtyWeapon);await recover(recoveryRow);
 assert.equal(await (await source()).inputValue(),invalid);assert(!(await validate()).valid);assert(await eb('Review & apply').isDisabled());
 await eb('Discard / Revert').click();receipt.recovery={exact_invalid_sha256:hash(invalid),review_revoked:true,parked_weapon_sha256:hash(weaponDraft.draft)};
 await phase('furnished room places saved kit, same-ID shield sibling, ordinary materials and one existing creature through supported controls');
 await open(template);await eb('Begin edit').click();await eb('Save as new variant').click();await fill('New variant ID','w5m_equipment_room');
 const geometry={id:'w5m_equipment_room',width:19,height:11,layers:['###################',...Array(7).fill('#.................#'),'#.<...............#','#.................#','###################'],legend:{'#':'wall','.':'floor','<':'stairs_up'},player_start:{x:3,y:8},special_tiles:[]};
 await (await source()).fill(JSON.stringify(geometry,null,2));await editIdle();
 await choose('Placement kind','decor');await choose('Placement decor','worn_mat');await b('Place decor').click();await cell(4,8);
 for(const [id,x,y] of [['w5m_blade',4,7],['w5m_jack',5,7],['w5m_satchel',6,7],['w5m_ward',7,7],['w5m_ward',8,7]])await place(id,x,y);
 for(const [x,y] of [...Array.from({length:7},(_,i)=>[i+3,4]),...Array.from({length:7},(_,i)=>[i+3,5]),[3,3],[4,3]])await place('wood_bundle',x,y);
 await choose('Placement kind','creature');await choose('Placement creature','stone_lurker');await b('Place creature').click();await cell(16,2);
 const first=await checkedApply(true);receipt.room=await saved(room);receipt.production=first.preview;
 await phase('normal acquisition, nonconsuming paid equip, light displacement and same-ID exact-instance replacement/drop');
 await start('latest');receipt.capture_v1=await saveStatus('capture-v1');let o=await observe();receipt.initial=o;
 const blade=await pick('w5m_blade');await equip('w5m_blade','weapon',blade.instance);await key('escape');
 const jack=await pick('w5m_jack');o=await equip('w5m_jack','armor_torso',jack.instance);assert.equal(o.effective_av,5);await key('escape');
 const satchel=await pick('w5m_satchel');await equip('w5m_satchel','satchel',satchel.instance);await key('escape');
 const ward=await pick('w5m_ward');const lightBefore=await observe();o=await equip('w5m_ward','offhand',ward.instance);assert(lightBefore.light);assert(!o.light);assert(o.inventory.some(i=>i.item_id==='tallow_torch'&&!i.equipped));receipt.light_displacement={before:lightBefore,after:o};await key('escape');
 const sibling=await pick('w5m_ward');o=await equip('w5m_ward','offhand',sibling.instance);assert(!o.inventory.find(i=>i.instance===ward.instance).equipped);
 await selectInventory('w5m_ward',ward.instance);o=await key('d');assert.equal(o.equipment.offhand.instance,sibling.instance);assert(!o.inventory.some(i=>i.instance===ward.instance));assert(o.floor.flatMap(r=>r.items).some(i=>i.instance===ward.instance));receipt.sibling_cleanup={first:ward,sibling,after:o};await key('escape');
 // Reacquire the dropped sibling through normal pickup; it does not replace the equipped instance.
 await pick('w5m_ward');o=await observe();assert.equal(o.equipment.offhand.instance,sibling.instance);
 await key('i');await screenshot('game-equipped-kit.png');await key('escape');
 await phase('same physical load changes carrying; ordinary pickup refuses over-capacity then succeeds with the exact satchel');
 for(let i=0;i<12;i++)await pick('wood_bundle');o=await observe();assert(o.carrying.base_weight>o.carrying.capacity);assert(o.carrying.weight<o.carrying.capacity);
 const load=portable(o.inventory),withBag=o;
 o=await equip('w5m_satchel','satchel',satchel.instance);assert(o.carrying.weight>o.carrying.capacity);assert.deepEqual(portable(o.inventory).map(({equipped,...i})=>i),load.map(({equipped,...i})=>i));await key('escape');
 const extra=o.floor.find(r=>r.items.some(i=>i.item_id==='wood_bundle'));await walk([extra.x,extra.y]);o=await key(',');assert.equal(o.inventory.filter(i=>i.item_id==='wood_bundle').length,12);assert(o.logs.some(s=>s.includes('Too much to carry')));receipt.carrying={withBag,withoutBag:o};
 o=await equip('w5m_satchel','satchel',satchel.instance);await key('escape');o=await key(',');assert.equal(o.inventory.filter(i=>i.item_id==='wood_bundle').length,13);receipt.carrying.admitted=o;
 await key('i');await screenshot('game-carrying.png');await key('escape');
 await phase('actual normal attack and incoming shield route with ordinary game randomness; no encounter/stat injection');
 for(let i=0;i<90;i++){
  o=await observe();const actor=o.actors.find(a=>a.id==='stone_lurker'&&a.hp>0);if(!actor)break;
  const [x,y]=o.player,dx=actor.x-x,dy=actor.y-y;
  if(Math.max(Math.abs(dx),Math.abs(dy))<=1){
   // Let at least one ordinary incoming attack reach the authored shield before attacking.
   if(!o.attacks.some(a=>a.shield?.id==='w5m_ward'))o=await key('z');
   else o=await key(dx===0?(dy<0?'up':'down'):dy===0?(dx<0?'left':'right'):dy<0?(dx<0?'y':'u'):(dx<0?'b':'n'));
  }else{
   o=await key(dx===0?(dy<0?'up':'down'):dx<0?'left':'right');
  }
  assert(!o.dead,'Native encounter death');
 }
 o=await observe();assert(o.attacks.some(a=>a.weapon?.id==='w5m_blade'));assert(o.attacks.some(a=>a.shield?.id==='w5m_ward'));assert(!o.actors.some(a=>a.id==='stone_lurker'&&a.hp>0));receipt.combat=o;await screenshot('game-combat.png');
 await key('f5');await walk([33,24]);o=await key(',','<');assert.equal(o.submap,null);o=await key('.','>');assert(o.submap);await key('f5');receipt.saved_state=await observe();
 await phase('cold ownership/depletion restore and independent ordinary save before source revisions');
 await quitGame();const sessionConfig=resolve(session.state_root,'session.json'),frozenPython=resolve(session.state_root,'..','runtime/python.exe');
 cold=spawn(frozenPython,['-I','-B',resolve('scripts/room-session-audit.py'),sessionConfig],{windowsHide:true,stdio:['ignore','ignore','pipe'],env:{...process.env,SDL_AUDIODRIVER:'dummy'}});let coldError='';cold.stderr.on('data',b=>coldError+=b);eventId=0;
 await until(async()=>{assert(!exited(cold),coldError);try{return (await observe()).pid===cold.pid;}catch{return false;}});o=await observe();
 assert.deepEqual(portable(o.inventory),portable(receipt.saved_state.inventory));assert.equal(o.effective_av,5);assert.deepEqual(o.carrying,receipt.saved_state.carrying);
 for(const [slot,v] of Object.entries(o.equipment))if(v){assert.equal(v.inventory_row,receipt.saved_state.equipment[slot].inventory_row);assert.equal(v.instance,o.inventory[v.inventory_row].instance);}
 assert(!o.floor.flatMap(r=>r.items).some(i=>i.item_id.startsWith('w5m_')));receipt.cold=o;await key('i');await screenshot('game-cold-ownership.png');await key('escape');
 await key('escape');await publishEvent({id:++eventId,key:'escape'});await until(async()=>exited(cold));assert.equal(cold.exitCode,0,coldError);receipt.cold_audit=JSON.parse(await readFile(resolve(session.state_root,'save-path-audit.json'),'utf8'));cold=null;
 receipt.compatibility_before=await coldProbe('--before');
 await phase('revise copied bag name and definition-owned reductions through controls; frozen reset, latest saved and fresh ordinary catalogue are distinct');
 await open(bagPath);await eb('Begin edit').click();await props();await fill('Item name','W5M revised expedition satchel');await fill('Reduction all','.05');await fill('Reduction Components','0');await checkedApply();receipt.revised_bag=await saved(bagPath);
 await open(room);await start('reset');receipt.capture_reset=await saveStatus('capture-reset');o=await observe();assert.equal(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);receipt.reset=o;
 const resetBag=await pick('w5m_satchel');o=await equip('w5m_satchel','satchel',resetBag.instance);assert.equal(o.inventory.find(i=>i.instance===resetBag.instance).name,'W5M expedition satchel');assert.equal(o.carrying.reductions.Components,.75);
 await start('latest');receipt.capture_v2=await saveStatus('capture-v2');o=await observe();assert.notEqual(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);const latestBag=await pick('w5m_satchel');o=await equip('w5m_satchel','satchel',latestBag.instance);assert.equal(o.inventory.find(i=>i.instance===latestBag.instance).name,'W5M revised expedition satchel');assert.equal(o.carrying.reductions.Components,0);receipt.latest=o;
 await b('Stop').click();await until(async()=>(await status()).status==='stopped');receipt.compatibility_after=await coldProbe('--after');
 assert.equal((await ipc('inspect_recovery',{key:other.key})).record.draft,otherDraft.draft);assert.equal((await ipc('inspect_recovery',{key:dirtyWeapon.key})).record.draft,weaponDraft.draft);assert.deepEqual(receipt.errors,[]);receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);if(page){receipt.status=await status().catch(()=>null);await page.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});}throw error;}
finally{await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));if(cold&&!exited(cold))cold.kill();if(page)void ipc('finish_close').catch(()=>{});if(child&&!exited(child))await until(async()=>exited(child),10000).catch(()=>child.kill());await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
