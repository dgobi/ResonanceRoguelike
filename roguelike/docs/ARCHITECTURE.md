# Architecture Overview

## Directory Structure

```
roguelike/
├── main.py                     Entry point — init, world gen, player setup, engine start
├── config.py                   Global constants and render-mode flag
│
├── components/                 ECS components attached to actors/items
│   ├── fighter.py              Hit locations, armor layers, HP pools
│   ├── equipment.py            10-slot equipment manager
│   ├── inventory.py            Weight-based carrying
│   ├── needs.py                Hunger & thirst (0.0-1.0 scales)
│   ├── corruption.py           Corruption tracking, whispers, state gates
│   ├── ai.py                   State-machine AI (Dormant→Wandering→Hunting…)
│   ├── language.py             Deep tongue lexicon learning
│   ├── perks.py                Perk acquisition and affinity scores
│   ├── perception.py           Sight/hearing radii and faction hostility
│   └── light_source.py         Light emission with falloff and flicker
│
├── entities/                   Base entity types
│   ├── entity.py               Base Entity (position, tile, name, movement flag)
│   ├── actor.py                Actor(Entity) — living beings with components
│   └── item.py                 Item(Entity) — carriable/droppable objects
│
├── engine/                     Core game systems
│   ├── engine.py               Main game loop, FOV, input, state management
│   ├── data_loader.py          Loads all JSON from data/ at startup
│   ├── display_config.py       Font loading, window setup, pygame surface config
│   ├── message_log.py          Colored stacking message system
│   ├── world_time.py           Day/night cycle, 8 moon phases, ambient light
│   ├── turn_queue.py           Round-robin actor scheduling
│   ├── combat.py               Attack resolution with armor layers and essences
│   ├── creature_abilities.py   Six special passive/triggered abilities
│   ├── creature_factory.py     Builds Actor instances from entity JSON templates
│   ├── item_factory.py         Builds Item instances from item JSON templates
│   ├── item_system.py          Use/equip/consume/read logic
│   ├── inventory_screen.py     Full inventory UI (I key)
│   ├── look_mode.py            Examine mode (; or x key)
│   ├── ai_system.py            Iterates all non-player actors and calls AI.take_turn
│   ├── text_reader.py          Multi-page found-document overlay
│   ├── loot_table.py           Weighted random loot generation
│   ├── save_manager.py         Save/load with ChunkCache for submap surfaces
│   ├── ui.py                   Status bar and message panel draw calls
│   ├── debug.py                F1-F12 + backtick debug overlays
│   ├── visual_events.py        Queued visual effects (damage numbers, screen shake)
│   └── starting_location.py    First-session descent into the lab
│
├── world/                      World data structures
│   ├── local_map.py            80×43 numpy tile array with light map
│   ├── world_map.py            128×128 Chunk grid, SubMap definitions, TownData
│   ├── region.py               RegionType and ConnectorType enums
│   ├── world_myth.py           Procedural myth generation
│   └── name_gen.py             Three-register procedural name generation
│
├── generation/                 Procedural content generation
│   ├── world_gen.py            Biome distribution (Perlin noise) for 128×128 grid
│   ├── region_gen.py           Per-biome local map generation dispatcher
│   ├── local_gen.py            BSP dungeon + text/loot placement
│   ├── entrance_gen.py         Entrance structure stamping
│   ├── layout_stamper.py       JSON → LocalMap ASCII grid stamper
│   └── town_gen.py             Town/city map generation (under revision)
│
├── rendering/                  Display layer
│   ├── renderer.py             Dual ASCII/sprite render with ghost + entity + UI passes
│   ├── tile_registry.py        Loads tile properties from tiles.json
│   ├── sprite_registry.py      1-bit sprite sheets with color tinting
│   ├── ui_registry.py          9-slice panel drawing (12 Hexany designs)
│   └── biome_icons.py          Procedural 64×64 biome icons (seeded, cached)
│
├── assets/
│   ├── fonts/                  TTF files + tileset PNGs
│   ├── sprites/                1-bit sprite sheets
│   └── ui/                     Panel texture PNGs
│
├── data/                       All game data as JSON — see DATA_REFERENCE.md
└── docs/                       This folder
```

---

## Module Dependency Map

```
main.py
  ├── engine/display_config.py     (pygame/tcod init, fonts)
  ├── engine/data_loader.py        (reads data/ once)
  ├── rendering/tile_registry.py
  ├── world/world_map.py
  ├── generation/world_gen.py
  ├── generation/region_gen.py
  ├── entities/actor.py            (player creation)
  └── engine/engine.py             ◄── main game loop lives here
        ├── world/local_map.py
        ├── engine/turn_queue.py
        ├── engine/world_time.py
        ├── engine/message_log.py
        ├── engine/combat.py
        ├── engine/ai_system.py
        │     └── components/ai.py
        ├── engine/item_system.py
        ├── engine/visual_events.py
        ├── engine/save_manager.py
        ├── rendering/renderer.py
        │     ├── rendering/sprite_registry.py
        │     ├── rendering/tile_registry.py
        │     └── rendering/ui_registry.py
        └── engine/ui.py
```

---

## World Hierarchy

```
WorldMap  (128 × 128 Chunks)
│
└── Chunk  (one per grid cell)
      ├── region_type  (RegionType enum)
      ├── zones[]      (zone IDs from data/zones/)
      ├── TownData     (if region_type == TOWN)
      └── SubMap[]     (0–4 per chunk)
            │
            └── LocalMap  (80 × 43 tiles)
                  ├── tiles   numpy array
                  ├── light_map  float RGB array
                  └── submap_links  {(x,y): submap_id}
```

The player always occupies exactly one `LocalMap`. Moving through a staircase or entrance transitions to a different `LocalMap` (same or different `SubMap`).

---

## Frame Loop (engine.py)

Each frame:

1. **Input** — keyboard/mouse events dispatched to active screen state
2. **Turn processing** (if not waiting for input):
   a. Player action validated
   b. `TurnQueue.next()` called until player's turn again
   c. Each non-player actor: `ai_system.update(actor, …)`
   d. `WorldTime.advance(1)`
   e. Needs decay, corruption tick, creature abilities
3. **FOV** — tcod FOV computed from player position
4. **Light map** — all `LightSource` components blended into `LocalMap.light_map`
5. **Render**:
   a. Ghost pass (last known positions of unseen actors)
   b. Tile pass (visible + explored tiles)
   c. Entity pass (actors, items)
   d. UI pass (status bar, message log)
   e. Visual effects (damage numbers, screen shake)
6. **pygame.display.flip()**

---

## Save System

`SaveManager` stores:
- `world_map` — full chunk grid with explored flags
- `local_map` — current map tiles + explored mask
- `player` — all components serialized
- `entities` — all non-player actors/items on current map
- `world_time` — current turn count
- `world_myth` — procedural narrative state
- `ChunkCache` — surface maps for each submap, loaded when descending/ascending

Saves are written to `saves/` as JSON. The engine auto-saves on submap transitions.

---

## Render Modes

Set `RENDER_MODE` in `config.py`:

| Mode | Backend | Tiles | Notes |
|---|---|---|---|
| `"ascii"` | tcod tileset | Unicode chars from `tiles.json` | Classic roguelike look |
| `"sprite"` | pygame surfaces | 1-bit sheets from `assets/sprites/` | Color-tinted pixel art |

Both modes share the same UI panels, message log, and status bar. Only the main game view differs.

---

## Color Palette (Punolite Plus)

All colors are defined as `[R, G, B]` triplets. Key entries:

| Name | Value | Used for |
|---|---|---|
| `void_black` | `[7, 12, 29]` | Primary background |
| `steel_blue` | `[40, 96, 128]` | Dungeon walls |
| `teal_dark` | `[40, 84, 84]` | Dungeon floor |
| `mid_green` | `[93, 167, 93]` | Grass |
| `dark_green` | `[57, 117, 92]` | Trees |
| `old_gold` | `[226, 181, 112]` | Torches, doors |
| `near_white` | `[227, 245, 241]` | Player, UI highlights |
| `blood_rose` | `[145, 58, 82]` | Undead creatures |
| `mist_blue` | `[129, 175, 181]` | Combat hit messages |
| `night_purple` | `[41, 21, 70]` | Deep tongue text |
| `midnight` | `[25, 27, 63]` | Status bar background |
| `slate_dark` | `[50, 73, 95]` | Message panel tint |
