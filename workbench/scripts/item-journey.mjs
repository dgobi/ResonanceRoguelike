import assert from "node:assert/strict";
import {readFile, writeFile, stat, realpath, mkdir, rename, symlink, unlink} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";

export async function itemJourney(page, root, output, receipt) {
  assert.match(root.replaceAll("\\","/"), /\/workbench\/\.artifacts\/w3b\/data-fixture-\d+$/);
  assert.equal(await realpath(root),resolve(root));
  const item="roguelike/data/items/components/wood_bundle.json", pool="roguelike/data/loot_pools/workshop_b_fuel.json", building="roguelike/data/buildings/commercial/workshop_b.json";
  const itemId="wood_bundle_w3b", poolId="workshop_b_fuel_w3b", itemTarget=item.replace("wood_bundle",itemId), poolTarget=pool.replace("workshop_b_fuel",poolId);
  const originals=new Map(await Promise.all([item,pool,building,"roguelike/data/generation/settlement_profiles.json"].map(async p=>[p,await readFile(resolve(root,p))])));
  const itemMeta=await stat(resolve(root,item));
  const editor=()=>page.locator('[data-testid="authoring"]:visible');
  const b=name=>page.getByRole("button",{name,exact:true}), eb=name=>editor().getByRole("button",{name,exact:true});
  const idle=()=>page.waitForFunction(()=>!document.querySelector(".status-dot.working"),null,{timeout:30000});
  async function confirmReviewed(path) {
    for(let attempt=0;attempt<4;attempt++) {
      await b("Confirm apply one file").click();await idle();
      const status=await page.locator("footer").innerText();
      if(status.includes(path)&&/Saved and byte-checked reopen:|Pool saved and reopened:/.test(status))return;
      // A background workspace sweep can own the host slot. BUSY performs no
      // write and clears the UI review; obtain fresh authority before retrying.
      assert.match(status,/BUSY/);receipt.apply_busy_retries=(receipt.apply_busy_retries||0)+1;
      await eb("Validate draft").click();await idle();
      assert(JSON.parse(await editor().getByTestId("draft-receipt").textContent()).review_token);
      await eb("Review & apply").click();
    }
    throw Error("Publication remained BUSY; no verified reopen");
  }
  const source=async()=>{await eb("Source").click();return editor().locator("textarea.source-editor").inputValue();};
  const open=async path=>{await page.getByLabel("Search ID, name or path").fill(path);await page.locator(`[data-asset="${path}"]`).click();await idle();};
  const shot=async name=>{const text=await page.locator("body").innerText();for(const s of ["A place to understand the world","Your world, under the lens"]) assert(!text.includes(s));await page.screenshot({path:resolve(output,name+".png")});};
  for(const path of ["roguelike/data/items/tools/tallow_torch.json","roguelike/data/items/weapons/binding_knife.json","roguelike/data/items/consumables/resonant_tincture.json"]) {
    const before=await readFile(resolve(root,path)); await open(path);
    // W5M admitted ordinary weapon common fields while preserving retained
    // essence/movesets. Light and effect-bearing tincture stay reference-only.
    assert.equal(await eb("Begin edit").isDisabled(),!path.includes("binding_knife"));
    assert.equal((await source()).replace(/\r\n/g,"\n"),before.toString().replace(/\r\n/g,"\n"));
    await b("Use binding").click(); assert((await page.getByTestId("item-editor").filter({visible:true}).innerText()).includes("Handler found"));
    if(path.includes("tincture")) assert((await page.getByTestId("item-editor").filter({visible:true}).innerText()).includes("do not consume"));
    assert.deepEqual(await readFile(resolve(root,path)),before);
  }
  receipt.checks.push("three advanced item sources open byte-exact read-only; actual dispatch found; declarative tincture effects explicitly unconsumed");
  await page.getByLabel("Search ID, name or path").fill(item);
  await page.locator(`[data-asset="${item}"]`).click(); await b("Close project").click(); await idle();
  assert.equal(await page.getByTestId("item-editor").filter({visible:true}).count(),0);
  await b("Open directory").click(); await idle();
  assert.equal(await page.getByTestId("item-editor").filter({visible:true}).count(),0);
  receipt.checks.push("closing/reopening the project during item lookup cannot restore a late item document");
  await open(building); await eb("Begin edit").click();
  const buildingText=await source(); await editor().locator("textarea.source-editor").fill(buildingText+" ");
  const parkedBuilding=await source();
  await page.getByLabel("Active layer").selectOption("specials"); await page.getByLabel("Placed record",{exact:true}).selectOption("3");
  await b("Open pool workshop_b_fuel").click(); await idle();
  await eb("Begin edit").click(); await page.getByLabel("Weight 1",{exact:true}).fill("2"); const parkedPool=await source();
  const started=performance.now(); await b("Open item wood_bundle").click(); await idle(); receipt.item_open_ms=Math.round(performance.now()-started);
  assert.equal((await source()).replace(/\r\n/g,"\n"),originals.get(item).toString().replace(/\r\n/g,"\n"));
  await b("References").click(); assert((await page.getByTestId("item-editor").filter({visible:true}).innerText()).includes("Potential tag match"));
  await b("Use binding").click(); assert((await page.getByTestId("item-editor").filter({visible:true}).innerText()).includes("Not applicable"));
  await b(/^Return to pool /).click();
  assert.equal(await page.evaluate(()=>document.activeElement?.getAttribute("data-pool-entry")),"0");
  assert.equal(await source(),parkedPool);
  await b("Open item wood_bundle").click(); await idle();
  assert.deepEqual(await readFile(resolve(root,item)),originals.get(item)); assert.equal((await stat(resolve(root,item))).mtimeMs,itemMeta.mtimeMs);
  await eb("Begin edit").click();
  const raw=await source(), closing=raw.lastIndexOf("}");
  await editor().locator("textarea.source-editor").fill(raw.slice(0,closing).trimEnd()+',\n "w3b_metadata": {"nested":[[null,true],["Retain authored wording",7]]}\n'+raw.slice(closing));
  const enriched=await source();
  // Returning from a linked document now preserves the selected item tab.
  await page.getByTestId("item-editor").filter({visible:true}).getByRole("button",{name:"Properties",exact:true}).click();
  const editStart=performance.now(); await page.getByLabel("Item weight (kg)").fill("1.75"); receipt.item_edit_ms=performance.now()-editStart;
  const changed=await source(); assert.equal(changed,enriched.replace('"weight": 1.0','"weight": 1.75'));
  await b("Undo item").click(); assert.equal(await source(),enriched); await b("Redo item").click(); assert.equal(await source(),changed);
  await page.getByLabel("Keyword tier 1",{exact:true}).fill("2"); const tiered=await source();
  assert.equal(tiered,changed.replace('"tier": 1','"tier": 2'));
  await shot("item-properties");
  await b(/^Return to pool /).click(); assert.equal(await source(),parkedPool);
  await b(/^Return to container /).click(); assert.equal(await source(),parkedBuilding);
  await page.locator('[data-document-tab$="/wood_bundle.json"]').click(); assert.equal(await source(),tiered);
  await editor().locator("textarea.source-editor").fill('{"id":');
  assert.equal(await page.getByLabel("Item weight (kg)").isDisabled(),true);
  assert.equal(await editor().locator("textarea.source-editor").inputValue(),'{"id":');
  await editor().locator("textarea.source-editor").fill(tiered);
  assert.equal(await b("Undo item").isDisabled(),true);
  await eb("Validate draft").click(); await eb("Source").click(); await editor().locator("textarea.source-editor").fill(tiered+" "); await idle();
  assert.equal(await editor().getByTestId("draft-verdict").count(),0); assert.equal(await eb("Review & apply").isDisabled(),true);
  await editor().locator("textarea.source-editor").fill(tiered);
  await eb("Save as new variant").click(); await editor().getByLabel("New variant ID").fill(itemId);
  const staged=await source(); await eb("Validate draft").click(); await idle();
  const validated=JSON.parse(await editor().getByTestId("draft-receipt").textContent());
  assert.equal(validated.valid,true,JSON.stringify(validated.diagnostics)); assert.equal(validated.factory.item_id,itemId); assert.equal(validated.factory.instance.weight,1.75);
  await b("Factory result").click(); await shot("item-factory");
  await eb("Review & apply").click(); await shot("item-review"); await confirmReviewed(itemTarget);
  const savedItem=await readFile(resolve(root,itemTarget)); assert.equal(savedItem.toString().replace(/\r\n/g,"\n"),staged.replace(/\r\n/g,"\n"));
  const savedRaw=JSON.parse(savedItem); assert.equal(savedRaw.weight,1.75); assert.equal(savedRaw.keywords[0].tier,2); assert.deepEqual(savedRaw.w3b_metadata,JSON.parse(tiered).w3b_metadata);
  await b(/^Return to pool /).click(); assert.equal(await source(),parkedPool);
  await page.getByLabel("Item ID 1",{exact:true}).selectOption(itemId);
  await eb("Save as new variant").click(); await editor().getByLabel("New variant ID").fill(poolId);
  await eb("Validate draft").click(); await idle(); await eb("Review & apply").click(); await confirmReviewed(poolTarget);
  const savedPool=await readFile(resolve(root,poolTarget)); assert.equal(JSON.parse(savedPool).items[0].item_id,itemId);
  await b(`Open item ${itemId}`).click(); await idle(); await b("References").click();
  assert((await page.getByTestId("item-editor").filter({visible:true}).innerText()).includes(poolId));
  await b("Factory result").click();await b("Validate and construct exact item").click();await idle();const factory=JSON.parse(await page.getByTestId("item-factory-receipt").textContent());
  assert.equal(factory.instance.weight,1.75); assert.equal(factory.item_id,itemId);
  receipt.item_chain={source:building,container_index:3,original_pool:pool,item:itemTarget,pool:poolTarget,factory};
  await shot("reopened-item-pool");
  await b(/^Return to pool /).click(); await b(/^Return to container /).click(); assert.equal(await source(),parkedBuilding);
  await page.getByLabel("Active layer").selectOption("specials"); await page.getByLabel("Placed record",{exact:true}).selectOption("3");
  await page.getByLabel("Loot pool 2",{exact:true}).selectOption(poolId); await b("Apply container edit").click();
  await b("Preview draft").click(); await idle();
  const sample=JSON.parse(await editor().getByTestId("draft-receipt").textContent()); assert.equal(sample.valid,true,JSON.stringify(sample.diagnostics));
  const container=sample.preview.containers.find(c=>c.x===sample.preview.origin[0]+2 && c.y===sample.preview.origin[1]+2);
  const observed=container.items.find(i=>i.item_id===itemId); assert.equal(observed.weight,1.75);
  receipt.observed_population={seed:sample.preview.seed,scene_seed:sample.preview.scene_seed,source:sample.preview.source,container,scope:"Unsaved deliberate structure fixture; actual population, no world selection claim"};
  await shot("observed-item-population"); await eb("Discard / Revert").click();
  receipt.checks.push("native container → pool → item; three retained drafts and separate histories; exact-span weight/tier edits; invalid raw freeze and late verdict suppression; item and pool variant diff/confirm/save/reopen; actual factory and seeded population observed");
  await writeFile(resolve(output,"item-variant.json"),savedItem); await writeFile(resolve(output,"pool-variant.json"),savedPool);
  receipt.variants=[itemTarget,poolTarget].map((path,i)=>({path,sha256:createHash("sha256").update(i?savedPool:savedItem).digest("hex")}));

  const ipc=async(command,args)=>{for(let attempt=0;attempt<20;attempt++){const result=await page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});if(result.error?.code!=="BUSY")return result;await page.waitForTimeout(100);}throw Error(`Host remained BUSY: ${command}`);};
  const opened=await ipc("open_document",{asset:itemTarget}), doc=opened.result;
  let checked=await ipc("validate_document",{token:doc.document_token,draft:doc.raw+" ",variantId:null}); assert(checked.result.valid);
  await writeFile(resolve(root,itemTarget),doc.raw+"\n");
  const conflict=await ipc("apply_document",{token:doc.document_token,reviewToken:checked.result.review_token,confirmed:true});
  assert.equal(conflict.error?.code,"EXTERNAL_MODIFICATION_CONFLICT"); await writeFile(resolve(root,itemTarget),savedItem);
  checked=await ipc("validate_document",{token:doc.document_token,draft:doc.raw+" ",variantId:null}); assert(checked.result.valid);
  const broken=await ipc("validate_document",{token:doc.document_token,draft:'{"id":',variantId:null}); assert.equal(broken.result.valid,false);
  assert.equal((await ipc("apply_document",{token:doc.document_token,reviewToken:checked.result.review_token,confirmed:true})).error?.code,"REVIEW_REQUIRED");
  const collisionId="w3b_concurrent", collisionPath=item.replace("wood_bundle",collisionId), collisionDraft=JSON.stringify({...savedRaw,id:collisionId});
  checked=await ipc("validate_document",{token:doc.document_token,draft:collisionDraft,variantId:collisionId}); assert(checked.result.valid);
  await writeFile(resolve(root,collisionPath),'{}');
  // Registered items bind catalogue freshness too: the new destination changes
  // dependencies, so admission refuses before the unchanged no-clobber writer.
  const collision=await ipc("apply_document",{token:doc.document_token,reviewToken:checked.result.review_token,confirmed:true});
  assert.equal(collision.error?.code,"SOURCE_CHANGED");receipt.concurrent_destination_refusal=collision.error.code;
  assert.equal(await readFile(resolve(root,collisionPath),"utf8"),'{}'); await unlink(resolve(root,collisionPath));
  for(const asset of ["roguelike/saves/x.json",".git/x.json","roguelike/engine/item_factory.py","workbench/docs/x.json","roguelike/data/items/components/../x.json","roguelike/data/items/components/x.json:ads"]){const r=await ipc("open_document",{asset});assert(r.error || r.ok===false);}
  const advanced=await ipc("open_document",{asset:"roguelike/data/items/tools/tallow_torch.json"});
  assert.equal((await ipc("validate_document",{token:advanced.result.document_token,draft:advanced.result.raw+" ",variantId:null})).error?.code,"READ_ONLY_ITEM");
  const linked=resolve(root,"roguelike/data/items/components/link"), held=resolve(root,"roguelike/data/items/components/held");
  assert(linked.startsWith(resolve(root)+"\\") && held.startsWith(resolve(root)+"\\"));
  await mkdir(linked); await writeFile(resolve(linked,"linked.json"),JSON.stringify({...savedRaw,id:"linked"}));
  await ipc("worker_request",{request:{op:"describe"}}); await rename(linked,held); await symlink(held,linked,"junction");
  try {assert.equal((await ipc("open_document",{asset:"roguelike/data/items/components/link/linked.json"})).error?.code,"PATH_ESCAPE");}
  finally {await unlink(linked); await rename(held,linked);}
  receipt.checks.push("native host rejects stale item review, external source conflict, concurrent destination creation, advanced-item publication, protected paths and internal junction traversal");
  for(const [path,bytes] of originals) assert.deepEqual(await readFile(resolve(root,path)),bytes,path);
  await b("Close project").click(); await idle(); await b("Open directory").click(); await idle();
  await open(poolTarget); await b(`Open item ${itemId}`).click(); await idle(); await b("Factory result").click();
  assert.equal(JSON.parse(await page.getByTestId("item-factory-receipt").textContent()).instance.weight,1.75);
  await shot("fresh-reopen");
  await page.setViewportSize({width:1100,height:740}); await shot("minimum-window");
  receipt.checks.push("fresh project reopen resolves new pool/item and actual instance; original files and selection profile unchanged; plain rendered chrome at full/minimum window");
}
