# generation/town_gen.py
"""
Town generator. Called by region_gen for RegionType.TOWN chunks.

Architecture (new 3×3, plaza-anchored):
  - 3×3 chunk footprint per town.
  - Centre chunk holds the plaza (bell tower + waystone plinth).
  - Cardinal chunks hold the inner grid (streets + buildings).
  - Corner chunks hold the outer ring (organic scatter + dirt tracks).
  - All tunable values read from data/generation/town_config.json.
  - Building categories auto-discovered from data/buildings/ subdirs.

Legacy 2×2 code retained below the new code until Phase 5 cleanup.
"""
from __future__ import annotations
import json
import random
from generation.context import stable_seed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.local_map import LocalMap
    from world.world_map import Chunk


# ------------------------------------------------------------------ #
#  BuildingDef dataclass
# ------------------------------------------------------------------ #

@dataclass
class BuildingDef:
    """Represents one loaded building layout."""
    id:         str
    category:   str
    layout:     list[str]      # 2D array of tile chars (rows top→bottom)
    allowed_in: str            = "town"
    weight:     float          = 1.0
    width:      int            = 0
    height:     int            = 0
    legend:     dict           = field(default_factory=dict)
    has_submap: bool           = False

    def __post_init__(self) -> None:
        if self.layout:
            self.height = len(self.layout)
            self.width  = max(len(row) for row in self.layout) if self.layout else 0


# ------------------------------------------------------------------ #
#  BuildingLoader
# ------------------------------------------------------------------ #

class BuildingLoader:
    """
    Scans data/buildings/ for subdirectory categories and loads all
    JSON building layouts. Each subdirectory name is a category.
    Adding a new category folder makes it available automatically.

    Also loads plaza variants from data/buildings/plaza/.
    """

    def __init__(self, buildings_root: str = "data/buildings") -> None:
        self._root:    Path                    = Path(buildings_root)
        self.buildings: dict[str, list[BuildingDef]] = {}  # category → [BuildingDef]
        self.plazas:    list[BuildingDef]      = []

    def load(self) -> None:
        """Scan and load all building JSONs. Call once at startup."""
        if not self._root.exists():
            print(f"Warning: buildings root not found: {self._root}")
            return

        for subdir in sorted(self._root.iterdir()):
            if not subdir.is_dir():
                continue
            category = subdir.name
            defs: list[BuildingDef] = []
            for fpath in sorted(subdir.glob("*.json")):
                bdef = self._load_file(fpath, category)
                if bdef is None:
                    continue
                defs.append(bdef)
                if category == "plaza":
                    self.plazas.append(bdef)
            if defs:
                self.buildings[category] = defs

        # Print summary
        counts = " ".join(
            f"{cat}={len(lst)}"
            for cat, lst in sorted(self.buildings.items())
            if cat != "plaza"
        )
        plaza_n = len(self.plazas)
        print(f"Town buildings loaded: {counts} | plaza={plaza_n}")

    def _load_file(self, path: Path, category: str) -> "BuildingDef | None":
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: failed to load building {path}: {e}")
            return None

        bid = data.get("id")
        if not bid:
            print(f"Warning: building {path} has no 'id', skipping.")
            return None

        # Accept 'layout' or 'layers' as the 2D array field
        layout = data.get("layout") or data.get("layers") or []
        if not layout:
            print(f"Warning: building {bid} has no layout/layers, skipping.")
            return None

        has_submap = "submap" in data
        if has_submap:
            print(f"  [submap stub] {bid} has 'submap' field — noted, not processed.")

        return BuildingDef(
            id         = bid,
            category   = category,
            layout     = layout,
            allowed_in = data.get("allowed_in", "town"),
            weight     = float(data.get("weight", 1.0)),
            legend     = data.get("legend", {}),
            has_submap = has_submap,
        )

    def get(self, category: str) -> list[BuildingDef]:
        """Return all BuildingDef entries for a category."""
        return self.buildings.get(category, [])

    def pick(
        self,
        category: str,
        rng: random.Random,
        allowed_in: str = "town",
    ) -> "BuildingDef | None":
        """
        Return a weighted-random BuildingDef from a category,
        filtered by allowed_in. Returns None if no valid entries.
        """
        pool = [
            b for b in self.buildings.get(category, [])
            if b.allowed_in in (allowed_in, "both")
        ]
        if not pool:
            return None
        weights = [b.weight for b in pool]
        return rng.choices(pool, weights=weights, k=1)[0]

    def pick_plaza(self, rng: random.Random) -> "BuildingDef | None":
        """Return a weighted-random plaza variant."""
        if not self.plazas:
            return None
        weights = [p.weight for p in self.plazas]
        return rng.choices(self.plazas, weights=weights, k=1)[0]


# ------------------------------------------------------------------ #
#  Module-level singleton (populated by data_loader via wire_building_loader)
# ------------------------------------------------------------------ #

_building_loader: "BuildingLoader | None" = None


def wire_building_loader(loader: "BuildingLoader") -> None:
    """Called by data_loader after BuildingLoader.load() to make it available here."""
    global _building_loader
    _building_loader = loader


def get_building_loader() -> "BuildingLoader | None":
    return _building_loader

# ------------------------------------------------------------------ #
#  Constants
# ------------------------------------------------------------------ #

TOWN_MARGIN  = 3   # wilderness border (tiles) — tight margin, fills more of chunk
COL_STREET_W = 3   # N-S street width (tiles)
ROW_STREET_H = 3   # E-W street height (tiles)
MIN_BLOCK_W  = 10
MAX_BLOCK_W  = 24
MIN_BLOCK_H  = 8
MAX_BLOCK_H  = 18

# Building categories per district
DISTRICT_BUILDINGS: dict[str, list[str]] = {
    "waystone_square": ["civic"],
    "bell_quarter":    ["civic"],
    "residential":     ["residential", "storage", "ruins"],
    "market_quarter":  ["commercial", "storage", "residential"],
    "ossuary":         ["religious", "ruins"],
}

# Creature pools per district: (creature_id, spawn_chance)
DISTRICT_CREATURES: dict[str, list] = {
    "waystone_square": [
        ("barrow_wight",    0.3),
        ("hollow_revenant", 0.5),
        ("grave_thing",     0.2),
    ],
    "bell_quarter": [
        ("hollow_knight",   0.2),
        ("barrow_wight",    0.4),
        ("hollow_revenant", 0.4),
    ],
    "residential": [
        ("grave_thing",     0.5),
        ("plague_crow",     0.3),
        ("hollow_revenant", 0.2),
    ],
    "market_quarter": [
        ("grave_thing",     0.4),
        ("highland_bandit", 0.05),
        ("plague_crow",     0.35),
        ("hollow_revenant", 0.2),
    ],
    "ossuary": [
        ("drowned_revenant", 0.4),
        ("barrow_wight",     0.4),
        ("grave_thing",      0.2),
    ],
}

DISTRICT_DENSITY: dict[str, tuple[int, int]] = {
    "waystone_square": (2, 4),
    "bell_quarter":    (2, 4),
    "residential":     (3, 6),
    "market_quarter":  (2, 4),
    "ossuary":         (2, 3),
}

BELL_STATES  = ["intact", "cracked", "spent",  "missing", "destroyed"]
BELL_WEIGHTS = [15,       25,        30,        20,        10        ]


# ------------------------------------------------------------------ #
#  3×3 town generation — Phases 2, 3, 4
# ------------------------------------------------------------------ #

_NEW_ROLES = {"NW", "N", "NE", "W", "C", "E", "SW", "S", "SE"}

# Config-driven constants (matching data/generation/town_config.json)
_SECONDARY_W        = 3         # secondary street width in tiles
_SECONDARY_NS_COUNT = (1, 2)    # cross-street count range for N/S chunks
_SECONDARY_EW_COUNT = (2, 3)    # cross-street count range for E/W chunks
_INNER_LAMP_STEP    = 6         # lamps.inner_grid_spacing
_OUTER_LAMP_STEP    = 14        # lamps.outer_ring_spacing
_SCATTER_ATTEMPTS   = 40        # outer_ring.scatter_attempts
_EDGE_DEPTH         = 10        # tiles-from-edge that count as "outer ring"
_DIRT_TRACK_W       = 2         # dirt track width in tiles
_PATH_WANDER        = 0.25      # outer_ring.path_wander_chance
# Lamp state probability (working, sputtering) — dead = remainder
_LAMP_P_PLAZA  = (0.25, 0.45)
_LAMP_P_INNER  = (0.08, 0.25)
_LAMP_P_OUTER  = (0.01, 0.12)


def _artery_positions(map_w: int, map_h: int) -> tuple[int, int, int, int]:
    """Return (ns_x0, ns_x1_excl, ew_y0, ew_y1_excl) for 3-wide arteries."""
    return (
        map_w // 2 - 1,
        map_w // 2 + 2,
        map_h // 2 - 1,
        map_h // 2 + 2,
    )


def _stamp_artery(
    local_map,
    terrain_data: dict,
    axis: str,
    a0: int, a1: int,
    length: int,
) -> set:
    """Stamp cobblestone for one artery. Returns stamped tile set."""
    tiles: set = set()
    for a in range(a0, a1):
        for b in range(length):
            x, y = (a, b) if axis == "ns" else (b, a)
            if local_map.in_bounds(x, y):
                _set_terrain(local_map, x, y, "cobblestone", terrain_data)
                tiles.add((x, y))
    return tiles


def _stamp_secondary_streets(
    local_map,
    terrain_data: dict,
    perp_axis: str,     # "ew" = horizontal streets; "ns" = vertical streets
    count: int,
    width: int,
    full_length: int,   # how far the streets span (the other dimension)
    full_breadth: int,  # dimension streets are distributed across
    margin: int,
) -> set:
    """
    Stamp evenly-distributed secondary cross-streets.
    perp_axis='ew': horizontal bands at evenly spaced y values.
    perp_axis='ns': vertical bands at evenly spaced x values.
    """
    tiles: set = set()
    avail = full_breadth - 2 * margin - count * width
    if count <= 0 or avail <= 0:
        return tiles
    step = max(1, avail // (count + 1))
    pos = margin + step
    for _ in range(count):
        for w in range(width):
            a = pos + w
            for b in range(full_length):
                x, y = (b, a) if perp_axis == "ew" else (a, b)
                if local_map.in_bounds(x, y):
                    _set_terrain(local_map, x, y, "cobblestone", terrain_data)
                    tiles.add((x, y))
        pos += step + width
    return tiles


_DECOR_TERRAIN_IDS = {"waystone_plinth", "stele", "street_lamp_working",
                      "street_lamp_sputtering", "street_lamp_dead"}

def _stamp_plaza_def(
    local_map,
    plaza: "BuildingDef",
    ox: int,
    oy: int,
    terrain_data: dict,
) -> None:
    """Stamp a BuildingDef plaza (legend-based layout) at top-left (ox, oy)."""
    from generation.decor_utils import place_decor as _pd_plaza
    for row_idx, row in enumerate(plaza.layout):
        for col_idx, ch in enumerate(row):
            terrain = plaza.legend.get(ch)
            if terrain is None:
                continue
            tx = ox + col_idx
            ty = oy + row_idx
            if local_map.in_bounds(tx, ty):
                if terrain in _DECOR_TERRAIN_IDS:
                    # Place as decor on top of existing floor tile
                    _pd_plaza(local_map, tx, ty, terrain)
                else:
                    _set_terrain(local_map, tx, ty, terrain, terrain_data)


def _find_plaza_tile(
    plaza: "BuildingDef",
    terrain_id: str,
    ox: int,
    oy: int,
) -> "tuple[int,int] | None":
    """Find the first occurrence of terrain_id in the plaza layout; return world coord."""
    for ch, t in plaza.legend.items():
        if t == terrain_id:
            for row_idx, row in enumerate(plaza.layout):
                for col_idx, c in enumerate(row):
                    if c == ch:
                        return (ox + col_idx, oy + row_idx)
    return None


def _pick_raw_building(
    category: str,
    building_data: dict,
    rng: random.Random,
) -> "dict | None":
    """Return a weighted-random raw building dict from building_data[category]."""
    pool = building_data.get(category, [])
    if not pool:
        return None
    weights = [float(b.get("weight", 1.0)) for b in pool]
    return rng.choices(pool, weights=weights, k=1)[0]


def _try_stamp_buildings(
    local_map,
    terrain_data: dict,
    building_data: dict,
    rng: random.Random,
    categories: list[str],
    zone: tuple[int, int, int, int],
    max_buildings: int = 4,
    south_align: bool = True,
    flip_v: bool = False,
    _debug_label: str = "",
) -> tuple[list[dict], int]:
    """Pack buildings into a zone and return the placed list.

    south_align=True (default): row-packs left-to-right along the bottom edge of the
    zone, then starts a second row above the first if space permits.  This eliminates
    the random-x overlap problem that produced 60+ wasted attempts per zone.

    south_align=False: random scatter (used for interior/non-aligned fills).
    """
    from config import DEBUG_MODE
    placed: list[dict] = []
    zx0, zy0, zw, zh = zone
    if zw < 8 or zh < 6:
        if DEBUG_MODE:
            print(f"[town_gen] {_debug_label} zone ({zx0},{zy0},{zw},{zh}) too small — skipped")
        return placed, 0

    _skip_no_bld  = 0
    _skip_too_big = 0
    _skip_overlap = 0
    attempts      = 0

    if south_align:
        # Multi-row pack: fills the zone from south to north, one row at a time.
        # Each row left-to-right cursor-packs buildings against the current bottom edge,
        # then raises the bottom by the tallest building in that row + 1 gap tile.
        # Continues until max_buildings reached or no vertical space remains.
        row_bottom = zy0 + zh - 1   # exclusive bottom of the current row slot

        while len(placed) < max_buildings:
            avail_h = row_bottom - zy0  # rows available from zone top to current bottom
            if avail_h < 4:
                break  # not enough vertical space for any building

            cursor_x   = zx0 + 1
            row_min_y  = None   # topmost building y placed in this row (tracks row height)
            row_placed = 0

            while cursor_x < zx0 + zw - 1 and len(placed) < max_buildings:
                remaining_w = (zx0 + zw - 1) - cursor_x
                if remaining_w < 4:
                    break

                fits = []
                for _c in categories:
                    for b in building_data.get(_c, []):
                        layers = b.get("layers", [])
                        if not layers:
                            continue
                        bw2 = max(len(r) for r in layers)
                        bh2 = len(layers)
                        if bw2 <= remaining_w and 3 <= bh2 <= avail_h - 1:
                            fits.append((_c, b, bw2, bh2))

                if not fits:
                    cursor_x = zx0 + zw   # exhaust this horizontal pass
                    _skip_too_big += 1
                    break

                attempts += 1
                _c, bld, bw, bh = rng.choice(fits)
                ox = cursor_x
                oy = row_bottom - bh   # pack against the current row bottom

                if DEBUG_MODE:
                    print(f"[town_gen] {_debug_label} SLOT ox={ox} oy={oy} bw={bw} bh={bh} row_bottom={row_bottom}")

                if _plot_is_clear(local_map, ox, oy, bw, bh):
                    _item_specs = _stamp_building_at(local_map, bld, ox, oy, terrain_data, flip_v=flip_v)
                    placed.append({
                        "id": bld.get("id", "unknown"),
                        "x": ox, "y": oy, "w": bw, "h": bh,
                        "district": _c,
                        "loot_table": bld.get("interior_loot_table"),
                        "item_specs": _item_specs,
                    })
                    if row_min_y is None or oy < row_min_y:
                        row_min_y = oy
                    row_placed += 1
                    cursor_x += bw
                else:
                    _skip_overlap += 1
                    cursor_x += bw

            if row_placed == 0:
                break  # couldn't fit anything in this pass — stop

            # Raise the bottom for the next row: above the tallest building + 1 gap
            row_bottom = row_min_y - 1

    else:
        # Random scatter — used when south_align is explicitly False
        while len(placed) < max_buildings and attempts < max_buildings * 8:
            attempts += 1
            cat = rng.choice(categories)
            bld = _pick_raw_building(cat, building_data, rng)
            if bld is None:
                _skip_no_bld += 1
                continue
            layers = bld.get("layers", [])
            if not layers:
                _skip_no_bld += 1
                continue
            bw = max(len(row) for row in layers)
            bh = len(layers)
            if bw > zw - 2 or bh > zh - 2:
                _skip_too_big += 1
                continue
            ox = rng.randint(zx0 + 1, max(zx0 + 1, zx0 + zw - bw - 1))
            oy = rng.randint(zy0 + 1, max(zy0 + 1, zy0 + zh - bh - 1))
            if _plot_is_clear(local_map, ox, oy, bw, bh):
                _item_specs = _stamp_building_at(local_map, bld, ox, oy, terrain_data, flip_v=flip_v)
                placed.append({
                    "id": bld.get("id", "unknown"),
                    "x": ox, "y": oy, "w": bw, "h": bh,
                    "district": cat,
                    "loot_table": bld.get("interior_loot_table"),
                    "item_specs": _item_specs,
                })
            else:
                _skip_overlap += 1

    if DEBUG_MODE:
        print(
            f"[town_gen] {_debug_label} zone ({zx0},{zy0},{zw},{zh}) "
            f"placed={len(placed)}/{max_buildings}  attempts={attempts}  "
            f"skip_no_bld={_skip_no_bld}  skip_too_big={_skip_too_big}  skip_overlap={_skip_overlap}"
        )
    return placed, attempts


_LAMP_VALID_TERRAIN = frozenset({
    "cobblestone", "flagstone", "cobblestone_cracked", "cobblestone_mossy",
    "packed_earth", "dirt_path", "weedy_cobble", "gravel",
    "grass", "tall_grass",
}) | frozenset(f"road_{i}" for i in range(16))


def _valid_lamp_pos(local_map, terrain_data: dict, x: int, y: int,
                    placed_buildings: list | None = None,
                    plaza_rect: tuple | None = None) -> bool:
    """Return True if (x,y) is a valid position for a street lamp."""
    if not local_map.in_bounds(x, y):
        return False
    if (x, y) in getattr(local_map, 'protected_cells', set()):
        return False
    terrain_id = str(local_map.tiles[x, y]["terrain"])
    if isinstance(terrain_id, bytes):
        terrain_id = terrain_id.decode()
    # Must be a walkable exterior tile
    if terrain_id not in _LAMP_VALID_TERRAIN:
        return False
    # Must not already have a decor tile
    if local_map.decor.get((x, y)):
        return False
    # Must not be inside the plaza bounding rect
    if plaza_rect is not None:
        px, py, pw, ph = plaza_rect
        if px <= x < px + pw and py <= y < py + ph:
            return False
    # Must not be inside a building footprint
    if placed_buildings:
        for bld in placed_buildings:
            bx, by = bld.get("x", 0), bld.get("y", 0)
            bw, bh = bld.get("w", 0), bld.get("h", 0)
            if bx <= x < bx + bw and by <= y < by + bh:
                return False
    return True


def _place_artery_lamps(
    local_map,
    terrain_data: dict,
    town_id: int,
    axis: str,
    a0: int, a1: int,
    skip_a0: int, skip_a1: int,
    length: int,
    step: int = _INNER_LAMP_STEP,
    lamp_probs: tuple = _LAMP_P_INNER,
    placed_buildings: list | None = None,
    plaza_rect: tuple | None = None,
) -> None:
    """Place street lamps flanking an artery, skipping the crossing band."""
    wp, sp = lamp_probs
    for b in range(0, length, step):
        if skip_a0 <= b < skip_a1:
            continue
        for a_off in (a0 - 1, a1):
            x, y = (a_off, b) if axis == "ns" else (b, a_off)
            if not _valid_lamp_pos(local_map, terrain_data, x, y,
                                   placed_buildings, plaza_rect):
                continue
            r = (stable_seed('lamp', x, y, town_id) & 0xFF) / 255.0
            if   r < wp:      lamp = "street_lamp_working"
            elif r < wp + sp: lamp = "street_lamp_sputtering"
            else:             lamp = "street_lamp_dead"
            from generation.decor_utils import place_decor as _pd_lamp
            _pd_lamp(local_map, x, y, lamp)


def _stamp_dirt_track(
    local_map,
    terrain_data: dict,
    start_x: int,
    start_y: int,
    direction: str,
    track_w: int,
    wander_chance: float,
    rng: random.Random,
) -> None:
    """Stamp a gravel dirt track from (start_x, start_y) toward the chunk edge."""
    x, y = start_x, start_y
    while local_map.in_bounds(x, y):
        for dw in range(track_w):
            tx = x + (dw if direction in ("N", "S") else 0)
            ty = y + (dw if direction in ("E", "W") else 0)
            if local_map.in_bounds(tx, ty):
                t = local_map.tiles[tx, ty]["terrain"]
                if isinstance(t, bytes):
                    t = t.decode()
                if t in ("grass", "packed_earth", "tall_grass", "weedy_cobble"):
                    _set_terrain(local_map, tx, ty, "gravel", terrain_data)
        if rng.random() < wander_chance:
            if direction in ("N", "S"):
                x = max(1, min(local_map.width - 2, x + rng.choice([-1, 0, 1])))
            else:
                y = max(1, min(local_map.height - 2, y + rng.choice([-1, 0, 1])))
        if   direction == "N": y -= 1
        elif direction == "S": y += 1
        elif direction == "E": x += 1
        elif direction == "W": x -= 1


def _split_zone_by_streets(
    zone: tuple[int, int, int, int],
    street_tiles: set,
    axis: str,
) -> list[tuple[int, int, int, int]]:
    """Split a zone into sub-zones that exclude street tile rows (axis='y') or
    columns (axis='x').  Returns the original zone unchanged if no streets fall
    inside it.  Handles runs of consecutive blocked rows/cols correctly.

    axis='y': secondary E-W streets (horizontal bands) in N/S chunks.
    axis='x': secondary N-S streets (vertical bands) in E/W chunks.
    """
    zx0, zy0, zw, zh = zone

    if axis == "y":
        blocked: set[int] = set()
        for (sx, sy) in street_tiles:
            if zy0 <= sy < zy0 + zh and zx0 <= sx < zx0 + zw:
                blocked.add(sy)
        if not blocked:
            return [zone]
        segs: list[tuple[int, int, int, int]] = []
        seg_start = zy0
        for y in range(zy0, zy0 + zh):
            if y in blocked:
                if y > seg_start:
                    segs.append((zx0, seg_start, zw, y - seg_start))
                seg_start = y + 1
        if seg_start < zy0 + zh:
            segs.append((zx0, seg_start, zw, zy0 + zh - seg_start))
        return segs if segs else [zone]

    else:  # axis == "x"
        blocked_x: set[int] = set()
        for (sx, sy) in street_tiles:
            if zy0 <= sy < zy0 + zh and zx0 <= sx < zx0 + zw:
                blocked_x.add(sx)
        if not blocked_x:
            return [zone]
        segs_x: list[tuple[int, int, int, int]] = []
        seg_start_x = zx0
        for x in range(zx0, zx0 + zw):
            if x in blocked_x:
                if x > seg_start_x:
                    segs_x.append((seg_start_x, zy0, x - seg_start_x, zh))
                seg_start_x = x + 1
        if seg_start_x < zx0 + zw:
            segs_x.append((seg_start_x, zy0, zx0 + zw - seg_start_x, zh))
        return segs_x if segs_x else [zone]


_PATH_TILES = frozenset({
    "gravel", "cobblestone", "flagstone", "cobblestone_cracked",
    "cobblestone_mossy", "weedy_cobble", "dirt_path", "packed_earth",
})
_PATH_OVERWRITE = frozenset({
    "grass", "varied_grass", "packed_earth", "tall_grass", "mud",
    "flower_pilgrims_woe", "flower_murk_violet",
    "shroom_sulphur_cap", "shroom_prophets_eye",
})


def _connect_building_to_path(
    local_map,
    terrain_data: dict,
    bld_info: dict,
    search_radius: int = 24,
) -> None:
    """Stamp a gravel L-path from the building exit point to the nearest road/path tile.

    The exit point is one tile south of the building's bottom-centre.
    Only overwrites soft terrain — never streets, walls, or water.
    """
    ox, oy = bld_info["x"], bld_info["y"]
    bw, bh = bld_info["w"], bld_info["h"]
    ex = ox + bw // 2
    ey = oy + bh        # one tile below bottom row

    if not local_map.in_bounds(ex, ey):
        return

    # Find nearest path/road tile by Manhattan distance
    best_dist = search_radius + 1
    best_x, best_y = -1, -1
    for dy in range(-search_radius, search_radius + 1):
        for dx in range(-search_radius, search_radius + 1):
            tx, ty = ex + dx, ey + dy
            if not local_map.in_bounds(tx, ty):
                continue
            t = local_map.tiles[tx, ty]["terrain"]
            if isinstance(t, bytes):
                t = t.decode()
            if t in _PATH_TILES:
                d = abs(dx) + abs(dy)
                if d < best_dist:
                    best_dist = d
                    best_x, best_y = tx, ty

    if best_x == -1:
        return  # No road found within radius

    # Stamp L-shaped path: horizontal first, then vertical
    cx, cy = ex, ey
    while cx != best_x:
        if local_map.in_bounds(cx, cy):
            t = local_map.tiles[cx, cy]["terrain"]
            if isinstance(t, bytes):
                t = t.decode()
            if t in _PATH_OVERWRITE:
                _set_terrain(local_map, cx, cy, "gravel", terrain_data)
        cx += 1 if best_x > cx else -1
    while cy != best_y:
        if local_map.in_bounds(cx, cy):
            t = local_map.tiles[cx, cy]["terrain"]
            if isinstance(t, bytes):
                t = t.decode()
            if t in _PATH_OVERWRITE:
                _set_terrain(local_map, cx, cy, "gravel", terrain_data)
        cy += 1 if best_y > cy else -1


def _apply_wfc_fill(
    local_map,
    terrain_data: dict,
    wfc_rng: random.Random,
    tileset_path: str,
    fill_rect: tuple[int, int, int, int],
    terrain_map: dict,
    fallback: str,
) -> None:
    """Stage a bounded solve, or paint an observable fallback on eligible fill only."""
    from generation.context import map_context, stable_seed
    from generation.wfc import WFCSolver
    from pathlib import Path
    x0, y0, w, h = fill_rect
    context = map_context(local_map)
    seed = stable_seed(wfc_rng.getstate())
    reason, grid, staged = '', None, []
    try:
        solver = WFCSolver.from_json(tileset_path, wfc_rng)
        grid = solver.solve(w, h)
        if grid is None:
            reason = 'attempt bound exhausted'
        elif not solver.valid(grid, w, h):
            raise ValueError('solver returned an invalid adjacency grid')
        if grid is not None:
            for lx in range(w):
                for ly in range(h):
                    tile = terrain_map.get(grid[lx][ly], fallback)
                    if tile not in terrain_data:
                        raise ValueError(f'unknown terrain {tile!r}')
                    staged.append((x0 + lx, y0 + ly, tile))
    except Exception as error:
        reason = f'{type(error).__name__}: {error}'
        grid = None
    if grid is None:
        staged = [(x0 + x, y0 + y, fallback) for x in range(w) for y in range(h)]
    protected = getattr(local_map, 'protected_cells', set())
    from rendering.decor import PLANT_DECOR_IDS
    for x, y, terrain in staged:
        if (local_map.in_bounds(x, y) and (x, y) not in protected
                and (x, y) not in local_map.submap_links
                and (x, y) not in local_map.floor_objects
                and (x, y) not in local_map.container_state
                and ((x, y) not in local_map.decor or local_map.decor[x, y] in PLANT_DECOR_IDS)
                and str(local_map.tiles[x, y]['terrain']) in ('grass', 'varied_grass')):
            _set_terrain(local_map, x, y, terrain, terrain_data)
    diagnostic = dict(palette=Path(tileset_path).name, rectangle=list(fill_rect),
                      seed=seed, revision=context.revision,
                      status='solved' if grid is not None else 'fallback', reason=reason)
    if not hasattr(local_map, 'generation_diagnostics'):
        local_map.generation_diagnostics = []
    local_map.generation_diagnostics.append(diagnostic)


def generate_town_chunk(
    chunk,
    local_map:     "LocalMap",
    map_w:         int,
    map_h:         int,
    terrain_data:  dict,
    building_data: dict,
    name_gen,
    rng:           random.Random,
) -> "tuple[LocalMap, tuple[int,int]]":
    """
    Generate one chunk of a 3×3 town.
    C    — both arteries + drift-placed plaza + quad buildings + WFC fill.
    N/S  — N-S artery + 1-2 E-W cross-streets + buildings + WFC fill.
    E/W  — E-W artery + 2-3 N-S cross-streets + buildings + WFC fill.
    NW/NE/SW/SE — outer ring: scatter_attempts buildings (edge-only ruins),
                  dirt track paths toward inner grid, outskirts WFC fill.
    """
    import os
    from world.world_map import TownData

    role = chunk.town_role or "C"
    ns_x0, ns_x1, ew_y0, ew_y1 = _artery_positions(map_w, map_h)

    street_tiles:     set[tuple[int, int]] = set()
    bell_state        = rng.choices(BELL_STATES, weights=BELL_WEIGHTS, k=1)[0]
    bell_tower_pos    = None
    waystone_pos      = (map_w // 2, map_h // 2)
    placed_buildings: list[dict] = []
    town_id           = chunk.town_id if chunk.town_id >= 0 else 0
    _total_attempts   = 0

    from generation.context import map_context
    context = map_context(local_map)
    wfc_rng = context.rng('wfc', town_id, role)
    wfc_base   = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "wfc"))
    block_json = os.path.join(wfc_base, "town_block.json")
    out_json   = os.path.join(wfc_base, "town_outskirts.json")

    BLOCK_MAP = {
        "packed_earth": "packed_earth", "dirt_path":  "dirt_path",
        "weedy_cobble": "weedy_cobble", "mud_patch":  "mud",
        "tall_grass":   "tall_grass",   "debris":     "debris_scatter",
    }
    OUTSKIRTS_MAP = {
        "packed_earth": "packed_earth", "tall_grass": "tall_grass",
        "weedy_cobble": "weedy_cobble", "debris":     "debris_scatter",
        "gravel":       "gravel",
    }
    PLAZA_MAP = {
        "cobble_clean":   "cobblestone",       "cobble_cracked": "cobblestone_cracked",
        "cobble_mossy":   "cobblestone_mossy", "puddle":         "puddle",
        "debris":         "debris_scatter",    "waystone_base":  "waystone_plinth",
    }

    plaza_rect: tuple | None = None  # set in centre chunk if plaza is stamped

    # ── Primary arteries ───────────────────────────────────────────────
    if role in ("C", "N", "S"):
        street_tiles |= _stamp_artery(local_map, terrain_data,
                                      "ns", ns_x0, ns_x1, map_h)
    if role in ("C", "E", "W"):
        street_tiles |= _stamp_artery(local_map, terrain_data,
                                      "ew", ew_y0, ew_y1, map_w)

    # Cardinal band counts are shared with their corner neighbours.
    from generation.ports import secondary_bands
    if role in ('N', 'S', 'E', 'W'):
        ns = role in ('E', 'W')
        for start, width in secondary_bands(context.world_seed, town_id, role, map_w if ns else map_h):
            street_tiles |= _stamp_artery(local_map, terrain_data, 'ns' if ns else 'ew',
                                         start, start + width, map_h if ns else map_w)
    from generation.feature_carving import reserve_town_routes
    reserve_town_routes(local_map, chunk, terrain_data, street_tiles, context)

    # ── Centre chunk ───────────────────────────────────────────────────
    if role == "C":
        bell_state = "missing"
        for x in range(ns_x0, ns_x1):
            for y in range(ew_y0, ew_y1):
                if local_map.in_bounds(x, y):
                    _set_terrain(local_map, x, y, "flagstone", terrain_data)

        loader    = get_building_loader()
        plaza_def = loader.pick_plaza(rng) if loader else None
        plaza_json = os.path.join(wfc_base, "town_plaza.json")

        if plaza_def:
            drift_x = rng.randint(-4, 4)   # drift_range = 8 → ±4
            drift_y = rng.randint(-4, 4)
            ox = max(0, min(map_w - plaza_def.width,
                            map_w // 2 - plaza_def.width  // 2 + drift_x))
            oy = max(0, min(map_h - plaza_def.height,
                            map_h // 2 - plaza_def.height // 2 + drift_y))
            _stamp_plaza_def(local_map, plaza_def, ox, oy, terrain_data)
            # Store plaza bounding rect — used to exclude lamps and bell_dead
            plaza_rect = (ox, oy, plaza_def.width, plaza_def.height)
            # Drifted plaza walls can interrupt an artery between its doors.
            # A reserved perimeter walkway joins all four approaches and actual
            # authored doorways without cutting through the plaza's walls.
            for px in range(ox - 1, ox + plaza_def.width + 1):
                for py in range(oy - 1, oy + plaza_def.height + 1):
                    if not local_map.in_bounds(px, py):
                        continue
                    local_map.protected_cells.add((px, py))
                    if px in (ox - 1, ox + plaza_def.width) or py in (oy - 1, oy + plaza_def.height):
                        _set_terrain(local_map, px, py, 'cobblestone', terrain_data)
                        street_tiles.add((px, py))

            # Plaza bell is always bell_cracked — layout legend is authoritative.
            # bell_state only applies to standalone bell towers (cardinal chunks).
            for bsearch in ("bell_cracked", "bell_intact", "bell_dead"):
                pos = _find_plaza_tile(plaza_def, bsearch, ox, oy)
                if pos:
                    bell_tower_pos = pos
                    bell_state = "cracked"
                    if local_map.in_bounds(pos[0], pos[1]):
                        _set_terrain(local_map, pos[0], pos[1],
                                     "bell_cracked", terrain_data)
                        from generation.decor_utils import place_decor as _pbd
                        _pbd(local_map, pos[0], pos[1], "cracked_bell")
                    break
            pos = _find_plaza_tile(plaza_def, "waystone_plinth", ox, oy)
            if pos:
                waystone_pos = pos

            for row_idx, row in enumerate(plaza_def.layout):
                for col_idx, ch in enumerate(row):
                    t = plaza_def.legend.get(ch)
                    # Authored plaza entrances and paving are the intended street
                    # destination, including its openable perimeter doors.
                    if t and (terrain_data.get(t, {}).get('walkable', False) or t == 'door_closed'):
                        tx2, ty2 = ox + col_idx, oy + row_idx
                        if local_map.in_bounds(tx2, ty2):
                            street_tiles.add((tx2, ty2))

            # WFC fill around plaza intersection
            pz_x0 = max(0,     ns_x0 - 6)
            pz_y0 = max(0,     ew_y0 - 4)
            pz_x1 = min(map_w, ns_x1 + 6)
            pz_y1 = min(map_h, ew_y1 + 4)
            _apply_wfc_fill(local_map, terrain_data, wfc_rng, plaza_json,
                            (pz_x0, pz_y0, pz_x1 - pz_x0, pz_y1 - pz_y0),
                            PLAZA_MAP, "cobblestone_cracked")
        else:
            for x in range(ns_x0 - 4, ns_x1 + 4):
                for y in range(ew_y0 - 4, ew_y1 + 4):
                    if local_map.in_bounds(x, y):
                        _set_terrain(local_map, x, y, "flagstone", terrain_data)
                        street_tiles.add((x, y))

        quad_zones = [
            (TOWN_MARGIN,   TOWN_MARGIN,   ns_x0 - TOWN_MARGIN - 2,         ew_y0 - TOWN_MARGIN - 2),
            (ns_x1 + 2,     TOWN_MARGIN,   map_w - ns_x1 - 2 - TOWN_MARGIN, ew_y0 - TOWN_MARGIN - 2),
            (TOWN_MARGIN,   ew_y1 + 2,     ns_x0 - TOWN_MARGIN - 2,         map_h - ew_y1 - 2 - TOWN_MARGIN),
            (ns_x1 + 2,     ew_y1 + 2,     map_w - ns_x1 - 2 - TOWN_MARGIN, map_h - ew_y1 - 2 - TOWN_MARGIN),
        ]
        centre_cats = ["civic", "religious", "commercial"]
        for qi, zone in enumerate(quad_zones):
            _apply_wfc_fill(local_map, terrain_data, wfc_rng, block_json,
                            zone, BLOCK_MAP, "packed_earth")
            _p, _a = _try_stamp_buildings(local_map, terrain_data, building_data, rng,
                                          centre_cats, zone, max_buildings=5,
                                          flip_v=(qi >= 2),   # qi 2/3 are south of EW road
                                          _debug_label=f"C-quad{qi}")
            placed_buildings.extend(_p)
            _total_attempts += _a

        _place_artery_lamps(local_map, terrain_data, town_id,
                            "ns", ns_x0, ns_x1, ew_y0, ew_y1, map_h,
                            step=_INNER_LAMP_STEP, lamp_probs=_LAMP_P_PLAZA,
                            plaza_rect=plaza_rect)
        _place_artery_lamps(local_map, terrain_data, town_id,
                            "ew", ew_y0, ew_y1, ns_x0, ns_x1, map_w,
                            step=_INNER_LAMP_STEP, lamp_probs=_LAMP_P_PLAZA,
                            plaza_rect=plaza_rect)

    # ── Cardinal N / S ──────────────────────────────────────────────────
    elif role in ("N", "S"):
        cats = ["residential", "commercial", "storage"]
        for zi, zone in enumerate([
            (TOWN_MARGIN, TOWN_MARGIN, ns_x0 - TOWN_MARGIN - 2, map_h - TOWN_MARGIN * 2),
            (ns_x1 + 2,   TOWN_MARGIN, map_w - ns_x1 - 2 - TOWN_MARGIN, map_h - TOWN_MARGIN * 2),
        ]):
            _apply_wfc_fill(local_map, terrain_data, wfc_rng, block_json,
                            zone, BLOCK_MAP, "packed_earth")
            for sub_zone in _split_zone_by_streets(zone, street_tiles, "y"):
                _p, _a = _try_stamp_buildings(local_map, terrain_data, building_data, rng,
                                              cats, sub_zone, max_buildings=8,
                                              _debug_label=f"{role}-zone{zi}")
                placed_buildings.extend(_p)
                _total_attempts += _a

        bell_state = "spent"
        _place_artery_lamps(local_map, terrain_data, town_id,
                            "ns", ns_x0, ns_x1, ew_y0, ew_y1, map_h,
                            step=_INNER_LAMP_STEP, lamp_probs=_LAMP_P_INNER)

    # ── Cardinal E / W ──────────────────────────────────────────────────
    elif role in ("E", "W"):
        cats = ["commercial", "storage", "residential"]
        for zi, zone in enumerate([
            (TOWN_MARGIN, TOWN_MARGIN,   map_w - TOWN_MARGIN * 2, ew_y0 - TOWN_MARGIN - 2),
            (TOWN_MARGIN, ew_y1 + 2,     map_w - TOWN_MARGIN * 2, map_h - ew_y1 - 2 - TOWN_MARGIN),
        ]):
            _apply_wfc_fill(local_map, terrain_data, wfc_rng, block_json,
                            zone, BLOCK_MAP, "packed_earth")
            for sub_zone in _split_zone_by_streets(zone, street_tiles, "x"):
                _p, _a = _try_stamp_buildings(local_map, terrain_data, building_data, rng,
                                              cats, sub_zone, max_buildings=8,
                                              flip_v=(zi == 1),   # zi 1 is south of EW road
                                              _debug_label=f"{role}-zone{zi}")
                placed_buildings.extend(_p)
                _total_attempts += _a

        bell_state = "spent"
        _place_artery_lamps(local_map, terrain_data, town_id,
                            "ew", ew_y0, ew_y1, ns_x0, ns_x1, map_w,
                            step=_INNER_LAMP_STEP, lamp_probs=_LAMP_P_INNER)

    # ── Corner chunks — Phase 3 outer ring ────────────────────────────
    else:
        bell_state = "spent"

        # Phase 4: outskirts WFC fill — runs before building scatter
        _apply_wfc_fill(local_map, terrain_data, wfc_rng, out_json,
                        (TOWN_MARGIN, TOWN_MARGIN,
                         map_w - TOWN_MARGIN * 2, map_h - TOWN_MARGIN * 2),
                        OUTSKIRTS_MAP, "packed_earth")

        # Scatter buildings: ruins/wilderness restricted to edge zone
        from config import DEBUG_MODE as _DBG
        edge_cats     = ["residential", "storage", "ruins", "wilderness"]
        interior_cats = ["residential", "storage"]
        placed_count  = 0
        _sc_no_bld    = 0
        _sc_oob       = 0
        _sc_overlap   = 0
        for attempt_i in range(_SCATTER_ATTEMPTS):
            if placed_count >= 15:
                break
            ox = rng.randint(TOWN_MARGIN, map_w - TOWN_MARGIN - 16)
            oy = rng.randint(TOWN_MARGIN, map_h - TOWN_MARGIN - 10)
            on_edge = (ox < _EDGE_DEPTH
                       or ox > map_w - _EDGE_DEPTH - 16
                       or oy < _EDGE_DEPTH
                       or oy > map_h - _EDGE_DEPTH - 10)
            cats = edge_cats if on_edge else interior_cats
            cat  = rng.choice(cats)
            bld  = _pick_raw_building(cat, building_data, rng)
            if bld is None:
                _sc_no_bld += 1
                continue
            layers = bld.get("layers", [])
            if not layers:
                _sc_no_bld += 1
                continue
            bw = max(len(row) for row in layers)
            bh = len(layers)
            if ox + bw > map_w - TOWN_MARGIN or oy + bh > map_h - TOWN_MARGIN:
                _sc_oob += 1
                continue
            if _plot_is_clear(local_map, ox, oy, bw, bh):
                _item_specs = _stamp_building_at(local_map, bld, ox, oy, terrain_data)
                bld_info = {
                    "id": bld.get("id", "unknown"),
                    "x": ox, "y": oy, "w": bw, "h": bh,
                    "district": cat,
                    "loot_table": bld.get("interior_loot_table"),
                    "item_specs": _item_specs,
                }
                placed_buildings.append(bld_info)
                _connect_building_to_path(local_map, terrain_data, bld_info)
                placed_count += 1
            else:
                _sc_overlap += 1
        if _DBG:
            print(
                f"[town_gen] {role}-scatter  placed={placed_count}/15  "
                f"attempts={attempt_i+1}/{_SCATTER_ATTEMPTS}  "
                f"skip_no_bld={_sc_no_bld}  skip_oob={_sc_oob}  skip_overlap={_sc_overlap}"
            )

        # Sparse lamps
        for lx in range(0, map_w, _OUTER_LAMP_STEP):
            for ly in range(0, map_h, _OUTER_LAMP_STEP):
                jx = lx + rng.randint(-2, 2)
                jy = ly + rng.randint(-2, 2)
                if not local_map.in_bounds(jx, jy):
                    continue
                if not _valid_lamp_pos(local_map, terrain_data, jx, jy,
                                       plaza_rect=plaza_rect):
                    continue
                r = (stable_seed('lamp', jx, jy, town_id) & 0xFF) / 255.0
                wp, sp = _LAMP_P_OUTER
                from generation.decor_utils import place_decor as _pd_lamp2
                if   r < wp:      _pd_lamp2(local_map, jx, jy, "street_lamp_working")
                elif r < wp + sp: _pd_lamp2(local_map, jx, jy, "street_lamp_sputtering")

    for building in placed_buildings:
        local_map.protected_cells.update((x, y)
            for x in range(building['x'], building['x'] + building['w'])
            for y in range(building['y'], building['y'] + building['h']))

    # ── Per-chunk diagnostic summary ───────────────────────────────────
    from config import DEBUG_MODE as _DBG2
    if _DBG2 and _total_attempts > 0:
        _wx = getattr(chunk, "wx", "?")
        _wy = getattr(chunk, "wy", "?")
        print(
            f"[TOWN seed={town_id} wx={_wx} wy={_wy} role={role} "
            f"slots_attempted={_total_attempts} slots_filled={len(placed_buildings)}]"
        )

    # ── District and creature spawns ───────────────────────────────────
    _district_by_role = {
        "C":  "bell_quarter",
        "N":  "residential",   "S": "residential",
        "E":  "market_quarter", "W": "market_quarter",
        "NW": "residential",  "NE": "residential",
        "SW": "ossuary",      "SE": "residential",
    }
    district_for_spawn = _district_by_role.get(role, "residential")
    safe_rect = (TOWN_MARGIN, TOWN_MARGIN,
                 map_w - TOWN_MARGIN * 2, map_h - TOWN_MARGIN * 2)
    creature_spawns = _compute_creature_spawns(
        local_map, [(district_for_spawn, safe_rect)], bell_state, context.rng('population')
    )

    # Aggregate item spawns from all building special_tiles
    item_spawns: list[dict] = []
    for _b in placed_buildings:
        item_spawns.extend(_b.get("item_specs", []))
    # Waystone prayer near the waystone plinth (role "C" chunk)
    if role == "C" and waystone_pos != (map_w // 2, map_h // 2):
        wx_p, wy_p = waystone_pos
        if local_map.in_bounds(wx_p + 1, wy_p):
            item_spawns.append({
                "kind": "item", "item_id": "lab_note",
                "text_id": "waystone_prayer_a",
                "x": wx_p + 1, "y": wy_p,
            })

    chunk.town_data = TownData(
        name            = chunk.name or "Settlement",
        size            = "large",
        districts       = [district_for_spawn],
        bell_state      = bell_state,
        is_festival     = rng.random() < 0.15,
        waystone_pos    = waystone_pos,
        bell_tower_pos  = bell_tower_pos,
        buildings       = placed_buildings,
        creature_spawns = creature_spawns,
        item_spawns     = item_spawns,
    )

    spawn = _find_spawn_on_street(
        local_map, TOWN_MARGIN, TOWN_MARGIN,
        map_w - TOWN_MARGIN * 2, map_h - TOWN_MARGIN * 2,
        street_tiles,
    )
    return local_map, spawn


# ------------------------------------------------------------------ #
#  Terrain stamping helper with validation
# ------------------------------------------------------------------ #

def _set_terrain(
    local_map,
    x: int,
    y: int,
    terrain_name: str,
    terrain_data: dict,
) -> None:
    """Stamp a single terrain tile, warning if the name is unknown."""
    from generation.layout_stamper import _set_tile
    if terrain_name not in terrain_data:
        print(f"[WARNING] town_gen: unknown terrain '{terrain_name}' at ({x},{y})")
        terrain_name = "floor"
    _set_tile(local_map, x, y, terrain_name, terrain_data)


# ------------------------------------------------------------------ #
#  Entry point
# ------------------------------------------------------------------ #

def generate_town(
    chunk,
    local_map:     "LocalMap",
    map_w:         int,
    map_h:         int,
    terrain_data:  dict,
    building_data: dict,
    name_gen,
    rng:           random.Random,
) -> tuple["LocalMap", tuple[int, int]]:
    """
    Stamp a town into local_map (grass base already set).
    Populates chunk.town_data and returns (local_map, spawn_xy).
    """
    from world.world_map import TownData

    # 3×3 multi-chunk mode (new system — 9 roles)
    if chunk.town_role in _NEW_ROLES:
        return generate_town_chunk(chunk, local_map, map_w, map_h,
                                   terrain_data, building_data, name_gen, rng)

    town_x = TOWN_MARGIN
    town_y = TOWN_MARGIN
    town_w = map_w - TOWN_MARGIN * 2
    town_h = map_h - TOWN_MARGIN * 2

    # ── 1: Block grid ────────────────────────────────────────────────
    blocks, col_starts, col_widths, row_starts, row_heights = _generate_block_grid(
        (town_x, town_y, town_w, town_h), rng
    )

    # ── 2: Streets ───────────────────────────────────────────────────
    street_tiles = _stamp_streets(
        local_map,
        col_starts, col_widths,
        row_starts, row_heights,
        town_x, town_y, town_w, town_h,
        terrain_data,
    )

    # ── 3: Special blocks ────────────────────────────────────────────
    waystone_idx, bell_idx = _pick_special_blocks(blocks, rng)

    # ── 4: Bell state ────────────────────────────────────────────────
    bell_state = rng.choices(BELL_STATES, weights=BELL_WEIGHTS, k=1)[0]

    # ── 5: Waystone square ───────────────────────────────────────────
    waystone_pos = _place_waystone_square(
        local_map, blocks[waystone_idx], building_data, terrain_data
    )

    # ── 6: Bell tower ─────────────────────────────────────────────────
    bell_tower_pos = _place_bell_tower(
        local_map, blocks[bell_idx], building_data, terrain_data, bell_state, rng
    )

    # ── 7: Fill blocks with buildings ─────────────────────────────────
    is_festival    = rng.random() < 0.3
    block_districts = _assign_block_districts(blocks, waystone_idx, bell_idx)
    placed_buildings: list[dict] = []

    for idx, block in enumerate(blocks):
        if idx in (waystone_idx, bell_idx):
            continue
        district = block_districts[idx]
        placed_buildings.extend(
            _fill_block_with_buildings(
                local_map, block, district, building_data, terrain_data, rng
            )
        )

    # ── 8: Alleys ─────────────────────────────────────────────────────
    _add_alleys(local_map, blocks, waystone_idx, bell_idx, terrain_data, rng)

    # ── 9: Creature spawns ────────────────────────────────────────────
    district_rects = [
        (block_districts[i], (bx, by, bw, bh))
        for i, (bx, by, bw, bh) in enumerate(blocks)
    ]
    creature_spawns = _compute_creature_spawns(
        local_map, district_rects, bell_state, rng
    )

    # ── Store TownData ────────────────────────────────────────────────
    district_names = list(dict.fromkeys(block_districts.values()))
    _item_spawns: list[dict] = []
    for _b in placed_buildings:
        _item_spawns.extend(_b.get("item_specs", []))
    # Waystone prayer near the waystone plinth
    if waystone_pos:
        wx_p, wy_p = waystone_pos
        if local_map.in_bounds(wx_p + 1, wy_p):
            _item_spawns.append({
                "kind": "item", "item_id": "lab_note",
                "text_id": "waystone_prayer_a",
                "x": wx_p + 1, "y": wy_p,
            })
    chunk.town_data = TownData(
        name            = chunk.name or "Unknown Town",
        size            = "small",
        districts       = district_names,
        bell_state      = bell_state,
        is_festival     = is_festival,
        waystone_pos    = waystone_pos,
        bell_tower_pos  = bell_tower_pos,
        buildings       = placed_buildings,
        creature_spawns = creature_spawns,
        item_spawns     = _item_spawns,
    )

    spawn = _find_spawn_on_street(
        local_map, town_x, town_y, town_w, town_h, street_tiles
    )
    return local_map, spawn


# ------------------------------------------------------------------ #
#  Block grid
# ------------------------------------------------------------------ #

def _generate_block_grid(
    town_rect: tuple[int, int, int, int],
    rng: random.Random,
) -> tuple[list, list, list, list, list]:
    """
    Divide the town footprint into rectangular blocks separated by streets.
    Returns (blocks, col_starts, col_widths, row_starts, row_heights).
    blocks is list of (bx, by, bw, bh).
    """
    tx, ty, tw, th = town_rect

    # --- Columns ---
    n_cols = rng.randint(3, min(5, tw // (MIN_BLOCK_W + COL_STREET_W)))
    n_cols = max(1, n_cols)

    col_starts: list[int] = []
    col_widths: list[int] = []
    x = tx
    remaining_w = tw

    for i in range(n_cols):
        cols_left    = n_cols - i
        streets_left = cols_left - 1   # streets between remaining columns
        min_needed   = cols_left * MIN_BLOCK_W + streets_left * COL_STREET_W
        if remaining_w < min_needed:
            break
        max_bw = min(
            MAX_BLOCK_W,
            remaining_w - (cols_left - 1) * MIN_BLOCK_W - streets_left * COL_STREET_W
        )
        bw = rng.randint(MIN_BLOCK_W, max(MIN_BLOCK_W, max_bw))
        col_starts.append(x)
        col_widths.append(bw)
        x            += bw
        remaining_w  -= bw
        if i < n_cols - 1:
            x           += COL_STREET_W
            remaining_w -= COL_STREET_W

    # --- Rows ---
    n_rows = rng.randint(3, min(4, th // (MIN_BLOCK_H + ROW_STREET_H)))
    n_rows = max(1, n_rows)

    row_starts:  list[int] = []
    row_heights: list[int] = []
    y = ty
    remaining_h = th

    for j in range(n_rows):
        rows_left    = n_rows - j
        streets_left = rows_left - 1
        min_needed   = rows_left * MIN_BLOCK_H + streets_left * ROW_STREET_H
        if remaining_h < min_needed:
            break
        max_bh = min(
            MAX_BLOCK_H,
            remaining_h - (rows_left - 1) * MIN_BLOCK_H - streets_left * ROW_STREET_H
        )
        bh = rng.randint(MIN_BLOCK_H, max(MIN_BLOCK_H, max_bh))
        row_starts.append(y)
        row_heights.append(bh)
        y           += bh
        remaining_h -= bh
        if j < n_rows - 1:
            y           += ROW_STREET_H
            remaining_h -= ROW_STREET_H

    # --- Build block list ---
    blocks = [
        (cs, rs, cw, rh)
        for cs, cw in zip(col_starts, col_widths)
        for rs, rh in zip(row_starts, row_heights)
    ]
    return blocks, col_starts, col_widths, row_starts, row_heights


# ------------------------------------------------------------------ #
#  Street stamping
# ------------------------------------------------------------------ #

def _stamp_streets(
    local_map,
    col_starts:  list[int],
    col_widths:  list[int],
    row_starts:  list[int],
    row_heights: list[int],
    town_x: int, town_y: int,
    town_w: int, town_h: int,
    terrain_data: dict,
) -> set[tuple[int, int]]:
    """
    Stamp cobblestone corridors between blocks.
    E-W streets between rows; N-S streets between columns.
    Intersections stamped with flagstone.
    Returns the full set of street tiles.
    """
    street_tiles: set[tuple[int, int]] = set()

    def _stamp(x: int, y: int, terrain: str) -> None:
        if local_map.in_bounds(x, y):
            _set_terrain(local_map, x, y, terrain, terrain_data)
            street_tiles.add((x, y))

    # E-W streets — corridors between consecutive row bands
    for j in range(len(row_starts) - 1):
        street_y = row_starts[j] + row_heights[j]
        for x in range(town_x, town_x + town_w):
            for dy in range(ROW_STREET_H):
                _stamp(x, street_y + dy, "cobblestone")

    # N-S streets — corridors between consecutive column bands
    for i in range(len(col_starts) - 1):
        street_x = col_starts[i] + col_widths[i]
        for y in range(town_y, town_y + town_h):
            for dx in range(COL_STREET_W):
                _stamp(street_x + dx, y, "cobblestone")

    # Intersections — override with flagstone so crossroads read distinctly
    for i in range(len(col_starts) - 1):
        for j in range(len(row_starts) - 1):
            ix = col_starts[i] + col_widths[i]
            iy = row_starts[j] + row_heights[j]
            for dx in range(COL_STREET_W):
                for dy in range(ROW_STREET_H):
                    _stamp(ix + dx, iy + dy, "flagstone")

    return street_tiles


# ------------------------------------------------------------------ #
#  Special block selection
# ------------------------------------------------------------------ #

def _pick_special_blocks(
    blocks: list, rng: random.Random
) -> tuple[int, int]:
    """
    Pick the waystone block (most central) and bell tower block (perimeter,
    preferring north-east corner).
    Returns (waystone_idx, bell_idx).
    """
    if len(blocks) == 0:
        return 0, 0
    if len(blocks) == 1:
        return 0, 0

    centres_x = [bx + bw // 2 for bx, by, bw, bh in blocks]
    centres_y = [by + bh // 2 for bx, by, bw, bh in blocks]
    mid_x = sum(centres_x) / len(centres_x)
    mid_y = sum(centres_y) / len(centres_y)

    # Waystone: closest to overall centre
    waystone_idx = min(
        range(len(blocks)),
        key=lambda i: (centres_x[i] - mid_x) ** 2 + (centres_y[i] - mid_y) ** 2,
    )

    # Bell: most peripheral, with north+east preference (grey stone quarter feel)
    def _bell_score(i: int) -> float:
        if i == waystone_idx:
            return float("-inf")
        cx, cy = centres_x[i], centres_y[i]
        dist = (cx - mid_x) ** 2 + (cy - mid_y) ** 2
        north_bonus = (mid_y - cy) * 8.0    # prefer smaller y (north)
        east_bonus  = (cx - mid_x) * 3.0    # prefer larger x (east)
        return dist + north_bonus + east_bonus

    bell_idx = max(range(len(blocks)), key=_bell_score)
    return waystone_idx, bell_idx


def _assign_block_districts(
    blocks: list,
    waystone_idx: int,
    bell_idx: int,
) -> dict[int, str]:
    result: dict[int, str] = {}
    for i in range(len(blocks)):
        if i == waystone_idx:
            result[i] = "waystone_square"
        elif i == bell_idx:
            result[i] = "bell_quarter"
        else:
            result[i] = "residential"
    return result


# ------------------------------------------------------------------ #
#  Waystone square
# ------------------------------------------------------------------ #

def _place_waystone_square(
    local_map,
    block_rect:    tuple[int, int, int, int],
    building_data: dict,
    terrain_data:  dict,
) -> tuple[int, int]:
    """Fill the waystone block with flagstone and stamp the plinth at centre."""
    from generation.layout_stamper import stamp_layout_interior
    bx, by, bw, bh = block_rect

    # Flagstone floor — open square
    for x in range(bx, bx + bw):
        for y in range(by, by + bh):
            if local_map.in_bounds(x, y):
                _set_terrain(local_map, x, y, "flagstone", terrain_data)

    cx = bx + bw // 2
    cy = by + bh // 2

    civic  = building_data.get("civic", [])
    plinth = next((b for b in civic if b.get("id") == "waystone_plinth_a"), None)
    if plinth:
        stamp_layout_interior(local_map, plinth, cx, cy, terrain_data)

    return (cx, cy)


# ------------------------------------------------------------------ #
#  Bell tower
# ------------------------------------------------------------------ #

def _place_bell_tower(
    local_map,
    block_rect:    tuple[int, int, int, int],
    building_data: dict,
    terrain_data:  dict,
    bell_state:    str,
    rng:           random.Random,
) -> tuple[int, int] | None:
    from generation.layout_stamper import stamp_layout_interior
    bx, by, bw, bh = block_rect

    civic          = building_data.get("civic", [])
    tower_layouts  = [b for b in civic if b.get("id", "").startswith("bell_tower")]
    if not tower_layouts:
        return None

    layout = _apply_bell_state(dict(rng.choice(tower_layouts)), bell_state)
    tlw    = layout.get("width",  8)
    tlh    = layout.get("height", 10)

    # Centre in the block, clamped so tower doesn't overflow
    cx = bx + bw // 2
    cy = by + tlh // 2 + 1
    cx = max(bx + tlw // 2 + 1, min(bx + bw - tlw // 2 - 1, cx))
    cy = max(by + tlh // 2 + 1, min(by + bh - tlh // 2 - 1, cy))

    stamp_layout_interior(local_map, layout, cx, cy, terrain_data)

    # Place the actual bell tile at the inner chamber centre
    BELL_TERRAIN = {
        "intact":    "bell_intact",
        "cracked":   "bell_cracked",
        "spent":     "bell_dead",
        "destroyed": "bell_dead",
    }
    bell_terrain = BELL_TERRAIN.get(bell_state)
    if bell_terrain:
        bx_bell = cx
        by_bell = cy
        td = terrain_data.get(bell_terrain, {})
        if local_map.in_bounds(bx_bell, by_bell):
            local_map.set_tile(bx_bell, by_bell, bell_terrain,
                               td.get("walkable", False),
                               td.get("transparent", False))
            # Add decor bell on top for visual/interaction layer
            from generation.decor_utils import place_decor as _place_bell_decor
            _BELL_DECOR = {"intact": "intact_bell", "cracked": "cracked_bell",
                           "spent": "bell_dead", "destroyed": "bell_dead"}
            _bd_id = _BELL_DECOR.get(bell_state)
            if _bd_id:
                _place_bell_decor(local_map, bx_bell, by_bell, _bd_id)
            print(f"[town] bell placed: {bell_terrain} at local ({bx_bell},{by_bell})")
    else:
        print(f"[town] bell NOT placed — bell_state={bell_state!r} not in BELL_TERRAIN")

    return (cx, cy)


def _apply_bell_state(layout: dict, bell_state: str) -> dict:
    """Inject a bell-state note into the layout's special_tiles."""
    layout        = dict(layout)
    special_tiles = list(layout.get("special_tiles", []))

    notes = {
        "intact":    "The bell is here. It is intact. It hums faintly.",
        "cracked":   "The bell is cracked. Wind moves through the crack. Do not ring it.",
        "spent":     "The bell remains. It discharged completely. It is safe. Almost.",
        "missing":   None,
        "destroyed": "The bell is gone. What remains is not recognisable.",
    }
    note = notes.get(bell_state)
    if note is not None:
        special_tiles.append({
            "x": 3, "y": 5,
            "type": "item",
            "item_id": "lab_note",
            "text_id": "world_official_a",
            "note": note,
        })

    layout["special_tiles"] = special_tiles
    return layout


# ------------------------------------------------------------------ #
#  Building filling
# ------------------------------------------------------------------ #

def _building_size(bld: dict) -> tuple[int, int]:
    """Return (width, height) computed from layers (not stored .get('width') defaults)."""
    layers = bld.get("layers", [])
    if not layers:
        return (0, 0)
    return (max(len(row) for row in layers), len(layers))


def _get_block_buildings(district_name: str, building_data: dict) -> list[dict]:
    """
    Return a weighted pool of building candidates for a district.
    Each building's district_weights entry determines how many times it
    appears in the pool (higher weight = more likely to be chosen).
    Falls back to all residential buildings if the district has no matches.
    """
    pool: list[dict] = []
    for buildings in building_data.values():
        for bld in buildings:
            w = bld.get("district_weights", {}).get(district_name, 0)
            if w > 0:
                pool.extend([bld] * int(w))
    if not pool:
        pool = building_data.get("residential", [])
    return pool


_CLEAR_TERRAIN = frozenset({
    "grass", "varied_grass", "gravel", "puddle", "debris_scatter",
    "packed_earth", "dirt_path", "mud", "tall_grass",
    # WFC block-fill outputs — must be overwritable so buildings can stamp over them
    "weedy_cobble",
    # Flora variants resolved from varied_grass by set_tile → must be overwritable
    "flower_pilgrims_woe", "flower_murk_violet",
    "shroom_sulphur_cap", "shroom_prophets_eye",
})

# Terrain that is NOT a building but should be allowed in the 1-tile buffer zone
# (roads, cobblestone, flagstone — infrastructure, not structures)
_BUFFER_EXEMPT = frozenset({
    "cobblestone", "cobblestone_cracked", "cobblestone_mossy", "flagstone",
}) | frozenset(f"road_{i}" for i in range(16))


def _plot_is_clear(local_map, ox: int, oy: int, w: int, h: int) -> bool:
    """True if the footprint AND a 1-tile clearance buffer are free of buildings.

    The core footprint (ox..ox+w, oy..oy+h) must be entirely base terrain.
    The 1-tile buffer around it must not contain building tiles (walls, floor,
    doors) — but roads, cobblestone, and out-of-bounds tiles are allowed in
    the buffer zone.

    The buffer prevents wall tiles from adjacent buildings ever touching,
    eliminating cross-junction autotile artifacts and creating natural alleyways.

    Extension point: if a layout has "allow_adjacent": true, callers should
    skip the buffer check for that layout. No layouts currently use this.
    """
    protected = getattr(local_map, 'protected_cells', set())
    if any((x, y) in protected for x in range(ox, ox + w) for y in range(oy, oy + h)):
        return False
    # 1. Core footprint: every tile must be overwritable base terrain
    for x in range(ox, ox + w):
        for y in range(oy, oy + h):
            if not local_map.in_bounds(x, y):
                return False
            t = local_map.tiles[x, y]["terrain"]
            if isinstance(t, bytes):
                t = t.decode()
            if str(t) not in _CLEAR_TERRAIN:
                return False

    # 2. Buffer zone: 1-tile border around footprint must not be a building
    for x in range(ox - 1, ox + w + 1):
        for y in range(oy - 1, oy + h + 1):
            # Skip the core footprint (already checked above)
            if ox <= x < ox + w and oy <= y < oy + h:
                continue
            # Out of bounds is fine — chunk edge, not a building
            if not local_map.in_bounds(x, y):
                continue
            t = local_map.tiles[x, y]["terrain"]
            if isinstance(t, bytes):
                t = t.decode()
            t = str(t)
            # Allow base terrain and road/infrastructure in buffer
            if t in _CLEAR_TERRAIN or t in _BUFFER_EXEMPT:
                continue
            # Anything else (wall, floor, door, etc.) means a building is adjacent
            return False

    return True


def _stamp_building_at(
    local_map,
    building:     dict,
    ox:           int,
    oy:           int,
    terrain_data: dict,
    flip_v:       bool = False,
) -> list[dict]:
    """Stamp a building with its top-left corner at (ox, oy).
    flip_v=True reverses the rows so the entrance (bottom gap) faces north.
    Use for buildings placed south of a road.
    Also stamps the optional decor_layer if present in the building definition.
    Returns a list of item spawn specs with world-space coordinates.
    """
    from generation.decor_utils import place_decor

    layers = building.get("layers", [])
    bh     = len(layers)
    if flip_v:
        layers = list(reversed(layers))
    legend = building.get("legend", {})
    for row_idx, row in enumerate(layers):
        for col_idx, ch in enumerate(row):
            terrain = legend.get(ch)
            if terrain is None:
                continue
            tx = ox + col_idx
            ty = oy + row_idx
            if local_map.in_bounds(tx, ty):
                _set_terrain(local_map, tx, ty, terrain, terrain_data)

    # Optional decorative layer — same grid format as layers, values are decor ids or null
    decor_layer = building.get("decor_layer", [])
    if flip_v:
        decor_layer = list(reversed(decor_layer))
    for row_idx, row in enumerate(decor_layer):
        for col_idx, decor_id in enumerate(row):
            if decor_id is None:
                continue
            tx = ox + col_idx
            ty = oy + row_idx
            place_decor(local_map, tx, ty, decor_id)

    from generation.context import map_context
    from generation.spawn_specs import transformed_specials
    return transformed_specials(building.get('special_tiles', []), map_context(local_map),
                                building.get('id', 'building'), ox, oy, bh, flip_v)


def _fill_block_with_buildings(
    local_map,
    block_rect:    tuple[int, int, int, int],
    district_name: str,
    building_data: dict,
    terrain_data:  dict,
    rng:           random.Random,
) -> list[dict]:
    """
    Fill both the south and north faces of a block with buildings side by side.
    South face: buildings use up to (bh-1) height, south-aligned so doors face the street.
    North face: only stamped if enough vertical space remains above the south buildings.
    Buildings pack left-to-right with shared party walls.
    """
    bx, by, bw, bh = block_rect
    placed: list[dict] = []

    pool = _get_block_buildings(district_name, building_data)
    if not pool:
        return placed

    def _fill_face(start_y_fn, max_h: int) -> None:
        """Pack buildings left-to-right on one horizontal face of the block."""
        x        = bx
        attempts = 0
        while x < bx + bw - 1 and attempts < 20:
            attempts += 1
            remaining_w = bx + bw - x
            fits = [
                b for b in pool
                if _building_size(b)[0] <= remaining_w
                and _building_size(b)[1] <= max_h
            ]
            if not fits:
                x += 2   # small gap skip — try with tighter remaining width
                continue

            building = rng.choice(fits)
            bldw, bldh = _building_size(building)
            ox   = x
            oy   = start_y_fn(bldh)

            if _plot_is_clear(local_map, ox, oy, bldw, bldh):
                _item_specs = _stamp_building_at(local_map, building, ox, oy, terrain_data)
                placed.append({
                    "id":         building.get("id", "unknown"),
                    "x":          ox,
                    "y":          oy,
                    "w":          bldw,
                    "h":          bldh,
                    "district":   district_name,
                    "loot_table": building.get("interior_loot_table"),
                    "item_specs": _item_specs,
                })
            x += bldw   # advance regardless — maintains party-wall spacing

    # South face: allow nearly full block height so proper houses fit.
    # Buildings south-align (door row at block south edge).
    _fill_face(lambda bldh: by + bh - bldh, bh - 1)

    # North face: calculate how much space sits above the tallest south building.
    # Only fill if at least 6 clear rows remain (enough for a cellar or alcove).
    if placed:
        top_of_south = min(bld["y"] for bld in placed)
        north_avail  = top_of_south - by - 1   # rows between block top and south buildings
    else:
        north_avail  = bh   # nothing stamped yet — full height available

    if north_avail >= 6:
        _fill_face(lambda _bldh: by, north_avail)

    return placed


# ------------------------------------------------------------------ #
#  Alleys
# ------------------------------------------------------------------ #

def _add_alleys(
    local_map,
    blocks:       list,
    waystone_idx: int,
    bell_idx:     int,
    terrain_data: dict,
    rng:          random.Random,
) -> None:
    """Stamp narrow gravel alleys through some wide blocks."""
    wide = [
        (i, b) for i, b in enumerate(blocks)
        if b[2] > 18 and i not in (waystone_idx, bell_idx)
    ]
    n_alleys = min(2, len(wide))
    if n_alleys == 0:
        return

    for _, (_, block) in enumerate(rng.sample(wide, n_alleys)):
        bx, by, bw, bh = block
        alley_x = bx + int(bw * rng.uniform(0.35, 0.65))
        for y in range(by, by + bh):
            for dx in range(2):
                sx = alley_x + dx
                if local_map.in_bounds(sx, y):
                    _set_terrain(local_map, sx, y, "gravel", terrain_data)


# ------------------------------------------------------------------ #
#  Creature spawn data
# ------------------------------------------------------------------ #

def _compute_creature_spawns(
    local_map,
    district_rects: list,   # [(district_name, (bx, by, bw, bh)), ...]
    bell_state:     str,
    rng:            random.Random,
) -> list[dict]:
    """
    Return list of {creature_id, x, y} for first-visit spawning.
    Engine reads from chunk.town_data.creature_spawns to place actors.
    """
    spawns: list[dict] = []
    bandit_placed = False

    for district_name, district_rect in district_rects:
        pool = DISTRICT_CREATURES.get(district_name, [])
        if not pool:
            continue

        count_min, count_max = DISTRICT_DENSITY.get(district_name, (2, 4))
        count = rng.randint(count_min, count_max)
        dx, dy, dw, dh = district_rect

        placed   = 0
        attempts = 0
        while placed < count and attempts < count * 30:
            attempts += 1
            creature_id, chance = rng.choice(pool)

            if rng.random() > chance:
                continue
            if creature_id == "hollow_knight" and bell_state not in ("intact", "cracked"):
                continue
            if creature_id == "highland_bandit":
                if bandit_placed:
                    continue
                bandit_placed = True

            tx = rng.randint(dx + 2, max(dx + 3, dx + dw - 3))
            ty = rng.randint(dy + 2, max(dy + 3, dy + dh - 3))
            if not local_map.in_bounds(tx, ty):
                continue
            if local_map.walkable[tx, ty]:
                spawns.append({"creature_id": creature_id, "x": tx, "y": ty})
                placed += 1

    return spawns


# ------------------------------------------------------------------ #
#  Player spawn point
# ------------------------------------------------------------------ #

def _find_spawn_on_street(
    local_map,
    town_x: int, town_y: int,
    town_w: int, town_h: int,
    street_tiles: set[tuple[int, int]],
) -> tuple[int, int]:
    """Find a walkable street tile near the south edge for player entry."""
    cx = town_x + town_w // 2
    for y in range(town_y + town_h - 2, town_y, -1):
        for ddx in range(0, town_w // 2):
            for sx in (cx + ddx, cx - ddx):
                if (sx, y) in street_tiles and local_map.walkable[sx, y]:
                    return (sx, y)

    # Fallback: any walkable street tile
    for sx, sy in street_tiles:
        if local_map.walkable[sx, sy]:
            return (sx, sy)

    return (town_x + town_w // 2, town_y + town_h // 2)
