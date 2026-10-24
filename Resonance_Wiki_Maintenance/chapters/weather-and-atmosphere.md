# Weather and atmosphere tuning

Weather has three owners: `data/weather.json` supplies visual parameters and named mechanical values; `engine/weather.py` controls states, transitions, duration and messages; Engine, AI and resonance code decide when those mechanics apply. Changing an existing rain effect is a data edit. Adding a new state requires code wiring.

## Preview an existing weather effect

1. Start a disposable world, remain on the surface, and open the debug console with backtick.
2. Enter `set_weather light_rain`, `set_weather heavy_rain`, `set_weather fog`, `set_weather forgetting_fog`, `set_weather bone_snow`, `set_weather resonance_storm`, `set_weather wind`, or `set_weather dead_calm`.
3. Enter `show_weather` to see the actual state, intensity and remaining countdown. Close the console and spend a turn when checking FOV: `set_weather` does not immediately call `_update_fov()`.
4. Inspect the effect at the intended window size and zoom. Tune one parameter group, restart to reload definitions, and repeat. Debug forcing chooses a fresh random intensity and duration; it is not a fixed-intensity comparison harness.
5. Enter `stop_weather` to force clear weather. This also clears the particle system and fog cache, so it can remove unrelated particles during the experiment. Spend a turn to refresh sight before judging the result.

`fog_wisps` is a rendering helper entry used while fog is active; it is **not** a valid state for `set_weather`. The complete valid states additionally include `clear` and `overcast`.

Sources: [debug weather commands](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/debug.py), [WeatherSystem](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/weather.py).

## Tune the visual JSON

The existing visual types are `streak` for rain/wind/storm, `dot` for bone snow, and `soft_blob` for fog wisps. Keep the required `type`, `spacing`, `color` and `alpha` values when editing a visual definition. Mechanics-only definitions such as `dead_calm` are not precipitation definitions.

| Field | Current interpretation |
|---|---|
| `spacing` | Base spacing in renderer viewport pixels. Larger values make the grid sparser. |
| `intensity_scale` | When true, spacing is approximately `spacing / intensity`, clamped between one third and three times the base. Intensity primarily changes density here. |
| `color` | RGB channels, each 0–255. |
| `alpha` | Opacity channel, 0–255. |
| `speed_y`, `speed_x` | Renderer pixels per real-time second for the types that read them. These do not advance simulation turns. Dot snow uses vertical speed plus oscillation instead of `speed_x`. |
| `streak_len` | Vertical length in pixels; horizontal slant is derived from the velocity ratio. It is not the total diagonal length. |
| `width` | Streak line width in pixels. |
| `dot_size` | Circle **radius** in pixels. Soft blobs also draw a larger halo. |
| `speed_x_oscillate` | Snow's horizontal oscillation amplitude in pixels, despite the field's name. |
| `oscillate_period` | Snow oscillation period in milliseconds; keep it positive. |
| `glyph_tiles` | Sprite IDs used by the resonance-storm glyph overlay. Register every referenced sprite. |

For example, light rain currently uses spacing `60`, vertical speed `380`, horizontal speed `45`, length `5`, alpha `75` and width `1`. To make it visually gentler, first reduce alpha or increase spacing. Avoid changing the simulation duration while comparing its appearance.

Fog's gradient and the storm vignette have additional code-controlled behavior in `rendering/particles.py` and `rendering/renderer.py`. `weather.json` does not expose every aspect of their shape, pulse or clear area.

Sources: [weather definitions](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/data/weather.json), [precipitation/storm renderer](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/rendering/renderer.py), [fog and particle implementation](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/rendering/particles.py).

## Tune duration and frequency

Edit `_TRANSITIONS` and `_DURATIONS` in `engine/weather.py`. Transition weights are relative weights among the choices for the **current** state. They are not a global percentage of play time. Self-transitions reset the countdown and can keep weather unchanged across successive periods.

| State | Sampled countdown, simulation turns |
|---|---:|
| `clear` | 80–200 |
| `overcast` | 40–120 |
| `light_rain` | 20–80 |
| `heavy_rain` | 15–50 |
| `fog` | 30–100 |
| `wind` | 20–60 |
| `dead_calm` | 30–80 |
| `resonance_storm` | 10–30 |
| `forgetting_fog` | 20–50 |
| `bone_snow` | 15–40 |

The endpoints are inclusive. A tick with a positive countdown decrements it and returns; the following tick after it reaches zero performs the transition. Ordinary transitions choose intensity from 0.3–1.0; forced transitions use 0.5–1.0. Forgetting fog has a minimum intensity of 0.85.

The natural transition graph can reach forgetting fog from ordinary fog and dead calm from wind. Intact-bell discharge can force a resonance storm with a 25% chance; cracked-bell discharge can force dead calm with a 15% chance. Bone snow currently has no incoming ordinary transition from a different state; debug commands can force it. A definition's presence does not establish natural occurrence.

Labels, status colours and transition messages live in `_DISPLAY` and `_TRANSITION_MESSAGES`, also in Python. Keep a new state's transition targets, duration entry and display handling consistent.

Source: [state machine and discharge pushes](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/weather.py).

## Mechanical values and their scope

| Current state / setting | Shipped value | Actual consumer |
|---|---:|---|
| Fog `fov_cap` | 6 | Caps the computed player sight radius, in tiles. |
| Forgetting fog `fov_cap` | 4 | Same sight-cap route. |
| Forgetting fog `pathfind_noise` | 3 | Integer random perturbation of AI walkable path costs; it is not a displacement radius. |
| Bone snow `corruption_per_step` | 0.003 | Adds 0.3 percentage points to the 0–1 corruption value on the tile-entered route, subject to that route's earlier returns. |
| Storm `discharge_chance_bonus` | 0.10 | Adds 10 percentage points to the 12% base cracked-bell wind-check probability. |
| Dead calm `bell_range_bonus` | 10 | Adds 10 tiles to the 25-tile distance cutoff for that wind check. |
| Dead calm `creature_alert_radius_bonus` | 4 | Adds 4 tiles to creature sight used in the player-visibility check. |

The cracked-bell check runs on the resonance system's 40-turn wind counter and scans terrain bells; the weather name `wind` is not a prerequisite for that counter. Rain collection is a separate hardcoded Engine route for waiting outdoors with an empty water skin; its thresholds are not fields in `weather.json`.

**Underground behavior is only partly gated.** The regular weather countdown and weather graphics stop in submaps. The current FOV cap, AI modifiers, bone-snow tile-entry effect and cracked-bell weather modifiers do not have the same submap guard in their consumers. A surface weather state can therefore continue affecting those systems underground. Treat this as a current implementation limitation when balancing or verifying weather, rather than relying on the source comment saying there is no weather underground.

Sources: [Engine weather rendering, sight and rain collection](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/engine.py), [weather tick, bone snow and bell checks](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/resonance_system.py), [AI weather consumers](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/components/ai.py).

## Add a new state deliberately

Add its state-machine entries, duration, label/message and reachable transition; add the JSON visual/mechanical definition; wire its graphics into Engine's explicit weather render dispatch; and implement any new mechanical key in its intended consumer. The renderer's older comment that adding JSON alone creates a weather type is incomplete for this route. A novel mechanical property has no effect until something reads it.

Save/load records the current state, intensity and countdown, and injects the current JSON mechanics after loading. Definition edits can therefore affect mechanics after restart while a saved countdown remains unchanged. Verify new-state behavior on the surface, in a submap, through a transition, and across an explicit save/load in a disposable campaign.

Source: [weather restoration](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/save_manager.py).
