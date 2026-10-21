> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](owner/STATUS.md). This banner does not resolve open design decisions.

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
