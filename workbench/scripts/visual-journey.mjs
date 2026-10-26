import assert from "node:assert/strict";
import { readFile, writeFile, stat, realpath } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";

export async function visualJourney(page, root, output, receipt, context) {
  assert.match(
    root.replaceAll("\\", "/"),
    /\/workbench\/\.artifacts\/w2\/data-fixture-\d+$/,
  );
  assert.equal(await realpath(root), resolve(root));
  const asset = "roguelike/data/buildings/commercial/apothecary_a.json",
    path = resolve(root, asset),
    before = await readFile(path),
    meta = await stat(path);
  const profilePath = resolve(
      root,
      "roguelike/data/generation/settlement_profiles.json",
    ),
    profiles = await readFile(profilePath);
  const button = (name) => page.getByRole("button", { name, exact: true });
  async function idle() {
    await page.waitForFunction(() => !document.querySelector(".busy-overlay"));
  }
  async function source() {
    await button("Source").click();
    const text = await page.locator("#draft-json").inputValue();
    return before.includes(Buffer.from("\r\n"))
      ? text.replace(/\r?\n/g, "\r\n")
      : text;
  }
  async function canvas() {
    await button("Authored layout").click();
    await page
      .locator('[data-testid="layout-map"][data-ready="true"]')
      .waitFor();
  }
  async function point(x, y) {
    return page.getByTestId("layout-map").evaluate(
      (el, [x, y]) => {
        const c = JSON.parse(el.dataset.camera),
          r = el.getBoundingClientRect();
        return {
          x: r.x + c.x + (x + 0.5) * 16 * c.scale,
          y: r.y + c.y + (y + 0.5) * 16 * c.scale,
        };
      },
      [x, y],
    );
  }
  async function clickCell(x, y) {
    await page.getByTestId("layout-map").scrollIntoViewIfNeeded();
    const p = await point(x, y);
    await page.mouse.click(p.x, p.y);
  }
  async function stroke(a, b) {
    await page.getByTestId("layout-map").scrollIntoViewIfNeeded();
    const p = await point(...a),
      q = await point(...b);
    await page.mouse.move(p.x, p.y);
    await page.mouse.down();
    await page.mouse.move(q.x, q.y, { steps: 3 });
    await page.mouse.up();
  }
  await page.getByLabel("Search ID, name or path").fill(asset);
  await page.locator(`[data-asset="${asset}"]`).click();
  await idle();
  await canvas();
  assert.equal(
    (await source()).replace(/\r\n/g, "\n"),
    before.toString().replace(/\r\n/g, "\n"),
  );
  await button("Preview draft").click();
  await idle();
  await page
    .getByTestId("preview-provenance")
    .filter({ hasText: "Current unsaved draft" })
    .waitFor();
  assert.deepEqual(await readFile(path), before);
  assert.equal((await stat(path)).mtimeMs, meta.mtimeMs);
  receipt.checks.push(
    "clean canvas/raw/unsaved production preview leaves original bytes and mtime unchanged",
  );
  await button("Begin edit").click();
  const enriched = JSON.parse(await source());
  enriched.unknown_metadata = {
    nested: [
      [null, "keep"],
      [true, 3],
    ],
  };
  await page.locator("#draft-json").fill(JSON.stringify(enriched, null, 2));
  const rich = await source();
  await canvas();
  await page.getByLabel("Terrain brush").selectOption("w");
  await button("Pencil · B").click();
  const began = performance.now();
  await stroke([2, 3], [4, 3]);
  receipt.visual_stroke_wall_ms = performance.now() - began;
  const terrain = await source();
  assert.equal(JSON.parse(terrain).layers[3], "#.www.....#");
  await button("Undo canvas").click();
  assert.equal(await source(), rich);
  await button("Redo canvas").click();
  assert.equal(await source(), terrain);
  await canvas();
  await page.getByLabel("Active layer").selectOption("decor");
  await page.getByLabel("Decor brush").selectOption("dried_herbs");
  await button("Fill · R").click();
  await stroke([3, 2], [4, 2]);
  const furnished = await source();
  assert.equal(JSON.parse(furnished).decor_layer[2][3], "dried_herbs");
  assert.equal(JSON.parse(furnished).decor_layer[2][4], "dried_herbs");
  await button("Undo canvas").click();
  assert.equal(await source(), terrain);
  await button("Redo canvas").click();
  assert.equal(await source(), furnished);
  await canvas();
  await page.getByLabel("Show decor", { exact: true }).uncheck();
  assert.equal(await button("Pencil · B").isDisabled(), true);
  await page.getByLabel("Show decor", { exact: true }).check();
  await page.getByLabel("Active layer").selectOption("specials");
  await button("Select · V").click();
  await clickCell(1, 1);
  await page.getByLabel("Container X", { exact: true }).fill("2");
  await page
    .getByLabel("Container decor", { exact: true })
    .selectOption("crate");
  await page
    .getByLabel("Loot pool 1", { exact: true })
    .selectOption("workshop_b_fuel");
  await button("Apply container edit").click();
  const moved = await source(),
    v = JSON.parse(moved);
  assert.equal(v.special_tiles[0].x, 2);
  assert.equal(v.special_tiles[0].decor_id, "crate");
  assert.equal(v.placement.targets[2].x, 2);
  assert.deepEqual(v.special_tiles.slice(1), enriched.special_tiles.slice(1));
  assert.deepEqual(v.unknown_metadata, enriched.unknown_metadata);
  await button("Undo canvas").click();
  assert.equal(await source(), furnished);
  await button("Redo canvas").click();
  assert.equal(await source(), moved);
  receipt.checks.push(
    "native continuous terrain stroke, decor rectangle fill and container move/ref edits share raw draft; each undo/redo is exact; linked target follows explicitly",
  );
  // Keyboard shortcuts only belong to the canvas; focused text keeps normal undo.
  const toolBefore = await page.locator(".tool-buttons .active").innerText();
  const rawBefore = await page.locator("#draft-json").inputValue();
  await page.locator("#draft-json").press("b");
  assert.notEqual(await page.locator("#draft-json").inputValue(), rawBefore);
  assert.equal(
    await page.locator(".tool-buttons .active").innerText(),
    toolBefore,
  );
  await page.locator("#draft-json").press("Control+z");
  assert.equal(await page.locator("#draft-json").inputValue(), rawBefore);
  await page.locator("#draft-json").fill(moved);
  assert.equal(await button("Undo canvas").isDisabled(), true);
  await canvas();
  await page.getByLabel("Active layer").selectOption("terrain");
  await button("Select · V").click();
  await page.locator('[data-testid="layout-map"] canvas').press("b");
  assert.equal(
    await page.locator(".tool-buttons .active").innerText(),
    "Pencil · B",
  );
  await page.locator('[data-testid="layout-map"] canvas').press("v");
  assert.equal(
    await page.locator(".tool-buttons .active").innerText(),
    "Select · V",
  );
  await button("Layout zoom in").click();
  await page.getByTestId("layout-map").scrollIntoViewIfNeeded();
  let p = await point(5, 4);
  await page.keyboard.down("Alt");
  await page.mouse.move(p.x, p.y);
  await page.mouse.down();
  await page.mouse.move(p.x + 21, p.y + 13);
  await page.mouse.up();
  await page.keyboard.up("Alt");
  for (const [x, y] of [
    [0, 0],
    [10, 7],
  ]) {
    await clickCell(x, y);
    assert.equal(
      await page.getByTestId("layout-selected").innerText(),
      `Source cell (${x}, ${y})`,
    );
  }
  const cdp = await context.newCDPSession(page);
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 2560,
    height: 1440,
    deviceScaleFactor: 1.5,
    mobile: false,
  });
  await button("Fit layout").click();
  receipt.visual_zoom_frame_intervals_ms = await page.evaluate(async () => {
    const canvas = document.querySelector('[data-testid="layout-map"] canvas'),
      times = [];
    let last = await new Promise(requestAnimationFrame);
    for (let i = 0; i < 120; i++) {
      const now = await new Promise(requestAnimationFrame);
      times.push(now - last);
      last = now;
      const r = canvas.getBoundingClientRect();
      canvas.dispatchEvent(
        new WheelEvent("wheel", {
          deltaY: i % 2 ? 10 : -10,
          clientX: r.x + r.width / 2,
          clientY: r.y + r.height / 2,
          cancelable: true,
        }),
      );
    }
    times.shift();
    times.sort((a, b) => a - b);
    return {
      median: times[59],
      p95: times[113],
      max: Math.max(...times),
      count: times.length,
    };
  });
  await clickCell(10, 7);
  assert.match(await page.getByTestId("layout-selected").innerText(), /10, 7/);
  receipt.visual_device_scale = await page.evaluate(() => devicePixelRatio);
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 2560,
    height: 1440,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await button("Fit layout").click();
  receipt.checks.push(
    "native pointer mapping at both edges after zoom/pan and WebView scale 1.5; raw edit clears canvas history",
  );
  await button("Save as new variant").click();
  await page.getByLabel("New variant ID").fill("apothecary_w2_furnished");
  const finalText = await source();
  await button("Preview draft").click();
  receipt.visual_frames_during_first_300ms = await page.evaluate(async () => {
    let n = 0;
    const start = performance.now();
    while (performance.now() - start < 300) {
      await new Promise(requestAnimationFrame);
      n++;
    }
    return n;
  });
  await idle();
  await page
    .getByTestId("preview-provenance")
    .filter({ hasText: "Current unsaved draft" })
    .waitFor();
  const validation = JSON.parse(
    await page.getByTestId("draft-receipt").textContent(),
  );
  assert.equal(validation.valid, true);
  assert.equal(
    validation.draft_sha256,
    createHash("sha256").update(finalText).digest("hex"),
  );
  const preview = validation.preview,
    [ox, oy] = preview.origin;
  assert.equal(preview.terrain[oy + 3][ox + 3], "worn_stone");
  assert.ok(
    preview.decor.some(
      (d) => d.x === ox + 3 && d.y === oy + 2 && d.id === "dried_herbs",
    ),
  );
  const container = preview.containers.find(
    (c) => c.x === ox + 2 && c.y === oy + 1,
  );
  assert.equal(container.decor_id, "crate");
  assert.deepEqual(
    container.items.map((i) => i.item_id),
    ["wood_bundle"],
  );
  receipt.visual_preview = {
    draft_sha256: validation.draft_sha256,
    seed: preview.seed,
    scene_seed: preview.scene_seed,
    origin: preview.origin,
    generation_revision: preview.generation_revision,
    candidate_sha256: preview.candidate_sha256,
    terrain_sha256: preview.terrain_sha256,
    generation_ms: preview.elapsed_ms,
    container,
    access: preview.access,
  };
  await page.screenshot({ path: resolve(output, "draft-production.png") });
  await canvas();
  await clickCell(2, 1);
  await page.screenshot({ path: resolve(output, "authored-layout.png") });
  await button("Diff").click();
  assert.match(
    await page.getByTestId("source-diff").innerText(),
    /apothecary_w2_furnished/,
  );
  await button("Review & apply").click();
  await page
    .getByRole("dialog", { name: "Confirm single-file apply" })
    .waitFor();
  await page.screenshot({ path: resolve(output, "review.png") });
  await button("Confirm apply one file").click();
  await button("Begin edit").waitFor({ timeout: 60000 });
  await idle();
  const variantPath = resolve(
      root,
      "roguelike/data/buildings/commercial/apothecary_w2_furnished.json",
    ),
    saved = await readFile(variantPath);
  assert.equal(saved.toString(), finalText);
  assert.deepEqual(await readFile(path), before);
  assert.deepEqual(await readFile(profilePath), profiles);
  assert.equal((await stat(path)).mtimeMs, meta.mtimeMs);
  assert.equal(JSON.parse(await source()).id, "apothecary_w2_furnished");
  await canvas();
  await button("Preview draft").click();
  await idle();
  const reopened = JSON.parse(
    await page.getByTestId("draft-receipt").textContent(),
  );
  assert.equal(reopened.valid, true);
  assert.equal(reopened.draft_sha256, validation.draft_sha256);
  assert.equal(reopened.preview.terrain_sha256, preview.terrain_sha256);
  await writeFile(resolve(output, "apothecary_w2_furnished.json"), saved);
  await writeFile(
    resolve(output, "production-preview.json"),
    JSON.stringify(reopened, null, 2),
  );
  receipt.checks.push(
    "native exact draft preview proves terrain/decor/factory container and wood_bundle; diff-confirm-variant-reopen passes current worker; original and selection profiles unchanged",
  );
  // Stale request, invalid raw source and a real ACCESS diagnostic are all visible.
  await button("Begin edit").click();
  await source();
  await page.locator("#draft-json").fill(saved.toString() + " ");
  await button("Preview draft").click();
  await source();
  await page.locator("#draft-json").fill(saved.toString() + "  ");
  await idle();
  assert.equal(await page.getByTestId("draft-verdict").count(), 0);
  await page.locator("#draft-json").fill('{"id":');
  await button("Authored layout").click();
  assert.match(
    await page.getByTestId("canvas-disabled").innerText(),
    /Correct JSON/,
  );
  assert.equal(await button("Pencil · B").isDisabled(), true);
  await source();
  const sealed = JSON.parse(saved);
  sealed.layers[6] = "###########";
  await page.locator("#draft-json").fill(JSON.stringify(sealed, null, 2));
  await button("Preview draft").click();
  await idle();
  assert.match(await page.locator(".problem-list").innerText(), /ACCESS/);
  assert.equal(await button("Review & apply").isDisabled(), true);
  await button("Locate cell / record").first().click();
  await page.getByTestId("layout-map").waitFor();
  await page.screenshot({ path: resolve(output, "access-failure.png") });
  await source();
  await page.locator("#draft-json").fill(saved.toString() + " ");
  await button("Validate draft").click();
  await idle();
  assert.equal(await button("Review & apply").isDisabled(), false);
  const external = saved.toString() + "\n";
  await writeFile(variantPath, external);
  // Deliberately apply before the idle file check; host still compares bytes.
  const token = JSON.parse(
    await page.getByTestId("draft-receipt").textContent(),
  ).review_token;
  await button("Review & apply").click();
  await button("Confirm apply one file").click();
  await idle();
  assert.match(
    await page.locator("footer").innerText(),
    /EXTERNAL_MODIFICATION_CONFLICT/,
  );
  assert.equal((await readFile(variantPath)).toString(), external);
  assert.ok(token);
  receipt.checks.push(
    "stale native validation ignored; invalid raw source freezes painting; actual ACCESS diagnostic locates source cell; concurrent file edit blocks publication",
  );
  await button("Discard / Revert").click();
  await page.getByRole("button", { name: "Generate / refresh" }).click();
  await idle();
  await page.screenshot({ path: resolve(output, "reopened.png") });
  receipt.visual_variant = {
    id: "apothecary_w2_furnished",
    path: "roguelike/data/buildings/commercial/apothecary_w2_furnished.json",
    sha256: createHash("sha256").update(saved).digest("hex"),
    fixture_only: true,
    selection_profiles_changed: false,
    source_unchanged: true,
  };
}
