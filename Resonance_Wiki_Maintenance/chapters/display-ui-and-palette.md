# Display, fonts, colour, and UI tuning

The game opens in a resizable 1280 × 720 Pygame window. Its default world art is full-colour sprites at a 32 × 32 pixel display size. UI text uses separate Junicode font objects. Zooming the map is therefore different from enlarging the interface text.

## Which settings actually take effect?

| Setting | Current location / value | How to use it |
|---|---|---|
| Default render mode | Final `RENDER_MODE = "sprite"` in `roguelike/config.py` | Change the final assignment to `"ascii"` for ASCII startup; restart. |
| Default map zoom | Final `ZOOM_LEVEL = 2` in the same file | Runtime `=`/`+` zooms in, `-` zooms out in local play. Setter clamps to 1–8. |
| Sprite tint | `DisplayConfig.__init__`: `use_sprite_tint = False` | Code-level whole-renderer choice. False preserves PNG colour; True multiplies artwork by tint. |
| ASCII glyph sheet | `FONT_PATH`, `FONT_COLUMNS=32`, `FONT_ROWS=8` | Default image supplies 10 × 10 glyphs, yielding 20 × 20 at zoom 2. |
| Right message width | `MSG_PANEL_W = 300` | Screen pixels; affects remaining map width. |
| Bottom status height | `STATUS_BAR_H = 120` | Screen pixels; used directly in the frame layout. |
| Common content inset | `UI_PANEL_INSET = 24` | Screen pixels; many UI layouts use this constant. |
| Overmap sidebar | `OVERMAP_SIDEBAR_W = 320` | Screen pixels. |
| Debug tools | `DEBUG_MODE = True` | Enables debug overlay and changes some key routing, including F5/F9. Consult the controls chapter. |
| Initial window size | `Engine.run()` literal `(1280, 720)` | There is no JSON window-size preference demonstrated in this path. |
| Window caption | `Engine.run()` literal `"Roguelike"` | The `TITLE` constant is not used by this call. |
| Frame cap | `Engine.run()` calls `clock.tick(60)` | Editing the unused `FPS = 20` constant does not change this cap. |

`config.py` contains repeated assignments. Python uses the last one. Changing the earlier `RENDER_MODE = "ascii"` while leaving the later sprite assignment intact has no effect.

There are font discovery, font-switching, and display serialization methods in `DisplayConfig`, but the current Engine has no exposed general options menu using them, and the save route does not persist these display preferences. Do not follow old prose promising an in-game font menu or persistent zoom setting. `FONT_TYPE` is retained metadata; the glyph lookup currently uses the TCOD character map rather than dispatching to a distinct CP437 implementation.

Sources: [config](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/config.py), [display configuration](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/display_config.py), [window and input implementation](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/engine.py).

## Make map art larger or smaller

Try the runtime zoom keys first. They change the number of world cells visible in the available viewport; they do not change the logical dimensions of a local map. For a persistent startup choice, edit the final `ZOOM_LEVEL` assignment and restart.

The logical `MAP_WIDTH=80` and `MAP_HEIGHT=43` are generation dimensions, not viewport pixel settings. Do not change them to solve a display-size problem. Doing so can affect structures, plans, coordinates, and saves and needs generation-specific validation.

Different registered sprite sizes are not automatically normalized to one common display cell. Keep new artwork compatible with the current 16-pixel grid unless you are deliberately changing the renderer and verifying all related coordinate paths.

## Make UI text larger

The actual sizes are in `DisplayConfig.init()`:

| Attribute | Font | Size argument in pixels |
|---|---|---:|
| `font_ui_large` | Junicode regular | 22 |
| `font_ui_bold_large` | Junicode bold | 22 |
| `font_ui_normal` | Junicode regular | 18 |
| `font_ui_bold` | Junicode bold | 18 |
| `font_ui_italic` | Junicode italic | 18 |
| `font_deep` | Junicode italic placeholder | 18 |
| `font_ui_small` | Junicode regular | 16 |
| `font_ui_tiny` | Junicode regular | 14 |
| Damage callout | Junicode bold | 13 |
| Status callout | Junicode bold | 12 |
| Creature callout | Junicode bold | 11 |
| Critical callout | Junicode bold | 18 |
| Level-up callout | Junicode bold | 21 |

1. Change only the needed size or font path.
2. Restart so every UI component gets the new font objects.
3. Inspect long inventory names, equipment columns, the craft requirements area, long found-text pages, examination popups, and the bottom status bar.
4. Check both your ordinary window size and a smaller window you actually use. Larger fonts can exceed fixed-height regions even when individual glyphs look good.

Use `font.get_linesize()` or measured text dimensions in code rather than assuming the point/size argument equals the rendered line height. The retained `UI-TEXT-HEIGHT` issue remains outside the completed combat/generation arcs; these instructions do not imply that every existing screen is robust to arbitrary font increases.

Source: [font initialization and helper methods](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/display_config.py), [documented deferred UI boundary](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/docs/owner/D_STATE.md).

## Colour ownership

`roguelike/engine/palette.py` is the current code palette. It defines AAP-64 values and semantic aliases such as `UI_TEXT_BRIGHT`, `MSG_DANGER`, and `TERRAIN_WALL`. The older Punolite naming and RGB tables are not the authority for current code. Some old comments still say Punolite.

| Change | Best starting point |
|---|---|
| UI text/border/message colour | The relevant semantic alias or the screen's local mapping to palette constants |
| Full-colour sprite appearance | PNG pixels |
| ASCII terrain colour | `tiles.json.tiles.<id>.color_fg` and `color_bg` |
| ASCII remembered terrain colour | `color_fg_dark` and `color_bg_dark` |
| Tint-mode world art | `tiles.json` foreground plus lighting/tint path |
| Deep Tongue UI colour | `DEEP_TONGUE_COLOUR`, currently `(162, 120, 218)` |
| Weather visuals | Weather definitions plus the renderer/particle consumer for the named effect |

Changing a palette constant does not rewrite literal RGB arrays in JSON or pixels in a PNG. Conversely, the `PALETTE` metadata in `tiles.json` is not a live replacement for `engine/palette.py`.

### Remembered tiles and lighting

ASCII rendering uses the tile registry's dark colour fields. Sprite rendering has separate logic: tint-mode remembered terrain derives reduced values from the ordinary colour, while default full-colour art is multiplied by a fixed memory brightness. `_draw_sprite()` uses the red channel of its supplied brightness tuple for all channels, so a tuple described in a comment as a cool colour cast does not produce independent RGB tinting there. Full-colour visible terrain also does not use `light_map` in the same way as tint mode.

Treat these as current implementation limits when adjusting darkness or introducing coloured light. A new `light_color` field alone is not proof of a visibly coloured pool in the default world renderer.

Source: [palette](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/palette.py), [map, decorative, and sprite draw paths](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/rendering/renderer.py).

## Add or change a panel frame

`UIRegistry.load()` discovers PNG files in `roguelike/assets/ui/` by filename stem. Existing artwork is designed around 96 × 96 sources with a 15-pixel border region. The registry converts pixels whose RGB sum exceeds 15 into an opaque tint mask, makes the remaining mask transparent, and draws a separate fill. It does not preserve a full-colour border illustration unchanged.

For a compatible new frame:

1. Start from an existing panel asset with the intended border geometry.
2. Preserve the source dimensions and border region while editing the ornamental mask.
3. Save a uniquely named PNG under `assets/ui/`.
4. Pass its filename stem as `panel_id` at the intended screen's draw call.
5. Restart and inspect the frame at the actual panel dimensions, especially narrow panels and corners.

The actual call signature is:

```python
engine.ui_registry.draw_panel(
    surface,
    panel_rect,
    "weathered_temple",
    tint_color=UI_BORDER,
    fill_color=UI_BACKGROUND,
    fill_alpha=255,
    border_scale=2,
)
```

At `border_scale=2`, the source's 15-pixel corner region becomes 30 screen pixels. Use the current implementation and the actual screen's layout instead of copying the old UI guide's 12-pixel-border assumption. `pygame.Rect.inflate(-18, -18)` removes 18 pixels from the total width/height—9 on each side—not 18 per side. When you need an inset of `pad` on all sides, use `inflate(-2 * pad, -2 * pad)` or construct the interior explicitly.

Source: [panel loader and drawing implementation](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/rendering/ui_registry.py), [inventory's current layout](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/inventory_screen.py).

## Principles to preserve when changing UI code

The old `UI_RULES.md` remains useful as design intent: keep a single content area, reserve hints outside scrolling content, keep selection highlights inside the list, derive columns from available space, and keep the selected row visible. Its exact numeric examples and simplified `draw_panel` call are not a current API specification.

Use separate draw calls for equipment badges and item names, and measure/truncate long text before it reaches adjacent columns. Clip scrolling content without clipping the hint row. Restore surface clipping after drawing. Keep input handling behind the existing modal/death guards; a visual change should not introduce a second mutation or turn-advance path.

For verification, use app-local or headless component rendering where available, then inspect the resulting images. A dummy-driver render checks drawing and layout only; it does not prove the live OS event loop or every resize path. `tools/render_baseline_screens.py` is a historical component-render utility that creates a copied baseline game through `baseline.prepare`; it should not be presented as the current preferred main-checkout workflow without adapting its harness.

Sources: [historical UI rules](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/docs/UI_RULES.md), [historical component-render utility](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/tools/render_baseline_screens.py), [repository working rules](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/AGENTS.md).
