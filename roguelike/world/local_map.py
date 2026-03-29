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

        # Decorative overlay layer — (lx, ly) → decor_id string.
        # Rendered above terrain, below entities. Serialised with the chunk.
        # Never write to this directly — use generation.decor_utils.place_decor().
        self.decor: dict[tuple[int, int], str] = {}

        # Corpse tracking — maps tile position to creature tile_id and decay counter.
        # Serialised with the local_map via pickle (CachedChunk).
        self.corpse_data:  dict[tuple[int, int], str] = {}
        self.corpse_decay: dict[tuple[int, int], int] = {}

        # Processing layer — (lx, ly) -> processing entry dict.
        # Replaces the old processing_queue list with O(1) position lookup.
        # Each entry: {
        #   "item_id": str,       # result item to create on completion
        #   "turns_remaining": int,
        #   "source": str,        # "drying" or "cooking"
        #   "decor_id": str,      # processing decor to clear on completion (empty for on_fire)
        #   "on_fire": bool,      # true = cooking on campfire, no decor placed
        #   "completion_message": str,  # per-recipe override
        # }
        # Never write directly — use processing_layer[(lx,ly)] = entry.
        # Serialised with the local_map via pickle (CachedChunk).
        self.processing_layer: dict[tuple[int, int], dict] = {}

        # Backward compat alias — old code that still references processing_queue
        # gets redirected. Will be removed once all references are migrated.
        self.processing_queue: list[dict] = []

        # Floor objects layer — (lx, ly) -> list[Item].
        # Multiple items can occupy the same tile.
        # Never write directly — use generation.floor_object_utils functions.
        # Serialised with the local_map via pickle (CachedChunk).
        self.floor_objects: dict[tuple[int, int], list] = {}

        # Items completed in a hot-cached chunk (player not present).
        # Delivered to floor when player enters the chunk.
        # Each entry: {"item_id": str, "lx": int, "ly": int}
        self.ready_items: list[dict] = []

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