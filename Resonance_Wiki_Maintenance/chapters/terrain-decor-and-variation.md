# Terrain, decorative overlays, and variation

Choose a terrain definition when a cell's ground or structural behavior changes. Choose a decorative overlay when an object should sit above the existing ground. A decorative can be interactive, block movement, emit resonance, or represent a harvestable plant; the name does not mean it is purely visual.

## The three layers you author most often

| Layer | Runtime storage | Typical purpose | Important constraint |
|---|---|---|---|
| Terrain | `LocalMap.tiles[x, y]` | Floors, walls, water, roads | One terrain ID per cell; changing it replaces the old ground. |
| Decorative | `LocalMap.decor[(x, y)]` | Candles, barrels, plants, blood, campfires | One decorative ID per cell; a second placement replaces the first. |
| Floor objects | `LocalMap.floor_objects[(x, y)]` | Pick-up items and completed processing outputs | A list of item instances; use the floor-object/transfer APIs. |

Rendering draws terrain, then decorative overlays, then processing/floor objects, then entities. Decorative sprites use transparency so terrain can remain visible beneath them. `LocalMap` and its decorative dictionary are carried by the scene cache/checkpoint system. The old guide's claim that decorative overlays disappear on every chunk unload is obsolete.

Sources: [LocalMap](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/world/local_map.py), [renderer layer composition](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/rendering/renderer.py), [scene cache and checkpoint serialization](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/save_manager.py).

## Add a simple floor terrain

This recipe introduces a new terrain ID while initially reusing known-good art. The supplied values are an authoring example, not an already shipped floor.

1. Add a `cottage_floor` key to the top-level object in `roguelike/data/terrain.json`:

```json
{
  "tile": "cottage_floor",
  "display_name": "Worn Cottage Floor",
  "walkable": true,
  "transparent": true,
  "description": "Worn stone underfoot, swept clean at the threshold.",
  "move_cost": 1.0
}
```

2. Add `cottage_floor` under `roguelike/data/tiles.json` → `tiles`, with a full ASCII definition:

```json
{
  "ascii": ".",
  "color_fg": [199, 176, 139],
  "color_bg": [6, 6, 8],
  "color_fg_dark": [35, 30, 25],
  "color_bg_dark": [4, 5, 9]
}
```

3. Add `cottage_floor` under `roguelike/data/sprites/sprite_map.json` → `tiles`:

```json
{"sheet": "terrain", "col": 20, "row": 1}
```

4. In a structure's terrain legend, map a chosen character to `cottage_floor`, then paint that character in its terrain rows. Follow the current structure-authoring chapter for the full layout contract and validation commands.
5. Generate a new preview or disposable scene. Inspect the floor, examine its display name, walk across it, and check sight through it. Editing the registries does not retroactively restamp saved scene geometry.

**Naming limit:** the terrain array stores strings with NumPy dtype `U32`. Keep terrain IDs at most 32 characters. Use the same key in all three registries; `tile` is not a reliable universal redirect for arbitrary terrain rendering routes.

## Terrain fields with real consumers

| Field | Meaning / units | Editing consequence |
|---|---|---|
| `walkable` | Boolean | Used when terrain is stamped into the map. Existing map masks are not rebuilt merely by editing the definition. |
| `transparent` | Boolean | Controls terrain sight transmission. Use this for a genuine sight-blocking wall. |
| `display_name`, `description` | Text | Used by examination and interaction messages where supported. |
| `move_cost` | Relative movement cost, normal floor `1.0` | Player movement accumulates debt above 1; AI uses it as a path cost. It is not a universal action-duration multiplier. |
| `harvestable`, `harvest_item`, `depleted_tile` | Flag and referenced IDs | Harvesting produces the item and may replace the terrain; both result IDs must exist. |
| `gatherable`, `gather_item`, `gather_chance`, `gather_depletes` | Flag, item ID, probability, flag | Gathering has a success roll; `depleted_tile` supplies the replacement when depletion is enabled. |
| `drinkable`, `drink_hydration` | Flag and authored survival points | Drinking normalizes hydration using the configured thirst maximum. Do not treat this as litres. |
| `secondary_effect` | Implemented effect name | Dispatched by `_apply_terrain_effect`; an arbitrary new string does not implement new behavior. |
| `interactable` | Handler name | Routed to an existing `_interactable_<name>` method. |
| `light_emit` | Radius in tiles in the current light/FOV consumers | Consumers cast to integer; it is not a normalized 0–1 brightness slider. |
| `light_mode` | `"steady"` or `"pulse"` | Selects radius behavior in terrain light-map accumulation. |
| `light_color` | RGB array, 0–255 channels | Used by terrain light-map contribution. Default full-colour map drawing has additional limitations described below. |
| `light_pulse_min`, `light_pulse_max` | Radius endpoints in tiles | Used in pulse mode. |
| `light_pulse_rate` | Cycles per second | The pulse calculation uses elapsed real time. |
| `visual_fx` | One supported string | Different emitter and brightness routes read this from different data owners; see below. |

Read the actual existing definition and consumer together before copying specialized fields. `terrain.json` contains retained entries that now have an active decorative counterpart, including campfires and some plants; the presence of an entry does not prove that generation still places it as terrain.

Sources: [terrain definitions](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/data/terrain.json), [Engine harvesting, interaction, movement, FOV, and light consumers](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/engine.py), [AI terrain path costs](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/components/ai.py).

## Add a decorative overlay

`roguelike/data/decoratives.json` is a JSON **array**, indexed by each entry's `id` when loaded. Append a new object, for example:

```json
{
  "id": "decor_wax_stump",
  "ascii": "*",
  "blocks_movement": false,
  "blocks_sight": false,
  "display_name": "Wax Stump",
  "description": "A shallow mound of old wax around a guttering wick.",
  "visual_fx": "flame_low"
}
```

Register a sprite key with the same ID. Reusing the shipped candle mapping gives a working initial visual:

```json
"decor_wax_stump": {"sheet": "terrain", "col": 23, "row": 6}
```

Also add a matching entry under `tiles.json.tiles` if you want the renderer's available ASCII fallback. **The world decorative renderer does not obtain that fallback from `decoratives.json.ascii`; it checks `TileRegistry`.** Keeping the `ascii` field in the decorative definition is useful descriptive data, but it is insufficient by itself for this fallback.

Placement routes:

- Add it to a structure's `decor_layer` using the current structure-authoring workflow.
- For a one-off disposable-session preview, open the debug console with backtick and enter `place_decor decor_wax_stump`. This places it at the player's current position; `place_decor clear` removes the overlay there.
- In code, call `generation.decor_utils.place_decor(local_map, x, y, decor_id)` and `clear_decor(local_map, x, y)`.

The placement helper checks bounds; it does not validate the ID, create container inventory, or choose a free coordinate. The debug command validates the ID but still places at the player's position. Avoid using an arbitrary blocking decorative as a player-position preview.

### Functional decorative fields

| Field | Supported use and caution |
|---|---|
| `blocks_movement` | Read by Engine movement/placement checks. Check the behavior of other actors separately; this is not a rewrite of the terrain walkability mask. |
| `blocks_sight` | Present in definitions and structural semantic fingerprints, but no runtime FOV consumer was found. Do not rely on it to create a visual barrier. |
| `interactable` | Named Engine handler; decor is checked before terrain at that coordinate. |
| `container` | Used with container-aware placement. A barrel graphic alone is not a container inventory; use the supported container special/placement route. |
| `harvestable`, `harvest_item`, `depleted_id` | Decorative harvest route. Notice `depleted_id`, whereas terrain uses `depleted_tile`. |
| `resonance_emit` | Read by the resonance system; use the resonance chapter for accumulation and timing. |
| `warmth_radius` | Used by warmth and processing eligibility; campfire behavior includes ID-specific routes. |
| `light_emit` | Can extend FOV from a visible decorative source. Unlike terrain, there is no matching general decorative coloured-light accumulation loop in `_update_light_map`. |
| `visual_fx` | Flame/smoke particle selection and limited brightness behavior. |

Sources: [decorative definitions](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/data/decoratives.json), [placement helper](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/decor_utils.py), [debug placement](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/debug.py).

## Variation: appearance versus generated terrain

There are two different mechanisms in `roguelike/rendering/decor.py`.

**`DECOR_TABLE` changes the displayed sprite.** A terrain name maps to weighted sprite keys. For example, `grass` can select `grass_1`, `grass_2`, stones, or `None`. A `None` result skips drawing that terrain sprite; it does not remove the terrain or make the cell impassable. Weights are relative, not necessarily percentages: the current grass weights total 92, so its weight-60 empty appearance is 60/92, not 60%. Selection is deterministic from local coordinates; it does not use the world seed in this function. This visual variation does not change the stored terrain ID or collision.

**`FUNCTIONAL_VARIANTS` resolves a generated terrain choice.** A supported `varied_` name is resolved when `LocalMap.set_tile()` runs, using its generation context. This affects the stored terrain/decor result. It is code-maintained rather than a general JSON rule system. The selected variant does not automatically replace the caller-supplied walkability/transparency arguments with a newly looked-up definition.

Plant variants have additional handling: IDs in `PLANT_DECOR_IDS` can become decorative overlays over grass when selected from an allowed ground token and there is no existing decorative. Directly passing a plant ID to `set_tile()` is not equivalent to placing a plant overlay, because the original token is checked against `_PLANT_VALID_TERRAIN`. Use the established generation route or `place_decor()` when deliberately placing one.

Source: [visual and functional variation](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/rendering/decor.py), [terrain setting](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/world/local_map.py).

## Connected tiles and autotiling

The renderer selects suffixes from a four-neighbor mask: north = 1, east = 2, south = 4, west = 8. A selected wall base can resolve to a name such as `wall_10` for east + west. The trigger is currently name-based: sprite names containing `wall`, `water`, `rock`, or `grey` enter the wall-style route; names starting with `road` enter the road route. Road variants are named `road_<mask>`.

Register the needed suffixes in `sprite_map.json` and keep a valid base sprite as fallback. Adding an arbitrary `autotile` JSON property will do nothing. Inspect the connection predicates before extending a naming family, because related terrain types and map edges affect connectivity. Water treats out-of-bounds differently from the wall-style default; roads treat it as connecting.

Source: [autotile selection and connection predicates](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/rendering/renderer.py).

## Particles, brightness effects, and light are separate

| Desired result | Current authoring route |
|---|---|
| Flame/smoke particles | A single `visual_fx` string in terrain or decorative data: `embers`, `flame_low`, `flame_med`, `flame_high`, or `smoke_incense`. |
| Terrain brightness oscillation | `visual_fx` in the tile-registry entry: `pulse_glow`, `pulse_dim`, or `flicker`; decorative fallback can influence the terrain pass. |
| Sparkles on a new arbitrary ID | Requires code support: the emitter currently checks a four-ID colour table, not every definition with `visual_fx: "sparkle"`. |
| Actual sight radius | FOV/light-source consumers, including `light_emit`; flame particles alone do not provide sight. |
| Colored terrain light contribution | Terrain `light_emit` and `light_color`, interpreted by `_update_light_map`; default full-colour rendering does not apply that map like tint mode does. |

Do not author `visual_fx` as an array. The renderer compares it with strings, and the flame dispatch tests it as a dictionary key; a list is unsupported and can raise an unhashable-type error. The historical guide's list example is incorrect for this revision. `sparkle` is not handled as a brightness multiplier by `_get_fx_brightness`.

The generic decorative draw pass does not apply each decorative's `color_fg` from `tiles.json`, and brightness effects on the terrain pass should not be assumed to animate the overlay itself. If a new object needs a new visual behavior, use the file map in the architecture chapter to find the actual rendering/emitter consumer.

## Verify a terrain or decorative change

Check four independent results: the definition loads; the intended generation/placement route selects it; the world renders it; the gameplay interaction behaves as intended. For a functional overlay, also leave the scene, return, save, and reload in a disposable session. Preserve expected container contents and harvested/depleted state. Use the existing headless acceptance tools appropriate to that route; a JSON formatting check alone cannot establish these behaviors.

This chapter corrects the legacy `DECORATIVES.md`, `DECOR AND RANDOM TILES.md`, and terrain sections of `SPRITESHEET_GUIDE.md` against the audited code. It does not change the underlying limitations described above.
