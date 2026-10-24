# Project glossary

Use these definitions when a guide distinguishes something that looks similar on screen but has a different owner in the game. Dimensions and version labels below describe this wiki's pinned G8 revision.

## Places and coordinates

| Term | Meaning in Resonance | Continue with |
|---|---|---|
| **Chunk** | One coarse world location and its metadata. Its surface storage map is **80 × 43 local tiles**. The default finite world has **128 × 128 chunks**. | [World generation](#world-generation) |
| **Local tile** | A position inside one map: x increases east/right, y increases south/down. Coordinates start at zero. | [Geometry reference](#structure-reference) |
| **Scene** | One actual playable surface map or underground map, including its terrain, contents and actors. Its full address distinguishes `(world_x, world_y, submap_id-or-None)`. | [Saves and state](#saves-and-state) |
| **Submap** | A separately identified underground place associated with a world location. It can share world coordinates with the surface while owning different terrain and contents. | [Entrances and submaps](#entrances-submaps) |
| **World tile** | A surface position expressed across chunk boundaries: `x = chunk_x × 80 + local_x`, `y = chunk_y × 43 + local_y`. Road plans and rural-site spacing use this space. | [Rural sites](#rural-sites) |

## Content and layers

| Term | Meaning in Resonance | Continue with |
|---|---|---|
| **Definition** | The reusable JSON or code description identified by an ID: for example, a weapon type or house layout. Editing it changes the relevant creation or lookup rules. | [Items and equipment](#items-equipment) |
| **Instance** | One actual item, actor or container with its own state. Two items sharing a definition ID can have different fuel, charges or equipment ownership. Saved instance fields can override changed defaults. | [Items and equipment](#items-equipment) |
| **Terrain layer** | The base tile grid and its movement/sight properties. Painting a stair-shaped tile does not itself create an underground destination or link. | [Structure reference](#structure-reference) |
| **Decor layer** | Objects drawn over terrain, with their own behavior such as movement blocking. A painted shelf does not automatically become a populated container. | [Structure reference](#structure-reference) |
| **Floor objects / container state / actors** | Separate owners for loose items, actual container contents and live creatures. Their presence must be checked beyond a terrain-only image. | [Saves and state](#saves-and-state) |
| **Layout** | An authored rectangular terrain grid, legend and supported content records. It describes what is built; selection and fitting decide where it appears. | [First building](#first-building) |

## Choosing and fitting places

| Term | Meaning in Resonance | Continue with |
|---|---|---|
| **Category** | An existing structure folder such as residential, commercial or wilderness. It identifies a loader route; it does not automatically admit the asset to a modern selection policy. | [Structure reference](#structure-reference) |
| **Context** | An explicit geometric permission in `placement.contexts`: grid, roadside, civic or landmark. | [Structure reference](#structure-reference) |
| **Role** | Selection intent for a plot, such as residential, commercial or support. A commercial role does not create trading behavior. | [Settlement tuning](#settlement-tuning) |
| **Candidate** | An eligible asset, site or transform being considered. Eligibility is not guaranteed selection or successful fit. | [Generation diagnosis](#generation-troubleshooting) |
| **Placement** | A chosen asset with a saved transform, position, footprint, buffer, entrances, targets and assigned approach. | [Geometry reference](#structure-reference) |
| **Site** | A durable rural parent, either a single building or a bounded compound with independent children, attached to a country road. The featured landmark is a separate owner. | [Rural sites](#rural-sites) |
| **Frontage / join / approach** | The selected road-facing entrance, exact assigned road connection and protected access between them. An unrelated nearby road cannot replace that assignment. | [Rural sites](#rural-sites) |
| **Entrance** | An explicit full doorway span with an outward normal, role and required flag. Separate doors divided by a wall need separate records. | [Structure reference](#structure-reference) |
| **Target** | A typed position whose intended usability is checked, such as a readable or container. Declaring a target does not spawn that object. | [Structure reference](#structure-reference) |
| **Sidecar** | A separate access-expectation JSON file supplied with `--access`. It names an entry and targets without changing the layout. | [Layout painter](#layout-painter) |

## Plans, revisions and evidence

| Term | Meaning in Resonance | Continue with |
|---|---|---|
| **Shared plan** | World-owned initial decisions for roads, crossings, settlements and selected places. Local scenes realize its slices; loading does not reroll it. | [World generation](#world-generation) |
| **Plan version / generation revision** | Different labels: current plan format is `6`; current generation revision is `wg8`. Save format and dispatch mode are separate contracts again. | [World generation](#world-generation) |
| **Provenance** | Recorded origin and creation information, such as actual scene revision, plan identity and adapter. An older visited scene keeps its real history. | [Generation diagnosis](#generation-troubleshooting) |
| **Dependency fingerprint** | A digest of consumed definitions used to detect incompatible changes before creating a pending placement. It is distinct from a raw file hash and from a saved inventory. | [Generation diagnosis](#generation-troubleshooting) |

## State, randomness and time

| Term | Meaning in Resonance | Continue with |
|---|---|---|
| **Live / active** | The currently owned playable scene and its actors. Its actual state takes precedence over stale cached copies. | [Saves and state](#saves-and-state) |
| **Hot / cold** | Hot means retained in memory; cold means persisted but currently unloaded. Cold scenes are not continuously simulated. | [Saves and state](#saves-and-state) |
| **Checkpoint** | A published coherent full save of player, world and scene state. Travel-cache writes do not by themselves publish a new explicit checkpoint. | [Saves and state](#saves-and-state) |
| **Session / overlay** | The mutable working state associated with the current run, layered over its checkpoint. It can include exploration or mutations not yet in that checkpoint. | [Saves and state](#saves-and-state) |
| **Weight / chance** | Weight is relative among eligible choices. Chance is a probability at a particular roll, in that field's documented units. Neither directly promises a finished world's frequency. | [Settlement tuning](#settlement-tuning) |
| **Cap / budget** | A cap limits accepted counts. A budget limits attempted work; exhausting it can leave feasibility unresolved. The units depend on the specific control. | [Settlement tuning](#settlement-tuning) |
| **Turn / frame / hit** | Turns advance simulation through game actions; frames update display and are not turns. Hit-based charges age on qualifying contact, rather than elapsed turns or frames. Read each effect's timing rule. | [Combat and effects](#combat-balance) |

## Source anchors

Definitions consolidate the current [world planner](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/world_plan.py), [placement contract](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/placement.py), [current effect ownership](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/docs/owner/WORLD_AND_STATE.md) and [G6 lifecycle contract](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/docs/owner/WORLDGEN_G6.md).
