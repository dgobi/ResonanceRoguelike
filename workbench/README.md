# Resonance Workbench · W1

An independent, local Tauri 2 desktop application for inspecting Resonance and
safely editing one ordinary-building definition at a time. The game remains the
validation authority. No campaign, running game or Internet service is required.

## Author one building

1. Open the current checkout. It starts read-only and retains W0's actual
   `starting_lab` 80 × 43 production preview.
2. Search by ID, description/name or relative path, optionally filter by folder.
   All immediate `data/buildings/<category>/*.json` ordinary buildings appear
   deterministically (58 at the W1 source baseline). Plazas are listed as
   unsupported/read-only; authored layouts retain W0 read-only inspection.
3. Select a building such as `commercial/workshop_b.json`. Source, properties,
   diagnostics, file hash, source revision and worker compatibility are visible.
   **Begin edit** opts into an in-memory draft. Description and legacy scatter
   weight use text-span edits; **Source** exposes the complete strict JSON.
4. **Validate draft** runs the real `read_document`, `DataLoader` and
   `compile_structure` against a disposable equivalent of current data. Problems
   distinguish syntax errors (line/column where available), structure/reference
   errors and warnings. The displayed map remains explicitly from disk.
5. Inspect **Diff**, then **Review & apply**. The confirmation repeats the exact
   diff and warns about existing world references. The host revalidates the exact
   stored bytes with fresh dependencies before publishing one file. The receipt
   records target, before/after hashes and existing/variant outcome. The index,
   editor and preview reopen from disk.
6. Prefer **Save as new variant** for identity or meaning changes. Enter a unique
   ID using letters, digits, `_` or `-`; this updates the draft's ID and derives
   `<same category>/<id>.json`. Existing IDs cannot be renamed in place. Current
   town/roadside selection profiles are **not** modified or populated by saving.
   Legacy flat-pool generation can discover added files; creating a variant does
   not establish that current planned generation will select it.

Opening, switching tabs and closing clean source never serializes it. Property
edits retain unrelated spans, BOM and line endings; raw edits retain the source's
CRLF convention. Unknown fields, nested arrays, specials, decor and text bindings
remain in the one shared draft. Discard/Revert returns to the opened bytes;
Generate/refresh reloads disk. Switching files/projects, refresh and native close
protect unsaved drafts with an explicit discard prompt. Drafts are memory-only;
forced process termination loses unsaved edits, while source stays intact.

A three-second idle check reports external changes and exposes the disk version
without replacing the draft. Apply always compares bytes again, independently of
that check. There is no forced save or automatic merge. Keep the draft for manual
reconciliation, or discard/reload the external version.

Validation establishes the supported structure contract and its declared
references. It does **not** prove reachability, natural selection or population
of an unsaved draft. The separate direct-consumer preview displays real initial
population from disk, not general gameplay balance or access certification.

## Launch

Windows x64 is verified. The release directory contains
`resonance-workbench.exe`, `bridge.py` and `python/`; **keep all three together**.
Double-click the executable. The NSIS package includes those same resources.
WebView2 Evergreen must already be installed; W0's installer does not download
it. This machine was verified with WebView2 155.0.4283.62.

Choose **Choose repository**, or enter the directory and use **Open directory**.
Select this repository's root (the `roguelike/` subdirectory is also accepted).
The read-only authored layout list contains `starting_lab`, a 60 × 16 source
definition. It produces a full 80 × 43 authored scene through the game compiler,
scene builder, generator and population factories.

Hover/click to inspect terrain coordinates and IDs; drag to pan, scroll or use
the buttons to zoom, and press Home to fit. Arrow keys pan the focused canvas.
**Generate / refresh** reloads source and uses the entered seed.
**Test invalid disposable fixture** runs the same validator on a temporary copy
with a deliberately incorrect width. **Cancel** terminates the active worker.
Authored-layout Source JSON remains read-only; ordinary buildings expose the W1 workflow above.

## Development and builds

Requirements: Windows x64, Node **24.x** (tested 24.15.0), npm (tested 11.12.1),
Rust/MSVC **1.95.0**, Visual Studio 2022 C++ tools/Windows SDK, and WebView2.
CPython **3.11** with the root `requirements-baseline.txt` is the development
runtime. The project's established environment supplies dependencies only;
imports always come from the selected checkout. Other operating systems are
unverified; runtime preparation and packaging are Windows-specific in W0.

From `workbench/` in PowerShell:

```powershell
npm.cmd ci
$env:RESONANCE_PYTHON = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
npm.cmd run dev
```

`RESONANCE_PYTHON` is a trusted **launching-shell** setting, never a frontend
argument. Without it, development uses `worker/runtime/python.exe` if prepared,
then the selected repository's `.venv/Scripts/python.exe`. A missing runtime has
an actionable error. Installed/portable release builds use their bundled runtime
unless this explicit environment override is set.

```powershell
# Prepare a redistributable CPython 3.11.0 runtime and exact, hash-pinned wheels.
# First preparation downloads the official Python archive and wheels.
.\scripts\prepare-runtime.ps1 -Python $env:RESONANCE_PYTHON
npm.cmd run build                    # executable + resources, no installer
npm.cmd run bundle                   # same app plus NSIS installer
```

Outputs: `src-tauri/target/release/resonance-workbench.exe` with `python/` and
`bridge.py`; installer in `src-tauri/target/release/bundle/nsis/`.
The Python archive and wheel hashes are checked during preparation. npm and
Cargo lockfiles pin transitive dependencies. `rust-toolchain.toml` fixes the
compiler. Rebuild downloads require connectivity; **application use is offline**.
The package imports game Python from the chosen source tree and does not freeze
an old copy of game rules. CPython and wheel licenses remain in the runtime.
Native numeric thread pools are capped at one for this small preview; the
initial default OpenBLAS pool reserved substantial memory without helping W0.
Git is optional at runtime: without it, source/catalog hashes remain available
and the Git revision/working-tree status is explicitly unavailable.

## Verification

```powershell
npm.cmd run build:web                # also typechecks; needed for cargo tests
npm.cmd test
cargo test --locked --manifest-path src-tauri/Cargo.toml
cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings
& $env:RESONANCE_PYTHON -B worker/test_bridge.py
& $env:RESONANCE_PYTHON -B scripts/render-reference.py
npm.cmd run test:desktop             # built RELEASE executable; real WebView2
npm.cmd run test:authoring           # disposable data + native apply/reopen/restart journey
& $env:RESONANCE_PYTHON -B worker/test_authoring.py
```

`scripts/desktop-test.mjs` opens a test-owned native window and sends app-local
DOM events through WebView2 CDP. It tests with the WebView network offline,
captures screenshots and measures startup, panning frames and process memory.
No owner's desktop input is driven. The test-only CDP port is 9333; normal
launches expose no debug server. Results/profile files stay in `.artifacts/`.

To test the development window, keep `npm run dev` running, set
`WORKBENCH_TEST_MODE=development` and `WORKBENCH_EXE` to the absolute
`src-tauri/target/debug/resonance-workbench.exe` path, then run `test:desktop`.
For the release fault controls, compile the deliberately broken test helper:

```powershell
rustc scripts/fault-worker.rs -o .artifacts/fault-worker.exe
$env:WORKBENCH_TEST_MODE = 'protocol-mismatch' # also malformed-worker, worker-exit, slow-worker, missing-worker
npm.cmd run test:desktop
Remove-Item Env:WORKBENCH_TEST_MODE
```

The helper is excluded from every package; it provides only negative evidence.
`missing-dependency` additionally takes `WORKBENCH_EMPTY_PYTHON`, a disposable
CPython runtime without the game dependency wheels.

## Contract and limits

The protocol is **2**, worker/app **0.2.0**, game structure contract **g2-2**.
W0 identify/describe/inspect/preview requests remain read-only. Draft validation
is available only through the host's document boundary. Discovery grants an
opaque document token; validation grants a one-draft review token. Apply takes
that token and explicit confirmation, never an arbitrary destination or trusted
frontend verdict. Variants stay in the discovered source's existing category.
There are no frontend filesystem/shell permissions, arbitrary Python evaluation
or Git mutations. The only frontend capabilities are local close-event listening.

The Rust host validates allowed path components, canonical containment and
reparse-point rejection again at publication. Windows directory handles prevent
parent moves; dependency read handles deny concurrent writes/renames during the
final validation. A separate source read lock covers validation, then releases
for replacement. The host compares current bytes immediately before publishing
and the actual displaced backup bytes afterward, restoring an intervening
external version on conflict. Input hashes/file membership are also rechecked.

An existing-file apply writes and flushes a sibling `.w1-stage-*.tmp`, closes its
write handle, then uses Windows `ReplaceFileW` with a uniquely named sibling
backup. Windows preserves supported original metadata, including creation time
and ACLs. A verified failure restores the backup; ordinary failures clean the
staging files. If recovery/cleanup is blocked, the error identifies the retained
backup and the idle disk check lists `.w1-*` remnants. Inspect those files before
manual recovery; Workbench never silently restores an ambiguous crash remnant.
Variants use no-clobber persistence. Exact published bytes are checked. This is
not a guarantee against arbitrary power loss, faulty storage or every Windows
filesystem. Publication is Windows-only; other platforms remain unverified.

The worker writes only disposable scratch data, denies personal-save reads,
imports rules from the selected checkout and suppresses bytecode. Cancellation,
project replacement and close reap active workers and clean their temporary
roots. **Open trusted game checkouts:** Python audit hooks prevent incidental
writes; they are not an OS sandbox against hostile Python/native libraries.

The canonical loader validates the complete structure catalog. A broken unrelated
catalog definition can block applying a draft until it is repaired. Discovery
and raw source inspection remain available when the loader reports structural
errors. Files over 1 MiB and unsafe destination names are outside W1 authoring.
No grid painting, other-family editing, profile changes, persistent edit history
or automatic campaign migration is included.

The semantic Pixi rendering shows actual terrain, initial objects and arrival;
colors/markers differ from the Pygame renderer. Inspection is revealed, without
player FOV, simulation, balance analysis or a natural-world selection claim.
The seed, exact large scene seed (string), catalog/source hashes and context
identify a repeatable controlled preview; this is not global gameplay replay.
Refresh after external source changes. A generic schema registry and W2 visual painting remain outside this delivery.

See [W1 delivery and evidence](docs/W1_DELIVERY.md) and the unchanged historical [W0 delivery](docs/W0_DELIVERY.md).
