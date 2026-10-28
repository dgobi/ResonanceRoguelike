// Actual packaged WebView2, app-local DOM/IPC only; disposable data and recovery.
import assert from "node:assert/strict";
import {spawn,spawnSync,execFileSync} from "node:child_process";
import {mkdir,readFile,writeFile,copyFile} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";
import {chromium} from "playwright-core";
const output=resolve(".artifacts/w5f",`native-${Date.now()}`),root=resolve(output,"project"),settings=resolve(output,"settings"),storage=resolve(output,"recovery");
await mkdir(settings,{recursive:true});
const fixture=spawnSync(resolve("worker/runtime/python.exe"),["-X","utf8","-B","-c","import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{windowsHide:true,stdio:"inherit"});assert.equal(fixture.status,0);
await mkdir(resolve(root,"roguelike/docs/examples"),{recursive:true});
for(const name of ["g17_authored_creature_room.json","g17_authored_creature_room.access.json"])await copyFile(resolve("../roguelike/docs/examples",name),resolve(root,"roguelike/docs/examples",name));
const base="roguelike/data/entities/creatures/",wight=base+"barrow_wight.json",ordinary=base+"hollow_revenant.json",other="roguelike/data/items/components/clay_pot.json",layout="roguelike/docs/examples/g17_authored_creature_room.json";
const variantId="w5f_native_variant",variantPath=base+variantId+".json";
let ordinaryBaseline=(await readFile(resolve(root,ordinary),"utf8")).replace(/\r?\n/g,"\r\n").replace('  "base_hp":','  "w5f_metadata": {"exact":[1e2, null, "λ"]},\r\n  "base_hp":');
await writeFile(resolve(root,ordinary),ordinaryBaseline);
const wightBaseline="\ufeff"+await readFile(resolve(root,wight),"utf8");
await writeFile(resolve(root,wight),wightBaseline);
await writeFile(resolve(settings,"project.json"),JSON.stringify({version:1,project_root:root}));
const executable=resolve("src-tauri/target/release/resonance-workbench.exe"),hash=b=>createHash("sha256").update(b).digest("hex");
const receipt={started_utc:new Date().toISOString(),root,settings,storage,package_sha256:hash(await readFile(executable)),processes:[],checks:[],drafts:[],errors:[]};
let child,browser,page,launches=0;
const b=name=>page.getByRole("button",{name,exact:true}),editor=()=>page.locator('[data-testid="authoring"]:visible'),eb=name=>editor().getByRole("button",{name,exact:true});
const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
const idle=()=>page.waitForFunction(()=>!document.querySelector(".status-dot.working"),null,{timeout:60000});
const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==="true"));
async function opened(asset){for(let i=0;i<6;i++){await idle();const r=await ipc("open_document",{asset});if(r.result)return r.result;assert.equal(r.error?.code,"BUSY",JSON.stringify(r));}throw Error("Open remained busy");}
const source=async()=>{await eb("Source").click();return editor().locator("textarea.source-editor").inputValue();};
const open=async path=>{await idle();await page.getByLabel("Category / route").selectOption("");await page.getByLabel("Search ID, name or path").fill(path);await page.locator(`[data-asset="${path}"]`).click();await idle();};
const list=async()=>{const r=await ipc("list_recovery");assert(!r.error,JSON.stringify(r));return r.records;};
const inspect=async key=>{const r=await ipc("inspect_recovery",{key});assert(!r.error,JSON.stringify(r));return r.record;};
const checkpoint=()=>editor().getByTestId("recovery-status").getByText(/Recovery checkpoint saved/).waitFor({timeout:15000});
const fill=async(label,value)=>{await page.getByLabel(label,{exact:true}).filter({visible:true}).fill(value);await editIdle();};
async function launch(){
  launches++;const env={...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:settings,RESONANCE_WORKBENCH_RECOVERY_DIR:storage,WEBVIEW2_USER_DATA_FOLDER:resolve(output,`webview-${launches}`),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:"--remote-debugging-port=9337 --remote-debugging-address=127.0.0.1"};delete env.RESONANCE_PYTHON;
  child=spawn(executable,[],{cwd:output,env,windowsHide:true,stdio:"ignore"});receipt.processes.push(child.pid);
  for(let i=0;;i++){assert.equal(child.exitCode,null);try{const r=await fetch("http://127.0.0.1:9337/json/list");if((await r.json()).length)break;}catch{}if(i>160)throw Error("CDP did not start");await new Promise(r=>setTimeout(r,250));}
  browser=await chromium.connectOverCDP("http://127.0.0.1:9337");page=browser.contexts()[0].pages()[0];page.on("pageerror",e=>receipt.errors.push(e.message));await page.setViewportSize({width:1600,height:1000});
  await page.getByTestId("startup-ready").waitFor({timeout:30000});await idle();
}
async function stop(abrupt=false){if(!child)return;const ended=new Promise(r=>child.once("exit",r));if(abrupt)execFileSync("taskkill",["/PID",String(child.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});else await ipc("finish_close").catch(()=>{});await ended;await browser?.close().catch(()=>{});child=null;browser=null;}
async function keepClose(){await b("Close project").click();await b("Keep for Recovery and Close").click();await page.getByRole("dialog",{name:"Unsaved draft"}).waitFor({state:"hidden"});await idle();}
async function recover(row){await b("Recover drafts").click();await page.locator(`[data-recovery-key="${row.key}"]`).click();await page.getByTestId("recovery-detail").waitFor();await b("Recover selected draft").click();await page.getByRole("dialog",{name:"Recover drafts"}).waitFor({state:"hidden"});await idle();}
async function validate(){await editIdle();for(let i=0;i<5;i++){await idle();await eb("Validate draft").click();await idle();if(await editor().getByTestId("draft-receipt").count())return JSON.parse(await editor().getByTestId("draft-receipt").textContent());assert.match(await page.locator("footer").innerText(),/BUSY/);}throw Error("Validation remained busy");}
async function apply(){await eb("Review & apply").click();await b("Confirm apply one file").click();await idle();await page.getByText(/Saved and byte-checked reopen:/).waitFor({timeout:30000});}
async function recordDraft(path,phase){await checkpoint();const row=(await list()).find(r=>r.source===path);assert(row);const record=await inspect(row.key);receipt.drafts.push({path,phase,key:row.key,generation:record.generation,sha256:hash(record.draft)});return {row,record};}
async function clickCell(x,y){await page.getByTestId("layout-map").scrollIntoViewIfNeeded();const p=await page.getByTestId("layout-map").evaluate((el,[x,y])=>{const c=JSON.parse(el.dataset.camera),r=el.getBoundingClientRect();return {x:r.x+c.x+(x+.5)*16*c.scale,y:r.y+c.y+(y+.5)*16*c.scale};},[x,y]);await page.mouse.click(p.x,p.y);}
try{
  await launch();await open(wight);let doc=await opened(wight);
  assert.deepEqual(doc.family.effective_operations,["edit"]);assert.match(await page.getByTestId("creature-editor").innerText(),/Body supplied by inline limbs/);
  await b("References").click();assert.match(await page.getByTestId("creature-editor").innerText(),/retained inactive metadata/);assert.match(await page.getByTestId("creature-editor").innerText(),/zones\/dungeon\/barrow.json/);
  await b("Supported fields").click();await eb("Begin edit").click();assert.equal(await eb("Save as new variant").count(),0);
  await fill("Creature name","W5F native Wight");await fill("Effective HP","37");await fill("Natural armour","6");await fill("Sight radius","3");await fill("Damage dice","2d5");
  await b("Undo creature").click();await editIdle();assert.equal(await page.getByLabel("Damage dice",{exact:true}).inputValue(),"1d6");await b("Redo creature").click();await editIdle();
  let first=await recordDraft(wight,"common-fields"),acceptedWight=first.record.draft;
  const forged=await ipc("validate_document",{token:doc.document_token,draft:JSON.stringify({...JSON.parse(acceptedWight),id:"w5f_special_clone"}),variantId:"w5f_special_clone"});assert.equal(forged.error?.code,"OPERATION_POLICY");
  assert((await ipc("edit_document",{token:doc.document_token,sequence:999,draft:acceptedWight,variant:true,variantId:"w5f_special_clone"})).error);assert.equal((await inspect(first.row.key)).draft,acceptedWight);
  await page.screenshot({path:resolve(output,"wight-controls.png")});
  await open(ordinary);await eb("Begin edit").click();await eb("Save as new variant").click();await fill("New variant ID",variantId);
  await fill("Creature name","W5F native ordinary");await fill("Creature description","This variant has its own description.");await fill("Effective HP","19");
  await page.getByLabel("Creature AI",{exact:true}).filter({visible:true}).selectOption("ambush");await editIdle();await fill("Pursuit timeout","2");await fill("Speed","1.25");
  let second=await recordDraft(ordinary,"ordinary-variant"),acceptedOrdinary=second.record.draft;
  assert(acceptedOrdinary.includes('"w5f_metadata": {"exact":[1e2, null, "λ"]}'));
  await open(other);await eb("Begin edit").click();await source();await editor().locator("textarea.source-editor").fill('{"w5f_other":"kept independently λ",');await editIdle();
  const third=await recordDraft(other,"other-family-invalid");
  assert.equal((await list()).length,3);await keepClose();await stop();
  await launch();assert.equal((await inspect(first.row.key)).draft,acceptedWight);assert.equal((await inspect(second.row.key)).draft,acceptedOrdinary);
  await recover(first.row);doc=await opened(wight);assert(await eb("Review & apply").isDisabled());await source();
  await editor().locator("textarea.source-editor").fill('\ufeff{\n "w5f_invalid": ["λ",');await editIdle();first=await recordDraft(wight,"invalid-json");
  await recover(second.row);assert(await eb("Review & apply").isDisabled());assert.equal((await inspect(second.row.key)).draft,acceptedOrdinary);
  await keepClose();await stop(true);
  await launch();assert.equal((await inspect(first.row.key)).draft,first.record.draft);await recover(first.row);
  assert(await eb("Review & apply").isDisabled());let invalid=await validate();assert.equal(invalid.valid,false);await source();
  await editor().locator("textarea.source-editor").fill(acceptedWight);await editIdle();await checkpoint();
  let checked=await validate();assert(checked.valid&&checked.review_token,JSON.stringify(checked));
  doc=await opened(wight);
  const ability=resolve(root,"roguelike/engine/creature_abilities.py"),abilityBytes=await readFile(ability);await writeFile(ability,Buffer.concat([abilityBytes,Buffer.from("\n")]));
  await page.waitForFunction(()=>[...document.querySelectorAll('[data-testid="authoring"] button')].some(b=>b.textContent.trim()==="Review & apply"&&b.disabled),null,{timeout:15000});
  await idle();
  const stale=await ipc("apply_document",{token:doc.document_token,reviewToken:checked.review_token,confirmed:true});assert(["REVIEW_REQUIRED","SOURCE_CHANGED"].includes(stale.error?.code),JSON.stringify(stale));
  assert.equal(await readFile(resolve(root,wight),"utf8"),wightBaseline);await writeFile(ability,abilityBytes);
  checked=await validate();assert(checked.valid&&checked.review_token);await apply();
  let reopened=await opened(wight);assert.equal(reopened.sha256,hash(acceptedWight));assert.equal(reopened.raw,acceptedWight);
  assert.equal((await inspect(second.row.key)).draft,acceptedOrdinary);assert.equal((await inspect(third.row.key)).draft,third.record.draft);
  receipt.wight={path:wight,sha256:reopened.sha256,factory:reopened.family.context.records[0].factory};
  await recover(second.row);checked=await validate();assert(checked.valid&&checked.review_token,JSON.stringify(checked));assert.equal(checked.factory.instance.ai_class,"AmbushAI");assert.equal(checked.factory.special_binding,null);
  await apply();reopened=await opened(variantPath);assert.equal(reopened.raw,acceptedOrdinary);assert.equal(reopened.sha256,hash(acceptedOrdinary));
  assert.equal(await readFile(resolve(root,ordinary),"utf8"),ordinaryBaseline);assert.equal((await inspect(third.row.key)).draft,third.record.draft);
  receipt.variant={path:variantPath,sha256:reopened.sha256,factory:reopened.family.context.records[0].factory};
  await b("Factory result").click();await page.screenshot({path:resolve(output,"variant-factory.png")});
  await open(layout);await eb("Begin edit").click();await b("Authored layout").click();await page.getByTestId("layout-map").waitFor();
  await page.getByLabel("Placement creature").selectOption(variantId);await b("Place creature").click();await clickCell(4,3);
  await eb("Save as new variant").click();await fill("New variant ID","w5f_native_room");
  await b("Preview draft").click();await idle();const layoutResult=JSON.parse(await editor().getByTestId("draft-receipt").textContent());assert(layoutResult.valid,JSON.stringify(layoutResult));
  receipt.layout=layoutResult;assert(JSON.stringify(layoutResult).includes(variantId));
  await eb("Apply variant").click();await b("Confirm apply one file").click();await idle();
  await page.screenshot({path:resolve(output,"variant-layout.png")});
  await page.setViewportSize({width:1100,height:740});await open(wight);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));await page.screenshot({path:resolve(output,"wight-minimum.png")});
  receipt.checks.push("three independent family drafts and generations across three actual app processes, including invalid BOM/Unicode source and abrupt process exit",
    "fresh validation required after recovery; special clone and forged recovery intent refused without deleting text",
    "ability-source changes revoke evidence; exact same-ID and ordinary variant publication/reopen; unrelated recovery retained",
    "saved ordinary variant selected, constructed and published through existing authored-submap UI; no selector enrollment");
  assert.equal(receipt.errors.length,0);receipt.passed=true;
}catch(e){receipt.passed=false;receipt.failure=String(e.stack||e);if(page)await page.screenshot({path:resolve(output,"failure.png")}).catch(()=>{});throw e;}
finally{await stop(true).catch(()=>{});await writeFile(resolve(output,"receipt.json"),JSON.stringify(receipt,null,2));console.log(JSON.stringify({output,passed:receipt.passed,failure:receipt.failure}));}
