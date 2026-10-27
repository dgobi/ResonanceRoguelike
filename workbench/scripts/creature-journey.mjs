import assert from "node:assert/strict";
import {readFile,writeFile,realpath,mkdir,rename,symlink,unlink,readdir} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";

export async function creatureJourney(page,root,output,receipt) {
  assert.match(root.replaceAll("\\","/"), /\/workbench\/\.artifacts\/w4a\/data-fixture-\d+$/);
  assert.equal(await realpath(root),resolve(root));
  const creature="roguelike/data/entities/creatures/hollow_revenant.json", variantId="hollow_revenant_w4a", target=creature.replace("hollow_revenant.json",variantId+".json");
  const building="roguelike/data/buildings/commercial/workshop_b.json", pool="roguelike/data/loot_pools/workshop_b_fuel.json", item="roguelike/data/items/components/clay_pot.json", recipe="roguelike/data/recipes/bile_coating.json";
  const originals=new Map(await Promise.all([creature,building,pool,item,recipe,"roguelike/data/layouts/w4a_reference_room.json","roguelike/data/generation/settlement_profiles.json","roguelike/data/resonance_spawns.json"].map(async p=>[p,await readFile(resolve(root,p))])));
  const editor=()=>page.locator('[data-testid="authoring"]:visible'), panel=()=>page.locator('[data-testid="creature-editor"]:visible');
  const b=name=>page.getByRole("button",{name,exact:true}), eb=name=>editor().getByRole("button",{name,exact:true});
  const idle=()=>page.waitForFunction(()=>!document.querySelector(".status-dot.working"),null,{timeout:45000});
  const source=async()=>{await eb("Source").click();return editor().locator("textarea.source-editor").inputValue();};
  const open=async path=>{await page.getByLabel("Category / route").selectOption("");await page.getByLabel("Search ID, name or path").fill(path);await page.locator(`[data-asset="${path}"]`).click();await idle();};
  const shot=async name=>{const text=await page.locator("body").innerText();for(const s of ["A place to understand the world","Your world, under the lens"]) assert(!text.includes(s));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));await page.screenshot({path:resolve(output,name+".png")});};
  const ipc=(command,args)=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
  await b("Creatures").click();assert.equal(await page.locator(".asset-list .asset").count(),13);
  for(const path of [creature.replace("hollow_revenant","hollow_knight"),creature.replace("hollow_revenant","vine_network"),"roguelike/data/entities/player.json"]) {
    await open(path);assert(await eb("Begin edit").isDisabled());assert.equal(await panel().getByLabel("Effective HP").count(),0);
    assert.equal((await source()).replace(/\r\n/g,"\n"),(await readFile(resolve(root,path),"utf8")).replace(/\r\n/g,"\n"));
  }
  await page.getByLabel("Search ID, name or path").fill(creature);await page.locator(`[data-asset="${creature}"]`).click();await b("Close project").click();await idle();assert.equal(await panel().count(),0);
  await b("Open directory").click();await idle();assert.equal(await panel().count(),0);
  receipt.checks.push("13 loaded non-player creature records; player, special-ability knight and advanced vine read-only; byte-exact source; close during lookup suppresses late result");
  // Park one draft in every existing family, preserving separate document tokens/history.
  await open(building);await eb("Begin edit").click();await source();await editor().locator("textarea.source-editor").fill((await source())+" ");const parkedBuilding=await source();
  await page.getByLabel("Active layer").selectOption("specials");await page.getByLabel("Placed record",{exact:true}).selectOption("3");
  await b("Open pool workshop_b_fuel").click();await idle();await eb("Begin edit").click();await page.getByLabel("Weight 1",{exact:true}).fill("2");const parkedPool=await source();
  await open(item);await eb("Begin edit").click();await page.getByLabel("Item weight (kg)").fill("0.7");const parkedItem=await source();
  await open(recipe);await eb("Begin edit").click();await page.getByLabel("Recipe name",{exact:true}).fill("Parked recipe draft");const parkedRecipe=await source();
  const start=performance.now();await open(creature);receipt.creature_open_ms=Math.round(performance.now()-start);
  const original=await source();assert.equal(original.replace(/\r\n/g,"\n"),originals.get(creature).toString().replace(/\r\n/g,"\n"));
  await b("Direct layout references").click();assert((await panel().innerText()).includes("Declared direct authored-submap reference"));
  await b("Inspect layout w4a_reference_room").click();await idle();assert((await panel().innerText()).includes('"creature_id": "hollow_revenant"'));
  await b("Read-only fields").click();assert((await panel().innerText()).includes("LookMode resolves descriptions"));
  await b("Supported fields").click();await eb("Begin edit").click();await page.getByLabel("Creature name").fill("Hollow Revenant W4A");
  const renamed=await source();await page.getByLabel("Effective HP").fill("19");const changed=await source();
  assert.equal(changed,renamed.replace('"base_hp": 14','"base_hp": 19').replace('"max_hp": 14','"max_hp": 19'));
  await b("Undo creature").click();assert.equal(await source(),renamed);await b("Redo creature").click();assert.equal(await source(),changed);
  await shot("creature-properties");
  await editor().locator("textarea.source-editor").fill('{"id":');assert(await page.getByLabel("Effective HP").isDisabled());
  await editor().locator("textarea.source-editor").fill(changed);assert(await b("Undo creature").isDisabled());
  await editor().locator("textarea.source-editor").fill(changed.replace('"ai_type": "wandering"','"ai_type": "ambush"'));
  await eb("Validate draft").click();await idle();assert.equal(JSON.parse(await editor().getByTestId("draft-receipt").textContent()).valid,false);assert(await eb("Apply variant").isDisabled());
  await source();await editor().locator("textarea.source-editor").fill(changed);
  await eb("Validate draft").click();await eb("Source").click();await editor().locator("textarea.source-editor").fill(changed+" ");await idle();assert.equal(await editor().getByTestId("draft-verdict").count(),0);
  await editor().locator("textarea.source-editor").fill(changed);await eb("Save as new variant").click();await editor().getByLabel("New variant ID").fill(variantId);const staged=await source();
  await eb("Validate draft").click();await idle();let validated=JSON.parse(await editor().getByTestId("draft-receipt").textContent());assert(validated.valid,JSON.stringify(validated));
  await b("Factory result").click();let factory=JSON.parse(await page.getByTestId("creature-factory-receipt").textContent());assert.equal(factory.instance.fighter.max_hp,19);assert.equal(factory.instance.fighter.hp,19);
  await shot("creature-factory");
  // A real external dependency edit clears current UI evidence and review.
  const dep=resolve(root,item), depBytes=await readFile(dep);await writeFile(dep,depBytes.toString()+" ");
  await page.waitForFunction(()=>!document.querySelector('[data-testid="creature-factory-receipt"]'),null,{timeout:12000});assert(await eb("Apply variant").isDisabled());await writeFile(dep,depBytes);
  await b("Validate and construct exact creature").click();await idle();assert.equal(JSON.parse(await page.getByTestId("creature-factory-receipt").textContent()).instance.fighter.max_hp,19);
  await eb("Apply variant").click();assert((await page.getByRole("dialog").innerText()).includes("does not join worldgen pools"));await b("Confirm apply one file").click();await idle();
  const saved=await readFile(resolve(root,target));assert.equal(saved.toString().replace(/\r\n/g,"\n"),staged.replace(/\r\n/g,"\n"));
  await b("Factory result").click();await b("Validate and construct exact creature").click();await idle();factory=JSON.parse(await page.getByTestId("creature-factory-receipt").textContent());
  assert.equal(factory.source_sha256,createHash("sha256").update(saved).digest("hex"));assert.equal(factory.creature_id,variantId);assert.equal(factory.instance.name,"Hollow Revenant W4A");
  assert.deepEqual(JSON.parse(saved).w4a_metadata,JSON.parse(original).w4a_metadata);
  receipt.creature_factory=factory;receipt.variant={path:target,sha256:factory.source_sha256};await writeFile(resolve(output,"creature-variant.json"),saved);await shot("creature-reopened");
  await b("Direct layout references").click();assert((await panel().innerText()).includes("No direct authored-submap references"));
  await page.locator('[data-document-tab$="/bile_coating.json"]').click();assert.equal(await source(),parkedRecipe);await eb("Discard / Revert").click();
  await page.locator('[data-document-tab$="/clay_pot.json"]').click();assert.equal(await source(),parkedItem);await eb("Discard / Revert").click();
  await b("Show pool workshop_b_fuel").click();assert.equal(await source(),parkedPool);await eb("Discard / Revert").click();await b("Return to structure").click();assert.equal(await source(),parkedBuilding);await eb("Discard / Revert").click();
  receipt.checks.push("five independent drafts; actual reference source without replacing structure draft; two-span effective HP/name edits and unknown metadata; undo/redo/raw freeze; invalid complex edits denied; stale async and changed-dependency evidence revoked; reviewed no-clobber variant and exact reopened real factory values");
  let opened=await ipc("open_document",{asset:target}), doc=opened.result;
  const draftFor=id=>JSON.stringify({...JSON.parse(doc.raw),id});
  const validate=async(id="w4a_safety")=>ipc("validate_document",{token:doc.document_token,draft:draftFor(id),variantId:id});
  const apply=async check=>ipc("apply_document",{token:doc.document_token,reviewToken:check.result.review_token,confirmed:true});
  const unchanged=await ipc("validate_document",{token:doc.document_token,draft:doc.raw,variantId:null});assert(unchanged.result.valid);assert(!unchanged.result.review_token);
  let checked=await validate();assert(checked.result.valid);
  assert.equal((await ipc("apply_document",{token:doc.document_token,reviewToken:checked.result.review_token+"forged",confirmed:true})).error?.code,"REVIEW_REQUIRED");
  assert.equal((await ipc("validate_document",{token:"forged",draft:draftFor("x"),variantId:"x"})).error?.code,"UNKNOWN_DOCUMENT");
  await writeFile(resolve(root,target),doc.raw+"\n");assert.equal((await apply(checked)).error?.code,"EXTERNAL_MODIFICATION_CONFLICT");await writeFile(resolve(root,target),saved);
  checked=await validate();await writeFile(dep,depBytes.toString()+" ");assert.equal((await apply(checked)).error?.code,"SOURCE_CHANGED");await writeFile(dep,depBytes);
  checked=await validate();const bad=await ipc("validate_document",{token:doc.document_token,draft:'{"id":',variantId:null});assert.equal(bad.result.valid,false);assert.equal((await apply(checked)).error?.code,"REVIEW_REQUIRED");
  checked=await validate("w4a_collision");const collision=resolve(root,"roguelike/data/entities/creatures/w4a_collision.json");await writeFile(collision,"{}");assert(["SOURCE_CHANGED","VARIANT_EXISTS"].includes((await apply(checked)).error?.code));assert.equal(await readFile(collision,"utf8"),"{}");await unlink(collision);
  for(const path of ["roguelike/data/entities/player.json",creature.replace("hollow_revenant","hollow_knight")]) {
    const ro=await ipc("open_document",{asset:path});assert.equal((await ipc("validate_document",{token:ro.result.document_token,draft:draftFor("promoted"),variantId:"promoted"})).error?.code,"READ_ONLY_CREATURE");
  }
  for(const path of ["roguelike/saves/x.json","roguelike/data/entities/../x.json","roguelike/data/entities/creatures/x.json:ads",".git/x.json"]) assert((await ipc("open_document",{asset:path})).error);
  const linked=resolve(root,"roguelike/data/entities/creatures/link"), held=resolve(root,"roguelike/data/entities/creatures/held");assert(linked.startsWith(resolve(root)+"\\")&&held.startsWith(resolve(root)+"\\"));
  await mkdir(linked);await writeFile(resolve(linked,"linked.json"),draftFor("linked"));await ipc("worker_request",{request:{op:"describe"}});await rename(linked,held);await symlink(held,linked,"junction");
  try {assert.equal((await ipc("open_document",{asset:"roguelike/data/entities/creatures/link/linked.json"})).error?.code,"PATH_ESCAPE");} finally {await unlink(linked);await rename(held,linked);}
  assert(!(await readdir(resolve(root,"roguelike/data/entities/creatures"))).some(p=>p.startsWith(".w1-")));
  for(const [path,bytes] of originals) assert.deepEqual(await readFile(resolve(root,path)),bytes,path);
  receipt.checks.push("host denies forged document/review, stale external source/dependency, revoked review, concurrent destination, player/advanced raw promotion, protected/traversal/ADS paths and junction; originals and spawn/selection files byte-identical");
  await b("Close project").click();await idle();await b("Open directory").click();await idle();await open(target);await b("Factory result").click();await b("Validate and construct exact creature").click();await idle();
  assert.equal(JSON.parse(await page.getByTestId("creature-factory-receipt").textContent()).source_sha256,receipt.variant.sha256);
  await page.setViewportSize({width:1100,height:740});await shot("creature-minimum-window");
  receipt.checks.push("fresh project exact variant reopen and factory result; full/minimum native captures and plain rendered chrome");
}
