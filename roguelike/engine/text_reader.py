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
    DEEP    = DEEP_PURPLE   # night_purple — deep tongue
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
        self._font:             pygame.font.Font | None = None
        self._font_deep:        pygame.font.Font | None = None
        self._ftitle:           pygame.font.Font | None = None
        self._corrupt_pool:     str                     = ",.;:|/-_~!?"

    def init(self, display: "DisplayConfig") -> None:
        self._font      = display.font_ui_normal
        self._font_deep = display.font_deep
        self._ftitle    = display.font_ui_large
        self._corrupt_pool = self._build_corrupt_pool(self._font)

    def open_text(self, text_def: dict) -> None:
        """Open the reader with a loaded text definition."""
        self._def          = text_def
        self._text_id      = text_def.get("id", "")
        self._page         = 0
        self._flicker_tick = 0
        self.open          = True

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
        p      = self.PAD

        cond       = self._def.get("condition", "worn")
        frame_rect = pygame.Rect(p - 10, p - 10,
                                 sw - (p - 10) * 2, sh - (p - 10) * 2)

        if engine is not None and hasattr(engine, "ui_registry"):
            tint = _TINTS.get(cond, SLATE_DARK)
            engine.ui_registry.draw_panel(
                screen, frame_rect, "weathered_temple",
                tint_color=tint, fill_color=self.BG, fill_alpha=248,
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

        # Title
        title = self._def.get("title")
        if title:
            screen.blit(
                self._ftitle.render(title, True, self.TITLE_C),
                (cx, y),
            )
            y += self.TSZ + 8

        # Condition label
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

        spans      = parse_page(page.get("text", ""))
        active_font = self._font_deep if (is_deep and self._font_deep) else self._font
        char_w     = active_font.size("M")[0]
        cols       = max(10, cw // char_w)
        lines      = _wrap(spans, cols)
        lh         = active_font.get_linesize() + 2
        base_color = self.DEEP if is_deep else self.NORMAL

        lang = getattr(getattr(engine, "player", None), "language", None) if engine else None

        for li, line in enumerate(lines):
            if y + lh > content_bottom - 28:
                break
            x = cx
            for si, span in enumerate(line):
                if span["type"] == "normal":
                    s = active_font.render(span["text"], True, base_color)
                    screen.blit(s, (x, y))
                    x += s.get_width()

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
