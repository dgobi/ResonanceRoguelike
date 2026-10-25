> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](owner/STATUS.md). This banner does not resolve open design decisions.

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
    # Activates the carried item's light source in offhand.
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

- **Authored pages:** Left/Right changes pages and resets visual scroll.
- **Overflow:** Up/Down scrolls a line; PgUp/PgDn scrolls a viewport; Home/End
  reaches the beginning/end. The fixed footer shows controls and progress.
- **Wrapping:** actual font and glyph widths determine visual rows. Paragraphs,
  explicit breaks, long tokens, mixed spans, inscriptions and the alphabet remain
  accessible on constrained displays, including 480 by 320.
- **Identity:** recovery keys remain `(text_id, authored_page, authored_span)`.
  Wrapping and scrolling never change them. Known words show their translation;
  unknown Deep Tongue words show their existing phoneme glyphs.
- **Learning and time:** ordinary inventory reading costs its existing opening
  turn. A text's `teach_words` action happens once per text ID. Rendering and
  navigation spend no turns and do not teach, recover, reroll or pulse.
- **Close:** Esc, Enter or keypad Enter. When opened from inventory, the
  underlying inventory remains available after closing the reader.

### Opening

```python
engine.text_reader.open_text(text_def: dict) -> None
```

Called by `ItemSystem._use_read()` and existing world interactions.

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
| `Enter` / keypad `Enter` | Use item / equip |
| `Esc` | Close |

### Finite treatment (G15)

Herbal Dressing uses `heal_minor` with data-driven `heal_amount: 12`. In `I`,
select the dose and press Enter, keypad Enter or E. A living injured fighter
recovers the actual missing HP up to that amount; feedback states the actual
restoration. The exact selected instance is consumed once, then the ordinary
inventory action advances AI/effects/survival. Existing inventory movement-debt
semantics and the broader HP-display policy remain unchanged. The item detail
description states its up-to-12-HP, single-use effect.

Full health, missing/dead fighter or stale ownership rejects treatment without
healing, consumption or time. Closing inventory is free. The narrow
`heal_minor` rejection handling does not reinterpret other handlers' `False`
returns: reading and equipment still take their established action.

Newly selected `apothecary_b` medicine chests retain the existing reagent rolls
and independently add one dose through `apothecary_b_treatment`. Search with E,
then select the dose in the normal container prompt. Capacity rejection leaves
that same item in the chest. Search, travel and load do not restock it. Existing
saved apothecary selections/visited contents retain their original owners and
dependencies. No starter gift, food/water, exposure change, XP or empty vessel is
attached to treatment.

### Equipment and carrying (G12)

Use the Revelation Lens and each existing satchel with the ordinary inventory
equip command; use again to remove it. The Lens occupies `weapon`; Q Reveals an
existing creature weakness/resistance on contact, and R uses its existing True
Strike and six-turn cooldown. Its damage uses `1d4` plus `damage_bonus: 2`.

`Inventory.current_weight` is the derived carrying load. Item weights stay raw
and unchanged. The equipped satchel applies its definition's reductions once:
leather 10% across categories; herbalist 30% to Consumables/Preparations;
component 35% to Components and 20% to Tools. UI categories and all acquisition,
take-all, exchange/output and encumbrance checks share that calculation.
An exchange projects the equipment remaining after its exact consumed items.

Removing, dropping or switching a bag may leave the player overweight. Those
actions and supported loads preserve every possession. Further acquisition must
fit the resulting effective limit; rejected items remain with their source and
feedback gives the effective load. Reequip a carried bag or drop possessions to
recover. Bags do not contain another inventory owner.

Old and new selected equipment with a missing/null use handler resolves to the
established equip route at ordinary use. Untouched definitions and visited
instances retain their generation dependency/fingerprint identity. Explicit
non-null custom handlers and unrelated mutable fields remain intact.

### Empty-crate wood (G14)

`E` opens adjacent interaction selection. Target an empty crate: `Enter` keeps
its ordinary search behavior; `X` opens an explicit dismantling confirmation.
`Enter` confirms, `Esc` cancels. Only decor ID `crate` with its matching live
container owner and an actually empty item list qualifies. Decorative-only
crates, other furniture and nonempty containers cannot be dismantled, including
contents hidden behind a stale looted flag.

An owned cutting tool of tier 1 or higher must be equipped in weapon/offhand.
Confirmation rechecks that capability, the exact scene/container owner and
unchanged source state, visible adjacent reach and diagonal corners. Success
retains the tool, removes both crate owners and leaves one existing wood bundle
on the same floor cell, preserving terrain and unrelated objects. This costs
one ordinary action through the existing clock/debt path. Cancellation, stale
prompts and output failures cost nothing and produce nothing. A full pack
still permits dismantling; later pickup uses normal capacity/ownership checks.

This is one runtime rule, with no content-definition, recipe, generation-plan
or save-schema changes. Visited crates remain until explicitly dismantled;
removed crates and floor output use the existing mutable-scene persistence.
The shed's existing floor wood plus the recovered bundle pay for Field Campfire.

### Crafting roles and heat (G12)

`C` retains the existing recipe list and ingredient-choice interface. Materials
in `components` or `requires_single_item` are exact physical instances, spent
only on successful commitment. `tools` are physical capabilities kept after
the work. `requires_ambient` describes environmental conditions, never a supply
of consumed material. A reusable item's keywords do not supply free fuel.
Reusable valuables are excluded from automatic material selection; an explicit
material choice marked **spent** incurs the actual cost and detaches equipment
and light safely. Cancelled, stale, invalid-placement and rejected-output work
preserves ingredients.

Field Campfire spends two `wood_bundle` instances and keeps a cutting tool.
Placement creates an unlit fire and costs its ordinary action; the existing
interaction ignites it with another action. A live, equipped offhand flame can
satisfy portable burning requirements. Carried, extinguished, expired or
displaced lights cannot. Passive processing additionally requires a nearby
stationary lit campfire and a valid placement: drying beside it, cooking on it.
A torch alone is not a drying/steeping station.

The existing musk route uses the Heath Stalker's tier-2 butchery yield (the gland
is a possible yield), dries one real gland beside stationary fire for the
authored ten turns, then leaves the pellet on the floor for pickup. Placement's
first phase counts toward those ten. Its normal targeting/throw path spends
one pellet on a legal confirmation, creates the existing radius-three
disruption for six AI phases, and then normal behavior resumes. Cancellation
keeps the pellet. Disruption is not a guaranteed flee or smell-specific rule.
Existing active/hot aging and cold-map freezing remain in effect.
