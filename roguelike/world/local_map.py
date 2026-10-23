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
        self.disruption_zones: list[dict] = []  # live map owner; cold maps freeze

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

        # Interacted waystones — set of (lx, ly) that the player has already
        # examined for deep tongue learning. Prevents repeat word grants.
        self.interacted_waystones: set[tuple[int, int]] = set()

        # Examined steles — set of (lx, ly) that have already taught words.
        self.examined_steles: set[tuple[int, int]] = set()

        # Waystone inscriptions — maps (lx, ly) → text_id string.
        # Selected once per waystone, persists across examinations.
        # Serialised with the local_map via pickle (CachedChunk).
        self.waystone_inscriptions: dict[tuple[int, int], str] = {}

        # Bell inscriptions — maps (lx, ly) → text_id string.
        # Selected once per bell, persists across examinations.
        self.bell_inscriptions: dict[tuple[int, int], str] = {}

        # Examined bells — set of (lx, ly) that have already taught words.
        self.examined_bells: set[tuple[int, int]] = set()

        # Stele text IDs — maps (lx, ly) → text_id string.
        # Set during layout stamping for stele special tiles.
        # Serialised with the local_map via pickle (CachedChunk).
        self.stele_text_ids: dict[tuple[int, int], str] = {}

        # Container state — (lx, ly) -> container entry dict.
        # Each entry: {
        #   "state": "closed" | "open" | "looted",
        #   "items": [serialised item dicts],
        #   "decor_id": str,  # the container's closed decor id
        # }
        # Never write directly — use generation.floor_object_utils container API.
        # Serialised with the local_map via pickle (CachedChunk).
        self.container_state: dict[tuple[int, int], dict] = {}

        # Vine networks — growing terrain/decor patterns managed by vine_system.py.
        # Each entry: {tiles, eyestalks, spore_vents, origin, age}
        # Serialised with the local_map via pickle (CachedChunk).
        self.vine_networks: list[dict] = []

    # Terrain IDs where plants may grow — grass and soil only
    _PLANT_VALID_TERRAIN = frozenset({
        "grass", "varied_grass", "mud", "packed_earth", "dirt_path",
        "tall_grass", "brambles",
    })

    def set_tile(self, x: int, y: int, terrain: str,
                 walkable: bool, transparent: bool) -> None:
        # Import inside the function to avoid circular imports
        from rendering.decor import resolve_functional_variant, PLANT_DECOR_IDS

        # Resolve 'varied_x' to a deterministic specific type using tile coords
        actual_terrain = resolve_functional_variant(terrain, mx=x, my=y)

        # Plants go to decor layer, terrain stays as grass underneath
        if actual_terrain in PLANT_DECOR_IDS:
            # Only place plant if terrain is valid AND no existing decor
            if terrain in self._PLANT_VALID_TERRAIN and (x, y) not in self.decor:
                from generation.decor_utils import place_decor
                self.tiles[x, y] = make_tile("grass", walkable, transparent)
                place_decor(self, x, y, actual_terrain)
            else:
                # Invalid terrain or decor collision — just place grass
                self.tiles[x, y] = make_tile("grass", walkable, transparent)
        else:
            self.tiles[x, y] = make_tile(actual_terrain, walkable, transparent)
            # Clear any plant decor when terrain is overwritten (e.g. road carved over grass)
            if (x, y) in self.decor and self.decor[(x, y)] in PLANT_DECOR_IDS:
                del self.decor[(x, y)]

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