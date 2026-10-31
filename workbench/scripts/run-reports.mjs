// G22 packaged WebView proof; disposable inputs, app-local DOM/IPC only.
import assert from 'node:assert/strict';
import {spawn,spawnSync,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile,unlink} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const output=resolve(process.env.G22_REPORTS_OUTPUT||`.artifacts/g22/reports-${Date.now()}`),root=resolve(output,'runtime-inputs');
await mkdir(output,{recursive:true});
const python=resolve('worker/runtime/python.exe'),exe=resolve('src-tauri/target/release/resonance-workbench.exe');
let r=spawnSync(python,['-X','utf8','-B','-c',"import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{windowsHide:true,encoding:'utf8'});
assert.equal(r.status,0,r.stdout+r.stderr);
const policy='roguelike/data/generation/settlement_profiles.json',building='roguelike/data/buildings/commercial/workshop_d.json',pool='roguelike/data/loot_pools/workshop_d_treatment.json';
const selected=new Map(await Promise.all([policy,building,pool].map(async p=>[p,await readFile(resolve(root,p),'utf8')])));
await unlink(resolve(root,building));await unlink(resolve(root,pool));
await writeFile(resolve(root,policy),selected.get(policy).replaceAll('workshop_d','workshop_c'));
await writeFile(resolve(output,'project.json'),JSON.stringify({version:1,project_root:root}));
const hash=b=>createHash('sha256').update(b).digest('hex');
const receipt={started_utc:new Date().toISOString(),package_sha256:hash(await readFile(exe)),runner_sha256:hash(await readFile(new URL(import.meta.url))),root,checks:[],saved:[],errors:[]};
const port=9352;
let child,browser,page;
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'),null,{timeout:60000});
const b=name=>page.getByRole('button',{name,exact:true}).filter({visible:true}),editor=()=>page.locator('[data-testid="authoring"]:visible'),eb=name=>editor().getByRole('button',{name,exact:true});
const field=name=>page.getByLabel(name,{exact:true}).filter({visible:true});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==='true'));
async function launch(){
 child=spawn(exe,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:output,RESONANCE_WORKBENCH_RECOVERY_DIR:resolve(output,'recovery'),WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${port} --remote-debugging-address=127.0.0.1`}});
 for(let i=0;;i++){assert.equal(child.exitCode,null);try{if((await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()).length)break;}catch{}assert(i<160);await new Promise(r=>setTimeout(r,250));}
 browser=await chromium.connectOverCDP(`http://127.0.0.1:${port}`);page=browser.contexts()[0].pages()[0];page.on('pageerror',e=>receipt.errors.push(e.message));await page.setViewportSize({width:1600,height:1000});await page.getByTestId('startup-ready').waitFor({timeout:30000});await idle();
}
async function stop(){if(child&&child.exitCode===null)execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});await browser?.close().catch(()=>{});child=null;}
async function open(asset){await idle();await field('Category / route').selectOption('');await field('Search ID, name or path').fill(asset);await page.locator(`[data-asset="${asset}"]`).click();await idle();}
async function source(){await eb('Source').click();return editor().locator('textarea.source-editor');}
async function validate(){await editIdle();for(let i=0;i<5;i++){await idle();await eb('Validate draft').click();await idle();if(await editor().getByTestId('draft-receipt').count())return JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert.match(await page.locator('footer').innerText(),/BUSY/);}throw Error('Validation remained busy');}
async function apply(variant=false){await eb(await eb('Apply variant').count()?'Apply variant':'Review & apply').click();await b('Confirm apply one file').click();await idle();await page.getByText(/Saved and byte-checked reopen:/).waitFor({timeout:30000});}
async function construct(sourceAsset,target,draft){
 await open(sourceAsset);await eb('Begin edit').click();
 const variant=sourceAsset!==target;
 if(variant){await eb('Save as new variant').click();await editor().getByLabel('New variant ID').fill(JSON.parse(draft).id);await editIdle();}
 await(await source()).fill(draft);await editIdle();const checked=await validate();assert(checked.valid,JSON.stringify(checked));await apply(variant);
 const saved=await readFile(resolve(root,target),'utf8');assert.deepEqual(JSON.parse(saved),JSON.parse(draft));assert.equal(hash(saved),checked.draft_sha256);receipt.saved.push({path:target,sha256:hash(saved)});
}
try{
 await launch();
 await open('roguelike/data/texts/lab/lab_note_primary_b.json');await b('Binding and metadata').click();
 assert.equal(await b('Attach location reports').count(),1);assert(!(await page.getByTestId('text-editor').filter({visible:true}).innerText()).includes('Repair location_reports'));
 receipt.checks.push('Absent attachment is a valid explicit state, without a false repair warning.');
 await construct('roguelike/data/loot_pools/apothecary_b_treatment.json',pool,selected.get(pool));
 await construct('roguelike/data/buildings/commercial/workshop_c.json',building,selected.get(building));
 await construct(policy,policy,selected.get(policy));
 receipt.checks.push('Selected single-dose pool, exact workshop D and two existing membership substitutions constructed, validated, reviewed, published and reopened through supported Source routes.');
 const asset='roguelike/data/texts/lab/lab_route_sheet_a.json',id='g22_report_variant',target=asset.replace('lab_route_sheet_a',id);
 await open(asset);await eb('Begin edit').click();await eb('Save as new variant').click();await editor().getByLabel('New variant ID').fill(id);await editIdle();
 const title='Road copy for the next traveller';await field('Reader title').fill(title);await editIdle();
 await b('Undo text').click();await editIdle();assert.equal(await field('Reader title').inputValue(),'Old Road Preparations');
 await b('Redo text').click();await editIdle();assert.equal(await field('Reader title').inputValue(),title);
 await b('Binding and metadata').click();await field('remove location_reports 2').click();await editIdle();await b('Add location_reports record').click();await editIdle();await field('Report role 2').fill('ward_store');await editIdle();
 const draft=await(await source()).inputValue();assert.deepEqual(JSON.parse(draft).location_reports,[{role:'workshop'},{role:'ward_store'}]);
 await editor().getByTestId('recovery-status').getByText(/Recovery checkpoint saved/).waitFor();
 const row=(await ipc('list_recovery')).records.find(r=>r.source===asset);assert(row);
 const recovery=(await ipc('inspect_recovery',{key:row.key})).record;assert.deepEqual(JSON.parse(recovery.draft).location_reports,JSON.parse(draft).location_reports);
 await stop();await launch();await b('Recover drafts').click();await idle();await page.locator(`[data-recovery-key="${row.key}"]`).click();await idle();await b('Recover selected draft').click();await idle();assert.equal(await(await source()).inputValue(),draft.replaceAll('\r\n','\n'));
 const doc=(await ipc('open_document',{asset})).result;assert(doc);
 const invalid=await ipc('validate_document',{token:doc.document_token,draft:JSON.stringify({...JSON.parse(draft),location_reports:[{role:'arbitrary_selector'}]}),variantId:id});assert(invalid.result&&!invalid.result.valid);assert(invalid.result.diagnostics.some(d=>d.code==='TEXT_REPORTS'));
 await b('Reader preview').click();await field('Preview page').selectOption('1');await b('Preview exact text').click();await idle();
 const frame=JSON.parse(await page.getByTestId('reader-preview-receipt').textContent());assert.equal(frame.page,1);assert(!frame.review_token);await page.screenshot({path:resolve(output,'unbound-preview.png')});
 let checked=await validate();assert(checked.valid&&checked.review_token,JSON.stringify(checked));
 const module=resolve(root,'roguelike/engine/location_reports.py'),bytes=await readFile(module);await writeFile(module,Buffer.concat([bytes,Buffer.from('\n')]));
 const stale=await ipc('apply_document',{token:doc.document_token,reviewToken:checked.review_token,confirmed:true});assert(['SOURCE_CHANGED','REVIEW_REQUIRED'].includes(stale.error?.code),JSON.stringify(stale));await writeFile(module,bytes);
 checked=await validate();assert(checked.valid&&checked.review_token);await apply(true);
 const saved=await readFile(resolve(root,target),'utf8');assert.equal(hash(saved),checked.draft_sha256);assert.equal(JSON.parse(saved).title,title);receipt.saved.push({path:target,sha256:hash(saved)});
 await b('Binding and metadata').click();await page.screenshot({path:resolve(output,'reports-reopened.png')});
 const run=spawnSync(python,['-X','utf8','-B',resolve('scripts/reports-runtime-probe.py'),root,target,resolve(output,'runtime.json')],{windowsHide:true,encoding:'utf8',timeout:120000});await writeFile(resolve(output,'runtime-output.txt'),run.stdout+run.stderr);assert.equal(run.status,0,run.stdout+run.stderr);receipt.runtime=JSON.parse(await readFile(resolve(output,'runtime.json'),'utf8'));
 receipt.checks.push('Unique text: typed report attachment, prose edit, Undo/Redo, Source, disk recovery after process restart, unsupported-role rejection, unbound production preview, stale-source rejection, reviewed variant publication, exact reopen and paid actual-game read.');
 assert.equal(receipt.errors.length,0);receipt.passed=true;
}catch(e){receipt.passed=false;receipt.failure=String(e.stack||e);if(page)await page.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw e;}
finally{await stop();receipt.finished_utc=new Date().toISOString();await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
