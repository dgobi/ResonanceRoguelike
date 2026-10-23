> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](owner/STATUS.md). This banner does not resolve open design decisions.

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
