// App-local DOM/CDP automation of an actual WebView2/Tauri window. No desktop input.
import { chromium } from "playwright-core";
import { spawn, execFileSync } from "node:child_process";
import { mkdir, readFile, writeFile, stat, readdir } from "node:fs/promises";
import { resolve, basename } from "node:path";
import { watch } from "node:fs";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const workbench = fileURLToPath(new URL("..", import.meta.url));
const root = process.env.WORKBENCH_TEST_ROOT || resolve(workbench, "..");
const executable = resolve(
  process.env.WORKBENCH_EXE ||
    resolve(workbench, "src-tauri/target/release/resonance-workbench.exe"),
);
const mode = process.env.WORKBENCH_TEST_MODE || "release";
if (mode === "creatures") {
  await import("./run-creature-common.mjs");
  process.exit(0);
}
const output = resolve(workbench, ".artifacts", `desktop-${mode}`);
await mkdir(output, { recursive: true });
const workerTemp = resolve(output, `worker-temp-${Date.now()}`);
await mkdir(workerTemp);
const port = 9333;
const env = {
  ...process.env,
  RESONANCE_WORKBENCH_CONFIG_DIR: resolve(output, `settings-${Date.now()}`),
  TMP: workerTemp,
  TEMP: workerTemp,
  WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS: `--remote-debugging-port=${port} --remote-debugging-address=127.0.0.1`,
  WEBVIEW2_USER_DATA_FOLDER: resolve(output, "webview-profile"),
};
if (mode !== "development") delete env.RESONANCE_PYTHON;
if (mode === "portable-clean")
  env.PATH = `${process.env.SystemRoot}\\System32;${process.env.SystemRoot}`;
if (mode === "missing-worker")
  env.RESONANCE_PYTHON = resolve(output, "does-not-exist.exe");
if (mode === "missing-dependency")
  env.RESONANCE_PYTHON = process.env.WORKBENCH_EMPTY_PYTHON;
const faultModes = [
  "protocol-mismatch",
  "malformed-worker",
  "worker-exit",
  "slow-worker",
];
if (faultModes.includes(mode)) {
  env.RESONANCE_PYTHON = resolve(workbench, ".artifacts/fault-worker.exe");
  env.WORKBENCH_FAULT = mode;
}
if (mode.startsWith("draft-worker-") || mode.startsWith("pool-worker-") || mode.startsWith("item-worker-") || mode.startsWith("recipe-worker-") || mode.startsWith("creature-worker-") || mode.startsWith("submap-worker-")) {
  env.RESONANCE_PYTHON = resolve(workbench, ".artifacts/fault-worker.exe");
  env.WORKBENCH_FAULT = mode.replace("submap-worker-", "draft-worker-").replace("pool-worker-", "draft-worker-").replace("item-worker-", "draft-worker-").replace("recipe-worker-", "draft-worker-").replace("creature-worker-", "draft-worker-");
  env.WORKBENCH_REAL_PYTHON = resolve(
    workbench,
    "src-tauri/target/release/python/python.exe",
  );
  env.WORKBENCH_FAULT_ONCE = resolve(output, `fault-once-${Date.now()}`);
}
let child, browser, page;
const receipt = {
  executable,
  mode,
  started_utc: new Date().toISOString(),
  checks: [],
  console_errors: [],
  external_requests: [],
};
const began = performance.now();
try {
  child = spawn(executable, env.RESONANCE_PYTHON ? ["--diagnostic-runtime"] : [], {
    cwd: output,
    env,
    windowsHide: true,
    stdio: "ignore",
  });
  receipt.host_pid = child.pid;
  for (let tries = 0; ; tries++) {
    if (child.exitCode !== null)
      throw new Error(`App exited ${child.exitCode}`);
    try {
      const data = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) =>
        r.json(),
      );
      if (data.length) break;
    } catch {}
    if (tries > 160) throw new Error("WebView2 CDP endpoint did not appear");
    await new Promise((r) => setTimeout(r, 250));
  }
  browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
  const context = browser.contexts()[0];
  page = context.pages()[0];
  page.on("pageerror", (error) => receipt.console_errors.push(error.message));
  page.on("request", (request) => {
    const u = new URL(request.url());
    if (
      ![
        "tauri.localhost",
        "ipc.localhost",
        "127.0.0.1",
        "localhost",
        "",
      ].includes(u.hostname) &&
      ["http:", "https:"].includes(u.protocol)
    )
      receipt.external_requests.push(request.url());
  });
  await page.getByRole("heading", { name: "Resonance Workbench" }).waitFor();
  receipt.launch_to_shell_ms = Math.round(performance.now() - began);
  receipt.webview_url = page.url();
  receipt.user_agent = await page.evaluate(() => navigator.userAgent);
  assert.ok(
    await page.evaluate(() => !!window.__TAURI_INTERNALS__),
    "Must be a Tauri webview",
  );
  receipt.checks.push("actual Tauri WebView2 window");
  if (mode !== "development") {
    // Emulated network outage in this app's WebView only; local Tauri IPC keeps
    // working. No network/firewall settings of the owner's desktop are changed.
    await context.setOffline(true);
    receipt.checks.push("WebView network offline");
  }
  await page.setViewportSize({ width: 2560, height: 1440 });
  if (mode === "pools") {
    const text = await page.locator("body").innerText();
    assert(!text.includes("A place to understand the world")); assert(!text.includes("Your world, under the lens"));
    await page.screenshot({path: resolve(output, "startup.png")});
  }
  await page.waitForFunction(() => !document.querySelector(".status-dot.working"), null, {timeout: 45000});
  await page.getByLabel("Repository directory").fill(root);
  const startOpen = performance.now();
  await page
    .getByRole("button", { name: "Open directory", exact: true })
    .click();
  // A previous project remains visible until the host accepts the replacement.
  // Its already-ready canvas is not evidence that this new open has completed.
  if (!faultModes.includes(mode) && !["missing-worker", "missing-dependency"].includes(mode))
    await page.waitForFunction(() => !document.querySelector(".status-dot.working"), null, {timeout:45000});
  if (mode === "interrupted-draft" || mode === "restart-draft") {
    const asset = "roguelike/data/buildings/commercial/workshop_b.json";
    const source = await readFile(resolve(root, asset));
    await page
      .locator('[data-testid="map"][data-ready="true"]')
      .waitFor({ timeout: 30000 });
    await page.getByLabel("Search ID, name or path").fill(asset);
    await page.locator(`[data-asset="${asset}"]`).click();
    await page.waitForFunction(() => !document.querySelector(".busy-overlay"));
    const opened = await page
      .getByLabel("Description", { exact: true })
      .inputValue();
    assert.equal(opened, JSON.parse(source).description);
    if (mode === "interrupted-draft") {
      await page
        .getByRole("button", { name: "Begin edit", exact: true })
        .click();
      await page
        .getByLabel("Description", { exact: true })
        .fill("Unsaved draft before process interruption");
      child.kill();
      await new Promise((r) => child.once("exit", r));
      assert.deepEqual(await readFile(resolve(root, asset)), source);
      receipt.checks.push(
        "hard process interruption with an unsaved draft leaves original source intact",
      );
    } else {
      assert.notEqual(opened, "Unsaved draft before process interruption");
      receipt.checks.push(
        "fresh native process reopens original valid source after interruption",
      );
    }
  } else if (mode.startsWith("draft-worker-") || mode.startsWith("pool-worker-") || mode.startsWith("item-worker-") || mode.startsWith("recipe-worker-") || mode.startsWith("creature-worker-") || mode.startsWith("submap-worker-")) {
    const poolFault = mode.startsWith("pool-worker-");
    const itemFault = mode.startsWith("item-worker-");
    const recipeFault = mode.startsWith("recipe-worker-");
    const creatureFault = mode.startsWith("creature-worker-");
    const submapFault = mode.startsWith("submap-worker-");
    const asset = submapFault ? "roguelike/docs/examples/g17_authored_creature_room.json" : creatureFault ? "roguelike/data/entities/creatures/hollow_revenant.json" : recipeFault ? "roguelike/data/recipes/bile_coating.json" : itemFault ? "roguelike/data/items/components/wood_bundle.json" : poolFault ? "roguelike/data/loot_pools/alchemist_reagents.json" : "roguelike/data/buildings/commercial/apothecary_a.json";
    const before = await readFile(resolve(root, asset));
    await page
      .locator('[data-testid="map"][data-ready="true"]')
      .waitFor({ timeout: 30000 });
    await page.getByLabel("Search ID, name or path").fill(asset);
    await page.locator(`[data-asset="${asset}"]`).click();
    await page.waitForFunction(() => !document.querySelector(".busy-overlay"));
    await page.getByRole("button", { name: "Begin edit", exact: true }).click();
    if (submapFault) await page.getByRole("button",{name:"Source",exact:true}).click();
    const draftControl = submapFault ? page.locator("#draft-json") : page.getByLabel(creatureFault ? "Creature name" : recipeFault ? "Recipe description" : itemFault ? "Item description" : "Description", {exact:true});
    const unsaved = submapFault ? (await draftControl.inputValue())+" " : "Unsaved draft for worker failure control";
    await draftControl.fill(unsaved);
    const start = performance.now();
    // A file event from the diagnostic helper establishes that the owned worker
    // reached the fault, without racing Cancel against process startup.
    const faultReached = new Promise(resolveReached => {
      const watcher=watch(output,(_event,name)=>{
        if(String(name)===basename(env.WORKBENCH_FAULT_ONCE)) { watcher.close(); resolveReached(); }
      });
    });
    await page
      .getByRole("button", { name: poolFault || itemFault || recipeFault || creatureFault ? "Validate draft" : "Preview draft", exact: true })
      .click();
    await faultReached;
    if (mode.endsWith("worker-cancel")) {
      await page
        .getByRole("button", { name: "Cancel authoring request", exact: true })
        .click();
      await page.waitForFunction(
        () => !document.querySelector(".busy-overlay"),
      );
    } else {
      const code =
        mode.endsWith("worker-exit") ? "WORKER_EXIT" : mode.endsWith("worker-malformed") ? "MALFORMED_WORKER_OUTPUT" : "WORKER_TIMEOUT";
      await page
        .locator("footer")
        .getByText(new RegExp(code))
        .waitFor({ timeout: 110000 });
      receipt.checks.push(
        code + " visible during an actual unsaved canvas session",
      );
    }
    receipt.draft_fault_elapsed_ms = Math.round(performance.now() - start);
    assert.equal(await page.getByTestId("draft-verdict").count(), 0);
    assert.equal(await draftControl.inputValue(),unsaved);
    assert.equal(
      await page
        .getByRole("button", { name: recipeFault || creatureFault || submapFault ? "Apply variant" : "Review & apply", exact: true })
        .isDisabled(),
      true,
    );
    assert.deepEqual(await readFile(resolve(root, asset)), before);
    receipt.checks.push(
      "failed/cancelled draft worker retains unsaved text and grants no review or publication; original bytes unchanged",
    );
    await page.screenshot({
      path: resolve(output, "draft-worker-failure.png"),
    });
    await page.getByRole("button", {name:poolFault || itemFault || recipeFault || creatureFault ? "Validate draft" : "Preview draft",exact:true}).click();
    await page.waitForFunction(()=>!document.querySelector(".status-dot.working"),null,{timeout:45000});
    assert.equal(JSON.parse(await page.getByTestId("draft-receipt").textContent()).valid,true);
    assert.equal(await draftControl.inputValue(),unsaved);
    receipt.checks.push("same-session recovery: diagnostic helper forwards the next request to real production validation; retained exact draft passes");
    await page
      .getByRole("button", { name: "Discard / Revert", exact: true })
      .click();
  } else if (mode === "slow-worker") {
    await page.getByRole("button", { name: "Cancel", exact: true }).waitFor();
    await new Promise((r) => setTimeout(r, 300));
    const workers = () =>
      JSON.parse(
        execFileSync(
          "powershell.exe",
          [
            "-NoProfile",
            "-Command",
            `ConvertTo-Json -InputObject @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq ${child.pid} -and $_.Name -eq 'fault-worker.exe' } | Select-Object ProcessId) -Compress`,
          ],
          { windowsHide: true, encoding: "utf8" },
        ),
      );
    assert.equal(workers().length, 1);
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await page
      .locator("footer")
      .getByText(/Cancelled/)
      .waitFor();
    assert.equal(workers().length, 0);
    receipt.checks.push("cancel reaps a live long-running worker");
    await page
      .getByRole("button", { name: "Open directory", exact: true })
      .click();
    await new Promise((r) => setTimeout(r, 300));
    assert.equal(workers().length, 1);
    // A project replacement also synchronously cancels the previous child.
    const replaced = await page.evaluate(async (path) => {
      try {
        await window.__TAURI_INTERNALS__.invoke("open_project", { path });
      } catch (e) {
        return e;
      }
    }, output);
    assert.equal(replaced.code, "INVALID_PROJECT");
    assert.equal(workers().length, 0);
    receipt.checks.push("project replacement reaps active worker");
    await page
      .getByRole("button", { name: "Open directory", exact: true })
      .click();
    await new Promise((r) => setTimeout(r, 300));
    const active = workers();
    assert.equal(active.length, 1);
    receipt.close_worker_pid = active[0].ProcessId;
    // finally closes the native window during this request, then verifies reaping.
  } else if (
    mode === "missing-worker" ||
    mode === "missing-dependency" ||
    faultModes.includes(mode)
  ) {
    const codes = {
      "missing-worker": "WORKER_MISSING",
      "missing-dependency": "MISSING_DEPENDENCY",
      "protocol-mismatch": "PROTOCOL_MISMATCH",
      "malformed-worker": "MALFORMED_WORKER_OUTPUT",
      "worker-exit": "WORKER_EXIT",
    };
    const code = codes[mode];
    await page.locator("footer").getByText(new RegExp(code)).waitFor();
    receipt.checks.push(`${code} visible and actionable`);
    await page.screenshot({ path: resolve(output, "failure.png") });
  } else {
    await page
      .locator('[data-testid="map"][data-ready="true"]')
      .waitFor({ timeout: 30000 });
    receipt.open_to_preview_ms = Math.round(performance.now() - startOpen);
    assert.match(
      await page.locator(".validation").innerText(),
      /Production validator passed/,
    );
    receipt.checks.push(
      "repository handshake, live asset validation and Pixi rendering",
    );
    receipt.worker = await page.evaluate(
      async () =>
        (
          await window.__TAURI_INTERNALS__.invoke("worker_request", {
            request: { op: "identify" },
          })
        ).result,
    );
    receipt.preview_sample = await page.evaluate(async () => {
      const response = await window.__TAURI_INTERNALS__.invoke(
        "worker_request",
        {
          request: {
            op: "preview",
            asset: "roguelike/data/layouts/starting_lab.json",
            seed: 20261023,
          },
        },
      );
      const r = response.result;
      return {
        asset: r.asset,
        seed: r.seed,
        scene_seed: r.scene_seed,
        scene_address: r.scene_address,
        origin: r.origin,
        spawn: r.spawn,
        width: r.width,
        height: r.height,
        generation_ms: r.elapsed_ms,
        host_ms: response.host_elapsed_ms,
        terrain_sha256: r.terrain_sha256,
        candidate_sha256: r.candidate_sha256,
        samples: [
          [15, 20, r.terrain[20][15]],
          [67, 16, r.terrain[16][67]],
          [79, 42, r.terrain[42][79]],
        ],
        containers: r.containers,
        object_cells: r.items.length,
        passed: r.passed,
      };
    });
    assert.equal(
      typeof receipt.preview_sample.scene_seed,
      "string",
      "Preserve the exact large scene seed",
    );
    const marker = await page.locator('[data-testid="map"]').evaluate((el) => {
      const c = JSON.parse(el.dataset.camera),
        b = el.getBoundingClientRect();
      return {
        x: b.x + c.x + 15.5 * 16 * c.scale,
        y: b.y + c.y + 20.5 * 16 * c.scale,
      };
    });
    await page.mouse.move(marker.x, marker.y);
    await page.mouse.click(marker.x, marker.y);
    await page
      .getByTestId("cell")
      .getByText("(15, 20)", { exact: true })
      .waitFor();
    assert.equal(await page.getByTestId("tile-id").innerText(), "stairs_up");
    receipt.checks.push("production arrival click maps to (15,20), stairs_up");
    await page.screenshot({ path: resolve(output, "ready-2560.png") });
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await page.locator("canvas").press("ArrowRight");
    await page.getByRole("button", { name: "Fit map" }).click();
    await page
      .getByRole("button", { name: "Test invalid disposable fixture" })
      .click();
    await page
      .getByTestId("fixture-result")
      .getByText("Invalid fixture correctly rejected", { exact: true })
      .waitFor();
    assert.match(
      await page.getByTestId("fixture-result").innerText(),
      /DIMENSION/,
    );
    receipt.checks.push("real DIMENSION diagnostic for disposable fixture");
    await page.locator(".inspector").evaluate((el) => {
      el.scrollTop = el.scrollHeight;
    });
    await page.screenshot({ path: resolve(output, "invalid-fixture.png") });
    const asset = resolve(root, "roguelike/data/layouts/starting_lab.json");
    const beforeBytes = await readFile(asset);
    const beforeStat = await stat(asset);
    await page
      .getByRole("button", { name: "Source JSON", exact: true })
      .click();
    assert.match(await page.locator(".raw").innerText(), /starting_lab/);
    await page.getByRole("button", { name: "Properties", exact: true }).click();
    await page
      .getByRole("button", { name: "Close project", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Open directory", exact: true })
      .click();
    await page
      .locator('[data-testid="map"][data-ready="true"]')
      .waitFor({ timeout: 30000 });
    assert.deepEqual(await readFile(asset), beforeBytes);
    assert.equal((await stat(asset)).mtimeMs, beforeStat.mtimeMs);
    receipt.checks.push("byte-exact view, close and reopen journey");
    // Exercise host authorization independently of disabled UI controls.
    const traversal = await page.evaluate(async () => {
      try {
        await window.__TAURI_INTERNALS__.invoke("worker_request", {
          request: { op: "inspect", asset: "../saves/personal.json" },
        });
      } catch (e) {
        return e;
      }
    });
    assert.equal(traversal.code, "PATH_ESCAPE");
    receipt.checks.push("host traversal rejection");
    const nativeState = execFileSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-Command",
        `Get-Process -Id ${child.pid} | Select-Object Id,MainWindowHandle,MainWindowTitle,WorkingSet64,PrivateMemorySize64 | ConvertTo-Json -Compress`,
      ],
      { windowsHide: true, encoding: "utf8" },
    );
    receipt.native_window = JSON.parse(nativeState);
    assert.ok(
      receipt.native_window.MainWindowHandle,
      "Actual desktop HWND must exist",
    );
    const cdp = await context.newCDPSession(page);
    const processList = await cdp
      .send("SystemInfo.getProcessInfo")
      .catch(() => null);
    receipt.webview_process_info = processList;
    receipt.frame_intervals_ms = await page.evaluate(async () => {
      const times = [];
      let last = performance.now();
      for (let n = 0; n < 120; n++) {
        const now = await new Promise(requestAnimationFrame);
        times.push(now - last);
        last = now;
        document.querySelector("canvas").dispatchEvent(
          new KeyboardEvent("keydown", {
            key: n % 2 ? "ArrowLeft" : "ArrowRight",
            bubbles: true,
          }),
        );
      }
      times.shift();
      times.sort((a, b) => a - b);
      return {
        median: times[Math.floor(times.length / 2)],
        p95: times[Math.floor(times.length * 0.95)],
        max: Math.max(...times),
        count: times.length,
      };
    });
    const memory = execFileSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-Command",
        `$all = Get-CimInstance Win32_Process; $ids = @(${child.pid}); for($n=0;$n -lt 4;$n++){ $ids += @($all | Where-Object { $_.ParentProcessId -in $ids } | ForEach-Object ProcessId); $ids = @($ids | Select-Object -Unique) }; Get-Process -Id $ids -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,WorkingSet64,PrivateMemorySize64 | ConvertTo-Json -Compress`,
      ],
      { windowsHide: true, encoding: "utf8" },
    );
    receipt.process_memory = JSON.parse(memory);
    await page.getByRole("button", { name: "Generate / refresh" }).click();
    const animationDuringWork = await page.evaluate(async () => {
      let count = 0;
      const start = performance.now();
      while (performance.now() - start < 300) {
        await new Promise(requestAnimationFrame);
        count++;
      }
      return count;
    });
    receipt.animation_frames_during_first_300ms_of_work = animationDuringWork;
    if (await page.getByRole("button", { name: "Cancel", exact: true }).count())
      await page.getByRole("button", { name: "Cancel", exact: true }).click();
    else
      await page.evaluate(() =>
        window.__TAURI_INTERNALS__.invoke("cancel_worker"),
      );
    await page.getByRole("button", { name: "Generate / refresh" }).click();
    await page
      .locator('[data-testid="map"][data-ready="true"]')
      .waitFor({ timeout: 30000 });
    receipt.checks.push("cancel and retry without app hang");
    if (mode === "authoring") {
      const { authoringJourney } = await import("./authoring-journey.mjs");
      await authoringJourney(page, root, output, receipt, child.pid);
    }
    if (mode === "visual") {
      const { visualJourney } = await import("./visual-journey.mjs");
      await visualJourney(page, root, output, receipt, context);
    }
    if (mode === "submaps") {
      const {submapJourney} = await import("./submap-journey.mjs");
      await submapJourney(page,root,output,receipt,context);
    }
    if (mode === "pools") {
      const { poolJourney } = await import("./pool-journey.mjs");
      await poolJourney(page, root, output, receipt);
    }
    if (mode === "recipes") {
      const {recipeJourney} = await import("./recipe-journey.mjs");
      await recipeJourney(page, root, output, receipt);
      if (process.env.WORKBENCH_CONTRACT_PROOF === "1") {
        const {contractJourney} = await import("./contract-journey.mjs");
        await contractJourney(page,root,output,receipt);
      }
    }
    if (mode === "texts") {
      const {textJourney} = await import("./text-journey.mjs");
      await textJourney(page,root,output,receipt);
    }
    if (mode === "workspace") {
      const {workspaceJourney} = await import("./workspace-journey.mjs");
      await workspaceJourney(page,root,output,receipt);
    }
    if (mode === "items") {
      const {itemJourney} = await import("./item-journey.mjs");
      await itemJourney(page, root, output, receipt);
    }
    await page.setViewportSize({ width: 1100, height: 740 });
    await page.screenshot({ path: resolve(output, "minimum-window.png") });
    await page
      .getByRole("button", { name: "Close project", exact: true })
      .click();
    await page.getByLabel("Repository directory").fill(output);
    await page
      .getByRole("button", { name: "Open directory", exact: true })
      .click();
    await page
      .locator("footer")
      .getByText(/INVALID_PROJECT/)
      .waitFor();
    receipt.checks.push("invalid project visible");
    assert.deepEqual(receipt.console_errors, []);
    assert.deepEqual(receipt.external_requests, []);
  }
  receipt.passed = true;
} catch (error) {
  receipt.passed = false;
  receipt.error = String(error.stack || error);
  if (page)
    await page
      .screenshot({ path: resolve(output, "unexpected-failure.png") })
      .catch(() => {});
  process.exitCode = 1;
} finally {
  // Test-owned process only. A separate lifecycle test uses the actual close event.
  if (child?.pid) {
    try {
      execFileSync(
        "powershell.exe",
        [
          "-NoProfile",
          "-Command",
          `$p=Get-Process -Id ${child.pid} -ErrorAction SilentlyContinue; if($p){ [void]$p.CloseMainWindow(); if(-not $p.WaitForExit(5000)){ Stop-Process -Id ${child.pid} } }`,
        ],
        { windowsHide: true },
      );
    } catch {}
  }
  if (receipt.close_worker_pid) {
    const exists = execFileSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-Command",
        `if(Get-Process -Id ${receipt.close_worker_pid} -ErrorAction SilentlyContinue){'alive'}else{'reaped'}`,
      ],
      { windowsHide: true, encoding: "utf8" },
    ).trim();
    receipt.worker_after_window_close = exists;
    if (exists !== "reaped") {
      receipt.passed = false;
      process.exitCode = 1;
    } else receipt.checks.push("native window close reaps active worker");
  }
  await browser?.close().catch(() => {});
  receipt.temporary_roots_remaining = (await readdir(workerTemp)).filter(
    (name) => name.startsWith("resonance-w0-"),
  );
  if (receipt.temporary_roots_remaining.length) {
    receipt.passed = false;
    process.exitCode = 1;
  } else
    receipt.checks.push("no temporary worker roots remain after native close");
  receipt.total_ms = Math.round(performance.now() - began);
  await writeFile(
    resolve(output, "receipt.json"),
    JSON.stringify(receipt, null, 2),
  );
  console.log(JSON.stringify(receipt, null, 2));
}
