# engine/text_reader.py
"""
Full-screen found-text overlay.

Supports:
  - Damaged spans: corruption glyphs with per-frame flicker
  - Redacted spans: solid block fill
  - Deep tongue pages: night_purple color
  - Condition-based border (pristine / worn / damaged / fragmentary)
  - Page navigation via left/right arrow or PgUp/PgDn
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


def _wrap(spans: list[dict], cols: int) -> list[list[dict]]:
    """
    Word-wrap a span list into lines of at most `cols` characters.
    Damaged/redacted spans are treated as 9-char-wide tokens.
    """
    lines: list[list[dict]] = []
    cur:   list[dict]       = []
    col = 0

    def flush() -> None:
        nonlocal cur, col
        if cur:
            lines.append(cur)
        cur = []
        col = 0

    for span in spans:
        if span["type"] != "normal":
            w = 9
            if col + w > cols and col > 0:
                flush()
            if col > 0:
                cur.append({"type": "normal", "text": " "})
                col += 1
            cur.append(span)
            col += w
            continue

        # Normal text — split on whitespace and wrap word by word
        for word in span["text"].split():
            sep   = " " if col > 0 else ""
            token = sep + word
            if col + len(token) > cols and col > 0:
                flush()
                token = word
            cur.append({"type": "normal", "text": token})
            col += len(token)

    flush()
    return lines


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
    DIM     = DEEP_EARTH   # dim grey for meta text

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
        if key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.close()
            return
        if not self._def:
            return
        pages = self._def.get("pages", [])
        n     = len(pages)
        if key in (pygame.K_RIGHT, pygame.K_PAGEDOWN, pygame.K_KP6):
            self._page = min(self._page + 1, n - 1)
        elif key in (pygame.K_LEFT, pygame.K_PAGEUP, pygame.K_KP4):
            self._page = max(self._page - 1, 0)

    # ------------------------------------------------------------------ #
    #  Render
    # ------------------------------------------------------------------ #

    RECOVERED = COLDBELL_LIGHT   # pale_cyan — recovered/inferred text

    def render(self, screen: pygame.Surface, engine=None) -> None:
        if not self.open or not self._def:
            return

        now = pygame.time.get_ticks()
        if now - self._flicker_last_ms > 1500:
            self._flicker_last_ms = now
            self._flicker_tick += 1

        sw, sh = screen.get_width(), screen.get_height()

        cond = self._def.get("condition", "worn")

        # Panel rect — "inscription" mode centers a smaller panel
        if self._panel_size == "inscription":
            pw = min(420, sw - 120)
            ph = min(540, sh - 80)
            frame_rect = pygame.Rect(
                (sw - pw) // 2, (sh - ph) // 2, pw, ph,
            )
        else:
            p = self.PAD
            frame_rect = pygame.Rect(p - 10, p - 10,
                                     sw - (p - 10) * 2, sh - (p - 10) * 2)

        if engine is not None and hasattr(engine, "ui_registry"):
            tint = _TINTS.get(cond, SLATE_DARK)
            engine.ui_registry.draw_panel(
                screen, frame_rect, self._panel_style,
                tint_color=tint, fill_color=self.BG, fill_alpha=255,
            )
        else:
            bg = pygame.Surface((sw, sh))
            bg.fill(self.BG)
            bg.set_alpha(248)
            screen.blit(bg, (0, 0))
            bcol = _BORDERS.get(cond, EARTH_BROWN)
            pygame.draw.rect(screen, bcol, frame_rect, 1)

        cx = frame_rect.x + UI_PANEL_INSET
        cy = frame_rect.y + UI_PANEL_INSET
        cw = frame_rect.width - UI_PANEL_INSET * 2
        content_bottom = frame_rect.bottom - UI_PANEL_INSET
        y  = cy

        # Title — skip when null/empty
        title = self._def.get("title")
        if title:
            screen.blit(
                self._ftitle.render(title, True, self.TITLE_C),
                (cx, y),
            )
            y += self.TSZ + 8

        # Condition label — suppress for inscription panel style
        if self._panel_style != "ziggurat":
            screen.blit(
                self._font.render(cond.upper(), True, self.DIM),
                (cx, y),
            )
            y += self.FSZ + 12

        # Page content
        pages = self._def.get("pages", [])
        if not pages:
            return

        page_idx = min(self._page, len(pages) - 1)
        page     = pages[page_idx]
        is_deep  = self._def.get("deep_tongue", False)
        trailing = page.get("trailing", False)

        # Render mode dispatch
        render_mode = self._def.get("render_mode", "")
        # Ziggurat panel auto-sets deep_tongue render mode
        _is_deep_tongue_mode = (self._panel_style == "ziggurat")
        if render_mode == "alphabet":
            y = self._render_alphabet(screen, cx, y, cw, content_bottom)
        elif _is_deep_tongue_mode:
            y = self._render_deep_tongue(screen, engine, cx, cy, cw,
                                          content_bottom, y, page)
        else:
            spans      = parse_page(page.get("text", ""))
            active_font = self._font_deep if (is_deep and self._font_deep) else self._font
            char_w     = active_font.size("M")[0]
            cols       = max(10, cw // char_w)
            lines      = _wrap(spans, cols)
            lh         = active_font.get_linesize() + 2 + self._line_spacing_bonus
            base_color = self.DEEP if is_deep else self.NORMAL
            centering  = (self._text_align == "center")

            lang = getattr(getattr(engine, "player", None), "language", None) if engine else None
            all_words = getattr(getattr(engine, "data", None), "deep_tongue", {}) if engine else {}

            for li, line in enumerate(lines):
                if y + lh > content_bottom - 28:
                    break

                # For centering: measure line width first, then offset
                if centering:
                    line_w = self._measure_line(
                        line, active_font, lang, all_words, page_idx,
                    )
                    x = cx + (cw - line_w) // 2
                else:
                    x = cx

                for si, span in enumerate(line):
                    if span["type"] == "normal":
                        x = self._render_normal_span(
                            screen, span["text"], x, y,
                            active_font, base_color,
                            lang, all_words, is_deep,
                        )

                    elif span["type"] == "damaged":
                        if lang and lang.is_recovered(self._text_id, page_idx, si):
                            recovered = lang.get_recovered(self._text_id, page_idx, si) or ""
                            s = active_font.render(recovered, True, self.RECOVERED)
                        else:
                            s = self._corrupt_surf(li, si)
                        screen.blit(s, (x, y))
                        x += s.get_width()

                    elif span["type"] == "redacted":
                        bw = active_font.size("MMMMMMMM")[0]
                        pygame.draw.rect(screen, self.REDACT, (x, y, bw, self.FSZ))
                        x += bw

                y += lh

        # Trailing cut-off indicator
        if trailing:
            s = active_font.render("— [text ends here] —", True, self.DAMAGE)
            screen.blit(s, (cx, y + 4))

        # Page count
        n = len(pages)
        if n > 1:
            nav = f"Page {page_idx + 1}/{n}   < > to turn"
            screen.blit(
                self._font.render(nav, True, self.DIM),
                (cx, content_bottom - self.FSZ - 4),
            )

        # Close hint
        hint = self._font.render("ESC / Enter to close", True, self.DIM)
        screen.blit(
            hint,
            (frame_rect.right - UI_PANEL_INSET - hint.get_width(),
             content_bottom - self.FSZ - 4),
        )

    # ------------------------------------------------------------------ #
    #  Deep tongue per-word rendering
    # ------------------------------------------------------------------ #

    def _measure_line(
        self,
        line: list[dict],
        font: pygame.font.Font,
        lang,
        all_words: dict,
        page_idx: int,
    ) -> int:
        """Measure total pixel width of a wrapped line (for centering)."""
        w = 0
        for si, span in enumerate(line):
            if span["type"] == "normal":
                w += self._measure_normal_span(span["text"], font, lang, all_words)
            elif span["type"] == "damaged":
                if lang and lang.is_recovered(self._text_id, page_idx, si):
                    recovered = lang.get_recovered(self._text_id, page_idx, si) or ""
                    w += font.size(recovered)[0]
                else:
                    w += font.size("[DAMAGED]")[0]
            elif span["type"] == "redacted":
                w += font.size("MMMMMMMM")[0]
        return w

    def _measure_normal_span(
        self, text: str, font: pygame.font.Font, lang, all_words: dict,
    ) -> int:
        """Measure pixel width of a normal span with deep tongue word substitution."""
        if not all_words:
            return font.size(text)[0]
        w = 0
        tokens = re.split(r'(\s+)', text)
        for token in tokens:
            if not token:
                continue
            if token.isspace():
                w += font.size(token)[0]
                continue
            stripped = token.strip(_PUNCT).lower()
            if stripped in all_words:
                if lang and lang.knows(stripped):
                    common = all_words[stripped].get("common", stripped)
                    render_font = self._font_deep if self._font_deep else font
                    w += render_font.size(common)[0]
                else:
                    try:
                        w += _glyph_word_pw(stripped, GLYPH_SIZE_INLINE)
                    except Exception:
                        w += font.size(token)[0]
                trail = token[len(token.rstrip(_PUNCT)):]
                if trail:
                    w += font.size(trail)[0]
            else:
                w += font.size(token)[0]
        return w

    def _render_deep_tongue(
        self,
        screen: pygame.Surface,
        engine,
        cx: int, cy: int, cw: int,
        content_bottom: int,
        y: int,
        page: dict,
    ) -> int:
        """
        Render inscription text with hard line breaks, vertically centred.
        Every token is a deep tongue candidate — known words show translation,
        unknown words show glyph sequences. Common words render as normal text.
        Lines are centred horizontally within an inner margin area.
        """
        text = page.get("text", "")
        active_font = self._font_deep if self._font_deep else self._font
        lh = GLYPH_SIZE_INLINE + self._line_spacing_bonus + 4

        lang = getattr(getattr(engine, "player", None), "language", None) if engine else None
        all_words = getattr(getattr(engine, "data", None), "deep_tongue", {}) if engine else {}

        # Inner rect — extra 20px margin beyond the standard border padding
        inner_left = cx + 20
        inner_top = cy + 20
        inner_w = cw - 40
        inner_bottom = content_bottom - 20

        # Split on hard line breaks, then wrap each
        raw_lines = text.split("\n")
        all_wrapped: list[list[str]] = []
        for raw_line in raw_lines:
            if not raw_line.strip():
                all_wrapped.append([])  # blank line
                continue
            wrapped = self._wrap_deep_tongue_line(
                raw_line, active_font, inner_w, lang, all_words,
            )
            all_wrapped.extend(wrapped)

        # Vertical centering
        total_h = len(all_wrapped) * lh
        avail_h = inner_bottom - inner_top
        start_y = inner_top + (avail_h - total_h) // 2
        start_y = max(inner_top + 8, start_y)

        y = start_y
        for wline in all_wrapped:
            if y + lh > inner_bottom:
                break
            if not wline:
                y += lh  # blank line
                continue
            # Measure for horizontal centering
            line_w = self._measure_deep_tongue_tokens(
                wline, active_font, lang, all_words,
            )
            x = inner_left + (inner_w - line_w) // 2
            # Render each token
            for token in wline:
                if not token:
                    continue
                if token.isspace():
                    s = active_font.render(token, True, self.DEEP)
                    screen.blit(s, (x, y))
                    x += s.get_width()
                    continue
                stripped = token.strip(_PUNCT).lower()
                lead = token[:len(token) - len(token.lstrip(_PUNCT))]
                trail = token[len(token.rstrip(_PUNCT)):]
                if lead:
                    s = active_font.render(lead, True, self.DEEP)
                    screen.blit(s, (x, y))
                    x += s.get_width()
                if stripped in all_words:
                    if lang and lang.knows(stripped):
                        common = all_words[stripped].get("common", stripped)
                        render_font = self._font_deep if self._font_deep else active_font
                        s = render_font.render(common, True, self.DEEP)
                        screen.blit(s, (x, y))
                        x += s.get_width()
                    else:
                        pw = _glyph_word_pw(stripped, GLYPH_SIZE_INLINE)
                        _draw_glyph_word(screen, stripped, x, y + 1,
                                         GLYPH_SIZE_INLINE, self.DEEP)
                        x += pw
                else:
                    s = active_font.render(stripped, True, self.DEEP)
                    screen.blit(s, (x, y))
                    x += s.get_width()
                if trail:
                    s = active_font.render(trail, True, self.DEEP)
                    screen.blit(s, (x, y))
                    x += s.get_width()

            y += lh

        return y

    def _wrap_deep_tongue_line(
        self, line: str, font: pygame.font.Font, max_w: int,
        lang, all_words: dict,
    ) -> list[list[str]]:
        """Word-wrap a single line into sub-lines of tokens that fit max_w."""
        # Split on whitespace and em-dash, preserving delimiters
        tokens = re.split(r'(\s+|\u2014)', line)
        result: list[list[str]] = []
        cur: list[str] = []
        cur_w = 0
        space_w = font.size(" ")[0]

        for token in tokens:
            if not token:
                continue
            if token.isspace():
                tw = font.size(token)[0]
                if cur_w + tw <= max_w:
                    cur.append(token)
                    cur_w += tw
                continue
            tw = self._measure_single_token(token, font, lang, all_words)
            if cur_w + tw > max_w and cur:
                result.append(cur)
                cur = []
                cur_w = 0
            cur.append(token)
            cur_w += tw
        if cur:
            result.append(cur)
        return result if result else [[""]]

    def _measure_single_token(
        self, token: str, font: pygame.font.Font, lang, all_words: dict,
    ) -> int:
        """Measure one token's pixel width with deep tongue substitution."""
        stripped = token.strip(_PUNCT).lower()
        lead = token[:len(token) - len(token.lstrip(_PUNCT))]
        trail = token[len(token.rstrip(_PUNCT)):]
        w = 0
        if lead:
            w += font.size(lead)[0]
        if stripped in all_words:
            if lang and lang.knows(stripped):
                common = all_words[stripped].get("common", stripped)
                render_font = self._font_deep if self._font_deep else font
                w += render_font.size(common)[0]
            else:
                w += _glyph_word_pw(stripped, GLYPH_SIZE_INLINE)
        else:
            w += font.size(stripped)[0]
        if trail:
            w += font.size(trail)[0]
        return w

    def _measure_deep_tongue_tokens(
        self, tokens: list[str], font: pygame.font.Font,
        lang, all_words: dict,
    ) -> int:
        """Measure total width of a list of tokens."""
        w = 0
        for token in tokens:
            if not token:
                continue
            if token.isspace():
                w += font.size(token)[0]
            else:
                w += self._measure_single_token(token, font, lang, all_words)
        return w

    def _render_normal_span(
        self,
        screen: pygame.Surface,
        text: str,
        x: int,
        y: int,
        font: pygame.font.Font,
        base_color: tuple,
        lang,
        all_words: dict,
        is_deep_page: bool,
    ) -> int:
        """
        Render a normal text span with per-word deep tongue detection.
        Deep tongue words render as glyphs (if unlearned) or italic translation (if learned).
        Returns the new x position after rendering.
        """
        if not all_words:
            s = font.render(text, True, base_color)
            screen.blit(s, (x, y))
            return x + s.get_width()

        # Tokenise preserving whitespace
        tokens = re.split(r'(\s+)', text)
        for token in tokens:
            if not token:
                continue
            if token.isspace():
                s = font.render(token, True, base_color)
                screen.blit(s, (x, y))
                x += s.get_width()
                continue

            # Strip punctuation for lookup
            stripped = token.strip(_PUNCT).lower()
            if stripped in all_words:
                if lang and lang.knows(stripped):
                    # Learned — show translation in italic deep font
                    common = all_words[stripped].get("common", stripped)
                    render_font = self._font_deep if self._font_deep else font
                    s = render_font.render(common, True, self.DEEP)
                    screen.blit(s, (x, y))
                    x += s.get_width()
                else:
                    # Unlearned — render as phoneme glyphs
                    try:
                        pw = _glyph_word_pw(stripped, GLYPH_SIZE_INLINE)
                        _draw_glyph_word(screen, stripped, x, y + 1, GLYPH_SIZE_INLINE, self.DEEP)
                        x += pw
                    except Exception:
                        s = font.render(token, True, self.DEEP)
                        screen.blit(s, (x, y))
                        x += s.get_width()
                # Re-render trailing punctuation
                trail = token[len(token.rstrip(_PUNCT)):]
                if trail:
                    s = font.render(trail, True, base_color)
                    screen.blit(s, (x, y))
                    x += s.get_width()
            else:
                s = font.render(token, True, base_color)
                screen.blit(s, (x, y))
                x += s.get_width()

        return x

    def _render_alphabet(
        self,
        screen: pygame.Surface,
        cx: int,
        y: int,
        cw: int,
        content_bottom: int,
    ) -> int:
        """Render all phoneme glyphs in a grid for the alphabet debug note."""
        phonemes = _get_all_phonemes()
        if not phonemes:
            s = self._font.render("[no phonemes loaded]", True, self.DIM)
            screen.blit(s, (cx, y))
            return y + 20

        glyph_size = GLYPH_SIZE_ALPHABET
        label_h = 14
        cell_w = glyph_size + 8
        cell_h = glyph_size + label_h + 4
        cols = max(1, cw // (cell_w + 20))

        for i, (phoneme, seed) in enumerate(phonemes):
            col = i % cols
            row = i // cols
            gx = cx + col * (cell_w + 20)
            gy = y + row * cell_h
            if gy + cell_h > content_bottom - 28:
                break

            gdef = _generate_glyph(phoneme, seed, glyph_size)
            _draw_glyph(screen, gdef, gx, gy, glyph_size, self.DEEP)

            # Label beneath
            label = self._font.render(phoneme, True, self.DIM)
            lw = label.get_width()
            screen.blit(label, (gx + (glyph_size - lw) // 2, gy + glyph_size + 2))

        total_rows = (len(phonemes) + cols - 1) // cols
        return y + total_rows * cell_h

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
