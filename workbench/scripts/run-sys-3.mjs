// SYS-3 commissioned exact-source authoring and actual packaged app-local play.
// are published. Settings, recovery, WebViews, snapshots and saves are disposable.
// All UI events are local to this owned app; no desktop automation.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,copyFile,rename,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const root=resolve('..'),output=resolve('.artifacts/sys-3',`native-${Date.now()}`),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
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
  const o=await observe();if(o.player[0]===x&&o.player[1]===y)return o;
  const q=[[...o.player,[]]],seen=new Set([o.player.join(',')]);let route;
  for(let j=0;j<q.length;j++){const [a,c,p]=q[j];if(a===x&&c===y){route=p;break;}for(const [dx,dy,k] of directions){const nx=a+dx,ny=c+dy,id=`${nx},${ny}`;if(seen.has(id)||!o.walkable[ny]?.[nx]||o.actors.some(a=>a.x===nx&&a.y===ny))continue;seen.add(id);q.push([nx,ny,[...p,k]]);}}
  assert(route?.length,`No route to ${x},${y}`);await key(route[0]);
 }throw Error('bounded walk exhausted');
}
async function selectInventory(id){let o=await observe();if(!o.inventory_open)o=await key('i');const n=o.inventory_rows.findIndex(r=>!r.header&&r.item_id===id);assert(n>=0,id);while(o.inventory_selected!==n)o=await key(o.inventory_selected<n?'down':'up');return o;}
async function menu(n){for(let i=0;i<n;i++)await key('down');return key('return');}

const itemPath=id=>`roguelike/data/items/consumables/${id}.json`, recipePath=id=>`roguelike/data/recipes/${id}.json`,room='roguelike/data/layouts/sys3_wash_room.json';
const specs=[['binding_wash','briar_binding_oil','Binding','binding'],['etching_wash','bile_coating','Dissolution','caustic']];
async function source(value){await eb('Source').click();await editor().locator('textarea.source-editor').fill(JSON.stringify(value,null,2));await editIdle();}
async function dose([id,seed,essence]){
 const path=itemPath(id),fresh=!(await exists(path));await open(fresh?itemPath(seed):path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);}
 await page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name:'Properties',exact:true}).click();await fill('Item name',id.replaceAll('_',' '));await fill('Item weight (kg)',.1);
 await fill('Item description','A water-steeped wash for a weapon. Its chosen material determines how many contacts it lasts.');
 await page.getByLabel('Group in inventory',{exact:true}).filter({visible:true}).setChecked(false);await editIdle();
 await select('Essence 1',essence);await fill('Strength 1',.4);await fill('Base contacts 1',6);
 const buttons=page.getByRole('button',{name:/^Remove keyword /}).filter({visible:true});while(await buttons.count()){await buttons.first().click();await editIdle();}
 await apply(path);const saved=hash(await readFile(resolve(root,path)));await begin();await apply(path);assert.equal(hash(await readFile(resolve(root,path))),saved);
 await fill('Base contacts 1',0);await eb('Validate draft').click();await idle();const invalid=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!invalid.valid);await b('Undo item').click();await editIdle();
 assert.equal(await page.getByLabel('Base contacts 1',{exact:true}).filter({visible:true}).inputValue(),'6');(receipt.invalidUndo??=[]).push({path,rejected:true,unchanged_sha256:saved});
 await page.screenshot({path:resolve(output,id+'-item.png')});
}
async function recipe([id,seed,essence,tag]){
 const path=recipePath(id),fresh=!(await exists(path));await open(fresh?recipePath('resonant_bone_tincture'):path);await begin();
 if(fresh){await eb('Save as new variant').click();await fill('New variant ID',id);
  const raw=JSON.parse((await opened(recipePath('resonant_bone_tincture'))).raw);delete raw.requires_single_item;
  raw.id=id;raw.result_item=id;raw.name=id.replaceAll('_',' ');raw.description='Steep one suitable material with dried fixative. Richer material makes the wash last longer.';
  raw.components=[{tag,min_tier:1,quantity:1,role:'primary'},{tag:'fixative',min_tier:1,quantity:1}];
  raw.completion_message='{item_name} is ready. The empty vessel can be used again.';
  await source(raw);await eb('Properties').click();
 }
 await b('Requirements').click();await fill('Batch water (mL)',125);
 if(await b('Enable material response').count())await b('Enable material response').click();
 await select('Primary tag',tag);await fill('Longer-life minimum tier',2);await fill('Lower-band contacts',6);await fill('Higher-band contacts',12);
 await select('components role 1','primary');await b('Preparation').click();await fill('Processing turns',15);
 await apply(path);await begin();await b('Requirements').click();await fill('Higher-band contacts',6);await eb('Validate draft').click();await idle();
 const invalid=JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert(!invalid.valid);await b('Undo recipe').click();await editIdle();
 await page.screenshot({path:resolve(output,id+'-recipe.png')});
}
async function makeRoom(){
 if(await exists(room)){await open(room);return;}
 await open(template);await begin();await eb('Save as new variant').click();await fill('New variant ID','sys3_wash_room');
 const geometry={id:'sys3_wash_room',width:17,height:11,layers:['#################','#...............#','#...............#','#...............#','#.......~.......#','#...............#','#...............#','#...............#','#.<.............#','#...............#','#################'],legend:{'#':'wall','.':'floor','<':'stairs_up','~':'shallow_water'},player_start:{x:3,y:6},special_tiles:[]};
 await source(geometry);await b('Authored layout').click();
 const ids=['small_steeping_cup','coldbell_cutting','briar_sap','sulphur_cap_fragment','crow_bile','dried_bitter_herb','dried_bitter_herb','dried_bitter_herb','dried_bitter_herb','crude_blade'];
 for(let i=0;i<ids.length;i++){await select('Placement kind','item');await select('Placement item',ids[i]);await b('Place item').click();await cell(i+2,2);}
 await select('Placement kind','decor');await select('Placement decor','campfire_lit');await b('Place decor').click();await cell(9,6);
 for(const [id,x,y] of [['hollow_revenant',13,7],['stone_lurker',13,4]]){await select('Placement kind','creature');await select('Placement creature',id);await b('Place creature').click();await cell(x,y);}
 await apply(room);
}
async function fixture(){const id=++eventId;await writeFile(resolve(session.state_root,'event.json'),JSON.stringify({id,fixture:'coating-contact-targets'}));await until(async()=>{const o=await observe();return o.applied===id&&o.fixture_applied;});}
async function pickup(){let o=await key(',');if(o.interaction.selection)throw Error('unexpected pickup selection');return o;}
async function close(){let o=await observe();if(o.inventory_open)await key('escape');}
async function acquire(){await fixture();let o=await observe();for(const tile of o.floor){await walk(tile.x,tile.y);await key(',');}return observe();}
async function useDose(id,hits){let o=await observe();if(!o.inventory_open)o=await key('i');const candidates=o.inventory.filter(i=>i.item_id===id&&(!hits||i.coating_dose?.hits===hits));assert(candidates.length,id+' '+hits);const instance=candidates[0].instance;const n=o.inventory_rows.findIndex(r=>r.instance===instance);assert(n>=0,JSON.stringify(o.inventory_rows));while(o.inventory_selected!==n)o=await key(o.inventory_selected<n?'down':'up');const turn=o.turn;o=await key('e');await close();assert.equal(o.turn,turn+1);return observe();}
async function prepare(id,primary,hits){
 await close();let o=await observe();const water=[];for(let y=0;y<o.terrain.length;y++)for(let x=0;x<o.terrain[y].length;x++)if(o.terrain[y][x]==='shallow_water')water.push([x,y]);assert.equal(water.length,1);
 await walk(water[0][0],water[0][1]+1);await selectInventory('small_steeping_cup');await key('e');await menu(0);await menu(0);o=await observe();const measure=o.vessel_menu.options.findIndex(s=>s.includes('125 mL'));assert(measure>=0);await menu(measure);await close();
 o=await key('c');const n=o.craft.rows.findIndex(r=>r.id===id);assert(n>=0);while(o.craft.selected!==n)o=await key(o.craft.selected<n?'down':'up');o=await key('return');
 while(o.craft.choosing){const p=o.craft.prompts[o.craft.choice_index];const wanted=p.comp_index==='vessel'?'small_steeping_cup':p.comp_index===0?primary:'dried_bitter_herb';const n=p.options.findIndex(i=>i.item_id===wanted);assert(n>=0,JSON.stringify(p));while(o.craft.choice_selected!==n)o=await key(o.craft.choice_selected<n?'down':'up');o=await key('return');}
 assert.equal(o.mode,'PLACEMENT_CURSOR',JSON.stringify(o.logs));
 // Place at current reachable feet using ordinary cursor keys.
 while(o.placement.cursor[0]!==o.player[0])o=await key(o.placement.cursor[0]<o.player[0]?'right':'left');while(o.placement.cursor[1]!==o.player[1])o=await key(o.placement.cursor[1]<o.player[1]?'down':'up');
 const turn=o.turn;o=await key('return');assert.equal(o.turn,turn+1);assert.equal(o.processing.length,1);assert.equal(o.processing[0].turns_remaining,14);assert.equal(o.processing[0].vessel_job.output.coating_dose.hits,hits);
 const captured=o.processing[0].vessel_job;for(let i=0;i<14;i++)o=await key('.');assert.equal(o.processing.length,0);
 const here=o.floor.find(r=>r.x===o.player[0]&&r.y===o.player[1]);assert.equal(here.items.find(i=>i.item_id===id).coating_dose.hits,hits);
 // A two-item floor prompt: take vessel, then resolved dose through normal pickup.
 for(let k=0;k<2;k++){o=await key(',');if(o.interaction?.selection){o=await key('return');}}
 o=await observe();assert(o.inventory.some(i=>i.item_id===id&&i.coating_dose.hits===hits));return {captured,final:o};
}
async function witness({edited=false,all=true}={}){
 await acquire();await selectInventory('crude_blade');await key('e');await close();
 const batches=[];batches.push(await prepare('binding_wash','coldbell_cutting',edited?7:6));batches.push(await prepare('binding_wash','briar_sap',12));
 if(all){batches.push(await prepare('etching_wash','sulphur_cap_fragment',6));batches.push(await prepare('etching_wash','crow_bile',12));}
 let o=await observe();const distinct=o.inventory.filter(i=>i.item_id==='binding_wash').map(i=>i.coating_dose.hits).sort((a,b)=>a-b);assert.deepEqual(distinct,[edited?7:6,12]);
 await key('f5');o=await key('f9');assert.deepEqual(o.inventory.filter(i=>i.item_id==='binding_wash').map(i=>i.coating_dose.hits).sort((a,b)=>a-b),distinct);
 // F9 restores real actors, so re-apply the explicitly controlled target fixture.
 const id=++eventId;await writeFile(resolve(session.state_root,'event.json'),JSON.stringify({id,fixture:'coating-contact-targets-reset'}));
 // Existing one-shot fixture remains captured for this process; reload restored
 // native policies. The dedicated diagnostic reset below is fixture-only.
 await until(async()=>(await observe()).applied===id);
 await useDose('binding_wash',edited?7:6);o=await observe();let weapon=o.inventory.find(i=>i.item_id==='crude_blade');assert.equal(weapon.temporary_essence.find(r=>r.essence==='Binding').strength,edited?.5:.4);
 const target=o.actors.find(a=>a.id==='hollow_revenant');await walk(target.x-1,target.y);let attacks=0;
 for(let n=0;n<80;n++){o=await observe();weapon=o.inventory.find(i=>i.item_id==='crude_blade');if(!weapon.temporary_essence.some(r=>r.essence==='Binding'))break;await key('right');attacks++;}
 o=await observe();assert(!o.inventory.find(i=>i.item_id==='crude_blade').temporary_essence.some(r=>r.essence==='Binding'));assert(o.attacks.some(a=>a.result.essence_applied==='Binding'));
 if(all){await useDose('etching_wash',6);o=await observe();const t=o.actors.find(a=>a.id==='stone_lurker');await walk(t.x-1,t.y);for(let n=0;n<80;n++){o=await observe();if(!o.inventory.find(i=>i.item_id==='crude_blade').temporary_essence.some(r=>r.essence==='Dissolution'))break;await key('right');}o=await observe();assert(!o.inventory.find(i=>i.item_id==='crude_blade').temporary_essence.some(r=>r.essence==='Dissolution'));assert(o.attacks.some(a=>a.result.essence_applied==='Dissolution'));}
 await key(undefined,true);await copyFile(resolve(session.state_root,'frame.png'),resolve(output,`combat-${edited?'edited':'base'}-${Date.now()}.png`));return {fixture:'Targets inert, extended HP; real resolver/contact paths. Not an ordinary survival outing.',batches,attacks,final:await observe(),captured:(await status()).captured};
}
async function stop(){await b('Stop').click();await until(async()=>(await status()).status==='stopped');}
try{
 const env={...process.env,SDL_VIDEODRIVER:'dummy',SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9593 --remote-debugging-address=127.0.0.1'};
 spawn('cscript.exe',['//nologo',resolve('Launch Workbench.vbs')],{cwd:output,windowsHide:true,stdio:'ignore',env});
 await until(async()=>{try{return (await (await fetch('http://127.0.0.1:9593/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9593');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(25000);
 const pid=Number(execFileSync('powershell.exe',['-NoProfile','-Command',"(Get-CimInstance Win32_Process -Filter \"name='resonance-workbench.exe'\" | Where-Object { $_.CommandLine -notlike '*--test*' } | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId"],{encoding:'utf8',windowsHide:true}).trim());
 child={pid};page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1200});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();

 if(process.env.SYS3_RUNTIME_ONLY!=='1'){
  await phase('Packaged publication of both wash items and recipes');for(const spec of specs)await dose(spec);for(const spec of specs)await recipe(spec);await makeRoom();
  await open(room);await start('latest');const captured=(await status()).captured.manifest_sha256;receipt.original=await witness();
  await open(itemPath('binding_wash'));await begin();await page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name:'Properties',exact:true}).click();await fill('Strength 1',.5);await apply(itemPath('binding_wash'));
  await open(recipePath('binding_wash'));await begin();await b('Requirements').click();await fill('Lower-band contacts',7);await apply(recipePath('binding_wash'));
  await open(room);await start('reset');assert.equal((await status()).captured.manifest_sha256,captured);receipt.reset=await witness({all:false});
  await start('latest');receipt.edited=await witness({edited:true,all:false});await stop();
  await open(recipePath('binding_wash'));await begin();await b('Requirements').click();await fill('Lower-band contacts',8);
  await open(room);await start('latest');receipt.dirtyExcluded=await witness({edited:true,all:false});await stop();
  await open(recipePath('binding_wash'));await begin();await b('Requirements').click();await b('Undo recipe').click();await editIdle();await fill('Lower-band contacts',6);await apply(recipePath('binding_wash'));
  await open(itemPath('binding_wash'));await begin();await page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name:'Properties',exact:true}).click();await fill('Strength 1',.4);await apply(itemPath('binding_wash'));
 }else{await open(room);await start('latest');receipt.finalRuntime=await witness();await stop();}
 for(const [p,sha] of Object.entries(baseline))assert.equal(hash(await readFile(resolve(root,p))),sha,p);
 receipt.unchanged_sources=baseline;
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;await phase('SYS-3 native flow passed');
}catch(error){receipt.failure=String(error.stack||error);receipt.failureText=await page?.locator('body').innerText().catch(()=>null);receipt.status=page?await status().catch(()=>null):null;await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
 if(child){try{await ipc('room_test_action',{action:'stop'});}catch{}execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
 await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
