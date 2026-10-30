// W5Q: actual packaged WebView; all data, settings and recovery positively owned.
import assert from 'node:assert/strict';
import {spawn,spawnSync,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const output=resolve('.artifacts/w5q',`native-${Date.now()}`),root=resolve(output,'project'),settings=resolve(output,'settings'),storage=resolve(output,'recovery');
await mkdir(settings,{recursive:true});
assert.equal(spawnSync(resolve('worker/runtime/python.exe'),['-X','utf8','-B','-c',"import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{windowsHide:true,stdio:'inherit'}).status,0);
await writeFile(resolve(settings,'project.json'),JSON.stringify({version:1,project_root:root}));
const first='roguelike/data/buildings/residential/w5p_lodge.json',selection='roguelike/data/generation/settlement_profiles.json',unrelated='roguelike/data/items/components/clay_pot.json';
await writeFile(resolve(root,first),await readFile(resolve('docs/evidence/w5p/fixtures/building_v2.json')));
const initialPolicy=await readFile(resolve(root,selection),'utf8');
const pool='roguelike/data/loot_pools/workshop_b_fuel.json',text='roguelike/data/texts/world_graffiti_a.json';
const hash=b=>createHash('sha256').update(b).digest('hex'),executable=resolve('src-tauri/target/release/resonance-workbench.exe');
const receipt={started_utc:new Date().toISOString(),root,output,processes:[],package_sha256:hash(await readFile(executable)),runner_sha256:hash(await readFile(new URL(import.meta.url))),checks:[],errors:[],fixtures:{},recovery:{}};
let child,browser,page;
const b=name=>page.getByRole('button',{name,exact:true}).filter({visible:true}),editor=()=>page.locator('[data-testid="authoring"]:visible'),eb=name=>editor().getByRole('button',{name,exact:true});
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'),null,{timeout:60000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==='true'));
const fill=async(label,value)=>{await page.getByLabel(label,{exact:true}).filter({visible:true}).fill(String(value));await editIdle();};
const choose=async(label,value)=>{await page.getByLabel(label,{exact:true}).filter({visible:true}).selectOption(String(value));await editIdle();};
const check=async(label,value=true)=>{await page.getByLabel(label,{exact:true}).filter({visible:true}).setChecked(value);await editIdle();};
async function phase(label){receipt.checks.push(label);console.log(label);await writeFile(resolve(output,'progress.json'),JSON.stringify(receipt,null,2));}
async function launch(){
 const n=receipt.processes.length;child=spawn(executable,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,`webview-${n}`),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9350 --remote-debugging-address=127.0.0.1'}});receipt.processes.push(child.pid);
 for(let i=0;;i++){assert.equal(child.exitCode,null);try{if((await(await fetch('http://127.0.0.1:9350/json/list')).json()).length)break;}catch{}assert(i<160);await new Promise(r=>setTimeout(r,250));}
 browser=await chromium.connectOverCDP('http://127.0.0.1:9350');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(30000);page.on('pageerror',e=>receipt.errors.push(e.stack||e.message));await page.setViewportSize({width:1700,height:1100});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();
}
async function stop(abrupt=false){if(!child)return;if(child.exitCode===null){const ended=new Promise(r=>child.once('exit',r));if(abrupt)execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});else await ipc('finish_close').catch(()=>{});await ended;}await browser?.close().catch(()=>{});child=null;}
async function open(path){await idle();await choose('Category / route','');await fill('Search ID, name or path',path);await page.locator(`[data-asset="${path}"]`).click();await page.waitForFunction(path=>[...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.offsetParent&&e.querySelector('.filepath')?.textContent===path),path);await idle();}
async function source(){await eb('Source').click();return editor().locator('textarea.source-editor');}
async function captured(path){await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();const row=(await ipc('list_recovery')).records.find(r=>r.source===path);assert(row);const record=(await ipc('inspect_recovery',{key:row.key})).record;assert(record);return {row,record};}
async function recover(row){
 for(let attempt=0;attempt<5;attempt++){
  await idle();await b('Recover drafts').click();await idle();await page.locator(`[data-recovery-key="${row.key}"]`).click();await idle();await b('Recover selected draft').click();await idle();
  const dialog=page.getByRole('dialog',{name:'Recover drafts',exact:true});if(!await dialog.count())return;
  assert.match(await page.locator('footer').innerText(),/BUSY/);await b('Keep for later').click();
 }throw Error('Recovery stayed busy');
}
async function validate(){await editIdle();for(let i=0;i<5;i++){await idle();await eb('Validate draft').click();await idle();const result=editor().getByTestId('draft-receipt');if(await result.count())return JSON.parse(await result.textContent());assert.match(await page.locator('footer').innerText(),/BUSY/);}throw Error('Validation remained busy');}
async function apply(){for(let attempt=0;attempt<5;attempt++){await eb('Review & apply').click();await b('Confirm apply one file').click();await idle();const status=await page.locator('footer').innerText();if(status.includes('Saved and byte-checked reopen:'))return;assert.match(status,/BUSY/);const result=await validate();assert(result.valid&&result.review_token);}throw Error('Apply stayed busy');}
async function fixture(name,path){const r=await ipc('open_document',{asset:path});assert(r.result,JSON.stringify(r));const raw=await readFile(resolve(root,path),'utf8');assert.equal(r.result.raw,raw);assert.equal(r.result.sha256,hash(raw));receipt.fixtures[name]={path,raw,sha256:hash(raw),definition:JSON.parse(raw)};return r.result;}
async function beginEdit(){
 for(let i=0;i<5;i++){await idle();if(await eb('Discard / Revert').count())return;await eb('Begin edit').click();try{await eb('Discard / Revert').waitFor({timeout:1500});return;}catch{receipt.checks.push('Begin-edit event retried after concurrent workspace refresh');}}
 throw Error('Begin edit did not install editing state');
}
async function controls(){await eb('Properties').click();}
async function sample(seed){await fill('Selection preview seed',seed);await b('Preview saved selection').click();await idle();
 const all=page.getByTestId('selection-preview-receipt');await all.last().waitFor({state:'attached'});return JSON.parse(await all.last().textContent());}
async function inspect(frame,row){await b(`Inspect placement ${row.id}`).click();await idle();const result=JSON.parse(await page.getByTestId('selection-preview-receipt').last().textContent());assert.equal(result.plan_identity,frame.plan_identity);assert.equal(result.input_identity,frame.input_identity);assert.equal(result.scene.placement.id,row.id);return result;}
try{
 await launch();await phase('Three independent exact drafts; fixed no-root-ID selection, building and unrelated item');
 await open(first);await beginEdit();await eb('Properties').click();await fill('Description','W5Q recoverable building draft with useful supplies and readable.');receipt.recovery[first]=await captured(first);
 await open(selection);assert.equal(JSON.parse(await(await source()).inputValue()).id,undefined);await beginEdit();await(await source()).fill('{\r\n "selection exact λ\\n": [');await editIdle();receipt.recovery[selection]=await captured(selection);
 await open(unrelated);await beginEdit();await(await source()).fill('{"unrelated":"retained λ",');await editIdle();receipt.recovery[unrelated]=await captured(unrelated);
 assert.equal(new Set(Object.values(receipt.recovery).map(r=>r.row.source)).size,3);
 await stop(true);await launch();for(const [path,saved] of Object.entries(receipt.recovery)){await recover(saved.row);assert.equal(await(await source()).inputValue(),saved.record.draft.replace(/\r\n/g,'\n'));assert(await eb('Review & apply').isDisabled());}
 await page.screenshot({path:resolve(output,'recovered-drafts.png')});
 await page.locator(`[data-document-tab="${selection}"]`).click();await(await source()).fill(initialPolicy);await editIdle();await eb('Undo document').click();assert.equal(await(await source()).inputValue(),receipt.recovery[selection].record.draft.replace(/\r\n/g,'\n'));await eb('Redo document').click();assert.equal(await(await source()).inputValue(),initialPolicy.replace(/\r\n/g,'\n'));
 // Recovery is exact text, never authority: checkpoint a protected edit and recover it.
 const protectedPolicy=JSON.parse(initialPolicy);protectedPolicy.profiles.grid.roles.civic[0].weight=999;await(await source()).fill(JSON.stringify(protectedPolicy));await editIdle();const protectedRecovery=await captured(selection);await stop(true);await launch();await recover(protectedRecovery.row);assert.equal(await(await source()).inputValue(),protectedRecovery.record.draft);
 const forbidden=await ipc('validate_document',{token:await editor().getAttribute('data-document-token'),draft:protectedRecovery.record.draft,variantId:null,seed:20261029});assert.equal(forbidden.error.code,'PROTECTED_POLICY');receipt.protected_recovery_rejected={code:forbidden.error.code,draft_sha256:hash(protectedRecovery.record.draft)};
 await(await source()).fill(initialPolicy);await editIdle();
 await recover(receipt.recovery[first].row);await controls();let validated=await validate();assert(validated.valid);await apply();await fixture('building',first);
 await phase('Saved building link focuses the single selection owner; explicit add, invalid weight rejection, Source/control history and exact return');
 await b('Settlement membership').click();await idle();assert.equal(await editor().locator('.filepath').textContent(),selection);await controls();await choose('Selection profile','grid');await choose('Selection role','residential');await b('Add this saved building').click();await editIdle();
 let current=JSON.parse((await captured(selection)).record.draft),index=current.profiles.grid.roles.residential.length-1;assert.equal(current.profiles.grid.roles.residential[index].asset,'w5p_lodge');
 await fill(`Membership ${index} weight`,0);validated=await validate();assert(!validated.valid&&validated.diagnostics.some(d=>d.field.endsWith('.weight')));receipt.invalid_weight=validated.diagnostics;
 await controls();await fill(`Membership ${index} weight`,5);await fill(`Membership ${index} cap`,3);const controlled=(await captured(selection)).record.draft;
 await(await source()).fill(controlled+'\n');await editIdle();await eb('Undo document').click();assert.equal(await(await source()).inputValue(),controlled.replace(/\r\n/g,'\n'));await eb('Redo document').click();assert.equal(await(await source()).inputValue(),controlled.replace(/\r\n/g,'\n')+'\n');
 await controls();await b(`Open building row ${index+1}`).click();await idle();await b('Return to selection settlement_profiles').click();await idle();assert.equal(await page.getByLabel('Selection profile').inputValue(),'grid');assert.equal(await page.getByLabel('Selection role').inputValue(),'residential');assert.equal(await page.locator(`[data-membership-row="${index}"][data-returned="true"]`).count(),1);
 await b(`Open building row ${index+1}`).click();await idle();await page.locator(`[data-document-tab="${selection}"]`).click();await fill(`Membership ${index} weight`,4);await page.locator(`[data-document-tab="${first}"]`).click();await b('Return to selection settlement_profiles').click();await page.getByText(/Recorded membership location is stale/).filter({visible:true}).waitFor();receipt.stale_membership_return=true;await fill(`Membership ${index} weight`,5);
 validated=await validate();assert(validated.valid);await apply();await fixture('policy_enrolled',selection);assert.equal(receipt.fixtures.policy_enrolled.sha256,validated.draft_sha256);
 await phase('Ordinary saved-policy generation with all competitors; inspect selected authored building and featured landmark');
 // A parked definition draft must never overlay saved generation inputs.
 await b(`Open building row ${index+1}`).click();await idle();await beginEdit();await eb('Properties').click();await fill('Description','W5Q parked building draft excluded from ordinary generation');const parked=await captured(first);receipt.parked_building={draft_sha256:hash(parked.record.draft),saved_sha256:receipt.fixtures.building.sha256};await b('Return to selection settlement_profiles').click();await idle();
 receipt.samples=[];let frame,selected;
 for(const seed of [20261029,20261030,20261031]){frame=await sample(seed);selected=frame.rows.find(r=>r.asset==='w5p_lodge');receipt.samples.push({seed,selected:frame.summary.find(r=>r.asset==='w5p_lodge')?.selected||0,plan_identity:frame.plan_identity,input_identity:frame.input_identity});if(selected)break;}
 assert(selected,'Explicit stopping rule: at most these three listed seeds; no selection found.');receipt.stopping_rule='Stop at first selection within explicit seeds 20261029, 20261030, 20261031; preserve every outcome and all saved competitors.';
 assert.equal(frame.profile_sha256,receipt.fixtures.policy_enrolled.sha256);assert.equal(frame.input_files[first],receipt.fixtures.building.sha256);assert(frame.selection_matches_saved_resolve);assert.equal(frame.width,128);assert.equal(frame.height,128);receipt.enrolled=await inspect(frame,selected);assert(receipt.enrolled.scene.records.some(r=>r.declared_text_id&&r.objects[0].text_id));assert(receipt.enrolled.scene.records.some(r=>r.kind==='container'&&r.objects[0].items.length));assert(receipt.enrolled.scene.access.every(r=>r.passed));
 await page.getByTestId('selection-constructed-scene').scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,'selected-building.png')});
 const landmark=frame.rows.find(r=>r.profile==='landmark');assert(landmark);receipt.landmark=await inspect(frame,landmark);assert(receipt.landmark.scene.records.every(r=>r.record_id.startsWith(landmark.id+':')&&r.receipt_owned));
 await phase('Deliberate membership removal and same-seed new plan; saved building unchanged and old result historical');
 await beginEdit();await choose('Selection profile','grid');await choose('Selection role','residential');await b(`Remove membership ${index+1}`).click();await editIdle();validated=await validate();assert(validated.valid);await apply();await fixture('policy_removed',selection);
 assert.equal(receipt.fixtures.policy_removed.definition.profiles.grid.roles.residential.some(r=>r.asset==='w5p_lodge'),false);assert.equal(hash(await readFile(resolve(root,first))),receipt.fixtures.building.sha256);await page.getByTestId('selection-preview-state').getByText(/Historical/).waitFor();receipt.historical_after_reopen=true;
 receipt.removed=await sample(frame.seed);assert(!receipt.removed.rows.some(r=>r.profile==='grid'&&r.asset==='w5p_lodge'));assert(!receipt.removed.summary.some(r=>r.profile==='grid'&&r.asset==='w5p_lodge'));assert.notEqual(receipt.removed.plan_identity,frame.plan_identity);assert.equal(receipt.removed.input_files[first],receipt.fixtures.building.sha256);await page.getByTestId('selection-preview-state').scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,'removed-same-seed.png')});
 const original=JSON.parse(initialPolicy);for(const profile of ['grid','roadside','landmark'])for(const [role,rows] of Object.entries(original.profiles[profile].roles))assert.deepEqual(receipt.fixtures.policy_removed.definition.profiles[profile].roles[role],rows);
 assert.equal((await ipc('inspect_recovery',{key:receipt.recovery[unrelated].row.key})).record.draft,receipt.recovery[unrelated].record.draft);assert.equal((await ipc('inspect_recovery',{key:parked.row.key})).record.draft,parked.record.draft);
 assert.deepEqual(receipt.errors,[]);receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);if(page){receipt.footer=await page.locator('footer').innerText().catch(()=>null);await page.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});}throw error;}
finally{await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));await stop();console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
