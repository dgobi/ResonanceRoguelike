# rendering/biome_icons.py
"""
Procedural 64×64 biome icons drawn with pygame.draw calls.
All colors from the Punolite Plus palette.
Cached after first generation.
"""
from __future__ import annotations
import pygame
import random

_CACHE: dict[tuple[str, int], pygame.Surface] = {}

# ------------------------------------------------------------------ #
#  Drawing functions — one per biome
# ------------------------------------------------------------------ #

def _draw_heath(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill((7, 12, 29))
    for i in range(10):
        x = 4 + i * 6 + rng.randint(-1, 1)
        h = rng.randint(18, 42)
        pygame.draw.line(surf, (57, 117, 92), (x, 60), (x, 60 - h), 2)
        pygame.draw.line(surf, (93, 167, 93), (x - 2, 60 - h + 8), (x, 60 - h), 1)
        pygame.draw.line(surf, (93, 167, 93), (x + 2, 60 - h + 8), (x, 60 - h), 1)


def _draw_forest(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill((7, 12, 29))
    for i in range(4):
        cx = 8 + i * 16 + rng.randint(-3, 3)
        cy = 30 + rng.randint(-5, 5)
        r  = rng.randint(10, 16)
        pygame.draw.circle(surf, (40, 80, 50),   (cx, cy), r)
        pygame.draw.circle(surf, (57, 117, 92),  (cx - 2, cy - 3), r - 4)
        pygame.draw.line(surf,   (80, 60, 30),   (cx, cy + r), (cx, 62), 3)


def _draw_dungeon(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill((4, 6, 14))
    for row in range(4):
        offset = (row % 2) * 9
        for col in range(5):
            x = offset + col * 18 - 4
            y = 10 + row * 14
            pygame.draw.rect(surf, (30, 55, 75),  (x, y, 16, 12))
            pygame.draw.rect(surf, (40, 84, 84),  (x + 1, y + 1, 14, 10))
    # Dark archway
    pygame.draw.rect(surf,   (4, 6, 14), (22, 28, 20, 34))
    pygame.draw.circle(surf, (4, 6, 14), (32, 28), 10)


def _draw_plains(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill((7, 12, 29))
    pygame.draw.rect(surf, (20, 35, 60),  (0, 0,  64, 30))
    pygame.draw.rect(surf, (40, 70, 50),  (0, 30, 64, 34))
    for _ in range(12):
        x = rng.randint(2, 60)
        h = rng.randint(4, 10)
        pygame.draw.line(surf, (57, 117, 92), (x, 62), (x, 62 - h), 1)


def _draw_swamp(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill((15, 25, 35))
    for row in range(3):
        y = 20 + row * 16
        pygame.draw.ellipse(surf, (25, 60, 70),   (4,  y,     56, 10))
        pygame.draw.ellipse(surf, (40, 100, 110), (8,  y + 1, 48,  7))
    for _ in range(5):
        x  = rng.randint(5, 55)
        hy = 15 + rng.randint(0, 20)
        pygame.draw.line(surf,    (57, 90, 60),  (x, 60), (x, hy), 2)
        pygame.draw.ellipse(surf, (70, 110, 70), (x - 4, hy - 3, 8, 5))


def _draw_mountain(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill((7, 12, 29))
    peaks = [(12, 48, 24, 8), (32, 44, 52, 5), (20, 52, 48, 6)]
    for (x1, y1, x2, _) in peaks:
        mid     = (x1 + x2) // 2
        snow_h  = (62 - y1) // 3
        pygame.draw.polygon(surf, (50, 75, 95),
                            [(x1, 62), (mid, y1), (x2, 62)])
        pygame.draw.polygon(surf, (180, 200, 210),
                            [(mid - 4, y1 + snow_h), (mid, y1), (mid + 4, y1 + snow_h)])


def _draw_town(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill((7, 12, 29))
    pygame.draw.rect(surf, (35, 50, 40), (0, 40, 64, 24))
    buildings = [(4, 20, 18, 22), (24, 15, 18, 27), (44, 22, 16, 20)]
    for (x, y, w, h) in buildings:
        pygame.draw.rect(surf, (40, 55, 70),  (x, y, w, h))
        pygame.draw.rect(surf, (50, 73, 95),  (x + 1, y + 1, w - 2, h - 2))
        roof_mid = x + w // 2
        pygame.draw.polygon(surf, (80, 60, 40),
                            [(x, y), (roof_mid, y - 8), (x + w, y)])
        win_x = x + w // 2 - 3
        win_y = y + h // 2 - 3
        pygame.draw.rect(surf, (180, 150, 80), (win_x, win_y, 6, 6))


# ------------------------------------------------------------------ #
#  Dispatch table
# ------------------------------------------------------------------ #

_DRAW: dict[str, callable] = {
    "heath":    _draw_heath,
    "forest":   _draw_forest,
    "dungeon":  _draw_dungeon,
    "plains":   _draw_plains,
    "swamp":    _draw_swamp,
    "mountain": _draw_mountain,
    "town":     _draw_town,
}


def get_biome_icon(region_type: str, seed: int = 42) -> pygame.Surface:
    """
    Return a 64×64 Surface with a procedurally drawn biome icon.
    Cached after first draw.
    """
    key = (region_type, seed)
    if key in _CACHE:
        return _CACHE[key]

    surf = pygame.Surface((64, 64))
    draw_fn = _DRAW.get(region_type)
    if draw_fn:
        draw_fn(surf, random.Random(seed))
    else:
        # Unknown biome — plain dark square with a question mark feel
        surf.fill((15, 15, 25))
        pygame.draw.rect(surf, (50, 50, 80), (4, 4, 56, 56), 1)

    _CACHE[key] = surf
    return surf
