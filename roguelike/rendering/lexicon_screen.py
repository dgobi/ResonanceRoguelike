# rendering/lexicon_screen.py
# UI RULES: read docs/UI_RULES.md before modifying this file.
"""
Lexicon screen — L key. Shows learned deep tongue words grouped by category.
Panel style: polis_sanctuary. Only shows learned words — never exposes unlearned.
"""
from __future__ import annotations
import pygame
from config import UI_PANEL_INSET
from typing import TYPE_CHECKING
from engine.palette import *
from rendering.glyph_gen import (
    GLYPH_SIZE_INLINE, GLYPH_SIZE_DETAIL,
    draw_word as _draw_glyph_word,
    word_pixel_width as _glyph_word_pw,
    get_phonemes_for_word as _get_phonemes,
)

if TYPE_CHECKING:
    from engine.engine import Engine
    from engine.display_config import DisplayConfig


_CATEGORIES = [
    "cosmic",
    "body",
    "time",
    "place",
    "people",
    "action",
    "essence",
    "number",
    "ominous",
    "legacy",
]

_CATEGORY_LABELS = {
    "cosmic":  "Cosmic",
    "body":    "Body",
    "time":    "Time",
    "place":   "Place",
    "people":  "People",
    "action":  "Action",
    "essence": "Essence",
    "number":  "Number",
    "ominous": "Ominous",
    "legacy":  "Legacy",
}

_CATEGORY_DESCRIPTIONS = {
    "action":   "Words of doing. Verbs of the deep tongue — what the builders caused to happen.",
    "cosmic":   "Words of structure. The deep ones named the laws of the world before naming the world itself.",
    "body":     "Words of flesh. Clinical, precise. The builders studied living tissue as they studied stone.",
    "people":   "Words of being. Roles, states, categories of person — the deep ones classified before they named.",
    "time":     "Words of duration. The builders experienced time as accumulation, not passage.",
    "essence":  "Words of property. The six essences and their interactions — the deepest technical vocabulary.",
    "number":   "Words of quantity. The builders counted in geometric progressions.",
    "ominous":  "Words of warning. The register of inscriptions — commands, prohibitions, consequences.",
    "legacy":   "The oldest words. Pre-systematic, pre-grammar. These came first.",
    "place":    "Words of location. The builders named every threshold, depth, and boundary.",
}


def _wrap_text(font: pygame.font.Font, text: str, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        test = line + (" " if line else "") + word
        if font.size(test)[0] <= max_w or not line:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


class LexiconScreen:
    """
    Two-panel lexicon screen. L opens/closes.
    LEFT: category list + learned words  RIGHT: word detail with glyph
    """

    BG       = DEEP_NOTHING
    BORDER   = VOID_PURPLE
    TITLE    = SPIRIT_BLUE
    TEXT     = WORN_STONE
    DIM      = DEEP_EARTH
    SELECTED = RESONANCE_GOLD
    DEEP_C   = DEEP_TONGUE_COLOUR
    LABEL_C  = STONE_BLUE
    HDR_C    = VOID_PURPLE

    def __init__(self) -> None:
        self.open:            bool      = False
        self._font_title:     pygame.font.Font | None = None
        self._font_normal:    pygame.font.Font | None = None
        self._font_small:     pygame.font.Font | None = None
        self._font_bold:      pygame.font.Font | None = None
        self._font_italic:    pygame.font.Font | None = None
        self._row_height:     int       = 20
        # Navigation
        self._flat:           list      = []   # (word_id_or_None, is_hdr, label)
        self.selected:        int       = 0
        self.scroll:          int       = 0
        self._collapsed:      set[str]  = set()

    def init(self, display: "DisplayConfig") -> None:
        self._font_title  = getattr(display, "font_ui_bold", None) or display.font_ui_normal
        self._font_normal = display.font_ui_normal
        self._font_small  = display.font_ui_small
        self._font_bold   = getattr(display, "font_ui_bold_large", None) or display.font_ui_large
        self._font_italic = getattr(display, "font_ui_italic", None) or display.font_ui_normal
        self._row_height  = max(self._font_normal.get_linesize(), GLYPH_SIZE_INLINE) + 4

    def toggle(self) -> None:
        self.open     = not self.open
        self._flat    = []
        self.selected = 0
        self.scroll   = 0

    # ------------------------------------------------------------------ #
    #  Flat list
    # ------------------------------------------------------------------ #

    def _build_flat(self, engine: "Engine") -> list:
        flat = []
        lang = getattr(engine.player, "language", None)
        if lang is None:
            return flat
        all_words = engine.data.deep_tongue

        for cat in _CATEGORIES:
            learned_in_cat = [
                wid for wid in lang.known_deep_words
                if all_words.get(wid, {}).get("category") == cat
            ]
            if not learned_in_cat:
                continue
            learned_in_cat.sort()
            label = _CATEGORY_LABELS.get(cat, cat.title())
            arrow = "v" if cat not in self._collapsed else ">"
            flat.append((None, True, f"{arrow} {label} ({len(learned_in_cat)})"))
            if cat not in self._collapsed:
                for wid in learned_in_cat:
                    flat.append((wid, False, ""))

        return flat

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> bool:
        if not self.open:
            return False

        if key in (pygame.K_ESCAPE, pygame.K_l):
            self.open = False
            return True

        if not self._flat:
            self._flat = self._build_flat(engine)

        sel = list(range(len(self._flat)))

        if key in (pygame.K_UP, pygame.K_KP8):
            self._move(-1, sel)
            return True
        if key in (pygame.K_DOWN, pygame.K_KP2):
            self._move(1, sel)
            return True
        if key in (pygame.K_PAGEUP,):
            self._move(-6, sel)
            return True
        if key in (pygame.K_PAGEDOWN,):
            self._move(6, sel)
            return True

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            cat = self._selected_category()
            if cat is not None:
                if cat in self._collapsed:
                    self._collapsed.discard(cat)
                else:
                    self._collapsed.add(cat)
                self._flat = []
            return True

        return True

    def _move(self, delta: int, sel: list[int]) -> None:
        if not sel:
            return
        if self.selected not in sel:
            self.selected = sel[0]
            return
        idx = sel.index(self.selected)
        self.selected = sel[max(0, min(len(sel) - 1, idx + delta))]
        vis = 12
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + vis:
            self.scroll = self.selected - vis + 1
        self.scroll = max(0, self.scroll)

    def _selected_word_id(self) -> str | None:
        if not self._flat or self.selected >= len(self._flat):
            return None
        wid, is_hdr, _ = self._flat[self.selected]
        return None if is_hdr else wid

    def _selected_category(self) -> str | None:
        if not self._flat or self.selected >= len(self._flat):
            return None
        _, is_hdr, label = self._flat[self.selected]
        if not is_hdr:
            return None
        # Extract category key from label like "v Cosmic (3)"
        raw = label[2:].split("(")[0].strip()
        for cat, display in _CATEGORY_LABELS.items():
            if display == raw:
                return cat
        return None

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #

    def render(self, surface: pygame.Surface, engine: "Engine") -> None:
        if not self.open or not self._font_normal:
            return
        try:
            self._render_inner(surface, engine)
        except Exception:
            import traceback
            traceback.print_exc()
            self.open = False

    def _render_inner(self, surface: pygame.Surface, engine: "Engine") -> None:
        sw, sh = surface.get_width(), surface.get_height()
        pw = min(860, sw - 40)
        ph = min(520, sh - 40)
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        engine.ui_registry.draw_panel(
            popup, pygame.Rect(0, 0, pw, ph), "polis_sanctuary",
            tint_color=self.BORDER, fill_color=self.BG, fill_alpha=255,
        )

        PAD = UI_PANEL_INSET
        lw = int(pw * 0.30)
        rw = pw - lw

        if not self._flat:
            self._flat = self._build_flat(engine)
            if self._flat and self.selected >= len(self._flat):
                self.selected = 0

        # Hint row
        _fh = self._font_small.get_linesize()
        _HINT_ROW_H = _fh + 8
        _hint_row_top = ph - PAD - _HINT_ROW_H

        self._draw_left(popup, engine, 0, 0, lw, ph, PAD, _hint_row_top)
        self._draw_right(popup, engine, lw, 0, rw, ph, PAD)

        # Vertical divider
        pygame.draw.line(popup, self.BORDER,
                         (lw, PAD), (lw, _hint_row_top - 1), 1)

        # Hint row separator + text
        pygame.draw.line(popup, self.BORDER,
                         (PAD, _hint_row_top), (pw - PAD, _hint_row_top), 1)
        _hint_text_y = _hint_row_top + (_HINT_ROW_H - self._font_small.get_height()) // 2

        # Left: word count flavour
        lang = getattr(engine.player, "language", None)
        _wc = len(lang.known_deep_words) if lang else 0
        _wc_s = self._font_small.render(
            f"{_wc} word{'s' if _wc != 1 else ''} known. The tongue runs deeper.",
            True, UI_TEXT_DIM,
        )
        popup.blit(_wc_s, (PAD, _hint_text_y))

        # Right: navigation hints
        footer = self._font_small.render(
            "^ v navigate   Enter expand   L/ESC close",
            True, self.DIM,
        )
        popup.blit(footer, (pw - PAD - footer.get_width(), _hint_text_y))

        surface.blit(popup, (px, py))

    def _draw_left(
        self, surf: pygame.Surface, engine: "Engine",
        ox: int, oy: int, w: int, h: int, pad: int,
        hint_row_top: int,
    ) -> None:
        x = ox + pad
        y = oy + pad

        # Title
        lang = getattr(engine.player, "language", None)
        count = len(lang.known_deep_words) if lang else 0
        title_text = f"LEXICON — {count} word{'s' if count != 1 else ''}"
        title = self._font_title.render(title_text, True, self.TITLE)
        surf.blit(title, (x, y))
        y += title.get_height() + 4
        pygame.draw.line(surf, self.BORDER, (ox + pad, y), (ox + w - pad, y), 1)
        y += 6

        lh = self._row_height
        _hl_left = ox + pad
        _hl_width = w - pad * 2

        for idx, (word_id, is_hdr, label) in enumerate(self._flat):
            if y + lh > hint_row_top - 2:
                break
            if idx < self.scroll:
                continue

            is_sel = (idx == self.selected)

            if is_hdr:
                if is_sel:
                    pygame.draw.rect(surf, UI_PANEL_DARK,
                                     (_hl_left, y, _hl_width, lh))
                hs = self._font_small.render(
                    label, True,
                    self.SELECTED if is_sel else self.HDR_C,
                )
                surf.blit(hs, (x, y))
                y += lh
                continue

            # Word entry — render glyph + deep + = common
            wdef = engine.data.deep_tongue.get(word_id, {})
            deep = wdef.get("deep", word_id)
            common = wdef.get("common", "")

            if is_sel:
                pygame.draw.rect(surf, UI_PANEL_DARK,
                                 (_hl_left, y, _hl_width, lh))

            # Inline glyph rendering
            glyph_x = x + 4
            try:
                _draw_glyph_word(surf, deep, glyph_x, y + 1,
                                 GLYPH_SIZE_INLINE, self.DEEP_C)
                glyph_x += _glyph_word_pw(deep, GLYPH_SIZE_INLINE) + 4
            except Exception:
                glyph_x += GLYPH_SIZE_INLINE + 2

            # Deep tongue text + translation
            text_str = f"{deep} = {common}"
            col = self.SELECTED if is_sel else self.TEXT
            ts = self._font_small.render(text_str, True, col)
            surf.blit(ts, (glyph_x, y))
            y += lh

    def _draw_right(
        self, surf: pygame.Surface, engine: "Engine",
        ox: int, oy: int, w: int, h: int, pad: int,
    ) -> None:
        # Detail rect — content area of right column
        _fh = self._font_small.get_linesize()
        _HINT_ROW_H = _fh + 8
        detail_left = ox + pad
        detail_top = oy + pad
        detail_w = w - pad * 2
        detail_bottom = oy + h - pad - _HINT_ROW_H
        lh = self._font_small.get_linesize() + 2

        word_id = self._selected_word_id()
        wdef = engine.data.deep_tongue.get(word_id, {}) if word_id else {}

        if not word_id or not wdef:
            # Check if a category header is selected — show description
            cat_key = self._selected_category()
            if cat_key:
                self._draw_category_detail(
                    surf, engine, cat_key, detail_left, detail_top,
                    detail_w, detail_bottom, lh,
                )
                return
            ns = self._font_normal.render(
                "Nothing has been learned yet.", True, self.DIM,
            )
            surf.blit(ns, (detail_left, detail_top + 20))
            return

        deep = wdef.get("deep", word_id)
        common = wdef.get("common", "")
        concept = wdef.get("concept", "")
        category = wdef.get("category", "")

        # ── Glyph inset box with ziggurat border — scales to word ──
        phonemes = _get_phonemes(deep)
        num_phonemes = max(1, len(phonemes))

        # Find largest glyph size that fits the detail width
        max_inset_w = detail_w - 8
        glyph_sz = GLYPH_SIZE_DETAIL
        for try_sz in (GLYPH_SIZE_DETAIL, 40, 32, 24):
            needed = num_phonemes * (try_sz + 4) + 24
            if needed <= max_inset_w:
                glyph_sz = try_sz
                break
        else:
            glyph_sz = 24

        glyph_w = glyph_sz + 4
        inset_content_w = num_phonemes * glyph_w
        inset_w = max(inset_content_w + 80, 120)
        inset_w = min(inset_w, max_inset_w)
        inset_h = glyph_sz + 80

        glyph_inset_rect = pygame.Rect(
            detail_left + (detail_w - inset_w) // 2,
            detail_top + 8,
            inset_w,
            inset_h,
        )

        # Draw ziggurat border around inset
        if hasattr(engine, "ui_registry") and engine.ui_registry.has("ziggurat"):
            engine.ui_registry.draw_panel(
                surf, glyph_inset_rect, "ziggurat",
                tint_color=UI_BORDER,
                fill_color=self.BG,
                fill_alpha=255,
            )
        else:
            pygame.draw.rect(surf, UI_BORDER, glyph_inset_rect, 1)

        # Draw glyph sequence centred within inset content area
        inset_inner = glyph_inset_rect.inflate(-40, -40)
        gpw = _glyph_word_pw(deep, glyph_sz)
        gx = inset_inner.centerx - gpw // 2
        gy = inset_inner.centery - glyph_sz // 2
        _draw_glyph_word(surf, deep, gx, gy, glyph_sz, self.DEEP_C)

        y = glyph_inset_rect.bottom + 12

        # ── Deep tongue word — large, centred ─────────────────────
        nm = self._font_bold.render(deep, True, self.DEEP_C)
        if nm.get_width() > detail_w:
            nm = self._font_normal.render(deep, True, self.DEEP_C)
        nm_x = detail_left + (detail_w - nm.get_width()) // 2
        surf.blit(nm, (nm_x, y))
        y += nm.get_height() + 4

        # ── Translation — italic, centred ─────────────────────────
        trans = self._font_italic.render(f'"{common}"', True, UI_TEXT_MID)
        tx = detail_left + (detail_w - trans.get_width()) // 2
        surf.blit(trans, (tx, y))
        y += trans.get_height() + 8

        # ── Separator ─────────────────────────────────────────────
        pygame.draw.line(surf, SLATE_DARK,
                         (detail_left, y), (detail_left + detail_w, y), 1)
        y += 6

        # ── Concept description — wrapped, centred lines ──────────
        wrap_w = detail_w - 16
        if concept:
            for ln in _wrap_text(self._font_small, concept, wrap_w):
                ls = self._font_small.render(ln, True, UI_TEXT_DIM)
                lx = detail_left + (detail_w - ls.get_width()) // 2
                if y + lh > detail_bottom:
                    break
                surf.blit(ls, (lx, y))
                y += lh

        # ── Category label — small, centred ───────────────────────
        y += 4
        cat_label = _CATEGORY_LABELS.get(category, category.title())
        cs = self._font_small.render(cat_label, True, self.LABEL_C)
        cx = detail_left + (detail_w - cs.get_width()) // 2
        if y + lh <= detail_bottom:
            surf.blit(cs, (cx, y))

        # ── Source of learning — bottom of detail rect ────────────
        lang = getattr(engine.player, "language", None)
        if lang and word_id in lang.translation_events:
            turn = lang.translation_events[word_id]
            src_text = f"Learned turn {turn}" if turn > 0 else "Learned"
            src_s = self._font_small.render(src_text, True, self.DIM)
            src_y = detail_bottom - src_s.get_height() - 2
            src_x = detail_left + (detail_w - src_s.get_width()) // 2
            surf.blit(src_s, (src_x, src_y))

    def _draw_category_detail(
        self, surf: pygame.Surface, engine: "Engine",
        cat_key: str,
        detail_left: int, detail_top: int,
        detail_w: int, detail_bottom: int,
        lh: int,
    ) -> None:
        """Render category description when a header is selected."""
        y = detail_top + 20

        # Category name — large, centred
        label = _CATEGORY_LABELS.get(cat_key, cat_key.title())
        nm = self._font_bold.render(label, True, self.TITLE)
        nm_x = detail_left + (detail_w - nm.get_width()) // 2
        surf.blit(nm, (nm_x, y))
        y += nm.get_height() + 12

        # Separator
        pygame.draw.line(surf, SLATE_DARK,
                         (detail_left, y), (detail_left + detail_w, y), 1)
        y += 8

        # Description — wrapped, centred lines
        desc = _CATEGORY_DESCRIPTIONS.get(cat_key, "")
        if desc:
            wrap_w = detail_w - 16
            for ln in _wrap_text(self._font_small, desc, wrap_w):
                ls = self._font_small.render(ln, True, UI_TEXT_DIM)
                lx = detail_left + (detail_w - ls.get_width()) // 2
                if y + lh > detail_bottom:
                    break
                surf.blit(ls, (lx, y))
                y += lh

        # Word count
        y += 8
        lang = getattr(engine.player, "language", None)
        all_words = engine.data.deep_tongue
        if lang:
            count = sum(
                1 for wid in lang.known_deep_words
                if all_words.get(wid, {}).get("category") == cat_key
            )
            count_text = f"{count} word{'s' if count != 1 else ''} learned"
            cs = self._font_small.render(count_text, True, self.LABEL_C)
            cx = detail_left + (detail_w - cs.get_width()) // 2
            if y + lh <= detail_bottom:
                surf.blit(cs, (cx, y))
