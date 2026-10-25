# G9 runtime review and next-stage implications

Reviewed source: `f9fe901417b360bc1fda84835e0a793eaac2f6df` in the read-only review checkout. Frozen G9 game inputs: `919e8b40ab5ebca6cf5df6ae3afaf6baa4b67d78`. This review inspected code, tests and retained cost evidence; fresh focused execution is owned by the parent review. No game, wiki, save or repository file was modified.

## Conclusion

No material correctness blocker was identified in the inspected G9 addition. Close the bounded road-connections arc once the parent review completes evidence reconciliation and fresh checks. The next feature brief should establish a useful player-facing exploration experience, using the existing road and settlement foundation. More route-quality metrics, extra shortcut search, or simulated transport efficiency are not justified by this review.

The strongest outstanding gameplay evidence gap is ordinary expedition viability. G9's long traversals explicitly use invincibility, stationary native actors and paused AI/survival. They establish real movement, physical connectivity and save-state correctness, but do not establish how those journeys feel or whether normal supplies, danger and rewards support them. A bounded expedition with active game systems is an appropriate next acceptance target. This is an evidence gap, not a finding that the current world is unplayable.

## What the G9 runtime actually does

- `roguelike/generation/world_plan.py:149–161,304–310` first composes and validates the complete historical G8 baseline, then augments it. It retains the G8 layout stream instead of rerolling towns to suit roads.
- `roguelike/generation/country_network.py:25–31` enforces complete policy fields, integer types, finite numeric values and bounded limits. The default permits two links, 25% shared added construction, eight examined pairs, 8,192 expansions per search and 32,768 per world.
- `country_network.py:63–81` searches macro corridors with actual 80/43 tile costs and a matching Manhattan heuristic. New edges are barred from protected owner/submap/capital chunks, rivers and deep mountains. This is a finite candidate proposal mechanism, not a claim of globally optimal road design.
- `country_network.py:89–137` checks newly occupied full-width cells, existing bridge-deck scope, reservations and complete local road slices before staging. Added reservations precede private rows while preserving baseline row order. The water index narrows exact checks; it does not grant broader collision permissions.
- `country_network.py:140–203` recalculates marginal unique construction and physical benefit against the current staged union. Candidate paths are cached, but physical benefit is reevaluated after the first accepted connection. Every qualified proposal uses normal plan validation. Optional inability to qualify produces an explicit bounded result.
- `country_network.py:206–253` validates the saved resolved contract without current policy or route replanning. It recovers baseline records, verifies their identities and order, checks construction accounting, rebuilds crossing/reservation additions and recomputes accepted physical benefit. `world_plan.py:552–560` and `plan_integrity.py:133–139` additionally check world geography at publication and restoration.
- Format-7 support is included in the public/common scene paths, dependency/adapter provenance, save preflight and world membership. Historical format-6 scenes remain historical; newly created pending scenes use the explicit G8-to-G9 adapter.

The new test files cover ordinary baseline preservation, all touched scenes, reverse first visits, disabled/zero/exhausted outcomes, two-link marginal accounting and overlap, exact budgets, existing-deck reuse, malformed policies and geometry, genuine historical restoration, current-policy removal, late rollback and sixteen checksum-consistent corruption cases. Those are meaningful behavioral checks. They should remain available as regression protection, without turning every later feature into another road-network research project.

## Costs and the correct interpretation

The reported planning increase is consistent with the source. Qualified candidates incur full normal plan validation and full-width physical BFS (`country_network.py:174–178`); final resolved validation and publication also validate the plan. `network_metrics.py:40–57` performs one sparse BFS per primary source until its remaining targets are found.

The retained seed-20261023 instrumented preview in `evidence/worldgen-g9/cost-investigation/summary.json` records eight macro searches at about 0.406 cumulative seconds, physical-distance evaluation at about 5.936, and normal plan validation at about 6.415. These are overlapping inclusive profiler values from a preview invocation, not additive timings or uninstrumented gameplay costs. They support the reported diagnosis that exact evaluation and validation cost more than macro search; they do not justify a fresh optimization project by themselves.

The expanded 470-scene, roughly 254 MB coverage checkpoint is larger than the 354-scene pre-edit run because it explores more geometry. It does not establish a storage regression attributable to a changed checkpoint implementation: G9 only adds version/provenance handling in that implementation.

Surface cache eviction already exists. `ChunkCache.evict_distant` in `roguelike/engine/save_manager.py:192–196` writes and evicts maps outside radius three; `roguelike/engine/engine.py:2331` invokes it on boundary transitions. It would be inaccurate to describe the present engine as having no cache eviction.

The remaining accumulated-campaign costs are concrete:

- `save_manager.py:211–236` gathers the complete checkpoint/session overlay, serializes hot/active state and validates every serialized scene.
- `roguelike/engine/checkpoints.py:175–220` writes a full new checkpoint generation and verifies it before publication. It validates the committed ancestor for backup and retains old generations; no retention cleanup occurs here.
- `save_manager.py:333–408` validates all saved scenes before atomic installation. Surface scenes are read once for entity validation and again for provenance. The current surface loop computes `digest(world.plan)` separately for each generated surface at lines 390–394.

A future focused checkpoint-cost brief can profile repeated work, retain exact corruption/rollback protections and establish a bounded retention policy if the owner commissions one. It should precede substantially larger world/campaign targets. It need not displace a small expedition-quality arc now, and should not be combined with terrain, encounter, world-scale and rendering changes.

## A useful next player-facing target

Require a short, reproducible journey from a normal fresh start through a legible country route, one meaningful optional stop and a reachable settlement or return point. Use actual visible information, interactions and ordinary supplies; include a period with native AI and survival active, invincibility off, and no teleports or injected consumables. Record movement/turns, starting resources, resources found and consumed, threat encounters or avoidance, and the final saved state. Keep controlled fixtures for targeted geometry/state assertions, but label them separately from this ordinary run.

The installed `roguelike/data/survival.json` defines hunger capacity 1,000 and thirst capacity 800 with base tick rates one; plains thirst has a 1.1 multiplier. `engine.py:1388–1417` applies biome rates and critical-stage damage when invincibility is off. The improved 8,063-step capital itinerary is therefore not a suitable surrogate for an ordinary early expedition unless resupply and action costs are included. Do not infer a universal sustainable travel distance by dividing capacity by that step count: diagonal movement, interactions, biome changes, item use, combat and other travel choices alter the accounting.

The acceptance goal should be readable reasons to explore and manageable decisions about risk and resources, grounded in the existing Resonance assets and lore. It should not be a numeric road-efficiency target or a requirement to populate every empty stretch.

## Scope boundaries

Preserve the delivered G9 policy and route geometry while developing the next bounded experience. Do not add shortcuts, reroute the baseline, enlarge the map, introduce traffic simulation, redesign storage, or make continuous rendering a hidden dependency.

The owner's latest instruction explicitly removes routine wiki maintenance from implementation work. A small directly affected authoritative guide and a completion report can document a feature; rebuilding or expanding the owner wiki belongs to a separately commissioned targeted brief. Historical G9 wiki work remains valid evidence of that completed commission, not an ongoing gate for G10.

## G10 terrain-character contract review

The proposed next arc, coherent wilderness and distinctive biome character, has a concrete source basis. `generation/region_gen.py:201–228,280–309` currently draws trees independently per tile for open land and forest, with a small connectivity pass for forest. Ash Wastes uses `varied_grass` with tree chance 0.01 (`102–106`) and receives the same fourteen tall-grass clusters as generic open land (`133–137`). That conflicts visually with its existing barren, discharged-stone entry text in `data/biomes/ash_wastes.json`. A terrain-character pass can improve the setting without touching the road algorithm or world-scale geography.

### Preserve historical pending generation explicitly

The current global `GENERATION_REVISION` is `wg9` (`generation/context.py:8`). Every `GenerationContext.seed` includes that revision (`37–42`). `planned_scene.py:27` creates a default context; `engine/scene_generation.py:135,159` does so for legacy surfaces and submaps. Therefore changing the global revision to `wg10` alone changes terrain, functional herb decoration, native population, entrance positions, container loot and underground streams. This would exceed a terrain-only task and reroll pending scenes of historical worlds.

Require a versioned saved surface/terrain policy for newly created worlds and explicit legacy dispatch for worlds without that policy. Preserve the G9 seed domains for unrelated content. Before edits, retain a genuine G9 checkpoint and fingerprints for representative pending scenes under the old implementation; verify the same pending results under the legacy branch with unchanged definitions. Cached scenes remain authoritative and must not be regenerated.

A new whole-plan format is not technically mandatory. The current format-7 road plan could remain byte-identical while a separately validated surface-generation policy is serialized with the world and recorded in scene provenance. Scene origin and world-plan origin already have separate adapter handling. If implementation chooses format 8 / wg10, it must do so deliberately: `country_network.baseline()` currently strips back to G8 and hashes every top-level baseline key, and its normal validation/publication dispatch explicitly recognizes format 7. Simply adding terrain fields or incrementing the plan version would break those identities or bypass the network checks. Extend the contract coherently rather than weakening G9 validation or silently treating old plans as new terrain.

The fresh terrain policy should record the algorithm version, applicable biome profiles, scalar parameters and stable seed domain needed for pending generation. Removal or change of the installed current policy must not silently repopulate an existing new-policy campaign differently. Keep the schema small; no duplicate world-sized field arrays, precomputed local scenes or persistent editable second geometry graph are needed.

### Functional terrain is more than appearance

`LocalMap.set_tile` (`world/local_map.py:133–156`) resolves `varied_grass` through `rendering/decor.py:48–55,83–101`. Its variants include harvestable plants, and the setter moves those variants to the decor layer. Calling this a cosmetic grass variation would miss a gameplay dependency. New barren ground and coherent vegetation should use explicit real terrain and deliberate plant placement, retaining the existing decor APIs and avoiding an accidental loss or multiplication of functional resources.

Existing terrain metadata also changes play: mud has move cost 2 and chill; tall grass 2.5 and concealment; ash 1.5; gravel 1.1. Denser vegetation and larger wet patches affect visibility, movement, escape and supplies. Retain all finalized road, bridge, approach, private, common and entrance protections; inspect and validate after dressing/native population, not just before.

The current resupply affordances are sufficient for a short demonstration without inventing new systems. `shallow_water` is drinkable and interactable; `river_water` is not labelled drinkable. `engine.py:3559–3583` supports drinking from terrain at the player's location, and `3987–4019` supports filling an empty water skin or drinking via interaction. A `water_skin` restores 400 hydration and becomes an empty skin. Rain collection exists at `3586–3625`. Dried provisions restore 300 nutrition, bitter herb 80; ordinary loot and harvesting can be used through actual handlers. These are existing content options, not a guarantee that every biome or route supplies them.

### Coherence and verification

Use absolute world-tile coordinates (`80*wx+lx`, `43*wy+ly`) and a terrain-specific world seed domain for broad coherent fields. Local chunk seeds alone create visible resetting patterns. Read saved adjacent biome metadata where necessary without generating neighboring scenes. Opposing edge tiles are at different coordinates, so demanding identical tile IDs there would be a mistaken continuity test. Instead compare independent chunk samples to a stitched/cropped reference field at the same coordinates, and verify visit-order/hash-seed independence.

A useful bounded acceptance set combines representative revealed production views for broad composition, normal-FOV views for actual readability, untouched infrastructure/ownership projections, playable access after all population passes, and a short active-survival/native-AI excursion. State exactly which ordinary cases and controlled biome fixtures are used. Do not require another 107,749-input exhaustive coverage journey, a new gameplay subsystem or a wiki rebuild to establish this terrain improvement.
