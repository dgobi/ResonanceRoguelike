# W3A — Contextual loot pools and source tracing

26 October 2026, America/Edmonton. Production `main`; W3A only.

The native Workbench now opens a direct building container's actual contextual
pool, edits it through the existing shared draft/validation/diff transaction,
saves and reopens a unique pool variant, and retains the building draft for an
explicit link to that pool. Item definitions are read-only. The demonstration
publishes a separate building variant and observes real factory-created items
through the existing production preview. Workbench slogans were replaced with
functional labels. No gameplay rules, shipped content, campaigns or wiki changed.

## Reconciliation and checkpoint

Before edits, `HEAD`, local `origin/main` and `git ls-remote origin refs/heads/main`
all returned `e29694748ebca4522726e9e799b8c7377d754c78`. W2 implementation is
`f4620d92cfbf51a4dc7a0428742cab3e2948a424`; its actual delivery, receipt, screenshots,
saved example and tests are present under `workbench/docs/`. No gameplay commit
intervened after the W2 implementation/delivery pair. The only pre-existing work
was the owner's untracked `RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md`.

Read the root `AGENTS.md` (no nested AGENTS files), approved Workbench plan,
attached W2 review and W3A brief, actual W2 delivery, README, and relevant
authoritative structure guide/owner decisions. Inspected:

- `src/App.tsx`, `Authoring.tsx`, `draft.ts`, `layout.ts`, `LayoutEditor.tsx`,
  `LayoutCanvas.tsx`, `MapView.tsx`, protocol and styles: navigation, one canonical
  draft, source spans, history, diagnostics, preview and UI strings.
- `src-tauri/src/main.rs`, `authoring.rs`, capabilities and resource config:
  discovery, document/review tokens, allowlisting, canonical/reparse checks,
  source locks, fresh validation, replacement, no-clobber variants and rollback.
- `worker/bridge.py`, current bridge/authoring/visual tests and native journeys:
  handshake, isolated scratch roots, audit guard, timeout/cancellation and actual
  Windows/WebView2 evidence.
- `roguelike/engine/data_loader.py`, `loot_roller.py`, `scene_generation.py`,
  item-factory path, `generation/structure_contract.py`, structure preview and
  building stamper: actual source identity, pool validator and production
  selection/population. Read the current pool files, apothecary/container route
  and current authoritative `roguelike/docs/STRUCTURE_AUTHORING.md`.

Independently reran the pre-change 13 TypeScript, 11 Rust, nine W0, three W1 and
five W2 Python tests and web build. All passed. The existing packaged W2 journey
also passed: authentic W0 preview, canvas edits, exact draft preview, diff,
save-as-variant/reopen, access rejection, stale response and external conflict;
80.934 seconds. This is current execution evidence, not reliance on the supplied
evidence-limited review. No unsafe W2 foundation blocker was found.

Start checkpoint: `checkpoint/workbench-w3a-start-20261026-a`, at the preflight
SHA above. All development stayed in this checkout on `main`. Test fixtures copy
only required Python/data inputs under ignored `.artifacts/`, without Git or
campaigns. They are runtime fixtures, not additional development checkouts.

## Implementation and exact supported contract

App/worker **0.4.0**, protocol **4**, unchanged game contract **g2-2**. Existing
lockfiles retain dependency versions. There is no new runtime dependency,
filesystem permission, generic editor registry, graph system or write endpoint.
All implementation changes are under `workbench/`.

`PoolEditor.tsx` and `pool.ts` add an ordered compact table, existing item-ID
selectors, roll bounds, row add/remove, history and read-only item source.
`Authoring.tsx` retains ownership of the exact text, validation revision, diff
and confirmation for both families. Raw changes immediately update valid table
data; invalid/duplicate-key JSON freezes mutation. Raw/property/ID edits clear
table history so Undo cannot revert an unrelated source edit. Default values
display without serialization; opening/closing clean source does not write.

The host retains at most one building and one pool document capability, with
separate original bytes/reviews. Contextual navigation keeps the building
component/draft mounted. Each apply remains one reviewed file. Saving either
revokes both reviews and clears frontend verdicts while retaining the other
draft. The new allowlist is limited to immediate
`roguelike/data/loot_pools/<safe-id>.json` files; all existing confinement and
Windows replacement/rollback code is reused. The worker and renderer gain no
live-file writing capability. **Reload pool** supports conflict recovery.

The 17 current contextual pools and 79 loaded item IDs come from the selected
checkout. Search includes IDs, paths and descriptions. Only single-object pool
files in that immediate directory are editable. `data/loot/`, nested or
array-of-pools authoring, item/recipe editing and other consumers are outside
this editor. The read-only direct-container references list is intentionally
limited to ordinary buildings; it is not a whole-game usage census.

| Field | Existing game rule used |
| --- | --- |
| `id` | Unique nonempty pool ID; host variant identity must also be a safe different ID matching its filename. |
| `description` | Retained metadata, editable explicitly; authored fiction is otherwise unchanged. |
| `items` | Ordered records with existing `item_id`; absent/empty means no loot. Repeated IDs remain independent entries. |
| `weight` | Relative finite nonnegative number, default 1. Nonempty rows require positive finite total weight. |
| `roll_count` | Inclusive ascending range of one/two nonnegative integers, at most `2^53−1`; default `[1,1]`. One value is fixed count. |

`Validator.pool` already provides sufficient game-owned field/reference rules;
no game adapter or loader/roller change was necessary. The worker additionally
checks unique source identity and verifies `DataLoader` loaded the exact staged
definition. This catches the loader's skipped/overwritten definitions instead
of presenting them as safely editable. For example, the structure reader accepts
a UTF-8 BOM but the pool loader does not: source bytes remain preserved and
publication is blocked. Unknown top-level/entry metadata is retained with
inactive-field warnings. Quantity/conditions/text binding do not acquire new
semantics. Invalid raw source and invalid item references cannot be published.

One narrow linking hardening extends building validation: a direct container's
pool must have exactly one loaded source definition. A subsequently introduced
duplicate ID cannot silently redirect the link through loader overwrite order.
This is covered by the production-chain regression; no broad W2 redesign occurred.

Selection is the current `roll_pool` implementation: weighted draws without
replacement **by entry**, count capped to entry count, stop when remaining total
weight is zero. Each referenced pool rolls independently. No frontend RNG,
derived drop percentages or frequency simulation was added.

## Native demonstration and provenance

The complete review-only examples are
[new pool](examples/alchemist_reagents_w3a.json) and
[new building](examples/apothecary_w3a_loot.json), outside the live catalogue.

1. Opened `commercial/apothecary_a.json`, began a new building variant, added
   nested preservation-test metadata and retained that unsaved draft.
2. Clicked its actual `special_tiles[0]` medicine chest at source **(1,1)** and
   followed the declared `alchemist_reagents` pool. Returned and reopened it,
   proving exact source/mtime no-op and retained building draft.
3. Added test-only nested metadata through Source, then changed the first
   `crow_bile` entry's weight **50 → 57** through the table. The native assertion
   proves that operation changes only that value span. Undid/redid it; invalid
   raw text froze controls and valid text refreshed them. Inspected
   `roguelike/data/items/butchery/crow_bile.json`, including its unchanged prose.
4. Rejected an unknown item, suppressed a delayed verdict after a newer raw edit,
   then validated/diffed/confirmed `alchemist_reagents_w3a` and reopened it.
   The original building and pool remained unchanged and no link changed itself.
5. Returned to the same building draft, selected the new pool deliberately,
   applied the container edit, and previewed `apothecary_w3a_loot`. The real
   centered, unrotated stamper/populator/factory created container contents;
   access checks passed. Saved and reopened the separate building variant.
6. Closed/reopened the project and followed the saved structure/container/pool
   chain again. Native host negatives independently proved pool and building
   external conflicts, changed-item dependency rejection on apply, old-review
   revocation, and protected-path rejection.

The final sample uses seed **20261023**, source origin **(35,17)**, medicine chest
at map **(36,18)**, and scene seed
**304619724305388012169893894248904913436**. It created `prophets_eye_cap` and
`sulphur_cap_fragment` through the actual item factory. The receipt records the
full item objects and game/catalog identities. The game source SHA-256 is
`79debddbf4860b264d8f7cb3df1fff6adf78c82021377ee07503ab384fda38d3`.
Fixtures have no Git metadata, so their runtime `commit` is explicitly null;
the preflight source revision and tested file hashes bind this evidence.
Different earlier fixture bytes produced different scene seeds; only the final
fixture/receipt is the delivered example. No small sample establishes frequency,
world selection, player discoverability or gameplay-effect behavior.

The trail shows the actual opened structure path/hash separately from the draft
target, container record/coordinate, current pool path/ID and inspected item
path/ID. Declared references, current validation and observed population are
separately labeled. A newly saved unreferenced pool remains visible and usable;
no multi-file atomicity is claimed. Existing selection-profile bytes are unchanged.

## UI wording and visual review

Reviewed UI strings in all five screen components plus host/worker messages,
including project open, browser, raw/table/canvas editor, loading, validation,
preview, conflict, confirmation and errors. Targeted source assertions cover the
known regressions without scanning or rewriting game-authored content.

| Previous UI text | Result |
| --- | --- |
| A place to understand the world. | Content editor |
| Your world, under the lens | Generation preview |
| Reading the living source | Loading source |
| Local map study | Generation preview |
| Build a furnished place | Structure editor |
| Explore the map | Select a cell |
| Keep your unsaved draft? | Discard unsaved changes? |
| W2 / ordinary-building-only scope labels | W3A / buildings and contextual loot pools; explicit retained-draft/item-read-only scope |

Actual native screenshots were inspected, including startup, content browser,
structure editor, pool/item source, rejected validation, save dialog, generated
scene and minimum 1100×740 window. The known phrases are explicitly absent from
rendered startup and representative workflow screens. The dark visual design
and useful technical explanations remain. Retained screenshots:
[startup](images/w3a/startup.png), [structure](images/w3a/structure-draft.png),
[pool and item](images/w3a/pool-item-trace.png),
[validation](images/w3a/pool-validation.png),
[save review](images/w3a/pool-review.png),
[production](images/w3a/linked-production.png),
[reopened trail](images/w3a/reopened-chain.png),
[minimum window](images/w3a/minimum-window.png).

The owner's copy requirement governs; consulted primary guidance on
[Windows UI text](https://learn.microsoft.com/en-us/windows/win32/uxguide/text-ui)
and [concise wording](https://learn.microsoft.com/en-us/style-guide/word-choice/use-simple-words-concise-sentences).
The installed text-span APIs and actual host boundary govern implementation;
consulted [JSON text edits](https://github.com/microsoft/node-jsonc-parser/blob/main/README.md)
and [Tauri filesystem scopes](https://v2.tauri.app/plugin/file-system/).

## Verification, packaging and preservation

Commands run from `workbench/`, except the targeted game suites:

| Command/control | Result |
| --- | --- |
| `npm.cmd run build:web` (also inside bundle) | TypeScript and Vite production build passed |
| `npm.cmd test` | 18 passed: retained 13 plus five pool/copy tests |
| `cargo test --locked --manifest-path src-tauri/Cargo.toml` | 13 passed, including pool slots, paths, conflict, no-clobber variant and injected rollback |
| `cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings` | Passed |
| `& <development-python> -B -m unittest discover -s worker -p 'test_*.py' -v` | 21 passed: W0 9, W1 3, W2 5, W3A 4; 106.551 s |
| Root: `PYTHONPATH=<repo>/roguelike;<repo>/tools/critical_fix_regressions/tests`; `python -B -m unittest test_structure_contract test_structure_access` | 12 passed, 4.670 s; disposable saves |
| `npm.cmd run build`; `npm.cmd run bundle` | Windows release executable/resources and x64 NSIS built |
| `npm.cmd run test:pools` | Final native W0 + W3A chain and safety journey passed, 43.766 s |
| `npm.cmd run test:visual` | Native W0 + retained W2 canvas/preview/variant/access/conflict journey passed, 38.853 s |
| `npm.cmd run test:authoring` | Native W0 + retained W1 safe authoring; forced unsaved-process interruption and fresh restart passed |
| `rustc scripts/fault-worker.rs -o .artifacts/fault-worker.exe`; `WORKBENCH_TEST_MODE=<mode>` with `node scripts/desktop-test.mjs` | Five native negatives passed: `pool-worker-exit`, `pool-worker-cancel`, `pool-worker-timeout`, `protocol-mismatch`, `malformed-worker` |

Pool worker exit returned in **62 ms**, cancellation in **57 ms**, and the real
host timeout surfaced `WORKER_TIMEOUT` after **90.274 s**. Each left no verdict,
review/apply capability, source-byte change or temporary worker roots. The helper
delegates normal reads to the real bundled worker and deliberately fails only
the requested draft operation; it is not packaged or used for positive evidence.
All final native receipts report no JavaScript errors or external network calls.

The compact [verification receipt](w3a-verification.json) carries final native
controls, timings, platform versions, tested file/binary/example/screenshot hashes
and preservation results. Full logs and runtime fixtures stay ignored under
`.artifacts/`; no test takes over the owner's desktop. Native windows receive
app-local DOM/CDP events with WebView network disabled. Positive journeys use
the bundled interpreter, without `RESONANCE_PYTHON` override.

Development Python: `G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe`
3.11.0, supplying pinned dependencies only; imports remain from current source.
Windows x64, Node 24.15.0, npm 11.12.1, Rust/Cargo 1.95.0/MSVC, Tauri Rust 2.12.5 /
API 2.12.4, React 19.3.1, Pixi 8.22.0, Vite 7.3.7, Playwright 1.56.1 and WebView2
155 were used. No dependency version changed.

Bounded final measurements cover the actual 17-pool/79-item catalogue and the
six-row reagent pool: container-to-pool navigation **567 ms**, one table input
edit **6.93 ms** driver wall time. These are local observations, not universal
latency or sustained-frame-rate promises. Native W0 frame/startup counters are
also retained in the receipt.

Preservation comparison passes for **7,972 protected files and seven save files**:
bytes, size, measured mtime and source creation time unchanged; save file set
unchanged. The owner's untracked plan remains byte-identical and untracked.
Only Workbench implementation and its guide/evidence are in this delivery.

The installer was built, not installed into the owner's application registry.
Signing, updates, a clean machine without WebView2, installer UX and non-Windows
targets remain unverified. Draft/history state remains memory-only; forced
termination loses drafts while source stays intact. Python audit hooks prevent
incidental writes but are not an OS sandbox for hostile checkouts.

## Publication

Implementation commit:
[`0b492dcbd778bd65b88932908f5c9f9bfd85e8fb`](https://github.com/dgobi/ResonanceRoguelike/commit/0b492dcbd778bd65b88932908f5c9f9bfd85e8fb)
— `feat(workbench): add contextual loot pool authoring and source tracing`.
Normal `git push origin main` succeeded, and
`git ls-remote origin refs/heads/main` returned that exact SHA. The local verified
checkpoint is `checkpoint/workbench-w3a-verified-20261026-a` at this commit;
the start checkpoint remains at `e29694748ebca4522726e9e799b8c7377d754c78`.

The following documentation-only commit carries this delivery, compact receipt,
exact native variants and eight reviewed screenshots. The final documentation
tip/readback is supplied in the owner handoff. No task branch, worktree, reset,
forced push, history rewrite or binaries are part of the commits. The owner's
pre-existing untracked proposed plan remains separate and unchanged.

W3A stops at this source-to-loot workflow. W3B item/recipe editing, generalized
graphs and W4–W7 remain separate decisions.
