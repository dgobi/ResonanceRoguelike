# W2 — Visual structure and interior authoring

26 October 2026, America/Edmonton. Production `main`; **W2 only**.

Implementation and publication identities are recorded below. Preflight `HEAD`,
local `origin/main` and remote readback were all
`6835fa5e9530cc08b087e2a03173db1fd905e0e5`.

The native Workbench now edits an ordinary building's terrain, decor and existing
direct containers through one text-preserving draft. It validates and previews
the exact unsaved draft through the production game, shows its diff, and saves a
unique variant through the existing guarded host transaction. The demonstrated
variant was saved and reopened in disposable runtime data. It is retained as a
[complete review artifact](examples/apothecary_w2_furnished.json), outside live
content and procedural selection. No gameplay code, selection profile or
personal campaign was changed.

## W1 reconciliation and source coverage

The attached W1 review was evidence-limited; it was used to select risks, not as
a certification. Actual W1 implementation is
`84cd66ecf3152029b4bd11a8b9c259cce1b605fa`, with delivery `6835fa5`. Actual W0
implementation is `23a1501`, cleanup `d26b63b`, and delivery `36cf60e`. The latest
gameplay implementation/delivery remains G17 `796b8fe` / `7745f72`; no gameplay
commit intervened. The sole pre-existing work was the owner's untracked
`RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md`, preserved separately.

Read root `AGENTS.md` (no nested instructions), supplied compass, decisions,
workflow and approved implementation/Workbench plans, issued W0/W1 briefs, the
W1 review and W2 brief, Workbench README, W0/W1 delivery records and their code
and tests. Inspected `tools/structure_authoring.py`,
`roguelike/docs/STRUCTURE_AUTHORING.md`, `engine.data_loader.DataLoader`,
`generation.structure_contract` (reader, compiler, catalog and capabilities),
`generation.placement` (profile validation/dependencies),
`generation.structure_preview` (preview/snapshot/access),
`generation.town_gen._stamp_building_at`, `engine.scene_generation.populate`,
and the current apothecary/workshop definitions and dependencies.

Before modifying the editor, independently ran the landed 7 TypeScript tests,
web production build, 10 Rust host tests, all 9 W0 and 3 W1 development-Python
process tests, and the existing packaged native W0/W1 journey plus forced
interruption/restart. Those passed. The embedded runtime separately ran 8 W0
tests with the missing-dependency control skipped; invoking W1 tests directly
with it could not import the sibling test module because of its isolated path.
The documented development interpreter ran the complete Python suites. This was
a test invocation issue, not a packaged worker failure.

The actual W1 boundary existed: opaque discovered document/review tokens,
strict game validation, byte/span fidelity, unique IDs, realpath/reparse checks,
source-hash conflicts, Windows replacement/rollback and no-clobber variants.
There was no foundation blocker or reason to rewrite W0/W1. One bounded
hardening was made: starting replacement validation revokes the previous host
review immediately, including failures before the worker returns. A native
negative test and Rust regression verify the old token is then unusable.

Checkpoint: `checkpoint/workbench-w2-start-20261026-a` at the preflight HEAD.
No branches, worktrees, duplicate development checkouts, resets or wiki changes.
Runtime fixtures copy only Python/data/dependency inputs under ignored
`.artifacts/`, without Git metadata or campaigns.

## Implementation and contract

| Files | Responsibility |
|---|---|
| `src/layout.ts`, `layout.test.ts`, `coordinates.ts` | Strict supported visual shapes, scoped JSON value edits, Unicode-aware row coordinates, stroke/fill geometry, container/linked-target edits, bounded canvas history and diagnostic locations |
| `src/LayoutCanvas.tsx` | Persistent Pixi application, reusable tile objects and high-resolution glyph textures, independent native layers, selection/problem markers, pan/zoom and CSS-pixel input mapping |
| `src/LayoutEditor.tsx` | Live catalogs, layer/brush controls, cell/record inspector, direct-container selectors, source/draft/saved views and production object evidence |
| `src/Authoring.tsx`, `App.tsx`, `protocol.ts`, `styles.css` | Existing canonical draft, stale-response suppression, portal into the center workspace, safe review/apply and dark desktop layout |
| `worker/bridge.py`, `worker/test_visual.py` | Isolated exact-draft production preview, catalog projection, existing game access checks, structured diagnostics and process-level negative tests |
| `src-tauri/src/authoring.rs`, `main.rs` | Versioned preview request confined to the existing document boundary, reviewed seed, fresh production revalidation before publication, old-review revocation |
| Native scripts and package/version files | App-local W2 journey, retained W0/W1 regressions, worker exit/timeout/cancel controls, Windows release/NSIS packaging |

Protocol **3**, app/worker **0.3.0**, unchanged game contract **g2-2**. No new
runtime library, state framework, renderer, database, generic registry or game
adapter file was introduced. Only Workbench files changed.

Terrain edits replace only affected `layers[y]` string values. Decor edits
replace individual `decor_layer[y][x]` values; the optional grid is initialized
only by an explicit first decor paint. Container edits replace only selected
fields, and optionally exact matching container target X/Y values. Unrelated
text, BOM, CRLF, unknown keys, nested arrays and other specials survive. Edited
values may be compactly reserialized; a no-op does not serialize or write.

The current route supports nested decor **rows** with string/null **cells**.
Historical array/object cells are preserved and freeze canvas mutation; there
is no array-to-string conversion. Direct `type`/`kind: container` records are
editable. Other live types and weighted alternatives remain inspect-only;
deferred body/stele physical behavior blocks successful draft preview with an
explicit unsupported diagnostic. Terrain palettes use existing legend entries;
decor/container/loot selectors come from the selected current DataLoader.

The canvas does not own another mutable document. Every visual operation edits
the W1 text draft. Source/property changes invalidate canvas history and old
validation. A drag, rectangle fill or container edit is one undoable operation;
history is capped at 100 and held only in memory. Text-field undo is left to the
text field. Invalid JSON/shapes and disk conflicts freeze mutation with a
recovery explanation. Native tests verify painting, visibility, keyboard focus,
both canvas edges after pan/zoom and a WebView device scale of 1.5. Unit tests
also cover DPR 1/1.5/2 and strongly rectangular 60 × 16 geometry with Unicode and
trailing spaces.

`preview_draft` writes the exact UTF-8 draft only into disposable current data,
then runs the canonical reader, loader and compiler. Production preview calls
`structure_preview.preview` → `_stamp_building_at` → `populate`; actual
container loot comes from the game roller/factory. The source/dependency identity
is rechecked afterward. The selected seed and draft hash accompany the result.
Rust issues a review only for the current valid draft and reruns this production
check with fresh inputs before publishing. The new request is rejected through
the generic renderer worker endpoint; it must use a discovered document token.

For buildings with a required entrance, the adapter supplies an explicit test
entry one cell outside the declared main entrance, required placement targets,
and every direct container to the existing game `check_access`. It does not
reimplement reachability or interaction rules. Failed access returns source
coordinates and a clickable diagnostic; duplicate/blocked containers fail the
actual population path. Buildings without a declared required entrance clearly
report access unverified. A preview is a centered, unrotated, revealed test scene
on grass—not a natural-selection or all-placement certification.

## Concrete native authoring demonstration

Selected current `commercial/apothecary_a.json`: **11 × 8**, three direct
containers, herbs and explicit version-one placement/access metadata.

1. Opened the native app with networking disabled; viewed canvas and raw source,
   previewed the clean draft, and verified unchanged source bytes/mtime.
2. Added test-only unknown nested metadata through Source to stress preservation.
3. Painted `w` / `worn_stone` at source **(2,3), (3,3), (4,3)** as one drag.
4. Filled **(3,2), (4,2)** with live `dried_herbs` decor.
5. Moved `special_tiles[0]` from **(1,1)** to **(2,1)**, selected `crate` and
   existing `workshop_b_fuel`, and deliberately moved its matching access target.
6. Undid/redid each visual operation and compared exact raw text. Valid raw
   changes refreshed the canvas; invalid text froze it without losing the draft.
7. Chose `apothecary_w2_furnished`, previewed exact unsaved bytes, examined the
   diff, confirmed the one-file variant write, reopened and previewed it again.

Seed **20261023**; centered origin **(35,17)**; unchanged game generation revision
**wg9**. The real crate appears at map **(37,18)** with one factory-created
**wood_bundle** from the existing pool. The source terrain/decor edits appear at
their translated map coordinates. Required static access checks pass.
The source apothecary and current selection-profile bytes remain unchanged.
Saving adds a definition, not a membership in current planned generation.
Historical flat-pool consumers can discover new files; the UI discloses this.

The compact receipt records hashes, scene seed, current source identity and
actual objects. The example's scoped `.gitattributes` retains the exact native
UTF-8/CRLF bytes (SHA-256
`c69a3711543603579eb2507424035e57b5473b7445cd8b7238159cb5e12fbdb4`).
Screenshots from the actual native WebView show
[authored layout](images/w2/authored-layout.png),
[production preview](images/w2/draft-production.png),
[diff confirmation](images/w2/review.png),
[a deliberately sealed route](images/w2/access-failure.png), and the
[1100 × 740 minimum window](images/w2/minimum-window.png).
No browser-only frontend result is counted as desktop evidence; no owner
desktop input was driven.

## Verification and packaging

Commands and ordinary controls are in [README](../README.md). Final results,
binary/source hashes and measured samples are retained in
[w2-verification.json](w2-verification.json). Larger outputs remain ignored in
`.artifacts/` and `src-tauri/target/`.

| Final command / control | Result |
|---|---|
| `npm.cmd run build:web` | TypeScript typecheck and Vite production build passed |
| `npm.cmd test` | 13 tests passed (7 retained, 6 visual-layer tests) |
| `cargo test --locked --manifest-path src-tauri/Cargo.toml` | 11 passed, including replacement/rollback fault cases and review revocation |
| `cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings` | Passed |
| `& $env:RESONANCE_PYTHON -B worker/test_bridge.py` | 9 passed, retained W0 process/negative cases |
| `& $env:RESONANCE_PYTHON -B worker/test_authoring.py` | 3 passed, retained W1 process cases |
| `& $env:RESONANCE_PYTHON -B worker/test_visual.py` | 5 passed; final run 31.056 s |
| `npm.cmd run build` | Windows release built |
| `npm.cmd run bundle` | Windows x64 NSIS built; final optimized Rust build 30.96 s |
| `npm.cmd run test:visual` | Packaged native W0 + W2 journey passed, 36.466 s |
| `npm.cmd run test:authoring` | Packaged native W0 + W1 passed, 54.115 s; forced interruption and fresh-process reopen passed separately |
| `rustc scripts/fault-worker.rs -o .artifacts/fault-worker.exe`; `WORKBENCH_TEST_MODE=<mode>` with `node scripts/desktop-test.mjs` | All 8 negative modes passed: `draft-worker-exit`, `draft-worker-timeout`, `draft-worker-cancel`, `protocol-mismatch`, `malformed-worker`, `worker-exit`, `slow-worker`, `missing-worker` |
| `& $env:RESONANCE_PYTHON -B scripts/measure-worker.py` | Three real bundled-worker timing/memory samples; authentic W0 terrain hash unchanged |
| Preservation comparison and `git diff --check` | Passed; 7,972 protected tracked/owner files and 7 save files unchanged in bytes, size, mtime and creation time; save-file set unchanged |

Python suites used the existing development interpreter at
`G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe`
(Python 3.11.0). Packaged positive native journeys used the bundled Python
3.11.0, without a `RESONANCE_PYTHON` override. Tests that write use disposable
data fixtures; worker-failure controls only hold unsaved drafts. The test-only
fault helper delegates normal reads to the real bundled worker, then fails the
draft preview. It is neither bundled nor used for positive evidence.

The final actual timeout surfaced `WORKER_TIMEOUT` after **90.536 s**. Draft
worker exit and cancellation returned in **53 ms** and **44 ms**, respectively.
Each left no verdict/review/apply capability or source-byte change. Retained
host tests exercise staged-write failure, post-replacement rollback and
concurrent bytes; native tests cover forged tokens, saves/code/traversal,
junction redirects, dependency changes and external source conflicts. All 12
final native modes left no worker scratch roots; their receipts record no
JavaScript errors or external network requests.

Windows **10.0.26200.0 x64**, Node **24.15.0**, npm **11.12.1**, Rust/Cargo
**1.95.0** with MSVC, Tauri Rust **2.12.5** / API **2.12.4**, React **19.3.1**,
Pixi **8.22.0**, Vite **7.3.7**, Playwright **1.56.1** and WebView2 user agent
**Chrome/Edge 155.0.0.0** were used. Existing lockfiles and pinned toolchain remain
in place; no package dependency was added. Positive native tests ran the built
release with WebView networking disabled.

The final native sample measured **594 ms** launch-to-shell and **4.982 s**
open-to-authentic W0 preview. One three-cell brush gesture took **51.31 ms** of
driver wall time. The draft's production generation took **77.99 ms**, and
55 animation callbacks occurred during its first 300 ms of asynchronous work.
Zoom interaction sampled 119 rAF intervals: median **5.5 ms**, p95 **5.7 ms**,
maximum **5.8 ms**. These are scheduling/responsiveness samples on this machine,
not a sustained 60-FPS painting benchmark. DPR 1.5 was emulated inside the native
WebView; no physical monitor settings changed. Native app working set was
28.2 MiB; the test's six WebView processes totaled 464.6 MiB. Three separate
real bundled W0 worker runs took 1.268–1.331 s wall time with about 53.2 MiB
peak working set. Complete raw counters are in the compact receipt.

Final local outputs (not committed):
`src-tauri/target/release/resonance-workbench.exe` (9,545,728 bytes) with adjacent
`bridge.py` and `python/`, and
`src-tauri/target/release/bundle/nsis/Resonance Workbench_0.3.0_x64-setup.exe`
(27,473,952 bytes). Their SHA-256 hashes, the actual tested Windows checkout file
hashes and screenshot hashes are in the receipt. Checkout hashes deliberately
include local line endings; Git may normalize other text files on checkout.

During verification, test-harness assumptions were corrected: immutable Tauri
IPC prevented an interception attempt, so the journey now reads the actual
visible production receipt; invalid raw JSON correctly removes the editable
canvas; and the refresh button includes its visible icon. One W0 hover/click
assertion timed out in a later regression run, then passed in the complete
rerun without a product change. One test launch terminated before producing a
malformed-worker receipt; its separate rerun passed. No root cause is claimed
for those transient harness failures. Running NSIS while a native test held its
output executable caused Windows sharing error 32; final packaging finished
successfully before the final native sequence. Only successful final receipts
are counted above. Higher-resolution Pixi glyph textures corrected an observed
blurred source-canvas screenshot before the final build.

## Publication and preserved owner work

Implementation commit:
[`f4620d92cfbf51a4dc7a0428742cab3e2948a424`](https://github.com/dgobi/ResonanceRoguelike/commit/f4620d92cfbf51a4dc7a0428742cab3e2948a424)
— `feat(workbench): add native layered building authoring with exact draft preview`.
The normal `git push origin main` succeeded, and
`git ls-remote origin refs/heads/main` returned that exact SHA. The local verified
checkpoint is `checkpoint/workbench-w2-verified-20261026-a` at this commit; the
start checkpoint remains at `6835fa5e9530cc08b087e2a03173db1fd905e0e5`.

The following documentation-only commit carries this delivery, compact receipt,
exact saved example and five native screenshots. The final remote tip is supplied
in the owner handoff. No binaries or runtime fixture trees are committed. The
owner's pre-existing untracked proposed plan remains untracked and byte-identical.
Only `workbench/` is part of W2; the game, wiki edition, selection profiles and
campaigns retain their preflight contents and metadata.

## Limits retained

Only ordinary buildings, existing legend glyphs and existing direct containers
have visual editing controls. No new special creation/deletion, transforms,
loot-pool editor, authored-submap editor, WFC, selection changes or campaign
migration. The original HTML painter and owner wiki remain untouched. Other
families retain their prior inspection boundaries.

The source canvas is semantic, not a game screenshot. Static access uses
revealed visibility, one chosen entry and current initial population; it does
not prove player balance, natural selection, other transforms or whole-world
placement. Worker audit hooks protect against incidental writes but are not an
OS sandbox for hostile Python/native libraries. Open trusted checkouts.

History remains memory-only; forced process termination loses unsaved work while
leaving source intact. Windows is the tested target. The executable/resources and
NSIS artifact are built; installer UX, signing, updates, first installation on a
machine without WebView2, and macOS/Linux remain unverified. The installer was
not installed into the owner's application registry.

Implementation references: [Pixi graphics](https://pixijs.com/8.x/guides/components/scene-objects/graphics),
[Microsoft JSON text spans](https://github.com/microsoft/node-jsonc-parser/blob/main/README.md),
and [Tiled layer separation](https://doc.mapeditor.org/en/stable/manual/layers/).
The installed Pixi 8.22.0 API declarations and actual game source govern behavior.

**W2 stops at this complete authoring route.** No further Workbench or gameplay
milestone is commissioned by this delivery.
