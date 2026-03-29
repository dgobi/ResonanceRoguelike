# rendering/glyph_gen.py
"""
Procedural glyph generation for the deep tongue writing system.

All glyphs share a common grammar:
  - Primary axis: a main stroke (vertical, horizontal, or diagonal)
  - Secondary arms: 0-3 shorter strokes branching from the primary
  - Tertiary ticks: small marks at stroke ends
  - Optional frame: a partial enclosure (arc, corner)
  - Style: standard, dense, open, or ancient

Variation from seed — same seed = same glyph always.
Uses pygame.draw only — no image loading, no font rendering.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from engine.palette import *


# ------------------------------------------------------------------ #
#  Glyph size constants — import these everywhere instead of hardcoding
# ------------------------------------------------------------------ #

GLYPH_SIZE_INLINE   = 16    # text reader inline, lexicon list
GLYPH_SIZE_DETAIL   = 48    # lexicon detail panel featured glyph
GLYPH_SIZE_ALPHABET = 28    # debug alphabet note display


# ------------------------------------------------------------------ #
#  GlyphDef
# ------------------------------------------------------------------ #

@dataclass
class GlyphDef:
    phoneme: str
    seed: int
    primary_angle: float        # radians
    primary_length: float       # 0.4-0.9 of glyph_size
    arms: list[tuple]           # (angle, length, attach_t) where t=0-1 along primary
    ticks: list[bool]           # tick at each arm end?
    frame: str | None           # "arc_left", "arc_right", "corner_tl", "corner_br", None
    style: str                  # standard/dense/open/ancient
    accent_strokes: list[tuple] # (start_t, angle, length) — short accent marks


_STYLES = ["standard", "dense", "open", "ancient"]

_FRAMES = [
    None, None, None,           # ~50% no frame
    "arc_left", "arc_right",
    "corner_tl", "corner_br",
]


def generate_glyph(phoneme: str, seed: int, size: int = 16) -> GlyphDef:
    """Deterministically generate a GlyphDef from seed."""
    rng = random.Random(seed)

    # Primary axis — angle biased toward vertical/diagonal (more script-like)
    angle_pool = [
        math.pi / 2,                    # vertical
        math.pi / 2 + rng.uniform(-0.4, 0.4),  # near-vertical
        math.pi / 4 + rng.uniform(-0.2, 0.2),  # diagonal
        3 * math.pi / 4 + rng.uniform(-0.2, 0.2),  # other diagonal
        0.0 + rng.uniform(-0.2, 0.2),   # near-horizontal
    ]
    primary_angle = rng.choice(angle_pool)
    primary_length = rng.uniform(0.5, 0.85)

    # Style
    style = rng.choice(_STYLES)

    # Arms — count varies by style
    if style == "dense":
        arm_count = rng.randint(2, 3)
    elif style == "open":
        arm_count = rng.randint(0, 1)
    elif style == "ancient":
        arm_count = rng.randint(1, 3)
    else:
        arm_count = rng.randint(1, 2)

    arms = []
    for _ in range(arm_count):
        # Arm branches off primary at some point along it
        attach_t = rng.uniform(0.15, 0.85)
        # Arm angle relative to primary — perpendicular bias
        arm_angle = primary_angle + rng.choice([
            math.pi / 2, -math.pi / 2,
            math.pi / 3, -math.pi / 3,
            math.pi / 4, -math.pi / 4,
        ]) + rng.uniform(-0.15, 0.15)
        arm_length = rng.uniform(0.15, 0.4)
        arms.append((arm_angle, arm_length, attach_t))

    # Ticks at arm ends
    ticks = [rng.random() < 0.5 for _ in arms]

    # Frame
    frame = rng.choice(_FRAMES)
    if style == "open":
        frame = None  # open style never has frame

    # Accent strokes (short marks) — ancient style gets more
    accent_count = 0
    if style == "ancient":
        accent_count = rng.randint(1, 2)
    elif style == "dense":
        accent_count = rng.randint(0, 1)

    accent_strokes = []
    for _ in range(accent_count):
        start_t = rng.uniform(0.0, 1.0)
        acc_angle = rng.uniform(0, 2 * math.pi)
        acc_length = rng.uniform(0.06, 0.12)
        accent_strokes.append((start_t, acc_angle, acc_length))

    return GlyphDef(
        phoneme=phoneme,
        seed=seed,
        primary_angle=primary_angle,
        primary_length=primary_length,
        arms=arms,
        ticks=ticks,
        frame=frame,
        style=style,
        accent_strokes=accent_strokes,
    )


# ------------------------------------------------------------------ #
#  Drawing
# ------------------------------------------------------------------ #

def _line_width(size: int) -> int:
    """Consistent stroke width for coherent visual weight."""
    if size <= 14:
        return 1
    elif size <= 20:
        return 1
    else:
        return 2


def _stroke(surface: pygame.Surface, colour: tuple, x0: float, y0: float,
            x1: float, y1: float, width: int) -> None:
    """Draw a single stroke, using aaline for width=1."""
    if width <= 1:
        pygame.draw.aaline(surface, colour, (x0, y0), (x1, y1))
    else:
        pygame.draw.line(surface, colour, (int(x0), int(y0)),
                         (int(x1), int(y1)), width)


def draw_glyph(surface: pygame.Surface, glyph_def: GlyphDef,
               x: int, y: int, size: int, colour: tuple) -> None:
    """Draw a glyph onto surface at (x, y) within a size x size cell."""
    cx = x + size / 2
    cy = y + size / 2
    lw = _line_width(size)
    half = size * glyph_def.primary_length / 2

    # Primary axis
    dx = math.cos(glyph_def.primary_angle) * half
    dy = math.sin(glyph_def.primary_angle) * half
    px0, py0 = cx - dx, cy - dy
    px1, py1 = cx + dx, cy + dy
    _stroke(surface, colour, px0, py0, px1, py1, lw)

    # Secondary arms
    for i, (arm_angle, arm_length, attach_t) in enumerate(glyph_def.arms):
        # Attachment point along primary
        ax = px0 + (px1 - px0) * attach_t
        ay = py0 + (py1 - py0) * attach_t
        arm_half = size * arm_length
        adx = math.cos(arm_angle) * arm_half
        ady = math.sin(arm_angle) * arm_half
        arm_end_x = ax + adx
        arm_end_y = ay + ady
        _stroke(surface, colour, ax, ay, arm_end_x, arm_end_y, lw)

        # Tertiary tick at arm end
        if i < len(glyph_def.ticks) and glyph_def.ticks[i]:
            tick_perp = arm_angle + math.pi / 2
            tick_len = size * 0.06
            t_dx = math.cos(tick_perp) * tick_len
            t_dy = math.sin(tick_perp) * tick_len
            _stroke(surface, colour,
                    arm_end_x - t_dx, arm_end_y - t_dy,
                    arm_end_x + t_dx, arm_end_y + t_dy, lw)

    # Optional frame
    if glyph_def.frame:
        _draw_frame(surface, glyph_def.frame, x, y, size, colour, lw)

    # Accent strokes
    for start_t, acc_angle, acc_length in glyph_def.accent_strokes:
        ax = px0 + (px1 - px0) * start_t
        ay = py0 + (py1 - py0) * start_t
        acc_half = size * acc_length
        _stroke(surface, colour,
                ax, ay,
                ax + math.cos(acc_angle) * acc_half,
                ay + math.sin(acc_angle) * acc_half, lw)


def _draw_frame(surface: pygame.Surface, frame: str,
                x: int, y: int, size: int, colour: tuple, lw: int) -> None:
    """Draw a partial frame enclosure."""
    margin = int(size * 0.1)
    r = pygame.Rect(x + margin, y + margin,
                    size - margin * 2, size - margin * 2)

    if frame == "arc_left":
        arc_rect = pygame.Rect(r.left - r.width // 2, r.top,
                               r.width, r.height)
        pygame.draw.arc(surface, colour, arc_rect,
                        -math.pi / 2, math.pi / 2, lw)
    elif frame == "arc_right":
        arc_rect = pygame.Rect(r.right - r.width // 2, r.top,
                               r.width, r.height)
        pygame.draw.arc(surface, colour, arc_rect,
                        math.pi / 2, 3 * math.pi / 2, lw)
    elif frame == "corner_tl":
        _stroke(surface, colour, r.left, r.bottom, r.left, r.top, lw)
        _stroke(surface, colour, r.left, r.top, r.right, r.top, lw)
    elif frame == "corner_br":
        _stroke(surface, colour, r.right, r.top, r.right, r.bottom, lw)
        _stroke(surface, colour, r.left, r.bottom, r.right, r.bottom, lw)


# ------------------------------------------------------------------ #
#  Word rendering
# ------------------------------------------------------------------ #

# Module-level cache: phoneme → GlyphDef (keyed by (phoneme, size))
_glyph_cache: dict[tuple[str, int], GlyphDef] = {}

# Phoneme data loaded on first use
_phoneme_data: dict | None = None
_word_decompositions: dict[str, list[str]] | None = None


def _ensure_phoneme_data() -> None:
    """Load phoneme data from JSON on first use."""
    global _phoneme_data, _word_decompositions
    if _phoneme_data is not None:
        return
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "data" / "deep_tongue_phonemes.json"
    if not p.exists():
        _phoneme_data = {}
        _word_decompositions = {}
        return
    with open(p, encoding="utf-8") as f:
        raw = json.load(f)
    _phoneme_data = {e["phoneme"]: e["glyph_seed"] for e in raw.get("phonemes", [])}
    _word_decompositions = raw.get("word_decompositions", {})


def get_phonemes_for_word(word: str) -> list[str]:
    """Return the phoneme decomposition for a deep tongue word."""
    _ensure_phoneme_data()
    return _word_decompositions.get(word.lower(), [word.lower()])


def get_glyph_for_phoneme(phoneme: str, size: int) -> GlyphDef:
    """Get or create a cached GlyphDef for a phoneme at a given size."""
    _ensure_phoneme_data()
    key = (phoneme, size)
    if key not in _glyph_cache:
        seed = _phoneme_data.get(phoneme, hash(phoneme) & 0xFFFFFF)
        _glyph_cache[key] = generate_glyph(phoneme, seed, size)
    return _glyph_cache[key]


def word_pixel_width(word: str, size: int, spacing: int = 2) -> int:
    """Calculate pixel width of a word rendered as phoneme glyphs."""
    phonemes = get_phonemes_for_word(word)
    if not phonemes:
        return size
    return len(phonemes) * size + max(0, len(phonemes) - 1) * spacing


def draw_word(surface: pygame.Surface, word: str,
              x: int, y: int, size: int, colour: tuple,
              spacing: int = 2) -> int:
    """
    Render a deep tongue word as a sequence of phoneme glyphs.
    Returns the total pixel width drawn.
    """
    phonemes = get_phonemes_for_word(word)
    cx = x
    for i, phoneme in enumerate(phonemes):
        gdef = get_glyph_for_phoneme(phoneme, size)
        draw_glyph(surface, gdef, cx, y, size, colour)
        cx += size
        if i < len(phonemes) - 1:
            cx += spacing
    return cx - x


def get_all_phonemes() -> list[tuple[str, int]]:
    """Return all (phoneme, glyph_seed) pairs for the alphabet display."""
    _ensure_phoneme_data()
    return [(p, s) for p, s in _phoneme_data.items()]
