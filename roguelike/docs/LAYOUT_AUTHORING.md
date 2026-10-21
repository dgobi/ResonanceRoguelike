# Layout Authoring Guide

This document explains how to create hand-crafted map layouts for the game.
Layouts are JSON files read by the layout stamper system at generation time.
No code changes are needed to add new layouts — just create the file and
reference it in the appropriate place.

---

## Two Types of Layout

### Surface Layouts (`type: "surface_layout"`)
Used for hand-crafted surface features stamped into procedurally generated
chunks. Currently used for entrance structures (`data/entrances/`).
Stamped at an interior position within a larger generated map.

### SubMap Layouts (`type: "submap_layout"`)
Used for fully hand-crafted underground spaces. The entire local map is
built from the layout rather than procedural generation.
Currently used for the starting laboratory (`data/layouts/starting_lab.json`).

---

## File Location

```
data/layouts/          SubMap layouts (full underground spaces)
data/entrances/        Surface entrance structures
data/rooms/            Special rooms (Tier 3 — not yet implemented)
data/features/         Small stamped features (Tier 3 — not yet implemented)
```

---

## The Layout File Format

```json
{
  "id": "my_layout",
  "type": "submap_layout",
  "description": "Human-readable description. Not used by the engine.",
  "width": 60,
  "height": 35,
  "legend": {
    "#": "wall",
    ".": "floor",
    "f": "flagstone",
    "w": "worn_stone",
    "+": "door_closed",
    "D": "door_open",
    "^": "stairs_up",
    ">": "stairs_down",
    "T": "tree",
    "~": "water",
    " ": null
  },
  "layers": [
    "############################################################",
    "#..........................................................#",
    "... one string per row, all the same length as 'width' ..."
  ],
  "special_tiles": [
    {"x": 5, "y": 7, "type": "item", "item_id": "lab_note", "text_id": "some_text_id"},
    {"x": 10, "y": 4, "type": "body", "name": "remains of someone"},
    {"x": 3, "y": 3, "type": "inscription", "text_id": "some_inscription_id"}
  ],
  "player_start": {"x": 5, "y": 7},
  "stairs_up": {"x": 5, "y": 27},
  "connection_point": {"x": 6, "y": 0},
  "spawn_offset": {"x": 6, "y": 4},
  "edges": ["north"]
}
```

---

## The Layers Array

The `layers` array is the heart of the layout. Each entry is a string
representing one row of the map, read top-to-bottom. The length of every
string must equal `width` exactly.

```
Row 0 is the TOP of the map (northernmost).
Row H-1 is the BOTTOM (southernmost).
Column 0 is the LEFT (westernmost).
Column W-1 is the RIGHT (easternmost).
```

Each character in a row is looked up in the `legend` dict. The legend
maps characters to terrain type names. Terrain type names must exist in
`data/terrain.json` to get correct walkable/transparent behaviour.

The null value (`" ": null`) means "leave existing terrain unchanged."
Use space for areas outside your layout boundary — the surrounding map
terrain will show through.

---

## The Legend

You define the character-to-terrain mapping yourself. Use any single
printable character. Common conventions:

```
#   wall          (impassable, opaque)
.   floor         (walkable, transparent)
f   flagstone     (walkable, transparent — research/formal areas)
w   worn_stone    (walkable, transparent — details, benches, features)
+   door_closed   (walkable after interaction, opaque until opened)
D   door_open     (walkable, transparent — already forced open)
^   stairs_up     (walkable, transparent)
>   stairs_down   (walkable, transparent)
T   tree          (impassable, opaque)
~   water         (walkable, transparent)
r   rock          (impassable, opaque — natural stone)
g   gravel        (walkable, transparent)
,   gravel        (alternate gravel character)
```

Any character not in the legend is treated as a warning and skipped.
The space character should always map to null (leave terrain unchanged).

---

## Special Tiles

Special tiles place items, bodies, or other entities at specific positions.
All coordinates are layout-relative (0,0 = top-left of layers array).

**Item placement:**
```json
{
  "x": 15, "y": 8,
  "type": "item",
  "item_id": "lab_note",
  "text_id": "lab_note_primary_a",
  "note": "Optional human note — ignored by engine"
}
```
`item_id` must exist in `data/items/`. If the item has `on_use: "read"`,
the `text_id` field sets which text opens when the item is used.

**Body placement:**
```json
{
  "x": 55, "y": 4,
  "type": "body",
  "name": "remains of R."
}
```
Places a corpse item at the position with the given name.

**Inscription placement** (future — not yet fully implemented):
```json
{
  "x": 3, "y": 3,
  "type": "inscription",
  "text_id": "lab_inscription_entry"
}
```

---

## Key Position Fields

**`player_start`** — Where the player spawns when entering this submap.
Coordinates are layout-relative. The engine offsets by the stamp origin.
```json
"player_start": {"x": 5, "y": 7}
```

**`stairs_up`** — Where the stairs_up tile is placed. Player presses `<`
here to return to the surface.
```json
"stairs_up": {"x": 5, "y": 27}
```

**`connection_point`** (entrance layouts only) — The tile that aligns
to the map edge. Used by the stamper to position the entrance correctly.
```json
"connection_point": {"x": 6, "y": 0}
```

**`spawn_offset`** (entrance layouts only) — Where the player spawns
when entering from this entrance. Relative to connection_point.
```json
"spawn_offset": {"x": 6, "y": 4}
```

**`edges`** (entrance layouts only) — Which map edge this layout faces.
The stamper rotates the layout for other edges.
```json
"edges": ["north"]
```

---

## Dimensions

### SubMap layouts (data/layouts/)
The layout is centred on the 80×43 local map.
Maximum usable area: **78×41** (leaving 1 tile border on each side).
Recommended sizes:

| Use case | Width | Height |
|---|---|---|
| Small chamber | 20–30 | 15–20 |
| Medium dungeon level | 40–55 | 25–35 |
| Large dungeon level | 60–70 | 35–40 |
| Starting lab (current) | 60 | 35 |

Always leave a 1-tile wall border on all sides. The engine fills
everything outside the stamped area with wall tiles.

### Entrance layouts (data/entrances/)
These are small structures stamped INTO a larger surface map.
Maximum size: **20×20** (larger will overlap chunk edges).
Typical sizes: 7–13 wide, 5–10 tall.

The `connection_point` must be on the edge facing the map boundary.
The structure sits INSIDE the surface chunk, not at the edge.

---

## Terrain Types Reference

All terrain types must exist in `data/terrain.json`. Current types:

| Name | Walkable | Transparent | Notes |
|---|---|---|---|
| wall | No | No | Standard dungeon wall |
| floor | Yes | Yes | Standard dungeon floor |
| flagstone | Yes | Yes | Formal/worked stone floor |
| worn_stone | Yes | Yes | Aged stone — floors and details |
| gravel | Yes | Yes | Loose stone, outdoor areas |
| cobblestone | Yes | Yes | Paved road/town surfaces |
| grass | Yes | Yes | Outdoor ground |
| tree | No | No | Forest |
| water | Yes | Yes | Swamp/river (walkable for now) |
| rock | No | No | Natural stone/mountain |
| door_closed | Yes* | No | *Walkable after player opens it |
| door_open | Yes | Yes | Already opened |
| stairs_up | Yes | Yes | Press < to ascend |
| stairs_down | Yes | Yes | Press > to descend |
| mud | Yes | Yes | Swamp ground |
| ash | Yes | Yes | Burned area |

*To add a new terrain type: add it to `data/terrain.json` with
walkable/transparent values, add it to `data/tiles.json` with colors,
add it to `data/sprites/sprite_map.json` with sprite coordinates.
Then it can be used in any legend.*

---

## Step-by-Step: Creating a New SubMap Layout

**1. Decide on dimensions.**
For a medium dungeon level, use 50×30. For a large area, 60×35.
Keep it smaller than the 78×41 maximum.

**2. Sketch the rooms on paper or in a text editor.**
Draw the rooms using # for walls and . for floor. Think about:
- How many rooms? How are they connected?
- Where does the player enter (player_start)?
- Where do they exit (stairs_up)?
- What floor materials suggest the history of the space?

**3. Create the JSON file.**
```
data/layouts/my_new_level.json
```
Start with this template:
```json
{
  "id": "my_new_level",
  "type": "submap_layout",
  "description": "What this place is.",
  "width": 50,
  "height": 30,
  "legend": {
    "#": "wall",
    ".": "floor",
    "f": "flagstone",
    "w": "worn_stone",
    "+": "door_closed",
    "^": "stairs_up",
    " ": null
  },
  "layers": [],
  "special_tiles": [],
  "player_start": {"x": 5, "y": 5},
  "stairs_up": {"x": 5, "y": 24}
}
```

**4. Fill in the layers array.**
Each row is a string of exactly `width` characters.
The array must have exactly `height` entries.
Row 0 is the top, Row H-1 is the bottom.

**5. Add special_tiles.**
For each item, note or body you want placed, add an entry to
`special_tiles` with layout-relative x,y coordinates.

**6. Reference the layout from a SubMap.**
In `generation/world_gen.py` or wherever the SubMap is created,
set `layout_id = "my_new_level"` on the SubMap object.
The generator will use your layout instead of BSP.

**7. Test.**
Run the game, descend into the submap, press F3 to reveal the full map.
Verify the layout looks as intended. Adjust the JSON and delete saves
to test again.

---

## Tips and Common Mistakes

**Every row must be exactly `width` characters.**
Count carefully. A row that is 1 character too short will silently
clip the rightmost tiles. A row that is too long will error.

**Use a monospace font when editing.**
The layout will only look right in a monospace font. VS Code, Notepad++,
Vim — any editor with monospace display works. Do not use Word or
a proportional font.

**The outer border should always be walls.**
The stamper doesn't add a border automatically. If your outermost row
or column is floor, it will be walkable at the edge of the submap,
which looks wrong and may cause issues.

**Leave a path between all walkable areas.**
If a room is fully enclosed with no door, the player can't reach it.
Always test that every area you want the player to access is reachable
from player_start.

**Special tile coordinates are layout-relative.**
They are NOT absolute map coordinates. The engine adds the stamp origin
(the centering offset) at generation time. If your player_start is at
x=5, y=7 in the layout, and the layout is centred on an 80×43 map,
the actual map position is approximately x=15, y=11 — but you only
ever think in layout coordinates.

**The `note` field in special_tiles is ignored by the engine.**
Use it as a comment to remind yourself what the tile is for.

**Doors need floor tiles on both sides.**
A door at position (12,7) needs floor at (11,7) and (13,7) to be
passable. If either adjacent tile is wall, the door is effectively
a dead end.

---

## Future: Layout Editor Tool

The current workflow (editing JSON in a text editor) works but is tedious
for large layouts. A planned Tier 4 tool would provide:

- Visual grid editor with click-to-paint terrain
- Live preview of how the layout renders in-game
- Drag-and-drop special tile placement
- Validation (row length, connectivity check, reachability)
- Direct save to `data/layouts/`

Until that tool exists, the text editor workflow with this guide is
the primary authoring method.

# NOTE:
Varied tiles: using prefix varied_ for the tile name in a layout will cause the engine to insert tiles from the FUNCTIONAL_VARIANTS list found in decor.py
For just cosmetic swaps the engine searches DECOR_TABLE for a matching tile name.