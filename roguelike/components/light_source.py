# components/light_source.py
from __future__ import annotations
import math
import numpy as np
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from world.local_map import LocalMap


class LightSource:
    """
    A component that makes an entity emit light.
    Attach to player, monsters, furniture, or terrain features.

    color:   RGB tuple — the tint of this light.
             Torch = BELL_BRASS, moonlight = SPIRIT_BLUE,
             corpse-light = VERDANT, void-lantern = RESONANCE_BLOOM
    radius:  tiles of illumination at full intensity
    falloff: how quickly light fades. 1.0 = linear, 2.0 = quadratic
    flicker: if True, radius varies slightly each render tick
    active:  can be toggled off (extinguished torch, closed lantern)
    """

    def __init__(
        self,
        radius:  int                    = 8,
        color:   tuple[int, int, int]   = BELL_BRASS,
        falloff: float                  = 1.8,
        flicker: bool                   = False,
        active:  bool                   = True,
    ) -> None:
        self.radius  = radius
        self.color   = color
        self.falloff = falloff
        self.flicker = flicker
        self.active  = active
        self._flicker_offset: float = 0.0

    def effective_radius(self) -> int:
        """Return radius with optional flicker variance."""
        if not self.flicker:
            return self.radius
        import random
        variance = random.uniform(-1.0, 1.0)
        return max(1, int(self.radius + variance))

    def toggle(self) -> None:
        self.active = not self.active

    def apply_to_light_map(
        self,
        light_map: np.ndarray,
        source_x:  int,
        source_y:  int,
        fov_mask:  np.ndarray,
    ) -> None:
        """
        Add this light source's contribution to the light map.
        Only illuminates tiles that are in the FOV mask.
        Uses distance-based falloff for a natural pool of light.
        """
        if not self.active:
            return

        r   = self.effective_radius()
        w   = light_map.shape[0]
        h   = light_map.shape[1]
        cr  = self.color[0] / 255.0
        cg  = self.color[1] / 255.0
        cb  = self.color[2] / 255.0

        x0  = max(0, source_x - r)
        x1  = min(w, source_x + r + 1)
        y0  = max(0, source_y - r)
        y1  = min(h, source_y + r + 1)

        for x in range(x0, x1):
            for y in range(y0, y1):
                if not fov_mask[x, y]:
                    continue

                dist = math.sqrt(
                    (x - source_x) ** 2 + (y - source_y) ** 2
                )
                if dist > r:
                    continue

                # Intensity: 1.0 at source, 0.0 at radius edge
                intensity = max(0.0, 1.0 - (dist / r) ** self.falloff)

                # Additive blending — multiple sources stack
                light_map[x, y, 0] = min(1.0,
                    light_map[x, y, 0] + cr * intensity)
                light_map[x, y, 1] = min(1.0,
                    light_map[x, y, 1] + cg * intensity)
                light_map[x, y, 2] = min(1.0,
                    light_map[x, y, 2] + cb * intensity)