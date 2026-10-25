# Codex G10 — Wilderness character and playable exploration

**Project:** Resonance Roguelike.  
**Repository:** https://github.com/dgobi/ResonanceRoguelike  
**Reviewed source:** `f9fe901417b360bc1fda84835e0a793eaac2f6df`, `checkpoint/worldgen-g9-verified-20261024-a`.  
**G9 frozen game inputs:** `919e8b40ab5ebca6cf5df6ae3afaf6baa4b67d78`.  
**Prepared:** 24 October 2026, America/Edmonton.  
**Companion:** `G9_REVIEW.md`, with independent review evidence and current production views.

## 1. Implement this outcome

Make travel through the existing wilderness look and play like movement through distinct places in Resonance. Forests should have recognizable stands and clearings; wet country should have coherent pools and firmer ground; the Ash Wastes should read as the barren, discharged landscape described by the game; mountains should have rock masses and traversable gaps. These patterns must continue across storage boundaries and respect the existing roads, rivers, entrances and authored sites.

The goal is a **fun, playable, believable-looking post-apocalyptic open world that fits the existing setting**. Judge this change through actual terrain, visibility, movement, supplies and a short playable excursion. G9 has completed the bounded country-road task. Leave its road policy and geometry alone in this arc.

**Wiki maintenance is excluded.** The owner's latest instruction supersedes the automatic wiki-maintenance paragraph in `AGENTS.md` and earlier G8/G9 briefs. Wiki work is commissioned separately in targeted briefs at the owner's discretion. As a small explicit policy change, replace that paragraph with this rule while preserving the other collaboration preferences. Do not update wiki chapters/examples, rebuild the standalone HTML, run a wiki release gate, or introduce a recurring wiki-impact checklist. Keep the existing edition intact. A concise feature guide and completion report are part of this implementation.

## 2. Why this is the next step

G9 preserves the complete G8 composition and meaningfully shortens one difficult ordinary journey. Independent review confirmed the reported 23,625 → 8,063 physical steps, all 57 sampled primary-pair distances, and the unchanged baseline records. Further road ranking or transport simulation is unnecessary for this brief.

The underlying terrain remains much less composed. `region_gen.py` draws trees independently per tile and mountains from a 45% rock draw, with local scatter and clearing passes. Ash Wastes uses `varied_grass`, a 1% tree draw and the generic fourteen tall-grass clusters. In a newly materialized, unmodified seed-20261023 Ash Wastes scene at `(72,103)`, the review found 3,368 grass/tall-grass cells out of 3,440, 36 trees and 125 functional plant decorations. Its shipped description says that nothing has grown there since the bells. This is a concrete mismatch between setting and generated play space, not a request for realistic ecological simulation. [Sources: current region generator](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/generation/region_gen.py), [Ash Wastes definition](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/data/biomes/ash_wastes.json), companion review evidence `evidence/gameplay-direction/views/baseline-views.json`.

The original proposal already called for geography sampled in world coordinates and placed terrain variety after connected composition. This brief takes that bounded next step. It does not reopen climate, river placement or the road graph. [Original proposal, geography and development order](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/docs/owner/WORLD_GENERATION_AUDIT_AND_PROPOSAL.md).

## 3. Scope and visible character

Implement one shared wilderness terrain method with small profiles for the eight existing nonurban biome IDs. Use the existing terrain, sprite and decor vocabulary. The following are art and play intentions; they do not commission eight separate simulation systems.

| Existing biomes | Required visible and playable result |
|---|---|
| `forest` | Grouped tree cover, identifiable clearings and routes through the trees. Retain concealment, useful vegetation and existing native threats. |
| `plains`, `heath` | Predominantly open ground with broad, irregular vegetation patches and sparse grouped obstacles; preserve their different character through restrained profile choices. |
| `swamp`, `drowned_wood` | Coherent wet patches and firmer routes. Drowned Wood should visibly combine trees and inundation; use the existing water/terrain mechanics deliberately. |
| `ash_wastes` | Predominantly barren, stone-dominated ground consistent with the existing text. No default lush grass, living trees or harvestable flowers/mushrooms in the biome's interior. Preserve deliberate edge transitions and explicit authored content. |
| `mountain`, `deep_mountain` | Rock masses, broken ground and passable gaps rather than an independent rock/gravel draw at every cell. Preserve VUKH's identity, location and existing metadata; no new summit or dungeon content. |

Preserve the saved coarse world geography: biome IDs, elevation/moisture metadata, rivers, start, capital, VUKH, towns, landmark, submaps and all rural owners. Keep the complete G9 plan and its resolved selection/ownership records unchanged for the same seed and installed planning inputs. The preferred separate surface-policy contract preserves the entire format-7 plan identity. If a necessary format extension is justified under section 6, compare a lossless G9 projection and list the contract/header differences explicitly; resolved G9 content must still be exact. This gives a useful before/after comparison without moving the destinations to flatter the new terrain.

Town and capital generation remain outside the new wilderness pass. Protect authored building clearances, yards, approaches, compound paths, civic commons and entrance sites within wilderness chunks. Nearby unowned ground can acquire the new biome character.

Gate this decision on the original scene/world ownership. `planned_scene.py` temporarily changes its copied town base to `PLAINS`; testing only that copied type would accidentally opt towns into the new pass. Preserve existing saved surface entrances and all submap chunk/ID/type/link ownership. For a fresh new-policy world, an entrance resolved during materialization may move within its owning chunk to fit the changed ground; it must still satisfy its complete placement, arrival and return contract.

Existing `gravel`, suitable walkable stone/earth terrain, `ash`, water, tree and rock assets can supply the visual vocabulary. Verify their actual flags and costs before choosing them: `grey_stone` is blocking, and `ancient_floor` implies laid construction. Do not carpet the wastes in an impassable tile or invent new modern-apocalypse lore or art assets to solve this task.

## 4. Compose terrain in world coordinates

Use a small number of stable, inexpensive spatial fields or an equivalently bounded method. Broad cover, local variation and individual placement should have separate purposes. Sample using absolute world-tile coordinates:

`world_x = 80 * chunk_x + local_x`, `world_y = 43 * chunk_y + local_y`.

The same world coordinate must receive the same terrain decision regardless of chunk visit order, caller, Python hash seed or which side of a boundary requested it. Chunk-local seeds alone must not reset the broad pattern at every screen. Avoid regular clearings at every chunk centre and straight artificial strips along storage edges.

Read saved neighboring biome/environment metadata through a bounded halo to soften appropriate transitions. Use one shared calculation on both sides. Preserve each biome's intended interior character and allow abrupt natural transitions where the profile calls for them. Do not relabel the macro biome map, generate neighboring scenes to answer a terrain query, or allocate a whole-world tile field. The coarse map remains noisy in places; this brief improves its local realization without commissioning a new climate model.

Continuity does **not** mean copying identical terrain IDs onto opposing borders: those cells occupy different world coordinates. Verify independent chunk samples against the same coordinates in a larger sampled-and-cropped reference. Apply this equality to the natural fields and base-terrain decisions before local access repair, authored overlays, entrance placement and population. Verify completed scenes through their actual ownership/access rules and inspect multi-chunk production views.

Keep work bounded by the requested scene and declared halo. Any repair needed for required access must be deterministic, narrowly applied, and recorded with its reason and changed cells. Preserve recognizable terrain masses through those repairs.

## 5. Preserve playable infrastructure and functional content

Keep the existing composition order and ownership rules. Base terrain is followed by the authoritative water, bank, road, bridge, common, path and structure passes, then content and dressing. Validate the completed populated scene. New terrain or dressing must not overwrite a required road, crossing, approach, entrance, stair, common, container interaction position or authored goal. Use the existing failure-safe publication path. [Current realization and access checks](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/generation/planned_scene.py).

Do not treat vegetation as cosmetic. `LocalMap.set_tile()` can resolve `varied_grass` into harvestable plant decor. Mud, tall grass, gravel and ash also have different movement or survival properties; `shallow_water` is drinkable while `river_water` is not marked drinkable. Use the existing terrain/decor APIs and explicit eligible-ground rules so a change of palette does not accidentally flood the world with supplies, remove all resources or make the new landscape impractical to cross. [Tile behavior](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/world/local_map.py), [terrain definitions](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/data/terrain.json).

Keep existing native creature profiles, survival rates, loot tables, weather and interactions. Locations may change where the new ground legitimately changes eligible placement. Do not globally reseed those systems or rebalance their rates to make the terrain demonstration pass. Record resource counts and reachable resource opportunities for the representative scenes, including intentional absence in barren ground. Not every chunk needs every resource.

Use required access and actual off-road travel witnesses to judge traversability. Do not require every decorative pocket to connect, and do not silently flatten an entire scene to satisfy a test. A passable terrain flood fill alone does not prove that doors, blocking decor, native actors and interactables work.

## 6. Keep new terrain and historical worlds explicit

Before runtime changes, capture a small genuine G9 checkpoint from the unmodified source. Include visited and pending wilderness, one scene adjoining a road or authored site, and an actual interaction mutation. Preserve its exact source and scene fingerprints. Separately record the old generator's result for representative pending scenes without marking those scenes visited in the saved witness.

Introduce an explicit, validated, saved surface-generation policy for new worlds. It must identify the terrain algorithm, profile values and seed domain needed to generate pending scenes. Keep it compact. An existing new-policy campaign must not silently change terrain because the installed tuning file was edited, removed or replaced. Record the applicable terrain policy in scene provenance and reject inconsistent or unsupported contracts before installing state.

Genuinely historical world schemas lacking the new policy must retain the supported G9 terrain route. Use an explicit durable schema/provenance discriminator so deleting a required policy from a new-policy world causes rejection, not silent fallback to legacy terrain. Verify visited scenes unchanged and the captured pending G9 results reproduced under unchanged definitions. Keep authentic older fixtures and adapters passing. Never retrofit a new-looking edge beside a saved old scene through an implicit default, or relabel newly generated output as historical evidence.

**Do not simply bump the global `GENERATION_REVISION` to `wg10`.** That value participates in every purpose seed, including native actors, functional decor, entrances, containers and underground scenes. Give the new terrain its own explicit domain and preserve unrelated seed domains. Keep that domain separate from the ordinary `LocalMap.generation_context` consumed by `populate()` and `map_context()`. Terrain changes can alter eligible actor/resource positions; that is distinct from reseeding their random choices. [Generation context](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/generation/context.py), [scene adapters](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/generation/scene_adapters.py).

A new whole-world-plan format is not required merely because the work is named G10. Prefer a separately versioned surface policy if it preserves the format-7 network plan and its identity cleanly. If a plan-format change proves necessary, explain the reason and deliberately extend the network/common/save validation paths. `country_network.baseline()` and several validators rely on existing versions and baseline identities; neither extra unchecked fields nor skipped G9 validation are acceptable shortcuts.

Retain atomic failure behavior: malformed profiles, unavailable required terrain and a late post-population rejection must leave the active player/world, scene cache, RNG and checkpoint HEAD unchanged. Removing the injected problem must allow recovery.

## 7. Provide one useful tuning and preview route

Expose only the small set of profile controls that materially shape the intended terrain: palette, cover/patch scale, cover amounts and transition behavior as needed. Ship complete defaults for the eight existing wilderness biomes. Validate schema/version, terrain/decor references, finite ranges and bounded work; reject unknown or ineffective fields with useful errors.

Provide one headless preview command, preferably by extending a suitable existing entry point. It should render a selected multi-chunk area from a seed and optionally a draft profile, and report coordinates, policy identity, resource/access counts, repair events and timings. Preview the actual generation path. Clearly label revealed comparison images; provide normal-FOV images separately for play evidence.

Draft preview must not overwrite installed data or owner inputs. Reuse the shared output-path protection, including aliases/symlinks and report/image collisions. Include a complete editable example and a short authoritative guide explaining preview, deliberate installation and recovery. No new browser editor, general authoring framework or repeated suite of unrelated authoring workflows is needed. Refresh/check the derived structure catalog if its declared JSON-input identity changes, preserving the historical catalog-repair lesson.

## 8. Demonstrate a short ordinary expedition

G9's 107,749-input coverage journey paused AI and survival and used invincibility. Retain that evidence as a geometry/persistence test. G10 needs a small additional demonstration of the new terrain under ordinary play conditions, not another journey of that length. [G9 report and stated controls](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/docs/owner/WORLDGEN_G9.md).

Use an unmodified ordinary seed and the normal fresh-start route. A few adjacent chunks are sufficient. Travel from the start or its nearby road into the wilderness, make a meaningful choice around cover or wet/rocky ground, use an existing resource or interaction, and reach an existing useful stop or return point. At least part of the outing must leave and rejoin the road; verify natural boundary travel in both axes across the overall controlled/ordinary evidence.

Before terrain edits, do a bounded preflight of the intended outing or its normal-start movement/survival/interaction path. Retain any pre-existing blocker so it is not later misdiagnosed as a terrain regression. This is a small check, not another full baseline coverage journey.

For the ordinary excursion:

- Keep normal FOV, native AI and survival active, with invincibility off. Use real movement, door, interaction and inventory handlers.
- Use the normal starting inventory and resources obtained in play. No injected supplies, actor removal, teleports or hidden restoration of health/thirst.
- A known-seed scripted itinerary is acceptable. State how it was selected and any RNG controls. Full-state assertions can verify the result; do not present a scripted route as a test of a player's unaided discovery or an autonomous exploration AI.
- Record starting and final health/supplies, movement/turns, terrain choices, resources obtained/consumed, and threats encountered or avoided. Retain unsuccessful attempts that exposed a material issue.
- F5-save the actual explored and modified checkpoint, cold-load it and F9-restore it. Verify visited terrain, harvested/looted state, actor state and a subsequent pending scene.

The positive must show usable terrain and a plausible short expedition under the installed rules. Do not claim that one successful outing proves overall fun or whole-world survival balance. If it reveals a terrain-caused access/resource problem, fix that within this scope. Record independent combat/survival design issues for a later decision rather than expanding this brief into a balance overhaul.

## 9. Verify proportionately

Start with the supplied review baseline, then capture a same-machine pre-edit sample where timings or scene fingerprints are compared. Use ordinary seeds `0`, `20261023`, `29417` for unchanged geography/plan comparisons. Keep rare controlled fixtures clearly separate from ordinary distribution evidence.

| Check | Required evidence |
|---|---|
| Existing world preserved | Complete G9 plan identity and coarse geography agree before/after for the three ordinary seeds, or an explicitly justified contract extension has an exact preserved G9 projection as described above. No scenes exist at planning completion. |
| Visible terrain improvement | Production before/after scenes covering all eight wilderness biomes across a bounded sample; multi-chunk views for forest/open, wet/dry, ash-edge and rocky terrain. Inspect them for coherent masses, readable routes and boundary artifacts. Use controlled patches only where ordinary placement cannot supply a particular edge case. |
| Correct field continuity | Same-coordinate natural-field/base-terrain crop agreement across horizontal/vertical seams and a four-chunk corner, before later scene-owned passes; independent creation in both orders and fresh processes with different hash seeds. |
| Gameplay semantics | Final road/bridge/owner masks and required access survive dressing/population. Actual harvesting/drinking or equivalent existing resource interaction works; native population remains present. |
| Compatibility and failure | Genuine G9 visited/pending witness, inherited historical fixtures, installed-policy removal/change, missing-required/malformed/forged saved-policy negatives and one meaningful late-failure rollback/recovery. |
| Ordinary play | The short live excursion and explored-checkpoint restore described above, with normal-FOV views and disclosed controls. |
| Costs | Paired scene-generation and boundary timings, policy/plan bytes and lazy-generation counts. Distinguish base-field cost from complete scene cost. Investigate material added stalls. The new terrain sampler/materializer must have no world-sized allocation, recursive neighbor materialization or work growing with previously explored scene count; existing checkpoint scaling is outside this task. |
| Owner workflow | Draft preview/installed policy consistency, one demonstrated safe install/recovery route, relevant output-collision protection, and a current derived catalog if affected. |

Keep tests behavioral and targeted. Preserve the existing G9 network/lifecycle regressions and run the expanded focused suite plus the established unfiltered production gate once against final frozen inputs. Record the existing `E04 / UI-TEXT-HEIGHT` deferral honestly. Add a bounded G10 terrain/expedition verification entry point with finite timeouts.

Use a release sequence appropriate to these changes. Do not copy G9's ten-gate sequence wholesale: the wiki and unchanged browser editor are outside this brief. Historical G9 release tools and evidence retain their original meaning. Run an additional gate only when the changed code or an observed failure makes it relevant. If final runtime/test inputs change after verification, rerun the affected checks and the required final gates against the new frozen input set.

Do not manufacture an aesthetic pass from a checksum or a connectivity statistic. The completion report must explain what changed in the production images and how the live excursion used it. Distribution counts, patch sizes and resource/access measures should support that judgment, not become a new simulation target.

## 10. Execution and delivery

Work in the owner's existing production checkout on `main`. Read `AGENTS.md`, apply the explicit wiki-policy override above, record HEAD/status/remotes and preserve unrelated owner work. If main has advanced beyond the reviewed revision, inspect and record the difference; do not reset it. No task branch, worktree, second development checkout or PR.

Use meaningful scoped checkpoints for the starting state, terrain contract/implementation and final verified delivery. Reuse the established dependency environment. Verify headlessly or through app-local events with guarded disposable saves; no desktop takeover, personal campaign access or routine owner testing assignment.

When the owner supplies this brief for implementation, delivery includes scoped commits and verified publication to the existing remote main, with immutable uniquely named checkpoints and remote readback, subject to any more specific instruction in that execution session. Do not move old tags, amend unrelated work or force-push.

Deliver the implementation, a concise `WORLDGEN_G10.md`, the short tuning/preview guide and one source-bound evidence package. Retain exact commands, results, relevant logs, the genuine compatibility fixture and before/after production images. Avoid redundant checkouts and disposable campaigns in the package. Use Markdown and machine-readable receipts; no PDF. The review can be repeated from the source and this evidence without asking the owner to replay the excursion manually.

### Completion criteria

1. The new wilderness profiles produce visibly coherent, distinct terrain using existing assets; the Ash Wastes mismatch is corrected.
2. World-coordinate fields and bounded transitions work across seams/corners without eagerly materializing neighbors.
3. G9 geography, routes, towns, sites, ownership and required access remain intact.
4. Terrain/resource/native behavior is usable under actual handlers, with one successful short ordinary expedition and normal-FOV evidence.
5. The saved terrain contract owns pending generation; genuine historical visited/pending scenes remain supported and atomic failure/recovery is demonstrated.
6. The small preview/tuning route is safe and documented; relevant focused and production verification passes against the delivered inputs.
7. Source publication and evidence agree. The new owner rule on separately commissioned wiki work is recorded, and no wiki maintenance is performed.

Stop at these outcomes. Further road optimization, traffic simulation, new crossings, larger worlds, climate/erosion/ecology models, new POIs or ruins, capital development, a survival rebalance, checkpoint redesign and a continuous viewport are separate decisions. The next review should choose among them from the resulting play experience and measured costs; G11 is not preauthorized.
