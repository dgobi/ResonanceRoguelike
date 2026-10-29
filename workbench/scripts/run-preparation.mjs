// W5K packaged authoring -> real preparation -> use -> revision/cold compatibility.
import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,cp,rename,access,unlink,readdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const acceptedPath=process.env.RESONANCE_W5K_ACCEPTED_JOURNEY,accepted=acceptedPath?JSON.parse(await readFile(acceptedPath,'utf8')):null;
const output=resolve('.artifacts/w5k',`native-${Date.now()}`),root=accepted?accepted.root:resolve(output,'project'),settings=resolve(output,'settings'),recovery=accepted?resolve(dirname(acceptedPath),'recovery'):resolve(output,'recovery');
if(accepted)assert(root.startsWith(resolve('.artifacts/w5k')+String.fromCharCode(92)));
await mkdir(settings,{recursive:true});
const python=resolve('worker/runtime/python.exe');
if(!accepted){assert.equal(spawnSync(python,['-I','-B','-c',"import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{stdio:'inherit',windowsHide:true}).status,0);
await cp(resolve('../roguelike/assets/sprites'),resolve(root,'roguelike/assets/sprites'),{recursive:true});
await mkdir(resolve(root,'roguelike/docs/examples'),{recursive:true});
for(const name of ['g17_authored_creature_room.json','g17_authored_creature_room.access.json'])await copyFile(resolve('../roguelike/docs/examples',name),resolve(root,'roguelike/docs/examples',name));
}
if(accepted&&process.env.RESONANCE_W5K_REFRESH_RUNTIME==='1')await cp(resolve('../roguelike/engine/recipe_authoring.py'),resolve(root,'roguelike/engine/recipe_authoring.py'));
await writeFile(resolve(settings,'project.json'),JSON.stringify({version:1,project_root:root}));
const hash=b=>createHash('sha256').update(b).digest('hex'),exe=resolve('src-tauri/target/release/resonance-workbench.exe');
const receipt={output,root,checks:[],errors:[],package_sha256:hash(await readFile(exe)),started_utc:new Date().toISOString()};
let child,browser,page,session,cold,sentinel,launchCount=0;
const exited=p=>p.exitCode!==null||p.signalCode!==null;
const room='roguelike/data/layouts/w5k_preparation_room.json',template='roguelike/docs/examples/g17_authored_creature_room.json';
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
  for(let i=0;i<queue.length;i++){const [x,y,p]=queue[i];if(x===target[0]&&y===target[1]){path=p;break;}for(const [dx,dy,k] of directions){const nx=x+dx,ny=y+dy,id=`${nx},${ny}`;if(seen.has(id)||!o.walkable[ny]?.[nx]||o.containers.some(c=>c.x===nx&&c.y===ny)||o.actors.some(a=>a.x===nx&&a.y===ny))continue;seen.add(id);queue.push([nx,ny,[...p,k]]);}}
  assert(path?.length,`No path from ${o.player} to ${target}`);const after=await key(path[0]);assert.notDeepEqual(after.player,o.player,'ordinary move');assert(!after.dead);
 }throw Error('Path exceeded bound');
}
async function quitGame(){const gamePid=session.pid;await key('escape');const path=resolve(session.state_root,'event.json');await writeFile(path,JSON.stringify({id:++eventId,key:'escape'}));await until(async()=>['stopped','failed'].includes((await status()).status));assert.equal((await status()).status,'stopped');return gamePid;}
async function launch(){
 const port=9461+launchCount++;
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
const itemPath=(id,category='consumables')=>`roguelike/data/items/${category}/${id}.json`;
const recipePath=id=>`roguelike/data/recipes/${id}.json`;
async function supply(path,id,category,values,{automatic=true}={}){
 await open(path);await eb('Begin edit').click();await eb('Save as new variant').click();await fill('New variant ID',id);await props();
 for(const [name,value] of Object.entries(values))await fill(name,String(value));
 await page.getByLabel('Group in inventory',{exact:true}).filter({visible:true}).setChecked(false);await editIdle();
 await page.getByLabel('Eligible for automatic ingredient selection',{exact:true}).filter({visible:true}).setChecked(automatic);await editIdle();
 await checkedApply(true);receipt.saved[id]=await saved(itemPath(id,category));return receipt.saved[id];
}
async function recipe(source,id,outputItem,turns,text,quantity){
 await open(recipePath(source));await eb('Begin edit').click();await eb('Save as new variant').click();await fill('New variant ID',id);
 await b('Requirements').click();await fill('Recipe name',`W5K ${id==='w5k_cook'?'roast meal':'field dressing'}`);
 await choose('New tools tag','vessel');await b('Add tools row').click();await editIdle();
 if(quantity)await fill('Required conjunction quantity',String(quantity));
 await b('Preparation').click();await fill('Processing turns',String(turns));await fill('Completion template',text);
 if(source==='cook_meat')assert(await page.getByLabel('Temporary processing marker',{exact:true}).filter({visible:true}).isDisabled());
 await b('Output').click();await choose('Recipe output item',outputItem);await checkedApply(true);receipt.saved[id]=await saved(recipePath(id));
 await b('Output').click();await b(`Open output item ${outputItem}`).click();await idle();await b(/^Return to recipe /).click();await idle();
 await b('Preparation').click();await page.screenshot({path:resolve(output,`workbench-${id}-preparation.png`)});await b('Requirements').click();await page.screenshot({path:resolve(output,`workbench-${id}.png`)});
}
async function craft(id){
 let o=await observe();if(!o.craft.open)o=await key('c');
 const index=o.craft.rows.findIndex(r=>r.id===id);assert(index>=0,JSON.stringify(o.craft));
 while(o.craft.selected!==index)o=await key(o.craft.selected<index?'down':'up');
 return key('return');
}
async function pickOutput(spot,id){
 let o=await observe();const target=o.floor.find(r=>r.x===spot[0]&&r.y===spot[1])?.items.find(i=>i.item_id===id);assert(target);
 assert(Math.max(Math.abs(o.player[0]-spot[0]),Math.abs(o.player[1]-spot[1]))<=1);
 o=await key(',');if(!o.inventory.some(i=>i.instance===target.instance)){
  const dx=spot[0]-o.player[0],dy=spot[1]-o.player[1];const direction=dx===0?(dy<0?'up':'down'):dy===0?(dx<0?'left':'right'):dy<0?(dx<0?'y':'u'):(dx<0?'b':'n');
  o=await key(direction);
 }
 assert(o.inventory.some(i=>i.instance===target.instance));return {target,observation:o};
}
async function coldProbe(mode){
 const r=spawnSync(python,['-I','-B',resolve('scripts/preparation-persistence.py'),root,resolve(output,'compatibility'),mode],{windowsHide:true,encoding:'utf8',timeout:60000});
 await writeFile(resolve(output,`cold-${mode.slice(2)}.log`),r.stdout+r.stderr);assert.equal(r.status,0,r.stdout+r.stderr);
 return JSON.parse(await readFile(resolve(output,'compatibility',`${mode.slice(2)}.json`),'utf8'));
}
async function capturedJob(){
 let o=await observe();
 for(const tile of o.floor.filter(r=>r.items.some(i=>i.item_id.startsWith('w5k_')))){
  await walk([tile.x,tile.y]);await key(',');
 }
 await walk([39,22]);const id=++eventId;await publishEvent({id,fixture:'preparation-heat'});
 await until(async()=>{const v=await observe();return v.applied===id&&v.fixture_applied;});
 o=await craft('w5k_cook');assert(o.craft.choosing);await key('return');o=await key('return');return o;
}
try{
 await launch();receipt.saved={};receipt.uses=[];let other,otherDraft;
 if(accepted){
  assert(accepted.room&&accepted.immediate&&Object.keys(accepted.saved).length===7);
  other=(await ipc('list_recovery')).records.find(r=>r.source==='roguelike/data/texts/lab/lab_note_primary_a.json');assert(other);otherDraft=(await ipc('inspect_recovery',{key:other.key})).record;await recover(other);
  if(process.env.RESONANCE_W5K_RESTORE_BASELINE==='1'){
   const row=accepted.saved.w5k_cook;
   if(hash(await readFile(resolve(root,row.path)))!==row.sha256){
    await open(row.path);await eb('Begin edit').click();await b('Preparation').click();await fill('Processing turns',String(row.definition.processing_turns));await fill('Completion template',row.definition.completion_message);await b('Output').click();await choose('Recipe output item',row.definition.result_item);await checkedApply();
   }
   const food=accepted.saved.w5k_roast;
   if(hash(await readFile(resolve(root,food.path)))!==food.sha256){await open(food.path);await eb('Begin edit').click();await props();await fill('Stored nutrition',String(food.definition.nutrition));await fill('Item name',food.definition.name);await checkedApply();}
   receipt.baseline_restoration={recipe:await saved(row.path),output:await saved(food.path),scope:'Supported controls restore the earlier accepted version for a final-package replay. Immutable captures are untouched.'};
  }
  for(const row of [...Object.values(accepted.saved),accepted.room,accepted.immediate])assert.equal(hash(await readFile(resolve(root,row.path))),row.sha256);
  receipt.saved=accepted.saved;receipt.room=accepted.room;receipt.immediate=accepted.immediate;receipt.recovery=accepted.recovery;receipt.conflict=accepted.conflict;
  receipt.accepted_authoring_continuation={path:resolve(acceptedPath),sha256:hash(await readFile(acceptedPath)),authoring_package_sha256:accepted.package_sha256,gameplay_package_sha256:receipt.package_sha256,runtime_refreshed:process.env.RESONANCE_W5K_REFRESH_RUNTIME==='1',scope:'Exact definitions authored/reopened through supported controls in the preceding packaged process. Its interrupted gameplay is not counted as completed use. This process repeats gameplay and performs revisions/cold checks.'};
  assert.equal(hash(otherDraft.draft),accepted.recovery.parked_sha256);await open(room);await phase('continue from exact accepted UI-authored bytes; recover independent dirty shared draft');
 }else{
 await phase('invalid recipe recovery and independent dirty shared document retain exact source without review');
 const base=recipePath('cook_meat'),parked='roguelike/data/texts/lab/lab_note_primary_a.json';
 await open(base);await eb('Begin edit').click();await (await source()).fill('{"w5k_invalid":[null,');await editIdle();
 await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const row=(await ipc('list_recovery')).records.find(r=>r.source===base);assert(row);const invalid=(await ipc('inspect_recovery',{key:row.key})).record;
 await open(parked);await eb('Begin edit').click();await (await source()).fill('{"parked":"independent λ",');await editIdle();
 await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();other=(await ipc('list_recovery')).records.find(r=>r.source===parked);otherDraft=(await ipc('inspect_recovery',{key:other.key})).record;
 child.kill();await until(async()=>exited(child));await browser.close().catch(()=>{});await launch();
 await recover(other);await recover(row);assert.equal(await (await source()).inputValue(),invalid.draft);assert(await eb('Review & apply').isDisabled());assert(!(await validate()).valid);
 await (await source()).fill(await readFile(resolve(root,base),'utf8'));await editIdle();await eb('Discard / Revert').click();await eb('Begin edit').waitFor();
 receipt.recovery={invalid_sha256:hash(invalid.draft),parked_sha256:hash(otherDraft.draft),fresh_pid:child.pid,no_review:true};
 await phase('supported supply controls save protected meat, automatic herbs, retained vessel and two usable outputs');
 await supply('roguelike/data/items/butchery/raw_meat_common.json','w5k_meat','butchery',{'Item name':'W5K protected field meat','Item description':'Selected deliberately for cooking.','Item weight (kg)':.2},{automatic:false});
 await supply('roguelike/data/items/consumables/bitter_herb.json','w5k_leaf','consumables',{'Item name':'W5K bitter sprig','Item description':'Two sprigs dry into a field treatment.','Item weight (kg)':.03,'Stored nutrition':.05});
 await supply('roguelike/data/items/components/clay_pot.json','w5k_pot','components',{'Item name':'W5K field vessel','Item weight (kg)':.3},{automatic:false});
 await supply('roguelike/data/items/consumables/cooked_meat.json','w5k_roast','consumables',{'Item name':'W5K nourishing roast','Item description':'A prepared quarter-need meal.','Item weight (kg)':.1,'Stored nutrition':.25,'Food use message':'W5K roast restores you.'});
 await supply('roguelike/data/items/consumables/herbal_dressing.json','w5k_dressing','consumables',{'Item name':'W5K dried field dressing','Item weight (kg)':.04,'Treatment healing':9});
 await phase('two independent preparation sources authored with component/conjunction/tool and real passive controls');
 await recipe('cook_meat','w5k_cook','w5k_roast',3,'W5K roast ready: {item_name}.');
 await recipe('dry_bitter_herb','w5k_dry','w5k_dressing',4,'W5K dressing ready: {item_name}.',2);
 await phase('same-ID immediate recipe permission and real publication; dependency invalidation and external conflict');
 await open(recipePath('briar_binding_oil'));await eb('Begin edit').click();await b('Requirements').click();await fill('Recipe description','W5K immediate conjunction permission check.');await checkedApply();receipt.immediate=await saved(recipePath('briar_binding_oil'));
 await open(recipePath('w5k_cook'));await eb('Begin edit').click();await b('Preparation').click();await fill('Processing turns','4');const validated=await validate();assert(validated.valid);
 const dependency=resolve(root,itemPath('w5k_roast')),depBytes=await readFile(dependency);await writeFile(dependency,Buffer.concat([depBytes,Buffer.from('\n')]));
 await until(async()=>await eb('Review & apply').isDisabled(),20000);await writeFile(dependency,depBytes);assert((await validate()).valid);
 await eb('Review & apply').click();const conflict=resolve(root,recipePath('w5k_cook')),original=await readFile(conflict),competing=Buffer.concat([original,Buffer.from('\n')]);await writeFile(conflict,competing);
 await b('Confirm apply one file').click();await idle();assert.match(await page.locator('footer').innerText(),/EXTERNAL_MODIFICATION_CONFLICT/);assert.deepEqual(await readFile(conflict),competing);await writeFile(conflict,original);
 await eb('Discard / Revert').click();await eb('Begin edit').waitFor();await b('Reload document').click();await idle();receipt.conflict={code:'EXTERNAL_MODIFICATION_CONFLICT',competing_sha256:hash(competing),bytes_preserved:true,dependency_staled_review:true};
 await phase('room placements reference saved supplies; geometry alone is disclosed Source fixture');
 await open(template);await eb('Begin edit').click();await eb('Save as new variant').click();await fill('New variant ID','w5k_preparation_room');
 const geometry={id:'w5k_preparation_room',width:13,height:9,layers:['#############',...Array(5).fill('#...........#'),'#.<.........#','#...........#','#############'],legend:{'#':'wall','.':'floor','<':'stairs_up'},player_start:{x:3,y:6},special_tiles:[]};
 await (await source()).fill(JSON.stringify(geometry,null,2));await editIdle();
 const ids=['w5k_meat','w5k_meat','w5k_leaf','w5k_leaf','w5k_leaf','w5k_leaf','w5k_pot'];for(let i=0;i<ids.length;i++)await place(ids[i],2+i,3);
 await checkedApply(true);receipt.room=await saved(room);await page.screenshot({path:resolve(output,'workbench-room.png')});
 }
 await start('latest');receipt.capture_v1=await saveStatus('capture-v1');let o=await observe();receipt.initial_floor=o.floor;
 for(const tile of o.floor.filter(r=>r.items.some(i=>i.item_id.startsWith('w5k_')))){
  const item=tile.items[0];await walk([tile.x,tile.y]);o=await key(',');assert(o.inventory.some(i=>i.instance===item.instance));
 }
 receipt.acquired=o.inventory.filter(i=>i.item_id.startsWith('w5k_'));assert.equal(receipt.acquired.length,7);
 const origin=session.captured.room_path; // capture metadata is retained independently of geometry calculations
 const firePlayer=[Math.floor((80-13)/2)+6,Math.floor((43-9)/2)+5];await walk(firePlayer);
 const fixture=++eventId;await publishEvent({id:fixture,fixture:'preparation-heat'});o=await until(async()=>{const v=await observe();return v.applied===fixture&&v.fixture_applied?v:null;});
 receipt.disclosed_fixture={player:o.player,fire:o.decor.find(r=>r.id==='campfire_lit'),needs:o.needs,hp:o.hp,scope:'Once-only production-created heat and needs/injury fixture; no room-decor authoring or pacing claim.'};
 await phase('ordinary CraftScreen sole protected component picker, picker cancel and placement cancel spend nothing');
 const before=o; o=await craft('w5k_cook');assert(o.craft.choosing);assert.equal(o.craft.prompts[0].options.length,1);assert.equal(o.craft.prompts[0].options[0].item_id,'w5k_meat');
 o=await key('escape');assert.equal(o.turn,before.turn);assert.deepEqual(o.inventory,before.inventory);await key('escape');
 o=await craft('w5k_cook');o=await key('return');assert.equal(o.mode,'PLACEMENT_CURSOR');o=await key('escape');assert.equal(o.turn,before.turn);assert.deepEqual(o.inventory,before.inventory);
 o=await craft('w5k_cook');o=await key('return');const selectedBefore=o.inventory;const cookSpot=o.placement.cursor;o=await key('return');
 assert.equal(o.turn,before.turn+1);assert.equal(o.processing[0].turns_remaining,2);assert.equal(o.processing[0].item_id,'w5k_roast');assert(o.processing[0].on_fire);assert.equal(o.processing[0].decor_id,'');
 assert.equal(o.inventory.filter(i=>i.item_id==='w5k_meat').length,1);assert(o.inventory.some(i=>i.item_id==='w5k_pot'));
 receipt.cooking={before:selectedBefore,confirmed:o,spot:cookSpot,cancel_no_turn:true};await screenshot('game-cooking.png');
 o=await key('z');o=await key('z');assert.equal(o.processing.length,0);assert.equal(o.floor.flatMap(r=>r.items).filter(i=>i.item_id==='w5k_roast').length,1);
 await screenshot('game-roast-floor.png');const roast=await pickOutput(cookSpot,'w5k_roast');receipt.cooking.output=roast.target;await use('w5k_roast',.25);await key('escape');
 await phase('conjunction preparation beside fire commits two distinct leaves, retains vessel, produces floor treatment and ordinary use');
 const dryBefore=await observe();o=await craft('w5k_dry');assert(!o.craft.choosing);assert.equal(o.mode,'PLACEMENT_CURSOR');const drySpot=o.placement.cursor;
 assert.notDeepEqual(drySpot,cookSpot);o=await key('return');assert.equal(o.processing[0].turns_remaining,3);assert.equal(o.processing[0].decor_id,'drying_herb');assert(!o.processing[0].on_fire);
 const spent=dryBefore.inventory.filter(i=>i.item_id==='w5k_leaf'&&!o.inventory.some(j=>j.instance===i.instance));assert.equal(spent.length,2);assert(o.inventory.some(i=>i.item_id==='w5k_pot'));
 receipt.drying={before:dryBefore,confirmed:o,spent,spot:drySpot};await screenshot('game-drying.png');
 for(let i=0;i<3;i++)o=await key('z');assert.equal(o.processing.length,0);const dressing=await pickOutput(drySpot,'w5k_dressing');receipt.drying.output=dressing.target;await use('w5k_dressing',null,9);await screenshot('game-treatment.png');await key('escape');
 receipt.compatibility_before=await coldProbe('--before');
 await phase('same-ID recipe/output revisions through supported controls; old capture reset and latest recipe parameters differ');
 await open(recipePath('w5k_cook'));await eb('Begin edit').click();await b('Preparation').click();await fill('Processing turns','5');await fill('Completion template','W5K revised work ready: {item_name}.');await b('Output').click();await choose('Recipe output item','w5k_dressing');await checkedApply();receipt.saved.w5k_cook_revised=await saved(recipePath('w5k_cook'));
 await open(itemPath('w5k_roast'));await eb('Begin edit').click();await props();await fill('Stored nutrition','.6');await fill('Item name','W5K revised nourishing roast');await checkedApply();receipt.saved.w5k_roast_revised=await saved(itemPath('w5k_roast'));
 await open(room);await start('reset');receipt.capture_reset=await saveStatus('capture-reset');assert.equal(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);
 receipt.reset_job=await capturedJob();assert.equal(receipt.reset_job.processing[0].turns_remaining,2);assert.equal(receipt.reset_job.processing[0].item_id,'w5k_roast');
 await start('latest');receipt.capture_v2=await saveStatus('capture-v2');assert.notEqual(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);
 receipt.latest_job=await capturedJob();assert.equal(receipt.latest_job.processing[0].turns_remaining,4);assert.equal(receipt.latest_job.processing[0].item_id,'w5k_dressing');await screenshot('game-revised-job.png');
 // Separate ordinary-save processes perform captured-versus-current completion,
 // new work from the revised recipe, and bounded missing-definition fault probes.
 await b('Stop').click();await until(async()=>(await status()).status==='stopped');
 receipt.compatibility_after=await coldProbe('--after');
 const outputFile=resolve(root,itemPath('w5k_roast'));await rename(outputFile,outputFile+'.w5k-held');
 try{receipt.missing=await coldProbe('--missing');}finally{await rename(outputFile+'.w5k-held',outputFile);}
 receipt.resumed=await coldProbe('--resume');
 await open(itemPath('w5k_roast'));await eb('Begin edit').click();await props();await fill('Stored nutrition','.8');await checkedApply();receipt.saved.w5k_roast_final=await saved(itemPath('w5k_roast'));
 receipt.compatibility_final=await coldProbe('--final');
 assert.equal((await ipc('inspect_recovery',{key:other.key})).record.draft,otherDraft.draft);assert.deepEqual(receipt.errors,[]);receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);if(page){receipt.status=await status().catch(()=>null);await page.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});}throw error;}
finally{await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));if(page)void ipc('finish_close').catch(()=>{});if(child&&!exited(child))await until(async()=>exited(child),10000).catch(()=>child.kill());await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
