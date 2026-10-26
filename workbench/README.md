# Resonance Workbench · W2

An independent, local Tauri 2 desktop application for inspecting Resonance and
safely drawing and editing one ordinary-building definition at a time. The game remains the
validation authority. No campaign, running game or Internet service is required.

## Author one building

1. Open the current checkout. It starts read-only and retains W0's actual
   `starting_lab` 80 × 43 production preview.
2. Search by ID, description/name or relative path, optionally filter by folder.
   All immediate `data/buildings/<category>/*.json` ordinary buildings appear
   deterministically (58 at the W1 source baseline). Plazas are listed as
   unsupported/read-only; authored layouts retain W0 read-only inspection.
3. Select a building such as `commercial/apothecary_a.json`. Source, properties,
   diagnostics, file hash, source revision and worker compatibility are visible.
   **Begin edit** opts into one in-memory draft. The **Authored layout** shows
   native terrain glyphs, decor dots and placed-record markers. Select the active
   layer, search its palette, and use Pencil or Fill. Description, scalar fields
   and visual operations use text-span edits; **Source** exposes the same strict JSON.
4. Select an existing container marker or choose it under **Placed records**.
   Change its X/Y, choose an actual container decor ID, and add/remove existing
   loot-pool references. **Apply container edit** stages one undoable operation.
   The checked option moves matching container access targets with the record;
   the diff exposes these explicit companion edits. Other special types remain
   inspect-only, including their nested alternatives and unknown fields.
5. **Preview draft** or **Validate draft** runs `read_document`, `DataLoader`,
   `compile_structure`, the production building stamper and population factories
   against disposable current data. Problems distinguish syntax, references,
   physical placement and game access failures. **Locate cell / record** navigates
   diagnostics with source coordinates. Failed or stale output clears the draft
   preview and cannot authorize apply. The preview's receipt identifies exact
   draft bytes, dependencies, worker/game source, seed and actual created objects.
6. Inspect **Diff**, then **Review & apply**. The confirmation repeats the exact
   diff and warns about existing world references. The host revalidates the exact
   stored bytes with fresh dependencies before publishing one file. The receipt
   records target, before/after hashes and existing/variant outcome. The index,
   editor and preview reopen from disk.
7. Prefer **Save as new variant** for identity or meaning changes. Enter a unique
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

There are three explicitly different views: **Authored layout** is the exact
source representation; **Draft production preview** is the current validated
unsaved draft; **Saved production preview** is the opened disk snapshot. W0's
starting laboratory retains its independent authentic 80 × 43 generated scene.
All production views are revealed semantic renderings, not player FOV or Pygame
sprite fidelity. Terrain/decor colors and record markers explain layers; they
do not create gameplay rules.

Draft checks stamp the ordinary building, centered without rotation into an
80 × 43 grass test scene, then call `engine.scene_generation.populate`. Actual
container contents come from the game's loot roller and item factory. With a
required declared entrance, existing `structure_preview.check_access` verifies
required placement targets and every directly editable container from one cell
outside the main entrance. These are static game reach/interaction checks with
revealed visibility. Buildings without a required entrance explicitly report
access unverified. No natural selection, all-transform placement, simulation or
balance certification is implied. Failed physical placement/access blocks saving.

## Canvas controls and preservation

- **V** selects/inspects; **B** pencils; **R** fills a dragged rectangle;
  **E** erases; **H**, Alt-drag or middle-drag pans. Wheel zooms; Home fits.
- Layer checkboxes independently show terrain, decor and placed records.
  Painting a hidden active layer is disabled. Coordinates are zero-based X/Y.
- Terrain uses only existing legend glyphs. Null-mapped glyphs leave the
  underlying test-context terrain intact; they do not mean floor. Weighted glyphs
  retain their native weights and resolve only in production preview.
- Decor uses the current dependency catalog. Erase writes `null`; terrain erase
  requires an existing null-mapped glyph. A missing decor grid is created only
  when explicitly painting its first cell. Current `g2-2` accepts nested row
  arrays with string/null cells. Historical array/object **cells** are preserved
  in Source and freeze visual mutation; they are never stringified or flattened.
- **Undo canvas / Redo canvas**, or Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y with canvas
  focus, undo a whole drag, fill or container edit. Text inputs keep their own
  undo. Any raw/property/variant-ID edit clears the canvas history explicitly.
  History holds up to 100 visual operations and is not persisted across sessions.
- Invalid JSON, unsupported native shapes and disk conflicts freeze painting.
  Correct Source or discard/reload; the canvas never overwrites an invalid draft
  with an older snapshot. Unknown metadata and unrelated source spans survive.
- Validation is asynchronous; newer edits supersede responses. Use **Cancel
  authoring request** to terminate a preview worker. Publication itself cannot
  be interrupted halfway through the trusted host transaction.

The complete [W2 demonstrated variant](docs/examples/apothecary_w2_furnished.json)
is a review artifact outside the live content catalog. It was created/reopened
through the native app on disposable current data. Its terrain changes at
(2..4,3), herbs at (3..4,2), and crate moved from (1,1) to (2,1) are described in
[W2 delivery](docs/W2_DELIVERY.md). Its pool is the existing `workshop_b_fuel`;
no pool definition or procedural membership was added.

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
npm.cmd run test:visual              # native canvas + exact draft preview + variant/reopen
& $env:RESONANCE_PYTHON -B worker/test_authoring.py
& $env:RESONANCE_PYTHON -B worker/test_visual.py
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
Modes `draft-worker-exit`, `draft-worker-timeout` and `draft-worker-cancel`
first open a real building and unsaved draft, then fail only its production
preview. The timeout mode exercises the host's actual 90-second deadline.
`missing-dependency` additionally takes `WORKBENCH_EMPTY_PYTHON`, a disposable
CPython runtime without the game dependency wheels.

## Contract and limits

The protocol is **3**, worker/app **0.3.0**, game structure contract **g2-2**.
W0 identify/describe/inspect/preview requests remain read-only. Draft validation
is available only through the host's document boundary. Discovery grants an
opaque document token; validation grants a one-draft review token. Apply takes
that token and explicit confirmation, never an arbitrary destination or trusted
frontend verdict. W2's validation token is issued only after the exact draft's
production preview passes; apply repeats that check with the reviewed seed and
fresh dependencies. Starting replacement validation revokes an older review even
if the new worker fails or is cancelled. Variants stay in the discovered source's existing category.
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
filesystem. Existing-file replacement is Windows-only; other platforms remain unverified.

The worker writes only disposable scratch data, denies personal-save reads,
imports rules from the selected checkout and suppresses bytecode. Cancellation,
project replacement and close reap active workers and clean their temporary
roots. **Open trusted game checkouts:** Python audit hooks prevent incidental
writes; they are not an OS sandbox against hostile Python/native libraries.

The canonical loader validates the complete structure catalog. A broken unrelated
catalog definition can block applying a draft until it is repaired. Discovery
and raw source inspection remain available when the loader reports structural
errors. Files over 1 MiB and unsafe destination names are outside W1 authoring.
Other-family visual editing, special creation/deletion, new legend definitions,
transform tools, loot editing, selection-profile changes, persistent edit history
and automatic campaign migration remain outside W2. Deferred physical specials
are visible and preserved, but block a successful draft preview with an explicit
unsupported diagnostic. Other live special types are inspect-only on the canvas.

The semantic Pixi rendering shows actual terrain, initial objects and arrival;
colors/markers differ from the Pygame renderer. Inspection is revealed, without
player FOV, simulation, balance analysis or a natural-world selection claim.
The seed, exact large scene seed (string), catalog/source hashes and context
identify a repeatable controlled preview; this is not global gameplay replay.
Refresh after external source/dependency changes. The palette represents the
catalog at open time; every validation and apply rereads current dependencies.
A generic schema registry and further W milestones remain separate work.

See [W2 delivery and evidence](docs/W2_DELIVERY.md), [W1 delivery](docs/W1_DELIVERY.md)
and the unchanged historical [W0 delivery](docs/W0_DELIVERY.md).
