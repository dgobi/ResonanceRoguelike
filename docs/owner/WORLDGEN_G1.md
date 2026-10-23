# G1 — Existing generation correctness

Implemented on production `main` on 23 October 2026, starting from clean
`ce1ef760d411a0d1e9dfec93f1addf149955ac8c`. The start checkpoint is
`checkpoint/worldgen-g1-start-20261023-155942`; the coherent implementation
milestone is `1172080` / `checkpoint/worldgen-g1-core` (106 focused tests).
Runtime protection follow-up is `2855dec`; the final gate input is `5dc2f65` /
`checkpoint/worldgen-g1-gate-inputs` (110 focused tests, including a nonempty
generated market-crate interaction). Generation revision is **`wg1`**. Final
validation and delivery are recorded below.
This is implementation completion, not a claim of subsequent owner acceptance.

## Player-visible behavior

The first visitor to a new scene receives its complete native contents whether
that visitor is the player, a crossing creature, or a live pursuer. Startup builds
the surface with full data and retains its actors while the player begins in the
laboratory. Ordinary travel, ascent and debug travel reuse active/cached state.
Returning to a looted scene cannot replenish containers, restore killed actors or
undo terrain edits. Failed creation retains the current owner and staged metadata.

Town scenes now create their declared floor items. `interrupted_meal` creates its
dried provisions and water skin. The laboratory's existing weighted table is
resolved once. Hovel and hunter-cabin doors now reach their authored notes, in
normal and mirrored placements. Every declared town street band has a reciprocal
mouth and inward connection; the centre plaza has an exterior circulation ring.
World road/river mouths respect position and width. The physical cracked plaza
bell sets gameplay metadata before guardian selection.

## Ownership and materialization

`engine/scene_generation.py` owns complete `create_surface` / `create_submap`
candidates and their shared `populate` adapter. It deep-copies metadata, validates
references, builds objects through ItemFactory/CreatureFactory and publishes
objects via existing floor/container APIs. Engine helpers select the active owner
first, then an inactive cache, then permitted first creation. Completion and
revision markers appear only on successful new results. Arrival placement and
pursuit transfer occur afterward, outside native generation. Materialization
itself does not tick gameplay, effects, weather or offscreen simulation.

A one-level weighted table supports item, container, scene and empty choices;
weights default to 1, are finite/nonnegative and have positive total. Enclosing
coordinates transform once and source definitions remain unchanged. Unsupported
kinds/nesting and missing supported references produce asset/index diagnostics.
Body and stele records remain explicitly deferred; authored submap inscription
metadata is retained, without inventing physical objects or dialogue semantics.

Stale same-address cache rows and immutable checkpoint snapshots are not live
owners. An active scene wins over them. Creature migration, live pursuit, timed-out
pursuit and pending arrivals retain their existing owner separation. Generation
never substitutes for a missing/corrupt checkpoint: SaveManager validation and B3
recovery remain authoritative. New exploration writes the session overlay and
cannot advance F5's HEAD/BACKUP; F9 discards post-checkpoint exploration.

## Reproducibility and geometry contract

`GenerationContext` uses BLAKE2b-128 over compact UTF-8 JSON with explicit scalar
type tags. Keys include revision, stored world/scene seeds, scene address and
purpose. Partitioning, room/corridor construction, roads, building selection,
initial population, found texts, per-container loot and functional decor have
separate generators. Installed tcod 19.3.0 requires the retained seeded Random
object's C handle for BSP splitting. No tcod upgrade was needed. Candidate sets
used by WFC are sorted. No whole-game RNG replay claim is made.

The semantic fingerprint includes terrain and gameplay flags, functional decor,
actual item state, container state/contents, actual native actor definitions and
initial state, inscriptions, links and meaningful generation metadata. It excludes
FOV/light buffers, timings and Python identities. Arrival and the intentional
migrant are compared separately; runtime ownership is independently asserted.
Fresh interpreters use PYTHONHASHSEED 1 and 2, A→B/B→A order and unrelated gameplay
RNG draws, with nonempty native surface fixtures and authored/BSP submaps.

Shared river identity uses the sorted adjacent coordinate pair and world seed;
town bands use the town ID, cardinal role and world seed. For an axis of length L,
positions quantize to `clamp(floor(p*(L-2))+1, 1, L-2)`. Width cells start at
`centre - width//2`. North/south use map width, east/west use height. Exact mouths
and straight approaches are reserved; wandering occurs inside the chunk. River
water remains player-walkable and creature-forbidden; ford logic preserves that
distinction instead of painting every crossing cell as a road. Macro size,
whole-world geography, town count and the one-million-value chunk seed range are
retained. The new shared widths/bands change newly generated local layouts.

Entrance placement tests row-derived full bounds and protected building/route
footprints, functional objects, existing/staged contents and their legal adjacent
approaches. It tries at most 300 shuffled candidates, stages the terrain/decor,
and requires a physical accessible down-stair before linking it. A bounded bare
stair fallback is permitted only on free accessible ground; impossible locations
fail before publication. Completed surface stairs and submap arrival/return paths
are validated after content placement. These guards are new invariants, not a
claim that the original audit observed an overwritten stair.

WFC has ten deterministic attempts. Success is adjacency-validated before
painting; None, load failures and exceptions record palette, rectangle, RNG-state
key, revision and reason before eligible fallback fill. Protected structures,
roads, objects and functional decor survive. The 74×37 outskirts seeds 0–9 have
**0 solves and 10 bounded fallbacks**; that is not ten successful WFC solves.
A separate successful small palette fixture satisfies all adjacency constraints.

## Existing saves

Absent provenance/completion fields mean **legacy-authoritative**. Intentionally
empty, partially historically populated and looted maps are never backfilled.
Saving a legacy world preserves `legacy-unversioned`; genuinely new scenes can
carry `wg1`, allowing mixed-generation exploration. Historic cross-version seams
are not certified and no map is overwritten to force agreement. Save-version
restrictions and rejection of unsupported old flat slots remain unchanged.
No personal campaigns were inspected, migrated, regenerated or deleted.

## Acceptance evidence

The tests run in the existing focused discovery path; none is an uncollected
standalone acceptance helper. All fixtures use actual data and temporary saves.

| Contract | Evidence in `tools/critical_fix_regressions/tests/` |
|---|---|
| G1-01 | `test_generation_g1`, `test_generation_ownership`: town/wilderness first creators; full semantic content and one intentional migrant |
| G1-02–03 | ownership: authored/BSP live-pursuer first, startup/lab, ascent, cached/active debug travel |
| G1-04 | content: all four scene definitions, synthetic guaranteed weighted kinds, actual lab table, exact transformed coordinates |
| G1-05 | ownership: actual kill/loot/container/terrain mutations; hot, cold and fresh-process save/load |
| G1-06 | content/ownership plus existing pending-arrival tests: active owner, stale cache, live/abandoned pursuit and migration |
| G1-07 | content/ownership: malformed references/tables, injected population and final validation failures, retained owner/metadata and successful retry |
| G1-08 | ownership: missing/corrupt checkpoints never call generation; F5/exploration/migration/F9; full B3 gate recovery |
| G1-09 | ownership: absent fields and empty legacy scenes, retained world provenance, current newly explored scene |
| G1-10–11 | content/G1: cross-process/order/gameplay matrix, BSP repeat, both weighted-entrance consumers, WFC adjacency |
| G1-12 | content/geometry: forced None/exception, protected fallback; `final-focused/wfc-outskirts.json` |
| G1-13–14 | geometry: two complete world metadata seeds, 36 fully populated town chunks, all bands and wilderness interfaces, rectangular positions/widths, exact mountain seam, inward roads and ford semantics |
| G1-15 | G1/geometry/ownership: both transforms, retained pools, real generated placements, actual movement/open/pickup/read, a real generated market crate reached, opened and transferred through game handlers |
| G1-16 | geometry/ownership: impossible/oversized/full authored entrances, preserved objects/approaches, final stair validation and arrival/return routes |
| G1-17 | geometry: physical cracked bell, no-plaza fallback, non-centre behavior and guardian eligibility |
| G1-18 | final focused log, unfiltered D gate and supplied example checker, recorded below |

Before evidence is in `evidence/worldgen-g1/before`. The six baseline regression
tests produced nine failing assertions/subtests: first-creator contents, missing
town scene items, same-seed BSP, ignored road positions, inaccessible hovel/cabin
notes and debug scene replacement. The original first-creator probe recorded six
native actors, 21 containers and ten floor items for player-first; creature-first
had only its migrant and no containers/items. Fresh-process probe outputs retain
functional-content differences. These are baseline observations, not guarantees
about every seed.

The terrain diagnostic reads actual generated arrays. Its atlas omits decor,
objects and actors; action tests cover those layers separately. At seed 20261020,
36 town chunks previously had 66 unreachable hovel and 16 hunter-cabin notes;
after G1 both are zero, with no building overlaps. The new sample still selects
55 hovels and eight hunter cabins; deterministic RNG and reserved routes can
change the mix without removing either asset or changing placement ceilings. The reported (65,73) south /
(65,74) north road mouths change from [41,42,43] versus [37,38,39] to matching
[39,40,41]. The image demonstrates road continuity, not a previously observed
player hard-lock. `folk_saint_alcove` remains a separate inaccessible placeholder
outside these two asset repairs.

## Final commands and results

Use the existing Python 3.11.0 environment with pygame 2.6.1, tcod 19.3.0 and
NumPy 2.4.6. No dependency installation was necessary; the atlas uses pygame.
Run from the repository root:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --evidence evidence/worldgen-g1/final-focused
& $ResonancePython -X utf8 tools/verify_d.py
& $ResonancePython -X utf8 roguelike/docs/examples/validate_building.py --game roguelike --building roguelike/docs/examples/author_cottage_a.json --output evidence/worldgen-g1/authoring.json
& $ResonancePython -X utf8 tools/worldgen_g1_diagnostic.py --output G:/GameDev/RoguelikeProject/evidence/worldgen-g1/after
```

- **110 focused tests passed** in 77.663 seconds, including the original 66 tests
  and 44 G1 tests. Log: `evidence/worldgen-g1/final-focused/focused-tests.txt`.
- **Unfiltered complete D + B1/B2/B3/C gate passed: 159 workers, 3,675 checks,
  zero failures.** Source commit: `5dc2f65`. The gate's source-stability check and
  a post-gate byte-hash comparison both pass. No runtime/data/test changes follow
  this completed gate. One earlier run was intentionally interrupted to add the
  real-container action fixture; only the restarted completed gate certifies G1.
- The supplied authoring checker passes. Cross-process semantic snapshots agree;
  the final terrain/access atlas was inspected. Syntax parsing and `pip check`
  pass. The source/document diff check preserves existing CRLF and permits a
  harmless final blank line; verbatim evidence logs retain their original trailing
  whitespace. No unrelated formatting normalization was delivered.
- [Summary](../../evidence/worldgen-g1/summary.json),
  [full compressed gate report](../../evidence/worldgen-g1/d-results.json.gz),
  [gate console](../../evidence/worldgen-g1/d-console.txt),
  [before atlas](../../evidence/worldgen-g1/before/terrain-atlas.png), and
  [after atlas](../../evidence/worldgen-g1/after/terrain-atlas.png) form the compact
  review package. The summary records the uncompressed report digest.
- Final delivery checkpoint: `checkpoint/worldgen-g1-verified-20261023`.
  Diff from `checkpoint/worldgen-g1-start-20261023-155942` to that tag for the
  complete scoped result. The remote is the existing
  `https://github.com/dgobi/ResonanceRoguelike.git`, branch `main`.
  Push completion and the resolved remote SHA are reported with delivery.

## Authoring and subsequent work

[Structure authoring](../../roguelike/docs/STRUCTURE_AUTHORING.md) is updated for
G1 and retains its honest consumer limits. The supplied cottage and checker are
installed only under `roguelike/docs/examples`, not in live generation pools.
The checker passes both orientations and places 12 cottages with 24 specs in its
isolated fixture. It manually materializes example contents, so it is not evidence
for the repaired Engine adapter. The [audit/proposal](WORLD_GENERATION_AUDIT_AND_PROPOSAL.md)
and its image remain historical review material with a G1 status banner.

Next bounded target: dependable structure authoring/access contracts and a
lossless authoring workflow, scoped separately before implementation. The full
settlement/plot planner, new schema/rotations, wilderness POIs, painter round-trip
repair, town configuration activation and content expansion are deferred.
Also deferred: physical body/stele behavior, folk-saint placeholder completion,
full gameplay/AI RNG replay, historical generator retention, cross-version seam
migration, personal-save migration, checkpoint pruning, unrelated UI-TEXT-HEIGHT
and the previously recorded combat/survival follow-ups. No arbitrary WFC palette
redesign or claim of universal solvability is included.
