# Where to make a change

Use this map to find the owning file before editing. A definition, a runtime instance, and a saved scene are different objects. Changing JSON can affect newly created instances without changing an existing instance or already generated map. The current repository is the implementation authority; older arc reports and design proposals explain history and intent.

## Repository versus game working directory

The repository root contains `AGENTS.md`, the root `docs/`, `tools/`, acceptance evidence, and the `roguelike/` game directory. Game-relative paths such as `data/terrain.json` and `assets/sprites/terrain.png` are resolved with `roguelike/` as the working directory. Tool commands documented as running from the repository root must be run there instead.

Read the current `AGENTS.md` before implementing changes. It specifies work on the production `main` checkout, preservation of owner changes, named checkpoints before substantial work, autonomous headless/app-local verification, and separate authorization for pushing. The wiki itself does not authorize a push or redefine those working rules.

Source: [AGENTS.md](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/AGENTS.md).

## File map by intended change

All paths in this table are repository-relative.

| I want to change… | Start here | Check the connection to… |
|---|---|---|
| New-game player stats, components, or starter items | `roguelike/main.py` | `ItemFactory`, body definitions, and the new-game/bootstrap path |
| Default window, input routing, turn scheduling, or scene transitions | `roguelike/engine/engine.py` | Modal/death guards, ownership, checkpoint boundaries, and acceptance tests |
| An item definition | `roguelike/data/items/` | `engine/item_factory.py`, `engine/item_system.py`, acquisition and transfer routes |
| Inventory/container/floor ownership | `roguelike/engine/item_transfers.py` | `generation/floor_object_utils.py`, inventory screen, save identity |
| Crafting requirements or output | `roguelike/data/recipes/` | `engine/crafting.py`, `rendering/craft_screen.py`, placement/processing consumers |
| Creature stats or AI selection | `roguelike/data/entities/` | `engine/creature_factory.py`, `engine/ai_system.py`, `components/ai.py` |
| A creature ability or special combat behavior | `roguelike/engine/creature_abilities.py` | `engine/effect_lifecycle.py`, `engine/combat.py`, Engine's active dispatch |
| A weapon move | `roguelike/engine/movesets.py` and weapon definitions | Engine moveset targeting, damage, coating, and action timing |
| A perk | `roguelike/data/perks/` | `engine/hooks.py`, `engine/perk_handlers.py`, purchase and reconstruction routes |
| Survival balance | `roguelike/data/survival.json` | `components/needs.py`, Engine turn ticks, configured units |
| Weather | `roguelike/data/weather.json` | `engine/weather.py`, world time, renderer and particle mechanics |
| Resonance/corruption | `roguelike/engine/resonance_system.py`, `discharge.py`, related data | Hook/event timing, source aggregation, component state |
| Written lore or a readable item | `roguelike/data/texts/`, text-item mapping | `engine/text_reader.py`, `engine/language_system.py`, item `text_id` |
| Deep Tongue identity or rendering | `roguelike/data/deep_tongue.json` | `components/language.py`, language system, `rendering/glyph_gen.py`, lexicon screen |
| Terrain, movement surface, or overlay | `roguelike/data/terrain.json`, `decoratives.json` | `world/local_map.py`, generation helper, renderer, Engine consumer |
| Sprite pixels or atlas registration | `roguelike/assets/sprites/`, `data/sprites/sprite_map.json` | `rendering/sprite_registry.py` and shared atlas-cell users |
| ASCII fallback | `roguelike/data/tiles.json` → `tiles` | `rendering/tile_registry.py`, glyph sheet |
| UI fonts and map zoom | `roguelike/engine/display_config.py`, `config.py` | Screen layout and runtime coordinate calculations |
| UI colours | `roguelike/engine/palette.py` | Screen-local aliases and JSON/pixel colours which are independent |
| Panel ornament | `roguelike/assets/ui/` | `rendering/ui_registry.py` and the target draw call |
| Inventory or examination layout | `roguelike/engine/inventory_screen.py`, `look_mode.py` | Font measurement, clipping, action routes |
| Craft/perk/lexicon screens | `roguelike/rendering/craft_screen.py`, `perk_screen.py`, `lexicon_screen.py` | Their definition loaders and gameplay consumers |
| World composition or selection | `roguelike/generation/world_plan.py`, `settlement_selection.py`, `poi_selection.py` | Versioned generation, profiles, eligibility, deterministic context |
| Authored building/entrance/named layout | `roguelike/data/buildings/`, `entrances/`, `layouts/` | Shared structure contract, runtime preview, registration and placement |
| Generation-to-runtime scene ownership | `roguelike/engine/scene_generation.py` | `generation/placement.py`, materialization and metadata publication |
| Saves and scene cache | `roguelike/engine/save_manager.py`, `checkpoints.py`, `save_components.py` | Schema compatibility, exact item identity, all dirty scene owners |
| Debug console or one-off diagnostic | `roguelike/engine/debug.py`, root `tools/` | A disposable save root and the actual intended production route |

Sources: [game bootstrap](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/main.py), [data loader](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/data_loader.py), [Engine](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/engine.py), [repository tree at the audited revision](https://github.com/dgobi/ResonanceRoguelike/tree/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5).

## Follow a feature from data to play

A reliable content change has five links: definition → loader → runtime consumer → acquisition/placement → verification. For example, a new sprite key is only a registration. An item must name it, a factory must create the item, and a starter/debug/loot/structure route must put an instance into the world. A field with a plausible name is not a new mechanic unless some active code reads it.

Most ordinary content folders are recursively indexed by JSON `id`, not filename. The loader accepts a single object or an array of objects and warns on entries without IDs. Duplicate IDs overwrite previous entries in the ordinary directory loader; do not rely on traversal order. Missing directories can produce an empty table, and malformed files in that route can be reduced to warnings. Inspect the startup log as well as JSON syntax.

Structure authoring now goes through `StructureCatalog`, which creates the route-specific building, entrance, and layout collections. This is not the historical unspecialized building loader described in some older documents. Use the structure guide's validator for those files.

There are also specialized direct readers and module caches. The `DataLoader` docstring's assertion that nothing else reads files is too broad. Restart after changing definitions unless the specific tool advertises a supported reload path.

Source: [DataLoader and StructureCatalog hookup](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/data_loader.py).

## Separate simulation from presentation

`Engine.run()` is the frame/event loop. `_advance_turn()` coordinates the simulation. Frame redraws, UI animation, and particles are not player turns. An input handler or action route decides whether to advance time. The retained `engine/turn_queue.py` is not the active general scheduler; do not extend it under the assumption that adding behavior there changes normal gameplay.

Keep a content definition immutable during play. Put changing values on the owning item, actor, component, or local map. A renderer should read those values rather than secretly changing inventory, combat, or generation state. When adding persistent state, determine whether it belongs to the player, an item instance, a creature, a map, or the world and check the corresponding save/reconstruction path.

The current save system preserves validated checkpoint generations and serialized scene owners; it is not simply a collection of independently overwritten JSON files. Runtime effects also have explicit timing rules: hot map owners may advance while cold serialized owners freeze. Use the save and effects chapters before adding timers.

Sources: [Engine simulation coordinator](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/engine.py), [checkpoint persistence](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/save_manager.py), [effect lifecycle](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/effect_lifecycle.py).

## A practical code-change workflow

1. Identify the owning definition and consumer in the table above. Search for the field or method before inventing another path.
2. Check the current owner guide and acceptance tool for that subsystem. Historical failure reports may describe bugs that later arcs repaired.
3. Make the smallest coherent change that includes registration, use, persistence where relevant, and observable feedback.
4. Run the subsystem's existing bounded headless checks with a disposable save root. For visual changes, render and inspect the affected screen; do not substitute a parse check for a layout check.
5. Record which behavior changed, how it was verified, and which old wiki sections need updating. Keep source-permalink references pinned to the revision actually reviewed.

A new mechanic usually needs a code consumer. Copying a data field such as `on_use`, `interactable`, a perk handler name, or `visual_fx` only selects already implemented behavior. If no handler exists, document the limit instead of describing the proposed effect as available.

## How to read the existing documentation

The repository contains both root `docs/owner/` generation delivery records and `roguelike/docs/owner/` earlier state/acceptance material, as well as broader guides under `roguelike/docs/`. Many broad guides carry an explicit historical banner. Some state pages are append-only histories with superseding updates at the top; their older nested sections must not be treated as simultaneous current truth.

For rendering and assets, this wiki has reconciled `SPRITESHEET_GUIDE.md`, `RENDERING.md`, `DECORATIVES.md`, `DECOR AND RANDOM TILES.md`, `UI_RULES.md`, and `ARCHITECTURE.md` with the current implementation. Important corrections include full-colour defaults, 32-pixel displayed sprites, persistent/functional decor, real font sizes, the current palette, the actual panel API, inactive configuration promises, and limitations in fallback/light/effect routes.

For future updates, preserve the old evidence as history, update the actionable recipe, and list unresolved discrepancies explicitly. A dated proposal is useful context; it is not evidence that its feature has shipped.

## G7 and G8 generation map

`generation/compounds.py` and `compound_integrity.py` own bounded rural parents and child/path ownership. `settlement_layout.py` owns G8 local streets, common, blocks and frontage; `settlement_selection.py` fills roles; `settlement_preview.py` renders complete previews. `plan_integrity.py`, `planned_scene.py` and `scene_adapters.py` preserve resolved geometry and lifecycle. See `docs/owner/WORLDGEN_G8.md` for evidence and `roguelike/docs/STRUCTURE_AUTHORING.md` for executable authoring instructions.
