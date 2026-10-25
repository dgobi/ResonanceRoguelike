# engine/text_reader.py
"""
Full-screen found-text overlay.

Supports:
  - Damaged spans: corruption glyphs with per-frame flicker
  - Redacted spans: solid block fill
  - Deep tongue pages: night_purple color
  - Condition-based border (pristine / worn / damaged / fragmentary)
  - Authored pages via left/right; bounded scrolling via arrows, PgUp/PgDn, Home/End
  - ESC or Enter to close
"""
from __future__ import annotations

import random
import re

import pygame
from typing import TYPE_CHECKING
from config import UI_PANEL_INSET
from engine.palette import *
from rendering.glyph_gen import (
    GLYPH_SIZE_INLINE, GLYPH_SIZE_ALPHABET,
    draw_word as _draw_glyph_word,
    word_pixel_width as _glyph_word_pw,
    get_all_phonemes as _get_all_phonemes,
    draw_glyph as _draw_glyph,
    generate_glyph as _generate_glyph,
)

if TYPE_CHECKING:
    from engine.display_config import DisplayConfig


# Characters used to represent damaged/corrupted text.
# All verified to render in Junicode at 14px.
_CORRUPT = list(
    "\u017f\u0142\u00f0\u00fe\u00e6\u0153"   # archaic latin: ſłðþæœ
    "\u2020\u2021\u00a7\u00b6"               # typographic: †‡§¶
    "\u0131\u0263\u0251\u025b\u0254\u028a"   # latin variants: ıɣɑɛɔʊ
    ",.;:!?/\\|-_~"                           # punctuation fragments
    "fijltI1rl"                               # narrow letters
)

# Border color per document condition (fallback when no ui_registry)
_BORDERS: dict[str, tuple[int, int, int]] = {
    "pristine":    FROST_WHITE,   # near_white
    "worn":        WORN_STONE,   # warm parchment
    "damaged":     BLOOD_STONE,   # blood_rose
    "fragmentary": DRIED_BLOOD,   # blood_mid
}

# Punctuation characters to strip from tokens during deep tongue lookup
_PUNCT = ".,;:!?\u2014\"'()[]"

# Panel tint per document condition (draw_panel tint_color)
_TINTS: dict[str, tuple[int, int, int]] = {
    "pristine":    STONE_BLUE,
    "worn":        SLATE_DARK,
    "damaged":     DEEP_STONE_BLUE,
    "fragmentary": DEEP_STONE_BLUE,
    "burned":      BLOOD_CELLAR,
}


# ------------------------------------------------------------------ #
#  Span parsing
# ------------------------------------------------------------------ #

def parse_page(text: str) -> list[dict]:
    """
    Split a page string into typed spans.
    Markers [DAMAGED] and [REDACTED] become special span types.
    """
    spans: list[dict] = []
    for part in re.split(r"(\[DAMAGED\]|\[REDACTED\])", text):
        if part == "[DAMAGED]":
            spans.append({"type": "damaged"})
        elif part == "[REDACTED]":
            spans.append({"type": "redacted"})
        elif part:
            spans.append({"type": "normal", "text": part})
    return spans




# ------------------------------------------------------------------ #
#  TextReader
# ------------------------------------------------------------------ #

class TextReader:
    """
    Full-screen overlay for reading found documents.
    Call open_text(text_def) to display; ESC/Enter to close.
    """

    BG      = VOID_BLACK   # void_black
    NORMAL  = WORN_STONE   # warm parchment text
    DEEP    = DEEP_TONGUE_COLOUR   # legible purple — deep tongue glyphs and translations
    DAMAGE  = DRIED_BLOOD   # blood_mid — corrupted glyphs
    REDACT  = MIDNIGHT_DEEP   # near-void block
    TITLE_C = OLD_GOLD   # old_gold
    DIM     = UI_TEXT_DIM  # visible navigation and document metadata

    PAD  = 60    # px from screen edge
    FSZ  = 14    # body font size
    TSZ  = 16    # title font size

    def __init__(self) -> None:
        self.open:              bool       = False
        self._def:              dict | None = None
        self._page:             int        = 0
        self._flicker_last_ms:  int        = 0
        self._flicker_tick:     int        = 0
        self._text_id:          str                     = ""
        self._panel_style:      str                     = "weathered_temple"
        self._text_align:       str                     = "left"
        self._line_spacing_bonus: int                   = 0
        self._panel_size:       str                     = "full"
        self._font:             pygame.font.Font | None = None
        self._font_deep:        pygame.font.Font | None = None
        self._ftitle:           pygame.font.Font | None = None
        self._corrupt_pool:     str                     = ",.;:|/-_~!?"
        self._scroll = 0
        self._max_scroll = 0
        self._viewport_height = 1
        self._line_height = 1
        self._visible_rows = []

    def init(self, display: "DisplayConfig") -> None:
        self._font      = display.font_ui_normal
        self._font_deep = display.font_deep
        self._ftitle    = display.font_ui_large
        self._corrupt_pool = self._build_corrupt_pool(self._font)

    def open_text(
        self,
        text_def: dict,
        panel_style: str = "weathered_temple",
        text_align: str = "left",
        line_spacing_bonus: int = 0,
        panel_size: str = "full",
    ) -> None:
        """Open the reader with a loaded text definition."""
        self._def                = text_def
        self._text_id            = text_def.get("id", "")
        self._page               = 0
        self._scroll             = 0
        self._max_scroll         = 0
        self._flicker_tick       = 0
        self._panel_style        = panel_style
        self._text_align         = text_align
        self._line_spacing_bonus = line_spacing_bonus
        self._panel_size         = panel_size
        self.open                = True

    def close(self) -> None:
        self.open = False
        self._def = None

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.close()
            return
        if not self._def:
            return
        pages = self._def.get("pages", [])
        n     = len(pages)
        old_page = self._page
        if key in (pygame.K_RIGHT, pygame.K_KP6):
            self._page = min(self._page + 1, n - 1)
        elif key in (pygame.K_LEFT, pygame.K_KP4):
            self._page = max(self._page - 1, 0)
        elif key in (pygame.K_UP, pygame.K_KP8):
            self._scroll -= self._line_height
        elif key in (pygame.K_DOWN, pygame.K_KP2):
            self._scroll += self._line_height
        elif key == pygame.K_PAGEUP:
            self._scroll -= self._viewport_height
        elif key == pygame.K_PAGEDOWN:
            self._scroll += self._viewport_height
        elif key == pygame.K_HOME:
            self._scroll = 0
        elif key == pygame.K_END:
            self._scroll = self._max_scroll
        if self._page != old_page:
            self._scroll = 0
        self._scroll = max(0, min(self._max_scroll, self._scroll))

    # ------------------------------------------------------------------ #
    #  Render
    # ------------------------------------------------------------------ #

    RECOVERED = COLDBELL_LIGHT   # pale_cyan — recovered/inferred text



    def _page_lines(self, width, engine=None):
        """Visual rows retain authored span IDs; layout never changes knowledge."""
        page = self._def.get("pages", [])[self._page]
        lang = getattr(getattr(engine, "player", None), "language", None)
        words = getattr(getattr(engine, "data", None), "deep_tongue", {})
        deep = self._def.get("deep_tongue", False) or self._panel_style == "ziggurat"
        font = self._font_deep if deep and self._font_deep else self._font
        lh = max(font.get_linesize(), GLYPH_SIZE_INLINE + 2) + 2 + self._line_spacing_bonus
        rows, current, used = [], [], 0

        def flush():
            nonlocal current, used
            rows.append(current)
            current, used = [], 0

        def add(surface, text, span_id):
            nonlocal used
            # Split an over-wide rendered token, including glyph words, into
            # bounded visual fragments without reinterpreting its source text.
            offset = 0
            total = surface.get_width()
            if current and used + total > width:
                flush()
            while offset < total:
                take = min(width - used, total - offset)
                fragment = surface.subsurface((offset, 0, take, surface.get_height())).copy()
                current.append(dict(surface=fragment, text=text, span=span_id,
                                    offset=offset, width=take))
                used += take
                offset += take
                if offset < total:
                    flush()

        if self._def.get("render_mode") == "alphabet":
            size = GLYPH_SIZE_ALPHABET
            cell_w = max(size + 28, self._font.size("SH")[0] + 8)
            lh = size + self._font.get_linesize() + 8
            cols = max(1, width // cell_w)
            for index, (phoneme, seed) in enumerate(_get_all_phonemes()):
                surface = pygame.Surface((min(cell_w, width), lh), pygame.SRCALPHA)
                glyph = _generate_glyph(phoneme, seed, size)
                _draw_glyph(surface, glyph, 0, 0, size, self.DEEP)
                surface.blit(self._font.render(phoneme, True, self.DIM), (0, size + 2))
                current.append(dict(surface=surface, text=phoneme, span=index, offset=0, width=surface.get_width()))
                if len(current) == cols:
                    flush()
        else:
            for span_id, span in enumerate(parse_page(page.get("text", ""))):
                kind = span["type"]
                recovered = kind == "damaged" and lang and lang.is_recovered(self._text_id, self._page, span_id)
                if kind == "normal" or recovered:
                    text = (lang.get_recovered(self._text_id, self._page, span_id) or "") if recovered else span["text"]
                    for token in re.split(r"(\n|[^\S\n]+)", text):
                        if not token:
                            continue
                        if token == "\n":
                            flush()
                            continue
                        token_w = font.size(token)[0] if recovered else self._measure_normal_span(token, font, lang, words)
                        surface = pygame.Surface((max(1, token_w), lh), pygame.SRCALPHA)
                        if recovered:
                            surface.blit(font.render(token, True, self.RECOVERED), (0, 0))
                        else:
                            self._render_normal_span(surface, token, 0, 0, font,
                                                     self.DEEP if deep else self.NORMAL, lang, words, deep)
                        add(surface, token, span_id)
                elif kind == "damaged":
                    add(self._corrupt_surf(self._page, span_id), "[DAMAGED]", span_id)
                else:
                    surface = pygame.Surface((font.size("MMMMMMMM")[0], font.get_linesize()))
                    surface.fill(self.REDACT)
                    add(surface, "[REDACTED]", span_id)
        if page.get("trailing"):
            flush()
            add(font.render("— [text ends here] —", True, self.DAMAGE), "— [text ends here] —", -1)
        if current or not rows:
            flush()
        return rows, lh

    def render(self, screen: pygame.Surface, engine=None) -> None:
        if not self.open or not self._def or not self._font:
            return
        pages = self._def.get("pages", [])
        if not pages:
            return
        self._page = max(0, min(self._page, len(pages) - 1))
        now = pygame.time.get_ticks()
        if now - self._flicker_last_ms > 1500:
            self._flicker_last_ms = now
            self._flicker_tick += 1
        sw, sh = screen.get_size()
        pad = UI_PANEL_INSET
        # Measure the current authored page, then wrap at the actual content
        # width before sizing its height. Later pages get their own layout.
        body = pages[self._page].get("text", "")
        title = self._def.get("title") or ""
        natural = max([self._font.size(line)[0] for line in body.split("\n")] + [260])
        pw = min(sw - 40, natural + pad * 2)
        width = pw - pad * 2
        rows, lh = self._page_lines(width, engine)
        self._line_height = lh
        # All header and footer heights use actual font metrics.
        title_lines = []
        if title:
            line = ""
            for char in title:
                if line and self._ftitle.size(line + char)[0] > width:
                    title_lines.append(line)
                    line = ""
                line += char
            title_lines.append(line)
        header_h = len(title_lines) * self._ftitle.get_linesize()
        cond = self._def.get("condition", "worn")
        if self._panel_style != "ziggurat":
            header_h += self._font.get_linesize() + 8
        footer_lh = self._font.get_linesize() + 2
        footer_h = footer_lh * 3 + 8
        ph = min(sh - 40, pad * 2 + header_h + len(rows) * lh + footer_h + 2)
        frame = pygame.Rect((sw - pw)//2, (sh - ph)//2, pw, ph)
        registry = getattr(engine, "ui_registry", None)
        if registry:
            registry.draw_panel(screen, frame, self._panel_style,
                                tint_color=_TINTS.get(cond, SLATE_DARK),
                                fill_color=self.BG, fill_alpha=255)
        else:
            pygame.draw.rect(screen, self.BG, frame)
            pygame.draw.rect(screen, _BORDERS.get(cond, EARTH_BROWN), frame, 1)
        content = frame.inflate(-pad * 2, -pad * 2)
        y = content.top
        previous_clip = screen.get_clip()
        screen.set_clip(content.clip(previous_clip))
        for line in title_lines:
            screen.blit(self._ftitle.render(line, True, self.TITLE_C), (content.left, y))
            y += self._ftitle.get_linesize()
        if self._panel_style != "ziggurat":
            screen.blit(self._font.render(cond.upper(), True, self.DIM), (content.left, y))
            y += self._font.get_linesize() + 8
        footer_top = content.bottom - footer_h
        viewport = pygame.Rect(content.left, y, content.width, max(1, footer_top - y - 2))
        self._viewport_height = viewport.height
        self._max_scroll = max(0, len(rows) * lh - viewport.height)
        self._scroll = max(0, min(self._max_scroll, self._scroll))
        self._visible_rows = []
        screen.set_clip(viewport.clip(content).clip(previous_clip))
        for index, row in enumerate(rows):
            ry = viewport.top + index * lh - self._scroll
            if ry + lh <= viewport.top or ry >= viewport.bottom:
                continue
            self._visible_rows.append(index)
            x = viewport.left
            if self._text_align == "center" or self._panel_style == "ziggurat":
                x += (width - sum(f["width"] for f in row)) // 2
            for fragment in row:
                screen.blit(fragment["surface"], (x, ry))
                x += fragment["width"]
        screen.set_clip(content.clip(previous_clip))
        pygame.draw.line(screen, self.DIM, (content.left, footer_top), (content.right, footer_top))
        status = f"< > Page {self._page + 1}/{len(pages)}"
        if self._max_scroll:
            status += f"   {round(100 * self._scroll / self._max_scroll)}%"
        for index, hint in enumerate((status, "Up/Down PgUp/PgDn Home/End scroll", "Esc / Enter close")):
            screen.blit(self._font.render(hint, True, self.DIM), (content.left, footer_top + 4 + index * footer_lh))
        screen.set_clip(previous_clip)
        # Concise production evidence; surfaces remain private rendering data.
        self._layout_rows = rows
        self._viewport = viewport
        self._frame = frame


    def _token_surface(self, token, font, base_color, lang, all_words):
        """Use the exact same glyph/font surfaces for measurement and drawing."""
        word = token.strip(_PUNCT).lower()
        if token.isspace() or word not in all_words:
            return font.render(token, True, base_color)
        lead = token[:len(token) - len(token.lstrip(_PUNCT))]
        trail = token[len(token.rstrip(_PUNCT)):]
        parts = [font.render(lead, True, base_color)]
        if lang and lang.knows(word):
            render_font = self._font_deep or font
            parts.append(render_font.render(all_words[word].get("common", word), True, self.DEEP))
        else:
            try:
                glyph = pygame.Surface((max(1, _glyph_word_pw(word, GLYPH_SIZE_INLINE)), GLYPH_SIZE_INLINE + 2), pygame.SRCALPHA)
                _draw_glyph_word(glyph, word, 0, 1, GLYPH_SIZE_INLINE, self.DEEP)
                parts.append(glyph)
            except Exception:
                parts.append(font.render(word, True, self.DEEP))
        parts.append(font.render(trail, True, base_color))
        surface = pygame.Surface((max(1, sum(p.get_width() for p in parts)), max(p.get_height() for p in parts)), pygame.SRCALPHA)
        x = 0
        for part in parts:
            surface.blit(part, (x, 0)); x += part.get_width()
        return surface

    def _measure_normal_span(self, text, font, lang, all_words):
        return sum(self._token_surface(t, font, self.NORMAL, lang, all_words).get_width()
                   for t in re.split(r'(\s+)', text) if t)

    def _render_normal_span(self, screen, text, x, y, font, base_color,
                            lang, all_words, is_deep_page):
        for token in re.split(r'(\s+)', text):
            if token:
                surface = self._token_surface(token, font, base_color, lang, all_words)
                screen.blit(surface, (x, y)); x += surface.get_width()
        return x

    # ------------------------------------------------------------------ #
    #  Corruption
    # ------------------------------------------------------------------ #

    def _build_corrupt_pool(self, font: pygame.font.Font) -> str:
        candidates = (
            "\u017f\u0142\u00f0\u00fe\u00e6\u0153"   # ſłðþæœ
            "\u2020\u2021\u00a7\u00b6\u0131\u0263"   # †‡§¶ıɣ
            "\u0251\u025b\u0254\u028a"                # ɑɛɔʊ
            ",.;:!?/\\|-_~"
            "fijltI1rlicevunmwszxao"
            "{}[]()<>"
        )
        pool = []
        for ch in candidates:
            metrics = font.metrics(ch)
            if metrics and metrics[0] is not None and metrics[0][4] > 0:
                pool.append(ch)
        for ch in ",.;:|/-_~!?":
            if ch not in pool:
                pool.append(ch)
        return "".join(pool)

    def _corrupt_surf(self, line_idx: int, span_idx: int) -> pygame.Surface:
        """Return corruption glyphs filling the pixel width of '[DAMAGED]', with one flickering."""
        seed       = f"{line_idx}:{span_idx}"
        rng        = random.Random(seed)
        target_px  = self._font.size("[DAMAGED]")[0]

        pool   = self._corrupt_pool
        chars: list[str] = []
        width = 0
        while width < target_px:
            ch = rng.choice(pool)
            cw = self._font.size(ch)[0]
            if width + cw > target_px and chars:
                break
            chars.append(ch)
            width += cw

        # One character flickers per tick (every 1500 ms)
        tick = self._flicker_tick
        if tick > 0 and chars:
            frng = random.Random(f"{seed}:{tick}")
            chars[frng.randint(0, len(chars) - 1)] = frng.choice(pool)

        return self._font.render("".join(chars), True, self.DAMAGE)
