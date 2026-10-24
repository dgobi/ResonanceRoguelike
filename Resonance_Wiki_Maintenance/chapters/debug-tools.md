# Debug tools for authoring

The default configuration has `DEBUG_MODE = True`. Backtick opens the console; type a supported command and press Enter. F1 shows a compact overlay. The complete command table below is extracted from this revision's `CONSOLE_COMMANDS` registry, so it includes commands omitted from the old debug manual.

## Reliable inspection workflow

1. Start a new named world with `tools/play_disposable.py`.
2. Use F3 to mark the local map explored. This does not remove the normal FOV/light rules.
3. Use `spawn_item <id>`, `spawn_creature <id>` or `place_decor <id>` to inspect a definition. These are deliberate spawn operations, not tests of its random placement eligibility.
4. For a planned location, use the world-plan/diagnostic output to obtain world chunk coordinates. Open the overmap (`M` on the surface, or debug F4), move its cursor to that chunk, and press Enter. This uses the engine's current complete scene-entry route.
5. Use F9 for state text in the terminal. Capture the seed, world position, local position and submap identity when reporting a defect.

Debug-created items enter the legacy entity-list item route and can be picked up normally. For persistent authored content use the actual item/container/scene specification path in the relevant authoring chapter. A debug creature searches adjacent terrain for a walkable tile; this does not establish the same placement guarantees as the production world generator.

## Function-key reference

| Key | Current debug behavior |
|---|---|
| F1 | Toggle debug overlay. |
| F2 | Toggle local FOV visualization. |
| F3 | Mark local tiles explored. |
| F4 | Reveal the overmap and toggle submap highlights. |
| F5 | Legacy nearest-submap teleport; directly generates a region. |
| F6 | Prompt for hour 0–23. |
| F7 | Set internal hunger/thirst/corruption fractions using the prompt. |
| F8 | Legacy force-regeneration helper; increments chunk seed and replaces the active map. |
| Shift+F8 | Toggle player invincibility. |
| F9 | Print current diagnostic state to the terminal. |
| F10 | Prompt for `wx,wy`; legacy direct region generation, replacing active actors. |
| F11 | Retire the current save slot through `delete_slot()`. |
| F12 | Remap `tile_id sheet col row` in memory. Persist wanted edits manually in `sprite_map.json`. |

F5/F8/F10 still call direct older generation helpers and replace actors with the player. They do not prove current scene materialization, plan ownership or persistence. Prefer Enter on the debug overmap and the current automated journey for those checks. Do not use forced regeneration to make an existing campaign adopt a changed structure contract.

## Useful commands

```text
spawn_item severance_blade
spawn_creature briar_lurker
place_decor campfire_lit
show_resonance
show_weather
particle_stats
help
```

`place_decor clear` removes decor at the player's position; it does not promise to reverse every gameplay object/layer associated with earlier authored content. Debug changes are real changes to the disposable session. Grant/remove perk commands bypass the ordinary purchase workflow. Visual commands can alter weather or remove emitters; they are inspection tools, not neutral observations.

## Complete console registry

<!-- DEBUG_COMMAND_TABLE -->

## Where to extend the debug tools

`engine/debug.py` owns the command functions and the `CONSOLE_COMMANDS` metadata. Add a handler and registry entry together. A command's category controls help grouping; the F1 overlay uses a narrower category list, so a valid console command need not appear in every summary panel. Keep a new debug command's mutation scope explicit, then check the actual action in a disposable world.

The old DEBUG.md includes a fictionalized F9 dump with per-location HP and equipment output that the current `_dump_state()` does not print. Use the real terminal output as evidence.

## Source basis

[Debug implementation](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/debug.py) · [current travel/input](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/engine.py) · [configuration](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/config.py).
