# G5 — Settlement variety and practical authoring

G5 runs in the existing production checkout on `main`, beginning clean at
`a68ffc5e9b07f4a9c2abbe43764ae6271cbb6a61`. The owner requested execution of the
attached brief. Its implementation requirements were used as the specification;
its claims about prior acceptance were not treated as new owner acceptance.
No personal campaign, alternate development checkout or desktop control was used.

## Implemented behavior

The primary road-facing entrance is separate from other required entrances.
Every required span still has valid outward geometry and must be reachable from
the assigned join. Service access through the interior is supported. New plans
record the selected entrance ID; historical plans derive it from their saved
normal/approach, preferring main then lexical ID without rewriting the plan.
The supplied failure was reproduced before changes, and the exact original G3
two-door plan is now exercised in a synthetic disposable checkpoint envelope.
Its canonical identity remains
`3efaf348da3c7daa3964645ae7355705fcb52e79de92cc4dd708188c1f3c13b1`.
This is an authentic historical plan, not a historical full-campaign fixture.

Twelve additional existing layouts have explicit connected profiles. No new
building geometry or content repair was needed. The four previous profiles remain
supported, including the mandatory spent-bell civic anchor. The live structure
corpus remains **64 documents**; the **65 frozen original codec documents** are
unchanged. Existing item/container/scene meanings are preserved.

The authoritative role table is
`roguelike/data/generation/settlement_profiles.json`. Version-2 geometry settings
retain the existing `g3_config.json` filename. New plans resolve residential,
commercial, support, civic and landmark intent before fitting. Each settlement
requires residential and commercial content; grid also requires one civic bell.
Support and remaining slots are optional. There is still one geographical
landmark, with four eligible existing alternatives.

Required assignments use bounded backtracking before optional filling. The
default budget is 256 asset/slot trials per settlement, with permitted transforms
inside each trial. A concrete two-slot regression proves that a flexible
commercial choice is moved to preserve the only residential frontage. Exhausted
requirements fail before world publication. Failed trials consume no accepted
cap. Private space stays exclusive; assigned public road cells may be shared.

The effective asset weight is base `placement.weight` × role multiplier × local
repeat multiplier. Asset selection precedes transform trials. Hard caps count
accepted instances per settlement. The nearest occupied slot in stable spatial
order receives a soft repeat penalty; ties choose the earlier slot. A sole
eligible choice records a soft fallback, while a weighted repeat remains labeled
as such. Caps are never silently exceeded, and optional failures remain gardens.

Slots are ordered by Manhattan distance from the original civic/arrival slot,
with coordinate and normal tie breaks. Required commercial content therefore
starts near arrival; remaining slots use the explicit commercial/residential/
support/residential schedule. Building roles do not create new merchant AI,
trading, quests or member zoning. `native-town-v1` remains unchanged: standard
grid members are civic plus residential; roadside members are market/residential.

## Cohort and real content

All admitted IDs passed every permitted direct transform and a full assigned
scene in each declared context. Controlled cohort checks retain other roles;
ordinary installed policy evidence is reported separately. No equal-frequency
or occupancy quota is claimed.

| Asset | Size | Context / role | Rotations / mirror | Required doors and actual goals |
|---|---|---|---|---|
| house_small_b | 8×7 | grid, roadside / residential | 0,180 / no | South main; family book, kitchen barrel, interior. |
| house_two_room_a | 10×8 | grid, roadside / residential | 0,90,180,270 / no | South main; both rooms and bedroom shelf through internal door. |
| house_hearth_a | 12×9 | grid, roadside / residential | 0,180 / no | South main; shelf, kitchen pots and interior. Painted hearth is not populated. |
| shop_a | 10×8 | grid, roadside / commercial | 0,180 / no | South main; readable and both interior areas; legal diagonal entry. |
| apothecary_a | 11×8 | grid, roadside / commercial | 0,180 / no | South main; three real containers and rear room; legal diagonal entry. |
| workshop_a | 12×9 | grid, roadside / commercial | 0,90,180,270 / no | Complete two-cell entry; two readables and scholar scene item. |
| storehouse_a | 14×7 | grid, roadside / support | 0,180 / no | Separate three-cell gate and service door; four containers and manifest. |
| tool_shed_a | 8×6 | grid, roadside / support | 0,180 / no | South main; tool rack, iron chest and sack. |
| shrine_a | 8×7 | grid, roadside / support | 0,180 / no | South main; inscriptions and offering scene. No civic bell. |
| hunter_cabin | 8×6 | landmark | 0,90,180,270 / no | South main; herbalist readable and interior. Furniture glyphs remain floor; old hunting loot inactive. |
| shepherds_hut_a | 7×6 | landmark | 0,90,180,270 / no | South main; explicit populated hearth-container. |
| waymarker_shelter_a | 6×5 | landmark | 0,90,180,270 / no | Two separated south doors; coffer, marker readable, position beside blocking waystone. |

Mirroring was not newly granted to these layouts. Half turns support ordinary
opposing street fronts; full quarter turns are deliberate for the two-room house,
workshop and rural spur alternatives. E/W orientations are certified in direct
previews without pretending ordinary N/S slots select them.

The handoff's static waymarker description needs a runtime correction: its legend
uses `waystone_plinth`, but `layout_stamper._set_tile` converts that ID into decor.
The production interaction test verifies the actual authored position and this
blocking decor representation. The functional counter now counts the union of
terrain/decor waystone positions, never the same object twice. A source terrain
label alone is not evidence of its eventual map representation.

## Saved-world contract

New worlds use `wg5`, format 3, `shared-v1`, `native-town-v1` and `structure-v1`.
These versions describe different contracts. The campaign save format is unchanged.
Resolved policy is stored once with required plot roles, asset/transform and
frontage identity. Invalid/missing new fields fail actual checkpoint preparation.

G3/G4 plans retain their exact geometry, dependency projection and identity, with
no role backfill or reselection. Already saved wg3/wg4 scenes restore their saved
mutations and provenance. New scenes from old plans use explicit g3-to-g5-v1 or
g4-to-g5-v1 adapters, dispatching by actual scene revision as well as plan origin.
The authentic supplied G4 plan is also covered in a synthetic disposable envelope.

Role/pool/weight/cap changes affect future plans only. A positive changed-selection
test restores and materializes the old choice. Relevant consumed-definition edits
still block only affected pending placements; load, visited scenes and unaffected
pending locations remain supported. Generic owner maps and legacy/no-plan worlds
retain their prior exceptions. Native input fingerprints remain observations,
not a global catalog-edit load gate. No source/catalog graphs or validation
receipts become map state.

The real interaction test takes an apothecary item, travels to the authored
waymarker, inscribes it, saves, mutates, cold loads and exercises F9. Container
contents and inscription state survive without refill. Existing late-failure,
coherent recovery, native-update, prayer, resource, stairs and ownership tests
remain in normal discovery. Fixture positioning and stationary actors are
declared; these checks do not establish encounter balance.

## Author and tune

The [six executed recipes](../../roguelike/docs/STRUCTURE_AUTHORING.md) cover a
service-door house, real commercial/support contents, the existing landmark slot,
settlement character, repetition, and diagnosis/installation. Complete source
examples live in `roguelike/docs/examples/g5_*.json`, outside live pools.
Initialization guards preserve edited drafts. Draft previews keep installed
policies and register the draft only in memory. Installation is deliberate;
the automated install check uses a disposable data catalog, not another checkout.

Use `tools/structure_authoring.py --orientations`, `--planned --context ... --role ...`,
`--selection-config ...`, `--catalog`, `--refresh-editor-catalog` and
`--check-editor-catalog`. The guide records exact keys, units, defaults, ranges,
effects and saved-world implications. A draft can be eligible yet not selected at
a particular seed; the unsuccessful seed-0 landmark recipe is retained and the
working recipe uses the already declared seed 29417.

G4 history is preserved with an explicit correction: its timed sample included
the capital gateway, not the crossing. G5 labels that set and checks the required
crossing separately. The guide also corrects standard grid native member roles.

## Acceptance mapping

Tests below are in `tools/critical_fix_regressions/tests/`. Final structured
results and exact source-bound commands are in the G5 evidence guide.

| Requirement | Concrete implementation / evidence |
|---|---|
| G5-01 | Retained before/after probe, input-package hash ledger, authentic compressed G3 plan and dependency binding. |
| G5-02 | placement.frontage_entrance; plan_integrity; planned_scene.validate_access; G5Entrances transform/direct/assigned/negative cases. |
| G5-03 | G5Entrances authentic-plan checkpoint/F9 test; unchanged digest and visited mutation; retained G4 durability negatives. |
| G5-04 | Twelve explicit profiles, cohort table and declared JSON; original four supported. |
| G5-05 | G5Cohort every permitted transform and context; direct goals plus complete assigned-scene positives. |
| G5-06 | settlement_selection and format-3 planner; G5Selection default role/cap/single-landmark checks. |
| G5-07 | Asset-first fitter; captured [6] then [1.5] weights despite multiple transforms; retained cross-process hash/RNG test. |
| G5-08 | Hard-cap vacancy, failed-fit quota, soft-fallback, bounded-infeasibility and constrained two-slot backtracking cases. |
| G5-09 | Required saved selection/role/frontage validator and actual checksum-consistent checkpoint corruptions. |
| G5-10 | Exact G3/G4 plan fixtures, visited wg3/wg4 mutations, legacy/no-plan and generic-owner regressions. |
| G5-11 | scene_adapters dispatch; opposite-order full fingerprints; actual saved old/new adapter checkpoint positives. |
| G5-12 | G5 selection-only pending positive plus retained G3/G4 consumed-definition affected-only failure cases. |
| G5-13 | Existing native/waystone/prayer/clay handlers, ordinary native updates, new apothecary and authored-waymarker interactions. |
| G5-14 | One landmark owner/node; four alternatives, all assigned-context positives and single-site assertion. |
| G5-15 | Retained late failure after population/dressing; actual container mutation/travel/cold restore/F9; no duplicate refill. |
| G5-16 | Declared three-seed diagnostic; zero-inclusive conditional outcomes; role/asset/cap/repetition counts and explicit denominators. |
| G5-17 | Updated real-handler journey chooses new cohort container and required landmark goal; exact transitions and coherent start rollback. |
| G5-18 | Complete examples and six recipes; verify_g5_authoring exact argv/cwd/exit/output hashes, edit records and repeated sentinels. |
| G5-19 | Both browsers' actual separated-door/weighted-special downloads through compiler and mixed planned preview; frozen and final codec corpora; refreshed catalog. |
| G5-20 | Frozen-input focused, browser, authoring/catalog, diagnostic/journey and unfiltered production gate; source reconciliation and checkpoint chain below. |

## Retained failures and corrections

- The supplied before probe reproduces the original required-secondary-door
  rejection in fresh planning and the authentic G3 plan.
- The first new inaccessible-door fixture hit an unrelated blocked container;
  it was corrected to block the actual service span, preserving a real negative.
- The first cohort test used the wrong catalog attribute; the corrected complete
  certification passed all twelve layouts.
- The first waymarker interaction test expected literal terrain. Production
  stamping converts it to decor; the test now checks the transformed authored
  coordinate, blocker and actual handler rather than changing game content.
- The seed-0 landmark recipe honestly reported no selection; seed 29417 from
  the declared set provides the documented mixed-policy positive.
- The first frozen focused gate at `4136a02` passed 174/175 tests. A legacy
  ownership fixture depended on a positive random encounter at seed 20261020;
  the new generation RNG domain legitimately rolled zero. Its disposable
  in-memory catalog now guarantees spawn attempts while retaining real factories
  and the nonempty retained-actor assertion. Runtime encounter policy is unchanged.
  The corrected final input is `4484469`.

All failed outputs retain their actual input manifests. No failed or unstable
run is relabeled as final acceptance. The two initial development authoring and
interaction suites overlapped; final gates run serially.

## Declared ordinary sample and costs

All three declared seeds completed without discarding a result. Every plan
finished with zero materialized scenes. Counts include the single landmark;
native counts cover every town member, excluding wilderness/landmark actors.

| Seed | G4 occupied/vacant | G5 occupied/vacant | Distinct selected assets | Town actors | Compact plan bytes | Planning seconds |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 77 / 4 | 72 / 9 | 13 | 42 | 589,110 | 0.866 |
| 20261023 | 89 / 8 | 85 / 12 | 13 | 46 | 726,297 | 1.077 |
| 29417 | 85 / 12 | 80 / 17 | 13 | 57 | 666,557 | 0.979 |

Every new cohort member appears naturally somewhere in this bounded sample.
The three landmark choices are shepherds_hut_a, waymarker_shelter_a and
hunter_cabin respectively. This is not a long-run frequency estimate; the original
roadside shrine remains eligible and its controlled positive is retained.

Each settlement has 6–12 distinct assets. The most-used asset accounts for
16.7–41.7% of its accepted placements (denominator excludes vacant plots).
Required minima and hard caps pass. Larger footprints, explicit role pools and
hard limits produce 4–5 fewer placements per world than G4. These vacancies are
legitimate; every accepted scene still passes complete access/content validation.
The new RNG domain can change native counts while retaining legal population
space and the existing district rules. Per-form/normal/asset/rotation/mirror
tables retain zeros, attempted transforms and reasons separately from saved plans.
Role tables retain eligible slots/assets, minima, accepted counts, caps and soft
repetition observations.

Compact plan size grows approximately 5–6% over G4, accounting for resolved policy,
roles, frontage identities and rejection information. Large zero-filled diagnostic
tables are separate report data, not durable world metadata. Final timed scene
ranges are 0.038–0.299, 0.034–0.284 and 0.047–0.273 seconds. They include the start,
every town member, landmark and capital gateway. The required crossing has a
separate positive access record for every seed.

The real-handler journey walked **27,075 steps across 412 exact boundary
transitions**, reached both forms and the landmark's usable goal, and took one
item from a newly admitted apothecary (two items to one). F9 restored the coherent
starting checkpoint. The worst observed transition was **0.274 seconds**, F5
**0.971 seconds**, F9 **0.531 seconds**, and the starting checkpoint occupied
**18,953,499 bytes**. The route length follows the changed authoritative plan;
it was not forced to match G4's 27,001 steps. Native actors remain stationary
obstacles, AI/survival updates are paused, and the player is invincible during
this journey. Separate short fixtures run ordinary native updates.

These are observations on the reused Python 3.11.0 / pygame 2.6.1 / tcod 19.3.0 /
NumPy 2.4.6 environment, with final suites run serially. G4 timing conditions
differed, so no performance improvement or regression magnitude is claimed from
those historical timings. The checkpoint size measures the saved starting state,
not a long explored campaign or world-scale benchmark.

## Verification results and delivery identity

All final gates passed on frozen input
`44844691fbc034a109e82ed88c10f09760c3af62`, with no source changes during any run.
The [evidence guide](../../evidence/worldgen-g5/README.md) links the compact
results, exact command receipts, original worker results, source reconciliation
and verified archives.

| Final gate | Observed result | Wrapper seconds |
|---|---|---:|
| Complete focused discovery | 175/175 tests; no failures or skips | 273.212 |
| Full Chromium + Firefox | 30 checks each; 65 original + 64 live codec documents each; actual downloaded candidates pass runtime checks | 21.799 |
| Executed authoring + catalog | 22 commands, 4 edit/install records; guarded drafts survive repeated initialization; catalog current | 18.812 |
| Three-seed diagnostic + journey | All declared seeds and real-handler journey pass | 120.612 |
| Explicit commercial-role CLI | Documented `--role commercial` mixed-policy positive | 2.259 |
| Unfiltered production gate | 3,675/3,675 checks; 159/159 valid workers | 568.343 |

The production evidence includes all seven deliberate runner-negative controls
and thirteen deliberate crash workers, with actual jobs/results and coverage.
No filtered case selection substitutes for this gate. Browser versions are
Chromium 156.0.8078.4 and Firefox 157.0, with Playwright 1.64.1. Catalog validation
reports 64 assets, zero errors and 238 classified warnings: 229 INACTIVE_FIELD,
3 INACTIVE_POOL_FIELD, 4 DEFERRED_SPECIAL and 2 TERRAIN_UNUSED. These describe
retained legacy authoring semantics; no content repair was hidden to remove them.

All six final command receipts bind the same 611 inputs to the tested commit.
Reconciliation finds 376 byte-identical files and 235 differing only in checkout
CRLF versus Git LF; there are no content differences. The frozen original codec
corpus remains unchanged, and removing only the new placement field from each of
the twelve cohort definitions reproduces its original data exactly.

The scoped implementation/checkpoint chain is:

| Checkpoint suffix (`checkpoint/worldgen-g5-…`) | Commit | Purpose |
|---|---|---|
| start-20261023-a | a68ffc5 | Clean production baseline |
| entrances-20261023-a | 7e2a94c | Secondary-door compatibility and authentic historical fixture |
| cohort-20261023-a | ebd2037 | Twelve existing profiles and certification |
| selection-20261023-a | 9dab6fb | Roles, bounded fitting and explicit scene adapters |
| authoring-20261023-a | 4136a02 | Authoring, browser, interaction and diagnostic implementation |
| final-gate-inputs-20261023-a | 4136a02 | First freeze; failed ownership fixture retained honestly |
| final-gate-inputs-20261023-r2 | 4484469 | Corrected fixture; all final gates pass |
| verified-20261023-a | Resolve tag | Documentation/evidence delivery commit; identical tested inputs |

The final commit adds only documentation and evidence after the tested input.
Its exact identity is the immutable
`checkpoint/worldgen-g5-verified-20261023-a` tag, avoiding a self-referential hash
inside this document. The delivery message records the observed full commit hash
after comparing local HEAD, remote main and the remote verified tag following the
ordinary atomic push. No history was rewritten and no checkpoint tag was moved.

## Limits and next scope

This is controlled variety within two existing forms and one landmark owner.
It adds no new streets, terrain adaptation, trading, quests, capital redevelopment,
cross-chunk structures, independent POIs, cache redesign or continuous viewport.
The inherited `UI-TEXT-HEIGHT` item remains deferred. Performance measurements
are bounded observations, not scale or long-campaign guarantees. Optional owner
play is separate from autonomous acceptance. The next review should scope multiple
independent POIs and road attachments, then compounds/network quality and later
world scale/continuous traversal.
