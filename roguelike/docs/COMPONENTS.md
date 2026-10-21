> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](owner/STATUS.md). This banner does not resolve open design decisions.

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
