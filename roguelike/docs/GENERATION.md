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
