// Actual native owner launch/restart, using app-local WebView events only.
import {chromium} from 'playwright-core';
import {spawn, execFileSync} from 'node:child_process';
import {mkdir, readFile, writeFile, cp, readdir, stat} from 'node:fs/promises';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const workbench=fileURLToPath(new URL('..',import.meta.url)), root=resolve(workbench,'..');
const output=resolve(workbench,'.artifacts/w4b',`startup-${Date.now()}`);
const release=resolve(workbench,'src-tauri/target/release'), exe=resolve(release,'resonance-workbench.exe');
await mkdir(output,{recursive:true});
const ownerConfig=resolve(output,'owner settings'), fixture=resolve(output,'alternate data fixture');
const python=resolve(workbench,'worker/runtime/python.exe');
execFileSync(python,['-B','-c',"import sys;sys.path.insert(0,'worker');from test_authoring import data_fixture;data_fixture(sys.argv[1])",fixture],{cwd:workbench,windowsHide:true});
const receipt={started_utc:new Date().toISOString(),output,baseline:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8',windowsHide:true}).trim(),runs:[]};
const source='roguelike/data/entities/creatures/hollow_revenant.json';
const before=await readFile(resolve(root,source));
let port=9350;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ipc=(page,command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
async function run(name,options={},action=async()=>{}) {
  const config=options.realConfig ? resolve(process.env.APPDATA,'com.resonance.workbench') : options.config || resolve(output,`${name} settings`), folder=resolve(output,name);await mkdir(folder,{recursive:true});
  const temp=resolve(folder,'temporary');await mkdir(temp);
  const thisPort=port++, chosen=options.exe || exe;
  const env={...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:config,TEMP:temp,TMP:temp,
    WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${thisPort} --remote-debugging-address=127.0.0.1`,WEBVIEW2_USER_DATA_FOLDER:resolve(folder,'webview')};
  delete env.RESONANCE_PYTHON;if(options.override)env.RESONANCE_PYTHON=options.override;
  if(options.realConfig)delete env.RESONANCE_WORKBENCH_CONFIG_DIR;
  if(options.fault)env.WORKBENCH_FAULT=options.fault;
  const args=options.diagnostic?['--diagnostic-runtime']:[];
  const command=options.launcher || options.shortcut ? resolve(process.env.SystemRoot,'System32/wscript.exe') : chosen;
  let launchArgs=options.launcher ? [resolve(workbench,'Launch Workbench.vbs')] : args;
  if(options.shortcut) {
    const driver=resolve(folder,'open-shortcut.vbs');
    await writeFile(driver,`CreateObject("WScript.Shell").Run """${options.shortcut.replaceAll('"','""')}""", 1, False\r\n`);
    launchArgs=[driver];
  }
  const child=spawn(command,launchArgs,{cwd:folder,env,windowsHide:true,stdio:'ignore'});
  const entry={name,executable:chosen,entry_point:options.shortcut || (options.launcher?resolve(workbench,'Launch Workbench.vbs'):chosen),cwd:folder,config,override_present:!!options.override,console_errors:[],external_requests:[]};receipt.runs.push(entry);
  let browser,page;const start=performance.now();
  try {
    for(let i=0;;i++){try{if((await fetch(`http://127.0.0.1:${thisPort}/json/list`).then(r=>r.json())).length)break;}catch{}if(i>160)throw Error('CDP timeout');await sleep(250);}
    browser=await chromium.connectOverCDP(`http://127.0.0.1:${thisPort}`);const context=browser.contexts()[0];page=context.pages()[0];
    page.on('pageerror',e=>entry.console_errors.push(e.message));page.on('request',r=>{const u=new URL(r.url());if(['http:','https:'].includes(u.protocol)&&!['tauri.localhost','ipc.localhost','127.0.0.1','localhost'].includes(u.hostname))entry.external_requests.push(r.url());});
    await context.setOffline(true);await page.getByRole('heading',{name:'Resonance Workbench'}).waitFor();
    if(options.error) {
      await page.locator('footer').getByText(new RegExp(options.error)).waitFor({timeout:30000});
      assert.equal(await page.getByTestId('startup-ready').count(),0);assert.equal(await page.locator('.asset-list .asset').count(),0);
      assert.equal((await ipc(page,'worker_request',{request:{op:'describe'}})).error?.code,'WORKER_NOT_READY');
      assert((await ipc(page,'open_document',{asset:source})).error);
      entry.visible_error=await page.locator('footer').innerText();
      await assert.rejects(stat(resolve(config,'project.json')));
    } else if(options.cancel) {
      await page.getByRole('button',{name:'Cancel',exact:true}).waitFor();await sleep(300);
      await page.getByRole('button',{name:'Cancel',exact:true}).click();
      await page.waitForFunction(()=>!document.querySelector('.status-dot.working'));
      assert.equal(await page.getByTestId('startup-ready').count(),0);
      assert.equal((await ipc(page,'worker_request',{request:{op:'describe'}})).error?.code,'WORKER_NOT_READY');
      entry.cancelled=true;
    } else {
      await page.locator('[data-testid="map"][data-ready="true"]').waitFor({timeout:45000});
      await page.waitForFunction(()=>!document.querySelector('.status-dot.working'));
      assert.equal(await page.getByRole('dialog').count(),0);
      const expected=options.project || root;
      assert.equal(await page.getByTestId('active-project').innerText(),expected);
      assert(!(await page.locator('footer').innerText()).includes('WORKER_MISSING'));
      entry.ready_ms=Math.round(performance.now()-start);entry.visible_status=await page.getByTestId('startup-ready').innerText();
      const identify=await ipc(page,'worker_request',{request:{op:'identify'}});assert(identify.ok,JSON.stringify(identify));entry.identity=identify.result;
      assert.equal(identify.result.protocol,8);assert.equal(identify.result.runtime.imports_verified,true);
      assert.equal(identify.result.host_runtime.mode,options.mode || 'bundled');
      assert.equal(JSON.parse(await readFile(resolve(config,'project.json'),'utf8')).project_root,expected);
      await action(page,entry,config);
    }
    await page.screenshot({path:resolve(folder,'window.png')});
    assert.deepEqual(entry.console_errors,[]);assert.deepEqual(entry.external_requests,[]);
    entry.passed=true;
  } catch(error) {
    entry.passed=false;entry.error=String(error.stack || error);entry.visible_failure=await page?.locator('body').innerText().catch(()=>null);await page?.screenshot({path:resolve(folder,'failure.png')}).catch(()=>{});throw error;
  } finally {
    if(page)await ipc(page,'finish_close').catch(()=>{});
    await browser?.close().catch(()=>{});await sleep(300);
    if(!options.launcher && child.exitCode===null){await sleep(500);if(child.exitCode===null)child.kill();}
    entry.temporary_roots_remaining=(await readdir(temp)).filter(n=>n.startsWith('resonance-w0-'));
    assert.deepEqual(entry.temporary_roots_remaining,[]);
    entry.total_ms=Math.round(performance.now()-start);
    await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
  }
}

try {
  await run('fresh-owner-launch',{config:ownerConfig,launcher:true},async(page,entry)=>{
    // Source navigation and construction are performed through ordinary controls.
    await page.getByRole('button',{name:'Creatures',exact:true}).click();
    await page.getByLabel('Search ID, name or path').fill(source);await page.locator(`[data-asset="${source}"]`).click();
    await page.waitForFunction(()=>!document.querySelector('.status-dot.working'));
    await page.getByRole('button',{name:'Factory result',exact:true}).click();await page.getByRole('button',{name:'Validate and construct exact creature',exact:true}).click();
    // W5F inspection already contains a construction receipt. Wait for the new
    // requested validation, not merely that earlier receipt, before another IPC.
    await page.getByTestId('draft-receipt').waitFor({state:'attached',timeout:30000});
    await page.waitForFunction(()=>!document.querySelector('.status-dot.working'));
    await page.getByTestId('creature-factory-receipt').waitFor({state:'attached',timeout:30000});
    entry.factory=JSON.parse(await page.getByTestId('creature-factory-receipt').textContent());assert.equal(entry.factory.instance.fighter.hp,14);assert.equal(entry.factory.instance.fighter.max_hp,14);
    const preview=await ipc(page,'worker_request',{request:{op:'preview',asset:'roguelike/data/layouts/starting_lab.json',seed:20261023}});
    assert(preview.ok && preview.result.passed,JSON.stringify(preview));entry.preview={passed:preview.result.passed,origin:preview.result.origin,spawn:preview.result.spawn,source:preview.result.source};
  });
  await run('owner-restart',{config:ownerConfig,launcher:true},async(page,entry)=>{assert((await page.locator('.project-details').textContent()).includes('saved project'));entry.saved_project_restored=true;});
  await run('change-project',{config:ownerConfig},async(page,entry)=>{
    // Existing dirty-draft policy must prevent reassignment to a new project.
    const building='roguelike/data/buildings/commercial/workshop_b.json';
    await page.getByLabel('Search ID, name or path').fill(building);await page.locator(`[data-asset="${building}"]`).click();await page.waitForFunction(()=>!document.querySelector('.status-dot.working'));
    await page.getByRole('button',{name:'Begin edit',exact:true}).click();await page.getByLabel('Description',{exact:true}).fill('Unsaved startup isolation draft');
    await page.getByLabel('Repository directory').fill(fixture);await page.getByRole('button',{name:'Open directory',exact:true}).click();
    const dialog=page.getByRole('dialog');await dialog.waitFor();entry.discard_dialog=await dialog.innerText();
    await dialog.getByRole('button',{name:'Keep editing',exact:true}).click();assert.equal(await page.getByLabel('Description',{exact:true}).inputValue(),'Unsaved startup isolation draft');
    await page.getByRole('button',{name:'Discard / Revert',exact:true}).click();
    const opened=await ipc(page,'open_document',{asset:building});const oldToken=opened.result.document_token;
    await page.getByRole('button',{name:'Open directory',exact:true}).click();await page.waitForFunction(expected=>document.querySelector('[data-testid="active-project"]')?.textContent===expected,fixture,{timeout:30000});await page.waitForFunction(()=>!document.querySelector('.status-dot.working'));
    assert.equal((await ipc(page,'validate_document',{token:oldToken,draft:opened.result.raw,variantId:null})).error?.code,'UNKNOWN_DOCUMENT');entry.old_token_revoked=true;
  });
  await run('changed-project-restart',{config:ownerConfig,project:fixture});
  if (!process.env.WORKBENCH_STARTUP_SMOKE) {
  await writeFile(resolve(ownerConfig,'project.json'),JSON.stringify({version:1,project_root:resolve(output,'missing project')}));
  await run('stale-setting',{config:ownerConfig},async(page,entry)=>{assert((await page.locator('.project-details').textContent()).includes('is unavailable'));entry.safe_fallback=true;});
  await writeFile(resolve(ownerConfig,'project.json'),'{invalid');await run('corrupt-setting',{config:ownerConfig});
  await run('stale-override-normal',{override:resolve(output,'missing python.exe')},async(page)=>{assert((await page.locator('.project-details').textContent()).includes('ignored during ordinary bundled launch'));});
  await run('missing-external',{override:resolve(output,'missing python.exe'),diagnostic:true,error:'WORKER_MISSING'});
  await run('raw-dependency',{exe:resolve(release,'deps/resonance_workbench.exe'),error:'UNSUPPORTED_LAUNCH'});
  const portable=resolve(output,'Portable app with spaces');await mkdir(portable);await cp(exe,resolve(portable,'resonance-workbench.exe'));await cp(resolve(release,'bridge.py'),resolve(portable,'bridge.py'));await cp(resolve(release,'python'),resolve(portable,'python'),{recursive:true});
  await run('portable-spaces',{exe:'\\\\?\\'+resolve(portable,'resonance-workbench.exe')},async(page,entry)=>{entry.validated_checkout_discovery=(await page.locator('.project-details').textContent()).includes('application checkout');assert(entry.validated_checkout_discovery);});
  await run('development',{exe:resolve(workbench,'src-tauri/target/debug/resonance-workbench.exe'),mode:'development'});
  for(const [name,fault,error] of [['initialization-exit','worker-exit','WORKER_EXIT'],['protocol-mismatch','protocol-mismatch','PROTOCOL_MISMATCH'],['malformed-worker','malformed-worker','MALFORMED_WORKER_OUTPUT']]) {
    await run(name,{override:resolve(workbench,'.artifacts/fault-worker.exe'),diagnostic:true,fault,error});
  }
  await run('initialization-cancel',{override:resolve(workbench,'.artifacts/fault-worker.exe'),diagnostic:true,fault:'slow-worker',cancel:true});
  // Explicit opt-in only for this brief's already-authorized workstation setup.
  if(process.env.WORKBENCH_OWNER_SHORTCUT) {
    await run('corrected-owner-shortcut',{shortcut:process.env.WORKBENCH_OWNER_SHORTCUT,realConfig:true});
    await run('corrected-owner-shortcut-restart',{shortcut:process.env.WORKBENCH_OWNER_SHORTCUT,realConfig:true});
  }
  }
  assert.deepEqual(await readFile(resolve(root,source)),before);receipt.protected_creature_sha256=createHash('sha256').update(before).digest('hex');receipt.passed=true;
} catch(error) {receipt.passed=false;receipt.error=String(error.stack||error);process.exitCode=1;}
await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));
console.log(JSON.stringify({passed:receipt.passed,output,runs:receipt.runs.map(r=>({name:r.name,passed:r.passed,ms:r.total_ms,error:r.error})),error:receipt.error},null,2));
