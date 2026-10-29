import assert from "node:assert/strict";
import {readFile,writeFile,realpath} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";

export async function workspaceJourney(page,root,output,receipt) {
  assert.match(root.replaceAll("\\","/"),/\/workbench\/\.artifacts\/w5c\/data-fixture-\d+$/);
  assert.equal(await realpath(root),resolve(root));
  const paths=["roguelike/data/items/components/wood_bundle.json","roguelike/data/items/components/clay_pot.json",
    "roguelike/data/recipes/bile_coating.json","roguelike/data/recipes/w5c_recipe_source.json",
    "roguelike/data/texts/lab/lab_note_primary_a.json","roguelike/data/texts/lab/lab_note_primary_b.json"];
  const building="roguelike/data/buildings/commercial/workshop_b.json";
  const originals=new Map(await Promise.all([...paths,building].map(async p=>[p,await readFile(resolve(root,p))])));
  const b=name=>page.getByRole("button",{name,exact:true}), editor=()=>page.locator('[data-testid="authoring"]:visible');
  const eb=name=>editor().getByRole("button",{name,exact:true});
  const visible=selector=>page.locator(`${selector}:visible`);
  const idle=()=>page.waitForFunction(()=>!document.querySelector(".status-dot.working") && !window.w5c?.active,null,{timeout:60000});
  const editIdle=()=>page.waitForFunction(()=>![...document.querySelectorAll('[data-testid="authoring"]')].some(e=>e.dataset.editPending==="true"));
  const source=async()=>{await eb("Source").click();return editor().locator("textarea.source-editor").inputValue();};
  const open=async path=>{await page.getByLabel("Search ID, name or path").fill(path);await page.locator(`[data-asset="${path}"]`).click();await idle();};
  const tab=async path=>{await page.locator(`[data-document-tab="${path}"]`).click();};
  const ipc=async(command,args)=>{
    for(let attempt=0;;attempt++){
      const result=await page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
      if(command!=="open_document" || result.error?.code!=="BUSY" || attempt>=9)return result;
      await idle();await page.waitForTimeout(100);
    }
  };
  const digest=bytes=>createHash("sha256").update(bytes).digest("hex");
  const validate=async()=>{
    for(let attempt=0;attempt<3;attempt++) {
      await idle();await eb("Validate draft").click();await idle();
      if(await editor().getByTestId("draft-receipt").count())return;
      // A sweep may win the host's single-operation reservation immediately
      // before the click. Retry only its explicit BUSY refusal, as the UI allows.
      assert.match(await page.locator("body").innerText(),/BUSY/);
      receipt.busy_retries=(receipt.busy_retries || 0)+1;
    }
    assert.fail("Validation stayed BUSY after three deliberate attempts.");
  };
  // Observe the real host sweep. A one-shot transport rejection after a real
  // successful write exercises the saved/reopen-failed UI without altering files.
  await page.evaluate(lost=>{
    const original=window.fetch.bind(window);
    window.w5c={sweeps:[],active:0,maxActive:0,failReopen:false};
    window.fetch=async(input,init)=>{
      const url=new URL(String(input),location.href),command=url.hostname==="ipc.localhost" ? decodeURIComponent(url.pathname.slice(1)):"";
      const args=command==="open_document" ? JSON.parse(typeof init.body==="string" ? init.body:new TextDecoder().decode(init.body)):null;
      if(command==="open_document" && args?.expectedSha256 && window.w5c.failReopen){window.w5c.failReopen=false;if(lost){const response=await original(input,init);window.w5c.lostResponse=await response.clone().json();}return new Response(JSON.stringify({code:"TEST_REOPEN_FAILURE",message:"Injected verified-reopen transport failure.",remedy:"Retry verified reopen."}),{headers:{"Content-Type":"application/json","Tauri-Response":"error"}});}
      if(command!=="workspace_disk")return original(input,init);
      const started=performance.now();window.w5c.active++;window.w5c.maxActive=Math.max(window.w5c.maxActive,window.w5c.active);
      try{const response=await original(input,init),result=await response.clone().json();if(result.ok)window.w5c.sweeps.push({started,wall_ms:performance.now()-started,...result.result});
        if(window.w5c.holdSweep){window.w5c.holdSweep=false;await new Promise(resolve=>window.w5c.releaseSweep=resolve);delete window.w5c.releaseSweep;}
        return response;}
      finally{window.w5c.active--;}
    };
  },process.env.W5D_REOPEN_REGRESSION === "lost");
  const measure=async count=>{
    const before=await page.evaluate(()=>({time:performance.now(),index:window.w5c.sweeps.length}));
    await page.waitForTimeout(6800);
    const sample=await page.evaluate(before=>({wall_ms:performance.now()-before.time,sweeps:window.w5c.sweeps.slice(before.index).map(s=>({wall_ms:s.wall_ms,elapsed_ms:s.elapsed_ms,dependency_scans:s.dependency_scans,documents:s.documents.length})),max_inflight:window.w5c.maxActive}),before);
    assert(sample.sweeps.length>=2,JSON.stringify(sample));
    assert(sample.sweeps.length<=3);assert.equal(sample.max_inflight,1);
    for(const sweep of sample.sweeps){assert.equal(sweep.dependency_scans,1);assert.equal(sweep.documents,count);}
    return sample;
  };
  await open(paths[0]);receipt.monitoring={one:await measure(1)};
  const drafts=new Map(),ids=new Map(),tokens=new Map(),beforeEdits=new Map();
  for(let index=0;index<paths.length;index++) {
    const path=paths[index];if(index)await open(path);
    const opened=await ipc("open_document",{asset:path});assert(opened.result,JSON.stringify(opened));tokens.set(path,opened.result.document_token);
    await eb("Begin edit").click();await eb("Save as new variant").click();
    const id=`w5c_parked_${index}`;ids.set(path,id);await editor().getByLabel("New variant ID").fill(id);await editIdle();
    beforeEdits.set(path,await source());
    const field=index<2 ? "Item description" : index<4 ? "Recipe description" : "Reader title";
    await page.getByLabel(field,{exact:true}).filter({visible:true}).fill(index<4 ? `Independent workspace draft ${index}` : `Correspondence ${index-3} — the unquiet bells`);await editIdle();
    if(index>=4){await page.getByLabel("Page text 1",{exact:true}).filter({visible:true}).fill(index===4 ? "Dear keeper, the bells sounded again. Keep this letter." : "Dear correspondent, I heard them too. Your letter reached me.");await editIdle();}
    if(index===5){await page.getByLabel("Page text 2",{exact:true}).filter({visible:true}).fill(Array.from({length:50},(_,i)=>`Letter continuation ${i}: the bells are still silent.`).join("\n"));await editIdle();}
    drafts.set(path,await source());
  }
  assert.equal(await page.locator("[data-document-tab]").count(),6);
  receipt.monitoring.six=await measure(6);
  await page.evaluate(()=>window.w5c.holdSweep=true);
  await page.waitForFunction(()=>!!window.w5c.releaseSweep);
  assert(await eb("Validate draft").isDisabled());assert(await b("Reload document").isDisabled());
  await page.evaluate(()=>window.w5c.releaseSweep());await idle();assert(!(await eb("Validate draft").isDisabled()));
  receipt.checks.push("a held real freshness response disables conflicting UI actions until release without queueing work");
  await open(building);await eb("Begin edit").click();const buildingOriginal=await source();
  await editor().locator("textarea.source-editor").fill(buildingOriginal+" \n");await editIdle();const buildingDraft=await source();
  // Each editor and history stays mounted, including Source and variant fields.
  for(let index=0;index<paths.length;index++) {
    const path=paths[index];await tab(path);assert.equal(await source(),drafts.get(path));assert.equal(await editor().getByLabel("New variant ID").inputValue(),ids.get(path));
    const undo=index<2 ? "Undo item" : index<4 ? "Undo recipe" : "Undo text",redo=undo.replace("Undo","Redo");
    await b(undo).click();await editIdle();assert.notEqual(await source(),drafts.get(path));await b(redo).click();await editIdle();assert.equal(await source(),drafts.get(path));
  }
  await tab(paths[5]);await b("Reader preview").click();await page.getByLabel("Preview page").filter({visible:true}).selectOption("1");
  await b("Preview exact text").click();await idle();await b("End").click();await b("Preview exact text").click();await idle();
  const frame=JSON.parse(await visible('[data-testid="text-editor"]').getByTestId("reader-preview-receipt").textContent());assert(frame.max_scroll>0);assert.equal(frame.scroll,frame.max_scroll);
  const scrollState=await page.locator(".preview-pane").evaluate(el=>{el.scrollTop=300;return el.scrollTop;});
  // Let the app receive the browser's scroll event before switching the view.
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  await tab(paths[4]);const invalid='{\n "id": "exact parked invalid", "pages": [';
  await editor().locator("textarea.source-editor").fill(invalid);await editIdle();const invalidBytes=await source();
  await tab(paths[5]);assert.equal(await page.getByLabel("Preview page").filter({visible:true}).inputValue(),"1");
  await page.waitForFunction(expected=>document.querySelector('.preview-pane').scrollTop===expected,scrollState);
  assert.equal(await page.locator(".preview-pane").evaluate(el=>el.scrollTop),scrollState);
  receipt.view_state={page:1,reader_scroll:frame.scroll,reader_max_scroll:frame.max_scroll,pane_scroll:scrollState,preserved:true};
  assert.match(await page.getByTestId("reader-preview-state").filter({visible:true}).innerText(),/^Current/);
  assert.equal(await source(),drafts.get(paths[5]));await tab(paths[4]);assert.equal(await source(),invalidBytes);
  assert(await eb("Apply variant").isDisabled());await editor().locator("textarea.source-editor").fill(drafts.get(paths[4]));await editIdle();
  // Both recipe origins point into the same existing item draft, then return to
  // the exact recipe and initiating relation button.
  for(const recipe of paths.slice(2,4)) {
    await tab(recipe);await validate();
    const recipeView=visible('[data-testid="recipe-editor"]');
    const details=recipeView.locator("details").filter({has:page.getByRole("button",{name:"clay_pot",exact:true,includeHidden:true})}).first();
    await details.locator("summary").click();const link=details.getByRole("button",{name:"clay_pot",exact:true});await link.click();
    assert.equal(await source(),drafts.get(paths[1]));assert.equal(await page.locator("[data-document-tab]").count(),7);
    await b(`Return to recipe ${JSON.parse(originals.get(recipe)).id}`).click();
    await page.waitForFunction(el=>document.activeElement===el,await link.elementHandle());
    assert.equal(await source(),drafts.get(recipe));
    assert.equal(await ipc("open_document",{asset:recipe}).then(r=>r.result.document_token),tokens.get(recipe));
  }
  const alias=await ipc("open_document",{asset:paths[1].toUpperCase().replaceAll("/","\\")});assert.equal(alias.result.document_token,tokens.get(paths[1]));
  await open(paths[1]);assert.equal(await source(),drafts.get(paths[1]));
  // Targeted prompts preserve the target and every other dirty file.
  await b("Close document").click();assert.match(await page.getByRole("dialog").innerText(),/clay_pot.json/);await b("Keep editing").click();assert.equal(await source(),drafts.get(paths[1]));
  await b("Reload document").click();await b("Keep editing").click();assert.equal(await source(),drafts.get(paths[1]));
  await b("Close project").click();for(const path of [...paths,building])assert((await page.getByRole("dialog").innerText()).includes(path));await b("Keep editing").click();
  await tab(paths[5]);await b("Reload document").click();await b("Discard and continue").click();await page.getByRole("dialog",{name:"Unsaved draft"}).waitFor({state:"hidden"});await idle();
  assert.equal((await source()).replace(/\r\n/g,"\n"),originals.get(paths[5]).toString().replace(/\r\n/g,"\n"));
  const reloaded=await ipc("open_document",{asset:paths[5]});assert.notEqual(reloaded.result.document_token,tokens.get(paths[5]));
  assert.equal((await ipc("invalidate_document",{token:tokens.get(paths[5])})).error.code,"FILE_TRANSACTION_FAILED");
  await tab(paths[0]);await b("Close document").click();await b("Discard and continue").click();await page.locator(`[data-document-tab="${paths[0]}"]`).waitFor({state:"detached"});await idle();
  assert.equal(await page.locator("[data-document-tab]").count(),6);
  await open(paths[0]);const reopened=await ipc("open_document",{asset:paths[0]});assert.notEqual(reopened.result.document_token,tokens.get(paths[0]));
  assert((await ipc("validate_document",{token:tokens.get(paths[0]),draft:drafts.get(paths[0]),variantId:ids.get(paths[0])})).error);
  // Host refuses a transition onto another open owner even with valid hash.
  const collision=await ipc("open_document",{asset:paths[1],replaceToken:tokens.get(paths[2]),expectedSha256:digest(originals.get(paths[1]))});
  assert.equal(collision.error.code,"DOCUMENT_OPEN");
  // One real publication. The one-shot reopen failure retains source, target,
  // exact draft and receipt; recovery only reopens, never repeats publication.
  await tab(paths[4]);await validate();
  const verdict=JSON.parse(await editor().getByTestId("draft-receipt").textContent());assert(verdict.valid && verdict.review_token,JSON.stringify(verdict));
  await page.evaluate(()=>window.w5c.failReopen=true);
  await eb("Apply variant").click();await b("Confirm apply one file").click();await tab(paths[2]);await idle();
  assert.equal(await source(),drafts.get(paths[2]));await tab(paths[4]);
  await editor().getByTestId("saved-reopen-failed").waitFor();assert.equal(await source(),drafts.get(paths[4]));
  const target=paths[4].replace("lab_note_primary_a",ids.get(paths[4]));const saved=await readFile(resolve(root,target));assert.equal(digest(saved),verdict.draft_sha256);
  assert(["REVIEW_REQUIRED","UNKNOWN_DOCUMENT"].includes((await ipc("apply_document",{token:tokens.get(paths[4]),reviewToken:verdict.review_token,confirmed:true})).error.code));
  if(process.env.W5D_REOPEN_REGRESSION === "newer") {
    const newer=drafts.get(paths[4])+" \n\t";
    await editor().locator("textarea.source-editor").fill(newer);await editIdle();
    assert.equal(await source(),newer);
    await eb("Retry verified reopen").click();await idle();
    assert.equal(await source(),newer,"Retry must preserve accepted post-publication text");
    assert.match(await page.locator("footer").innerText(),/NEWER_DRAFT/);
    await page.getByLabel("Reader title",{exact:true}).filter({visible:true}).fill("Accepted structured work after publication");await editIdle();
    const structured=await source();assert.match(structured,/Accepted structured work/);
    await eb("Retry verified reopen").click();await idle();assert.equal(await source(),structured);
    receipt.checks.push("raw and structured edits accepted after save survive a refused reopen");
    await b("Close project").click();await b("Discard and continue").click();await idle();await b("Open directory").click();await idle();
    return;
  }
  await eb("Retry verified reopen").click();await idle();assert.equal((await source()).replace(/\r\n/g,"\n"),saved.toString().replace(/\r\n/g,"\n"));
  assert.equal(await editor().getByTestId("saved-reopen-failed").count(),0);
  assert.doesNotMatch(await page.locator("footer").innerText(),/TEST_REOPEN_FAILURE/);
  const savedDoc=await ipc("open_document",{asset:target});assert.equal(savedDoc.result.sha256,digest(saved));
  receipt.variant={path:target,reviewed_sha256:verdict.draft_sha256,saved_sha256:digest(saved),reopened_sha256:savedDoc.result.sha256,reopen_failure:"one-shot transport injection after real publication",recovery:"verified reopen only"};
  for(const path of [paths[1],paths[2],paths[3]]){await tab(path);assert.equal(await source(),drafts.get(path));assert.equal(await editor().getByLabel("New variant ID").inputValue(),ids.get(path));}
  // File change belongs to that draft; dependency changes invalidate reviews,
  // but never discard any source. The disposable source is restored afterwards.
  await writeFile(resolve(root,paths[1]),Buffer.concat([originals.get(paths[1]),Buffer.from(" ")]));
  await tab(paths[1]);await editor().getByText("Externally changed · unsaved draft retained",{exact:true}).waitFor({timeout:15000});assert.equal(await source(),drafts.get(paths[1]));
  await writeFile(resolve(root,paths[1]),originals.get(paths[1]));
  await tab(building);assert.equal(await source(),buildingDraft);
  await tab(paths[3]);await page.locator(".preview-pane").evaluate(el=>el.scrollTop=0);await page.screenshot({path:resolve(output,"six-documents.png")});
  await page.setViewportSize({width:1100,height:740});await tab(paths[1]);assert.equal(await source(),drafts.get(paths[1]));
  await tab(paths[3]);await page.locator(".preview-pane").evaluate(el=>el.scrollTop=0);
  assert.equal(await page.locator("[data-document-tab]").count(),7);
  await page.screenshot({path:resolve(output,"six-documents-minimum.png")});await page.setViewportSize({width:2560,height:1440});
  // Closing the actual origin yields an explicit unavailable-origin message.
  await validate();const details=visible('[data-testid="recipe-editor"]').locator("details").filter({has:page.getByRole("button",{name:"clay_pot",exact:true,includeHidden:true})}).first();
  if(!await details.evaluate(e=>e.open))await details.locator("summary").click();await details.getByRole("button",{name:"clay_pot",exact:true}).click();
  await tab(paths[3]);await b("Close document").click();await b("Discard and continue").click();await page.locator(`[data-document-tab="${paths[3]}"]`).waitFor({state:"detached"});await tab(paths[1]);
  await b("Return to recipe w5c_recipe_source").click();assert.match(await page.locator("footer").innerText(),/ORIGIN_UNAVAILABLE/);assert.equal(await source(),drafts.get(paths[1]));
  for(const [path,bytes] of originals)assert.deepEqual(await readFile(resolve(root,path)),bytes,path);
  receipt.checks.push("six independent file owners; exact invalid source; variant targets and undo/redo retained; aliases/repeated opens reuse tokens; shared-item references return to both recipe origins",
    "targeted close/reload keep/discard and obsolete-token rejection; destination owner collision; one reviewed/saved/reopened variant with deliberate recovery after reopen failure",
    "individual external conflict and conservative freshness preserve drafts; registered building source remains byte-exact; unavailable closed reference origin is explicit");
  // Leave no dirty confirmation for the harness's final project-close smoke.
  await b("Close project").click();await b("Discard and continue").click();await page.getByTestId("startup-ready").waitFor({state:"detached"});await idle();
  await b("Open directory").click();await idle();
}
