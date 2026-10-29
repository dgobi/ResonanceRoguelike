// Read-only saved-input/output navigation on the final packaged Workbench.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdir,readFile,writeFile,readdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const sha=b=>createHash('sha256').update(b).digest('hex');
const candidates=await Promise.all((await readdir('.artifacts/w5k')).filter(n=>n.startsWith('native-')).map(async n=>{try{const path=resolve('.artifacts/w5k',n,'receipt.json'),r=JSON.parse(await readFile(path,'utf8'));return r.passed?{path,r}:null;}catch{return null;}}));
const parent=candidates.filter(Boolean).sort((a,b)=>b.r.started_utc.localeCompare(a.r.started_utc))[0];assert(parent);
const output=resolve('.artifacts/w5k',`references-${Date.now()}`),settings=resolve(output,'settings'),recovery=resolve(output,'recovery');await mkdir(settings,{recursive:true});
await writeFile(resolve(settings,'project.json'),JSON.stringify({version:1,project_root:parent.r.root}));
const exe=resolve('src-tauri/target/release/resonance-workbench.exe'),receipt={root:parent.r.root,source_receipt:parent.path,package_sha256:sha(await readFile(exe)),checks:[]};
assert.equal(receipt.package_sha256,parent.r.package_sha256);
let child,browser,page;
const until=async fn=>{for(let i=0;i<600;i++){const r=await fn();if(r)return r;await new Promise(r=>setTimeout(r,100));}throw Error('Timed out');};
try{
 child=spawn(exe,[],{cwd:output,windowsHide:true,stdio:'ignore',env:{...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:recovery,WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9561 --remote-debugging-address=127.0.0.1'}});
 await until(async()=>{try{return (await (await fetch('http://127.0.0.1:9561/json/list')).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP('http://127.0.0.1:9561');page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(30000);await page.setViewportSize({width:1600,height:1050});await page.getByTestId('startup-ready').waitFor();
 const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'));
 const b=name=>page.getByRole('button',{name,exact:true}).filter({visible:true});
 const current=path=>page.waitForFunction(path=>[...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.offsetParent&&e.querySelector('.filepath')?.textContent===path),path);
 await idle();const path='roguelike/data/recipes/w5k_dry.json';await page.getByLabel('Search ID, name or path').fill(path);await page.locator(`[data-asset="${path}"]`).click();await current(path);await idle();
 await b('Requirements').click();await b('w5k_leaf').click();await current('roguelike/data/items/consumables/w5k_leaf.json');await idle();
 await b('Return to recipe w5k_dry').click();await current(path);await idle();receipt.checks.push('Saved conjunction automatic material w5k_leaf opens its exact saved source and returns to w5k_dry');
 await b('Output').click();await b('Open output item w5k_dressing').click();await current('roguelike/data/items/consumables/w5k_dressing.json');await idle();await b('Return to recipe w5k_dry').click();await current(path);await idle();
 receipt.checks.push('Saved output w5k_dressing opens its exact saved source and returns to the same recipe');
 await b('Requirements').click();await page.getByRole('heading',{name:'All tags on each material',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,'saved-conjunction-references.png')});
 receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);await page?.screenshot({path:resolve(output,'failure.png')}).catch(()=>{});throw error;}
finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2));if(page)await page.evaluate(()=>window.__TAURI_INTERNALS__.invoke('finish_close')).catch(()=>{});await browser?.close().catch(()=>{});if(child&&child.exitCode===null&&child.signalCode===null)await until(()=>child.exitCode!==null||child.signalCode!==null).catch(()=>child.kill());console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));
}
