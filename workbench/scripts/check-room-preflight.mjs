// Focused final packaged preflight/fallback checks against a disposable journey project.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdir,readFile,writeFile,rename,readdir,copyFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {chromium} from 'playwright-core';
const root=resolve(process.argv[2]);assert(root.includes(`${process.platform==='win32'?'\\':'/'}.artifacts${process.platform==='win32'?'\\':'/'}w5h`));
const output=resolve('.artifacts/w5h',`preflight-${Date.now()}`);await mkdir(output,{recursive:true});
await writeFile(resolve(output,'project.json'),JSON.stringify({version:1,project_root:root}));
const exe=resolve('src-tauri/target/release/resonance-workbench.exe'),port=9364;
const child=spawn(exe,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,SDL_AUDIODRIVER:'dummy',RESONANCE_WORKBENCH_ROOM_TEST_AUTOMATION:'1',RESONANCE_WORKBENCH_CONFIG_DIR:output,RESONANCE_WORKBENCH_RECOVERY_DIR:resolve(output,'recovery'),WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${port} --remote-debugging-address=127.0.0.1`}});
const receipt={output,root,host_pid:child.pid};let browser,page,pebble,starterBytes,ui;
async function until(fn,timeout=90000){const start=Date.now();for(;;){const r=await fn();if(r)return r;assert(Date.now()-start<timeout,'Timed out');await new Promise(r=>setTimeout(r,100));}}
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const status=()=>ipc('room_test_action',{action:'status'});
try{
 await until(async()=>{try{return (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP(`http://127.0.0.1:${port}`);page=browser.contexts()[0].pages()[0];await page.getByTestId('startup-ready').waitFor();await page.waitForFunction(()=>!document.querySelector('.status-dot.working'));
 let opened;await until(async()=>{opened=await ipc('open_document',{asset:'roguelike/data/layouts/w5h_native_room.json'});if(opened.error?.code==='BUSY')return false;assert(opened.result,JSON.stringify(opened));return true;});const token=opened.result.document_token;
 assert(!(await ipc('room_test_action',{action:'test',token})).error);const first=await until(async()=>{const s=await status();assert.notEqual(s.status,'failed',JSON.stringify(s));return s.status==='running'?s:null;});
 const itemRoot=resolve(root,'roguelike/data/items');const name=(await readdir(itemRoot,{recursive:true})).find(n=>n.endsWith('tallow_torch.json'));assert(name);pebble=resolve(itemRoot,name);starterBytes=await readFile(pebble);const inertTorch=JSON.parse(starterBytes);inertTorch.on_use='w5h_inert_light';await writeFile(pebble,JSON.stringify(inertTorch));
 const failed=await ipc('room_test_action',{action:'latest',token});assert(failed.error);assert.match(failed.error.message,/Ordinary starting torch could not be equipped/);const retained=await status();assert.equal(retained.status,'running');assert.equal(retained.pid,first.pid);assert.equal(retained.captured.snapshot_id,first.captured.snapshot_id);await writeFile(pebble,starterBytes);pebble=null;
 receipt.required_light={error:failed.error,preserved_pid:first.pid,snapshot_id:first.captured.snapshot_id};
 await ipc('room_test_action',{action:'stop'});
 ui=resolve(root,'roguelike/assets/ui');await rename(ui,ui+'.held');assert(!(await ipc('room_test_action',{action:'latest',token})).error);const fallback=await until(async()=>{const s=await status();assert.notEqual(s.status,'failed',JSON.stringify(s));return s.status==='running'?s:null;});
 assert(fallback.validation.diagnostics.some(d=>d.code==='UI_FALLBACK'&&d.severity==='warning'));await writeFile(resolve(fallback.state_root,'event.json'),JSON.stringify({id:1,capture:true}));await until(async()=>{try{return JSON.parse(await readFile(resolve(fallback.state_root,'observation.json'),'utf8')).applied===1;}catch{return false;}});await copyFile(resolve(fallback.state_root,'frame.png'),resolve(output,'actual-ui-fallback.png'));
 receipt.fallback={snapshot_id:fallback.captured.snapshot_id,pid:fallback.pid,diagnostics:fallback.validation.diagnostics};await rename(ui+'.held',ui);ui=null;await ipc('room_test_action',{action:'stop'});assert((await status()).reaped);receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);throw error;}
finally{
 if(pebble)await writeFile(pebble,starterBytes).catch(()=>{});if(ui)await rename(ui+'.held',ui).catch(()=>{});
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));if(page)void ipc('finish_close').catch(()=>{});await until(async()=>child.exitCode!==null||child.signalCode!==null,10000).catch(()=>child.kill());await browser?.close().catch(()=>{});console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
