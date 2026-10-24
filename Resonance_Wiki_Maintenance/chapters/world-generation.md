# How the current world is built

Fresh worlds at this wiki's revision use **G7**, generation revision `wg7`, shared world-plan format `5`, and the existing `shared-v1` dispatch. The world is finite: **128 × 128 storage chunks**, each with an **80 × 43 local map**. The plan is created before local scenes. Exploring a location realizes its slice of that plan, then preserves what actually happened there.

This distinction is useful when making content: a **layout** describes an authored place, a **placement profile** says how it can fit, a **selection profile** makes it eligible, a **world plan** chooses an asset and its location, and a **scene** contains the actual terrain, actors and objects the player can change.

## Choose the right editing surface

All paths in this table are relative to the repository root.

| I want to change… | Edit or inspect… | What else is needed? |
|---|---|---|
| A house's floor plan, doors or contents | `roguelike/data/buildings/<existing-category>/<id>.json` | Validate its complete placement contract and every permitted orientation. |
| Which houses, shops or stores appear in new towns | `roguelike/data/generation/settlement_profiles.json` | Install the asset and explicitly register its ID in the required form and role. |
| Relative frequency and repetition in towns | Role `weight`, `max_per_settlement`, `repeat_multiplier`, `schedule` in that file | A weight is relative among eligible, fitting choices; it is not a percentage or guaranteed count. |
| Settlement count, road width, setbacks or plot spacing | `roguelike/data/generation/g3_config.json` | Keep current `version: 2`; the old filename is deliberate. |
| The single featured landmark's alternatives | `profiles.landmark.roles.landmark` in `settlement_profiles.json` | Use a layout with an explicit connected `landmark` context. |
| Additional independent rural sites | `roguelike/data/generation/poi_profiles.json` | This is a separate pool from the featured landmark. |
| Entrance appearance | `roguelike/data/entrances/<id>.json` | Match an existing entrance type and validate its real stairs and access. |
| The starting laboratory | `roguelike/data/layouts/starting_lab.json` | Use the authored-submap route, including a real arrival and real stair terrain. |
| A different authored underground level | A layout under `roguelike/data/layouts/` | A `SubMap.layout_id` must point to it; adding a JSON file alone does not schedule a level. |
| Wilderness resource or decor density | Existing biome/terrain/decor data and their consuming generator | Check the active final-geometry dressing pass; a new field does not create a pass. |
| Legacy WFC ground fill | `roguelike/data/wfc/` and the relevant call in `town_gen.py` | The fresh G7 planned scene path does not use the legacy town WFC fill. |

## The layers you will encounter

1. **Geography and anchors.** World generation creates coarse biome and river information and preserves the start, VUKH/locus and capital anchors.
2. **Shared plan.** Country roads, a required crossing, settlement footprints, plots, the featured landmark and extra rural sites are chosen as durable records. Required constraints must succeed before publication.
3. **Local terrain.** The relevant biome supplies base terrain. The shared plan paints exact water, road and bridge bands across local-map boundaries.
4. **Authored structures.** Selected assets are transformed, stamped, given their supported contents and protected approach. Items and containers use the production factories.
5. **Protected entrances and dressing.** Stairs, resources, waystones, prayers and native population are placed with the existing exclusions and policies.
6. **Final checks and ownership.** Complete approaches, required doorway spans, usable contents, roads and stairs are checked before the scene becomes live. Once created, that scene owns its actual state.

A road's identity and assigned join matter. A visually nearby road is not interchangeable with the one saved for a building. Whole road bands and owned crossings are shared across boundaries; local chunks do not independently invent the endpoints of these planned roads.

## What a normal G7 world contains

The default settlement count is an inclusive draw from two through four. Forms alternate between a **grid town** spanning two by two chunks and a **roadside settlement** spanning two chunks along a country road. Each requires residential and commercial content. The grid requires the existing spent-bell civic anchor. Support plots are optional, and unsuccessful optional plots can remain recorded vacant gardens.

There is **one required featured landmark**, chosen from its own alternatives. There are also **two through four desired additional rural sites** under the default POI policy. Counts refer to parents: each single site has one building; each compound has two required children and at most one optional child, contained with shared access in one storage chunk. Default v2 selection requires at least one single and one compound. A permissible shortfall from the desired count must still meet the configured minimum and record its reason.

Plot roles describe selection intent. They do not add merchant behavior, trading interfaces, quests or new AI. Native town member roles still use `native-town-v1`: the standard grid has a civic member and residential members; roadside has market and residential members. A commercial building in a residential member does not silently change the member's population policy.

## Identity and versions

| Label | What it identifies |
|---|---|
| `wg7` | Current generation origin/revision; historical visited scenes retain their real earlier revision. |
| Plan format `5` | Resolved mixed rural parents, compound children and paths. |
| `shared-v1` | The shared-plan dispatch mode. |
| `structure-v1` | The consumed structural dependency projection. |
| `native-town-v1` | Town native-context semantics. |
| Campaign save version | The checkpoint representation; it is a different contract from world generation. |

Avoid treating any one of these as “the game version.” A current scene may realize a historical plan through an explicit adapter while its neighboring visited scene retains older provenance.

## Boundaries of the current implementation

The current implementation supports individual buildings and their complete approaches **inside one 80 × 43 storage chunk**. It does not yet provide structures spanning chunks, capital redevelopment, a continuous scrolling world viewport, infinite geography or long-campaign save/cache compaction. Ordinary rural population remains the existing policy. Creating a new JSON key for any of these does not activate the feature.

The connected library has sixteen explicitly profiled live buildings: twelve settlement assets including the civic bell, and four rural/landmark alternatives. The larger 64-document structure catalog also contains legacy buildings, plazas, entrances and the laboratory. Catalog presence and modern planned eligibility are separate facts.

## Sources and implementation anchors

- [World planner and current settings validation](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/world_plan.py)
- [Complete planned scene creation](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/planned_scene.py)
- [G6 delivered scope and boundaries](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/docs/owner/WORLDGEN_G6.md)
- [Current geometry settings](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/data/generation/g3_config.json)
