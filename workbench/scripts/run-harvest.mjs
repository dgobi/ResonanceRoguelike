// W5N packaged author -> native defeat -> exact harvest -> preparation -> revision.
import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,cp,rename,access,unlink,readdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const output=resolve('.artifacts/w5n',`native-${Date.now()}`),root=resolve(output,'project'),settings=resolve(output,'settings'),recovery=resolve(output,'recovery');
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
const room='roguelike/data/layouts/w5n_harvest_room.json',template='roguelike/docs/examples/g17_authored_creature_room.json';
const eb=n=>page.locator('[data-testid="authoring"]:visible').getByRole('button',{name:n,exact:true}),b=n=>page.getByRole('button',{name:n,exact:true}).filter({visible:true});
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'),null,{timeout:90000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==='true'));
const fill=async(n,v)=>{for(let attempt=0;attempt<5;attempt++){await idle();const field=page.getByLabel(n,{exact:true}).filter({visible:true});await field.fill(v);await editIdle();const actual=await field.inputValue();if(actual===v||(await field.getAttribute('type')==='number'&&Number(actual)===Number(v)))return;}throw Error(`Edit was not acknowledged: ${n}`);};
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
async function apply(variant=false){await editor().getByRole('button',{name:/^(Apply variant|Review & apply)$/}).click();await b('Confirm apply one file').click();await idle();await page.getByText(/Saved and byte-checked reopen:/).waitFor({timeout:60000});}
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
 const port=9661+launchCount++;
 child=spawn(exe,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:recovery,WEBVIEW2_USER_DATA_FOLDER:resolve(output,`webview-${launchCount}`),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${port} --remote-debugging-address=127.0.0.1`}});receipt.host_pid=child.pid;
 await until(async()=>{assert(!exited(child));try{return (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP(`http://127.0.0.1:${port}`);page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(30000);page.on('pageerror',e=>receipt.errors.push(String(e.stack||e)));await page.setViewportSize({width:1600,height:1050});await page.getByTestId('startup-ready').waitFor();await idle();
}
const editor=()=>page.locator('[data-testid="authoring"]:visible');
const props=async()=>{await editor().locator('.author-tabs').getByRole('button',{name:'Properties',exact:true}).click();};
const choose=async(n,v)=>{for(let attempt=0;attempt<5;attempt++){await idle();const field=page.getByLabel(n,{exact:true}).filter({visible:true});await field.selectOption(v);await editIdle();if(await field.inputValue()===v)return;}throw Error(`Selection was not acknowledged: ${n}`);};
async function newVariant(id){for(let attempt=0;attempt<5;attempt++){await idle();if(!await page.getByLabel('New variant ID',{exact:true}).filter({visible:true}).count()){await eb('Save as new variant').click();await editIdle();}if(await page.getByLabel('New variant ID',{exact:true}).filter({visible:true}).count()){await fill('New variant ID',id);return;}}throw Error('Variant intent was not acknowledged');}
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
async function recover(row){
 for(let attempt=0;attempt<5;attempt++){
  await idle();await b('Recover drafts').click();await idle();await page.locator(`[data-recovery-key="${row.key}"]`).click();await idle();await b('Recover selected draft').click();await idle();
  const dialog=page.getByRole('dialog',{name:'Recover drafts',exact:true});if(!await dialog.count())return;
  assert.match(await page.locator('footer').innerText(),/BUSY/);await b('Keep for later').click();
 }throw Error('Recovery stayed busy');
}
async function cell(x,y){const canvas=page.getByTestId('layout-editor').filter({visible:true});await canvas.locator('.layout-views').getByRole('button',{name:'Authored layout',exact:true}).click();const map=page.getByTestId('layout-map').filter({visible:true});await map.scrollIntoViewIfNeeded();const p=await map.evaluate((el,[x,y])=>{const c=JSON.parse(el.dataset.camera),r=el.getBoundingClientRect();return {x:r.x+c.x+(x+.5)*16*c.scale,y:r.y+c.y+(y+.5)*16*c.scale};},[x,y]);await page.mouse.click(p.x,p.y);await editIdle();}
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
const creaturePath=id=>`roguelike/data/entities/creatures/${id}.json`,toolPath='roguelike/data/items/weapons/w5n_cleaver.json';
const harvest=async()=>{await props();await b('Harvest').click();};
async function reviewed(variant=false){const verdict=await validate();assert(verdict.valid&&verdict.review_token,JSON.stringify(verdict));await eb('Diff').click();const diff=await editor().getByTestId('source-diff').innerText();await apply();return {verdict,diff};}
async function coldProbe(mode){const r=spawnSync(python,['-I','-B',resolve('scripts/harvest-persistence.py'),root,resolve(output,'compatibility'),mode],{windowsHide:true,encoding:'utf8',timeout:60000});await writeFile(resolve(output,`ordinary-${mode.slice(2)}.log`),r.stdout+r.stderr);assert.equal(r.status,0,r.stdout+r.stderr);return JSON.parse(await readFile(resolve(output,'compatibility',`${mode.slice(2)}.json`),'utf8'));}
async function furnish(id,x,y){await choose('Placement kind','decor');await choose('Placement decor',id);await b('Place decor').click();await cell(x,y);}
async function interact(target){let o=await key('e');assert.equal(o.mode,'INTERACTION_CURSOR');for(let i=0;i<5&&!o.interaction.cursor.every((n,i)=>n===target[i]);i++){const [x,y]=o.interaction.cursor;o=await key(x<target[0]?'right':x>target[0]?'left':y<target[1]?'down':'up');}assert.deepEqual(o.interaction.cursor,target);return key('return');}
const portable=items=>items.map(({instance,...r})=>r);
async function encounter(){
 let o=await observe();assert(!o.inventory.some(i=>i.item_id==='raw_meat_common'));assert(!o.floor.flatMap(r=>r.items).some(i=>i.item_id==='raw_meat_common'));
 const tool=await pick('w5n_cleaver');await equip('w5n_cleaver','weapon',tool.instance);await key('escape');
 for(let i=0;i<70;i++){
  o=await observe();const actor=o.actors.find(a=>a.id==='w5n_carrier'&&a.hp>0);if(!actor)break;
  const [x,y]=o.player,dx=actor.x-x,dy=actor.y-y;
  o=await key(dx===0?(dy<0?'up':'down'):dy===0?(dx<0?'left':'right'):Math.max(Math.abs(dx),Math.abs(dy))<=1?(dy<0?(dx<0?'y':'u'):(dx<0?'b':'n')):dx<0?'left':'right');assert(!o.dead);
 }
 o=await observe();assert(!o.actors.some(a=>a.id==='w5n_carrier'&&a.hp>0));assert(o.attacks.some(a=>a.weapon?.id==='w5n_cleaver'));
 const remains=o.floor.flatMap(r=>r.items.filter(i=>i.source_creature==='w5n_carrier').map(i=>({...i,xy:[r.x,r.y]})));assert.equal(remains.length,1);
 return {tool,corpse:remains[0],after:o};
}
async function harvestCorpse(encounter,insufficient=false){
 await walk(encounter.corpse.xy);
 if(insufficient){await equip('w5n_cleaver','weapon',encounter.tool.instance);await key('escape');const before=await observe();const refused=await key(',');assert.equal(refused.turn,before.turn+1);assert(refused.floor.flatMap(r=>r.items).some(i=>i.instance===encounter.corpse.instance));assert(refused.logs.some(s=>s.includes('insufficient')));receipt.insufficient={before,after:refused};await equip('w5n_cleaver','weapon',encounter.tool.instance);await key('escape');}
 const before=await observe(),after=await key(',');assert(!after.floor.flatMap(r=>r.items).some(i=>i.instance===encounter.corpse.instance));assert(after.inventory.some(i=>i.instance===encounter.tool.instance));assert.equal(after.equipment.weapon.instance,encounter.tool.instance);assert.equal(after.turn-before.turn,5);
 return {before,after,outputs:after.floor.find(r=>r.x===encounter.corpse.xy[0]&&r.y===encounter.corpse.xy[1])?.items||[]};
}
try{
 await launch();receipt.saved={};receipt.diffs={};receipt.actions=[];
 await phase('independent dirty text and second creature documents survive harvest authoring/history/recovery');
 const parked='roguelike/data/texts/lab/lab_note_primary_a.json';await open(parked);await eb('Begin edit').click();await (await source()).fill('{"parked":"W5N independent λ",');await editIdle();await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const other=(await ipc('list_recovery')).records.find(r=>r.source===parked),otherDraft=(await ipc('inspect_recovery',{key:other.key})).record;
 await open(creaturePath('hollow_revenant'));await eb('Begin edit').click();await props();await fill('Creature description','W5N parked independent creature; never captured.');await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const second=(await ipc('list_recovery')).records.find(r=>r.source===creaturePath('hollow_revenant')),secondDraft=(await ipc('inspect_recovery',{key:second.key})).record;
 await phase('ordinary creature variant gains a two-tier profile through supported nested controls');
 await open(creaturePath('sewer_thing'));await eb('Begin edit').click();await newVariant('w5n_carrier');await props();
 for(const [label,value] of Object.entries({'Creature name':'W5N marrow carrier','Effective HP':4,'Natural armour':0,'Damage dice':'1d1','Damage bonus':0,'Wander radius':0,'Speed':.25}))await fill(label,String(value));
 await b('Harvest').click();await b('Add harvest profile').click();await editIdle();await choose('Corpse decay','timed');await fill('Decay turns','500');
 for(let i=1;i<=2;i++){await b('Add harvest tier').click();await editIdle();await fill(`Cutting threshold ${i}`,String(i));await b(`Add output to tier ${i}`).click();await editIdle();await choose(`Harvest item ${i}.1`,'raw_meat_common');await fill(`Minimum quantity ${i}.1`,String(i));await fill(`Maximum quantity ${i}.1`,String(i));}
 await b('Add output to tier 2').click();await editIdle();await choose('Harvest item 2.2','animal_bone');await b('up harvest output 2.2').click();await editIdle();await b('down harvest output 2.1').click();await editIdle();await b('remove harvest output 2.2').click();await editIdle();await b('Undo creature').click();await editIdle();await b('Redo creature').click();await editIdle();
 await b('up harvest tier 2').click();await editIdle();await b('down harvest tier 1').click();await editIdle();await b('Add harvest tier').click();await editIdle();await b('remove harvest tier 3').click();await editIdle();
 await page.screenshot({path:resolve(output,'creature-harvest-controls.png')});const first=await reviewed(true);receipt.diffs.creature=first.diff;receipt.saved.creature=await saved(creaturePath('w5n_carrier'));
 assert.equal(receipt.saved.creature.definition.base_hp,4);assert.equal(receipt.saved.creature.definition.speed,.25);assert.equal(receipt.saved.creature.definition.damage_dice,'1d1');assert.equal(receipt.saved.creature.definition.butcher_yield.decay_turns,500);assert.equal(receipt.saved.creature.definition.butcher_yield.tiers.length,2);assert.equal(receipt.saved.creature.definition.butcher_yield.tiers[1].yields.length,1);
 await phase('saved obtainable cutting-tool variant through existing equipment controls');
 await open('roguelike/data/items/weapons/crude_blade.json');await eb('Begin edit').click();await newVariant('w5n_cleaver');await props();await fill('Item name','W5N field cleaver');await fill('Base damage dice','2d6');await fill('Base damage bonus','3');await fill('Keyword tier 1','2');
 const toolReview=await reviewed(true);receipt.diffs.tool=toolReview.diff;receipt.saved.tool=await saved(toolPath);assert.deepEqual(receipt.saved.tool.definition.keywords,[{tag:'cutting',tier:2}]);
 await phase('invalid nested creature recovery restores exact bytes without review authority; other drafts remain intact');
 await open(creaturePath('w5n_carrier'));await eb('Begin edit').click();const invalid=receipt.saved.creature.raw.trimEnd().slice(0,-1);await (await source()).fill(invalid);await editIdle();await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();const recoveryRow=(await ipc('list_recovery')).records.find(r=>r.source===creaturePath('w5n_carrier'));
 child.kill();await until(async()=>exited(child));await browser.close().catch(()=>{});await launch();await recover(other);await recover(second);await recover(recoveryRow);assert.equal(await (await source()).inputValue(),invalid.replace(/\r\n/g,'\n'));assert.equal((await ipc('inspect_recovery',{key:recoveryRow.key})).record.draft,invalid);assert(!(await validate()).valid);assert(await eb('Review & apply').isDisabled());await eb('Discard / Revert').click();receipt.recovery={invalid_sha256:hash(invalid),parked_text_sha256:hash(otherDraft.draft),parked_creature_sha256:hash(secondDraft.draft),review_revoked:true};
 await phase('saved room places obtainable tool, creature and asserted stationary fire through room controls');
 await open(template);await eb('Begin edit').click();await newVariant('w5n_harvest_room');
 const geometry={id:'w5n_harvest_room',width:19,height:11,layers:['###################',...Array(7).fill('#.................#'),'#.<...............#','#.................#','###################'],legend:{'#':'wall','.':'floor','<':'stairs_up'},player_start:{x:3,y:8},special_tiles:[]};await (await source()).fill(JSON.stringify(geometry,null,2));await editIdle();
 await furnish('campfire_unlit',8,5);await place('w5n_cleaver',4,7);await choose('Placement kind','creature');await choose('Placement creature','w5n_carrier');await b('Place creature').click();await cell(13,4);
 const roomReview=await reviewed(true);receipt.room=await saved(room);receipt.production=roomReview.verdict.preview;
 assert(receipt.room.definition.special_tiles.some(r=>r.type==='decor'&&r.decor_id==='campfire_unlit'&&r.x===8&&r.y===5),'Required accepted furnishing record');
 assert(receipt.production.population_receipts.some(r=>r.kind==='decor'&&r.actual_count===1&&r.realized_decor?.id==='campfire_unlit'),JSON.stringify(receipt.production.population_receipts));await page.screenshot({path:resolve(output,'accepted-room.png')});
 await phase('saved dependency revision stales creature review; external source conflict preserves competing bytes');
 await open(creaturePath('w5n_carrier'));await eb('Begin edit').click();await harvest();await fill('Decay turns','501');assert((await validate()).valid);
 const dep=resolve(root,'roguelike/data/items/butchery/raw_meat_common.json'),depBytes=await readFile(dep);await writeFile(dep,Buffer.concat([depBytes,Buffer.from('\n')]));await until(async()=>await eb('Review & apply').isDisabled(),20000);await writeFile(dep,depBytes);assert((await validate()).valid);await eb('Review & apply').click();
 const cp=resolve(root,creaturePath('w5n_carrier')),bytes=await readFile(cp),competing=Buffer.concat([bytes,Buffer.from('\n')]);await writeFile(cp,competing);await b('Confirm apply one file').click();await idle();assert.match(await page.locator('footer').innerText(),/EXTERNAL_MODIFICATION_CONFLICT/);assert.deepEqual(await readFile(cp),competing);await writeFile(cp,bytes);await eb('Discard / Revert').click();receipt.conflict={dependency_stales:true,competing_bytes_preserved:true,competing_sha256:hash(competing)};
 await open(room);await start('latest');receipt.capture_v1=await saveStatus('capture-v1');let o=await observe();receipt.initial=o;
 assert(o.decor.some(r=>r.id==='campfire_unlit'&&r.x===39&&r.y===21));assert(o.floor.flatMap(r=>r.items).some(i=>i.item_id==='w5n_cleaver'));assert(o.actors.some(a=>a.id==='w5n_carrier'));
 await phase('ordinary attacks create actual corpse; bare-hands refusal then exact owned cutter harvest and pickup');
 receipt.encounter=await encounter();await screenshot('native-corpse.png');receipt.harvest=await harvestCorpse(receipt.encounter,true);assert.equal(receipt.harvest.outputs.length,2);assert(receipt.harvest.outputs.every(i=>i.item_id==='raw_meat_common'));await screenshot('native-harvest.png');
 const provenance=receipt.harvest.outputs.map(i=>i.instance);o=await key(',');if(!provenance.every(id=>o.inventory.some(i=>i.instance===id))){assert.equal(o.mode,'INTERACTION_CURSOR');o=await key('down');o=await key('down');o=await key('return');}
 assert(provenance.every(id=>o.inventory.some(i=>i.instance===id)));receipt.harvest.picked=o;
 await phase('light actual authored fire; cook one corpse-derived physical ingredient, collect and eat its result');
 await walk([39,22]);o=await interact([39,21]);assert(o.decor.some(r=>r.id==='campfire_lit'&&r.x===39&&r.y===21));receipt.lit=o;
 o=await key('c');const ci=o.craft.rows.findIndex(r=>r.id==='cook_meat');assert(ci>=0);while(o.craft.selected!==ci)o=await key(o.craft.selected<ci?'down':'up');const beforeCook=o;o=await key('return');assert.equal(o.mode,'PLACEMENT_CURSOR');assert.deepEqual(o.placement.cursor,[39,21]);o=await key('return');assert.equal(o.processing[0].item_id,'cooked_meat');
 const spent=beforeCook.inventory.filter(i=>provenance.includes(i.instance)&&!o.inventory.some(j=>j.instance===i.instance));assert.equal(spent.length,1);assert.equal(o.processing[0].turns_remaining,7);receipt.cooking={before:beforeCook,confirmed:o,spent};await screenshot('native-cooking.png');
 for(let i=0;i<7;i++)o=await key('z');assert.equal(o.processing.length,0);const cooked=o.floor.flatMap(r=>r.items).find(i=>i.item_id==='cooked_meat');assert(cooked);
 o=await key(',');o=await key('up');assert(o.inventory.some(i=>i.instance===cooked.instance));receipt.cooking.output=cooked;
 await selectInventory('cooked_meat',cooked.instance);const beforeUse=await observe();o=await key('return');assert(!o.inventory.some(i=>i.instance===cooked.instance));assert(o.needs.hunger<beforeUse.needs.hunger);assert.equal(o.turn,beforeUse.turn+1);receipt.used={before:beforeUse,after:o};await screenshot('native-used-food.png');await key('escape');
 await walk([33,24]);o=await key(',','<');assert.equal(o.submap,null);o=await key('.','>');assert(o.submap);await key('f5');receipt.saved_state=await observe();assert(receipt.saved_state.decor.some(r=>r.id==='campfire_lit'));assert(!receipt.saved_state.actors.some(a=>a.id==='w5n_carrier'));assert(!receipt.saved_state.floor.flatMap(r=>r.items).some(i=>i.item_id==='w5n_cleaver'||i.source_creature==='w5n_carrier'||i.item_id==='cooked_meat'));
 await phase('separate pinned cold process restores depletion, exact owned tool, consumed food and persistent furnishing');
 await quitGame();await unlink(resolve(session.state_root,'event.json'));receipt.cold_stale_control_removed=true;const sessionConfig=resolve(session.state_root,'session.json'),frozenPython=resolve(session.state_root,'..','runtime/python.exe');cold=spawn(frozenPython,['-I','-B',resolve('scripts/room-session-audit.py'),sessionConfig],{windowsHide:true,stdio:['ignore','ignore','pipe'],env:{...process.env,SDL_AUDIODRIVER:'dummy'}});let coldError='';cold.stderr.on('data',b=>coldError+=b);eventId=0;await until(async()=>{assert(!exited(cold),coldError);try{return (await observe()).pid===cold.pid;}catch{return false;}});o=await observe();assert.deepEqual(portable(o.inventory),portable(receipt.saved_state.inventory));assert.deepEqual(o.decor,receipt.saved_state.decor);assert.equal(o.equipment.weapon.inventory_row,receipt.saved_state.equipment.weapon.inventory_row);assert.equal(o.equipment.weapon.instance,o.inventory[o.equipment.weapon.inventory_row].instance);assert(!o.actors.some(a=>a.id==='w5n_carrier'));assert(!o.floor.flatMap(r=>r.items).some(i=>i.item_id==='w5n_cleaver'||i.source_creature==='w5n_carrier'||i.item_id==='cooked_meat'));receipt.cold=o;await screenshot('native-cold-state.png');await key('escape');await publishEvent({id:++eventId,key:'escape'});await until(async()=>exited(cold));assert.equal(cold.exitCode,0,coldError);receipt.cold_audit=JSON.parse(await readFile(resolve(session.state_root,'save-path-audit.json'),'utf8'));cold=null;
 receipt.compatibility_before=await coldProbe('--before');
 await phase('same-ID creature table/decay and tool copied-tier revision through Workbench; frozen reset versus latest saved');
 await open(creaturePath('w5n_carrier'));await eb('Begin edit').click();await harvest();await fill('Decay turns','900');for(let i=1;i<=2;i++){await choose(`Harvest item ${i}.1`,'animal_bone');await fill(`Minimum quantity ${i}.1`,String(i===2?3:1));await fill(`Maximum quantity ${i}.1`,String(i===2?3:1));}const revision=await reviewed();receipt.diffs.creature_revised=revision.diff;receipt.saved.creature_revised=await saved(creaturePath('w5n_carrier'));
 await open(toolPath);await eb('Begin edit').click();await props();await fill('Keyword tier 1','1');await checkedApply();receipt.saved.tool_revised=await saved(toolPath);
 await open(room);await start('reset');receipt.capture_reset=await saveStatus('capture-reset');assert.equal(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);const resetEncounter=await encounter();assert(resetEncounter.corpse.decay_timer<=500&&resetEncounter.corpse.decay_timer>450);receipt.reset=await harvestCorpse(resetEncounter);assert.equal(receipt.reset.outputs.length,2);assert(receipt.reset.outputs.every(i=>i.item_id==='raw_meat_common'));
 await start('latest');receipt.capture_v2=await saveStatus('capture-v2');assert.notEqual(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);const latestEncounter=await encounter();assert(latestEncounter.corpse.decay_timer<=900&&latestEncounter.corpse.decay_timer>850);receipt.latest=await harvestCorpse(latestEncounter);assert.equal(receipt.latest.outputs.length,1);assert.equal(receipt.latest.outputs[0].item_id,'animal_bone');await screenshot('native-revised-harvest.png');
 await b('Stop').click();await until(async()=>(await status()).status==='stopped');receipt.compatibility_after=await coldProbe('--after');
 assert.equal((await ipc('inspect_recovery',{key:other.key})).record.draft,otherDraft.draft);assert.equal((await ipc('inspect_recovery',{key:second.key})).record.draft,secondDraft.draft);assert.deepEqual(receipt.errors,[]);receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);if(page){receipt.status=await status().catch(()=>null);await page.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});}throw error;}
finally{await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));if(cold&&!exited(cold))cold.kill();if(page)void ipc('finish_close').catch(()=>{});if(child&&!exited(child))await until(async()=>exited(child),10000).catch(()=>child.kill());await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
