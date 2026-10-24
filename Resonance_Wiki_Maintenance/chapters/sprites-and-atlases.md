# Sprites, atlases, and asset registration

Use this chapter when you want to change how an existing tile looks, add artwork for a new item or creature, or introduce another sprite sheet. All paths below are relative to the repository root unless explicitly described as game-relative. The audited revision is `4d7a7892e1afffb8d872ed4a8fd442984d14e7d5`.

## The current artwork pipeline

The default game uses **full-colour sprites**. `DisplayConfig.use_sprite_tint` starts as `False`; `RENDER_MODE` ends as `"sprite"` in `roguelike/config.py`. The currently registered sheet cells are declared as 16 × 16 pixels. At the default zoom of 2, a world tile occupies 32 × 32 screen pixels. The older instructions describing an exclusively white, one-bit, 24-pixel pipeline are historical.

A sprite's appearance and an object's behavior have separate owners:

| What you want to change | File or field |
|---|---|
| Pixels, colours, transparency | The PNG in `roguelike/assets/sprites/` |
| Which atlas cell represents a named sprite | `roguelike/data/sprites/sprite_map.json`, inside `tiles` |
| Sheet filename and cell dimensions | The same file, inside `sheets` |
| ASCII character and ASCII colours | `roguelike/data/tiles.json`, inside its `tiles` object |
| Which named sprite an item or actor uses | Its definition's `tile` field |
| Whether a terrain cell is passable or see-through | `roguelike/data/terrain.json` |
| Whether an overlay has an interaction or blocks player movement | `roguelike/data/decoratives.json` and the corresponding implemented consumer |

`SpriteRegistry.get()` returns the original colour artwork. `get_tinted()` multiplies the artwork by a tint, which is useful for white-on-transparent art. Switching the global tint flag changes the whole renderer; it is not a per-sheet art-style setting. In the default full-colour world view, editing `tiles.json.color_fg` does not recolour the pixels in your PNG.

Sources: [sprite registry](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/rendering/sprite_registry.py), [display configuration](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/display_config.py), [renderer](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/rendering/renderer.py).

## Replace the appearance of an existing object

1. Find the object's definition and read its `tile` value. For terrain, start with its terrain ID: the world renderer normally resolves the terrain ID directly rather than treating every `terrain.json.tile` value as a universal alias.
2. Find that key under `sprite_map.json.tiles`.
3. Choose the new cell on an existing sheet. Columns and rows start at zero, at the top-left.
4. Change only `sheet`, `col`, and `row` in that mapping. Reuse the existing key when only the artwork is changing; do not rename identity-bearing item or creature IDs.
5. Restart the game to reload the registry and PNGs. Check the object in the map and in its relevant popup or inventory view.

For example, the current `player` mapping is:

```json
{"sheet": "creatures", "col": 0, "row": 0}
```

This value belongs at the existing `tiles.player` key in `sprite_map.json`; it is not a complete replacement for the JSON file. The separate `floor` mapping currently uses `terrain`, column 20, row 1.

**Shared-art consequence:** changing pixels in an atlas cell changes every mapping that uses that cell. Adding a distinct sprite key pointing to the same cell does not create a separate copy of its artwork.

## Add a new sheet

Prepare a regular PNG grid with no outer margin or spacing between cells. Use transparent backgrounds for overlays, actors, and items where the floor must show through. Full-colour art is supported. White-on-transparent is required only when you specifically want multiply-tinted artwork.

For the least surprising behavior, use **16 × 16 cells for new sheets**, matching the current grid. The loader accepts different cell dimensions, but the renderer takes its common grid size from the first loaded sheet while individual draw calls use the selected sprite's dimensions. Mixed dimensions therefore are not a promise of consistent alignment. Do not use per-tile `tile_w`/`tile_h` overrides as a way to crop arbitrary rectangles: extraction still uses the owning sheet's dimensions.

1. Save your image as `roguelike/assets/sprites/my_objects.png`.
2. Add this entry inside the existing `sheets` object:

```json
"my_objects": {
  "file": "assets/sprites/my_objects.png",
  "tile_w": 16,
  "tile_h": 16
}
```

3. Add a key inside the existing `tiles` object:

```json
"my_reliquary": {"sheet": "my_objects", "col": 0, "row": 0}
```

4. Point the new item's or creature's `tile` field at `my_reliquary`; use the appropriate content chapter for the remaining behavioral fields and acquisition route.
5. Add a matching `my_reliquary` entry inside `roguelike/data/tiles.json` → `tiles` for ASCII support. A complete tile-definition value is:

```json
{
  "ascii": "!",
  "color_fg": [228, 210, 170],
  "color_bg": [6, 6, 8],
  "color_fg_dark": [40, 35, 30],
  "color_bg_dark": [4, 5, 9]
}
```

6. Restart. The startup log should list the sheet under its registered ID. A loaded PNG alone does not prove the referenced cell is valid or that the item is obtainable in play.

The file path in a sheet record is **relative to the game working directory**, normally `roguelike/`, which is why it starts with `assets/` rather than `roguelike/assets/`.

## Find the correct coordinates

The repository includes two Pillow utilities. In the commands below, set `$AssetPython` to the full path of a separate Python interpreter that already has Pillow installed; the game baseline does not include Pillow. They produce images in your **current working directory** and do not edit `sprite_map.json`.

From the repository root:

```powershell
& $AssetPython "Sprite Reference Generator/sprite_ref_2.py" "roguelike/assets/sprites/terrain.png" 16 16
```

This produces `terrain_PRO_SCHEMATIC.png`, preserving the source grid and labelling each cell `column : row`. It is the easier choice for the 24-column × 24-row terrain and objects sheets.

For paginated linear reference sheets:

```powershell
& $AssetPython "Sprite Reference Generator/sprite_ref.py" "roguelike/assets/sprites/creatures.png" 16 16
```

This labels a flattened index. Convert that index with:

```text
column = index % source_columns
row    = index // source_columns
```

For the 16-column creatures sheet, index 35 means column 3, row 2. The printed index equals the column only on a single-row sheet. The first script defaults to 12-pixel cells and the second to 16; supply both dimensions explicitly. Pillow is required by these optional reference generators and is not listed in `requirements-baseline.txt`.

Sources: [paginated reference generator](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/Sprite%20Reference%20Generator/sprite_ref.py), [coordinate-grid generator](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/Sprite%20Reference%20Generator/sprite_ref_2.py).

## Registered sheets at this revision

The image dimensions below were read from the PNGs and the registry was loaded with Pygame under SDL's dummy video driver. This checks asset geometry and loading; it does not certify the composition of every rendered screen.

| Sheet ID | PNG dimensions | Declared cell | Usable grid / note | Mapping count |
|---|---|---|---|---:|
| `terrain` | 384 × 384 | 16 × 16 | 24 columns × 24 rows | 236 |
| `objects` | 384 × 384 | 16 × 16 | 24 × 24 | 9 |
| `creatures` | 256 × 320 | 16 × 16 | 16 × 20 | 17 |
| `pixel` | 3200 × 16 | 16 × 16 | 200 × 1; loaded but no current mapping uses it | 0 |
| `hexany_creatures` | 5120 × 16 | 16 × 16 | 320 × 1; loaded but no current mapping uses it | 0 |
| `urizen` | 123600 × 12 | 16 × 16 | **Mismatch:** image is shorter than one declared cell | 1 |

There are 263 registered sprite keys. The `wall_pillar` key is the sole Urizen mapping and crops a 16 × 16 rectangle from that 12-pixel-high image. Treat it as an existing asset-registration discrepancy, not a template for new artwork. Correcting the registration requires choosing the intended geometry and rechecking affected coordinates; this handbook does not silently change the game.

Source: [current sprite map](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/data/sprites/sprite_map.json).

## Live remapping and its limit

With `DEBUG_MODE=True`, F12 opens a remapping prompt. Enter four space-separated values, for example:

```text
floor terrain 20 1
```

This changes the in-memory mapping. It does **not** save the change to JSON. After finding a useful coordinate, record it in `sprite_map.json` yourself. The registry has a `save_map()` method, but the F12 handler does not call it. Do not mistake a successful live preview for a persisted edit.

Source: [F12 handler and remap execution](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/debug.py).

## Troubleshooting artwork

| Symptom | Check |
|---|---|
| Correct shape, wrong colour in default sprite mode | Edit the PNG. `color_fg` does not drive full-colour map artwork. |
| Unexpected black or white square | Inspect the PNG's alpha channel. The game does not automatically remove a background. |
| A question-mark placeholder | A registered atlas crop may be completely transparent. `sprite_placeholder` is used for blank cells when available. |
| Nothing drawn | Check the sprite key, sheet load warnings, path, and coordinates. An unknown key or unloaded sheet is not universally replaced by the placeholder. |
| Sprite appears at the wrong position or size | Check for mixed cell sizes or per-mapping dimensions. The current common grid assumes 16 × 16. |
| New ASCII tile is ignored | Place it under the existing `tiles` wrapper. Sibling keys outside that wrapper are ignored. |
| Colours seem dim outside sight | Memory rendering has its own dimming logic; it is not necessarily the `color_fg_dark` value used by ASCII mode. |

`TileRegistry` accepts either a one-character `ascii` string or an integer Unicode codepoint in `char`. Keep the complete colour fields shown above. Three existing vine ASCII records (`vine_growth`, `vine_eyestalk`, `vine_spore_vent`) sit outside the wrapper at this revision and are excluded by the loader. Their existence in the file is not proof that they are registered.

Source: [tile registry](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/rendering/tile_registry.py).
