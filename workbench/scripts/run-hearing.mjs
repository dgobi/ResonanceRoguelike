// Packaged WebView2; app-local DOM/IPC, hidden launch, disposable runtime inputs.
import assert from 'node:assert/strict';
import {spawn,spawnSync,execFileSync} from 'node:child_process';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const output=resolve(process.env.G20_HEARING_OUTPUT||`.artifacts/g20/hearing-${Date.now()}`),root=resolve(output,'runtime-inputs');
await mkdir(output,{recursive:true});
const python=resolve('worker/runtime/python.exe');
let r=spawnSync(python,['-X','utf8','-B','-c',"import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{windowsHide:true,encoding:'utf8'});
assert.equal(r.status,0,r.stdout+r.stderr);
const asset='roguelike/data/entities/creatures/hollow_revenant.json',exe=resolve('src-tauri/target/release/resonance-workbench.exe');
const hash=b=>createHash('sha256').update(b).digest('hex');
const original=await readFile(resolve(root,asset));
await writeFile(resolve(output,'project.json'),JSON.stringify({version:1,project_root:root}));
const receipt={started_utc:new Date().toISOString(),package_sha256:hash(await readFile(exe)),root,checks:[],saved:[],errors:[]};
const port=9348;
let child,browser,page;
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'),null,{timeout:60000});
const b=name=>page.getByRole('button',{name,exact:true}),editor=()=>page.locator('[data-testid="authoring"]:visible'),eb=name=>editor().getByRole('button',{name,exact:true});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==='true'));
async function open(){await idle();await page.getByLabel('Category / route').selectOption('');await page.getByLabel('Search ID, name or path').fill(asset);await page.locator(`[data-asset="${asset}"]`).click();await idle();}
async function validate(){await editIdle();for(let i=0;i<5;i++){await idle();await eb('Validate draft').click();await idle();if(await editor().getByTestId('draft-receipt').count())return JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert.match(await page.locator('footer').innerText(),/BUSY/);}throw Error('Validation remained busy');}
async function save(hearing){
  if(await eb('Begin edit').count())await eb('Begin edit').click();
  await page.getByLabel('Hearing radius',{exact:true}).filter({visible:true}).fill(String(hearing));await editIdle();
  let checked=await validate();assert(checked.valid,JSON.stringify(checked));
  if(hearing===0){
    const doc=(await ipc('open_document',{asset})).result;assert(doc);
    const sound=resolve(root,'roguelike/engine/sound.py'),bytes=await readFile(sound),before=await readFile(resolve(root,asset));
    await writeFile(sound,Buffer.concat([bytes,Buffer.from('\n')]));
    const stale=await ipc('apply_document',{token:doc.document_token,reviewToken:checked.review_token,confirmed:true});
    assert(['SOURCE_CHANGED','REVIEW_REQUIRED'].includes(stale.error?.code),JSON.stringify(stale));assert.deepEqual(await readFile(resolve(root,asset)),before);
    await writeFile(sound,bytes);checked=await validate();assert(checked.valid,JSON.stringify(checked));receipt.stale_source_rejected=true;
  }
  await eb('Review & apply').click();await b('Confirm apply one file').click();await idle();
  await page.getByText(/Saved and byte-checked reopen:/).waitFor({timeout:30000});
  const doc=(await ipc('open_document',{asset})).result;assert(doc);assert.equal(JSON.parse(doc.raw).perception.hearing_radius,hearing);
  await writeFile(resolve(output,`hearing-${hearing}.json`),doc.raw);
  assert.equal(await page.getByLabel('Hearing radius',{exact:true}).filter({visible:true}).inputValue(),String(hearing));
  const run=spawnSync(python,['-X','utf8','-B',resolve('scripts/hearing-runtime-probe.py'),root,String(hearing)],{windowsHide:true,encoding:'utf8'});
  assert.equal(run.status,0,run.stdout+run.stderr);receipt.saved.push({hearing,sha256:doc.sha256,runtime:JSON.parse(run.stdout.trim().split('\n').at(-1))});
}
try{
  child=spawn(exe,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:output,RESONANCE_WORKBENCH_RECOVERY_DIR:resolve(output,'recovery'),WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${port} --remote-debugging-address=127.0.0.1`}});
  for(let i=0;;i++){assert.equal(child.exitCode,null);try{if((await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).length)break;}catch{}if(i>160)throw Error('CDP did not start');await new Promise(r=>setTimeout(r,250));}
  browser=await chromium.connectOverCDP(`http://127.0.0.1:${port}`);page=browser.contexts()[0].pages()[0];page.on('pageerror',e=>receipt.errors.push(e.message));await page.setViewportSize({width:1600,height:1000});
  await page.getByTestId('startup-ready').waitFor({timeout:30000});await open();await eb('Begin edit').click();
  await page.getByLabel('Hearing radius',{exact:true}).filter({visible:true}).fill('4');await editIdle();
  await b('Undo creature').click();await editIdle();assert.equal(await page.getByLabel('Hearing radius',{exact:true}).filter({visible:true}).inputValue(),'6');
  await b('Redo creature').click();await editIdle();assert.equal(await page.getByLabel('Hearing radius',{exact:true}).filter({visible:true}).inputValue(),'4');
  await eb('Source').click();assert((await editor().locator('textarea.source-editor').inputValue()).includes('"hearing_radius": 4'));
  await eb('Properties').click();
  await save(0);await save(4);
  const saved=JSON.parse(await readFile(resolve(root,asset),'utf8')),baseline=JSON.parse(original);saved.perception.hearing_radius=baseline.perception.hearing_radius;assert.deepEqual(saved,baseline);
  await page.getByLabel('Hearing radius',{exact:true}).filter({visible:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,'hearing-saved.png')});await page.setViewportSize({width:1100,height:740});await page.getByLabel('Hearing radius',{exact:true}).filter({visible:true}).scrollIntoViewIfNeeded();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));await page.screenshot({path:resolve(output,'hearing-minimum.png')});
  receipt.checks.push('Typed hearing edit, Source, Undo/Redo, reviewed publication and byte-checked reopen at zero and four','Actual factory/runtime threshold changes: four-cost flint unheard at zero, heard at four','Unrelated creature fields preserved; desktop input unused; minimum width has no horizontal overflow');assert.equal(receipt.errors.length,0);receipt.passed=true;
}catch(e){receipt.passed=false;receipt.failure=String(e.stack||e);if(page)await page.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw e;}
finally{if(child&&child.exitCode===null)execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});await browser?.close().catch(()=>{});await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
