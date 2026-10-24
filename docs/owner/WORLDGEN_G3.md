# G3 — Connected world composition

Implemented directly in production `main`, from clean
`3466fc6ac3c61a8b60ab46635e381ceeff29ccbf`. The supplied G3 brief was the task
specification; its references to earlier acceptance were not treated as new
owner-acceptance events. Historical [G1](WORLDGEN_G1.md) and
[G2](WORLDGEN_G2.md) records remain intact.

## Delivered behavior

Ordinary new worlds now publish a validated world-owned `shared-v1` plan before
any local scene is generated. The world remains 128 × 128 coarse chunks with
80 × 43 local maps. Plans contain integer world-tile road bands, river/channel
arms, owned bridge decks, required destination nodes, settlements, plots,
reservations, selected structures and semantic dependency records. No dense
56-million-tile world, live actor, DataLoader or catalog is stored in a plan.

A bounded terrain-cost search realizes each counted country-road edge. The
required graph connects the starting surface exit, both settlement forms, a
planned crossing, the designated capital gateway and a separate landmark. A
two-by-two grid settlement plans streets before plots; a two-chunk roadside
settlement consumes an already selected country-road identity. The default count
is inclusive 2–4, including roadside sites; minimum separation and a counted
near-start site are enforced together. VUKH and the capital remain reserved
geographic anchors. Required infeasibility fails before world publication.

Roads and water use exact shared slices on both storage axes. Bridges reuse
walkable cobblestone, with explicit road/channel ownership and player-and-creature
travel class. This is a geometric bridge primitive, not structural simulation.
Legacy ford and whole-mouth behavior remain separately tested.

The initial connected library opts in four existing assets: `house_small_a`,
`market_stall_a`, `bell_tower_a` and `roadside_shrine_a`. The grid civic bell uses
one world-owned spent-bell specification with matching physical terrain. The
profile declares entrances, complete spans/outward normals, buffer, approach,
allowed quarter turns/reflection, contexts, weight and required goals. The shared
transform covers non-square terrain, complete decor IDs, source specials,
weighted choices' enclosing anchors, targets and entrance spans/normals.
Unsupported coordinate-bearing metadata is diagnosed instead of silently moved.

Each accepted building and its approach fit one storage chunk. Assigned frontage
is explicit; a nearby unrelated road cannot substitute for the assigned join.
Buffers and approaches reserve space with the footprint. Null terrain preserves
painted ground but does not release ownership. Optional failed plots become
recorded vacant gardens; required civic/landmark failures remain errors. The
landmark has a bounded connected approach and a separate geographic site.

Local creation stages biome/dressing, water, bridge/road slices, plots, contents
and protected submap entrances, then validates the final road/entrance/goal chains
before publishing the complete scene. Production item relocation remains legal.
Transient receipts identify source record, selected branch, realized coordinate
and exact generated objects, including ordered scene rows and container contents.
Receipts are diagnostics, not durable inventories or respawn authority.

## Corrective milestone and compatibility

The supplied before probes reproduced the catalog leak, false arrival certificate
and relocated-item registration failure. The actual disposable town checkpoint
contained 357,660 extra bytes of catalog state in this environment. Caller-owned
data now travels through explicit transient arguments. LocalMap reconstruction
drops G2's accidental `structure_data` attribute while preserving scene state;
a fresh-process load with another data root is covered.

Draft initialization uses non-overwriting guards. The documented commands were
executed with sentinel edits and retained byte identities. Direct stamps have no
invented arrival; authored arrivals must equal the actual generated spawn.
Registration follows object identity, not an anywhere-on-map same-ID search.
Legacy weighted-null entrance fallback semantics are documented unchanged.

World origin, scene generation revision, plan format and save format remain
distinct. New worlds/scenes use `wg3`; coherent checkpoints explicitly serialize
the shared plan. Save preparation validates registry identities, references,
membership, bounds, route endpoints, crossing/reservation ownership and required
G3 scene provenance. Player-modified geometry and moved/looted contents are not
compared against an initial blueprint on restoration.

Startup load and F9 invoke no new-world generation, planning or initial
population. Missing/corrupt required plans follow atomic checkpoint recovery.
Absent-field/wg1/wg2 worlds keep their saved origin and existing macro metadata;
unexplored chunks retain an explicit no-plan legacy route. No personal campaign
was opened, migrated or regenerated. Authoritative unversioned LocalMaps used by
other ownership systems are preserved; explicitly generated G3 surfaces require
their saved plan references.

Semantic manifests are deduplicated by selected asset. They cover consumed
geometry, defaults, decor, direct items, every supported weighted alternative,
scene rows, loot-pool selection semantics, item factories and text-item bindings.
Formatting, line endings, inactive structure metadata and unused assets do not
seed topology or invalidate selected placements. Already generated scenes remain
loadable after a relevant valid edit. Only affected new materialization fails,
before departure, naming the placement/dependency and advising matching content
or a fresh world. Live text/presentation keeps the existing runtime-by-ID policy.

## Authoring and representative world

Use the complete [authoring walkthrough](../../roguelike/docs/STRUCTURE_AUTHORING.md).
It includes exact commands, complete frontage/landmark examples, all eight
permitted orientation previews, actual grid/roadside placement and the precise
active configuration/pool paths. The offline painter's placement panel preserves
the full document; both browsers' actual downloads go through Python validation
and production planned placement. The 65 frozen originals remain unchanged and
all 64 live documents round-trip separately.

The active settings file is
[`g3_config.json`](../../roguelike/data/generation/g3_config.json).
`town_config.json` and legacy `rotatable`/`facing`/`allowed_in` fields remain
inactive for G3 selection. Weight is not a guaranteed placement count. A draft
landmark was not selected at seeds 20261023 or 0; the documented positive uses
29417 and retains the existing shrine in its pool. These outcomes are retained,
not presented as a frequency estimate.

Optional play, using production source and a fresh disposable save root:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/play_disposable.py --seed 20261023 --session g3-first
```

Existing session names are refused. This is not a manual verification assignment.
Autonomous commands are:

```powershell
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --evidence evidence/worldgen-g3/focused-final
& $ResonancePython -X utf8 tools/verify_structure_editor.py --evidence evidence/worldgen-g3/browser-final
& $ResonancePython -X utf8 tools/worldgen_g3_diagnostic.py --journey --evidence evidence/worldgen-g3/diagnostic-final
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/worldgen-g3/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
& $ResonancePython -X utf8 tools/verify_d.py
```

## Acceptance mapping

All new tests use the existing focused discovery. The complete production gate
retains its independent worker/assertion enumeration and runner negative controls.

| Row | Concrete evidence |
|---|---|
| G3-01 | `G3Corrections.test_real_town_checkpoint_and_cold_second_catalog`; real town save, cold second-root load, accidental attribute stripping and complete scene fingerprint. |
| G3-02 | `test_documented_initialization_preserves_edited_draft`; `authoring-sentinel.json` and all eight executed walkthrough commands. |
| G3-03 | `test_actual_arrival_and_direct_route_absence`; exact authored spawn, reachable wrong tile, all three direct routes, explicit validation entry and SVG absence. |
| G3-04 | `test_relocated_registration_and_suppression_identity`, `test_receipts_scene_multiplicity_text_and_container_ownership`; retained G2 mixed-pool selection. |
| G3-05 | `G3Plans.test_schema_references_profiles_settings_and_all_alternatives`; retained shared-contract all-branch tests and immutable original corpus. |
| G3-06 | `test_complete_asymmetric_transform_under_all_permissions`; eight real stamps, contents/decor, inverse geometry and unsupported-coordinate negative; orientation CLI outputs. |
| G3-07 | `test_world_graph_constraints_and_lazy_shared_forms`, `test_plan_failure_is_atomic_and_bounded`; all declared ordinary seeds and impossible count/separation fixture. |
| G3-08 | `test_full_width_reciprocal_roads_and_rivers_both_axes`, `test_boundary_adjacent_bridge_exact_bands_both_axes_and_unassigned_water`; retained legacy ford tests. |
| G3-09 | Shared-form test, per-member scene diagnostics, world-owned civic/road identities and both settlement detail drawings. |
| G3-10 | `test_reservations_conflicts_and_exact_assigned_frontage`; profile complete-width rejection, actual planned content access validation and journey interaction. |
| G3-11 | Reservation/schema/atomicity tests; owned crossing negative, conflict/vacancy diagnostics, retained protected-stair tests. |
| G3-12 | `test_plan_failure_is_atomic_and_bounded`, `test_late_population_failure_no_world_plan_cache_or_owner_publication`; deterministic retry. |
| G3-13 | `test_order_global_draws_and_complete_scene_identity`, `test_migrant_first_complete_scene_and_cached_mutations_do_not_respawn`, `G3Lifecycle.test_fresh_process_hash_seeds_complete_plan_and_content`; fingerprints include content/links/provenance. |
| G3-14 | `worldgen_g3_diagnostic.py --journey`, seed 20261023: normal lab ascent, both settlement forms, actual bridge traversal, authored container interaction, landmark and exact boundary positions. |
| G3-15 | Journey F5/exploration/interaction/F9; lifecycle pending-change test and migrant/cold-cache mutation test. Travel leaves checkpoint HEAD unchanged. |
| G3-16 | `test_startup_and_f9_restore_never_generate_plan_or_population`, `test_saved_plan_validation_and_legacy_modes`, `test_reference_validation_distinguishes_generated_and_unversioned_owner_maps`; existing checkpoint recovery gate. |
| G3-17 | `test_semantic_dependency_scoping`, `test_pending_semantic_change_preserves_load_cached_scene_and_unaffected_placement`; saved/cached state succeeds, unaffected new landmark succeeds, changed pending house fails before publication. |
| G3-18 | Both final browser runs: 65 originals + 64 live codec round-trips, actual control edits/downloads and CLI/planner; exact walkthrough, sentinel and orientation outputs. |
| G3-19 | Declared ordinary seeds `[0,20261023,29417]`; every result/timing/plan size recorded, explicit stress fixtures, no tile generation at plan completion; journey transition/checkpoint costs. |
| G3-20 | Final frozen-input focused/browser/diagnostic/full-gate reports, archive manifests, commit reconciliation and remote verification. |

The journey is a controlled movement fixture: native actors remain present as
stationary obstacles, while AI/survival turn updates are paused. Movement, doors,
stair eligibility, interaction visibility/corner rules, scene preparation, travel,
F5 and F9 use production handlers. Separate tests certify native population and
ownership. It is not a full combat/survival balance playthrough.

## Checkpoints and verification provenance

The final run passed **148 focused tests**, **28 checks in each browser**, all
three declared ordinary seeds and the complete connected journey. The unfiltered
production gate passed **3,675 checks across 159 workers**, retaining all seven
runner negative controls. All reports reconcile to the same 583 source inputs.

The three observed world plans took 0.599–0.706 seconds and occupied
527,981–657,128 compact JSON bytes, with no scenes generated at plan completion.
The representative journey walked 26,989 steps and 412 exact chunk boundaries;
its worst observed transition was 0.207 seconds. F5 took 1.025 seconds and F9
0.410 seconds, with an 18,818,411-byte checkpoint. Plot occupancy was 44–48%.
The evidence guide records per-seed costs, repetition, vacancies, detours and the
limits of comparison with the preserved G2-style path and historical G2 results.

- Start: `checkpoint/worldgen-g3-start-20261023` → `3466fc6`.
- Corrections: `checkpoint/worldgen-g3-corrections-20261023` → `e081eda`, 132 focused tests.
- Plans: `checkpoint/worldgen-g3-plans-20261023` → `68dc048`, 142 focused tests plus targeted plan checks.
- Composition: `checkpoint/worldgen-g3-composition-20261023` → `9abf702`.
- First final input: `checkpoint/worldgen-g3-final-gate-inputs-20261023` → `9abf702`.
  Focused/browser/journey passed; the production gate exposed an over-broad
  reference check for synthetic unversioned owner maps and was interrupted.
  Its partial worker results and failure diagnostics are retained.
- Corrected final input: `checkpoint/worldgen-g3-final-gate-inputs-r2-20261023`
  → `cbc9c66`; the new regression distinguishes an unversioned owner from a G3
  surface missing required references. This commit also normalizes the touched
  save-manager file's CRLF to LF; no other non-newline behavior is hidden there.
- Verified delivery: `checkpoint/worldgen-g3-verified-20261023`, the final
  documentation/evidence commit with frozen runtime inputs. The final delivery
  response gives its full verified remote main/tag SHA.

Final measured results and remote verification are recorded in
[`evidence/worldgen-g3/README.md`](../../evidence/worldgen-g3/README.md).
The evidence/documentation delivery commit changes no tested input. Raw execution
hashes remain separate from semantic dependency hashes. The browser report names
both its UI subset and the complete runtime source manifest; codec coverage does
not mean every control was exercised on every document.

## Explicit limits and next question

This arc provides finite shared composition, modest grid/linear forms and a small
opted-in asset subset. It does not add infinite generation, a continuous viewport,
multi-chunk buildings, recursive compounds, capital redevelopment, history/economy,
general neighboring AI, arbitrary authored creatures, physical body/stele
semantics, save compaction, generator archives, campaign migration or gameplay RNG
replay. Required connected pools reject deliberately remote profiles; optional
legacy ruins remain outside them. Vacancy and repetition are measured separately
from hard traversal validity.

The next design question is which settlement proportions, open-space density and
asset variety the owner wants before expanding the connected library or adding
compound buildings. Those are a later review/brief, not implied G3 scope.
