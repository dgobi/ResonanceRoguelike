# World and state

Purpose: know which place and object a change belongs to, and what survives leaving or reloading. Source context is the Arc A reviewed working copy; persistence assertions below come from [arc-a2-results.json](../../../evidence/arc-a2-results.json). They are real-method diagnostics, not a game-window traversal.

## Four coordinate spaces

| Space / units | Owner and example |
|---|---|
| World chunk coordinates | `Engine.world_x/world_y`, `WorldMap` metadata. The opening is `(0,64)` in a 128×128 world. |
| Local tile coordinates | `Actor.x/y` and `LocalMap.tiles[x,y]`, nominally 80×43. NumPy arrays are indexed x then y; never silently swap them. Opening `(15,20)`. |
| Authored layout coordinates | JSON row/column positions relative to its own origin. `starting_lab` is 60×16 centered at `(10,13)`; player_start `(5,7)` becomes local `(15,20)`. Entrance layouts can rotate. |
| Pixel coordinates | Renderer/camera/viewport units. Generally `(local-camera)*effective_tile_size + viewport_origin`; see `rendering/coords.py` and the actual renderer. Font pixels, map tiles and overmap cells are not interchangeable. |

A scene needs `(world_x, world_y, submap_id-or-None)`. Both the surface and `sub_0_64_0` share world `(0,64)` and can both have a local `(3,3)`. A location without scene identity is ambiguous.

## Stores in one active scene

`Engine.local_map` and `Engine.entities` select the active scene. `world/local_map.py::LocalMap` holds:

| Layer | Stored form and consumer |
|---|---|
| Terrain | Structured tile array: terrain ID, walkability, transparency, visible/explored. `set_tile`, generation, movement, FOV and renderer consume it. |
| Decor | `(x,y) -> decor_id`. `generation/decor_utils.py` places/clears it; it can block movement/sight, carry harvest/interaction/resonance behavior, and is pickled. It is not merely cosmetic. |
| Floor objects | `(x,y) -> list[Item]`, via `generation/floor_object_utils.py`. Dropped loot and current layout items live here, separate from actors. |
| Containers | `container_state[(x,y)]`, with closed/open/looted state and serialized item ID/text ID entries; decor supplies the visible furniture. Access reconstructs items; arbitrary mutable instance state is not preserved by this tiny container record. |
| Actors | `Engine.entities` includes player and creatures; components hold HP, AI, perception, inventory etc. Some legacy item-as-entity paths remain. |
| Processing / authored information | `processing_layer`, `corpse_data`, `corpse_decay`, `stele_text_ids`, inscriptions, examined sets and vine networks belong to LocalMap. `processing_queue` is a separate retained list, not an actual alias to the live layer. |

Definitions are reusable descriptions (`item_id`, `_creature_id`, decor/terrain IDs). Instances carry position, fuel, liquid, coatings, damage and ownership. Two items with the same definition ID are still two instances. Current equipment JSON stores a definition ID and relinks the first matching inventory object; unique instance identity is not yet a save contract.

## Generation, cache and reload lifecycle

World generation creates chunk descriptors, links and submap metadata. `generation/region_gen.py::generate_region` materializes surface maps; `generation/local_gen.py::generate_submap` materializes authored or BSP underground scenes. Unvisited/generated/cached are distinct concepts: metadata alone is not a rendered local map. On travel, cached scene content should take precedence over regeneration.

`SaveManager.cache` owns `ChunkCache.hot[(wx,wy)]` for surface maps and `submap_hot[submap_id]` for underground maps. `store`/`store_submap` immediately write disk caches. The maps are retained object references in hot memory; actor lists are serialized dictionaries. `SaveManager.hot` does not exist: the offscreen processing branch currently asks that wrong owner and does no intended background work.

Full save writes world JSON, player JSON, meta JSON and the current map. It unconditionally stores the current map under the **surface key**, even underground. Load also picks the surface key after restoring a submap ID. Ascent then retrieves that damaged surface entry. This is why a save can look successful underground and still lose the surface.

The bounded fixture gives surface `(3,3)` a grass marker and a hollow revenant; underground `(3,3)` gets flagstone and a grave thing. After full save, a fresh-process load and ascent report surface identity `None` but **flagstone and grave thing**. In-session load also fails. The check compares both identity and contents, not just screenshots or filenames.

## Persist, reset, recompute: first ledger

| State | Actual present policy and limit |
|---|---|
| World metadata, turn, position, submap ID, stair return | Explicit JSON fields. Their presence does not guarantee correct scene routing. |
| Tile grid and LocalMap layers | Pickled with CachedChunk, including explored/decor/floor/container/processing state. Full save does not explicitly flush every dirty hot entry. |
| HP, hunger/thirst, corruption component, language, perks, level | Explicit player JSON. Component recreation can lose configuration and hook registration. Engine resonance/corruption are separately saved; this split is unresolved. |
| Inventory | Factory reconstruction plus a whitelist: ID/name/on_use/fuel/liquid/text/coatings. Empty Inventory is false and serializes as null, so load skips replacement. Nutrition is recreated from current definitions, not saved. |
| Equipment | Slot -> item definition ID, matched to restored inventory. Empty slots do not clear old references. Duplicate same-ID instances remain ambiguous. |
| Light | Light fields restored separately. The offhand torch is not relinked to `_item_ref`; fuel ticking depends on that reference. |
| Creatures | Selected HP/AI/perception fields. Serializer uses `entity_id` or mutable tile, not `_creature_id`; hibernating stone lurker becomes ID `rock` and fails reconstruction. |
| FOV and lighting | Recomputed by `_update_fov` after bootstrap/travel/load/turns; cached explored information is distinct from currently visible. |
| Effects / timers / RNG | Some sprint/moveset fields persist, many sickness/chill/true-sight duration and speed timers do not. Fresh construction resets omissions; in-session load can retain stale ones. Simulation RNG progress is not saved. |
| UI, particles, callouts | Generally fresh process state, not a campaign persistence promise. Presentation does not own combat/state truth. |

Example invariant: empty saved inventory/equipment should replace six bootstrap items and the bootstrap offhand torch. The actual fresh-process test leaves all six starter items. A one-jerky inventory with all empty saved slots replaces the inventory but retains an offhand torch **outside** it. These are separate failures.

Check with `tools/persistence_diagnostics.py --prefix my-state-check` in a new session prefix. Each result separates harness completion from expected property and observed value. Treat its exits and JSON as explained in OBSERVATIONS.md. No save migration, arbitrary old-save loading, crash recovery or complete field ledger is certified here.
