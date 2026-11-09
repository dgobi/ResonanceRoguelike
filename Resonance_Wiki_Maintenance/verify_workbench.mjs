// GUIDE-1: native Workbench UI in a bounded payload. App-local DOM only.
// Run from repository root: node Resonance_Wiki_Maintenance/verify_workbench.mjs
import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {mkdtemp,mkdir,readFile,writeFile,rm} from 'node:fs/promises';
import {resolve,dirname,join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createServer} from 'node:net';
import {createHash} from 'node:crypto';
const here=dirname(fileURLToPath(import.meta.url)),repo=resolve(here,'..');
const require=createRequire(resolve(repo,'workbench/package.json'));
const {chromium}=require('playwright-core');
const output=resolve(process.argv[2]||join(repo,'evidence/guide-1/workbench'));
await mkdir(output,{recursive:true});
const session=await mkdtemp(join(tmpdir(),'resonance-guide-ui-'));
const root=join(session,'payload'),settings=join(session,'settings'),recovery=join(session,'recovery');
const python=process.env.RESONANCE_PYTHON||resolve(repo,'workbench/worker/runtime/python.exe');
const staged=spawnSync(python,['-X','utf8','-B','-c',"import sys;from pathlib import Path;sys.path.insert(0,'Resonance_Wiki_Maintenance');from practice import stage;stage(Path(sys.argv[1]),'L02')",session],{cwd:repo,windowsHide:true,encoding:'utf8',timeout:60000});
await writeFile(join(output,'fixture.log'),staged.stdout+staged.stderr);assert.equal(staged.status,0,staged.stderr);
await mkdir(settings);await writeFile(join(settings,'project.json'),JSON.stringify({version:1,project_root:root}));
const exe=resolve(repo,'workbench/src-tauri/target/release/resonance-workbench.exe');
const hash=b=>createHash('sha256').update(b).digest('hex');
const receipt={kind:'actual packaged native Workbench, app-local DOM; isolated captured payload',source_revision:spawnSync('git',['rev-parse','HEAD'],{cwd:repo,encoding:'utf8',windowsHide:true}).stdout.trim(),executable:exe,package_sha256:hash(await readFile(exe)),root,save_root:join(session,'state'),checks:[],errors:[],requests:[]};
const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port;await new Promise(r=>server.close(r));
let child,browser,page;
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let i=0;i<180;i++){const r=await fn();if(r)return r;await delay(250);}throw Error('Bounded UI wait exceeded');}
const b=name=>page.getByRole('button',{name,exact:true});
const editor=()=>page.locator('[data-testid="authoring"]:visible');
const eb=name=>editor().getByRole('button',{name,exact:true});
const ib=name=>page.getByTestId('item-editor').filter({visible:true}).getByRole('button',{name,exact:true});
const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'),null,{timeout:45000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==='true'));
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const open=async path=>{await idle();await page.getByLabel('Category / route').selectOption('');await page.getByLabel('Search ID, name or path').fill(path);await page.locator(`[data-asset="${path}"]`).click();await idle();};
const source=async()=>{await eb('Source').click();return editor().locator('textarea.source-editor');};
async function validate(){await editIdle();for(let n=0;n<5;n++){await idle();await eb('Validate draft').click();await idle();if(await editor().getByTestId('draft-receipt').count())return JSON.parse(await editor().getByTestId('draft-receipt').textContent());assert.match(await page.locator('footer').innerText(),/BUSY/);}throw Error('Validation stayed busy');}
async function publish(){for(let n=0;n<4;n++){await eb('Review & apply').click();await b('Confirm apply one file').click();await idle();if((await page.locator('footer').innerText()).includes('Saved and byte-checked reopen:'))return;assert.match(await page.locator('footer').innerText(),/BUSY/);assert((await validate()).valid);}throw Error('Publish stayed busy');}
try{
 const env={...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:recovery,WEBVIEW2_USER_DATA_FOLDER:join(session,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${port} --remote-debugging-address=127.0.0.1`};delete env.RESONANCE_PYTHON;
 child=spawn(exe,[],{cwd:session,windowsHide:true,stdio:'ignore',env});receipt.pid=child.pid;
 await until(async()=>{assert.equal(child.exitCode,null);try{return (await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP(`http://127.0.0.1:${port}`);const context=browser.contexts()[0];page=context.pages()[0];page.setDefaultTimeout(30000);page.on('pageerror',e=>receipt.errors.push(String(e)));page.on('request',r=>{if(!r.url().startsWith('http://tauri.localhost')&&!r.url().startsWith('data:'))receipt.requests.push(r.url());});
 await page.setViewportSize({width:1600,height:1000});await page.getByTestId('startup-ready').waitFor();await idle();await context.setOffline(true);
 const originalPath='roguelike/data/items/consumables/cooked_meat.json',original=await readFile(join(root,originalPath));
 await open(originalPath);await eb('Begin edit').click();await eb('Save as new variant').click();await editor().getByLabel('New variant ID').fill('guide1_ui_ration');await editIdle();
 await ib('Properties').click();
 const candidate=JSON.parse(await(await source()).inputValue());candidate.name='Guide UI Ration';candidate.weight=0.15;candidate.nutrition=180;
 await(await source()).fill(JSON.stringify(candidate,null,2));await editIdle();await ib('Properties').click();
 assert.equal(await page.getByLabel('Item weight (kg)').inputValue(),'0.15');
 // Exercise a real bounded form control as well as equivalent source.
 await page.getByLabel('Item weight (kg)').fill('0.2');await editIdle();
 await ib('Use binding').click();assert.match(await page.getByTestId('item-editor').innerText(),/Handler found/);
 const checked=await validate();assert(checked.valid&&checked.review_token,JSON.stringify(checked));
 await ib('Factory result').click();await page.screenshot({path:join(output,'item-factory.png')});
 await publish();const target='roguelike/data/items/consumables/guide1_ui_ration.json',saved=await readFile(join(root,target));
 assert.equal(JSON.parse(saved).nutrition,180);assert.equal(JSON.parse(saved).weight,0.2);assert.deepEqual(await readFile(join(root,originalPath)),original);
 receipt.item={path:target,sha256:hash(saved),nutrition:180,weight:0.2,source_unchanged:true};
 await open(target);assert.equal((await(await source()).inputValue()).replaceAll('\r\n','\n'),saved.toString().replaceAll('\r\n','\n'));
 await ib('Properties').click();await page.screenshot({path:join(output,'item-published.png')});
 await open('roguelike/data/items/tools/tallow_torch.json');assert.equal(await eb('Begin edit').isDisabled(),false);receipt.checks.push('Current held light is admitted; obsolete read-only assertion not used');
 const roomPath='roguelike/data/layouts/guide1_workroom.json';await open(roomPath);await eb('Begin edit').click();
 const room=JSON.parse(await(await source()).inputValue());const item=room.special_tiles.find(r=>r.item_id==='guide1_ration');assert(item);item.item_id='guide1_ui_ration';
 await(await source()).fill(JSON.stringify(room,null,2));await editIdle();assert((await validate()).valid);await publish();
 assert(JSON.parse(await readFile(join(root,roomPath))).special_tiles.some(r=>r.item_id==='guide1_ui_ration'));
 await page.screenshot({path:join(output,'room-bound.png')});
 receipt.checks.push('Food variant through actual form/source/binding/factory/validate/review/publish/reopen controls','Unique saved item bound by a separately validated published room','No normal data or personal campaign path selected; all writes inside fresh payload');
 assert.equal(receipt.errors.length,0);receipt.passed=true;
}catch(error){receipt.passed=false;receipt.error=String(error.stack||error);if(page)await page.screenshot({path:join(output,'failure.png')}).catch(()=>{});process.exitCode=1;}
finally{
 if(child&&child.exitCode===null){await ipc('finish_close').catch(()=>{});await until(async()=>child.exitCode!==null).catch(()=>child.kill());}
 await browser?.close().catch(()=>{});
 receipt.fixture_retained=false;
 await writeFile(join(output,'receipt.json'),JSON.stringify(receipt,null,2));
 // Only the exact newly allocated temporary root is removed.
 assert.equal(dirname(session),resolve(tmpdir()));assert(session.includes('resonance-guide-ui-'));
 await rm(session,{recursive:true,force:true});
 console.log(JSON.stringify({passed:receipt.passed,output,error:receipt.error}));
}
