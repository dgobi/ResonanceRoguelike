import assert from "node:assert/strict";
import {readFile,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";

export async function contractJourney(page,root,output,receipt) {
  const item="roguelike/data/items/components/wood_bundle.json", module="roguelike/engine/item_authoring.py";
  const label="Eligible for automatic ingredient selection", sha=b=>createHash("sha256").update(b).digest("hex");
  const original=await readFile(resolve(root,item)), beforeModule=await readFile(resolve(root,module));
  const afterModule=await readFile(process.env.WORKBENCH_CONTRACT_AFTER);
  assert.notEqual(sha(beforeModule),sha(afterModule));
  const editor=()=>page.locator('[data-testid="authoring"]:visible'), b=name=>page.getByRole("button",{name,exact:true}), eb=name=>editor().getByRole("button",{name,exact:true});
  const idle=()=>page.waitForFunction(()=>!document.querySelector(".status-dot.working"),null,{timeout:45000});
  const source=async()=>{await eb("Source").click();return editor().locator("textarea.source-editor").inputValue();};
  const ipc=(command,args)=>page.evaluate(async([command,args])=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},[command,args]);
  await page.setViewportSize({width:1500,height:1000});
  await page.getByLabel("Search ID, name or path").fill(item);await page.locator(`[data-asset="${item}"]`).click();await idle();
  assert.equal(await page.getByLabel(label,{exact:true}).count(),0,"Baseline descriptor must not contain the extension");
  await eb("Begin edit").click();await page.getByLabel("Item weight (kg)",{exact:true}).fill("3.5");const retained=await source();
  await eb("Validate draft").click();await idle();
  const prior=JSON.parse(await editor().getByTestId("draft-receipt").textContent());assert(prior.review_token);
  // Replace only the selected project's integration module with the real new
  // production file. No descriptor injection or worker/application rebuild.
  await writeFile(resolve(root,module),afterModule);
  const changed=await ipc("worker_request",{request:{op:"inspect",asset:item}});
  assert.equal(changed.result.family.contract,prior.family.contract);
  assert.notEqual(changed.result.family.descriptor_sha256,prior.family.descriptor_sha256);
  assert.notEqual(changed.result.source.game_source_sha256,prior.source.game_source_sha256);
  // The original UI review is revoked by its real idle dependency poll.
  await page.waitForFunction(()=>{
    const active=[...document.querySelectorAll('[data-testid="authoring"]')].find(e=>e.getClientRects().length);
    return [...(active?.querySelectorAll("button") || [])].find(b=>b.textContent.trim()==="Review & apply")?.disabled;
  },null,{timeout:10000});
  assert.equal(await source(),retained);
  assert(await eb("Review & apply").isDisabled());
  await eb("Discard / Revert").click();await b("Reload item").click();await idle();
  assert.equal(await page.getByLabel(label,{exact:true}).isChecked(),true);
  assert.equal(JSON.parse(await source()).consumed_on_use,undefined);
  await b("Factory result").click();await b("Properties").first().click();
  assert.deepEqual(await readFile(resolve(root,item)),original,"Open/view/default must not write a key");
  await eb("Begin edit").click();await source();
  const raw=await source(), end=raw.lastIndexOf("}");
  const enriched=raw.slice(0,end).trimEnd()+',\n "w5a_metadata":{"keep":[null,true,{"prose":"untouched"}]}\n'+raw.slice(end);
  await editor().locator("textarea.source-editor").fill(enriched);
  await page.getByLabel(label,{exact:true}).uncheck();const disabled=await source();
  assert.equal(JSON.parse(disabled).consumed_on_use,false);assert(disabled.includes('"w5a_metadata":{"keep":[null,true,{"prose":"untouched"}]}'));
  const invalid=disabled.replace(/("consumed_on_use"\s*:\s*)false/,'$1null');
  await editor().locator("textarea.source-editor").fill(invalid);await eb("Validate draft").click();await idle();
  const refused=JSON.parse(await editor().getByTestId("draft-receipt").textContent());assert.equal(refused.valid,false);assert(!refused.review_token);
  assert.equal(await source(),invalid);assert(await eb("Review & apply").isDisabled());
  await editor().locator("textarea.source-editor").fill(disabled);
  await eb("Save as new variant").click();await editor().getByLabel("New variant ID").fill("wood_bundle_w5a");
  await eb("Validate draft").click();await idle();
  const checked=JSON.parse(await editor().getByTestId("draft-receipt").textContent());assert(checked.valid);assert(checked.review_token);
  assert.equal(checked.family.context.records[0].factory.instance.consumed_on_use,false);
  await page.getByTestId("item-editor").screenshot({path:resolve(output,"w5a-boolean-control.png")});
  await eb("Review & apply").click();await b("Confirm apply one file").click();await idle();
  const saved=await readFile(resolve(root,checked.path));assert.equal(sha(saved),checked.draft_sha256);
  assert.equal(JSON.parse(await source()).consumed_on_use,false);
  await b("Factory result").click();const factory=JSON.parse(await page.getByTestId("item-factory-receipt").textContent());
  assert.equal(factory.definition_sha256,sha(saved));assert.equal(factory.instance.consumed_on_use,false);
  assert.deepEqual(await readFile(resolve(root,item)),original);
  // Explicit host stale-review rejection, independent of renderer polling.
  const opened=await ipc("open_document",{asset:item});
  const live=await ipc("validate_document",{token:opened.result.document_token,draft:opened.result.raw+" ",variantId:null});assert(live.result.review_token);
  await writeFile(resolve(root,module),beforeModule);
  const stale=await ipc("apply_document",{token:opened.result.document_token,reviewToken:live.result.review_token,confirmed:true});
  assert(["SOURCE_CHANGED","REVIEW_REQUIRED"].includes(stale.error?.code),JSON.stringify(stale));
  await writeFile(resolve(root,module),afterModule);
  assert.deepEqual(await readFile(resolve(root,item)),original);
  receipt.extension={module,before_module_sha256:sha(beforeModule),after_module_sha256:sha(afterModule),
    before_descriptor:prior.family.descriptor_sha256,after_descriptor:checked.family.descriptor_sha256,
    before_game_source:prior.source.game_source_sha256,after_game_source:checked.source.game_source_sha256,
    contract:checked.family.contract,stale_review_code:stale.error.code,invalid_null_draft_sha256:refused.draft_sha256,
    publication:{path:checked.path,reviewed_sha256:checked.draft_sha256,saved_sha256:sha(saved),reopened_sha256:factory.definition_sha256},
    observed_consumed_on_use:factory.instance.consumed_on_use};
  receipt.checks.push("W5A: unchanged packaged app loaded real before/after game descriptor; old evidence revoked with exact draft retained; absent default caused no write; generic boolean localized edit and invalid null recovery; deliberate item variant publication matched reviewed/reopened bytes and actual factory; direct stale-source review rejected");
}
