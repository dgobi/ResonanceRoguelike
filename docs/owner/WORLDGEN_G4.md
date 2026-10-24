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
