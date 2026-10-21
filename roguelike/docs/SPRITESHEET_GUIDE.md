> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](owner/STATUS.md). This banner does not resolve open design decisions.

# Spritesheet Guide
## Adding New Sheets and Assigning Tiles to Everything

This guide assumes the engine already supports multiple sheets
(sprite_map.json has "sheets" + "tiles" structure, SpriteRegistry
reads tile_w/tile_h per sheet). If that setup isn't done yet,
follow the session notes for the exact code changes first.

---

## How the System Works

sprite_map.json has two sections:

```json
{
  "sheets": {
    "obj":    {"file": "assets/sprites/lofi_1bit_obj.png",  "tile_w": 8,  "tile_h": 8},
    "char":   {"file": "assets/sprites/lofi_1bit_char.png", "tile_w": 8,  "tile_h": 8},
    "urizen": {"file": "assets/sprites/urizen_onebit_tileset__v2d0-Sheet.png",
               "tile_w": 12, "tile_h": 12}
  },
  "tiles": {
    "floor":       {"sheet": "obj",    "col": 2,   "row": 5},
    "cobblestone": {"sheet": "urizen", "col": 342, "row": 0},
    "bog_wraith":  {"sheet": "urizen", "col": 887, "row": 0}
  }
}
```

The engine:
1. Loads each sheet PNG at startup
2. Looks up tile_id in "tiles" → gets sheet + col + row
3. Extracts the sprite at (col * tile_w, row * tile_h)
4. Scales to display size (always 24px regardless of source size)
5. Tints white pixels with color_fg from tiles.json

Color comes from tiles.json. Shape comes from sprite_map.json.
These are independent — same sprite can appear in different colors
by having two tile_ids pointing to the same col/row with different
color_fg values in tiles.json.

---

## Adding a New Spritesheet

### Requirements
- PNG format
- White sprites on TRANSPARENT background (RGBA — not white background)
- Tiles packed left to right, no gaps between them
- All tiles the same size

### Step 1 — Place the file
Copy the PNG to: `assets/sprites/yoursheet.png`

### Step 2 — Register in sprite_map.json "sheets"
```json
"yoursheet": {
  "file":   "assets/sprites/yoursheet.png",
  "tile_w": 12,
  "tile_h": 12
}
```
Use whatever tile dimensions the sheet actually uses.
No code changes needed — SpriteRegistry reads this at startup.

### Step 3 — Verify it loaded
Run `python main.py`. Terminal will print:
```
Loaded sheet 'yoursheet': assets/sprites/yoursheet.png
SpriteRegistry: N tiles across M sheets
```
If it prints a warning, check the file path exactly — case sensitive.

---

## Finding Tile Coordinates

Use the urizen_ref_XXXX_XXXX.png reference sheets.
Each shows 500 tiles with their index number printed below.

For Urizen (single-row sheet):
  col = the index number shown
  row = 0 (always)

For multi-row sheets:
  col = horizontal position counting from 0 (left)
  row = vertical position counting from 0 (top)

---

## Applying a Tile to a Terrain Type

Terrain types are stamped onto the map by generators and layout
stampers. They appear in building layout JSON legends, generation
code, and the three data files below.

### All three files must be updated:

**1. sprite_map.json — add to "tiles":**
```json
"cobblestone": {"sheet": "urizen", "col": 342, "row": 0}
```

**2. tiles.json — add color and ASCII fallback:**
```json
"cobblestone": {
  "ascii":        ",",
  "color_fg":     [88, 88, 96],
  "color_bg":     [20, 20, 28],
  "color_fg_dark":[18, 18, 22],
  "color_bg_dark":[8,  8,  12]
}
```
color_fg tints the white sprite pixels. Use Punolite palette colors
(see CLAUDE.md palette section).
color_fg_dark / color_bg_dark are used for memory tiles (explored, unlit).

**3. terrain.json — add walkability:**
```json
"cobblestone": {
  "walkable":    true,
  "transparent": true,
  "description": "Fitted stone, worn smooth by years of passage."
}
```

### Using the new terrain in a building layout

Building layouts use a "legend" that maps ASCII characters to
terrain names. Any character can map to any terrain:

```json
{
  "id": "house_small_a",
  "width": 10, "height": 8,
  "legend": {
    "#": "wall",
    ".": "floor",
    "c": "cobblestone",
    "s": "worn_stone",
    "+": "door_closed",
    " ": null
  },
  "layers": [
    "##########",
    "#........#",
    "#........#",
    "#...cc...#",
    "#........#",
    "#........#",
    "#........#",
    "####.#####"
  ]
}
```

null means no tile is stamped — the tile remains whatever base
terrain was placed by the generator (usually grass or cobblestone).

---

## Applying a Tile to an Item

### Step 1 — Add to sprite_map.json "tiles"

Name the key by what it looks like, not the item name.
Multiple items can share the same sprite key:
```json
"blade_single":  {"sheet": "urizen", "col": 1205, "row": 0},
"blade_heavy":   {"sheet": "urizen", "col": 1206, "row": 0},
"knife_short":   {"sheet": "urizen", "col": 1208, "row": 0},
"lantern_iron":  {"sheet": "urizen", "col": 743,  "row": 0},
"herb_bundle":   {"sheet": "urizen", "col": 892,  "row": 0},
"flask_clay":    {"sheet": "urizen", "col": 512,  "row": 0}
```

### Step 2 — Add to tiles.json
```json
"blade_single": {
  "ascii":        "/",
  "color_fg":     [140, 130, 120],
  "color_bg":     [7,   12,  29 ],
  "color_fg_dark":[40,  38,  35 ],
  "color_bg_dark":[5,   8,   18 ]
}
```
No terrain.json entry needed for items.

### Step 3 — Set "tile" field in item JSON
In `data/items/weapons/crude_blade.json`:
```json
{
  "id":   "crude_blade",
  "name": "a crude blade",
  "tile": "blade_single",
  ...
}
```

---

## Applying a Tile to a Creature

Identical process to items. The sprite appears on the map and
in the examine popup.

### Step 1 — Add to sprite_map.json "tiles"
```json
"bog_wraith_sprite":    {"sheet": "urizen", "col": 887, "row": 0},
"hollow_knight_sprite": {"sheet": "urizen", "col": 654, "row": 0},
"grave_thing_sprite":   {"sheet": "urizen", "col": 421, "row": 0}
```

### Step 2 — Add to tiles.json
Use the creature's palette color as color_fg:
```json
"bog_wraith_sprite": {
  "ascii":        "W",
  "color_fg":     [63, 160, 164],
  "color_bg":     [7,  12,  29 ],
  "color_fg_dark":[20, 50,  52 ],
  "color_bg_dark":[5,  8,   18 ]
}
```

### Step 3 — Set "tile" in creature JSON
```json
{
  "id":   "bog_wraith",
  "tile": "bog_wraith_sprite",
  ...
}
```

---

## Annotating Items for Future Functionality

When adding content whose mechanics aren't implemented yet,
annotate it so it's caught in future passes. The engine
ignores unknown JSON fields, so this is safe.

### In any JSON file — use a "TODO" field:
```json
{
  "id":    "resonance_bowl",
  "name":  "a resonance bowl",
  "tile":  "bowl_stone",
  "on_use":"examine",
  "TODO":  "Tier 3 alchemy — fixed station. Required for resonance-essence preparations. See CLAUDE.md alchemy section."
}
```

For creatures with abilities not yet implemented:
```json
{
  "id":           "pale_herder",
  "TODO_ability": "Tier 3 — EstablishedAI archetype. Herds creatures. Territory-based. See CLAUDE.md AI archetypes."
}
```

For terrain features with planned mechanics:
```json
"waystone": {
  "ascii":   "W",
  "color_fg":[100, 100, 112],
  "TODO":    "Tier 3 — resonance emitter. Passive corruption in range. Bell magic anchor."
}
```

### Track in docs/FUTURE_CONTENT.md:
```markdown
## Items — Alchemy (Tier 3)
- resonance_bowl  data/items/tools/resonance_bowl.json
- alembic         data/items/tools/alembic.json

## Creatures — New AI Archetypes (Tier 3)
- pale_herder     data/entities/creatures/pale_herder.json

## Terrain — Mechanics Pending
- waystone        resonance emitter
- street_lamp     light emitter terrain feature
- bell            active hazard
```

---

## Quick Reference

### New terrain tile — touch these three files:
1. sprite_map.json "tiles" → sheet, col, row
2. tiles.json → color_fg, color_bg, ascii, dark variants
3. terrain.json → walkable, transparent, description

### New item or creature sprite — touch these:
1. sprite_map.json "tiles" → sheet, col, row
2. tiles.json → color_fg, color_bg, ascii, dark variants
3. Entity JSON → "tile": "your_sprite_key"

### New spritesheet — touch only this:
1. sprite_map.json "sheets" → file, tile_w, tile_h
(No code changes.)

---

## Troubleshooting

**Black square in game:**
The PNG is black-on-white, not white-on-transparent.
The tinting system multiplies onto white pixels — black pixels
stay black regardless of color_fg.
Fix: open in GIMP, Colors → Color to Alpha → white → export PNG.

**Wrong sprite showing:**
Check col value against the reference sheet. Off-by-one is common.
Try col-1 and col+1 to confirm.

**Correct shape, wrong color:**
Edit color_fg in tiles.json.
[255, 255, 255] = no tint (pure white sprite).
Use Punolite palette values from CLAUDE.md.

**Crash on startup mentioning sheet name:**
File path in sprite_map.json "sheets" doesn't match actual
filename exactly. Check case, underscores, and extension.

**Item or creature has no sprite in examine popup:**
The "tile" field in the entity JSON doesn't match any key
in sprite_map.json "tiles". Check spelling exactly.

**New terrain renders as void/black in towns:**
The terrain name is in sprite_map.json and tiles.json but
missing from terrain.json. Add walkable/transparent/description.
Or the terrain name used in the building layout legend doesn't
match the key in terrain.json — check spelling.

# NOTE
By default the engine will convert the sprite name into the display name of the tile (used in Look Mode). However a separate display_name field can be used to define a different one in terrain.json.