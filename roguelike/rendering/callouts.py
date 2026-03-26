# rendering/callouts.py
"""
Floating text callouts above world-space positions.
Used for damage numbers, creature sounds, and status effects.
World-space coordinates — system converts tile pos to screen in draw().
"""
from __future__ import annotations
from dataclasses import dataclass
import pygame


# ------------------------------------------------------------------ #
#  Data structures
# ------------------------------------------------------------------ #

@dataclass
class Callout:
    text:         str
    world_x:      float        # tile x (callout appears above tile centre)
    world_y:      float        # tile y
    r: int
    g: int
    b: int
    lifetime:     float        # seconds remaining
    max_lifetime: float        # total lifetime at spawn
    vy:           float = -28.0    # px/s upward drift (negative = up)
    font_size:    str   = "damage" # key into CALLOUT_FONTS dict


# ------------------------------------------------------------------ #
#  CalloutSystem
# ------------------------------------------------------------------ #

class CalloutSystem:
    """Manages all active floating text callouts."""

    MAX = 40   # maximum simultaneous callouts

    def __init__(self) -> None:
        self._callouts: list[Callout] = []

    # ── Add / clear ────────────────────────────────────────────────

    def add(
        self,
        text:      str,
        world_x:   float,
        world_y:   float,
        color:     tuple[int, int, int],
        lifetime:  float = 1.5,
        font_size: str   = "damage",
    ) -> None:
        """Spawn a new callout. Silently dropped if cap is reached."""
        if len(self._callouts) < self.MAX:
            r, g, b = color
            self._callouts.append(Callout(
                text=text,
                world_x=world_x,
                world_y=world_y,
                r=r, g=g, b=b,
                lifetime=lifetime,
                max_lifetime=lifetime,
                font_size=font_size,
            ))

    def clear(self) -> None:
        self._callouts.clear()

    # ── Update ─────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        alive = []
        for c in self._callouts:
            c.lifetime -= dt
            if c.lifetime > 0:
                alive.append(c)
        self._callouts = alive

    # ── Draw ───────────────────────────────────────────────────────

    def draw(
        self,
        surf:          pygame.Surface,
        callout_fonts: "dict | None",
        tile_w:        int,
        tile_h:        int,
        map_origin_x:  int,
        map_origin_y:  int,
        cam_x:         int,
        cam_y:         int,
        viewport:      "pygame.Rect | None" = None,
    ) -> None:
        """
        Render all active callouts.
        callout_fonts: dict mapping font_size strings to pygame.font.Font objects.
                       Comes from display.CALLOUT_FONTS.
        map_origin_x/y: viewport top-left in screen pixels (with shake applied).
        cam_x/y: camera tile offset.
        viewport: clipping rect (optional).
        """
        if not self._callouts or not callout_fonts:
            return

        _fallback = next(iter(callout_fonts.values()), None)
        if _fallback is None:
            return

        if viewport is not None:
            surf.set_clip(viewport)

        for c in self._callouts:
            font = callout_fonts.get(c.font_size, _fallback)
            if font is None:
                continue

            elapsed = c.max_lifetime - c.lifetime
            sx = int(map_origin_x + (c.world_x + 0.5 - cam_x) * tile_w)
            sy = int(map_origin_y + (c.world_y - cam_y) * tile_h
                     + int(c.vy * elapsed))

            # Alpha: full until 70% of lifetime, then linear fade to 0
            frac = 1.0 - (c.lifetime / c.max_lifetime)
            if frac < 0.70:
                alpha = 255
            else:
                alpha = max(0, int(255 * (1.0 - (frac - 0.70) / 0.30)))

            text_surf = font.render(c.text, True, (c.r, c.g, c.b))
            text_surf.set_alpha(alpha)
            surf.blit(text_surf, (sx - text_surf.get_width() // 2, sy))

        if viewport is not None:
            surf.set_clip(None)
