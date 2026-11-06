# SYS-5 — Contested remains and local scavenging

Gutter Gleaners and Pale Carrion Beetles can discover exposed flesh, approach it
and spend ordinary decisions feeding. In inventory, **P → Place one portion
here** exposes exactly one unit for one action; Esc is free. A completed loose
feed consumes one count. A corpse can be stripped once while preserving its
captured non-flesh harvest, tool requirements and running decay. Ordinary
harvesting with an equipped blade still obtains useful bone and other surviving
outputs. Feeding grants no healing, speed, XP or allegiance change.

Production remains on `main`, with one implementation writer and three read-only
review helpers. Owner work and personal saves are preserved. No development
checkout, task branch, desktop control, campaign migration or wiki edit was used.
This is the finite SYS-5 package; later roadmap work is outside its boundary.

## Delivered contracts

| Surface | Result |
| --- | --- |
| Shared attachment | One `enemy_scavenging` configuration on ordinary hostile melee `strike_and_withdraw` and direct-melee `territorial_guard`; no other host enrollment |
| Final tuning | Both approach budgets 8; Gleaner feed 5, speed 0.7, sight 8 without darkvision; Beetle feed 3, speed 1, sight 8 with darkvision, defended radius 4 / excursion 6 |
| Fresh loose resources | Crow Meat, Stalker Meat and newly published Gleaner Flesh use the same explicit tier-1 `flesh` capability; no consumer ID special cases |
| Fresh remains | Explicit flesh outputs on Plague Crow, Heath Stalker and Gutter Gleaner; complete ordered effective recipes captured at construction |
| Player placement | Exact owned unit, copied properties and new split identity only when splitting; rollback on failed publication; stale/denied/cancelled attempts are free |
| Corpse production | Native death and direct authored `remains` share one constructor; no actor spawn/kill-credit shortcut; ambiguous, unsupported, ephemeral or invalid sources reject |
| Completion | Exact active-floor owner, stable resource identity, observed location, valid count and legal contact revalidated; two feeders cannot duplicate a unit or strip twice |
| Harvest | Every captured flesh output suppressed after stripping; actual equipped cutting tier, bone-reader bonus, equal-threshold precedence, ranges, empty-yield semantics and normal costs retained; output/source-removal failures roll back |
| Priority | Hostility and retained pursuit, withdrawal/hold/return, wounded regroup, attributed alarms and anonymous sound precede food; real speed/action denial remains authoritative |
| Perception | Shared illumination, darkvision, weather, LOS, occupancy and corner geometry; no inventory/container discovery or unseen relocation tracking |

Current-scene feeding only: inactive scenes neither advance attempts nor gain
decay catch-up. Departure retires partial work; return preserves depleted bodies
and consumed items. Same-scene saves retain captured configuration and partial
feeding. Positive modern discriminators reject malformed presence before
installing a candidate session. Genuine historical absence stays inert, including
B1 item rows without keywords. Historical corpses retain their old live-table
harvesting behavior; there is no retroactive resource enrollment.

See [Local scavenging](../../roguelike/docs/LOCAL_SCAVENGING.md) for precise
controls, data bounds, failure semantics and authoring rules. Affected creature,
item, structure, territory, response, selection and room-test guides were updated.

## Practical Workbench reuse

Supported fields expose the shared attachment and tuning; Harvest exposes a
per-output flesh designation; Item Properties expose the explicit keyword; the
layout editor offers direct remains placement/source editing. Existing source
entitlement, unique saved dependencies, validation, review, single-file apply,
byte-checked reopen, history and recovery remain authoritative. Raw Source cannot
promote an incompatible original host or inject arbitrary saved resource state.

The actual packaged UI published `gleaner_flesh`, both eater variants and
`sys5_scavenging_room`. Retained original attempts include new-ID creation and
invalid host/flesh/arrival rejection with undo. The successful supplement added
loose Gleaner Flesh and Crow Meat to the room and corrected the meat description
to describe cooking. Both living eaters consume a loose unit and strip a body;
the player equips the ordinary blade/armour and harvests surviving crow bone.
All four repeated witnesses end alive at HP57, without a gameplay fixture.

Saved feeding 3 → 5 changes the latest capture. Reset preserves the original
three-step capture, and a dirty seven-step draft stays excluded. The final saved
Gleaner value is five. Partial states and stripped bodies survive native F5/F9.
The original creation archive and expanded supplement are distinct evidence:
[creation index](../../evidence/sys-5/native-authoring.json),
[supplement index](../../evidence/sys-5/native-supplement.json).

## Ordinary availability and measured choices

The original seven weight-1 barrow rows remain in order at authored chance 0.35.
`barrow_scavenger_store` and `barrow_carrion_sump` append two weight-1 rows.
Existing saved assignments are unchanged. A native seed-20261023 world assigns
31 stores and 32 sumps; the witness realizes two additional assigned scenes per
context plus the two scenes entered through actual surface stairs. This small
generation sample is distinct from the ordinary travel observations.

Both ordinary journeys disclose one initial surface-approach staging and full-map
route knowledge. They use actual acquired supplies, starter equipment, ordinary
keys, living AI, genuine F5 branch replay and disposable save roots. There are no
inserted supplies, invulnerability, disabled actors, debug vision or cost changes.

| Comparison | Measured result |
| --- | --- |
| Store: conserve | Harvest intact crow and cook one acquired Gleaner Flesh. Reach the far-store objective at turn 542 / HP60, with hostile pursuit |
| Store: spend | Place one acquired portion, use existing light/cover, let the eater consume it and strip the crow. Reach the same objective at turn 537 / HP60 with no current hostile target |
| Store: reclaim | From the genuine choice checkpoint, harvest the exact corpse after the Gleaner discovers it; its pending attempt ends without a feed completion |
| Store: interruption | Reveal the player during a real partial paid feed; the host retires food and pursues, leaving the one-unit bait intact; then restore the genuine feed checkpoint |
| Store: remaining material | Ordinary hostile combat remains necessary near the body; equipped-blade butchery yields bone without crow meat, and changed revisit retains depletion |
| Sump: bypass | Reach the eastern objective through the longer southern route while the screen remains intact, HP60 |
| Sump: quiet | Three careful cuts open the screen at turn 507; after retreat the Beetle has fed and returned to its post by comparison turn 517, HP60 |
| Sump: force | One force action opens at turn 505 and emits an actual heard dismantling sound; investigation delays feeding, still incomplete at comparison turn 515, complete at 516, HP60 |

The store's five-turn difference compares whole plans, including cooking. It is
not an isolated bait speed benefit. The sump proves priority/timing and useful
access alternatives, not guaranteed damage avoidance. These are selected living
encounters, not certification of unaided discovery, all-seed balance or fun.
Feeding does not pacify either host or replace territorial commitments.
Production-rendered inspection clearly labels stripped flesh and remaining
harvest; both ordinary return journeys preserve changed resources/access.

## Verification and publication boundary

Starting main: `aea1d565097982a699230dcc7e4210b8106fbbe1`.
M6 full-run boundary: `591cacc207e1271c67ae93a53ce4f4ae4665f3b3`.
Final repair/recheck boundary: `25159337712158762f5d6b19b1bd4363465f8997`.

The complete unfiltered 19-gate matrix ran on frozen M6 inputs through
`tools/verify_sys_5.py --evidence .baseline/sys-5/final-a`. Eighteen gates passed:
production D **3,704/3,704 across 159 workers**; full focused **726/726**;
frontend **100 tests / 21 files**; Rust host **73**; typecheck/clippy;
debug/release/NSIS builds; startup **15 cases**; desktop lifecycle; expanded
SYS-5 and retained SYS-1–4 native witnesses; ordinary play and persistence.
All 29 worker modules ran; 27 passed. Three assignment requests exceeded their
existing 20-second limit, and one corpus assertion still expected 37 creatures
instead of the shipped 39. The full-run failure and logs remain unaltered.

The scoped repair reuses a lazily built reference catalogue only within one
assignment-authoring snapshot, and omits unused remains-choice enumeration from
validation. Original and staged snapshots remain separate. Every room retains
compiler, source identity, pool/text dependency, factory and native placement
checks; public UI choice defaults remain complete. No selector/gameplay cache or
request-timeout change was made. The count correction retains the complete
39-creature inspection/construction loop and all negative admission checks.
An isolated before/after sample measured inspection at 16.55 / 4.40 seconds,
and draft validation at a 20-second timeout / 6.18 seconds. The complete assignment
worker also passed with its original timeout; these are local measurements. The insufficient first repair and bounded
profiling attempts are retained in [validation preflight](../../evidence/sys-5/validation-preflight.json).

The [retention witness](../../evidence/sys-5/verification-retention-witness.py)
pins the original release/manifest, inverse-reconstructs exactly three changed
consumed inputs, and verifies the unchanged 1,303-file set, dependencies,
packages and all original logs. It reruns five complete affected focused modules
(**98 tests**), both ordinary journeys, packaged SYS-5, every worker module and
the dependency control. All affected rechecks passed: 98 focused tests, 145 worker
cases across all 29 modules, the separate dependency control, ordinary play and
packaged SYS-5. The bundled worker's one intentional dependency-absence skip is
exercised by that development-Python control. Final acceptance is
retained full execution plus complete affected rechecks, not a fresh clean full
execution. Counts overlap and must not be added.

Windows dependencies are Python 3.11.0, pygame 2.6.1, tcod 19.3.0 and NumPy 2.4.6.
The established baseline venv supplies only the interpreter/dependencies; game
imports use this production checkout. Workers use the bundled isolated Python
runtime. All gameplay witnesses use dummy SDL, app-local events and disposable
save roots. Exact commands, environment, source/log hashes, final rechecks and
package identities are recorded in the evidence directory.

The unfrozen broad preflight and tuning failures are retained in
[preflight evidence](../../evidence/sys-5/preflight-evidence.json). Its cached
catalogue/source-edit rejections, stale membership expectations and a test
double's omitted placement result were resolved without weakening negative
admission tests. It is not final verification. Scoped read-only reviews also
closed alias ownership, harvesting rollback, historical keyword absence,
constructor-free source validation, suppressed-hostile priority, finite territory
retry, vessel contradictions and remaining-stack/empty-harvest evidence gaps.
The authoring reviewer independently checked the final repair and retention scope.

Genuine pre-change fixtures were captured before implementation; the separate B1
receipt executes unchanged historical serializer/factory modules rather than
deleting fields from modern records. Eleven final-play checkpoint comparisons
cover intact/stripped bodies, partial feeding, departed/returned scenes and a
real 3 → 2 remaining stack through F5/F9 and independent cold processes. The
remaining-stack flat-map fixture is explicitly separate from ordinary play.

The final preservation receipt confirms all 280 owner files and seven personal
save files unchanged, including save modification times. The original seven
barrow layouts, parent host examples and template are unchanged; no wiki files
were edited. See [verification summary](../../evidence/sys-5/verification-summary.json),
[affected recheck](../../evidence/sys-5/verification-recheck.json),
[preservation](../../evidence/sys-5/preservation.json), and
[read-only reviews](../../evidence/sys-5/review.json).

Publication and independent remote readback follow this verified evidence commit.
