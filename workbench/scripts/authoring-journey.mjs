import assert from "node:assert/strict";
import { readFile, writeFile, stat, readdir, realpath } from "node:fs/promises";
import { resolve } from "node:path";
import { execFileSync } from "node:child_process";
export async function authoringJourney(page, root, output, receipt, pid) {
  assert.match(
    root.replaceAll("\\", "/"),
    /\/workbench\/\.artifacts\/w1\/data-fixture-\d+$/,
  );
  assert.equal(await realpath(root), resolve(root));
  const asset = "roguelike/data/buildings/commercial/workshop_b.json";
  const target = resolve(root, asset),
    before = await readFile(target),
    metadata = await stat(target);
  const other = "roguelike/data/buildings/commercial/apothecary_b.json";
  const otherBefore = await readFile(resolve(root, other)),
    otherMeta = await stat(resolve(root, other));
  const profiles = await readFile(
    resolve(root, "roguelike/data/generation/settlement_profiles.json"),
  );
  const search = page.getByLabel("Search ID, name or path");
  const invoke = (command, args) =>
    page.evaluate(
      async ({ command, args }) => {
        try {
          return await window.__TAURI_INTERNALS__.invoke(command, args);
        } catch (e) {
          return { error: e };
        }
      },
      { command, args },
    );
  async function select(path) {
    await search.fill(path);
    await page.locator(`[data-asset="${path}"]`).click();
    await page
      .getByRole("button", { name: "Begin edit", exact: true })
      .waitFor();
    await page.waitForFunction(() => !document.querySelector(".busy-overlay"));
  }
  await select(other);
  await page.getByRole("button", { name: "Source", exact: true }).click();
  await select(asset);
  assert.deepEqual(await readFile(target), before);
  assert.equal((await stat(target)).mtimeMs, metadata.mtimeMs);
  assert.deepEqual(await readFile(resolve(root, other)), otherBefore);
  assert.equal((await stat(resolve(root, other))).mtimeMs, otherMeta.mtimeMs);
  receipt.checks.push(
    "search by exact path and two shipped definitions: byte/mtime no-op",
  );
  await page.getByRole("button", { name: "Begin edit", exact: true }).click();
  await page
    .getByLabel("Description", { exact: true })
    .fill("W1 native transaction: preserved workshop contents.");
  await page.getByRole("button", { name: "Diff", exact: true }).click();
  assert.match(
    await page.getByTestId("source-diff").innerText(),
    /\+.*W1 native transaction/,
  );
  await page.getByRole("button", { name: "Generate / refresh" }).click();
  await page
    .getByRole("dialog", { name: "Unsaved draft", exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Keep editing", exact: true }).click();
  // Native close request: app-local Win32 message to this test-owned HWND.
  execFileSync(
    "powershell.exe",
    [
      "-NoProfile",
      "-Command",
      `[void](Get-Process -Id ${pid}).CloseMainWindow()`,
    ],
    { windowsHide: true },
  );
  await page
    .getByRole("dialog", { name: "Unsaved draft", exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Keep editing", exact: true }).click();
  receipt.checks.push(
    "refresh and actual native close protect the unsaved draft",
  );
  await page
    .getByRole("button", { name: "Validate draft", exact: true })
    .click();
  // Change the text while the real Python request is active: its valid result
  // must not authorize the later text, including an edit-back-to-same-value.
  await page.getByRole("button", { name: "Source", exact: true }).click();
  const editor = page.getByLabel("Draft JSON", { exact: true });
  const changed = await editor.inputValue();
  await editor.fill(changed + " ");
  await page.waitForFunction(() => !document.querySelector(".busy-overlay"));
  assert.equal(await page.getByTestId("draft-verdict").count(), 0);
  assert.equal(
    await page
      .getByRole("button", { name: "Review & apply", exact: true })
      .isDisabled(),
    true,
  );
  receipt.checks.push(
    "real asynchronous validation response suppressed after a newer edit",
  );
  await editor.fill('{\n"id":');
  await page
    .getByRole("button", { name: "Validate draft", exact: true })
    .click();
  await page
    .getByTestId("draft-verdict")
    .filter({ hasText: "Draft rejected" })
    .waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Review & apply", exact: true })
      .isDisabled(),
    true,
  );
  const invalid = JSON.parse(changed);
  invalid.legend["#"] = "not_a_real_tile";
  await page.getByRole("button", { name: "Source", exact: true }).click();
  await editor.fill(JSON.stringify(invalid, null, 2));
  await page
    .getByRole("button", { name: "Validate draft", exact: true })
    .click();
  await page
    .getByTestId("draft-verdict")
    .filter({ hasText: "Draft rejected" })
    .waitFor();
  assert.match(await page.locator(".problem-list").innerText(), /TERRAIN_USED/);
  assert.deepEqual(await readFile(target), before);
  receipt.checks.push(
    "malformed JSON and real unknown terrain reject publication despite retained map",
  );
  await page.getByRole("button", { name: "Source", exact: true }).click();
  await editor.fill(changed);
  await page
    .getByRole("button", { name: "Validate draft", exact: true })
    .click();
  await page
    .getByTestId("draft-verdict")
    .filter({ hasText: "Draft contract and references passed" })
    .waitFor();
  await page
    .getByRole("button", { name: "Review & apply", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Confirm single-file apply" })
    .waitFor();
  await page.screenshot({ path: resolve(output, "review.png") });
  await page
    .getByRole("button", { name: "Confirm apply one file", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Begin edit", exact: true })
    .waitFor({ timeout: 60000 });
  await page.waitForFunction(() => !document.querySelector(".busy-overlay"));
  const applied = await readFile(target);
  assert.equal(
    JSON.parse(applied).description,
    "W1 native transaction: preserved workshop contents.",
  );
  assert.deepEqual(
    { ...JSON.parse(applied), description: JSON.parse(before).description },
    JSON.parse(before),
  );
  const originalText = before.toString(),
    resultText = applied.toString();
  assert.equal(
    resultText.replace(
      JSON.stringify(JSON.parse(applied).description),
      JSON.stringify(JSON.parse(before).description),
    ),
    originalText,
  );
  assert.equal((await stat(target)).birthtimeMs, metadata.birthtimeMs);
  await page.getByTestId("apply-receipt").locator("summary").click();
  await page.screenshot({ path: resolve(output, "applied.png") });
  receipt.checks.push(
    "typed scalar edit: diff, fresh host validation, confirm, Windows replace, exact unrelated text, metadata, reopen, real revalidation",
  );
  // A second apply creates an explicit new variant with a unique ID.
  await page.getByRole("button", { name: "Begin edit", exact: true }).click();
  await page
    .getByRole("button", { name: "Save as new variant", exact: true })
    .click();
  await page
    .getByLabel("New variant ID", { exact: true })
    .fill("workshop_w1_native_variant");
  await page
    .getByRole("button", { name: "Validate draft", exact: true })
    .click();
  await page
    .getByTestId("draft-verdict")
    .filter({ hasText: "Draft contract and references passed" })
    .waitFor();
  await page
    .getByRole("button", { name: "Review & apply", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirm apply one file", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Begin edit", exact: true })
    .waitFor({ timeout: 60000 });
  await page.waitForFunction(() => !document.querySelector(".busy-overlay"));
  assert.equal(
    JSON.parse(
      await readFile(
        resolve(
          root,
          "roguelike/data/buildings/commercial/workshop_w1_native_variant.json",
        ),
      ),
    ).id,
    "workshop_w1_native_variant",
  );
  assert.deepEqual(
    await readFile(
      resolve(root, "roguelike/data/generation/settlement_profiles.json"),
    ),
    profiles,
  );
  receipt.checks.push(
    "unique variant applied and reopened; selection profiles byte-identical",
  );
  // Test publication security at the actual host command boundary.
  for (const bad of [
    "../x.json",
    "roguelike/saves/campaign.json",
    "roguelike/engine/data_loader.py",
    "roguelike/data/buildings/plaza/x.json",
    "C:/outside.json",
    "roguelike/data/buildings/commercial/../x.json",
  ]) {
    assert.ok((await invoke("open_document", { asset: bad })).error, bad);
  }
  assert.equal(
    (
      await invoke("validate_document", {
        token: "forged",
        draft: "{}",
        variantId: null,
      })
    ).error.code,
    "UNKNOWN_DOCUMENT",
  );
  let doc = (await invoke("open_document", { asset })).result;
  const draft = doc.raw.replace(
    JSON.stringify(JSON.parse(doc.raw).description),
    '"W1 unsaved conflict draft"',
  );
  let validation = (
    await invoke("validate_document", {
      token: doc.document_token,
      draft,
      variantId: null,
    })
  ).result;
  assert.ok(validation.valid);
  const terrainFile = resolve(root, "roguelike/data/terrain.json"),
    terrainBytes = await readFile(terrainFile);
  const brokenTerrain = JSON.parse(terrainBytes);
  delete brokenTerrain.wall;
  await writeFile(terrainFile, JSON.stringify(brokenTerrain));
  try {
    const refused = await invoke("apply_document", {
      token: doc.document_token,
      reviewToken: validation.review_token,
      confirmed: true,
    });
    assert.equal(refused.error.code, "VALIDATION_FAILED");
    assert.deepEqual(await readFile(target), applied);
  } finally {
    await writeFile(terrainFile, terrainBytes);
  }
  validation = (
    await invoke("validate_document", {
      token: doc.document_token,
      draft,
      variantId: null,
    })
  ).result;
  receipt.checks.push(
    "dependency changed after review: exact draft revalidated at apply and refused; source survives",
  );
  const external = applied
    .toString()
    .replace(
      JSON.stringify(JSON.parse(applied).description),
      '"External editor survives"',
    );
  await writeFile(target, external);
  let result = await invoke("apply_document", {
    token: doc.document_token,
    reviewToken: validation.review_token,
    confirmed: true,
  });
  assert.equal(result.error.code, "EXTERNAL_MODIFICATION_CONFLICT");
  assert.equal((await readFile(target)).toString(), external);
  const disk = (await invoke("document_disk", { token: doc.document_token }))
    .result;
  assert.equal(disk.changed, true);
  assert.equal(disk.raw, external);
  receipt.checks.push(
    "real host rejects stale publication and exposes intact external version",
  );
  assert.ok(
    (
      await invoke("validate_document", {
        token: doc.document_token,
        draft,
        variantId: "../../saves/escape",
      })
    ).error,
  );
  assert.equal(
    (
      await invoke("apply_document", {
        token: doc.document_token,
        reviewToken: "forged",
        confirmed: true,
      })
    ).error.code,
    "REVIEW_REQUIRED",
  );
  // Junction redirect after trusted discovery and open. No write may follow it.
  const category = resolve(root, "roguelike/data/buildings/commercial"),
    moved = category + "-real";
  assert.ok(
    category.startsWith(resolve(root) + "\\") &&
      moved.startsWith(resolve(root) + "\\"),
  );
  assert.equal(await realpath(category), category);
  doc = (await invoke("open_document", { asset })).result;
  validation = (
    await invoke("validate_document", {
      token: doc.document_token,
      draft: doc.raw + " ",
      variantId: null,
    })
  ).result;
  execFileSync(
    "powershell.exe",
    [
      "-NoProfile",
      "-Command",
      "Move-Item -LiteralPath $env:W1_SOURCE -Destination $env:W1_MOVED; New-Item -ItemType Junction -Path $env:W1_SOURCE -Target $env:W1_MOVED | Out-Null",
    ],
    {
      windowsHide: true,
      env: { ...process.env, W1_SOURCE: category, W1_MOVED: moved },
    },
  );
  try {
    assert.equal(
      (await invoke("document_disk", { token: doc.document_token })).error.code,
      "PATH_ESCAPE",
    );
    assert.equal(
      (
        await invoke("apply_document", {
          token: doc.document_token,
          reviewToken: validation.review_token,
          confirmed: true,
        })
      ).error.code,
      "PATH_ESCAPE",
    );
  } finally {
    // Remove the junction itself non-recursively, then restore the test category.
    execFileSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-Command",
        "[System.IO.Directory]::Delete($env:W1_SOURCE); Move-Item -LiteralPath $env:W1_MOVED -Destination $env:W1_SOURCE",
      ],
      {
        windowsHide: true,
        env: { ...process.env, W1_SOURCE: category, W1_MOVED: moved },
      },
    );
  }
  assert.equal((await readFile(target)).toString(), external);
  receipt.checks.push(
    "traversal, saves/code, forged identities/reviews, unsafe variant and junction redirect denied at native host boundary",
  );
  // Show conflict in the actual editor, preserving its local draft.
  await select(asset);
  await page.getByRole("button", { name: "Begin edit", exact: true }).click();
  await page
    .getByLabel("Description", { exact: true })
    .fill("Retained manual reconciliation draft");
  await writeFile(
    target,
    external.replace(
      "External editor survives",
      "Another external edit survives",
    ),
  );
  await page
    .getByTestId("draft-state")
    .filter({ hasText: "Externally changed" })
    .waitFor({ timeout: 10000 });
  await page.screenshot({ path: resolve(output, "conflict.png") });
  await page.getByRole("button", { name: "Generate / refresh" }).click();
  await page
    .getByRole("button", { name: "Discard and continue", exact: true })
    .click();
  await page.getByRole("button", { name: "Begin edit", exact: true }).waitFor();
  await page.waitForFunction(() => !document.querySelector(".busy-overlay"));
  assert.equal(
    await page.getByLabel("Description", { exact: true }).inputValue(),
    "Another external edit survives",
  );
  assert.ok(!(await readdir(category)).some((n) => n.startsWith(".w1-")));
  receipt.checks.push(
    "visible conflict, discard/reload and no unnoticed staging/backup files",
  );
  receipt.authoring_target = asset;
}
