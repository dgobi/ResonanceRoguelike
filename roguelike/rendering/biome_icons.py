# rendering/biome_icons.py
"""
Procedural 64×64 biome icons drawn with pygame.draw calls.
All colors from the Punolite Plus palette.
Cached after first generation.
"""
from __future__ import annotations
import pygame
import random
from engine.palette import *

_CACHE: dict[tuple[str, int], pygame.Surface] = {}

# ------------------------------------------------------------------ #
#  Drawing functions — one per biome
# ------------------------------------------------------------------ #

def _draw_heath(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill(VOID_BLACK)
    for i in range(10):
        x = 4 + i * 6 + rng.randint(-1, 1)
        h = rng.randint(18, 42)
        pygame.draw.line(surf, FOREST_DEEP, (x, 60), (x, 60 - h), 2)
        pygame.draw.line(surf, LIFE_GREEN, (x - 2, 60 - h + 8), (x, 60 - h), 1)
        pygame.draw.line(surf, LIFE_GREEN, (x + 2, 60 - h + 8), (x, 60 - h), 1)


def _draw_forest(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill(VOID_BLACK)
    for i in range(4):
        cx = 8 + i * 16 + rng.randint(-3, 3)
        cy = 30 + rng.randint(-5, 5)
        r  = rng.randint(10, 16)
        pygame.draw.circle(surf, FOREST_DEEP,   (cx, cy), r)
        pygame.draw.circle(surf, FOREST_DEEP,  (cx - 2, cy - 3), r - 4)
        pygame.draw.line(surf,   RUST_BROWN,   (cx, cy + r), (cx, 62), 3)


def _draw_dungeon(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill(VOID_BLACK)
    for row in range(4):
        offset = (row % 2) * 9
        for col in range(5):
            x = offset + col * 18 - 4
            y = 10 + row * 14
            pygame.draw.rect(surf, DEEP_STONE_BLUE,  (x, y, 16, 12))
            pygame.draw.rect(surf, TEAL_DEEP,  (x + 1, y + 1, 14, 10))
    # Dark archway
    pygame.draw.rect(surf,   VOID_BLACK, (22, 28, 20, 34))
    pygame.draw.circle(surf, VOID_BLACK, (32, 28), 10)


def _draw_plains(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill(VOID_BLACK)
    pygame.draw.rect(surf, DEEP_STONE_BLUE,  (0, 0,  64, 30))
    pygame.draw.rect(surf, MOSS_DARK,  (0, 30, 64, 34))
    for _ in range(12):
        x = rng.randint(2, 60)
        h = rng.randint(4, 10)
        pygame.draw.line(surf, FOREST_DEEP, (x, 62), (x, 62 - h), 1)


def _draw_swamp(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill(DEEP_STONE_BLUE)
    for row in range(3):
        y = 20 + row * 16
        pygame.draw.ellipse(surf, TEAL_DEEP,   (4,  y,     56, 10))
        pygame.draw.ellipse(surf, TEAL_DEEP, (8,  y + 1, 48,  7))
    for _ in range(5):
        x  = rng.randint(5, 55)
        hy = 15 + rng.randint(0, 20)
        pygame.draw.line(surf,    FOREST_DEEP,  (x, 60), (x, hy), 2)
        pygame.draw.ellipse(surf, OLD_GROWTH, (x - 4, hy - 3, 8, 5))


def _draw_mountain(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill(VOID_BLACK)
    peaks = [(12, 48, 24, 8), (32, 44, 52, 5), (20, 52, 48, 6)]
    for (x1, y1, x2, _) in peaks:
        mid     = (x1 + x2) // 2
        snow_h  = (62 - y1) // 3
        pygame.draw.polygon(surf, SLATE_DARK,
                            [(x1, 62), (mid, y1), (x2, 62)])
        pygame.draw.polygon(surf, FROST_WHITE,
                            [(mid - 4, y1 + snow_h), (mid, y1), (mid + 4, y1 + snow_h)])


def _draw_town(surf: pygame.Surface, rng: random.Random) -> None:
    surf.fill(VOID_BLACK)
    pygame.draw.rect(surf, MOSS_DARK, (0, 40, 64, 24))
    buildings = [(4, 20, 18, 22), (24, 15, 18, 27), (44, 22, 16, 20)]
    for (x, y, w, h) in buildings:
        pygame.draw.rect(surf, SLATE_DARK,  (x, y, w, h))
        pygame.draw.rect(surf, SLATE_DARK,  (x + 1, y + 1, w - 2, h - 2))
        roof_mid = x + w // 2
        pygame.draw.polygon(surf, RUST_BROWN,
                            [(x, y), (roof_mid, y - 8), (x + w, y)])
        win_x = x + w // 2 - 3
        win_y = y + h // 2 - 3
        pygame.draw.rect(surf, OLD_GOLD, (win_x, win_y, 6, 6))


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
        surf.fill(DEEP_NOTHING)
        pygame.draw.rect(surf, MIDNIGHT_DEEP, (4, 4, 56, 56), 1)

    _CACHE[key] = surf
    return surf
