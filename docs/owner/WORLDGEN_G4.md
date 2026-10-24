# G4 — Composition reliability and gameplay restoration

Implemented in the existing production checkout on `main`, starting clean at
`b77298119cc714cba08543eb9c7eaf8309a90402`. The attached brief supplied the task
requirements; its references to earlier acceptance are not new acceptance events.
The supplied probes reproduced F1–F6 before source changes. Personal campaigns,
the 65 frozen original documents and the four installed eligible assets were
preserved. No alternate development checkout or desktop control was used.

## Delivered behavior

Fresh settlements publish one canonical name, explicit member roles, town zones,
difficulty and resonance before native selection. Grid civic members use the
existing bell-quarter population; other grid members use residential population.
Roadside members use market and residential populations. Native actors are built
by the production factories once, during staged scene preparation. Cached scenes,
cold restoration and F9 retain their actual actors and mutations.

The planned pipeline now separates base biome terrain from infrastructure-aware
passes. Shared roads, rivers and bridges are painted first; structures and authored
contents follow; protected stairs remain late. Wood, flint, clay, waystones and
native population then operate on final geometry with reservation exclusions.
One reachable starting waystone and its laboratory stair/return link survive.
Each grid civic member receives a functional waystone and prayer. Other town roles
explicitly do not receive a civic waystone. Native/resource records are staged,
validated and published through the existing complete-scene boundary.

Opposing entrances can share their assigned public-road cells. Footprints,
buffers and private approaches remain exclusive. Actual assigned street geometry
governs setback, including unequal country/street widths and even-width bands.
All four normals and both trial orders are covered; no equal-density quota is
imposed. Mirroring is now eligible in random placement when explicitly permitted.
Asset weights are drawn once per asset, independently of transform count.

Explicit weighted-child x/y coordinates move with their parent under all eight
quarter-turn/reflection combinations. Each supplied coordinate is validated
independently; omitted fields stay absent and contradictory alternatives fail.
Preview, selection and stamping share this transform. Source documents remain
unchanged, including unknown non-coordinate metadata.

Preflight now validates both directions of durable ownership, supported types and
transforms, complete entrance spans, reservations and reconstructed Chunk/town
agreement. Removing map markers cannot downgrade a surface whose Chunk identifies
it as generated. The generic unversioned-owner exception remains supported.
Checksum-consistent semantic corruptions are rejected before installation; recovery
selects one complete earlier checkpoint, and complete failure preserves active state.

## Saved-world contract

New worlds use G4 origin, plan format 2 and the existing `shared-v1` dispatch mode.
The structural dependency projection remains `structure-v1`; new native semantic
metadata is versioned as `native-town-v1`. Scene revision and plan origin are
separate. A G4 scene can consume a format-1 G3 plan through `g3-to-g4-v1`.

Visited G3 scenes stay authoritative: no inhabitants, waystones, items or roads
are backfilled on load/F9/revisit. In particular, **an already visited G3 starting
surface retains its missing waystone**. Historical member names, zones, difficulty
and resonance are not normalized. Unseen G3 scenes preserve the saved geometry and
selection while using the supported current adapter. Infeasible required access
fails before publication rather than moving buildings or regenerating a plan.

The original G3 structural hash projection is retained. Newly restored native and
resource behavior uses current valid definitions at first materialization; G3 did
not freeze those historical inputs. Actual scene provenance records the plan
digest/origin, adapter, native context and compact input fingerprints. Native entity,
zone, biome, terrain/decor and prayer-item inputs are recorded at creation. These
fingerprints are observations, not a second inventory or a catalog-edit load gate.
Current text and presentation still resolve by runtime ID. No historical generator
archive, personal-save migration or cross-version regeneration promise is made.

Relevant structural edits allow load/revisit and unaffected pending scenes. An
affected pending placement fails with its specific dependency/geometry explanation.
Absent-field/wg1/wg2 worlds retain their legacy/no-plan origin and dispatch even
when a newly created scene truthfully records G4 generation.

## Author and tune a structure

Use the complete [frontage example](../../roguelike/docs/examples/author_frontage_a.json)
or [landmark example](../../roguelike/docs/examples/author_landmark_a.json), and the
[executed authoring guide](../../roguelike/docs/STRUCTURE_AUTHORING.md). Initialize
a draft only if absent, edit/export from the offline painter, validate all permitted
orientations, then preview it in the installed mixed grid/roadside/landmark pool.
Inspect rejected candidates before deliberately installing a new ID and registering
it in `roguelike/data/generation/g3_config.json`. Its filename remains unchanged.
Start a disposable new world to see new-world policy; existing maps stay saved.

The guide lists all active configuration fields and explains public/private access,
street widths, transform eligibility, weighting, weighted coordinates and common
fit/access/dependency failures. Legacy `town_config.json`, `rotatable`, `facing`,
`allowed_in` and old weights remain inactive for shared-plan selection.

From the repository root, with the existing dependency environment:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --evidence evidence/worldgen-g4/focused-final
& $ResonancePython -X utf8 tools/verify_structure_editor.py --evidence evidence/worldgen-g4/browser-final
& $ResonancePython -X utf8 tools/verify_g4_authoring.py --evidence evidence/worldgen-g4/authoring-final
& $ResonancePython -X utf8 tools/worldgen_g4_diagnostic.py --journey --evidence evidence/worldgen-g4/diagnostic-final
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/worldgen-g4/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
& $ResonancePython -X utf8 tools/verify_d.py
```

## Measured ordinary-world results

The three declared seeds completed without discarded outcomes. Planning still
materializes zero local scenes. Occupied/vacant counts include the landmark;
native counts cover every town member, excluding the landmark.

| Seed | G3 occupied/vacant | G4 occupied/vacant | G4 town members / actors | G3 → G4 plan bytes | G4 planning seconds |
|---|---:|---:|---:|---:|---:|
| 0 | 39 / 42 | 77 / 4 | 10 / 36 | 527,981 → 558,570 | 1.129 |
| 20261023 | 45 / 52 | 89 / 8 | 12 / 48 | 657,128 → 691,916 | 1.515 |
| 29417 | 43 / 54 | 85 / 12 | 12 / 48 | 592,452 → 628,333 | 1.409 |

Across these seeds, north-facing town occupancy changed from **0/136 to 124/136**;
south-facing occupancy remains **124/136**. Required entrance/target access and
the physical capital gateway passed for all three seeds. The full conditional
tables retain zeros, eligible transformations, attempted transformations and
rejection reasons; they are available in the evidence archive.

Plans are about 5–6% larger while occupied plots nearly double. The changed plan
includes more accepted placements, semantic metadata and different rejection
records. G3's historical
planning range was 0.599–0.706 seconds. Planning now accepts more buildings and
performs stricter validation; native actors are created later during scene
materialization. G4's final diagnostic ran alongside other gates, so these elapsed
times do not isolate the cost of each change. They are observations on the reused
production environment, not a controlled speed regression benchmark.

The extended journey walked **27,001 steps** across **412 exact boundaries**, reached the landmark entrance and
required target, and preserved coherent F9 rollback. Its worst observed transition
was **0.498 seconds**, F5 **1.330 seconds**, F9 **0.926 seconds**, and checkpoint
size **18,898,413 bytes**. Historical G3 values were 26,989 steps, 0.207/1.025/0.410
seconds and 18,818,411 bytes. Journey controls and test-load differences limit
timing comparisons; the saved starting checkpoint is not a measure of all explored
scenes. Full scene/transition records remain available for review.

The sampled local scenes took 0.061–0.474, 0.059–0.551 and 0.082–0.435 seconds
respectively. These samples include every town member plus the starting surface,
required crossing and landmark. The capital gateway is checked separately.

## Checkpoint chain

All checkpoints are unique, named tags on the existing `main` history. No
owner work was present at the clean baseline, and no history was rewritten.

| Checkpoint suffix (`checkpoint/worldgen-g4-…-20261023`) | Commit | Result |
|---|---|---|
| `start` | `b772981` | Clean reviewed baseline; three before probes retained. |
| `gameplay` | `488ea54` | Settlement semantics and staged gameplay restoration. |
| `placement` | `7776d2e` | Public-road compatibility, assigned widths and transforms. |
| `durability` | `7d83b7b` | Durable ownership and explicit old-plan adaptation. |
| `final-gate-inputs` | `d46e108` | First frozen run; focused timeout and generic fixture mismatch retained. |
| `final-gate-inputs-r2` | `2fe0372` | Corrected fixture declaration and complete final input freeze. |
| `verified` | Resolve tag | Final documentation/evidence delivery; remote commit recorded in the delivery response. |

The complete final input commit is
`2fe0372327b1c3343c40fe92ce0d475d00555939`. The first gate's production failure was
confined to a synthetic generic-map fixture retaining a generated Chunk claim;
the production downgrade validator was preserved. The focused timeout prompted
a bounded 300-second runner limit and partial-output retention. Failed attempts
are kept separately, with the corrective commit and full subsequent reruns.

## Final verification

All final gates passed on `2fe0372`:

| Gate | Observed result |
|---|---|
| Complete focused discovery | 163 tests, 223.622 seconds, no skips/failures. |
| Chromium 156.0.8078.4 | 30 checks; 65 frozen originals plus 64 final live documents round-trip. |
| Firefox 157.0 | 30 checks; the same 129-document codec corpus and real file/download actions. |
| Executed authoring workflow | 12 recorded commands; both edited sentinel drafts survive repeated initialization. |
| Catalog and editor freshness | 64 assets; zero errors, 238 retained legacy warnings; editor catalog current. |
| Diagnostic and extended journey | All three declared seeds, all members, physical gateways and lifecycle assertions pass. |
| Unfiltered production gate | 3,675/3,675 checks across 159 workers; seven runner negative controls retained. |

The focused suite ran alone after the first attempt timed out; the other final
gates ran concurrently. The expanded focused suite and stronger durability checks
have a higher test cost than G3's 148-test suite. Browser codec coverage is distinct
from its bounded control/edit/download checks.

Every final report reconciles to **592 identical execution inputs** and all
**12,125 recorded worker-module imports**. Of those inputs, 372 match the input
commit byte for byte; 220 differ only by LF/CRLF conversion. No executable, data,
test, editor or documented fixture input changed after verification. The final
delivery changes only this owner report and scoped evidence.

The [evidence guide](../../evidence/worldgen-g4/README.md),
[structured results](../../evidence/worldgen-g4/final-results.json) and
[source reconciliation](../../evidence/worldgen-g4/source-reconciliation.json)
provide exact commands, versions, outcomes and hashes. Complete final output is
retained in a verified 127-member archive (4,066,099 bytes); development and first
gate output is retained separately in a verified 250-member archive (7,423,354
bytes). Every archive member was read back and checked against its inventory.

## Acceptance mapping

All new tests are included in ordinary focused discovery. Test names below refer
to `tools/critical_fix_regressions/tests/`; complete logs and structured reports
are retained in the [G4 evidence](../../evidence/worldgen-g4/README.md).

| Row | Concrete evidence |
|---|---|
| G4-01 | `before/composition.json`, `frontage.json`, `persistence.json`; all six failures reproduced on clean reviewed main. |
| G4-02 | `G4Gameplay.test_every_member_semantics_native_policy_and_determinism`; every member, positive role counts and explicit civic applicability; old-world metadata test. |
| G4-03 | `G4Interactions.test_ordinary_native_turns_travel_cold_restore_f9_and_late_atomicity`; eight normal turns, real edge transition, removed-actor mutation, exact ownership and restoration. |
| G4-04 | Start/stair access test and `test_waystone_prayer_clay_real_interactions_and_restore`; visited-G3 preservation test and normal lab journey. |
| G4-05 | Functional final-geometry and interaction tests; diagnostic functional-pass counts/absence policy; real prayer pickup, waystone inscription and clay gathering/depletion. |
| G4-06 | Late failure after restored content: active map/actors, world serialization, cache and HEAD unchanged; inherited catalog/receipt ownership tests. |
| G4-07 | `G4Placement.test_public_sharing_both_orders_widths_and_all_normals` and private-conflict negatives. |
| G4-08 | Assigned widths 1/3/4/5 against country widths 1/5; all four normals, two-cell spans, wrong-road/water negatives and retained bridge/spur tests. |
| G4-09 | `test_weighted_coordinates_every_transform_identity_and_immutability`; neither/both/x-only/y-only alternatives, all eight transforms, exact coordinates, realized text identity, inverse and source checks. |
| G4-10 | `test_mirror_required_fit_and_asset_first_weight`; asymmetric mirror-only fit, prohibition, actual preview and captured asset-draw weights. |
| G4-11 | `G4Durability.test_malformed_records_and_world_reverse_ownership`; removed/duplicate/orphaned owners, invalid fields and saved Chunk inconsistencies, original G3 clipped-bank geometry. |
| G4-12 | Actual checkpoint marker/identity/version corruptions; inherited generic-owner positive, explicit legacy/no-plan G4 scene, G4 scene on G3 plan. |
| G4-13 | `test_checksum_consistent_newest_corruption_coherent_recovery_and_failure`; real candidate selection and active-state preservation, generation forbidden during recovery. |
| G4-14 | Original G3 geometry/metadata, mutated visited start, adapter scene checkpoint, no generation during load/revisit; inherited absent/wg1/wg2 and F9 tests. |
| G4-15 | Original supplied G3 plan generated in opposite visit orders; identical complete fingerprints and unchanged plan/world; impossible required-interaction fixture fails atomically. |
| G4-16 | G3 pending dependency-edit test plus retained G3 lifecycle author-edit regression: load/cached/unaffected work, affected pending placement rejects. |
| G4-17 | Three declared seeds, all outcomes retained; zero-inclusive form/normal/asset/transform trial tables, eligibility and slot denominators; timing/size/occupancy definitions. |
| G4-18 | Real-handler journey: both forms, required crossing, exact boundaries, container, landmark entrance and target, F5/F9; separate native/resource fixtures; physical capital-gateway reachability. |
| G4-19 | Executed sentinel walkthrough with exact command records/hashes; Chromium and Firefox real file edits/downloads, 65 frozen plus 64 live documents, weighted coordinates and mirror orientations. |
| G4-20 | Frozen-input focused/browser/authoring/catalog/diagnostic and unfiltered production reports; source reconciliation and delivery checkpoint chain. |

## Evidence interpretation and remaining scope

The ordinary sample is exactly seeds `0`, `20261023`, `29417`. Synthetic tests use
small declared widths, asymmetric assets, corruption mutations and fixed RNG seeds;
there is no hidden seed search. Zero results are retained. `plot_occupancy` uses all
proposed slots including the landmark. Historical `frontage_coverage` duplicated
occupancy and is deprecated. Per-edge detour ratios describe each polyline relative
to endpoint Manhattan distance, not shortest travel on the joined physical network.

The long journey preserves native actors as stationary obstacles and pauses
AI/survival updates; normal movement, stairs, doors, interaction and save handlers
remain active. It is topology/lifecycle evidence, not balance certification. The
short native fixture separately enables normal AI/survival updates with player
invincibility and declared fixture positioning. Its PNG uses the real production
renderer on an SDL dummy surface; plan/scene SVGs are diagnostic drawings.

The world remains finite at 128×128 chunks, with 80×43 local maps and individual
buildings/approaches inside one storage chunk. Four opted-in assets remain the
bounded library. Broader visual variety, new forms, multi-chunk buildings, capital
redevelopment, continuous traversal, infinite generation and save compaction are
deferred. Physical road-network quality merits a separate future pass. Inherited
`UI-TEXT-HEIGHT` remains deferred and is not certified fixed by the passing combat
and persistence gate. G4 stops here; a subsequent brief can expand variety after
review of these corrected contracts.
