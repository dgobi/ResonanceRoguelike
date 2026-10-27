# W5A delivery: registered item and recipe contracts

27 October 2026. W5A is complete in the production checkout on `main`.
Items and immediate recipes share discovery, document ownership, validation,
review, publication and reopen. The optional **Eligible for automatic ingredient
selection** control (`consumed_on_use`) is supplied by the game descriptor.
Actual factory/allocation/exchange checks retain the existing game behavior.

## Revisions and scope

The starting local HEAD, `origin/main` and live remote were
`3d4c0cfdde151fa562bbf1dc2e1e9e5cc35b9a97`. Migration:
`b43dd4fef1ce8a5e7663b15088c244a6c73d2588`; navigation/context/evidence corrections:
`91abc3f11daf794ac62990ae3e4eb7d4c253c9be`,
`ef9a7b1a0ec506e8bee0e2477cdb98f91f90983b`, and
`b85e12514dc2f173cac0fcd2e65de6b3b58fbafa`.

Extension implementation: `c4997595b6e3e074a0b3998f902878d9fa085f76`. The separate evidence
commit is identified in the handoff and Git history; this file need not contain
its own commit SHA. Checkpoints are
`checkpoint/workbench-w5a-start-20261027-a` and
`checkpoint/workbench-w5a-verified-20261027-a`.
No branch, worktree, development copy, history rewrite or push was used. This
session authorized implementation/evidence commits, with no existing push
authorization. Live remote readback remains the starting revision.

## Changed responsibilities

| Source | Responsibility |
| --- | --- |
| `roguelike/engine/content_authoring.py` | Explicit trusted item/recipe registration; discovery/matching, bounded schema vocabulary, descriptor identity, semantic adapter dispatch |
| `item_authoring.py`, `recipe_authoring.py` | Game-owned fields/help/defaults, references, source eligibility, publication policy and actual construction/execution evidence |
| `workbench/worker/bridge.py` | Common family envelope and exact-draft dispatch; independently checks original source entitlement and candidate validity |
| `src/content.ts`, `familyData.ts`, `ContractControls.tsx`, `ContentEditor.tsx` | Bounded transport validation, typed specialized evidence and reusable controls over localized source edits |
| `src/App.tsx`, `Authoring.tsx` | Family document collection and shared commands; parked drafts, source trails, return navigation and hash-checked reopen |
| `src-tauri/src/main.rs`, `authoring.rs` | Family document lookup and verified bounded policy beneath existing admission/completion protections; host-owned path and filesystem checks |

Strings, multiline text, finite numbers/integers, booleans, references and the
existing ordered keyword/requirement tables consume descriptor metadata. Defaults
are display values only; `x-initial` supplies explicit new-row values where the
consumer has no effective default. Exact source remains authoritative, including
unknown nested metadata, line endings, absence, explicit false and invalid null.
Unsupported capabilities deny authoring while retaining inspection where allowed.
See [the extension guide](CONTENT_CONTRACTS.md) for the bounded vocabulary and limits.

Item/recipe semantic adapters remain real game validators. Schema and reference
checks alone do not grant publication. Original read-only sources cannot be
promoted by rewriting the candidate. The host binds family, contract, descriptor,
source and semantic evidence and independently confines paths. Recipes remain
new-variant-only; eligible components retain their edit/variant rules. Publishing
a recipe affects future session loading; item variants are not assigned to loot.

W4D's operation ownership, epoch/token/revision/attempt checks, cancellation,
one-time review consumption and reserved-publication BUSY behavior remain active.
All eight `w4d_*` regressions pass through the migrated helpers with legacy/submap
coverage retained. Replacement tokens and distinct recipe policy have additional
coverage. The writer from `fn pin_inputs(` to immediately before the
`apply_document` command is byte-identical to the baseline after LF normalization:
SHA-256 `fe785dc98ccadebb26c6426303068f35e7e36d9cc8a170c2950d07841b96c1bf`.

## Extension-only proof

Against pre-extension `b85e12514dc2f173cac0fcd2e65de6b3b58fbafa`, the only runtime
change is two descriptor lines in `roguelike/engine/item_authoring.py`. Remaining
extension files are tests/runners and guidance. There is no extension change to
App, Authoring, protocol/family contexts, generic controls, Rust authority, the
central worker dispatcher or gameplay consumers.

`node scripts/run-contracts.mjs` runs the existing recipe journey in disposable
data, then replaces that project's real pre-extension item module with the
production descriptor module. The supported release executable, compiled
frontend, packaged bridge, all bundled Python files and installer are hashed
before/after and remain identical. The old review is revoked on source change
with its exact draft retained; normal reopen shows the new generic boolean.
Opening/viewing the absent default leaves source bytes unchanged. An invalid null
draft is refused and retained; a repaired false variant is deliberately published
and reopened with reviewed/saved/factory-source hashes equal. A separate direct
host apply with stale game source is rejected. Full hashes are in the receipt.

The worker tests construct actual `ItemFactory` instances for absent/true/false,
call `material_candidate`, `plan_craft` and `commit_craft`, and verify explicit
material choice, consumed materials and retained tools. False excludes automatic
material selection but permits an explicit matching choice. Ordinary item-use
disposal and game semantics are unchanged.

## Newly observed verification

All commands below ran in `workbench/` unless stated otherwise. Dependencies stayed
locked; no new form library was added.

| Command | Final result |
| --- | --- |
| `npm.cmd test` | 36 tests across 10 files passed |
| `npm.cmd run typecheck` | Passed |
| `cargo test --locked --manifest-path src-tauri/Cargo.toml` | 33 passed, including all eight W4D tests |
| `cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings` | Passed |
| `worker/runtime/python.exe -X utf8 -B -m unittest discover -s worker -p 'test_*.py' -v` | 43 collected; 42 passed, one embedded-runtime dependency-absence skip; 662.051 seconds |
| Existing development interpreter, `-m unittest test_bridge.BridgeTests.test_dependency_absence_structured -v`, in `workbench/worker` | Skipped case separately passed; 0.753 seconds |
| `npm.cmd run bundle -- -- --locked` | Release executable and NSIS 0.9.0 package created |
| `node scripts/run-contracts.mjs` | Passed; 183.964 seconds |
| `npm.cmd run test:items` | Passed; 129.386 seconds |
| `npm.cmd run test:submaps` | Passed; 133.398 seconds |
| `WORKBENCH_STARTUP_SMOKE=1 npm.cmd run test:startup` | Four supported launch/restart checks passed |
| Final preservation comparison and `git diff --check` | Passed; all unrelated entries/settings unchanged |

The baseline preflight newly reran all 32 frontend tests/typecheck and the existing
four item/four recipe worker checks before refactoring. W4D's other committed
results were prior reported evidence; the final gates above are new W5A runs.

The combined recipe journey parks an item and legacy drafts, edits ordered
requirements/references, exercises real recipe allocation/exchange, publishes a
new recipe and returns with the item text intact. The additional item journey
covers the migration's navigation and saved-reference refresh risk, including
item/pool/building links and fresh factory evidence. The legacy submap journey
covers cancellation, stale-review refusal, parked drafts, actual placement and
publication/reopen. Startup smoke checks the supported VBS launch, owner-project
restart, project change and changed-project restart with bundled resources.

Runtime: Node 24.15.0, npm 11.12.1, Rust 1.95.0 (`59807616e`, 2026-04-14),
CPython 3.11.0, pygame 2.6.1, tcod 19.3.0, NumPy 2.4.6, cffi 2.1.1,
pycparser 3.11 and typing_extensions 4.16.0. Workbench/worker 0.9.0, protocol 8.
The compact [verification receipt](w5a-verification.json) binds final source,
native checks and packaged-resource hashes. Large logs/screenshots/test data stay
under ignored `.artifacts/`.

## Preservation and limits

The inherited preservation manifest is explicitly older
(`7745f72ea5446af22d3f340c30043d3752ef0f54`), not a fabricated W5A snapshot.
Its 7,979 entries include seven save files. The two intentionally edited existing
game authoring modules are excluded from equality; every remaining entry matches
its recorded bytes and measured metadata, and the save file set is unchanged.
The owner plan remains untracked and byte-identical. Owner settings match W4D;
the VBS launcher and corrected shortcut remain unchanged. Baseline-to-final scope
contains only the registered authoring integration, controls, tests and guidance;
no active game JSON, personal campaign, gameplay consumer or wiki changes.

Early development exposed a missing publication consequence note, lost item
source trails, stale parked reference context and the need to refresh clean
factory evidence. These were corrected before final native verification. One
early installer attempt encountered a test-owned executable lock and was rerun
successfully after that process exited. An initial unittest module invocation
failed during setup before the correct discovery commands. Failed attempts are
not counted as passing evidence. The final item journey initially expected
`VARIANT_EXISTS` for concurrent destination creation; registered items now bind
catalogue freshness and correctly refuse earlier with `SOURCE_CHANGED`. The
assertion was updated to that exact refusal, retaining the untouched-destination
byte check, and the journey rerun. Writer no-clobber tests remain unchanged.
Final frontend checks, package and selected native journeys ran after the last UI
correction; Rust and Python sources stayed
unchanged after their passing suites.

Native automation uses app-local events and isolated settings/data, without
desktop takeover or owner QA. Package creation is not clean-machine installation,
code signing, full-game or ordinary-play certification. Historical full-game and
unrelated native campaigns were not commissioned. Durations are per run and are
not summed across overlapping work. No next adjusted-plan stage or wiki gate was
started.
