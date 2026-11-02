# AI-8: independent hostile alarm and investigation components

Runtime/content/editor revision: `6f4b347adf8b699d76b2f3bdba2f094c65d9b8cd`.
Exact final verification-input revision: `087bcc9c70102dee17166415f61fd8be6ccff629`,
production `main`. Its only delta corrects two existing catalogue expectations
for the three new layouts; product bytes and all other verification inputs are
unchanged. Nineteen passed gates retain their exact tested revision/input binding;
the entire affected focused gate was newly rerun on the corrected input.
[Exact verifier delta](../../evidence/ai-8/verification-input-delta.json).
Start: `272b0b1cb691df77057045631dd3788a1bae6315`; no intervening tracked
changes. Completion adds reporting and review evidence only. Final main SHA
and complete checkpoint object/peeled revision are supplied in the handoff;
this report cannot embed its own future commit hash.

Two independent version-1 `enemy_responses` attachments compose with the existing
v1 `strike_and_withdraw` and v5 `territorial_guard` recipes. The base recipe is
still independently selected. Callers spend an ordinary opportunity preparing,
then another on a later charged phase with fresh own player sight. Interruption
cancels the tell. Calls report only emission origin, scene, faction and unique
source/sequence identity. Existing sound propagation/hearing determines receipt.
Response begins strictly after emission's phase, has finite phase/opportunity/
failure limits, and cannot confer a target or attack. Own combat, withdrawal,
territorial bounds, retirement and committed return retain priority. Receipt and
arrival never relay; both-module actors need independent lawful sight to call.

Definitions keep attachment configuration separate from historical profile
schemas. Saved `composite.responses` holds effective config and exact local
state; absent attachments serialize nothing. Factory restoration explicitly
ignores newly tuned definition attachments for old instances. Strict alignment,
scene/individual provenance, compatible intent and bounded counters validate
before installation. Scene departure drops preparation/reported interest and
movement accumulation, preserving finite cooldown/dedup and territorial return.
[Feature, clock, save and authoring contract](../../roguelike/docs/ENEMY_RESPONSE_COMPONENTS.md).

## Content and authoring

The game-owned two-entry registry supplies Workbench defaults, numerical bounds
and validation. **Enemy response components** has separate call/investigation
choices; unsupported faction/recipe/special/ranged/NPC/escort combinations reject.
First attachment requires a new ID. Enrolled same-recipe variants can change
participation/tuning for fresh actors; protected body/art and unrelated metadata
retain existing exact-source policies. No new AI class or per-monster dispatcher
was added. Privileged inspection includes call/receipt provenance, sight/action
reasons, absolute cooldown/deadline plus current phase, and remaining opportunity
budgets; inspection does not advance time.

| Example | Base recipe | Attachments |
| --- | --- | --- |
| barrow_alarm_sentinel | v5 direct melee | call |
| barrow_alarm_skirmisher | v1 strike/withdraw | investigate |
| barrow_alarm_runner | v1 strike/withdraw | call |
| barrow_alarm_watch | v5 direct melee | both |

Actual packaged controls through `workbench/Launch Workbench.vbs` created four
variants and two room examples, and applied the new C room. Initial C reopen
correctly refused a concurrently changed selection dependency after the file
write. Sequential reopen confirmed all seven exact sources. The successful
iteration exercised undo/redo, participation off/on, save/reopen, invalid faction
rejection and legitimate no-ops. Captured Reset retained the enabled input;
latest-saved used disabled input and excluded the parked dirty enabled draft.
Both rooms then passed again on the final built package.
[Source/review receipts](../../evidence/ai-8/authoring.json).

`ai8_alarm_crossing` and `ai8_alarm_reverse` use a closed doorway, occluding wall
and southern alternate route with opposite host/module arrangements. New
`barrow_ward_store_c` reuses the Ward, existing note, modest empty crate and stair.
Fresh-world A/B/C relative weights are **1/1/1**, with unchanged **0.35** overall
authored-barrow chance. A/B definitions and old assignments/rooms remain owned.
Enrollment is the existing selection contract, separate from Test room.

## Independently executed verification

All following results were executed for this task; historical AI-7 reported
counts are not substituted. Exact commands, environment, timings, input manifest
and log hashes are in [release evidence](../../evidence/ai-8/release.json) and
[gate totals](../../evidence/ai-8/gates.json). The frozen source remained stable.

- Unfiltered focused: **588/588** tests, including 16 new
  adversarial AI-8 checks.
- Unfiltered production-D: **3,704/3,704**, **159** workers.
- Workbench worker cohort: **51/51** across all eleven affected modules;
  frontend **96/96**, host **71/71**, startup **15/15**.
- Typecheck, clippy, debug/release build, NSIS bundle, desktop lifecycle, final
  AI-8 native rooms, retained AI-7 native rooms and AI-3 native lifecycle passed.
- Six AI-8 play families, newly rerun AI-3/5/6/7 play, and the supplemental
  ordinarily selected western approach passed.

Windows Python **3.11.0** from the pinned baseline environment imports this
production source; native workers use the bundled pinned runtime. Node
**24.15.0**, Rust/Cargo **1.95.0**, pygame **2.6.1**, tcod **19.3.0**, NumPy
**2.4.6**; dummy SDL, disposable saves, ordinary/app-local inputs. Main command:
`python -X utf8 -B tools/verify_ai_8.py --evidence .baseline/ai-8/final-a`.
The original unfiltered gate invocation ran at the runtime revision above. The
final focused repeat uses the retained `focused-retention-witness.py`, whose
exact source, command, input delta and result are retained with the report.
The full command arrays and exact interpreter paths are retained, including
the existing unfiltered production/focused gates and parallel worker cohort.
No owner desktop control or routine manual QA was used.

Workbench package: `workbench/src-tauri/target/release/resonance-workbench.exe`,
SHA-256 `38404df09762b257823dc6cb2250de14976e0bd7e7ae07682d97b09c75df19e4`.
NSIS `Resonance Workbench_0.9.0_x64-setup.exe`, 28,492,423 bytes, SHA-256
`dd85424d3c5909e28b6fa7d6388498e8106fbe34b023b216770b954be920eb6e`.
[Package binding](../../evidence/ai-8/package.json).

The matched controlled room comparison removes only the call component before
first ordinary input. Enabled phases prepare/call/investigate; disabled phases
use normal guard approach while the listener stays put. The receiver first moves
on the phase after emission, and later attacks only after own sight. Fixed RNG
17/19 produced final comparison HP 35 enabled / 33 disabled; this is not a
universal advantage or difficulty assessment. Sight-edge interruption stages only
player position before ordinary actions. The stale-site case retreats using real
keys, preserves a committed guard return, resolves investigation without a hidden
target, then leaves/revisits through normal stairs without replay.

128x128 new-world seed **20261027** selects **80** C rooms; witness chunk
**(69,92)**, `submap_69_92_0`, was constructed through its genuine surface entrance.
Player placement at that entrance and known-geometry route scripting are
explicitly staged, not unaided laboratory travel. The eastern resource route
first engages the skirmisher; it correctly declines the later call due to its own
commitment. A separate western approach demonstrates actual typed receipt and
later physical investigation with unchanged product inputs. Both use real combat,
two real deaths/remains, a collected Ward, F5/F9, independent cold load and return
without respawning actors/items. [Supplemental source/input binding](../../evidence/ai-8/extra-witness-binding.json).

Save comparisons cover preparation, cooldown, unresolved report, committed guard
return, aftermath, revisit and the historical escort. Inspection/save/cancel do
not charge time. Existing v1-v5 and legacy actors are covered by current affected
and full regressions. Actual historical v5 archive and pre-AI-6 v4 archive passed
new cold comparisons through retained AI-6/7 play. The v6 archive was captured
during this task by importing pinned AI-7 source in memory (85 recorded Python
sources), with unchanged AI-7 actor/room bytes, then loaded exactly under AI-8.
It is not a schema downgrade or a claim of earlier archive capture. Cold snapshot
equality is not a universal RNG-stream persistence claim.

## Preservation and delivery

All **100** recorded pre-existing untracked owner files remain byte-identical and
outside task commits. Tracked `art_lab` and wiki deltas are empty. No personal
campaign, extra development copy, worktree or task branch was created/opened.
[Preservation manifest](../../evidence/ai-8/preservation.json).
The initial full focused run passed 586/588 and exposed only stale catalogue
totals (88 structures and 20 authored submaps). They now expect 91 and 23 and
explicitly include the three new layouts; both corrected cases also passed
individually before the complete unfiltered rerun. No game change addressed these
inventory failures. Material development failures and fixture corrections remain in
[attempts/limits](../../evidence/ai-8/attempts.json); they are not certification.
Catalogue expectations were narrowly adjusted for four creatures and three rooms;
the game-owned contract expectation advances from creature-composite-8 to -9.

Start, implementation, verified-input and complete checkpoints are published.
[Remote checkpoint readback](../../evidence/ai-8/publication.json) records annotated
objects and peeled input revisions; the final handoff supplies the final main and
complete-tag independent Git/GitHub readback. Reporting does not change consumers.

Scope stops at two active-scene, same-faction v1/v5 hostile components. No global
network, reinforcement spawn, AI-9, ally expansion, rejected NPC medical support,
wiki/HTML rebuild or reference-pack refresh was implemented.
