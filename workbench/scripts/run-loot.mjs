// W5O packaged pool authoring, exact container transfers/use and catalogue activation.
import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,cp,rename,access,unlink,readdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const output=resolve('.artifacts/w5o',`native-${Date.now()}`),root=resolve(output,'project'),settings=resolve(output,'settings'),recovery=resolve(output,'recovery');
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
const room='roguelike/data/layouts/w5o_loot_room.json',template='roguelike/docs/examples/g17_authored_creature_room.json';
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
async function validate(){for(let attempt=0;attempt<5;attempt++){await editIdle();await idle();await eb('Validate draft').click();await idle();const v=editor().getByTestId('draft-receipt');if(await v.count())return JSON.parse(await v.textContent());const footer=await page.locator('footer').innerText();assert.match(footer,/BUSY/);}throw Error('Validation stayed busy');}
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
 const port=9761+launchCount++;
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
let containerTarget,returnStair;
const poolPath=id=>`roguelike/data/loot_pools/${id}.json`,foodPath='roguelike/data/items/consumables/w5o_biscuit.json';
const poolEditor=()=>page.getByTestId('pool-editor').filter({visible:true});
const poolRaw=async()=>{const text=await (await source()).inputValue();return JSON.parse(text);};
async function addItem(id){await choose('New pool item',id);await b('Add entry').click();await editIdle();}
async function clearEntries(){while(await poolEditor().getByLabel('Remove entry 1',{exact:true}).count()){await poolEditor().getByLabel('Remove entry 1',{exact:true}).click();await editIdle();}}
async function reviewed(name){const v=await validate();assert(v.valid&&v.review_token,JSON.stringify(v));await eb('Diff').click();receipt.diffs[name]=await editor().getByTestId('source-diff').innerText();await checkedApply();return v;}
async function selectInventory(id,instance){let o=await observe();if(!o.inventory_open)o=await key('i');const index=o.inventory_rows.findIndex(r=>!r.header&&r.item_id===id&&(!instance||r.instance===instance));assert(index>=0,JSON.stringify(o.inventory_rows));while(o.inventory_selected!==index)o=await key(o.inventory_selected<index?'down':'up');return o;}
async function interact(target){let o=await key('e');assert.equal(o.mode,'INTERACTION_CURSOR');for(let i=0;i<12&&!o.interaction.cursor.every((n,i)=>n===target[i]);i++){const [x,y]=o.interaction.cursor;o=await key(x<target[0]?'right':x>target[0]?'left':y<target[1]?'down':'up');}assert.deepEqual(o.interaction.cursor,target);return key('return');}
async function take(id){let o=await observe();if(o.inventory_open)await key('escape');await walk([containerTarget[0],containerTarget[1]+1]);o=await interact(containerTarget);const prompt=o.interaction.selection;assert.equal(prompt?.source,'container');const index=prompt.items.findIndex(i=>i.item_id===id);assert(index>=0);const selected=prompt.items[index];for(let i=0;i<index;i++)await key('down');const before=await observe(),after=await key('return');assert(after.inventory.some(i=>i.instance===selected.instance));assert(!after.containers.flatMap(c=>c.items).some(i=>i.instance===selected.instance));assert.equal(after.turn,before.turn+1);return {selected,before,after};}
const portable=items=>items.map(({instance,...r})=>r);
const containerState=o=>o.containers.map(c=>({...c,items:portable(c.items)}));
async function ordinary(mode){const r=spawnSync(python,['-I','-B',resolve('scripts/loot-persistence.py'),root,resolve(output,'ordinary'),mode],{windowsHide:true,encoding:'utf8',timeout:60000});await writeFile(resolve(output,`${mode.slice(2)}.log`),r.stdout+r.stderr);assert.equal(r.status,0,r.stdout+r.stderr);return JSON.parse(await readFile(resolve(output,'ordinary',`${mode.slice(2)}.json`),'utf8'));}
try{
 await launch();receipt.saved={};receipt.diffs={};
 await phase('save and byte-check reopen one useful food through the existing item editor');
 await open('roguelike/data/items/consumables/cooked_meat.json');await eb('Begin edit').click();await newVariant('w5o_biscuit');await props();
 for(const [label,value] of Object.entries({'Item name':'W5O travel biscuit','Item description':'Disposable contextual-loot reward.','Item weight (kg)':.05,'Stored nutrition':.2,'Food use message':'The biscuit settles your hunger.'}))await fill(label,String(value));
 await reviewed('food');receipt.saved.food=await saved(foodPath);
 await phase('two saved pool variants, complete row controls, omitted defaults and coherent Source/table history');
 await open(poolPath('alchemist_reagents'));await eb('Begin edit').click();await newVariant('w5o_provisions');await clearEntries();await addItem('w5o_biscuit');await addItem('wood_bundle');await addItem('w5o_biscuit');
 await b('up pool entry 3').click();await editIdle();await b('down pool entry 2').click();await editIdle();await b('up pool entry 3').click();await editIdle();
 await addItem('flint_shard');await b('Remove entry 4').click();await editIdle();await b('Undo pool').click();await editIdle();assert.equal((await poolRaw()).items.length,4);await b('Redo pool').click();await editIdle();
 await choose('Roll count representation','fixed');await fill('Minimum rolls','3');await fill('Weight 1','5');await b('Use default weight 1').click();await editIdle();await fill('Weight 2','2');await fill('Pool description','Guaranteed two useful meals and a distinguishable residual log.');
 const beforeMetadata=await (await source()).inputValue(),object=JSON.parse(beforeMetadata);object.owner_metadata={nested:[null,'λ'],escaped:'retained'};object.items[0].row_metadata={nested:{keep:[1,null]}};
 const metadata=JSON.stringify(object,null,2).replace('"retained"','"\\u0072etained"');await (await source()).fill(metadata);await editIdle();await fill('Weight 2','7');const afterTable=await (await source()).inputValue();
 await b('Undo pool').click();await editIdle();assert.equal(await (await source()).inputValue(),metadata);await b('Undo pool').click();await editIdle();assert.equal(await (await source()).inputValue(),beforeMetadata);await b('Redo pool').click();await b('Redo pool').click();await editIdle();assert.equal(await (await source()).inputValue(),afterTable);
 await reviewed('pool_a');receipt.saved.pool_a=await saved(poolPath('w5o_provisions'));assert.deepEqual(receipt.saved.pool_a.definition.roll_count,[3]);assert(!('weight' in receipt.saved.pool_a.definition.items[0]));
 await open(poolPath('storage_tools'));await eb('Begin edit').click();await newVariant('w5o_lights');await clearEntries();await addItem('tallow_torch');await choose('Roll count representation','range');await fill('Minimum rolls','1');await fill('Maximum rolls','1');await choose('Roll count representation','default');await b('Use default weight 1').click();await editIdle();await fill('Pool description','One saved reference-only held light.');await reviewed('pool_b');receipt.saved.pool_b=await saved(poolPath('w5o_lights'));assert(!('roll_count' in receipt.saved.pool_b.definition));
 await page.screenshot({path:resolve(output,'pool-controls.png')});
 await phase('two pool drafts plus malformed unrelated draft recover across a real host restart without review authority');
 const parked='roguelike/data/texts/lab/lab_note_primary_a.json';await open(parked);await eb('Begin edit').click();await (await source()).fill('{"parked":"W5O λ",');await editIdle();
 await open(poolPath('w5o_lights'));await eb('Begin edit').click();await fill('Pool description','Parked pool draft; excluded from saved capture.');
 await open(poolPath('w5o_provisions'));await eb('Begin edit').click();await newVariant('w5o_unfinished');const invalid=(await (await source()).inputValue()).trimEnd().slice(0,-1);await (await source()).fill(invalid);await editIdle();
 await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();const records=(await ipc('list_recovery')).records.filter(r=>[parked,poolPath('w5o_lights'),poolPath('w5o_provisions')].includes(r.source));assert.equal(records.length,3);
 const recoveryBytes={};for(const row of records)recoveryBytes[row.source]=(await ipc('inspect_recovery',{key:row.key})).record;
 child.kill();await until(async()=>exited(child));await browser.close().catch(()=>{});await launch();for(const row of records)await recover(row);
 await open(poolPath('w5o_provisions'));assert.equal(await (await source()).inputValue(),invalid);assert.equal(await page.getByLabel('New variant ID',{exact:true}).filter({visible:true}).inputValue(),'w5o_unfinished');await eb('Validate draft').click();await idle();assert.match(await page.locator('footer').innerText(),/VARIANT_ID/);assert(await eb('Review & apply').isDisabled());assert.equal(await editor().getByTestId('draft-receipt').count(),0);
 for(const row of records)assert.equal((await ipc('inspect_recovery',{key:row.key})).record.draft,recoveryBytes[row.source].draft);
 await page.screenshot({path:resolve(output,'recovered-drafts.png')});receipt.recovery={records:recoveryBytes,review_revoked:true};await eb('Discard / Revert').click();
 await phase('existing ordinary-building to shared pool to item and exact return; changed row location is disclosed stale');
 const building='roguelike/data/buildings/commercial/apothecary_a.json';await open(building);await eb('Begin edit').click();await fill('Description','W5O retained building draft.');
 const map=page.getByTestId('layout-map').filter({visible:true});await map.scrollIntoViewIfNeeded();const point=await map.evaluate(el=>{const c=JSON.parse(el.dataset.camera),r=el.getBoundingClientRect();return {x:r.x+c.x+1.5*16*c.scale,y:r.y+c.y+1.5*16*c.scale};});await page.mouse.click(point.x,point.y);await b('Open pool alchemist_reagents').click();await idle();const firstId=await poolEditor().getByLabel('Item ID 1',{exact:true}).inputValue();await b(`Open item ${firstId}`).first().click();await idle();await b(/^Return to pool alchemist_reagents row 1$/).click();await b(/^Return to container apothecary_a$/).click();await idle();assert.equal(await page.getByLabel('Description',{exact:true}).filter({visible:true}).inputValue(),'W5O retained building draft.');receipt.building_return=true;
 await open(poolPath('w5o_provisions'));await eb('Begin edit').click();await b('Open item w5o_biscuit').first().click();await idle();await page.locator(`[data-document-tab="${poolPath('w5o_provisions')}"]`).click();await fill('Pool description','Changed while away');await page.locator(`[data-document-tab="${foodPath}"]`).click();await b(/^Return to pool w5o_provisions row 1$/).click();await page.getByTestId('stale-pool-location').filter({visible:true}).waitFor();receipt.stale_row_disclosed=true;await eb('Discard / Revert').click();
 await phase('room controls link both saved pools; assert exact accepted records and four real contents before native launch');
 await open(template);await eb('Begin edit').click();await newVariant('w5o_loot_room');const geometry={id:'w5o_loot_room',width:19,height:11,layers:['###################',...Array(7).fill('#.................#'),'#.<...............#','#.................#','###################'],legend:{'#':'wall','.':'floor','<':'stairs_up'},player_start:{x:3,y:8},special_tiles:[]};
 await (await source()).fill(JSON.stringify(geometry,null,2));await editIdle();await choose('Placement kind','container');await choose('Placement container','crate');await b('Place container').click();await cell(5,6);await cell(5,6);await b('Add existing pool').click();await choose('Loot pool 1','w5o_provisions');await b('Add existing pool').click();await choose('Loot pool 2','w5o_lights');await b('Apply container edit').click();await editIdle();
 const roomVerdict=await reviewed('room');receipt.production=roomVerdict.preview;receipt.room=await saved(room);assert.deepEqual(receipt.room.definition.special_tiles,[{x:5,y:6,type:'container',decor_id:'crate',loot_pools:['w5o_provisions','w5o_lights']}]);const produced=receipt.production.containers[0];assert(produced);containerTarget=[produced.x,produced.y];assert.deepEqual(containerTarget,[receipt.production.origin[0]+5,receipt.production.origin[1]+6]);returnStair=[receipt.production.origin[0]+2,receipt.production.origin[1]+8];assert.deepEqual(produced.items.map(i=>i.item_id).sort(),['w5o_biscuit','w5o_biscuit','wood_bundle','tallow_torch'].sort());await page.screenshot({path:resolve(output,'accepted-room.png')});
 await cell(5,6);await b('Open pool w5o_provisions').click();await idle();const refs=await poolEditor().innerText();assert(refs.includes('w5o_loot_room'));await b('Open item w5o_biscuit').first().click();await b(/^Return to pool w5o_provisions row 1$/).click();await b(/^Return to container w5o_loot_room$/).click();receipt.room_return=true;
 await phase('external conflict and saved item dependency changes revoke review and preserve competing bytes');
 await open(poolPath('w5o_provisions'));await eb('Begin edit').click();await fill('Pool description','Conflict draft');assert((await validate()).valid);const dep=resolve(root,foodPath),depBytes=await readFile(dep);await writeFile(dep,Buffer.concat([depBytes,Buffer.from('\n')]));await until(async()=>await eb('Review & apply').isDisabled(),20000);await writeFile(dep,depBytes);assert((await validate()).valid);await eb('Review & apply').click();
 const cp=resolve(root,poolPath('w5o_provisions')),bytes=await readFile(cp),competing=Buffer.concat([bytes,Buffer.from('\n')]);await writeFile(cp,competing);await b('Confirm apply one file').click();await idle();assert.match(await page.locator('footer').innerText(),/EXTERNAL_MODIFICATION_CONFLICT/);assert.deepEqual(await readFile(cp),competing);await writeFile(cp,bytes);await eb('Discard / Revert').click();receipt.conflict={dependency_stales:true,competing_preserved:true,sha256:hash(competing)};
 await open(room);await start('latest');receipt.capture_v1=await saveStatus('capture-v1');receipt.initial=await observe();assert(!receipt.initial.fixture_applied);assert.deepEqual(receipt.initial.containers[0].items.map(i=>i.item_id).sort(),produced.items.map(i=>i.item_id).sort());
 await phase('normal movement/container transfer acquires exact rolled biscuit, ordinary inventory use consumes it, second meal stays owned');
 receipt.taken=await take('w5o_biscuit');const beforeUse=await selectInventory('w5o_biscuit',receipt.taken.selected.instance),afterUse=await key('return');assert(!afterUse.inventory.some(i=>i.instance===receipt.taken.selected.instance));assert(afterUse.needs.hunger<beforeUse.needs.hunger);assert.equal(afterUse.turn,beforeUse.turn+1);receipt.used={before:beforeUse,after:afterUse};await screenshot('native-used-loot.png');await key('escape');receipt.retained=await take('w5o_biscuit');await screenshot('native-partial-container.png');
 await walk(returnStair);let o=await key(',','<');assert.equal(o.submap,null);o=await key('.','>');assert(o.submap);await key('f5');receipt.saved_state=await observe();assert.deepEqual(receipt.saved_state.containers[0].items.map(i=>i.item_id).sort(),['wood_bundle','tallow_torch'].sort());assert.equal(receipt.saved_state.containers[0].state,'open');
 await phase('separate pinned --load process restores partial container, acquired exact copied fields and absent consumed loot without reroll');
 await quitGame();await unlink(resolve(session.state_root,'event.json'));const config=resolve(session.state_root,'session.json');cold=spawn(resolve(session.state_root,'..','runtime/python.exe'),['-I','-B',resolve('scripts/room-session-audit.py'),config],{windowsHide:true,stdio:['ignore','ignore','pipe'],env:{...process.env,SDL_AUDIODRIVER:'dummy'}});let coldError='';cold.stderr.on('data',b=>coldError+=b);eventId=0;await until(async()=>{assert(!exited(cold),coldError);try{return (await observe()).pid===cold.pid;}catch{return false;}});
 o=await observe();assert.deepEqual(portable(o.inventory),portable(receipt.saved_state.inventory));assert.deepEqual(containerState(o),containerState(receipt.saved_state));receipt.cold=o;await walk([containerTarget[0],containerTarget[1]+1]);await interact(containerTarget);await key('escape');o=await observe();assert.deepEqual(containerState(o),containerState(receipt.saved_state));for(let i=0;i<4;i++){const current=await observe();if(current.mode==='LOCAL'&&!current.inventory_open)break;await key('escape');}await screenshot('native-cold-state.png');await key('escape');await publishEvent({id:++eventId,key:'escape'});await until(async()=>exited(cold));assert.equal(cold.exitCode,0,coldError);receipt.cold_audit=JSON.parse(await readFile(resolve(session.state_root,'save-path-audit.json'),'utf8'));cold=null;
 receipt.ordinary_before=await ordinary('--before');
 await phase('same-ID saved pool revision changes fresh sample; reset keeps old capture; latest saved captures revised contents');
 await open(poolPath('w5o_provisions'));await eb('Begin edit').click();await clearEntries();await addItem('animal_bone');await choose('Roll count representation','fixed');await fill('Minimum rolls','1');await fill('Pool description','Revised fresh salvage: one bone.');await reviewed('pool_a_revised');receipt.saved.pool_a_revised=await saved(poolPath('w5o_provisions'));
 await open(room);await start('reset');receipt.capture_reset=await saveStatus('capture-reset');assert.equal(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);receipt.reset=await observe();assert.deepEqual(receipt.reset.containers[0].items.map(i=>i.item_id).sort(),produced.items.map(i=>i.item_id).sort());
 await start('latest');receipt.capture_v2=await saveStatus('capture-v2');assert.notEqual(session.captured.manifest_sha256,receipt.capture_v1.captured.manifest_sha256);receipt.latest=await observe();assert.deepEqual(receipt.latest.containers[0].items.map(i=>i.item_id).sort(),['animal_bone','tallow_torch'].sort());await screenshot('native-revised-loot.png');await b('Stop').click();await until(async()=>(await status()).status==='stopped');receipt.ordinary_after=await ordinary('--after');
 for(const row of records.filter(r=>r.source!==poolPath('w5o_provisions')))assert.equal((await ipc('inspect_recovery',{key:row.key})).record.draft,recoveryBytes[row.source].draft);
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);if(page){receipt.status=await status().catch(()=>null);await page.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});}throw error;}
finally{await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));if(cold&&!exited(cold))cold.kill();if(page)void ipc('finish_close').catch(()=>{});if(child&&!exited(child))await until(async()=>exited(child),10000).catch(()=>child.kill());await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
