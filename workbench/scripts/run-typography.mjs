// App-local WebView IPC/DOM only. All project, settings and recovery data are disposable.
import assert from "node:assert/strict";
import {spawn,spawnSync,execFileSync} from "node:child_process";
import {mkdir,readFile,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";
import {chromium} from "playwright-core";

const output=resolve(".artifacts/w5e",`native-${Date.now()}`),root=resolve(output,"project"),settings=resolve(output,"settings"),storage=resolve(output,"recovery");
await mkdir(settings,{recursive:true});
const python=resolve("worker/runtime/python.exe"),fixture=spawnSync(python,["-X","utf8","-B","-c","import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{windowsHide:true,stdio:"inherit"});assert.equal(fixture.status,0);
const profile="roguelike/data/display/typography.json",other="roguelike/data/texts/lab/lab_note_primary_b.json";
let baseline=(await readFile(resolve(root,profile),"utf8")).replace(/\r?\n/g,"\r\n").replace('  "version": 1,','  "metadata": {"exact":[1e2, null, "λ"]},\r\n  "version": 1,');
await writeFile(resolve(root,profile),baseline);
await writeFile(resolve(settings,"project.json"),JSON.stringify({version:1,project_root:root}));
const executable=resolve("src-tauri/target/release/resonance-workbench.exe"),hash=b=>createHash("sha256").update(b).digest("hex");
const receipt={started_utc:new Date().toISOString(),package_sha256:hash(await readFile(executable)),root,settings,storage,checks:[],processes:[],drafts:[],errors:[]};
let child,browser,page,launches=0;
const b=name=>page.getByRole("button",{name,exact:true}),editor=()=>page.locator('[data-testid="authoring"]:visible'),eb=name=>editor().getByRole("button",{name,exact:true});
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector(".status-dot.working"),null,{timeout:60000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==="true"));
const source=async()=>{await eb("Source").click();return editor().locator("textarea.source-editor").inputValue();};
const open=async path=>{await idle();await page.getByLabel("Search ID, name or path").fill(path);await page.locator(`[data-asset="${path}"]`).click();await idle();};
const list=async()=>{const r=await ipc("list_recovery");assert(!r.error,JSON.stringify(r));return r.records;};
const inspect=async key=>{const r=await ipc("inspect_recovery",{key});assert(!r.error,JSON.stringify(r));return r.record;};
const checkpoint=()=>editor().getByTestId("recovery-status").getByText(/Recovery checkpoint saved/).waitFor({timeout:15000});
async function launch(){
  launches++;const env={...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,`webview-${launches}`),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:"--remote-debugging-port=9336 --remote-debugging-address=127.0.0.1"};delete env.RESONANCE_PYTHON;
  child=spawn(executable,[],{cwd:output,env,windowsHide:true,stdio:"ignore"});receipt.processes.push(child.pid);
  for(let i=0;;i++){assert.equal(child.exitCode,null);try{const r=await fetch("http://127.0.0.1:9336/json/list");if((await r.json()).length)break;}catch{}if(i>160)throw Error("CDP did not start");await new Promise(r=>setTimeout(r,250));}
  browser=await chromium.connectOverCDP("http://127.0.0.1:9336");page=browser.contexts()[0].pages()[0];page.on("pageerror",e=>receipt.errors.push(e.message));await page.setViewportSize({width:1600,height:1000});
  await page.getByTestId("startup-ready").waitFor({timeout:30000});await idle();
}
async function stop(abrupt=false){
  if(!child)return;const ended=new Promise(r=>child.once("exit",r));
  if(abrupt)execFileSync("taskkill",["/PID",String(child.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});else await ipc("finish_close").catch(()=>{});
  await ended;await browser?.close().catch(()=>{});child=null;browser=null;
}
async function keepClose(){await b("Close project").click();await b("Keep for Recovery and Close").click();await page.getByRole("dialog",{name:"Unsaved draft"}).waitFor({state:"hidden"});await idle();}
async function recover(row){await b("Recover drafts").click();await page.locator(`[data-recovery-key="${row.key}"]`).click();await page.getByTestId("recovery-detail").waitFor();await b("Recover selected draft").click();await page.getByRole("dialog",{name:"Recover drafts"}).waitFor({state:"hidden"});await idle();}
async function validate(){for(let i=0;i<4;i++){await idle();await eb("Validate draft").click();await idle();if(await editor().getByTestId("draft-receipt").count())return JSON.parse(await editor().getByTestId("draft-receipt").textContent());assert.match(await page.locator("footer").innerText(),/BUSY/);}throw Error("Validation remained busy");}
function runtime(){const p=spawnSync(python,["-X","utf8","-B",resolve("scripts/typography-runtime-probe.py"),root],{windowsHide:true,encoding:"utf8",timeout:30000});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout.trim().split(/\r?\n/).at(-1));}
try{
  await launch();await open(profile);let doc=(await ipc("open_document",{asset:profile})).result;const oldToken=doc.document_token;
  await eb("Begin edit").click();assert.equal(await eb("Save as new variant").count(),0);
  await page.getByLabel("Headings",{exact:true}).selectOption("IMFellEnglish-Regular.ttf");await editIdle();
  await page.getByLabel("Ordinary prose",{exact:true}).selectOption("IMFellEnglish-Italic.ttf");await editIdle();
  await page.getByLabel("Damage callout",{exact:true}).selectOption("FoulisGreek.ttf");await editIdle();
  await eb("Undo typography").click();await editIdle();assert.equal(await page.getByLabel("Damage callout",{exact:true}).inputValue(),"Junicode-Bold.ttf");
  await eb("Redo typography").click();await editIdle();await checkpoint();
  let row=(await list()).find(r=>r.source===profile),record=await inspect(row.key),accepted=record.draft;
  assert(accepted.includes('"metadata": {"exact":[1e2, null, "λ"]}'));
  let reverted=accepted.replace('"font_ui_large": "IMFellEnglish-Regular.ttf"','"font_ui_large": "Junicode.ttf"').replace('"font_ui_normal": "IMFellEnglish-Italic.ttf"','"font_ui_normal": "Junicode.ttf"').replace('"font_callout_damage": "FoulisGreek.ttf"','"font_callout_damage": "Junicode-Bold.ttf"');assert.equal(reverted,baseline);
  await eb("Game preview").click();await eb("Preview game typography").click();await idle();
  await page.getByTestId("typography-preview-state").getByText("Current production typography preview").waitFor();
  receipt.preview=JSON.parse(await page.getByTestId("typography-preview-receipt").textContent());assert.equal(receipt.preview.draft_sha256,hash(accepted));
  await page.screenshot({path:resolve(output,"candidate-preview.png")});
  const forged=await ipc("edit_document",{token:oldToken,sequence:999,draft:accepted,variant:true,variantId:"alternate"});assert(forged.error);assert.equal((await inspect(row.key)).draft,accepted);
  receipt.drafts.push({phase:"selected-faces",key:row.key,generation:record.generation,sha256:hash(record.draft)});
  await open(other);await eb("Begin edit").click();await source();await editor().locator("textarea.source-editor").fill('{"other":"untouched recovery λ",');await editIdle();await checkpoint();
  const otherRow=(await list()).find(r=>r.source===other),otherRecord=await inspect(otherRow.key);
  await keepClose();await stop();
  await launch();row=(await list()).find(r=>r.source===profile);assert.equal((await inspect(row.key)).draft,accepted);await recover(row);
  doc=(await ipc("open_document",{asset:profile})).result;assert.notEqual(doc.document_token,oldToken);assert(await eb("Review & apply").isDisabled());assert.equal((await source()).replaceAll("\n","\r\n"),accepted);
  await editor().locator("textarea.source-editor").fill('\ufeff{\n "font_ui_large": "IMFellEnglish-Regular.ttf",\n "unfinished": ["λ",');await editIdle();await checkpoint();
  record=await inspect(row.key);receipt.drafts.push({phase:"invalid-json",key:row.key,generation:record.generation,sha256:hash(record.draft)});
  await keepClose();await stop();
  await launch();row=(await list()).find(r=>r.source===profile);assert.equal((await inspect(row.key)).draft,record.draft);await recover(row);assert(await eb("Review & apply").isDisabled());
  assert.equal((await source()).replaceAll("\n","\r\n"),record.draft);await editor().locator("textarea.source-editor").fill(accepted);await editIdle();await checkpoint();
  const fresh=await validate();assert(fresh.valid && fresh.review_token,JSON.stringify(fresh));assert.equal(fresh.draft_sha256,hash(accepted));
  await eb("Review & apply").click();await b("Confirm apply one file").click();await idle();await eb("Begin edit").waitFor();
  const saved=await readFile(resolve(root,profile)),reopened=(await ipc("open_document",{asset:profile})).result;
  assert.equal(hash(saved),hash(accepted));assert.equal(reopened.sha256,hash(saved));assert.deepEqual(await inspect(otherRow.key),otherRecord);assert.equal((await list()).length,1);
  receipt.publication={reviewed:fresh.draft_sha256,saved:hash(saved),reopened:reopened.sha256,profile,roles:JSON.parse(accepted)};
  await page.screenshot({path:resolve(output,"published-reopened.png")});await stop();
  receipt.runtime=runtime();assert.equal(receipt.runtime.typography.fallback,false);assert.equal(receipt.runtime.profile_sha256,hash(accepted));
  for(const r of receipt.runtime.typography.roles)assert.equal(r.requested,JSON.parse(accepted)[r.role]);
  const invalid=JSON.stringify({...JSON.parse(accepted),font_ui_small:"missing.ttf"});await writeFile(resolve(root,profile),invalid);receipt.fallback=runtime();assert(receipt.fallback.typography.fallback);assert.equal(receipt.fallback.profile_sha256,hash(invalid));assert(receipt.fallback.warnings.length);
  assert.equal(await readFile(resolve(root,profile),"utf8"),invalid);await writeFile(resolve(root,profile),saved);
  receipt.checks.push("three actual native processes retain selected faces then exact invalid JSON; fresh review required", "normal one-file publication and verified reopen match candidate bytes; independent recovery is unchanged", "fresh production font initialization loads published roles; invalid present profile falls back completely without writes", "no variant control and forged variant intent refused by host; actual candidate specimen and reader");
  assert.deepEqual(receipt.errors,[]);receipt.passed=true;
}catch(e){receipt.passed=false;receipt.error=String(e.stack || e);await page?.screenshot({path:resolve(output,"failure.png")}).catch(()=>{});if(child)await stop(true).catch(()=>{});process.exitCode=1;}
await writeFile(resolve(output,"receipt.json"),JSON.stringify(receipt,null,2));await writeFile(resolve(".artifacts/w5e/native-latest.json"),JSON.stringify({output,passed:receipt.passed}));console.log(JSON.stringify({output,passed:receipt.passed,error:receipt.error,processes:receipt.processes},null,2));
