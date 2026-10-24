# How the current world is built

Fresh worlds at this wiki's revision use **G9**, generation revision `wg9`, shared world-plan format `7`, and the existing `shared-v1` dispatch. The world is finite: **128 × 128 storage chunks**, each with an **80 × 43 local map**. The plan is created before local scenes. Exploring a location realizes its slice of that plan, then preserves what actually happened there.

This distinction is useful when making content: a **layout** describes an authored place, a **placement profile** says how it can fit, a **selection profile** makes it eligible, a **world plan** chooses an asset and its location, and a **scene** contains the actual terrain, actors and objects the player can change.

## Choose the right editing surface

All paths in this table are relative to the repository root.

| I want to change… | Edit or inspect… | What else is needed? |
|---|---|---|
| A house's floor plan, doors or contents | `roguelike/data/buildings/<existing-category>/<id>.json` | Validate its complete placement contract and every permitted orientation. |
| Which houses, shops or stores appear in new towns | `roguelike/data/generation/settlement_profiles.json` | Install the asset and explicitly register its ID in the required form and role. |
| Relative frequency and repetition in towns | Role `weight`, `max_per_settlement`, `repeat_multiplier`, `schedule` in that file | A weight is relative among eligible, fitting choices; it is not a percentage or guaranteed count. |
| Settlement count, road width, setbacks or plot spacing | `roguelike/data/generation/g3_config.json` | Keep current `version: 4`, `settlement_layout_version: 1` and `country_network_version: 1`; the old filename is deliberate. |
| Grid streets, common and frontage | `roguelike/data/generation/settlement_layouts.json` | See [Settlement layouts](#settlement-layouts). |
| The single featured landmark's alternatives | `profiles.landmark.roles.landmark` in `settlement_profiles.json` | Use a layout with an explicit connected `landmark` context. |
| Additional independent rural sites | `roguelike/data/generation/poi_profiles.json` | This is a separate pool from the featured landmark. |
| Entrance appearance | `roguelike/data/entrances/<id>.json` | Match an existing entrance type and validate its real stairs and access. |
| The starting laboratory | `roguelike/data/layouts/starting_lab.json` | Use the authored-submap route, including a real arrival and real stair terrain. |
| A different authored underground level | A layout under `roguelike/data/layouts/` | A `SubMap.layout_id` must point to it; adding a JSON file alone does not schedule a level. |
| Wilderness resource or decor density | Existing biome/terrain/decor data and their consuming generator | Check the active final-geometry dressing pass; a new field does not create a pass. |
| Legacy WFC ground fill | `roguelike/data/wfc/` and the relevant call in `town_gen.py` | The fresh G9 planned scene path does not use the legacy town WFC fill. |

## The layers you will encounter

1. **Geography and anchors.** World generation creates coarse biome and river information and preserves the start, VUKH/locus and capital anchors.
2. **Shared plan.** Country roads, a required crossing, settlement footprints, plots, the featured landmark and extra rural sites are chosen as durable records. Required constraints must succeed before publication.
3. **Local terrain.** The relevant biome supplies base terrain. The shared plan paints exact water, road and bridge bands across local-map boundaries.
4. **Authored structures.** Selected assets are transformed, stamped, given their supported contents and protected approach. Items and containers use the production factories.
5. **Protected entrances and dressing.** Stairs, resources, waystones, prayers and native population are placed with the existing exclusions and policies.
6. **Final checks and ownership.** Complete approaches, required doorway spans, usable contents, roads and stairs are checked before the scene becomes live. Once created, that scene owns its actual state.

A road's identity and assigned join matter. A visually nearby road is not interchangeable with the one saved for a building. Whole road bands and owned crossings are shared across boundaries; local chunks do not independently invent the endpoints of these planned roads.

## What a normal G9 world contains

The default settlement count is an inclusive draw from two through four. Forms alternate between a **grid town** spanning two by two chunks and a **roadside settlement** spanning two chunks along a country road. Each requires residential and commercial content. The grid requires the existing spent-bell civic anchor. Support plots are optional, and unsuccessful optional plots can remain recorded vacant gardens.

There is **one required featured landmark**, chosen from its own alternatives. There are also **two through four desired additional rural sites** under the default POI policy. Counts refer to parents: each single site has one building; each compound has two required children and at most one optional child, contained with shared access in one storage chunk. Default v2 selection requires at least one single and one compound. A permissible shortfall from the desired count must still meet the configured minimum and record its reason.

Plot roles describe selection intent. They do not add merchant behavior, trading interfaces, quests or new AI. Native town member roles still use `native-town-v1`: the standard grid has a civic member and residential members; roadside has market and residential members. A commercial building in a residential member does not silently change the member's population policy.

## Identity and versions

| Label | What it identifies |
|---|---|
| `wg9` | Current generation origin/revision; historical visited scenes retain their real earlier revision. |
| Plan format `7` | Complete G8 layout/common/rural baseline plus resolved optional country connections. |
| Planning settings `4` | Current network policy; explicit settings `3` retain the historical G8 contract. |
| `shared-v1` | The shared-plan dispatch mode. |
| `structure-v1` | The consumed structural dependency projection. |
| `native-town-v1` | Town native-context semantics. |
| Campaign save version | The checkpoint representation; it is a different contract from world generation. |

Avoid treating any one of these as “the game version.” A current scene may realize a historical plan through an explicit adapter while its neighboring visited scene retains older provenance.

## Boundaries of the current implementation

The current implementation supports individual buildings and their complete approaches **inside one 80 × 43 storage chunk**. It does not yet provide structures spanning chunks, capital redevelopment, a continuous scrolling world viewport, infinite geography or long-campaign save/cache compaction. Ordinary rural population remains the existing policy. Creating a new JSON key for any of these does not activate the feature.

The installed catalog includes settlement assets, the spent bell, single-site alternatives and compound child candidates. The frozen editor corpus has 65 documents, including legacy buildings, plazas, entrances and the laboratory. Catalog presence and modern planned eligibility are separate facts.

## Sources and implementation anchors

- [World planner and current settings validation](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/world_plan.py)
- [Complete planned scene creation](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/planned_scene.py)
- [G6 delivered scope and boundaries](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/docs/owner/WORLDGEN_G6.md)
- [Current geometry settings](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/data/generation/g3_config.json)

## Optional country connections

G9 first completes and validates the whole G8 backbone, settlements and rural contents. It then considers at most two optional country connections before any local scene exists. Original roads, crossings, destinations, saved town arrivals, frontage and rural attachments remain intact. The installed `country_network.json` is a separate policy; changing it affects new worlds.

Construction counts new unique **unit centerline edges**, with one shared cap of 25% of the complete baseline country union. Reused edges cost no new construction. Travel counts shortest **four-neighbour steps on full-width road, deck and access cells** between fixed primary destinations: start, every settlement, capital gateway and landmark. A macro step spans 80 horizontal or 43 vertical tiles. Search score, physical distance and actual movement-input counts are different units.

Default admission requires at least 500 saved steps and 25% improvement for a named primary pair, recomputed after each accepted connection. Candidate search is finite and deterministic; it is not a global optimum. Ordinary seed 20261023 improves settlement-1 to capital-gateway from 23,625 to 8,063 physical steps with 5,265 new centerline edges out of 24,631 (21.37%). Ordinary seeds 0 and 29417 add none. These three samples are not a frequency forecast.

New road bands cannot enter town, building, compound, capital or submap owner chunks, including new endpoint entrances. Full widths and corners are checked. Existing bridge decks can be reused under explicit crossing ownership; **no new physical river bridge** is constructed. Every touched local road slice must remain connected. Original paths still provide genuine alternative country corridors.

See [Towns, roads and variety](#settlement-tuning) for preview, tuning, disable and install/revert workflows. Organic roads, density, larger worlds, streaming and checkpoint compaction remain outside this feature.
