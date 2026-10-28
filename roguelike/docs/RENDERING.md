> **Arc A status:** Historical source retained below. Creative intent remains a design reference; technical claims need the [current implementation and authority map](owner/STATUS.md). This banner does not resolve open design decisions.

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

### Proportional game typography

`engine/typography.py` defines the production contract. The single active profile
is `data/display/typography.json`: fixed `id: "game_typography"`, integer
`version: 1`, and all thirteen string assignments below. Values are exact TTF
basenames directly inside `assets/Fonts`. Unknown metadata has no runtime effect.
Workbench edits this existing file through its ordinary validation/review route.

| Attribute / field | Default resource | Nominal size | Shared consumers |
|---|---|---:|---|
| `font_ui_large` | `Junicode.ttf` | 22 | Reader and menu headings |
| `font_ui_normal` | `Junicode.ttf` | 18 | Reader prose/footer and several menus |
| `font_ui_small` | `Junicode.ttf` | 16 | Perk requirements, inventory and map details |
| `font_ui_tiny` | `Junicode.ttf` | 14 | Message log, combat formulae and HUD |
| `font_ui_italic` | `Junicode-Italic.ttf` | 18 | Italic menu and lexicon text; chosen face replaces the role without synthesis |
| `font_ui_bold` | `Junicode-Bold.ttf` | 18 | Inventory, perk and lexicon titles; chosen face replaces the role without synthesis |
| `font_ui_bold_large` | `Junicode-Bold.ttf` | 22 | Prominent menu text; chosen face replaces the role without synthesis |
| `font_deep` | `Junicode-Italic.ttf` | 18 | Known proportional Deep Tongue text; unknown-language glyphs are generated separately |
| `font_callout_damage` | `Junicode-Bold.ttf` | 13 | Floating damage numbers; small alias |
| `font_callout_status` | `Junicode-Bold.ttf` | 12 | Floating status effects |
| `font_callout_creature` | `Junicode-Bold.ttf` | 11 | Creature sounds; tiny alias |
| `font_callout_crit` | `Junicode-Bold.ttf` | 18 | Critical hit numbers |
| `font_callout_levelup` | `Junicode-Bold.ttf` | 21 | Level and perk-point announcements |

`CALLOUT_FONTS.small` aliases damage; `tiny` aliases creature. Sizes and aliases
are fixed. Choosing another face for an italic/bold role replaces the face; no
synthetic italic/bold is added. Deep Tongue's proportional font is separate from
procedurally generated unknown-language glyphs.

`DisplayConfig.init()` resolves and loads the complete assignment before screens
cache fonts and metrics. **Saved changes apply at next game initialization.**
No active-profile registry, per-save copy or live replacement exists. An absent
profile uses the complete defaults without creating a file. A present malformed,
unsupported or unusable profile warns and falls back to the complete defaults;
it never rewrites the profile or saves. Missing/corrupt default resources cause a
clear startup failure. Selected fonts use actual file bytes through
`pygame.font.Font`; system fonts are never substituted. Diagnostics distinguish
requested face, resolved resource and fallback. Preview candidates fail strictly.

Font resolution rejects absolute/traversing names, links/reparse points, missing
or corrupt resources, names over 128 characters, files over 16 MiB, and discovery
over 64 TTFs / 256 directory entries. No OS discovery, downloads or asset writes.

Functional coverage checks use `pygame.freetype.Font(..., ucs4=True).get_metrics`
on the same bytes; SDL_ttf `Font.metrics` alone can report missing-glyph boxes.
All roles require printable ASCII. Additional role repertoires come from current
consumers: normal/deep reader markers and bold lexicon titles require `—`; small
perk/inventory/map details require `≥ — · •`; tiny log prefixes, scroll indicator
and combat formulae require `› ↑ → × −`. These are bounded interface checks,
not universal Unicode coverage. Authored prose remains byte-exact.

The defaults already lack normal `✓` and tiny `○ ●`; decorative storm symbols
are also outside the blocking gate. Their absence is a warning, not a redesign
or rejection of defaults. Other authored characters may be missing. Generated
`[DAMAGED]` text now excludes optional archaic/phonetic characters absent from the
chosen normal face, keeping the existing ASCII fallback. Thus its generated
alphabet can change by face; authored pages, span identities, language knowledge,
damage/recovery and time behavior do not change.

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
