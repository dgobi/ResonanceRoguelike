import assert from "node:assert/strict";
import {readFile,writeFile,stat,realpath,rename,symlink,unlink,readdir} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";

export async function submapJourney(page,root,output,receipt,context) {
  assert.match(root.replaceAll("\\","/"),/\/workbench\/\.artifacts\/w4c\/data-fixture-\d+$/);
  assert.equal(await realpath(root),resolve(root));
  const asset="roguelike/docs/examples/g17_authored_creature_room.json", destination="roguelike/data/layouts/w4c_guard_room.json";
  const protectedPaths=[asset,asset.replace(".json",".access.json"),"roguelike/data/layouts/starting_lab.json","roguelike/data/generation/settlement_profiles.json"];
  const originals=new Map(await Promise.all(protectedPaths.map(async p=>[p,await readFile(resolve(root,p))])));
  const metadata=await stat(resolve(root,asset));
  const b=name=>page.getByRole("button",{name,exact:true});
  const editor=()=>page.locator('.authoring:visible');
  const eb=name=>editor().getByRole("button",{name,exact:true});
  const idle=()=>page.waitForFunction(()=>!document.querySelector('.busy-overlay'));
  const ipc=(command,args={})=>page.evaluate(async({command,args})=>{try{return await window.__TAURI_INTERNALS__.invoke(command,args);}catch(error){return {error};}},{command,args});
  async function open(path){await page.getByLabel("Search ID, name or path").fill(path);await page.locator(`[data-asset="${path}"]`).click();await idle();}
  async function source(){await eb("Source").click();return (await editor().locator('.source-editor').inputValue()).replace(/\r?\n/g,"\r\n");}
  async function canvas(){await b("Authored layout").click();await page.locator('[data-testid="layout-map"][data-ready="true"]').waitFor();}
  async function clickCell(x,y){await page.getByTestId("layout-map").scrollIntoViewIfNeeded();const p=await page.getByTestId("layout-map").evaluate((el,[x,y])=>{const c=JSON.parse(el.dataset.camera),r=el.getBoundingClientRect();return {x:r.x+c.x+(x+.5)*16*c.scale,y:r.y+c.y+(y+.5)*16*c.scale};},[x,y]);await page.mouse.click(p.x,p.y);}
  const shot=name=>page.screenshot({path:resolve(output,`${name}.png`)});
  await open(asset);assert.equal(await source(),originals.get(asset).toString());
  await b("Saved production preview").click();await page.getByTestId("placement-receipt").waitFor({state:"attached"});
  const example=JSON.parse(await page.getByTestId("placement-receipt").textContent());assert(example.access_source.sha256);assert.equal(example.actors[0].actual_count,1);
  await b("Close project").click();await idle();await b("Open directory").click();await idle();await open(asset);
  assert.equal(await source(),originals.get(asset).toString());assert.equal((await stat(resolve(root,asset))).mtimeMs,metadata.mtimeMs);
  // Park an independent editor draft through cancellation and publication.
  const item="roguelike/data/items/components/clay_pot.json", itemOriginal=await readFile(resolve(root,item));
  await open(item);await eb("Begin edit").click();await page.getByLabel("Item weight (kg)").fill("0.7");
  const parkedItem=await source();await b("Show structure").click();
  await eb("Begin edit").click();await canvas();
  assert(await b("Pencil · B").isDisabled());assert(await b("Fill · R").isDisabled());
  assert(!(await page.getByLabel("Placement creature").innerText()).includes("player"));
  await clickCell(7,2);await page.getByLabel("Creature source X").fill("6");await b("Apply creature edit").click();
  const moved=await source();assert.equal(moved,originals.get(asset).toString().replace('"x": 7, "y": 2, "creature_id"','"x": 6, "y": 2, "creature_id"'));
  await b("Undo canvas").click();assert.equal(await source(),originals.get(asset).toString());await b("Redo canvas").click();assert.equal(await source(),moved);
  await canvas();await page.getByLabel("Placement creature").selectOption("hollow_revenant");await b("Place creature").click();await clickCell(4,3);
  assert.equal(JSON.parse(await source()).special_tiles.length,4);await b("Delete creature").click();assert.equal(await source(),moved);
  await b("Undo canvas").click();assert.equal(JSON.parse(await source()).special_tiles.length,4);await b("Redo canvas").click();assert.equal(await source(),moved);
  await canvas();
  // Existing W2 coordinate path: two rectangular-map corners after app-local DPI,
  // zoom and pan. No desktop pointer or system display settings are used.
  const session=await context.newCDPSession(page);await session.send("Emulation.setDeviceMetricsOverride",{width:2560,height:1440,deviceScaleFactor:1.5,mobile:false});
  await b("Fit layout").click();await b("Layout zoom out").click();
  await page.getByTestId("layout-map").scrollIntoViewIfNeeded();const bounds=await page.getByTestId("layout-map").boundingBox();
  await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);await page.keyboard.down("Alt");await page.mouse.down();await page.mouse.move(bounds.x+bounds.width/2+12,bounds.y+bounds.height/2+9);await page.mouse.up();await page.keyboard.up("Alt");
  for(const [x,y] of [[0,0],[10,6]]){await clickCell(x,y);assert.match(await page.getByTestId("layout-selected").innerText(),new RegExp(`\\(${x}, ${y}\\)`));}
  await session.send("Emulation.clearDeviceMetricsOverride");await session.detach();await b("Fit layout").click();
  await clickCell(6,2);await page.getByLabel("Creature source X").fill("0");await page.getByLabel("Creature source Y").fill("0");await b("Apply creature edit").click();
  const invalid=await source();await b("Preview draft").click();await idle();assert.match(await page.getByTestId("draft-verdict").innerText(),/Draft rejected/);assert(await eb("Apply variant").isDisabled());
  await eb("Problems").click();assert.match(await editor().innerText(),/PRODUCTION_PLACEMENT/);await eb("Locate cell / record").first().click();
  await page.setViewportSize({width:1100,height:740});await shot("submap-minimum-problems");await page.setViewportSize({width:2560,height:1440});
  await b("Undo canvas").click();assert.equal(await source(),moved);
  await editor().locator('.source-editor').fill('{"id":');assert(await b("Place creature").isDisabled());assert.equal(await page.getByTestId("draft-verdict").count(),0);
  await editor().locator('.source-editor').fill(moved);assert(await b("Undo canvas").isDisabled());
  // In-flight evidence cannot survive another raw edit.
  await b("Preview draft").click();await editor().locator('.source-editor').fill(moved+" ");await idle();assert.equal(await page.getByTestId("draft-verdict").count(),0);
  await editor().locator('.source-editor').fill(moved);
  await eb("Save as new variant").click();await page.getByLabel("New variant ID").fill("w4c_guard_room");
  const finalDraft=await source();
  // Hold *real completed host responses* at the renderer boundary. This is a
  // frontend late-handler test; Rust's pre-install boundary is covered by the
  // deterministic host helpers, without adding privileged test IPC commands.
  await page.evaluate(()=>{
    const original=window.fetch;
    window.w4dGates=[];
    window.fetch=async function(input,init) {
      if(!String(input).endsWith("/validate_document") || window.w4dGates.length>=2) return original.call(this,input,init);
      const gate={args:JSON.parse(init.body)};window.w4dGates.push(gate);
      const response=await original.call(this,input,init);gate.response=await response.clone().json();
      await new Promise(resolve=>{gate.release=resolve;});gate.delivered=true;
      return response;
    };
    window.w4dRestore=()=>{window.fetch=original;};
  });
  await b("Preview draft").click();await page.waitForFunction(()=>window.w4dGates[0]?.response);
  const obsolete=await page.evaluate(()=>({args:window.w4dGates[0].args,result:window.w4dGates[0].response.result}));
  assert(obsolete.result.review_token);
  await b("Cancel authoring request").click();await idle();
  assert.equal(await source(),finalDraft);assert.equal(await page.getByTestId("draft-verdict").count(),0);
  assert(await eb("Apply variant").isDisabled());
  assert.equal((await ipc("apply_document",{token:obsolete.args.token,reviewToken:obsolete.result.review_token,confirmed:true})).error?.code,"REVIEW_REQUIRED");
  await b("Preview draft").click();await page.waitForFunction(()=>window.w4dGates[1]?.response);
  await page.evaluate(()=>window.w4dGates[0].release());
  await page.waitForFunction(()=>window.w4dGates[0].delivered);
  // Flush renderer work deterministically; no timing sleep.
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  assert(await b("Cancel authoring request").isVisible());
  assert.equal(await page.getByTestId("draft-verdict").count(),0);
  await page.evaluate(()=>{window.w4dGates[1].release();window.w4dRestore();});await idle();
  receipt.checks.push("W4D real completed validation held at renderer; accepted cancel revoked host token, exact draft retained, old completion could not restore verdict or clear newer preview; fresh production result accepted");
  let verdict=JSON.parse(await page.getByTestId("draft-receipt").textContent());assert(verdict.valid);assert(verdict.review_token);
  let evidence=JSON.parse(await page.getByTestId("placement-receipt").textContent());
  assert.deepEqual(evidence.actors[0].source_xy,[6,2]);assert.deepEqual(evidence.actors[0].xy,[41,20]);assert.equal(evidence.actors[0].actual_count,1);assert.deepEqual(evidence.actors[0].actor_classes,["Actor"]);
  assert.equal(evidence.draft_sha256,createHash("sha256").update(finalDraft).digest("hex"));await shot("submap-instantiated");
  // An observed sidecar/dependency change invalidates the same host evidence;
  // the sidecar is read-only context, never a second publication output.
  const sidecar=resolve(root,asset.replace(".json",".access.json"));const sidecarBytes=await readFile(sidecar);
  await writeFile(sidecar,sidecarBytes.toString()+" ");await page.waitForFunction(()=>!document.querySelector('[data-testid="draft-verdict"]'),null,{timeout:10000});
  await writeFile(sidecar,sidecarBytes);await b("Preview draft").click();await idle();
  await eb("Diff").click();assert((await page.getByTestId("source-diff").innerText()).includes("w4c_guard_room"));
  await eb("Apply variant").click();await b("Confirm apply one file").click();await idle();
  const saved=await readFile(resolve(root,destination));assert.equal(saved.toString(),finalDraft);assert.equal(await source(),finalDraft);
  await b("Preview draft").click();await idle();evidence=JSON.parse(await page.getByTestId("placement-receipt").textContent());assert.equal(evidence.source_sha256,createHash("sha256").update(saved).digest("hex"));
  receipt.placement=evidence;receipt.variant={path:destination,sha256:evidence.source_sha256};
  await page.locator('[data-document-tab$="/clay_pot.json"]').click();assert.equal(await source(),parkedItem);
  await eb("Discard / Revert").click();await b("Show structure").click();
  assert.deepEqual(await readFile(resolve(root,item)),itemOriginal);
  receipt.checks.push("W4D parked item draft survived submap edits, cancellation, fresh preview and publication byte-for-byte; source item unchanged");
  await canvas();await page.getByLabel("Placed record",{exact:true}).selectOption("0");await shot("submap-source");
  receipt.checks.push("read-only example → exact shared marker draft; add/move/delete, undo/redo, raw freeze, stale job rejection, source/scene coordinates, real Actor, minimum-window diagnostics, sidecar invalidation, new-file publish and byte-exact reopen");
  // Exercise native host capabilities directly after completing the visible journey.
  const doc=(await ipc("open_document",{asset:destination})).result;
  const draftFor=id=>JSON.stringify({...JSON.parse(doc.raw),id});
  const validate=(id="w4c_safety")=>ipc("validate_document",{token:doc.document_token,draft:draftFor(id),variantId:id,seed:20261026});
  const apply=check=>ipc("apply_document",{token:doc.document_token,reviewToken:check.result.review_token,confirmed:true});
  let checked=await validate();assert(checked.result.valid);
  assert.equal((await ipc("validate_document",{token:"forged",draft:draftFor("x"),variantId:"x"})).error?.code,"UNKNOWN_DOCUMENT");
  assert.equal((await ipc("apply_document",{token:doc.document_token,reviewToken:"forged",confirmed:true})).error?.code,"REVIEW_REQUIRED");
  await ipc("invalidate_document",{token:doc.document_token});assert.equal((await apply(checked)).error?.code,"REVIEW_REQUIRED");
  checked=await validate();await writeFile(resolve(root,destination),doc.raw+" ");assert.equal((await apply(checked)).error?.code,"EXTERNAL_MODIFICATION_CONFLICT");await writeFile(resolve(root,destination),saved);
  const definition=resolve(root,"roguelike/data/entities/creatures/hollow_revenant.json"),defBytes=await readFile(definition);
  checked=await validate();await writeFile(definition,defBytes.toString()+" ");assert.equal((await apply(checked)).error?.code,"SOURCE_CHANGED");await writeFile(definition,defBytes);
  checked=await validate();await ipc("validate_document",{token:doc.document_token,draft:'{"id":',variantId:null});assert.equal((await apply(checked)).error?.code,"REVIEW_REQUIRED");
  checked=await validate("w4c_collision");const collision=resolve(root,"roguelike/data/layouts/w4c_collision.json");await writeFile(collision,"{}");assert(["SOURCE_CHANGED","VARIANT_EXISTS"].includes((await apply(checked)).error?.code));await unlink(collision);
  const ro=(await ipc("open_document",{asset:"roguelike/data/layouts/starting_lab.json"})).result;
  assert.equal((await ipc("validate_document",{token:ro.document_token,draft:draftFor("promoted"),variantId:"promoted"})).error?.code,"READ_ONLY_LAYOUT");
  for(const asset of ["roguelike/saves/x.json","roguelike/data/layouts/../x.json","roguelike/data/layouts/x.json:ads","roguelike/docs/examples/other.json"])
    assert((await ipc("open_document",{asset})).error);
  const layouts=resolve(root,"roguelike/data/layouts"),held=resolve(root,"roguelike/data/layouts-held");assert(layouts.startsWith(resolve(root)+"\\")&&held.startsWith(resolve(root)+"\\"));
  await rename(layouts,held);await symlink(held,layouts,"junction");
  try{assert.equal((await ipc("open_document",{asset:destination})).error?.code,"PATH_ESCAPE");}finally{await unlink(layouts);await rename(held,layouts);}
  assert(!(await readdir(layouts)).some(p=>p.startsWith('.w1-')));
  for(const [path,bytes] of originals)assert.deepEqual(await readFile(resolve(root,path)),bytes,path);
  receipt.checks.push("native trusted writer rejects stale/forged/revoked reviews, external source and creature changes, destination races, starting_lab promotion, traversal/ADS/docs writes and layout junction; originals unchanged");
  await b("Close project").click();await idle();await b("Open directory").click();await idle();await open(destination);assert.equal(await source(),finalDraft);
  await b("Preview draft").click();await idle();assert.equal(JSON.parse(await page.getByTestId("placement-receipt").textContent()).actors[0].actual_count,1);
  receipt.checks.push("project close/reopen reproduces exact saved variant and production actor with no sidecar output or campaign selection");
}
