// Packaged Windows, app-local CDP only. Every project, settings, recovery and
// WebView directory belongs to this run. Cold restarts are new native processes.
import assert from "node:assert/strict";
import {spawn,spawnSync,execFileSync} from "node:child_process";
import {mkdir,readFile,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";
import {chromium} from "playwright-core";

const output=resolve(".artifacts/w5d",`native-${Date.now()}`),root=resolve(output,"project"),settings=resolve(output,"settings"),storage=resolve(output,"recovery");
await mkdir(settings,{recursive:true});
const fixture=spawnSync(resolve("worker/runtime/python.exe"),["-X","utf8","-B","-c","import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{windowsHide:true,stdio:"inherit"});
assert.equal(fixture.status,0);
await writeFile(resolve(settings,"project.json"),JSON.stringify({version:1,project_root:root}));
const executable=resolve("src-tauri/target/release/resonance-workbench.exe"),hash=b=>createHash("sha256").update(b).digest("hex");
const paths=["roguelike/data/texts/lab/lab_note_primary_a.json","roguelike/data/texts/lab/lab_note_primary_b.json","roguelike/data/items/components/wood_bundle.json"];
const receipt={started_utc:new Date().toISOString(),executable,package_sha256:hash(await readFile(executable)),root,settings,storage,checks:[],processes:[],drafts:[],checkpoints:[],errors:[]};
let child,browser,page,launches=0;
const b=name=>page.getByRole("button",{name,exact:true}),editor=()=>page.locator('[data-testid="authoring"]:visible'),eb=name=>editor().getByRole("button",{name,exact:true});
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector(".status-dot.working"),null,{timeout:60000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==="true"));
const source=async()=>{await eb("Source").click();return editor().locator("textarea.source-editor").inputValue();};
const open=async path=>{await idle();await page.getByLabel("Search ID, name or path").fill(path);await page.locator(`[data-asset="${path}"]`).click();await idle();};
const tab=path=>page.locator(`[data-document-tab="${path}"]`).click();
const list=async()=>{const r=await ipc("list_recovery");assert(!r.error,JSON.stringify(r));return r.records;};
const inspect=async key=>{const r=await ipc("inspect_recovery",{key});assert(!r.error,JSON.stringify(r));return r;};
const checkpoint=()=>editor().getByTestId("recovery-status").getByText(/Recovery checkpoint saved/).waitFor({timeout:15000});
async function launch(fault=false){
  launches++;const env={...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,
    WEBVIEW2_USER_DATA_FOLDER:resolve(output,`webview-${launches}`),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:"--remote-debugging-port=9335 --remote-debugging-address=127.0.0.1"};
  if(fault)env.RESONANCE_PYTHON=resolve(output,"missing-python.exe");else delete env.RESONANCE_PYTHON;
  child=spawn(executable,fault ? ["--diagnostic-runtime"]:[],{cwd:output,env,windowsHide:true,stdio:"ignore"});receipt.processes.push(child.pid);
  for(let i=0;;i++){assert.equal(child.exitCode,null);try{const r=await fetch("http://127.0.0.1:9335/json/list");if((await r.json()).length)break;}catch{}if(i>160)throw Error("CDP did not start");await new Promise(r=>setTimeout(r,250));}
  browser=await chromium.connectOverCDP("http://127.0.0.1:9335");page=browser.contexts()[0].pages()[0];page.on("pageerror",e=>receipt.errors.push(e.message));
  await page.setViewportSize({width:1600,height:1000});await page.getByRole("heading",{name:"Resonance Workbench",exact:true}).waitFor();await idle();
  if(!fault)await page.getByTestId("startup-ready").waitFor({timeout:30000});
  await inject("");
}
async function stop(abrupt=false){
  if(!child)return;
  receipt.checkpoints.push(...await page.evaluate(()=>window.w5d?.checkpoints || []).catch(()=>[]));
  const ended=new Promise(r=>child.once("exit",r));
  if(abrupt)execFileSync("taskkill",["/PID",String(child.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});
  else await ipc("finish_close").catch(()=>{}); // Native close may precede its IPC response.
  await ended;await browser?.close().catch(()=>{});child=null;browser=null;
}
async function choose(row){await b("Recover drafts").click();await page.locator(`[data-recovery-key="${row.key}"]`).click();await page.getByTestId("recovery-detail").waitFor();}
async function recover(row){await choose(row);await b("Recover selected draft").click();await page.getByRole("dialog",{name:"Recover drafts",exact:true}).waitFor({state:"hidden"});await idle();}
async function keepCloseProject(){
  await idle();await b("Close project").click();await page.getByRole("dialog",{name:"Unsaved draft"}).waitFor();await b("Keep for Recovery and Close").click();await page.getByRole("dialog",{name:"Unsaved draft"}).waitFor({state:"hidden"});await idle();
}
async function validate(){
  for(let i=0;i<4;i++){
    await idle();await eb("Validate draft").click();await idle();
    if(await editor().getByTestId("draft-receipt").count())return JSON.parse(await editor().getByTestId("draft-receipt").textContent());
    const text=await page.locator("footer").innerText();assert.match(text,/BUSY/);
  }throw Error("validation stayed busy");
}
async function inject(mode){
  await page.evaluate(mode=>{
    window.w5d ??={original:window.fetch.bind(window),applies:0,checkpoints:[],pending:{}};window.w5d.mode=mode;
    window.fetch=async(input,init)=>{
      const u=new URL(String(input),location.href),command=u.hostname==="ipc.localhost" ? decodeURIComponent(u.pathname.slice(1)):"";
      const args=init?.body ? JSON.parse(typeof init.body==="string" ? init.body:new TextDecoder().decode(init.body)):{};
      if(command==="apply_document")window.w5d.applies++;
      const reject=(code,message)=>new Response(JSON.stringify({code,message,remedy:"Test-owned transport fault."}),{headers:{"Content-Type":"application/json","Tauri-Response":"error"}});
      if(command==="edit_document" && window.w5d.mode==="busy-edit"){window.w5d.mode="";return reject("BUSY","Injected reserved-publication refusal");}
      if(command==="checkpoint_document" && window.w5d.mode==="checkpoint-block")return reject("RECOVERY","Injected recovery-storage failure");
      if(command==="open_document" && args.expectedSha256 && window.w5d.mode.startsWith("reopen-")){
        const mode=window.w5d.mode;window.w5d.mode="";
        if(mode==="reopen-after"){const response=await window.w5d.original(input,init);window.w5d.replaced=await response.clone().json();}
        return reject("TEST_REOPEN_FAILURE",mode);
      }
      const started=performance.now(),response=await window.w5d.original(input,init);
      if(command==="edit_document"){
        const result=await response.clone().json();if(typeof result==="number")window.w5d.pending[args.token] ??= performance.now();
      }
      if(command==="checkpoint_document"){
        const result=await response.clone().json();
        window.w5d.checkpoints.push({...result,wall_ms:performance.now()-started,accepted_to_checkpoint_ms:window.w5d.pending[args.token] ? performance.now()-window.w5d.pending[args.token]:null});
        if(result.generation)delete window.w5d.pending[args.token];
      }
      return response;
    };
  },mode);
}
try{
  await launch();const originals=new Map(),tokens=new Map();
  for(let i=0;i<paths.length;i++){
    await open(paths[i]);const doc=(await ipc("open_document",{asset:paths[i]})).result;tokens.set(paths[i],doc.document_token);originals.set(paths[i],doc.raw);
    await eb("Begin edit").click();await eb("Save as new variant").click();await editIdle();await editor().getByLabel("New variant ID").fill(`w5d_draft_${i}`);await editIdle();
    if(i===0){await source();await editor().locator("textarea.source-editor").fill('\ufeff{\n "metadata": "Unicode λ 雨 and \\n escaping",\n "pages": [');}
    if(i===1){await page.getByLabel("Reader title",{exact:true}).filter({visible:true}).fill("A durable letter — λ");await editIdle();await page.getByLabel("Page text 1",{exact:true}).filter({visible:true}).fill('First line\nSecond line, with a quoted "word".');}
    if(i===2){await page.getByLabel("Item description",{exact:true}).filter({visible:true}).fill("Durable component variant");}
    await editIdle();await checkpoint();
  }
  await tab(paths[2]);const beforeFailure=(await list()).find(r=>r.source===paths[2]),previousCheckpoint=(await inspect(beforeFailure.key)).record.draft;
  await inject("checkpoint-block");await page.getByLabel("Item description",{exact:true}).filter({visible:true}).fill("Retained through a failed checkpoint");await editIdle();await editor().getByTestId("recovery-status").getByText(/Unable to save recovery/).waitFor();
  assert.equal((await inspect(beforeFailure.key)).record.draft,previousCheckpoint);
  await b("Close document").click();await b("Keep for Recovery and Close").click();await page.waitForFunction(()=>document.querySelector("footer").textContent.includes("Injected recovery-storage failure"));assert.equal(await page.getByRole("dialog",{name:"Unsaved draft"}).count(),1);await b("Keep editing").click();
  await inject("");await eb("Retry recovery save").click();await checkpoint();
  receipt.checks.push("failed recovery checkpoint keeps previous complete copy and in-memory draft; failed close flush retains owner; explicit retry succeeds");
  let rows=await list();assert.equal(rows.length,3);
  const locked=(await inspect(rows[0].key)).record;
  const competing=spawnSync("cargo",["test","--locked","--manifest-path","src-tauri/Cargo.toml","--","--exact","recovery::tests::checkpoint_child_process"],{
    windowsHide:true,encoding:"utf8",env:{...process.env,W5D_CHILD_STORE:storage,W5D_CHILD_RECORD:JSON.stringify(locked)},timeout:30000,
  });
  assert.notEqual(competing.status,0);assert.match(competing.stdout+competing.stderr,/owned by another running Workbench instance/);
  assert.deepEqual((await inspect(rows[0].key)).record,locked);
  receipt.checks.push("a separate native process using the real recovery writer cannot overwrite the running application's locked record");
  for(const row of rows){const {record}=await inspect(row.key);receipt.drafts.push({source:record.source,key:row.key,generation:record.generation,sha256:hash(record.draft),variant_id:record.variant_id,original_token:tokens.get(record.source)});}
  await tab(paths[2]);const accepted=await source();await inject("busy-edit");await editor().locator("textarea.source-editor").fill(accepted+"REJECTED_OPTIMISTIC_SENTINEL");await editIdle();assert.equal(await source(),accepted);
  const itemRow=rows.find(r=>r.source===paths[2]);assert(!(await inspect(itemRow.key)).record.draft.includes("REJECTED_OPTIMISTIC_SENTINEL"));
  receipt.checks.push("only host-accepted edits become recovery truth; rejected optimistic raw edit rolls back");
  const legacy="roguelike/data/buildings/commercial/workshop_b.json";await open(legacy);await eb("Begin edit").click();const legacySource=await source();await editor().locator("textarea.source-editor").fill(legacySource+" ");await editIdle();
  await b("Close project").click();assert.equal(await b("Keep for Recovery and Close").count(),0);await b("Keep editing").click();await eb("Discard / Revert").click();await editIdle();
  await keepCloseProject();await stop();
  await launch();rows=await list();assert.equal(rows.length,3);
  for(const row of rows){const {record}=await inspect(row.key),before=receipt.drafts.find(d=>d.source===row.source);assert.equal(hash(record.draft),before.sha256);assert.equal(record.variant_id,before.variant_id);assert.equal(record.generation,before.generation);}
  receipt.checks.push("two same-family text drafts and one item survive a cold native process restart with independent exact text and intent; legacy drafts cannot be silently kept");
  await recover(rows.find(r=>r.source===paths[0]));assert.match(await source(),/Unicode λ 雨/);assert(await eb("Apply variant").isDisabled());
  const first=(await ipc("open_document",{asset:paths[0]})).result;assert.notEqual(first.document_token,tokens.get(paths[0]));assert((await ipc("invalidate_document",{token:tokens.get(paths[0])})).error);
  await recover(rows.find(r=>r.source===paths[1]));assert.equal(await editor().getByLabel("New variant ID").inputValue(),"w5d_draft_1");assert(await eb("Apply variant").isDisabled());
  const reviewed=await validate();assert(reviewed.valid && reviewed.review_token);
  await inject("reopen-before");await eb("Apply variant").click();await b("Confirm apply one file").click();await idle();await editor().getByTestId("saved-reopen-failed").waitFor();
  const savedText=await readFile(resolve(root,"roguelike/data/texts/lab/w5d_draft_1.json"));assert.equal(hash(savedText),reviewed.draft_sha256);
  const raw=await source();await editor().locator("textarea.source-editor").fill(raw+" \n\t");await editIdle();const newer=await source();await eb("Retry verified reopen").click();await idle();assert.equal(await source(),newer);assert.match(await page.locator("footer").innerText(),/NEWER_DRAFT/);
  await page.getByLabel("Reader title",{exact:true}).filter({visible:true}).fill("Structured newer work remains");await editIdle();const structured=await source();await eb("Retry verified reopen").click();await idle();assert.equal(await source(),structured);await checkpoint();
  receipt.checks.push("real publication then failed reopen preserves accepted raw and structured newer edits on retry");
  await recover(rows.find(r=>r.source===paths[2]));const itemReview=await validate();assert(itemReview.valid && itemReview.review_token);
  await inject("reopen-after");await eb("Review & apply").click();await b("Confirm apply one file").click();await idle();await editor().getByTestId("saved-reopen-failed").waitFor();
  assert((await page.evaluate(()=>window.w5d.replaced)).ok);
  const beforeRefused=await source();await editor().locator("textarea.source-editor").fill(beforeRefused+"REFUSED_AFTER_HOST_REPLACEMENT");await editIdle();assert.equal(await source(),beforeRefused);
  await page.getByLabel("Item description",{exact:true}).filter({visible:true}).fill("REFUSED_STRUCTURED_AFTER_REPLACEMENT");await editIdle();assert.equal(await source(),beforeRefused);
  assert.equal(await page.evaluate(()=>window.w5d.applies),2);
  receipt.checks.push("successful host replacement with lost response refuses obsolete-owner raw and structured edits; completed fact retained");
  await keepCloseProject();await stop();
  await launch();rows=await list();assert.equal(rows.length,3);
  const publishedItem=rows.find(r=>r.source===paths[2]);assert(publishedItem.published);
  const itemTarget=publishedItem.published.path,bytes=await readFile(resolve(root,itemTarget));
  await choose(publishedItem);await b("Reconcile saved file").click();await page.getByRole("dialog",{name:"Recover drafts"}).waitFor({state:"hidden"});await idle();
  assert.equal((await list()).length,2);assert.equal(hash(await readFile(resolve(root,itemTarget))),hash(bytes));
  const reopened=(await ipc("open_document",{asset:itemTarget})).result;assert.equal(reopened.sha256,itemReview.draft_sha256);
  receipt.publication={path:itemTarget,reviewed:itemReview.draft_sha256,saved:hash(bytes),reopened:reopened.sha256,reconciled_without_apply:true};
  const newerRow=(await list()).find(r=>r.source===paths[1]);assert(newerRow.generation>newerRow.published.generation);
  await choose(newerRow);await b("Reconcile saved file").click();await page.getByRole("dialog",{name:"Recover drafts"}).waitFor();await page.waitForFunction(()=>document.querySelector("footer").textContent.includes("Saved target does not cover"));assert.equal((await list()).length,2);await b("Keep for later").click();
  receipt.checks.push("cold restart reconciliation reads exact published bytes, retires only covered item generation, and refuses to retire newer text work");
  const invalidRow=(await list()).find(r=>r.source===paths[0]);await recover(invalidRow);const abrupt=(await source())+"\nABRUPT_EXIT_SENTINEL";await editor().locator("textarea.source-editor").fill(abrupt);await editIdle();await checkpoint();
  const abruptRecord=(await inspect(invalidRow.key)).record;await page.screenshot({path:resolve(output,"recovered-drafts.png")});await stop(true);
  await launch();assert.equal((await inspect(invalidRow.key)).record.draft,abruptRecord.draft);receipt.abrupt={generation:abruptRecord.generation,sha256:hash(abruptRecord.draft),restored_sha256:hash((await inspect(invalidRow.key)).record.draft)};
  await stop();
  // Failed runtime handshake must not remove storage inspection/discard access.
  await writeFile(resolve(root,paths[0]),"changed malformed source {");
  await launch(true);assert.match(await page.locator("footer").innerText(),/WORKER_MISSING/);await choose(invalidRow);
  assert.equal(await page.getByLabel("Recovered exact draft",{exact:true}).inputValue(),abruptRecord.draft.replaceAll("\r\n","\n"));
  await page.getByText("Compare baseline and current disk",{exact:true}).click();assert.equal(await page.getByLabel("Current disk",{exact:true}).inputValue(),"changed malformed source {");
  await b("Keep for later").click();await choose(newerRow);await b("Discard selected draft…").click();await b("Confirm discard recovery").click();await page.waitForFunction(()=>!document.querySelector('[data-testid="recovery-detail"]'));
  assert.equal((await list()).length,1);await page.screenshot({path:resolve(output,"worker-unavailable-recovery.png")});
  receipt.checks.push("separate abrupt-exit segment retains completed checkpoint; failed worker handshake leaves inspection, comparison and deliberate selected discard available");
  assert.deepEqual(receipt.errors,[]);receipt.passed=true;await stop();
}catch(e){receipt.passed=false;receipt.error=String(e.stack || e);await page?.screenshot({path:resolve(output,"failure.png")}).catch(()=>{});if(child)await stop(true).catch(()=>{});process.exitCode=1;}
await writeFile(resolve(output,"receipt.json"),JSON.stringify(receipt,null,2));await writeFile(resolve(".artifacts/w5d/native-latest.json"),JSON.stringify({output,passed:receipt.passed}));console.log(JSON.stringify(receipt,null,2));
