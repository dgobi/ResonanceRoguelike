# world/world_map.py
from __future__ import annotations
import enum
from dataclasses import dataclass, field


@dataclass
class TownData:
    """
    Metadata about a generated town, stored on the Chunk.
    Set by generate_town() and serialized to world.json.
    """
    name:            str
    size:            str                       # "small" or "large"
    districts:       list[str]                 # district names present
    bell_state:      str                       # "intact","cracked","spent","missing","destroyed"
    is_festival:     bool
    waystone_pos:    tuple[int, int]
    bell_tower_pos:  tuple[int, int] | None = None
    buildings:       list[dict] = field(default_factory=list)
    creature_spawns: list[dict] = field(default_factory=list)  # [{creature_id, x, y}, ...]


class RegionType(enum.Enum):
    PLAINS   = "plains"
    FOREST   = "forest"
    TOWN     = "town"
    SWAMP    = "swamp"
    MOUNTAIN = "mountain"
    HEATH    = "heath"

    def overmap_tile(self) -> str:
        return {
            RegionType.PLAINS:   "overmap_plains",
            RegionType.FOREST:   "overmap_forest",
            RegionType.TOWN:     "overmap_town",
            RegionType.SWAMP:    "overmap_swamp",
            RegionType.MOUNTAIN: "overmap_mountain",
            RegionType.HEATH:    "overmap_heath",
        }[self]


@dataclass
class SubMap:
    """
    An underground space attached to a surface Chunk.
    Accessed via stairs_down inside the surface chunk.
    entry_x/y: player spawn coordinates within the submap.
    surface_x/y: tile on the surface where the stairs_down was placed.
    layout_id: if set, stamps a hand-crafted JSON layout instead of BSP.
    """
    submap_id:   str
    submap_type: str
    name:        str
    seed:        int
    layout_id:   str  = ""
    generated:   bool = False
    entry_x:     int  = 0
    entry_y:     int  = 0
    surface_x:   int  = 0
    surface_y:   int  = 0
    depth:       int  = 1


class ConnectorType(enum.Enum):
    ROAD    = "road"
    RIVER   = "river"
    PATH    = "path"
    PASS    = "pass"      # mountain pass
    PASSAGE = "passage"   # dungeon/town entrance structure


@dataclass
class EdgeConnector:
    """
    Describes what crosses a chunk boundary on a given edge.
    position: 0.0-1.0, fraction along the edge where the feature crosses.
    """
    connector_type: ConnectorType
    position:       float          # 0.0 = top/left, 1.0 = bottom/right
    feature_id:     str = ""       # e.g. river name, road name
    entrance_type:  str = ""       # entrance structure type for PASSAGE connectors


@dataclass
class Chunk:
    wx:          int
    wy:          int
    region_type: RegionType
    seed:        int
    explored:    bool = False
    visited:     bool = False

    # Zone composition — list of (zone_id, weight) tuples
    # Determined at world gen time, used by local generator
    zones: list[tuple[str, float]] = field(default_factory=list)

    # Procedurally generated name — assigned at world gen time
    name:          str = ""
    name_register: str = "common"

    # Town metadata — set if this chunk is part of a town
    town_id:   int | None = None
    town_role: str | None = None
    town_data: "TownData | None" = None

    # WorldMyth locus marker — True for the single chunk nearest the myth origin
    is_locus:  bool = False

    # SubMaps — underground spaces accessed via stairs_down in this chunk
    submaps:   list = field(default_factory=list)

    # Edge connectors — what crosses each boundary
    # Keys: "north", "south", "east", "west"
    edges: dict[str, list[EdgeConnector]] = field(default_factory=lambda: {
        "north": [],
        "south": [],
        "east":  [],
        "west":  [],
    })

    def add_submap(self, submap_type: str, name: str, seed: int,
                   layout_id: str = "") -> SubMap:
        """Create a SubMap attached to this chunk and return it."""
        sm = SubMap(
            submap_id   = f"submap_{self.wx}_{self.wy}_{len(self.submaps)}",
            submap_type = submap_type,
            name        = name,
            seed        = seed,
            layout_id   = layout_id,
        )
        self.submaps.append(sm)
        return sm

    def add_connector(
        self,
        edge: str,
        connector_type: ConnectorType,
        position: float,
        feature_id:    str = "",
        entrance_type: str = "",
    ) -> EdgeConnector:
        connector = EdgeConnector(connector_type, position, feature_id, entrance_type)
        self.edges[edge].append(connector)
        return connector


class WorldMap:
    def __init__(self, width: int, height: int) -> None:
        self.width  = width
        self.height = height
        self.chunks: dict[tuple[int, int], Chunk] = {}
        self.myth = None   # WorldMyth | None — set after world generation

    def get(self, wx: int, wy: int) -> Chunk | None:
        return self.chunks.get((wx, wy))

    def set(self, chunk: Chunk) -> None:
        self.chunks[(chunk.wx, chunk.wy)] = chunk

    def in_bounds(self, wx: int, wy: int) -> bool:
        return 0 <= wx < self.width and 0 <= wy < self.height

    def mark_explored_radius(self, wx: int, wy: int, radius: int = 1) -> None:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                chunk = self.get(wx + dx, wy + dy)
                if chunk:
                    chunk.explored = True