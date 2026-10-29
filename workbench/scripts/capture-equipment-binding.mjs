// Supplementary actual package frame of a validated, unpublished legacy variant.
// Accepted kit bytes and its original reviewed diff remain in the journey receipt.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
const receiptPath=resolve(process.argv[2]),n=JSON.parse(await readFile(receiptPath,'utf8'));assert(n.passed);
const output=resolve(dirname(receiptPath),'binding-inspection'),settings=resolve(output,'settings');await mkdir(settings,{recursive:true});
await writeFile(resolve(settings,'project.json'),JSON.stringify({version:1,project_root:n.root}));
const exe=resolve('src-tauri/target/release/resonance-workbench.exe'),hash=b=>createHash('sha256').update(b).digest('hex');assert.equal(hash(await readFile(exe)),n.package_sha256);
const port=9581,child=spawn(exe,[],{windowsHide:true,stdio:'ignore',env:{...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:resolve(output,'recovery'),WEBVIEW2_USER_DATA_FOLDER:resolve(output,'webview'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${port} --remote-debugging-address=127.0.0.1`}});
let browser,page;const result={package_sha256:n.package_sha256,scope:'Supplementary validated new-ID candidate from the same shipped legacy source; never published. The accepted kit original reviewed diff and exact fixture bytes are recorded separately in the journey receipt.'};
async function until(fn){const start=Date.now();for(;;){if(await fn())return;assert(Date.now()-start<90000);await new Promise(r=>setTimeout(r,100));}}
try{
 await until(async()=>{try{return (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).length;}catch{return false;}});
 browser=await chromium.connectOverCDP(`http://127.0.0.1:${port}`);page=browser.contexts()[0].pages()[0];await page.setViewportSize({width:1600,height:1050});await page.getByTestId('startup-ready').waitFor();
 const idle=()=>page.waitForFunction(()=>!document.querySelector('.status-dot.working'));
 const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==='true'));
 await idle();const source='roguelike/data/items/equipment/satchel/leather_satchel.json';await page.getByLabel('Search ID, name or path',{exact:true}).fill(source);await page.locator(`[data-asset="${source}"]`).click();await idle();
 const editor=page.locator('[data-testid="authoring"]:visible'),eb=name=>editor.getByRole('button',{name,exact:true});
 await eb('Begin edit').click();await eb('Save as new variant').click();await page.getByLabel('New variant ID',{exact:true}).fill('w5m_binding_evidence');await editIdle();
 await eb('Validate draft').click();await idle();const verdict=JSON.parse(await editor.getByTestId('draft-receipt').textContent());assert(verdict.valid&&verdict.review_token);
 await eb('Diff').click();const pre=editor.getByTestId('source-diff');const diff=await pre.innerText();assert(/\+.*"on_use":"equip_toggle"/.test(diff),diff);
 await pre.scrollIntoViewIfNeeded();await pre.evaluate(el=>{el.scrollTop=el.scrollHeight;for(let p=el.parentElement;p;p=p.parentElement)if(p.scrollHeight>p.clientHeight)p.scrollTop=p.scrollHeight;});
 await page.screenshot({path:resolve(output,'reviewed-handler-insertion.png')});result.diff=diff;result.draft_sha256=verdict.draft_sha256;result.review_authority_issued=true;result.passed=true;
 await eb('Discard / Revert').click();
}finally{
 await writeFile(resolve(output,'receipt.json'),JSON.stringify(result,null,2));
 if(page)await page.evaluate(()=>window.__TAURI_INTERNALS__.invoke('finish_close')).catch(()=>{});
 await until(async()=>child.exitCode!==null||child.signalCode!==null).catch(()=>child.kill());await browser?.close().catch(()=>{});
}
console.log(JSON.stringify({output,passed:result.passed}));
