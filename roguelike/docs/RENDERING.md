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
