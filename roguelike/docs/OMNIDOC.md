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

# Combat System

All combat logic lives in `roguelike/engine/combat.py`. Special creature abilities are in `roguelike/engine/creature_abilities.py`.

---

## Attack Resolution

### Entry Point

```python
resolve_attack(
    attacker_name: str,
    defender_name: str,
    defender_fighter: Fighter,
    body_def: dict,
    weapon: Item | None,
    creature_essence_mods: dict,
    rng: Random,
    attacker_disrupted: bool = False
) -> CombatResult
```

Called by the engine whenever an actor attacks. Returns a `CombatResult` describing everything that happened.

### Resolution Steps

1. **Select hit location** — weighted random draw from body definition's location table (weighted by `size` field)
2. **Roll damage** — parse weapon's `damage` dice string (e.g. `"1d6+2"`), roll it, add `fighter.power`
3. **Roll twice if disrupted** — if `attacker_disrupted` (Hollow Knight aura), roll damage twice and take the lower
4. **Apply essence modifier** — if weapon has an essence matching a `creature_essence_mods` key, multiply damage
5. **Penetrate armor layers** — iterate layers at the hit location, each layer absorbs some damage based on AV; track struck and bypassed layers
6. **Deal location damage** — call `fighter.take_location_damage(location_id, remaining_damage, body_def)`; collect any new impairments
7. **Build CombatResult** — assemble messages, message types, and damage number

### Dice Format

`"NdM+K"` where N = number of dice, M = sides, K = optional modifier (can be negative).

```python
roll_dice("2d6+3", rng)   # rolls 2d6 then adds 3
roll_dice("1d4", rng)     # rolls 1d4
```

---

## CombatResult

```python
@dataclass
class CombatResult:
    hit: bool
    location_id: str
    location_name: str         # display name (e.g. "right arm")
    layers_struck: list        # armor layers that absorbed damage
    layers_bypassed: list      # armor layers the attack went through
    damage_raw: int            # pre-armor damage
    damage_dealt: int          # post-armor damage applied to HP
    impairments: list[str]     # new impairments triggered this hit
    essence_applied: str       # essence name, or None
    essence_modifier: float    # multiplier applied (1.0 = no change)
    attacker_dead: bool
    defender_dead: bool
    messages: list[str]        # human-readable message lines
    message_types: list[str]   # color keys ("hit", "deflect", "impair", "death")
    damage_number: int         # shown in floating number display
    is_player_hit: bool
```

### Message Type Colors

| Type | Color | Used for |
|---|---|---|
| `"hit"` | mist_blue | Normal hit |
| `"deflect"` | slate_mid | Armor blocked all damage |
| `"impair"` | dusty_rose | Impairment triggered |
| `"death"` | blood_rose | Target killed |

---

## Essence System

Six essences modify damage dealt when a weapon's essence matches the defender's vulnerability list.

### The Six Essences

| Essence | Theme |
|---|---|
| Dissolution | Corrodes, breaks down |
| Binding | Preserves form, constrains |
| Quickening | Alive, animates, accelerates |
| Consumption | Feeds or drains |
| Revelation | Exposes the true |
| Severance | Cuts connections, severs links |

### Pip Display

Essence strength is shown as filled pips in the inventory:

| Value | Display |
|---|---|
| 0.2 | `●○○○○` |
| 0.4 | `●●○○○` |
| 0.6 | `●●●○○` |
| 0.8 | `●●●●○` |
| 1.0 | `●●●●●` |

### Applying Essences

```python
apply_essence(
    damage: int,
    essence: str,
    strength: float,
    creature_modifiers: dict
) -> tuple[int, float]
    # Returns (modified_damage, net_modifier).
    # creature_modifiers maps essence_name → multiplier.
```

If the weapon's essence is in `creature_modifiers`, the modifier is `strength * creature_modifiers[essence]`. A modifier > 1.0 amplifies; < 1.0 reduces.

### Weapon–Creature Matchups

| Weapon | Vs Creature | Modifier |
|---|---|---|
| Binding Knife | Bog Wraith | ×3.0 (decisive) |
| Severance Blade | Hollow Knight / Revenant | ×2.5 (decisive) |
| Revelation Lens | Grave Thing | ×2.8 (decisive) |
| Dissolution Blade | Briar Lurker | ×2.0 |
| Dissolution Blade | Stone Lurker | ×1.8 |

---

## Armor Penetration

Each body location carries an ordered list of armor layers. When damage arrives:

```python
roll_layers(
    layers: list[dict],
    damage: int,
    rng: Random
) -> tuple[int, list, list]
    # Returns (remaining_damage, struck_layers, bypassed_layers)
```

Each layer has:
- `name` — display name (e.g. `"fused plate"`)
- `av` — armor value (damage blocked)
- `material` — material tag (affects certain essence interactions)

Damage is reduced by each layer's `av`. A layer is "struck" if it absorbed any damage and "bypassed" if damage passed through. Remaining damage after all layers is applied to the location's HP pool.

---

## Creature Abilities  (`creature_abilities.py`)

Six special abilities triggered by `process_abilities(entity, engine)` each turn for eligible creatures.

### 1. Bog Wraith — FOV Drain

- Effect: Each turn within 8 tiles, reduces player's effective FOV by a gradient amount
- On death: +8-tile overcorrection (brief expanded vision)
- Counter: Binding-essence weapons deal ×3.0

### 2. Barrow Wight — Corruption Aura

- Effect: +0.005 corruption per turn while within 2 tiles
- Emits a warning message every 20 turns of proximity

### 3. Hollow Knight — Resonant Disruption

- Effect: Any attacker within 5 tiles rolls damage **twice** and takes the lower roll
- Counter: Severance-essence weapons deal ×2.5

### 4. Plague Crow — Sickness on Hit

- Effect: 30% chance to inflict **Sickness** on a successful hit
- Sickness: accelerates both hunger and thirst drain for 30 turns

### 5. Stone Lurker — Hibernation Ambush

- Hibernates visually as a rock tile
- Wakes when the player enters within 3 tiles
- On wake: gains a free ambush attack before the player can react

### 6. Briar Lurker — Thorn Retaliation

- On receiving any melee hit: retaliates with 1–2 thorn hits
- Thorn hits always target torso, bypass normal armor (direct damage)

---

## Body Definitions  (`data/bodies/`)

Body definitions are JSON files loaded by `DataLoader`. Each defines the hit locations for a creature type.

### Schema

```json
{
  "id": "humanoid",
  "locations": [
    {
      "id": "head",
      "name": "head",
      "display": "head",
      "size": 10,
      "hp": 10,
      "impairment_threshold": 5,
      "impairment": "blinded"
    },
    {
      "id": "torso",
      "name": "torso",
      "display": "chest",
      "size": 40,
      "hp": 30
    }
  ]
}
```

| Field | Description |
|---|---|
| `size` | Relative probability of being hit (used in weighted selection) |
| `hp` | Starting HP for this location |
| `impairment_threshold` | HP value at which impairment triggers |
| `impairment` | String added to `fighter.impairments` at threshold |

### Available Body Types

12 body definitions ship with the game: humanoid, wight, hollow_knight, hollow_revenant, drowned_revenant, grave_thing, heath_stalker, briar_lurker, stone_lurker, bog_wraith, plague_crow, bandit.

# Components Reference

Components are plain Python objects attached to `Actor` instances. They hold state and expose methods — the engine and system modules call them rather than the actor doing logic itself.

All components live in `roguelike/components/`.

---

## Fighter  (`fighter.py`)

Manages hit points split across body locations, armor layers, and combat impairments.

### Fields

| Field | Type | Description |
|---|---|---|
| `max_hp` | `int` | Legacy total HP (used for simple creatures) |
| `power` | `int` | Base attack power (added to weapon roll) |
| `defense` | `int` | Legacy flat damage reduction |
| `body_id` | `str` | Key into `data/bodies/` |
| `location_hp` | `dict[str, int]` | Current HP per body location |
| `location_max` | `dict[str, int]` | Max HP per body location |
| `impairments` | `set[str]` | Active impairments (e.g. `"blinded"`, `"left_leg_broken"`) |
| `armor_layers` | `dict[str, list]` | Ordered armor layers per location, each `{"name", "av", "material"}` |

### Properties

| Property | Returns | Notes |
|---|---|---|
| `hp` | `int` | Sum of all `location_hp` values |
| `hp_fraction` | `float` | `hp / sum(location_max)` |
| `is_dead` | `bool` | True if all locations are at 0 |

### Methods

```python
initialize_from_body(body_def: dict) -> None
```
Reads a body definition from `data/bodies/` and populates `location_hp`, `location_max`, and empty `armor_layers` entries for each location.

```python
take_damage(amount: int) -> int
```
Legacy fallback — subtracts from torso HP. Returns actual damage dealt.

```python
take_location_damage(location_id: str, damage: int, body_def: dict) -> list[str]
```
Applies `damage` to the given location. Triggers and returns a list of newly-activated impairment strings if the location drops below its threshold.

```python
heal(amount: int) -> int
```
Restores HP to torso location (capped at max). Returns amount actually healed.

```python
has_impairment(imp: str) -> bool
can_attack() -> bool    # dominant hand OK and alive
can_move() -> bool      # at least one leg functional and alive
```

---

## Equipment  (`equipment.py`)

Manages the 10 equipment slots. Items are stored by slot name.

### Slots

`weapon`, `offhand`, `armor_head`, `armor_torso`, `armor_arms`, `armor_legs`, `belt_1`, `belt_2`, `belt_3`, `light`

### Methods

```python
equip(item: Item, slot: str) -> None
unequip(slot: str) -> Item | None      # returns displaced item or None
is_equipped(item: Item) -> bool
equipped_in(slot: str) -> Item | None
```

---

## Inventory  (`inventory.py`)

Weight-based carrying. Items beyond `capacity` kg cannot be added.

### Fields

| Field | Type | Description |
|---|---|---|
| `capacity` | `float` | Max carry weight in kg |
| `items` | `list[Item]` | Currently carried items |

### Properties

```python
current_weight: float    # sum of item.weight * item.count
is_full: bool            # current_weight >= capacity
encumbrance: float       # 0.0 (empty) to 1.0 (at capacity)
```

### Methods

```python
add(item: Item) -> bool     # False if would exceed capacity
remove(item: Item) -> bool  # False if item not in list
has(item_id: str) -> bool
get_by_id(item_id: str) -> Item | None
```

---

## Needs  (`needs.py`)

Hunger and thirst, each a float in `[0.0, 1.0]` where 0 = fully satisfied and 1 = critical.

### Fields

| Field | Default | Description |
|---|---|---|
| `hunger` | `0.0` | Current hunger level |
| `thirst` | `0.0` | Current thirst level |

### Thresholds

Both scales share the same breakpoints:

| Value | Hunger State | Thirst State |
|---|---|---|
| < 0.15 | Sated | Slaked |
| < 0.35 | Hungry | Thirsty |
| < 0.60 | Famished | Parched |
| < 0.85 | Starving | Desiccating |
| ≥ 0.85 | Wasting | Drained |

### Properties

```python
hunger_state: str        # one of the hunger labels above
thirst_state: str        # one of the thirst labels above
fov_penalty: int         # sight radius reduction at high need levels
is_critical: bool        # True if either stat ≥ 0.85
```

### Methods

```python
advance(hunger_rate=None, thirst_rate=None) -> None
    # Decay both stats by their rates each turn.
    # Default rates come from zone/player config.

eat(nutrition: float) -> None     # reduce hunger by nutrition (clamped to 0)
drink(hydration: float) -> None   # reduce thirst by hydration (clamped to 0)

drain_messages(log: MessageLog, prev_hunger: float, prev_thirst: float) -> None
    # Emits state-transition messages when crossing thresholds.
```

---

## Corruption  (`corruption.py`)

Tracks spiritual corruption as a float `[0.0, 1.0]`. Accumulates passively in tainted zones; hard to reduce.

### Fields

| Field | Type | Description |
|---|---|---|
| `value` | `float` | Current corruption (0.0–1.0) |
| `_whisper_cooldown` | `int` | Turns until next whisper message |

### States

| Threshold | State |
|---|---|
| < 0.15 | Unmarked |
| < 0.30 | Touched |
| < 0.50 | Stained |
| < 0.70 | Marked |
| < 0.90 | Consumed |
| ≥ 0.90 | Vessel |

### Properties

```python
state: str                # label from table above
fov_penalty: int          # sight penalty at higher corruption
void_magic_bonus: float   # scales 0–1 with corruption
hallucinating: bool       # True above ~0.70
is_vessel: bool           # True at 0.90+
```

### Methods

```python
accumulate(amount: float) -> None   # increase; clamped to 1.0
cleanse(amount: float) -> None      # decrease; heavily reduced effectiveness at high values

tick(log: MessageLog, zone_tags: list[str], turn: int) -> None
    # Called each turn. Applies passive accumulation based on zone_tags.
    # Emits whisper messages from the deep tongue lexicon on cooldown.
```

---

## LightSource  (`light_source.py`)

Emits light in a radius. Multiple sources are blended additively into `LocalMap.light_map`.

### Fields

| Field | Type | Description |
|---|---|---|
| `radius` | `int` | Base emission radius in tiles |
| `color` | `tuple[int,int,int]` | RGB light color |
| `falloff` | `float` | 1.0 = linear, 2.0 = quadratic |
| `flicker` | `bool` | Randomly reduce effective radius each frame |
| `active` | `bool` | Whether the light is currently on |

### Methods

```python
effective_radius() -> int
    # Returns radius, randomly -1 or -2 if flicker is True.

toggle() -> None

apply_to_light_map(
    light_map: np.ndarray,
    source_x: int,
    source_y: int,
    fov_mask: np.ndarray
) -> None
    # Additively blends this light onto light_map for all tiles
    # within effective_radius() that are in fov_mask.
```

---

## AI  (`ai.py`)

State-machine AI. Each actor with an AI component takes one turn per round.

### AIState Enum

`DORMANT` → `WANDERING` → `ALERTED` → `HUNTING` → `ATTACKING` → `FLEEING` → `WAITING`

### Fields

| Field | Type | Description |
|---|---|---|
| `state` | `AIState` | Current behavioral state |
| `wander_radius` | `int` | Max tiles from home when wandering |
| `alert_memory` | `int` | Turns to remain alerted without re-sighting player |
| `home_x, home_y` | `int` | Spawn/patrol origin |
| `target_x, target_y` | `int` | Last known player position |
| `memory_turns` | `int` | Turns remaining in alert memory |

### Methods

```python
take_turn(
    actor: Actor,
    local_map: LocalMap,
    entities: list,
    player: Actor,
    log: MessageLog,
    rng: Random,
    ambient_light: float,
    engine: Engine
) -> None
    # Main entry point. Calls _update_state then _act.

_update_state(...)  # Transitions between AIState values based on visibility
_act(...)           # Executes movement, attack, or wait based on current state
```

### State Transitions

```
DORMANT    ──sight/sound──►  ALERTED
WANDERING  ──sight──────────►  HUNTING
ALERTED    ──sight lost──►  WANDERING  (after alert_memory runs out)
HUNTING    ──adjacent──────►  ATTACKING
ATTACKING  ──target dead──►  WANDERING
FLEEING    ──hp restored──►  WANDERING
```

---

## Language  (`language.py`)

Tracks which Deep Tongue words the player has learned and which damaged text spans have been recovered.

### Fields

| Field | Type | Description |
|---|---|---|
| `known_deep_words` | `set[str]` | Learned Deep Tongue words |
| `translation_events` | `dict` | `{word: turn_learned}` |
| `recovered_spans` | `set[tuple]` | `(text_id, page_idx, span_idx)` tuples |
| `recovered_text` | `dict` | Recovered glyph strings by span key |

### Methods

```python
knows(word: str) -> bool
learn(word: str, turn: int) -> bool    # returns True if newly learned
recover_span(text_id, page_idx, span_idx, recovered: str) -> None
is_recovered(text_id, page_idx, span_idx) -> bool
get_recovered(text_id, page_idx, span_idx) -> str | None
```

---

## Perks  (`perks.py`)

Manages acquired perks and the eight affinity score tracks.

### Affinities

`the_hollow_road`, `the_witnessing`, `the_green_patience`, `the_bound_name`, `the_unmarked_way`, `the_consuming`, `the_sutured_work`, `the_red_accounting`

### Fields

| Field | Type | Description |
|---|---|---|
| `acquired` | `set[str]` | Perk IDs the player has |
| `perk_state` | `dict` | Mutable per-perk state (cooldowns, counters, etc.) |
| `affinity_scores` | `dict[str, float]` | Score per affinity track |

### Methods

```python
has(perk_id: str) -> bool
acquire(perk_id: str, affinity: str = None) -> bool
    # Returns True if newly acquired. Increments affinity score if provided.

get_state(perk_id: str) -> dict   # returns mutable state dict for the perk
affinity_score(affinity: str) -> float
```

---

## Perception  (`perception.py`)

Defines what an actor can perceive and who they consider hostile.

### Fields

| Field | Type | Description |
|---|---|---|
| `sight_radius` | `int` | Max tiles for visual detection |
| `hearing_radius` | `int` | Max tiles for sound detection |
| `sees_in_dark` | `bool` | Ignores ambient light requirement |
| `faction` | `str` | This actor's faction label |
| `hostile_to` | `list[str]` | Faction labels this actor attacks on sight |

### Methods

```python
is_hostile_to(other_faction: str) -> bool

can_see(
    viewer_x: int, viewer_y: int,
    target_x: int, target_y: int,
    target_visible_to_player: bool,
    ambient_light: float
) -> bool
    # Returns True if line-of-sight and light conditions are met.
```

# Creature Reference

All creatures are defined in `roguelike/data/entities/creatures/`. Body definitions are in `roguelike/data/bodies/`. Special abilities are implemented in `roguelike/engine/creature_abilities.py`.

---

## Creature Roster

| Creature | Tile | Body | Damage | Key Armor | Essence Vulnerability | Special |
|---|---|---|---|---|---|---|
| Barrow Wight | `barrow_wight` | wight | 1d6+1 | Resonance AV2, Dense Bone AV3 | Binding ×3.0 | Corruption aura |
| Hollow Knight | `hollow_knight` | hollow_knight | 1d8+2 | Fused Plate AV6, Helm AV5 | Severance ×2.5 | Disruption aura |
| Hollow Revenant | `hollow_revenant` | hollow_revenant | 1d4+1 | Resonance Shell AV1 | Severance ×2.5 | — |
| Drowned Revenant | `drowned_revenant` | drowned_revenant | 1d4+1 | Waterlogged AV1 | — | — |
| Grave Thing | `grave_thing` | grave_thing | 1d6 | Compressed Bone AV4 | Revelation ×2.8 | — |
| Heath Stalker | `heath_stalker` | heath_stalker | 1d6 | Sinewy AV2, Lean Muscle AV1 | — | — |
| Briar Lurker | `briar_lurker` | briar_lurker | 1d4 | Dense Thornmass AV3 | Dissolution ×2.0 | Thorn retaliation |
| Stone Lurker | `stone_lurker` | stone_lurker | 1d8+2 | Stone Carapace AV6 | Dissolution ×1.8 | Hibernation ambush |
| Bog Wraith | `bog_wraith` | bog_wraith | 1d4 | Diffuse AV3 (mist) | Binding ×3.0 | FOV drain |
| Plague Crow | `plague_crow` | plague_crow | 1d3 | Feathers AV0 | — | Sickness 30% on hit |
| Highland Bandit | `highland_bandit` | humanoid | 1d6+1 | None | — | — |

---

## Special Abilities

Triggered by `creature_abilities.process_abilities(entity, engine)` each turn.

### Bog Wraith — FOV Drain

The Bog Wraith warps the boundaries of sight.

- **Effect:** Each turn within 8 tiles, reduces the player's effective FOV radius by a gradient amount proportional to distance
- **On death:** Overcorrects — player briefly gains +8 to FOV radius before it normalizes
- **Counter:** Binding-essence weapons deal ×3.0 damage

### Barrow Wight — Corruption Aura

Proximity to the Wight corrodes the spirit.

- **Effect:** +0.005 corruption per turn while within 2 tiles of the player
- **Warning:** Emits a warning message every 20 turns of sustained proximity
- **Compound:** Multiple Wights do not stack the aura, but each checks independently

### Hollow Knight — Resonant Disruption

The Knight's broken essence disrupts the form of attackers.

- **Effect:** Any attacker within 5 tiles rolls attack damage **twice** and takes the **lower** roll
- **Range:** 5-tile radius; the player must be adjacent or near-adjacent to trigger
- **Counter:** Severance-essence weapons deal ×2.5 damage

### Plague Crow — Sickness

The Crow's talons carry decay.

- **Effect:** 30% chance to inflict **Sickness** on a successful hit
- **Sickness mechanics:** Accelerates both hunger and thirst drain rates for 30 turns
- **Stacking:** Multiple sickness applications extend the duration

### Stone Lurker — Hibernation Ambush

The Lurker waits as stone, then strikes.

- **Hibernation:** While dormant, the Lurker appears as a rock tile — visually indistinguishable from terrain
- **Wake trigger:** Player enters within 3 tiles
- **Free attack:** On waking, the Lurker immediately performs one free attack before normal turn order resumes
- **Counter:** Dissolution-essence weapons deal ×1.8 damage

### Briar Lurker — Thorn Retaliation

Strike the briars and they strike back.

- **Effect:** On receiving any melee hit, retaliates with 1–2 thorn hits
- **Thorn mechanics:** Thorn hits always target torso; they are direct hits (bypass all armor layers)
- **Counter:** Dissolution-essence weapons deal ×2.0 damage

---

## Body Definitions

The 12 body definitions are in `roguelike/data/bodies/`. Each defines hit locations with HP pools, hit weights, and impairment thresholds.

### Common Locations by Body Type

**Humanoid** (`humanoid`, `highland_bandit`):

| Location | Size | HP | Impairment at Threshold |
|---|---|---|---|
| head | 10 | 10 | blinded (at 5 HP) |
| torso | 40 | 30 | — |
| left arm | 15 | 12 | left_arm_broken (at 4 HP) |
| right arm | 15 | 12 | right_arm_broken (at 4 HP) |
| left leg | 15 | 14 | left_leg_broken (at 5 HP) |
| right leg | 15 | 14 | right_leg_broken (at 5 HP) |

**Barrow Wight** (`wight`):
Locations: skull, ribcage, left limb, right limb. Higher bone AV across all locations.

**Hollow Knight** (`hollow_knight`):
Locations: helm, torso plate, arms, legs. Highest AV values in the game.

**Bog Wraith** (`bog_wraith`):
Diffuse body — single "form" location with mist-based AV. Cannot be impaired.

**Plague Crow** (`plague_crow`):
Locations: breast, head, wings. Very low HP pools; AV 0 on all.

---

## AI Behavior by Creature Type

All creatures use the standard AI state machine (see [COMPONENTS.md](COMPONENTS.md#ai)), but with different parameters:

| Creature | Sight Radius | Hears in Dark | Wander Radius | Alert Memory | Notes |
|---|---|---|---|---|---|
| Barrow Wight | 8 | yes | 8 | 12 | `sees_in_dark: true` |
| Hollow Knight | 6 | yes | 5 | 8 | Patrols slowly |
| Hollow Revenant | 5 | yes | 10 | 6 | Roams widely |
| Drowned Revenant | 4 | yes | 8 | 4 | Low memory |
| Grave Thing | 4 | no | 3 | 3 | Nearly blind; short range |
| Heath Stalker | 10 | no | 12 | 10 | High sight; roams far |
| Briar Lurker | 3 | no | 2 | 5 | Almost stationary |
| Stone Lurker | 3 | no | 0 | — | Hibernates; no wander |
| Bog Wraith | 6 | yes | 10 | 8 | Floats through rooms |
| Plague Crow | 12 | no | 15 | 6 | Excellent sight; skittish |
| Highland Bandit | 8 | no | 10 | 8 | Human intelligence |

---

## Factions

Faction labels used by `Perception.hostile_to`:

| Faction | Hostile to |
|---|---|
| `player` | — |
| `undead` | `player`, `living` |
| `beast` | `player` |
| `bandit` | `player` |
| `living` | `undead` |

Creatures only attack factions on their `hostile_to` list. Adding new factions requires updating `hostile_to` lists in creature JSON.

# Data Reference

All game data lives in `roguelike/data/` as JSON files. The `DataLoader` reads them once at startup (`engine/data_loader.py`). No game values are hardcoded in Python.

---

## Tiles  (`data/tiles.json`)

Defines rendering properties for every tile type.

```json
{
  "wall": {
    "char": "#",
    "color_fg": [40, 96, 128],
    "color_bg": [7, 12, 29],
    "sprite_sheet": "obj",
    "sprite_col": 2,
    "sprite_row": 0
  }
}
```

| Field | Type | Description |
|---|---|---|
| `char` | string | Unicode character for ASCII mode |
| `color_fg` | `[R,G,B]` | Foreground (glyph) color |
| `color_bg` | `[R,G,B]` | Background cell color |
| `sprite_sheet` | string | `"char"` or `"obj"` |
| `sprite_col` | int | Column in sprite sheet |
| `sprite_row` | int | Row in sprite sheet |

---

## Terrain  (`data/terrain.json`)

Walkability and transparency for each terrain type. Used by `LocalMap` and FOV.

```json
{
  "floor": { "walkable": true,  "transparent": true  },
  "wall":  { "walkable": false, "transparent": false }
}
```

---

## Zones  (`data/zones/`)

One JSON file per biome zone. Defines generation parameters, ambient light, and creature/structure pools.

```json
{
  "id": "barrow_depths",
  "category": "dungeon",
  "display_name": "Barrow Depths",
  "ambient_light": 0.0,
  "tags": ["undead", "dark", "cold"],
  "creatures": ["barrow_wight", "hollow_revenant", "grave_thing"],
  "structures": [
    { "id": "burial_alcove", "weight": 3 },
    { "id": "collapsed_passage", "weight": 1 }
  ],
  "loot_table": "barrow_depths"
}
```

| Field | Type | Description |
|---|---|---|
| `ambient_light` | float | Base lighting (0.0 = pitch dark, 1.0 = full daylight) |
| `tags` | list | Used to filter structure and creature pools |
| `creatures` | list | Entity IDs that can spawn in this zone |
| `structures` | list | Weighted structure ID references |
| `loot_table` | string | Key into `data/loot/` |

---

## Entities  (`data/entities/`)

Subdirectories: `creatures/`, `npcs/`, `player.json`. One JSON per entity type.

```json
{
  "id": "barrow_wight",
  "name": "Barrow Wight",
  "tile": "barrow_wight",
  "body_id": "wight",
  "fighter": {
    "power": 4,
    "defense": 0
  },
  "ai": {
    "wander_radius": 6,
    "alert_memory": 12
  },
  "perception": {
    "sight_radius": 8,
    "hearing_radius": 4,
    "sees_in_dark": true,
    "faction": "undead",
    "hostile_to": ["player", "living"]
  },
  "equipment": {
    "weapon": "barrow_claw"
  },
  "essence_modifiers": {
    "binding": 3.0
  },
  "xp_value": 25
}
```

| Field | Type | Description |
|---|---|---|
| `tile` | string | Key into `tiles.json` |
| `body_id` | string | Key into `data/bodies/` |
| `fighter` | object | `power` and `defense` values |
| `ai` | object | `wander_radius` and `alert_memory` |
| `perception` | object | Sight/hearing radii, faction, hostility list |
| `equipment` | object | Starting equipped items by slot |
| `essence_modifiers` | object | `essence_name → multiplier` damage modifiers |
| `xp_value` | int | XP awarded on kill (reserved for future use) |

---

## Items  (`data/items/`)

Subdirectories: `weapons/`, `armor/`, `consumables/`, `tools/`. One JSON per item.

### Weapon Example

```json
{
  "id": "severance_blade",
  "name": "Severance Blade",
  "tile": "blade",
  "weight": 1.2,
  "equip_slot": "weapon",
  "damage": "1d6+1",
  "essence": "severance",
  "essence_strength": 0.8,
  "qualities": ["keen", "heavy"]
}
```

### Armor Example

```json
{
  "id": "iron_helm",
  "name": "Iron Helm",
  "tile": "helmet",
  "weight": 1.5,
  "equip_slot": "armor_head",
  "armor_layers": [
    { "location": "head", "name": "iron plate", "av": 4, "material": "metal" }
  ]
}
```

### Consumable Example

```json
{
  "id": "dried_jerky",
  "name": "Dried Jerky",
  "tile": "food",
  "weight": 0.1,
  "stackable": true,
  "nutrition": 0.25,
  "on_use": "eat"
}
```

### Tool Example

```json
{
  "id": "torch",
  "name": "Torch",
  "tile": "torch_unlit",
  "weight": 0.3,
  "equip_slot": "light",
  "turns_lit": 300,
  "light_data": {
    "radius": 6,
    "color": [226, 181, 112],
    "falloff": 1.8,
    "flicker": true
  },
  "on_use": "equip_light"
}
```

### Common Item Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier |
| `name` | string | Display name |
| `tile` | string | Key into `tiles.json` |
| `weight` | float | Weight in kg |
| `stackable` | bool | Can stack in inventory |
| `equip_slot` | string | Equipment slot name (omit if not equippable) |
| `on_use` | string | Function name in `item_system.py` |
| `qualities` | list | Quality descriptor IDs from `qualities.json` |
| `description` | string | Flavor text shown in inventory |

---

## Bodies  (`data/bodies/`)

Defines hit locations for a creature body type. Used by `Fighter.initialize_from_body()`.

```json
{
  "id": "humanoid",
  "locations": [
    {
      "id": "head",
      "name": "head",
      "display": "head",
      "size": 10,
      "hp": 10,
      "impairment_threshold": 5,
      "impairment": "blinded"
    },
    {
      "id": "torso",
      "name": "torso",
      "display": "chest",
      "size": 40,
      "hp": 30
    },
    {
      "id": "left_arm",
      "name": "left arm",
      "display": "left arm",
      "size": 15,
      "hp": 12,
      "impairment_threshold": 4,
      "impairment": "left_arm_broken"
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `size` | int | Relative hit weight (higher = more likely to be hit) |
| `hp` | int | Starting HP for this location |
| `impairment_threshold` | int | HP value at which impairment triggers |
| `impairment` | string | Impairment string added to `fighter.impairments` |

---

## Loot Tables  (`data/loot/`)

One JSON per zone ID. Lists weighted item pools.

```json
{
  "zone_id": "barrow_depths",
  "item_count": { "min": 2, "max": 5 },
  "entries": [
    { "item_id": "dried_jerky",      "weight": 4 },
    { "item_id": "severance_blade",  "weight": 1 },
    { "item_id": "tallow_candle",    "weight": 3 }
  ]
}
```

---

## Structures  (`data/structures/`)

Reusable room/feature templates stamped into generated maps. Selected by zone tag matching.

```json
{
  "id": "burial_alcove",
  "tags": ["undead", "dark"],
  "width": 5,
  "height": 4,
  "grid": [
    "#####",
    "#...#",
    "#.s.#",
    "#####"
  ],
  "legend": {
    "#": "wall",
    ".": "floor",
    "s": "sarcophagus"
  }
}
```

---

## Texts  (`data/texts/`)

Found documents the player can read. Subdirectories: `lab/`, `world/`. 40+ texts total.

```json
{
  "id": "lab_note_01",
  "title": "Research Note",
  "pages": [
    {
      "lines": [
        { "text": "The binding held for three days.", "damaged": false },
        { "text": "On the fourth — ", "damaged": true }
      ]
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `damaged` | bool | If true, text renders as corrupted glyphs unless Deep Tongue words are known |

Deep Tongue words in text are automatically detected by the text reader and rendered in `font_deep` (italic night_purple).

---

## Perks  (`data/perks/`)

Player ability definitions. Currently 3 stubs.

```json
{
  "id": "the_opened_page",
  "name": "The Opened Page",
  "affinity": "the_witnessing",
  "description": "You see what others hide.",
  "effects": {
    "see_exact_hp": true
  }
}
```

---

## Deep Tongue  (`data/deep_tongue.json`)

17-word lexicon. Each entry has a `deep` (in-world word) and `translation` (English meaning).

```json
[
  { "deep": "varath", "translation": "to bind" },
  { "deep": "soel",   "translation": "vessel" }
]
```

The DataLoader keys this by `deep` field. The text reader and corruption system reference these words.

---

## Qualities  (`data/qualities.json`)

Descriptive adjectives for items.

```json
{
  "keen":   { "display": "keen",   "affects": "damage", "modifier": 0.1 },
  "rusted": { "display": "rusted", "affects": "damage", "modifier": -0.2 }
}
```

---

## Entrances  (`data/entrances/`)

ASCII layout templates for above-ground submap entry structures. 6 types. See [GENERATION.md](GENERATION.md#entrance-generation) for the list.

---

## Buildings  (`data/buildings/`)

17 placeholder town building layouts in 6 category subdirectories. Used by `town_gen.py`. See [LAYOUT_AUTHORING.md](LAYOUT_AUTHORING.md) for format details.

---

## Sprites  (`data/sprites/sprite_map.json`)

Maps tile names to sprite sheet coordinates.

```json
{
  "player":       { "sheet": "char", "col": 0, "row": 0 },
  "barrow_wight": { "sheet": "char", "col": 3, "row": 1 }
}
```

Used by `sprite_registry.py` at render time.

# Procedural Generation

Generation happens in three nested stages: world, region, and local. Each stage reads from the stage above and writes data structures used by the stage below.

All generation code lives in `roguelike/generation/`.

---

## Stage 1 — World Generation  (`world_gen.py`)

Produces the 128×128 `WorldMap` grid of `Chunk` objects.

### Passes

| Pass | What it does |
|---|---|
| 1–6 | Perlin-noise biome distribution; assigns `RegionType` to each chunk |
| 7 | SubMap generation — 1–4 submaps per chunk, weighted by biome type |
| 8 | Mark starting location (world centre = FOREST, one lab submap) |
| 9 | Generate `WorldMyth` locus (a unique named landmark) |
| 10 | Create `EdgeConnector` objects between adjacent chunks (roads, rivers, paths) |

### Biome Weights for SubMaps

| RegionType | SubMaps per chunk | Notes |
|---|---|---|
| PLAINS | 0–1 | Sparse |
| FOREST | 1–2 | — |
| SWAMP | 1–3 | Dense |
| MOUNTAIN | 2–4 | Most submaps |
| HEATH | 1–2 | — |
| TOWN | 1 | Always exactly one town submap |

### EdgeConnectors

Adjacent chunks can share connectors of type `ROAD`, `RIVER`, `PATH`, `PASS`, or `PASSAGE`. Connectors record a `position` float (0.0–1.0 along the shared edge) and optional `feature_id`.

---

## Stage 2 — Region Generation  (`region_gen.py`)

Called when the player first enters a chunk. Generates a `LocalMap` for each SubMap in the chunk.

### Dispatch

```
RegionType → generation strategy
─────────────────────────────────
TOWN        → town_gen.generate_town()
FOREST      → wilderness noise
SWAMP       → wilderness noise (wet variant)
PLAINS      → wilderness noise (open variant)
HEATH       → wilderness noise (scrubland variant)
MOUNTAIN    → BSP dungeon (cave variant)
Underground → BSP dungeon (standard)
```

### Entrance Placement

After the base map is generated, `_place_submap_entrance()` stamps an entrance structure at the SubMap's entry point. Entrance structures are defined in `data/entrances/` and placed via `entrance_gen.py`.

### Structure Seeding

After dungeon generation, `zone_structures(zone_id, rng)` from the DataLoader selects weighted structures to stamp into the map. Structures must match zone tags.

---

## Stage 3a — BSP Dungeon  (`local_gen.py`)

Binary Space Partition room generation used for dungeons and some interiors.

### Algorithm

1. Start with a rectangle covering the full 80×43 map
2. Recursively split it (alternating H/V) until leaf nodes reach minimum size (~12×12)
3. Place a room (4×4 minimum, randomized smaller than the leaf) in each leaf
4. Connect rooms with L-shaped corridors
5. Seal the perimeter with `_enforce_submap_border()` to prevent edge holes

### Post-Processing

After BSP:

- **Text placement** — 2–4 found texts placed in rooms ≥ 4×4 (tile `found_text` with `text_id` metadata)
- **Loot placement** — zone-appropriate items from `loot_table.py`
- **Creature spawning** — creatures from zone's entity list, avoiding player spawn area
- **Stair/exit placement** — `>` (descend) and `<` (ascend) tiles at connected submap boundaries

### Perimeter Enforcement

```python
_enforce_submap_border(local_map: LocalMap) -> None
```

Ensures the outermost row/column of tiles is always `wall` (non-walkable). Prevents the player from walking off the edge of the map.

---

## Stage 3b — Town Generation  (`town_gen.py`)

**Status: under revision.** Generates town maps with buildings, districts, and road networks.

### TownData Fields

```python
@dataclass
class TownData:
    name: str
    size: str                # "small" or "large"
    districts: list[str]     # district labels
    bell_state: str          # bell tower state
    is_festival: bool
    waystone_pos: tuple      # (x, y) of waystone tile
    bell_tower_pos: tuple    # (x, y) of bell tower
    buildings: list[dict]    # placed building records
    creature_spawns: list    # NPC/creature spawn points
```

### Building Categories

6 categories of building layouts in `data/buildings/`:

| Category | Example contents |
|---|---|
| `residential` | Small homes, apartments |
| `commercial` | Shops, markets |
| `civic` | Town hall, guildhall |
| `religious` | Chapels, shrines |
| `storage` | Warehouses, cellars |
| `ruins` | Collapsed structures |

---

## Layout Stamping  (`layout_stamper.py`)

Stamps a JSON layout (hand-crafted or procedural) onto an existing `LocalMap`. Used for entrance structures, special rooms, and fixed layouts.

See [LAYOUT_AUTHORING.md](LAYOUT_AUTHORING.md) for full authoring reference.

### Functions

```python
stamp_layout(
    layout: dict,
    local_map: LocalMap,
    origin_x: int,
    origin_y: int
) -> dict
    # Places ASCII grid from layout["grid"] starting at (origin_x, origin_y).
    # Returns a dict of entity spawn points from the layout's "entities" list.

stamp_layout_interior(
    layout: dict,
    local_map: LocalMap,
    origin_x: int,
    origin_y: int
) -> dict
    # Handles legend mappings (char → terrain_id), used for complex layouts.
```

### Layout JSON Format

```json
{
  "id": "barrow_entrance",
  "width": 9,
  "height": 7,
  "grid": [
    "#########",
    "#.......#",
    "#..>....#",
    "#.......#",
    "#########"
  ],
  "legend": {
    "#": "wall",
    ".": "floor",
    ">": "stair_down"
  },
  "entities": [
    { "char": "B", "entity_id": "barrow_wight", "x": 4, "y": 2 }
  ]
}
```

---

## Entrance Generation  (`entrance_gen.py`)

Places above-ground entrance structures at submap entry points on surface maps.

### Entrance Types (6)

| ID | Visual | Notes |
|---|---|---|
| `barrow_mound` | Low earth mound with stone door | Common in heath/plains |
| `drowned_threshold` | Submerged archway | Swamp zones |
| `sunken_ruin` | Partially collapsed stonework | Any |
| `overgrown_gatehouse` | Vine-covered gate | Forest zones |
| `rock_face_cut` | Cut directly into cliff | Mountain zones |

Each entrance type is defined in `data/entrances/` as a JSON layout with its own ASCII grid and legend.

---

## World Mythology  (`world/world_myth.py`)

Generates a procedural mythology for the world — names, events, and the location of the narrative locus.

The `WorldMyth` object is created during world gen and stored on `WorldMap`. It provides:

- A named locus (unique landmark on the overmap)
- Myth excerpts displayed in the status bar panel
- Narrative fragments referenced in found texts

---

## Name Generation  (`world/name_gen.py`)

Three-register procedural name generator. Names are assembled from template patterns defined in `data/names.json`.

```python
generate_name(register: str, rng: Random) -> str
    # register: "place", "creature", "item", "person"
```

Registers select from different phoneme pools and structural templates, producing distinct-sounding names per category.

# Rendering Pipeline

All rendering code lives in `roguelike/rendering/`. The entry point is `renderer.py`, which is called once per frame from the main engine loop.

---

## Render Modes

Set `RENDER_MODE` in `roguelike/config.py`.

| Mode | Value | Backend |
|---|---|---|
| ASCII | `"ascii"` | tcod tileset — Unicode characters from `tiles.json` |
| Sprite | `"sprite"` | pygame surfaces — 1-bit sprite sheets with color tinting |

Both modes share the same UI panels, message log, and status bar. Only the main game viewport differs.

---

## Frame Passes  (`renderer.py`)

Each frame runs three ordered passes:

### Pass 1 — Ghost Pass

Draws the last known position of actors the player can no longer see. Uses a dimmed version of the actor's tile color. Updated by the engine whenever an actor moves into or out of FOV.

### Pass 2 — Tile + Entity Pass

For every tile in the viewport:
1. If `explored` but not `visible` — draw the tile in a darkened/desaturated color
2. If `visible` — draw the tile at full brightness, multiplied by `light_map[x, y]`
3. Draw items on the tile
4. Draw actors on the tile

Light map values are float RGB triplets blended additively from all active `LightSource` components.

### Pass 3 — UI Pass

Draws the fixed chrome around the game view:

- **Left panel** — main viewport (80 columns × 43 rows)
- **Right panel** — message log (`MSG_PANEL_W = 300px`)
- **Bottom panel** — status bar (`STATUS_BAR_H = 120px`)

UI draw calls come from `engine/ui.py`. Panel borders use 9-slice textures from `ui_registry.py`.

---

## Tile Registry  (`tile_registry.py`)

Loads `data/tiles.json` at startup and exposes tile properties for both render modes.

### Per-tile Properties

| Field | Type | Description |
|---|---|---|
| `char` | `str` | Unicode character (ASCII mode) |
| `color_fg` | `[R,G,B]` | Foreground color |
| `color_bg` | `[R,G,B]` | Background color |
| `sprite_col` | `int` | Column in sprite sheet (Sprite mode) |
| `sprite_row` | `int` | Row in sprite sheet (Sprite mode) |
| `sprite_sheet` | `str` | `"char"` or `"obj"` |

---

## Sprite Registry  (`sprite_registry.py`)

Manages 1-bit sprite sheets and applies color tinting at draw time.

### Sprite Sheets

| File | Grid | Contents |
|---|---|---|
| `lofi_1bit_char.png` | 24×21, 8×8 px tiles | Characters, creatures, player |
| `lofi_1bit_obj.png` | 12×27, 8×8 px tiles | Objects, terrain, items |

Sprite coordinates are stored in `data/sprites/sprite_map.json` as `(col, row)` pairs keyed by tile name.

### Color Tinting

Each sprite is white-on-black. At draw time:

1. Extract the 8×8 sub-surface for the sprite
2. Apply `color_bg` as a solid rect beneath the sprite
3. Apply `color_fg` via `BLEND_RGBA_MULT` on the white pixels
4. Multiply by the tile's `light_map` value for dynamic lighting

---

## UI Registry  (`ui_registry.py`)

Draws 9-slice bordered panels using pre-made PNG textures.

### Panel Designs (12 total, "Hexany" series)

| Panel | Tint color | Used for |
|---|---|---|
| `weathered_temple` | steel_blue | Primary game border |
| `slate_dark` panel | slate_dark | Message log |
| `midnight` panel | midnight | Status bar |
| `slate_mid` panel | slate_mid | Popups (inventory, examine) |

### 9-Slice Drawing

```python
draw_panel(
    surface: pygame.Surface,
    panel_id: str,
    x: int, y: int,
    width: int, height: int,
    tint: tuple = None
) -> None
```

Slices the texture into 9 regions (4 corners, 4 edges, 1 centre) and scales them to fill the target rectangle without distorting corners.

---

## Biome Icons  (`biome_icons.py`)

Procedural 64×64 icons for each biome type, drawn with `pygame.draw` primitives, seeded so they are deterministic per biome.

### Biome Types

`forest`, `swamp`, `mountain`, `heath`, `plains`, `town`, `dungeon`

Icons are cached after first generation. Displayed in the status bar's chunk info section.

```python
get_biome_icon(biome_id: str, seed: int) -> pygame.Surface
```

---

## UI Layout  (`engine/ui.py`)

### Status Bar (bottom, `STATUS_BAR_H = 120px`)

Left column:
- Chunk name and biome icon
- WorldMyth excerpt (one line)
- SubMap depth and entrance type (if in a submap)

Right column:
- Player HP bar (colored by fraction: green → yellow → red)
- Corruption state label
- Hunger and thirst state labels
- Time of day and moon phase

### Message Log (right, `MSG_PANEL_W = 300px`)

- Displays the 12 most recent messages
- Older messages fade to a lower alpha
- Stacked messages show `×N` suffix
- Message colors match `MessageLog` type (see [SYSTEMS.md](SYSTEMS.md#message-log))

---

## Display Configuration  (`engine/display_config.py`)

Loads fonts and configures the pygame window at startup.

### Fonts (Junicode family)

| Attribute | Style | Size |
|---|---|---|
| `font_large` | Regular | 20px |
| `font_bold_large` | Bold | 20px |
| `font_normal` | Regular | 16px |
| `font_small` | Regular | 14px |
| `font_tiny` | Regular | 12px |
| `font_italic` | Italic | 16px |
| `font_deep` | Italic | 16px, night_purple |

`font_deep` is used exclusively for Deep Tongue words in the text reader overlay.

### Window Layout

```
┌──────────────────────────────────┬───────────────┐
│                                  │               │
│         Game Viewport            │  Message Log  │
│          (80 × 43 tiles)         │   (300 px)    │
│                                  │               │
├──────────────────────────────────┴───────────────┤
│                  Status Bar (120 px)              │
└───────────────────────────────────────────────────┘
```

# Engine Systems Reference

Core systems that run the game loop. All live in `roguelike/engine/`.

---

## Turn Queue  (`turn_queue.py`)

Simple round-robin scheduler. All actors (player + all monsters) are added on map load; removed on death or map exit.

```python
add(actor: Actor) -> None
remove(actor: Actor) -> None
next() -> Actor       # returns next actor whose turn it is
```

The engine calls `next()` until it gets the player, then waits for player input. When input is received it completes the player's action and calls `next()` again, processing all other actors until the player's turn comes back.

---

## World Time  (`world_time.py`)

Tracks an in-world clock. One game turn = 1 in-world minute.

### Constants

| Constant | Value | Notes |
|---|---|---|
| `TURNS_PER_HOUR` | 60 | — |
| `TURNS_PER_DAY` | 1440 | 24 hours |
| `TURNS_PER_PHASE` | 4320 | 3 days per moon phase |
| `TURNS_PER_CYCLE` | 34560 | 24 days per full lunar cycle |

### Properties

```python
hour: float           # 0.0–24.0
hour_int: int
is_day: bool          # 6:00–20:00
is_night: bool
time_string: str      # "14:32"

sun_intensity: float  # 0.0–1.0 on a sine arc, 6am–8pm
sun_color: tuple      # RGB, warmer at dawn/dusk

moon_phase_index: int        # 0–7
moon_phase_name: str
moon_intensity: float        # 0.0–1.0; full moon = 1.0
moon_color: tuple

day_number: int
status_string: str    # "Day 3, 14:32"
moon_string: str      # "Full Witness (day 9)"
```

### Moon Phases (8 total, 3 days each)

0. Dark Seal
1. Thin Knife
2. Half Truth
3. Swelling Eye
4. Full Witness
5. Dimming Eye
6. Half Lie
7. Waning Knife

### Ambient Light

```python
get_ambient_light(zone_ambient: float, is_outdoor: bool) -> tuple[float, tuple]
    # Returns (intensity, color).
    # Outdoor: blends sun and moon contributions.
    # Indoor: returns zone_ambient with neutral color.
```

### Methods

```python
advance(turns: int = 1) -> None
```

---

## Message Log  (`message_log.py`)

Stacking colored message system. Identical consecutive messages are merged with a count suffix (`×3`).

### Message Colors

| Method | Color | Purpose |
|---|---|---|
| `add(text, color)` | custom | Generic |
| `add_important(text)` | old_gold | Key events |
| `add_danger(text)` | blood_rose | Damage, death |
| `add_world(text)` | mid_green | World/environmental |
| `add_corrupt(text)` | night_purple | Corruption effects |
| `add_whisper(text)` | slate_mid | Deep tongue whispers |

### Methods

```python
recent(n: int) -> list[Message]    # latest n messages
advance_turn() -> None             # increments internal turn counter
```

### Message Fields

```python
@dataclass
class Message:
    text: str
    color: tuple[int,int,int]
    turn: int
    count: int     # stacked duplicates; display as "text ×count" if > 1
```

---

## AI System  (`ai_system.py`)

Thin loop that iterates all non-player actors each round and calls `AI.take_turn(...)`.

```python
update_all(entities, player, local_map, log, rng, world_time, engine) -> None
```

Actors without an `ai` component are skipped. Dead actors are skipped (engine removes them on next tick).

For detailed AI state-machine logic see [COMPONENTS.md](COMPONENTS.md#ai).

---

## Item System  (`item_system.py`)

Handles all item interactions. The engine dispatches to these functions from the inventory UI.

### Functions

```python
equip_toggle(item: Item, engine: Engine) -> None
    # Equip if unequipped, unequip if already equipped.
    # Calls _apply_armor_to_fighter or _remove_armor_from_fighter for armor items.

eat(item: Item, engine: Engine) -> None
    # Consumes the item. Calls needs.eat(item.nutrition).

drink(item: Item, engine: Engine) -> None
    # Consumes the item. Calls needs.drink(item.hydration).

read(item: Item, engine: Engine) -> None
    # Opens the text_reader overlay with item.text_id.

heal_minor(item: Item, engine: Engine) -> None
    # Calls fighter.heal(item.heal_amount).

equip_light(item: Item, engine: Engine) -> None
    # Activates item's light_source component; adds to light slot.
```

### Armor Helpers

```python
_apply_armor_to_fighter(item: Item, fighter: Fighter) -> None
    # Prepends item's armor layers to the relevant fighter locations.

_remove_armor_from_fighter(item: Item, fighter: Fighter) -> None
    # Strips all layers contributed by this item. Guards against duplicates.
```

---

## Save Manager  (`save_manager.py`)

Serializes and deserializes the entire game state to `saves/` as JSON.

### ChunkCache

When the player descends into a SubMap, the surface `LocalMap` (and its entities) is stored in `ChunkCache`. When the player ascends, the cache restores it. This allows surfaces to remain persistent between visits.

```python
class ChunkCache:
    store(submap_id: str, local_map: LocalMap, entities: list) -> None
    restore(submap_id: str) -> tuple[LocalMap, list] | None
```

### Save Contents

| Key | Type | Notes |
|---|---|---|
| `world_map` | dict | Full 128×128 chunk grid, explored flags, SubMap definitions |
| `local_map` | dict | Current tile array + explored bitmask |
| `player` | dict | All component data serialized |
| `entities` | list | All non-player actors/items on current map |
| `world_time` | dict | Turn count |
| `world_myth` | dict | Narrative state |
| `chunk_cache` | dict | Stored surfaces keyed by submap_id |
| `current_submap_id` | str | Active submap or None |
| `surface_return_x/y` | int | Return position when ascending |

### Methods

```python
save(engine: Engine) -> None       # write to saves/save.json
load(engine: Engine) -> bool       # return True if save found and loaded
has_save() -> bool
delete_save() -> None
```

---

## Loot Tables  (`loot_table.py`)

Weighted random loot generation, dispatched by submap zone type.

### Usage

```python
generate_loot(zone_id: str, data: DataLoader, rng: Random) -> list[Item]
```

Loot table JSON lives in `data/loot/`. Each table entry has `item_id` and `weight` fields. The function draws N items (determined by zone tier) from the weighted pool.

---

## Visual Events  (`visual_events.py`)

Queued effects that play over subsequent frames without blocking the game loop.

### Event Types

- **Damage number** — floating number at tile position, fades over ~30 frames
- **Screen shake** — offset the viewport by `(magnitude * dx, magnitude * dy)`, decays each frame

### Methods

```python
queue_damage_number(x, y, amount, color) -> None
queue_screen_shake(magnitude, dx, dy) -> None
process(renderer) -> None    # called each frame by the render loop
```

---

## Data Loader  (`data_loader.py`)

Loads all JSON data files at startup. Accessed everywhere via `engine.data`.

### Loaded Collections

| Attribute | Source | Keyed by |
|---|---|---|
| `tiles` | `data/tiles.json` | tile name |
| `terrain` | `data/terrain.json` | terrain name |
| `qualities` | `data/qualities.json` | quality id |
| `zones` | `data/zones/` | zone id |
| `entities` | `data/entities/` | entity id |
| `items` | `data/items/` | item id |
| `loot` | `data/loot/` | zone id |
| `structures` | `data/structures/` | structure id |
| `entrances` | `data/entrances/` | entrance id |
| `texts` | `data/texts/` | text id |
| `perks` | `data/perks/` | perk id |
| `bodies` | `data/bodies/` | body id |
| `deep_tongue` | `data/deep_tongue.json` | deep word |
| `buildings` | `data/buildings/` | grouped by category |

### Query Methods

```python
structures_with_tags(tags: list[str]) -> list
    # Returns structures containing ALL of the given tags.

structures_with_any_tag(tags: list[str]) -> list
    # Returns structures containing ANY of the given tags.

zones_by_category(category: str) -> list
    # Returns zone dicts matching the given category string.

zone_structures(zone_id: str, rng: Random) -> list
    # Returns weighted-shuffled structure list for a zone.
```

---

## Text Reader  (`text_reader.py`)

Full-screen overlay for reading found documents (`data/texts/`).

### Features

- **Multi-page:** arrow keys / PgUp/PgDn to scroll
- **Damaged glyphs:** random glyph substitution for damaged spans; recovers as player learns Deep Tongue words
- **Deep Tongue:** words from the lexicon render in italic `night_purple` font
- **Learning:** reading a Deep Tongue word the player hasn't seen triggers `language.learn()`

### Opening

```python
engine.open_text_reader(text_id: str) -> None
```

Called by `item_system.read()`.

---

## Look Mode  (`look_mode.py`)

Examine mode activated with `;` or `x`. A cursor moves around the map; pressing Enter (or looking at an entity) opens an info popup.

### Popup Contents

- Entity name and tile
- HP bar — only shown if `_can_see_exact_hp()` returns True
- Fighter stats (power, defense)
- Equipped items
- Active impairments
- Corruption state (for actors that have a Corruption component)

```python
_can_see_exact_hp(entity, engine) -> bool
    # True if: DEBUG_MODE, player has true_sight,
    #          or player has the_opened_page perk.
```

---

## Inventory Screen  (`inventory_screen.py`)

Full inventory UI opened with `I`.

### Per-Item Display

- Item name and quality descriptor
- Weight
- If weapon: damage dice, essence type and pip count
- If armor: coverage slots, AV value, material
- If consumable: nutrition/hydration/heal values
- Equipped flag and slot name

### Actions

| Key | Action |
|---|---|
| `E` | Equip / unequip |
| `D` | Drop to ground |
| `Enter` / `U` | Use item |
| `Esc` | Close |


-we need to add a critical hit system, natural for perk tie-in, needs special callout
-[future settings option when we implement that screen] we should ultimately be able to enable damage numbers as text callouts


