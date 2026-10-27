# W4A delivery — creature definitions and factory preview

Verified 26 October 2026, America/Edmonton (final native run 27 October UTC).

W4A is complete. Workbench 0.7.0 can browse current creature sources, edit a
supported revenant's name and effective HP, publish a new-ID variant through the
existing exact-draft writer, reopen it and construct a real production actor.
The demonstrated change is **14 → 19 HP**, with both initial and maximum HP 19.
No active creature, selection table, campaign, personal save or wiki was changed.

## Revision and W3C reconciliation

- Checkout: `G:\GameDev\RoguelikeProject`, branch `main`; existing remote
  `https://github.com/dgobi/ResonanceRoguelike`.
- Before implementation, local `main`, `origin/main` and live remote `main` all
  resolved to `6c60982cda4ae0fd08aeb0aeac66edf7fafadd1e`.
- W3C implementation was `e76e92a184d7bfd4c6356f2e9ec2e2bb92a683ec`.
  The previously unspecified final evidence commit was **6c60982** above.
  There were no subsequent intervening commits. Nothing was reset.
- W4A implementation: **`c668742eaf0a84c69838568cbb99034456485bb2`**, pushed to
  existing `origin/main` and verified by `git ls-remote` before this evidence commit.
- Named local checkpoints: `checkpoint/workbench-w4a-start-20261026-a` at the
  baseline and `checkpoint/workbench-w4a-verified-20261026-a` at implementation.
  No development copy, worktree or task branch was created.
- This report and its companion artifacts form the subsequent evidence commit.
  Its own SHA cannot be embedded in its committed bytes. The final handoff and
  `workbench/.artifacts/w4a/final-publication.json` record the exact implementation
  SHA, evidence SHA and verified final remote tip after pushing. The delivered
  Downloads copy of this report also appends those exact values. Resolve this
  tracked report's evidence commit with
  `git log -1 --format=%H -- workbench/docs/W4A_DELIVERY.md`.

W3C's historical counts were treated as reported evidence. Before editing, this
session reran 24 TypeScript tests, 16 Rust tests, four real recipe worker tests,
and the packaged W3C recipe journey, all passing (115.560 seconds combined).
The shared document/review boundary, atomic writer, source navigation and native
route were inspected. Final regression results below cover the expanded code.

## Delivered contract

The additive game-owned `engine.creature_authoring` adapter is read-only and is
not imported by gameplay. Worker protocol **7**, worker/app **0.7.0**, creature
capability **`revenant-hp-1`** identify the boundary. No existing game spawning,
AI, combat, serialization or save implementation changed.

The current loader exposes 13 non-player creature records plus the separate
player. Its permissive skip/last-wins behavior is unchanged; authoring independently
refuses duplicate keys, ambiguous IDs, case collisions and required unresolved
references. The original single-object source identity and supported shape grant
entitlement. Raw category, ID or AI changes cannot promote an unsupported source.
`hollow_revenant` is the one shipped writable source. Player, special-ability
knights, advanced vine records, unsupported entities and arrays remain read-only.

Supported fields are literal `Actor.name` (1–256 characters) and **Effective HP**
(integer 1–1,000,000). Those are explicit authoring bounds. The real factory uses
`base_hp` before `fighter.max_hp`, defaulting to 10; `Fighter` initializes current
HP from maximum HP. Typed HP changes update both persisted values in one history
operation. Only ID/name/the two HP fields may differ in a published raw draft.
Typed operations preserve every other source span; raw operations preserve other
JSON values, including nested unknown metadata and ordered arrays.

Descriptions remain read-only because the current look UI resolves them by
`actor.tile`, not the new definition ID. AI, damage, attacks, limbs, harvesting,
perception, faction/hostility, effects and spawn declarations are also read-only.
The actual `TileRegistry` resolves tiles and referenced harvest items must be
unique. Faction strings are membership labels, with no separate faction registry.
The factory's absent `body_human` fallback is disclosed: this source has inline
limbs, which `combat.get_body_def` prioritizes, so that unused fallback is a warning.

Creatures use the existing browser, Source, Problems, Diff, history and writer.
Five independent building/pool/item/recipe/creature drafts survive navigation.
The new inspector adds Supported fields, Read-only fields, Factory result and
Direct layout references. Layout inspection retains a parked structure draft.
Catalogue pages render at most 100 rows. Minimum-window tabs and independent
scrolling were inspected in the actual native window.

Publication is variant-only, one new unique file beside the discovered source.
The original source entitlement, exact reviewed bytes, revision and dependency
identity remain host-bound. The existing safe-path/no-link, atomic/no-clobber,
rollback and reopened-hash checks remain in use. No second write API was added.
Invalid JSON, external changes, cancelled/replaced jobs and late responses revoke
or suppress obsolete validation/factory evidence.

## Production evidence and its limits

The [example](examples/hollow_revenant_w4a.json) was published and reopened in a
disposable data root through the packaged app. Its exact SHA-256 is
`913f9216d3c1693f346a250a9ff1153348ad00610c321f0dbbdd96bc42d013b3`.
The [factory receipt](examples/hollow_revenant_w4a.factory.json) SHA-256 is
`ef02b03a773ce2eea03b18a9d4d7120a644dea36a507d3991fec0217ebc4c613`.
Both committed artifacts are outside the active catalogue, with byte-preserving
Git attributes. The original disposable fixture included nested `w4a_metadata`
before opening; the journey verifies it survives publication. Shipped data and
authored description were not edited to produce this demonstration.

The actual `DataLoader → CreatureFactory.spawn → Actor/Fighter/Perception/AI`
path observed `hollow_revenant_w4a`, name `Hollow Revenant W4A`, `WanderingAI`,
tile `hollow_revenant` and HP/max HP **19/19**. The receipt records exact source,
loaded catalogue, worker and game-source hashes. The disposable root has no Git
repository, so its Git identity is honestly null; the game-source hash binds it
to the tested implementation:
`ce61e2d93600447728c81559fe98896667387a02bc99592dd7d6297162b0654a`.

Direct layout references are saved, top-level `authored_submap` creature
declarations with paths and coordinates. Ordinary buildings, plazas and entrance
layouts gain no placement entitlement. `spawn_zones` has no current Python
consumer; zone creature lists, town selectors and resonance-spawn rules are
separate authorities. New definitions do not join those lists, replace saved
actors or change rooms. An empty reference table is limited to this supported
direct route, not a claim that every possible use has been found.

G17 corroboration used its existing production validator/preview and example,
with the exact variant installed only in copied test data. A direct creature at
source **(7,2)** produced the real 19-HP actor at **(42,20)**, origin **(35,18)**,
away from arrival **(37,23)**. Moving it to source **(2,5)** was rejected for
overlapping arrival/a physical stair. No selection membership was added. This
proves initial construction and occupancy; it runs no AI/combat turns, campaign,
save, natural encounter, balance assessment or persistence/defeat replay.

## Verification

Windows **10.0.26200**, x64; Node **24.15.0**, npm **11.12.1**, Rust/Cargo
**1.95.0**, CPython **3.11.0**, native WebView2 **155**. The actual bundled runtime
reported pygame 2.6.1, tcod 19.3.0, NumPy 2.4.6, cffi 2.1.1, pycparser 3.11 and
typing_extensions 4.16.0. Development Python was
`G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe`;
game imports came from the selected checkout. No historical source copy was used.

Commands below ran from `workbench/`, except the game tests from repository root.
Seconds are measured wall time, except the native creature journey's own elapsed
receipt. [Machine evidence](w4a-verification.json) retains precise values, source
hashes, commands, native checks, preservation and local-log hashes.

| Verification | Result | Seconds |
| --- | --- | ---: |
| `npm.cmd test` | 27 passed | 1.890 |
| `npm.cmd run typecheck` | passed | 5.534 |
| `cargo test --locked --manifest-path src-tauri/Cargo.toml` | 17 passed | 4.745 |
| `cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings` | passed | 2.304 |
| `python -B -m unittest discover -s worker -p test_*.py -v` | 34 passed | 436.554 |
| `python -B -m unittest discover -s worker -p test_creatures.py -v` | final focused 5 passed | 47.075 |
| `python -B -m unittest test_structure_contract test_structure_access test_crafting test_gameplay_g17 -v` | 34 passed | 14.251 |
| `npm.cmd run bundle` | executable and NSIS built | 92.071 |
| `npm.cmd run test:creatures` | packaged offline journey passed | 59.827 |
| `npm.cmd run test:recipes` | packaged W3C regression passed | 130.702 |
| `npm.cmd run test:visual` | packaged W2 regression passed | 58.809 |
| `npm.cmd run test:items` | packaged W3B regression passed | 59.099 |
| `WORKBENCH_TEST_MODE=creature-worker-exit npm.cmd run test:desktop` | passed | 7.543 |
| `WORKBENCH_TEST_MODE=creature-worker-cancel npm.cmd run test:desktop` | passed | 7.693 |
| `WORKBENCH_TEST_MODE=creature-worker-timeout npm.cmd run test:desktop` | real 90-second deadline passed | 97.075 |
| `WORKBENCH_TEST_MODE=protocol-mismatch npm.cmd run test:desktop` | passed | 1.571 |
| `WORKBENCH_TEST_MODE=malformed-worker npm.cmd run test:desktop` | passed | 1.611 |

PowerShell fault modes use `$env:WORKBENCH_TEST_MODE` before the listed npm command.
The test-only fault executable was built with
`rustc scripts/fault-worker.rs -o .artifacts/fault-worker.exe`; it is not shipped.
Game tests used `PYTHONPATH=roguelike;tools;tools/critical_fix_regressions/tests`
and dummy SDL video/audio. An initial invocation omitted `tools`, causing a G17
fixture import error; the corrected command passed all 34 tests.

Native evidence covers the complete browse/edit/validate/diff/save/reopen/factory
route, five parked drafts, unknown metadata, undo/redo, invalid raw freezing,
source-reference navigation, late-result suppression and dependency invalidation.
Host negative cases deny forged documents/reviews, raw player/advanced promotion,
stale source/dependencies, concurrent destinations, traversal, ADS and junctions.
Rust tests exercise write failure, conflict, no-clobber and rollback through the
existing writer. W1/W3A are covered by the full worker/Rust suites and navigation;
their unchanged native routes were not multiplied into a redundant full campaign.

One native iteration exposed JSON `1.0` versus `1` comparison; immutable values
now compare JSON numbers semantically while keeping booleans distinct. A test
rejects `true → 1`. Final full-worker/native checks passed. After the full worker
suite, the final diagnostic-only correction to `combat.get_body_def` was checked
by the focused five tests and final packaged creature journey. Earlier failed
iterations are not counted as passing evidence.

The final native run recorded zero external requests, zero console errors and no
remaining worker temporary roots. App-local CDP/DOM events controlled only the
test-owned window. [Full factory capture](images/w4a/creature-factory.png) and
[minimum 1100×740 capture](images/w4a/creature-minimum-window.png) were visually
inspected. Rendered chrome passed the prohibited-promotional-string check.
The installer was built, not installed, signed or tested on a clean machine.
No unrelated full-game campaign or wiki release gate was introduced.

## Source coverage and preservation

Inspected production authorities include `engine/data_loader.py`,
`creature_factory.py`, `ai_system.py`, `creature_abilities.py`, `effect_lifecycle.py`,
`combat.py`, `look_mode.py`, `scene_generation.py`, `discharge.py`,
`save_components.py`, `save_manager.py`, `entities/actor.py`, the Fighter,
Perception and AI components, `rendering/tile_registry.py`,
`generation/structure_contract.py`, `structure_preview.py`, `town_gen.py`, current
creature/player JSON and G17's authored-creature example. W3C's adapter, editor,
protocol, Rust entitlement/writer and evidence were inspected alongside the root
AGENTS, approved plan and owner briefs. Exact inspected hashes are in the machine
receipt. G17's existing implementation/delivery are `796b8fe` / `7745f72`.

The preservation checker passed: **7,972 protected source files and seven personal
save files**, unchanged bytes/measured metadata and unchanged save membership.
Its inherited baseline is `7745f72ea5446af22d3f340c30043d3752ef0f54`; it does not
mislabel that older protection manifest as the W4A Git baseline. The untracked
owner plan remains untracked and byte-identical, SHA-256
`bcf41ab230fea7aa43a2a2f26b2826bd6d0d53ec814c788903badc642910f49a`.
The production catalogue SHA-256 remains
`5bd33d875fd924bf552cf0879f0ee6b66e821a03afa59508d5e86fb00352f8db`.

The authoritative workflow guide is updated in [README](../README.md). Committed
review artifacts are limited to this report, compact machine evidence, two small
example JSON files and two captures. Binaries, installer, disposable data and
detailed local test logs remain ignored. W4A stops here; placement UI and later
Workbench/gameplay milestones require their own brief.
