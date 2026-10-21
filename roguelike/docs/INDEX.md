# Roguelike Project — Documentation Index

This folder contains technical documentation for the codebase. Use this as your entry point.

## Files in This Folder

| File | Contents |
|---|---|
| [INDEX.md](INDEX.md) | This file — navigation hub |
| [ARCHITECTURE.md](ARCHITECTURE.md) | High-level system overview, module map, data flow |
| [COMPONENTS.md](COMPONENTS.md) | All ECS components: fields, methods, thresholds |
| [COMBAT.md](COMBAT.md) | Attack resolution, essences, armor penetration |
| [GENERATION.md](GENERATION.md) | World gen, region gen, BSP dungeon, layout stamping |
| [RENDERING.md](RENDERING.md) | Render pipeline, sprite registry, UI layout |
| [SYSTEMS.md](SYSTEMS.md) | Engine systems: turns, time, save/load, AI, items |
| [DATA_REFERENCE.md](DATA_REFERENCE.md) | JSON data formats for tiles, entities, items, zones |
| [CREATURES.md](CREATURES.md) | Full creature roster, body definitions, abilities |
| [ESSENCE.md](ESSENCE.md) | All six essences, descriptions, weapons, creature modifier table |
| [LAYOUT_AUTHORING.md](LAYOUT_AUTHORING.md) | *(existing)* How to write hand-crafted map layouts |
| [SPRITESHEET_GUIDE.md](SPRITESHEET_GUIDE.md) | *(existing)* Sprite coordinate system |
| [DEBUG.md](DEBUG.md) | *(existing)* F-key debug overlay reference |

## Quick Orientation

The game is a single-player roguelike written in Python with pygame and tcod.

- **Entry point:** `roguelike/main.py`
- **Game loop:** `roguelike/engine/engine.py`
- **All game data:** `roguelike/data/` (JSON files, no hardcoded values)
- **Render mode:** toggled in `config.py` — ASCII (tcod) or Sprite (pygame 1-bit)

### Key Design Pillars

1. **Entity-Component System** — actors carry components (Fighter, Needs, AI, etc.) rather than inheriting behaviour
2. **Data-driven** — creatures, items, tiles, zones, and perks are defined in JSON; the engine reads them at startup
3. **Layered world** — 128×128 overworld chunks, each containing 0-4 SubMaps; SubMaps hold 80×43 `LocalMap` instances
4. **Essence system** — six essences (Dissolution, Binding, Quickening, Consumption, Revelation, Severance) modify weapon damage against certain creature types
5. **Corruption arc** — the player accumulates corruption (0.0-1.0), gating whispers, hallucinations, and void magic
