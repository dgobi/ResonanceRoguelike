// W5J packaged controls -> saved placement -> ordinary use -> revision/cold load.
import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,cp,rename,access,unlink,readdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const output=resolve('.artifacts/w5j',`native-${Date.now()}`),root=resolve(output,'project'),settings=resolve(output,'settings'),recovery=resolve(output,'recovery');
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
const room='roguelike/data/layouts/w5j_supplies_room.json',template='roguelike/docs/examples/g17_authored_creature_room.json';
const eb=n=>page.locator('[data-testid="authoring"]:visible').getByRole('button',{name:n,exact:true}),b=n=>page.getByRole('button',{name:n,exact:true}).filter({visible:true});
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'),null,{timeout:90000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==='true'));
const fill=async(n,v)=>{await page.getByLabel(n,{exact:true}).filter({visible:true}).fill(v);await editIdle();};
async function phase(label){console.log(label);receipt.checks.push(label);await writeFile(resolve(output,'progress.json'),JSON.stringify(receipt,null,2));}
async function open(path){await idle();await page.getByLabel('Category / route',{exact:true}).selectOption('');await fill('Search ID, name or path',path);await page.locator(`[data-asset="${path}"]`).click();await page.waitForFunction(path=>[...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.offsetParent&&e.querySelector('.filepath')?.textContent===path),path);await idle();}
async function source(){await eb('Source').click();return page.locator('[data-testid="authoring"]:visible textarea.source-editor');}
async function validate(){await editIdle();await idle();await eb('Validate draft').click();await idle();return JSON.parse(await page.locator('[data-testid="authoring"]:visible [data-testid="draft-receipt"]').textContent());}
async function apply(variant=false){await eb(variant?'Apply variant':'Review & apply').click();await b('Confirm apply one file').click();await idle();await page.getByText(/Saved and byte-checked reopen:/).waitFor({timeout:60000});}
async function status(){const r=await ipc('room_test_action',{action:'status'});assert(!r.error,JSON.stringify(r));return r;}
async function until(fn,timeout=60000){const start=Date.now();for(;;){const v=await fn();if(v)return v;assert(Date.now()-start<timeout,'Timed out');await new Promise(r=>setTimeout(r,100));}}
async function running(previous){const began=Date.now();return until(async()=>{const s=await status();if(!s.preparing&&Date.now()-began>1000){const alert=page.getByTestId('room-test-panel').getByRole('alert');if(await alert.count())assert.fail(await alert.innerText());assert(!s.last_action_error&&!s.error,JSON.stringify(s));assert.notEqual(s.status,'failed',JSON.stringify(s));}return s.status==='running'&&!s.preparing&&s.session_id!==previous?s:null;},100000);}
async function observe(){return JSON.parse(await readFile(resolve(session.state_root,'observation.json'),'utf8'));}
let eventId=0;
async function key(key,text='',capture=false){const id=++eventId;const path=resolve(session.state_root,'event.json');await writeFile(path+'.tmp',JSON.stringify({id,key,text,capture}));await rename(path+'.tmp',path);return until(async()=>{if(!cold){const s=await status();assert.notEqual(s.status,'failed',s.diagnostics||JSON.stringify(s));}try{const o=await observe();return o.applied===id?o:null;}catch{return null;}});}
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
  for(let i=0;i<queue.length;i++){const [x,y,p]=queue[i];if(x===target[0]&&y===target[1]){path=p;break;}for(const [dx,dy,k] of directions){const nx=x+dx,ny=y+dy,id=`${nx},${ny}`;if(seen.has(id)||!o.walkable[ny]?.[nx]||o.containers.some(c=>c.x===nx&&c.y===ny)||o.actors.some(a=>a.x===nx&&a.y===ny))continue;seen.add(id);queue.push([nx,ny,[...p,k]]);}}
  assert(path?.length,`No path from ${o.player} to ${target}`);const after=await key(path[0]);assert.notDeepEqual(after.player,o.player,'ordinary move');assert(!after.dead);
 }throw Error('Path exceeded bound');
}
async function quitGame(){const gamePid=session.pid;await key('escape');const path=resolve(session.state_root,'event.json');await writeFile(path,JSON.stringify({id:++eventId,key:'escape'}));await until(async()=>['stopped','failed'].includes((await status()).status));assert.equal((await status()).status,'stopped');return gamePid;}
async function launch(){
 const port=9361+launchCount++;
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
async function selectInventory(id){let o=await observe();if(!o.inventory_open)o=await key('i');const index=o.inventory_rows.findIndex(r=>!r.header&&r.item_id===id);assert(index>=0,JSON.stringify(o.inventory_rows));while(o.inventory_selected!==index)o=await key(o.inventory_selected<index?'down':'up');return o;}
async function use(id,fraction,hp=0){
 let before=await selectInventory(id);const selected=before.inventory_rows[before.inventory_selected].instance;
 const selectedObject=before.inventory.find(r=>r.instance===selected);assert(selectedObject);
 const siblings=before.inventory.filter(r=>r.item_id===id&&r.instance!==selected).map(r=>r.instance);
 const after=await key('return');assert(after.inventory_open);assert.equal(after.action_calls-before.action_calls,1);assert.equal(after.turn-before.turn,1);
 assert(!after.inventory.some(r=>r.instance===selected));for(const instance of siblings)assert(after.inventory.some(r=>r.instance===instance));
 if(fraction){const field=id.includes('drink')?'thirst':'hunger';const observed=before.needs[field]-after.needs[field];assert(Math.abs(observed-fraction)<.005,JSON.stringify({before:before.needs,after:after.needs,fraction}));}
 if(hp)assert.equal(after.hp-before.hp,hp);
 const row={id,selected,siblings,definition:selectedObject,before:{needs:before.needs,hp:before.hp,turn:before.turn,calls:before.action_calls},after:{needs:after.needs,hp:after.hp,turn:after.turn,calls:after.action_calls,inventory:after.inventory,rows:after.inventory_rows}};
 receipt.uses.push(row);return after;
}
const itemPath=id=>`roguelike/data/items/${id==='w5j_material'?'components':'consumables'}/${id}.json`;
async function supply(source,id,values){
 await open(source);await eb('Begin edit').click();await eb('Save as new variant').click();await editIdle();await fill('New variant ID',id);await props();
 for(const [name,value] of Object.entries(values))await fill(name,String(value));
 await choose('Existing tile','generic_item');
 await page.getByLabel('Group in inventory',{exact:true}).filter({visible:true}).setChecked(id==='w5j_food_a');await editIdle();
 await page.getByLabel('Eligible for automatic ingredient selection',{exact:true}).filter({visible:true}).setChecked(id!=='w5j_material');await editIdle();
 if(id==='w5j_material'){
  await fill('Keyword tier 1','2');const text=await (await sourceEditor()).inputValue();
  await (await sourceEditor()).fill(text.replace(/}\s*$/,', "w5j_metadata":{"nested":[null,true,["retained",9]]}\n}'));await editIdle();
 }
 if(id==='w5j_drink'){
  await choose('Return item','empty_water_skin');await validate();await props();
  const draft=await (await sourceEditor()).inputValue();await props();await b('Open return empty_water_skin').click();await idle();
  assert(await eb('Begin edit').isDisabled());await b(/^Return to item /).click();await idle();
  assert.equal(await (await sourceEditor()).inputValue(),draft);receipt.return_navigation={draft_sha256:hash(draft),retained:true};
  await props();await page.getByLabel('Stored hydration',{exact:true}).filter({visible:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,'workbench-drink.png')});
 }
 await checkedApply(true);receipt.saved[id]=await saved(itemPath(id));return receipt.saved[id];
}
const sourceEditor=source;
async function coldProbe(mode){const r=spawnSync(python,['-I','-B',resolve('scripts/supplies-persistence.py'),root,resolve(output,'compatibility'),mode],{windowsHide:true,encoding:'utf8',timeout:60000});await writeFile(resolve(output,`cold-${mode.slice(2)}.log`),r.stdout+r.stderr);assert.equal(r.status,0,r.stdout+r.stderr);return JSON.parse(await readFile(resolve(output,'compatibility',mode==='--before'?'before.json':'after.json'),'utf8'));}
try{
 await launch();receipt.saved={};receipt.uses=[];
 await phase('invalid supply and independent shared draft survive native restart without review authority');
 const base='roguelike/data/items/components/wood_bundle.json',parked='roguelike/data/texts/lab/lab_note_primary_a.json';
 await open(base);await eb('Begin edit').click();await (await source()).fill('{"w5j_invalid":[null,');await editIdle();
 await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const row=(await ipc('list_recovery')).records.find(r=>r.source===base);assert(row);const invalid=(await ipc('inspect_recovery',{key:row.key})).record;
 await open(parked);await eb('Begin edit').click();await (await source()).fill('{"parked":"independent λ",');await editIdle();await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const other=(await ipc('list_recovery')).records.find(r=>r.source===parked);const otherDraft=(await ipc('inspect_recovery',{key:other.key})).record;
 child.kill();await until(async()=>exited(child));await browser.close().catch(()=>{});await launch();
 await recover(other);assert.equal(await (await source()).inputValue(),otherDraft.draft);await recover(row);assert.equal(await (await source()).inputValue(),invalid.draft);assert(await eb('Review & apply').isDisabled());const rejected=await validate();assert(!rejected.valid&&!rejected.review_token);
 await (await source()).fill(await readFile(resolve(root,base),'utf8'));await editIdle();await eb('Discard / Revert').click();await eb('Begin edit').waitFor();
 receipt.recovery={invalid_sha256:hash(invalid.draft),parked_sha256:hash(otherDraft.draft),new_process:child.pid,no_review:true};
 await phase('typed controls create material, two independent foods, drink and treatment; review/apply/exact reopen');
 await supply(base,'w5j_material',{'Item name':'W5J cordwood','Item description':'Authored fuel with an explicit material choice.','Item weight (kg)':.25});
 await supply('roguelike/data/items/consumables/bitter_herb.json','w5j_food_a',{'Item name':'W5J herb ration','Item description':'Fraction-dose field meal.','Item weight (kg)':.05,'Stored nutrition':.35,'Food use message':'W5J herb ration restores you.'});
 await supply('roguelike/data/items/consumables/cooked_meat.json','w5j_food_b',{'Item name':'W5J roast ration','Item description':'Independent points-dose meal.','Item weight (kg)':.1,'Stored nutrition':180,'Food use message':'W5J roast ration restores you.'});
 await supply('roguelike/data/items/consumables/water_flask.json','w5j_drink',{'Item name':'W5J trail drink','Item description':'A quarter-need drink with a saved return.','Item weight (kg)':.3,'Stored hydration':.25,'Drink use message':'W5J trail drink restores you.'});
 await supply('roguelike/data/items/consumables/herbal_dressing.json','w5j_treatment',{'Item name':'W5J field dressing','Item description':'Seven HP of ordinary treatment.','Item weight (kg)':.05,'Treatment healing':7});
 await props();await page.screenshot({path:resolve(output,'workbench-treatment.png')});
 await phase('real external modification conflict preserves competing bytes and unrelated dirty document');
 await open(itemPath('w5j_food_b'));await eb('Begin edit').click();await fill('Stored nutrition','181');assert((await validate()).valid);await eb('Review & apply').click();
 const target=resolve(root,itemPath('w5j_food_b')),original=await readFile(target),competing=Buffer.concat([original,Buffer.from('\n')]);await writeFile(target,competing);
 await b('Confirm apply one file').click();await idle();assert.match(await page.locator('footer').innerText(),/EXTERNAL_MODIFICATION_CONFLICT/);assert.deepEqual(await readFile(target),competing);await writeFile(target,original);
 await eb('Discard / Revert').click();await eb('Begin edit').waitFor();await b('Reload document').click();await idle();
 assert.equal((await ipc('inspect_recovery',{key:other.key})).record.draft,otherDraft.draft);receipt.conflict={code:'EXTERNAL_MODIFICATION_CONFLICT',competing_sha256:hash(competing),preserved:true};
 await phase('saved IDs placed with ordinary room placement controls and exact room publication');
 await open(template);await eb('Begin edit').click();await eb('Save as new variant').click();await fill('New variant ID','w5j_supplies_room');
 const geometry={id:'w5j_supplies_room',width:13,height:9,layers:['#############',...Array(5).fill('#...........#'),'#.<.........#','#...........#','#############'],legend:{'#':'wall','.':'floor','<':'stairs_up'},player_start:{x:3,y:6},special_tiles:[]};
 await (await source()).fill(JSON.stringify(geometry,null,2));await editIdle();
 const ids=['w5j_material','w5j_food_a','w5j_food_a','w5j_food_b','w5j_drink','w5j_drink','w5j_treatment','w5j_treatment'];
 for(let i=0;i<ids.length;i++)await place(ids[i],2+i,3);
 await checkedApply(true);receipt.room=await saved(room);await page.screenshot({path:resolve(output,'workbench-room.png')});
 await phase('latest saved capture; ordinary walking/pickup acquires exact authored floor instances');
 await start('latest');receipt.capture_v1=await saveStatus('capture-v1');let o=await observe();receipt.floor_before=o.floor;
 const floor=o.floor.filter(r=>r.items.some(i=>i.item_id.startsWith('w5j_')));
 for(const tile of floor){assert.equal(tile.items.length,1);const expected=tile.items[0];await walk([tile.x,tile.y]);o=await key(',');assert(o.inventory.some(i=>i.instance===expected.instance));assert(!o.floor.flatMap(r=>r.items).some(i=>i.instance===expected.instance));}
 receipt.acquired=o.inventory.filter(i=>i.item_id.startsWith('w5j_'));assert.equal(receipt.acquired.length,8);await screenshot('game-acquired.png');
 const event=resolve(session.state_root,'event.json'),fixtureId=++eventId;await writeFile(event,JSON.stringify({id:fixtureId,fixture:'supplies-injured'}));await until(async()=>{o=await observe();return o.applied===fixtureId&&o.fixture_applied;});
 receipt.disclosed_fixture={hunger:o.needs.hunger,thirst:o.needs.thirst,hp:o.hp,max_hp:o.max_hp,scope:'Initial need/injury only; subsequent effects, ownership and time are ordinary.'};
 await phase('ordinary inventory input uses two foods, exchanged drink and treatment; selected identities and action counts');
 await use('w5j_food_a',.35);await use('w5j_food_b',.18);o=await use('w5j_drink',.25);
 assert(o.inventory_rows.some(r=>r.item_id==='empty_water_skin'));assert(o.inventory_rows.every(r=>r.instance!==receipt.uses.at(-1).selected));
 await selectInventory('empty_water_skin');await screenshot('game-return-visible.png');await use('w5j_treatment',null,7);await screenshot('game-treatment.png');await key('escape');
 receipt.compatibility_before=await coldProbe('--before');
 await phase('same-ID supply revisions through typed controls; reset retains earlier capture; latest constructs revisions');
 for(const [id,values] of [['w5j_food_a',{'Stored nutrition':.6}],['w5j_drink',{'Stored hydration':.5,'Drink use message':'W5J revised drink message.'}],['w5j_material',{'Item name':'W5J revised cordwood','Item weight (kg)':.4}]]){
  await open(itemPath(id));await eb('Begin edit').click();for(const [name,value] of Object.entries(values))await fill(name,String(value));
  if(id==='w5j_drink')await choose('Return item','w5j_material');await checkedApply();receipt.saved[id+'_revised']=await saved(itemPath(id));
 }
 await open(room);await start('reset');receipt.capture_reset=await saveStatus('capture-reset');assert.equal(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);
 o=await observe();assert.equal(o.floor.flatMap(r=>r.items).find(i=>i.item_id==='w5j_food_a').nutrition,.35);assert.equal(o.floor.flatMap(r=>r.items).find(i=>i.item_id==='w5j_drink').hydration,.25);
 await start('latest');receipt.capture_v2=await saveStatus('capture-v2');assert.notEqual(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);o=await observe();
 assert.equal(o.floor.flatMap(r=>r.items).find(i=>i.item_id==='w5j_food_a').nutrition,.6);assert.equal(o.floor.flatMap(r=>r.items).find(i=>i.item_id==='w5j_drink').hydration,.5);await screenshot('game-revised.png');
 await b('Stop').click();await until(async()=>(await status()).status==='stopped');receipt.compatibility_after=await coldProbe('--after');
 assert.equal((await ipc('inspect_recovery',{key:other.key})).record.draft,otherDraft.draft);assert.deepEqual(receipt.errors,[]);receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);if(page){receipt.status=await status().catch(()=>null);await page.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});}throw error;}
finally{await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));if(page)void ipc('finish_close').catch(()=>{});if(child&&!exited(child))await until(async()=>exited(child),10000).catch(()=>child.kill());await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
