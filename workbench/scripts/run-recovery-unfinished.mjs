// W5G bounded repair: actual packaged processes, real text/recipe policies,
// accepted unfinished drafts before variant selection. App-local CDP only.
import assert from "node:assert/strict";
import {spawn,spawnSync,execFileSync} from "node:child_process";
import {mkdir,readFile,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";
import {chromium} from "playwright-core";
const output=resolve(".artifacts/w5g",`repair-native-${Date.now()}`),root=resolve(output,"project"),settings=resolve(output,"settings"),storage=resolve(output,"recovery");
await mkdir(settings,{recursive:true});
assert.equal(spawnSync(resolve("worker/runtime/python.exe"),["-X","utf8","-B","-c","import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{windowsHide:true,stdio:"inherit"}).status,0);
await writeFile(resolve(settings,"project.json"),JSON.stringify({version:1,project_root:root}));
const executable=resolve("src-tauri/target/release/resonance-workbench.exe"),hash=b=>createHash("sha256").update(b).digest("hex");
const paths=["roguelike/data/texts/lab/lab_note_primary_b.json","roguelike/data/recipes/bile_coating.json"];
const receipt={processes:[],package_sha256:hash(await readFile(executable)),drafts:[],results:[],errors:[],output};
let child,browser,page;
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const b=name=>page.getByRole("button",{name,exact:true}),editor=()=>page.locator('[data-testid="authoring"]:visible'),eb=name=>editor().getByRole("button",{name,exact:true});
const idle=()=>page.waitForFunction(()=>!document.querySelector(".status-dot.working"),null,{timeout:60000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==="true"));
async function launch(){
 const n=receipt.processes.length;child=spawn(executable,[],{cwd:output,windowsHide:true,stdio:"ignore",env:{...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,`webview-${n}`),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:"--remote-debugging-port=9338 --remote-debugging-address=127.0.0.1"}});receipt.processes.push(child.pid);
 for(let i=0;;i++){assert.equal(child.exitCode,null);try{if((await (await fetch("http://127.0.0.1:9338/json/list")).json()).length)break;}catch{}assert(i<160);await new Promise(r=>setTimeout(r,250));}
 browser=await chromium.connectOverCDP("http://127.0.0.1:9338");page=browser.contexts()[0].pages()[0];page.on("pageerror",e=>receipt.errors.push(e.message));await page.setViewportSize({width:1600,height:1000});await page.getByTestId("startup-ready").waitFor({timeout:30000});await idle();
}
async function stop(){const ended=new Promise(r=>child.once("exit",r));execFileSync("taskkill",["/PID",String(child.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});await ended;await browser?.close().catch(()=>{});child=null;}
async function open(path){await idle();await page.getByLabel("Search ID, name or path").fill(path);await page.locator(`[data-asset="${path}"]`).click();await idle();}
async function captured(path){await editor().getByTestId("recovery-status").getByText(/Recovery checkpoint saved/).waitFor();const row=(await ipc("list_recovery")).records.find(r=>r.source===path);assert(row);const record=(await ipc("inspect_recovery",{key:row.key})).record;return {row,record};}
async function recover(row){await b("Recover drafts").click();await page.locator(`[data-recovery-key="${row.key}"]`).click();await b("Recover selected draft").click();await page.getByRole("dialog",{name:"Recover drafts",exact:true}).waitFor({state:"hidden"});await idle();}
async function validate(){await editIdle();await idle();await eb("Validate draft").click();await idle();return JSON.parse(await editor().getByTestId("draft-receipt").textContent());}
try{
 await launch();const records=[];
 for(const [i,path] of paths.entries()){
  await open(path);await eb("Begin edit").click();await eb("Source").click();const baseline=await readFile(resolve(root,path),"utf8");
  const draft=i===0?baseline+"\n":'\ufeff{\n "unfinished": ["λ",';await editor().locator("textarea.source-editor").fill(draft);await editIdle();
  const saved=await captured(path);assert.equal(saved.record.variant,false);assert.equal(saved.record.variant_id,"");assert.equal(saved.record.target,path);records.push(saved);receipt.drafts.push({path,generation:saved.record.generation,sha256:hash(saved.record.draft),variant:false});
 }
 await stop();await launch();
 for(const [i,saved] of records.entries()){
  await recover(saved.row);await eb("Source").click();assert.equal(await editor().locator("textarea.source-editor").inputValue(),saved.record.draft.replace(/\r\n/g,"\n"));
  assert(await eb("Apply variant").isDisabled());let checked=await validate();assert(!checked.review_token);if(i)assert.equal(checked.valid,false);
  await eb("Source").click();const baseline=JSON.parse(await readFile(resolve(root,paths[i]),"utf8"));await editor().locator("textarea.source-editor").fill(JSON.stringify(baseline,null,2));await editIdle();
  await eb("Save as new variant").click();await editor().getByLabel("New variant ID",{exact:true}).fill(`w5g_repair_${i}`);await editIdle();checked=await validate();assert(checked.valid&&checked.review_token,JSON.stringify(checked));receipt.results.push({path:paths[i],valid:checked.valid,review:true,diagnostics:checked.diagnostics});
 }
 await page.screenshot({path:resolve(output,"restored-variant-review.png")});assert.deepEqual(receipt.errors,[]);receipt.passed=true;
}catch(error){receipt.failure=String(error.stack||error);throw error;}finally{await writeFile(resolve(output,"receipt.json"),JSON.stringify(receipt,null,2));if(child)await stop();console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
