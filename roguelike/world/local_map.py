# world/local_map.py
from __future__ import annotations
import numpy as np
from config import MAP_WIDTH, MAP_HEIGHT


tile_dt = np.dtype([
    ("terrain",     "U32"),
    ("walkable",    bool),
    ("transparent", bool),
    ("visible",     bool),
    ("explored",    bool),
])


def make_tile(terrain: str, walkable: bool, transparent: bool) -> np.ndarray:
    return np.array(
        (terrain, walkable, transparent, False, False),
        dtype=tile_dt,
    )


BLANK = make_tile("wall", False, False)


class LocalMap:
    def __init__(self, width: int = MAP_WIDTH, height: int = MAP_HEIGHT) -> None:
        self.width  = width
        self.height = height
        self.tiles  = np.full((width, height), fill_value=BLANK, dtype=tile_dt)

        # Light map — RGB float per tile, rebuilt each turn
        # from all active light sources in the scene
        self.light_map = np.zeros((width, height, 3), dtype=np.float32)

        # SubMap links — maps tile (x,y) → submap_id for stairs_down tiles
        self.submap_links: dict[tuple[int, int], str] = {}

    def set_tile(self, x: int, y: int, terrain: str,
                 walkable: bool, transparent: bool) -> None:
        # Import inside the function to avoid circular imports
        from rendering.decor import resolve_functional_variant
        
        # Resolve 'varied_x' to a deterministic specific type using tile coords
        actual_terrain = resolve_functional_variant(terrain, mx=x, my=y)
        
        # Store the actual resolved terrain in the map
        self.tiles[x, y] = make_tile(actual_terrain, walkable, transparent)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    @property
    def visible(self) -> np.ndarray:
        return self.tiles["visible"]

    @property
    def explored(self) -> np.ndarray:
        return self.tiles["explored"]

    @property
    def walkable(self) -> np.ndarray:
        return self.tiles["walkable"]

    @property
    def transparent(self) -> np.ndarray:
        return self.tiles["transparent"]