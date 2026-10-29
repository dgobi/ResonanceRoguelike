// W5L packaged authoring -> real preparation -> use -> revision/cold compatibility.
import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,cp,rename,access,unlink,readdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const output=resolve('.artifacts/w5l',`native-${Date.now()}`),root=resolve(output,'project'),settings=resolve(output,'settings'),recovery=resolve(output,'recovery');
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
const room='roguelike/data/layouts/w5l_furnished_room.json',template='roguelike/docs/examples/g17_authored_creature_room.json';
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
 await b('Requirements').click();await fill('Recipe name',`W5L ${id==='w5l_cook'?'roast meal':'field dressing'}`);
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
 const r=spawnSync(python,['-I','-B',resolve('scripts/furnishing-persistence.py'),root,resolve(output,'compatibility'),mode],{windowsHide:true,encoding:'utf8',timeout:60000});
 await writeFile(resolve(output,`cold-${mode.slice(2)}.log`),r.stdout+r.stderr);assert.equal(r.status,0,r.stdout+r.stderr);
 return JSON.parse(await readFile(resolve(output,'compatibility',`${mode.slice(2)}.json`),'utf8'));
}
async function furnish(id,x,y){await choose('Placement kind','decor');await choose('Placement decor',id);await b('Place decor').click();await cell(x,y);}
async function interact(target){
 let o=await key('e');assert.equal(o.mode,'INTERACTION_CURSOR');
 for(let i=0;i<5&&!o.interaction.cursor.every((n,i)=>n===target[i]);i++){
  const [x,y]=o.interaction.cursor;o=await key(x<target[0]?'right':x>target[0]?'left':y<target[1]?'down':'up');
 }
 assert.deepEqual(o.interaction.cursor,target);return key('return');
}
async function selectedCraft(id){
 let o=await observe();if(!o.craft.open)o=await key('c');const n=o.craft.rows.findIndex(r=>r.id===id);assert(n>=0);
 while(o.craft.selected!==n)o=await key(o.craft.selected<n?'down':'up');return o;
}
try{
 await launch();receipt.saved={};receipt.uses=[];
 await phase('independent dirty shared document retained while saving dependencies with supported controls');
 const parked='roguelike/data/texts/lab/lab_note_primary_a.json';await open(parked);await eb('Begin edit').click();await (await source()).fill('{"parked":"W5L independent λ",');await editIdle();
 await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const other=(await ipc('list_recovery')).records.find(r=>r.source===parked);assert(other);const otherDraft=(await ipc('inspect_recovery',{key:other.key})).record;
 await supply('roguelike/data/items/butchery/raw_meat_common.json','w5l_meat','butchery',{'Item name':'W5L protected field meat','Item weight (kg)':.2},{automatic:false});
 await supply('roguelike/data/items/components/clay_pot.json','w5l_pot','components',{'Item name':'W5L retained field vessel','Item weight (kg)':.3},{automatic:false});
 await supply('roguelike/data/items/consumables/cooked_meat.json','w5l_roast','consumables',{'Item name':'W5L nourishing roast','Stored nutrition':.25,'Food use message':'W5L roast restores you.'});
 await recipe('cook_meat','w5l_cook','w5l_roast',3,'W5L roast ready: {item_name}.');
 await phase('new room geometry from Source; furnishings, inputs, readable and real container authored with supported controls');
 await open(template);await eb('Begin edit').click();await eb('Save as new variant').click();await fill('New variant ID','w5l_furnished_room');
 const geometry={id:'w5l_furnished_room',width:19,height:11,layers:['###################',...Array(7).fill('#.................#'),'#.<...............#','#.................#','###################'],legend:{'#':'wall','.':'floor','<':'stairs_up'},player_start:{x:3,y:8},special_tiles:[]};
 await (await source()).fill(JSON.stringify(geometry,null,2));await editIdle();
 await furnish('worn_mat',4,4);await furnish('dried_herbs',3,2);await furnish('street_lamp_working',13,2);await furnish('campfire_unlit',8,5);
 // Exercise reference/edit/move/remove, undo/redo and raw-to-canvas synchronization.
 await choose('Placed record','0');await choose('Marker decor ID','worn_mat');await fill('Decor source X','5');await b('Apply decor edit').click();await editIdle();
 await b('Undo canvas').click();await editIdle();await b('Redo canvas').click();await editIdle();await fill('Decor source X','4');await b('Apply decor edit').click();await editIdle();
 await furnish('tallow_dip',2,2);await b('Delete decor').click();await editIdle();
 await place('w5l_meat',5,6);await place('w5l_pot',6,6);await place('letter',6,3);
 await page.getByLabel('Override readable text',{exact:true}).filter({visible:true}).setChecked(true);await choose('Marker text ID','lab_note_primary_b');await b('Apply item edit').click();await editIdle();
 await choose('Placement kind','container');await choose('Placement container','crate');await b('Place container').click();await cell(15,7);
 await b('Add existing pool').click();await choose('Loot pool 1','storage_tools');await b('Apply container edit').click();await editIdle();
 const first=await checkedApply(true);receipt.room=await saved(room);receipt.production=first.preview;
 assert.equal(receipt.room.definition.special_tiles.filter(r=>r.type==='decor').length,4);
 assert(first.preview.population_receipts.filter(r=>r.kind==='decor').every(r=>r.actual_count===1&&r.objects.length===0));
 assert(first.preview.population_receipts.find(r=>r.kind==='container').objects[0].items.length>0);
 await b('Saved production preview').click();await page.getByTestId('scene-coordinates').waitFor();await page.getByTestId('map').filter({visible:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,'workbench-production.png')});await b('Authored layout').click();await page.getByTestId('layout-map').scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,'workbench-furnished-room.png')});
 await phase('saved furnishing dependency stales real review; external conflict preserves competing room bytes');
 await eb('Begin edit').click();await choose('Placed record','0');await fill('Decor source X','5');await b('Apply decor edit').click();await editIdle();
 assert((await validate()).valid);const dep=resolve(root,'roguelike/data/decoratives.json'),depBytes=await readFile(dep),defs=JSON.parse(depBytes);defs.find(r=>r.id==='worn_mat').description+=' W5L saved dependency probe.';await writeFile(dep,JSON.stringify(defs));
 await until(async()=>await eb('Review & apply').isDisabled(),20000);await writeFile(dep,depBytes);assert((await validate()).valid);
 await eb('Review & apply').click();const conflict=resolve(root,room),roomBytes=await readFile(conflict),competing=Buffer.concat([roomBytes,Buffer.from('\n')]);await writeFile(conflict,competing);await b('Confirm apply one file').click();await idle();
 assert.match(await page.locator('footer').innerText(),/EXTERNAL_MODIFICATION_CONFLICT/);assert.deepEqual(await readFile(conflict),competing);await writeFile(conflict,roomBytes);
 receipt.conflict={competing_sha256:hash(competing),preserved:true,saved_decor_dependency_staled_review:true};await eb('Discard / Revert').click();await eb('Begin edit').waitFor();await b('Reload document').click();await idle();
 await phase('invalid furnished draft recovery loses review authority and preserves independent shared draft');
 await eb('Begin edit').click();const invalid=receipt.room.raw.slice(0,-2);await (await source()).fill(invalid);await editIdle();await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const row=(await ipc('list_recovery')).records.find(r=>r.source===room);assert(row);child.kill();await until(async()=>exited(child));await browser.close().catch(()=>{});await launch();await recover(other);await recover(row);
 assert.equal(await (await source()).inputValue(),invalid);assert(!(await validate()).valid);assert(await eb('Review & apply').isDisabled());
 await (await source()).fill(receipt.room.raw);await editIdle();assert((await validate()).valid);await eb('Discard / Revert').click();await eb('Begin edit').waitFor();receipt.recovery={furnished_invalid_sha256:hash(invalid),parked_sha256:hash(otherDraft.draft),fresh_pid:child.pid};
 await phase('Test room constructs all authored furnishings; ordinary movement verifies blocker and isolated static-light FOV contribution');
 await start('latest');receipt.capture_v1=await saveStatus('capture-v1');let o=await observe();receipt.initial=o;
 const lamp=[44,18],fire=[39,21];assert(o.decor.some(r=>r.id==='campfire_unlit'&&r.x===39&&r.y===21));
 await walk([43,18]);const beforeBlock=await observe();o=await key('right');assert.deepEqual(o.player,beforeBlock.player);receipt.blocker={before:beforeBlock.player,after:o.player,target:lamp};
 await selectInventory('tallow_torch');o=await key('return');assert(!o.light);await key('escape');o=await observe();
 assert(o.lighting.emitters.some(r=>r.id==='street_lamp_working'&&r.visible));assert(o.lighting.visible_beyond_player_circle.length>0);
 receipt.light={player:o.player,light:o.light,lighting:o.lighting,scope:'Actual production secondary FOV beyond the player circle with torch extinguished and campfire initially unlit; no added RGB-decor lighting behavior claimed.'};await screenshot('game-authored-light.png');
 await selectInventory('tallow_torch');await key('return');await key('escape');
 for(const tile of (await observe()).floor.filter(r=>r.items.some(i=>['w5l_meat','w5l_pot'].includes(i.item_id)))){const item=tile.items[0];await walk([tile.x,tile.y]);o=await key(',');assert(o.inventory.some(i=>i.instance===item.instance));}
 await walk([39,22]);const fixture=++eventId;await publishEvent({id:fixture,fixture:'supplies-injured'});o=await until(async()=>{const v=await observe();return v.applied===fixture&&v.fixture_applied?v:null;});receipt.disclosed_needs={needs:o.needs,hp:o.hp,scope:'Once-only needs/health setup; no decor/heat event was sent.'};
 await selectedCraft('w5l_cook');await screenshot('game-choose-protected-unlit.png');const unlitBefore=await observe();o=await key('return');assert(o.craft.choosing);o=await key('return');assert(!o.craft.open&&o.mode!=='PLACEMENT_CURSOR');assert.deepEqual(o.inventory,unlitBefore.inventory);assert.equal(o.turn,unlitBefore.turn);assert(o.logs.some(s=>s.includes('stationary fire')));receipt.unlit_failure=o;
 await phase('ordinary interaction lights authored campfire; normal protected choice, placement, first tick, floor output, pickup and food use');
 o=await interact(fire);assert(o.decor.some(r=>r.id==='campfire_lit'&&r.x===39&&r.y===21));receipt.lit=o;
 await selectedCraft('w5l_cook');await screenshot('game-choose-protected-lit.png');const beforeCook=await observe();await key('return');o=await key('return');assert.equal(o.mode,'PLACEMENT_CURSOR');assert.deepEqual(o.placement.cursor,fire);o=await key('return');
 assert.equal(o.turn,beforeCook.turn+1);assert.equal(o.processing[0].turns_remaining,2);assert.equal(o.inventory.filter(i=>i.item_id==='w5l_meat').length,0);assert(o.inventory.some(i=>i.item_id==='w5l_pot'));receipt.cooking={before:beforeCook,confirmed:o};await screenshot('game-authored-cooking.png');
 await key('z');o=await key('z');assert.equal(o.processing.length,0);assert.equal(o.floor.flatMap(r=>r.items).filter(i=>i.item_id==='w5l_roast').length,1);await screenshot('game-floor-output.png');receipt.cooking.output=(await pickOutput(fire,'w5l_roast')).target;await use('w5l_roast',.25);await screenshot('game-used-roast.png');await key('escape');
 o=await interact(fire);assert(o.decor.some(r=>r.id==='campfire_unlit'));receipt.extinguished=o;await key('f5');
 await walk([33,24]);o=await key(',','<');assert.equal(o.submap,null);o=await key('.','>');assert(o.submap);assert(o.decor.some(r=>r.id==='campfire_unlit'));await key('f5');receipt.saved_state=await observe();
 await phase('cold restore in separate pinned process retains exact used state; ordinary-save fixture before room revision');
 await quitGame();const sessionConfig=resolve(session.state_root,'session.json'),frozenPython=resolve(session.state_root,'..','runtime/python.exe');
 cold=spawn(frozenPython,['-I','-B',resolve('scripts/room-session-audit.py'),sessionConfig],{windowsHide:true,stdio:['ignore','ignore','pipe'],env:{...process.env,SDL_AUDIODRIVER:'dummy'}});let coldError='';cold.stderr.on('data',b=>coldError+=b);eventId=0;
 await until(async()=>{assert(!exited(cold),coldError);try{return (await observe()).pid===cold.pid;}catch{return false;}});o=await observe();
 for(const k of ['player','submap','needs','hp','decor'])assert.deepEqual(o[k],receipt.saved_state[k]);
 const portable=items=>items.map(({instance,...r})=>r);assert.deepEqual(portable(o.inventory),portable(receipt.saved_state.inventory));assert(!o.inventory.some(r=>r.item_id==='w5l_meat'||r.item_id==='w5l_roast'));assert(!o.floor.flatMap(r=>r.items).some(r=>r.item_id==='w5l_roast'));receipt.cold=o;await screenshot('game-cold-state.png');await key('z');assert(!(await observe()).floor.flatMap(r=>r.items).some(r=>r.item_id==='w5l_roast'));await key('escape');await publishEvent({id:++eventId,key:'escape'});await until(async()=>exited(cold));assert.equal(cold.exitCode,0,coldError);receipt.cold_audit=JSON.parse(await readFile(resolve(session.state_root,'save-path-audit.json'),'utf8'));cold=null;
 receipt.compatibility_before=await coldProbe('--before');
 await phase('same-ID furnishing revision through controls; immutable reset versus latest saved capture');
 await open(room);await eb('Begin edit').click();await choose('Placed record','3');await fill('Decor source X','10');await b('Apply decor edit').click();await editIdle();await checkedApply();receipt.room_revised=await saved(room);
 await start('reset');receipt.capture_reset=await saveStatus('capture-reset');o=await observe();assert.equal(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);assert(o.decor.some(r=>r.id==='campfire_unlit'&&r.x===39&&r.y===21));receipt.reset=o;
 await start('latest');receipt.capture_v2=await saveStatus('capture-v2');o=await observe();assert.notEqual(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);assert(o.decor.some(r=>r.id==='campfire_unlit'&&r.x===41&&r.y===21));assert(!o.decor.some(r=>r.x===39&&r.y===21));receipt.latest=o;await screenshot('game-revised-furnishing.png');await b('Stop').click();await until(async()=>(await status()).status==='stopped');
 receipt.compatibility_after=await coldProbe('--after');
 assert.equal((await ipc('inspect_recovery',{key:other.key})).record.draft,otherDraft.draft);assert.deepEqual(receipt.errors,[]);receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);if(page){receipt.status=await status().catch(()=>null);await page.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});}throw error;}
finally{await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));if(cold&&!exited(cold))cold.kill();if(page)void ipc('finish_close').catch(()=>{});if(child&&!exited(child))await until(async()=>exited(child),10000).catch(()=>child.kill());await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
