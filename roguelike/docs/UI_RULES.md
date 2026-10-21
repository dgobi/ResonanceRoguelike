# UI Rules -- Non-Negotiable

Read this before touching any file in engine/*_screen.py, rendering/*_screen.py,
or any UI render path. These rules exist because UI overlap has recurred more than
five times. They are not guidelines. They are constraints.

---

## The Panel Contract

Every UI panel has exactly one content rect. It is calculated once:

    content_rect = panel_rect.inflate(-PADDING_H, -PADDING_V)

where PADDING_H and PADDING_V account for both the 9-slice border width AND an
inner breathing gap. Use PANEL_BORDER = 12 (border tile width) and PANEL_GAP = 6
(inner gap). So PADDING_H = PADDING_V = PANEL_BORDER + PANEL_GAP = 18.

All content -- sprites, text, icons, bars, buttons -- draws within content_rect.
Nothing draws outside content_rect. Not even by one pixel.

---

## The Hint Row

Every panel that has instructions at the bottom reserves a hint row:

    HINT_ROW_H = font_height + 8   # 4px above, 4px below
    hint_row_top = content_rect.bottom - HINT_ROW_H
    hint_text_y = hint_row_top + (HINT_ROW_H - font_height) // 2

Scrollable content clips at hint_row_top - 2. It never enters the hint row.
The hint row is always visible. It is never scrolled out of view.
Draw a 1px separator line at hint_row_top in UI_BORDER colour.

---

## The Highlight Rectangle

The selection highlight is a filled rect in UI_PANEL_DARK at full opacity (255).
Never use an alpha surface for the highlight. Never use a colour with alpha < 200.
The highlight rect is inset from the panel border:

    highlight_rect = Rect(content_rect.left, row_top, content_rect.width, row_height)

It never extends beyond content_rect.left or content_rect.right.
It never extends beyond content_rect.top or hint_row_top.

---

## Column Layout

Every panel with columnar content defines named column constants derived from
content_rect. No hardcoded pixel offsets. No local offset calculations inside loops.

Standard inventory column pattern:
    COL_SPRITE  = content_rect.left + 2
    COL_BADGE   = content_rect.left + 36
    COL_NAME    = content_rect.left + 58
    COL_WEIGHT  = content_rect.right - 50

The badge "[E]" and the item name are ALWAYS separate render calls.
They are NEVER concatenated into a single string.
Name text is truncated with "..." before it reaches COL_WEIGHT - 4.

---

## Scroll Invariant

The following invariant must hold at all times in any scrollable list:

    scroll_offset <= selected_index < scroll_offset + visible_rows

Enforce after every key event that changes selected_index or scroll_offset.
Add in DEBUG_MODE:
    assert 0 <= selected_index - scroll_offset < visible_rows

The scroll indicator "^" (more above) and "v" (more below) draw at the right
edge of the list area alongside the first/last visible row. They never replace
a list row. They never draw in the hint row.

---

## Panel Construction

All panels use draw_panel() from rendering/ui_registry.py. No exceptions.
draw_panel(surface, rect, tint_colour) handles the 9-slice border.
The rect passed to draw_panel is the OUTER panel rect, not the content rect.
Content draws within content_rect = panel_rect.inflate(-18, -18).

Available panel styles (border PNG files in assets/ui/):
    weathered_temple  -- default, used for inventory/health screens, text reader (default)
    thorny_growth     -- craft screen
    polis_sanctuary   -- perk screen, lexicon screen
    ziggurat          -- stele inscription text reader
    (add others here as they are assigned)

When assigning a new panel style, add it to this list.

---

## Checklist Before Committing Any UI Change

- [ ] All content within content_rect
- [ ] Hint row always visible, never scrolled
- [ ] Highlight rect fully opaque, within content_rect, above hint_row_top
- [ ] Column positions named constants derived from content_rect
- [ ] Badge and name never concatenated
- [ ] Scroll invariant enforced with DEBUG_MODE assertion
- [ ] draw_panel() called for every panel
- [ ] No hardcoded pixel values not derived from panel dimensions
- [ ] Tested at multiple window sizes if resizable
