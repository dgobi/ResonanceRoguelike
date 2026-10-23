# generation/entrance_gen.py
"""
Entrance architecture.

Public API:
  place_outdoor_entrance(local_map, edge, position, entrance_type, seed, terrain_data)
  place_dungeon_entry(local_map, edge, position, terrain_data)

Layouts come from the explicitly bound caller catalog.
stamp_layout() in layout_stamper.py handles rotation and tile placement.
"""
from __future__ import annotations
import json
import random
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.local_map import LocalMap


# ------------------------------------------------------------------ #
#  Tile helpers (shared with layout_stamper via import)
# ------------------------------------------------------------------ #

_SOLID = {"wall", "rock", "worn_stone", "tree"}
_OPEN  = {
    "floor", "flagstone", "cobblestone", "gravel",
    "grass", "mud", "ash", "water",
    "stairs_down", "stairs_up",
}


def _set(local_map: "LocalMap", x: int, y: int,
         terrain: str, td: dict) -> None:
    if local_map.in_bounds(x, y):
        t = td.get(terrain, td["floor"])
        local_map.set_tile(x, y, terrain, t["walkable"], t["transparent"])
        if terrain in _SOLID:
            local_map.transparent[x, y] = False
            local_map.walkable[x, y]    = False
        elif terrain in _OPEN:
            local_map.transparent[x, y] = True
            local_map.walkable[x, y]    = True


# ------------------------------------------------------------------ #
#  Layout registry (lazy file-based cache)
# ------------------------------------------------------------------ #

def _get_layouts(data=None) -> dict:
    """Use the caller catalog; the standalone default has no global cache."""
    if data is None:
        from engine.data_loader import DataLoader
        data = DataLoader(str(Path(__file__).resolve().parents[1] / 'data'))
    return data.entrances


def _pick_layout(entrance_type: str, rng: random.Random, data=None) -> dict | None:
    """Return a random layout variant for the given entrance_type."""
    layouts = _get_layouts(data)
    variants = [
        v for v in layouts.values()
        if v.get("entrance_type") == entrance_type
    ]
    if not variants:
        return None
    return rng.choice(variants)


# ------------------------------------------------------------------ #
#  Coordinate helpers (kept for place_dungeon_entry)
# ------------------------------------------------------------------ #

def _edge_frame(
    edge: str,
    position: float,
    map_w: int,
    map_h: int,
) -> tuple[int, int, int, int, int, int]:
    if edge == "north":
        ox = int(position * (map_w - 2)) + 1
        return ox, 0,           0,  1,  1, 0
    elif edge == "south":
        ox = int(position * (map_w - 2)) + 1
        return ox, map_h - 1,   0, -1,  1, 0
    elif edge == "west":
        oy = int(position * (map_h - 2)) + 1
        return 0,  oy,          1,  0,  0, 1
    else:  # east
        oy = int(position * (map_h - 2)) + 1
        return map_w - 1, oy,  -1,  0,  0, 1


def _map_xy(ox, oy, a, d, dax, day, dix, diy) -> tuple[int, int]:
    return ox + a * dax + d * dix, oy + a * day + d * diy


# ------------------------------------------------------------------ #
#  Public API
# ------------------------------------------------------------------ #

def place_outdoor_entrance(
    local_map: "LocalMap",
    edge: str,
    position: float,
    entrance_type: str,
    seed: int,
    terrain_data: dict,
    data=None,
) -> None:
    """Place an entrance structure on the outdoor side of a chunk boundary."""
    from generation.layout_stamper import stamp_layout
    rng = random.Random(seed)
    layout = _pick_layout(entrance_type, rng, data=data)
    if layout is None:
        return
    stamp_layout(local_map, layout, edge, position, terrain_data, rng=rng)


def place_dungeon_entry(
    local_map: "LocalMap",
    edge: str,
    position: float,
    terrain_data: dict,
) -> None:
    """
    Carve the dungeon-side entry: 3-wide floor corridor from edge inward,
    widening into a 5-wide antechamber at depth 6–10.
    """
    ox, oy, dix, diy, dax, day = _edge_frame(
        edge, position, local_map.width, local_map.height
    )
    td = terrain_data

    # 3-wide corridor, 8 tiles deep
    for a in range(-1, 2):
        for d in range(0, 9):
            x, y = _map_xy(ox, oy, a, d, dax, day, dix, diy)
            _set(local_map, x, y, "floor", td)

    # 5-wide antechamber at depth 9–13
    for a in range(-2, 3):
        for d in range(9, 14):
            x, y = _map_xy(ox, oy, a, d, dax, day, dix, diy)
            _set(local_map, x, y, "floor", td)
