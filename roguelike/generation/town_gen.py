# generation/town_gen.py
"""
Town generator. Called by region_gen for RegionType.TOWN chunks.

Architecture:
  - Wilderness (grass) base — no cobblestone flood-fill.
  - Block grid: rectangular blocks separated by street corridors.
  - Streets stamped as narrow cobblestone corridors between blocks.
  - Buildings fill the south face of each block (facing the street).
  - Waystone square: central block left open as flagstone + plinth.
  - Bell tower: perimeter block, tower stamped in.
  - Alleys: gravel cuts through wide blocks.
"""
from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.local_map import LocalMap
    from world.world_map import Chunk

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
#  2×2 town generation constants
# ------------------------------------------------------------------ #

# Primary road bands in local-chunk coordinates.
# These straddle the chunk seam so roads connect across all 4 chunks.
# N-S road occupies east 4 tiles of left chunks, west 4 tiles of right.
# E-W road occupies south 4 tiles of top chunks, north 4 tiles of bottom.
NS_SEAM_LO = 76    # left chunks:  road at local x = 76..79
NS_SEAM_HI = 4     # right chunks: road at local x = 0..3
EW_SEAM_LO = 39    # top chunks:   road at local y = 39..42
EW_SEAM_HI = 4     # bottom chunks: road at local y = 0..3
SEAM_ROAD_W = 4    # tiles wide

# How many tiles each road band extends from the seam edge into the chunk
ROAD_MARGIN = 3    # keep buildings at least this far from road band edge


def _road_bands_for_role(role: str) -> tuple[tuple[int,int], tuple[int,int]]:
    """
    Return (ns_band, ew_band) as (x_start, x_end_excl) and
    (y_start, y_end_excl) for the primary road bands in a chunk with
    the given role.
    """
    if role in ("NW", "SW"):
        ns = (NS_SEAM_LO, 80)       # x 76-79 (east edge)
    else:
        ns = (0, NS_SEAM_HI)        # x 0-3   (west edge)

    if role in ("NW", "NE"):
        ew = (EW_SEAM_LO, 43)       # y 39-42 (south edge)
    else:
        ew = (0, EW_SEAM_HI)        # y 0-3   (north edge)

    return ns, ew


def _safe_zone_for_role(role: str, map_w: int, map_h: int) -> tuple[int,int,int,int]:
    """
    Return (x0, y0, w, h) of the safe interior zone for block-grid
    placement — avoids all road bands and map edges.
    """
    ns, ew = _road_bands_for_role(role)

    if role in ("NW", "SW"):
        x0 = TOWN_MARGIN
        x1 = ns[0] - ROAD_MARGIN           # left of N-S road
    else:
        x0 = ns[1] + ROAD_MARGIN           # right of N-S road
        x1 = map_w - TOWN_MARGIN

    if role in ("NW", "NE"):
        y0 = TOWN_MARGIN
        y1 = ew[0] - ROAD_MARGIN           # above E-W road
    else:
        y0 = ew[1] + ROAD_MARGIN           # below E-W road
        y1 = map_h - TOWN_MARGIN

    w = max(0, x1 - x0)
    h = max(0, y1 - y0)
    return x0, y0, w, h


def _place_town_lamps(
    local_map,
    terrain_data: dict,
    ns: tuple[int,int],
    ew: tuple[int,int],
    map_w:    int,
    map_h:    int,
    town_id:  int,
) -> None:
    """
    Place street-lamp terrain tiles along the edges of the primary road
    bands. Lamps are placed one tile OUTSIDE the road band so they don't
    block movement on the road itself.

    State distribution is seeded by tile position + town_id:
      near plaza  (dist ≤ 8):  50% working, 30% sputtering, 20% dead
      mid-town   (≤ 20):       20% working, 40% sputtering, 40% dead
      periphery  (> 20):       10% working, 20% sputtering, 70% dead
    """
    ns_cx = (ns[0] + ns[1]) // 2
    ew_cy = (ew[0] + ew[1]) // 2

    def state_for(x: int, y: int) -> str:
        dist = ((x - ns_cx) ** 2 + (y - ew_cy) ** 2) ** 0.5
        h    = hash((x * 7919, y * 6271, town_id)) & 0xFF
        if dist <= 8:
            if h < 128: return "street_lamp_working"
            if h < 204: return "street_lamp_sputtering"
            return "street_lamp_dead"
        elif dist <= 20:
            if h < 51:  return "street_lamp_working"
            if h < 153: return "street_lamp_sputtering"
            return "street_lamp_dead"
        else:
            if h < 26:  return "street_lamp_working"
            if h < 77:  return "street_lamp_sputtering"
            return "street_lamp_dead"

    LAMP_STEP = 8   # place a lamp every N tiles along the road

    # Lamps flanking the E-W road band — one tile above and below
    for x in range(0, map_w, LAMP_STEP):
        if ns[0] <= x < ns[1]:
            continue  # skip the N-S crossing
        for y_off in [ew[0] - 1, ew[1]]:
            if local_map.in_bounds(x, y_off):
                _set_terrain(local_map, x, y_off, state_for(x, y_off), terrain_data)

    # Lamps flanking the N-S road band — one tile left and right
    for y in range(0, map_h, LAMP_STEP):
        if ew[0] <= y < ew[1]:
            continue  # skip the E-W crossing
        for x_off in [ns[0] - 1, ns[1]]:
            if local_map.in_bounds(x_off, y):
                _set_terrain(local_map, x_off, y, state_for(x_off, y), terrain_data)


def generate_town_quadrant(
    chunk,
    local_map,
    map_w:         int,
    map_h:         int,
    terrain_data:  dict,
    building_data: dict,
    rng:           random.Random,
) -> tuple:
    """
    Generate one 2×2 quadrant of a multi-chunk town.
    Uses chunk.town_role ("NW"|"NE"|"SW"|"SE") to determine which
    primary road bands to stamp and which safe zone to fill.
    """
    from world.world_map import TownData

    role = chunk.town_role or "NW"
    ns, ew = _road_bands_for_role(role)

    # ── Primary roads ────────────────────────────────────────────────
    street_tiles: set[tuple[int, int]] = set()

    # N-S road band
    for x in range(ns[0], ns[1]):
        for y in range(map_h):
            if local_map.in_bounds(x, y):
                _set_terrain(local_map, x, y, "road_0", terrain_data)
                street_tiles.add((x, y))

    # E-W road band
    for y in range(ew[0], ew[1]):
        for x in range(map_w):
            if local_map.in_bounds(x, y):
                _set_terrain(local_map, x, y, "road_0", terrain_data)
                street_tiles.add((x, y))

    # Plaza: intersection of both road bands → flagstone
    for x in range(ns[0], ns[1]):
        for y in range(ew[0], ew[1]):
            if local_map.in_bounds(x, y):
                _set_terrain(local_map, x, y, "flagstone", terrain_data)

    # ── Safe zone block grid ─────────────────────────────────────────
    zone_x0, zone_y0, zone_w, zone_h = _safe_zone_for_role(role, map_w, map_h)

    if zone_w < MIN_BLOCK_W or zone_h < MIN_BLOCK_H:
        # Too small — just place a lamp and return
        spawn = _find_spawn_on_street(local_map, 0, 0, map_w, map_h, street_tiles)
        chunk.town_data = TownData(
            name=chunk.name or "Settlement", size="large", districts=[],
            bell_state="spent", is_festival=False,
            waystone_pos=(map_w // 2, map_h // 2), bell_tower_pos=None,
            buildings=[], creature_spawns=[],
        )
        return local_map, spawn

    blocks, col_starts, col_widths, row_starts, row_heights = _generate_block_grid(
        (zone_x0, zone_y0, zone_w, zone_h), rng
    )

    additional_streets = _stamp_streets(
        local_map,
        col_starts, col_widths,
        row_starts, row_heights,
        zone_x0, zone_y0, zone_w, zone_h,
        terrain_data,
    )
    street_tiles.update(additional_streets)

    # ── Special blocks (NW only) ────────────────────────────────────
    bell_state     = rng.choices(BELL_STATES, weights=BELL_WEIGHTS, k=1)[0]
    waystone_pos   = (map_w // 2, map_h // 2)
    bell_tower_pos = None
    placed_buildings: list[dict] = []

    if role == "NW" and len(blocks) >= 2:
        waystone_idx, bell_idx = _pick_special_blocks(blocks, rng)
        block_districts        = _assign_block_districts(blocks, waystone_idx, bell_idx)

        waystone_pos   = _place_waystone_square(local_map, blocks[waystone_idx],
                                                building_data, terrain_data)
        bell_tower_pos = _place_bell_tower(local_map, blocks[bell_idx],
                                           building_data, terrain_data, bell_state, rng)
        for idx, block in enumerate(blocks):
            if idx in (waystone_idx, bell_idx):
                continue
            district = block_districts[idx]
            placed_buildings.extend(
                _fill_block_with_buildings(local_map, block, district,
                                           building_data, terrain_data, rng)
            )
    else:
        # Non-NW chunks fill with district-appropriate buildings
        bell_state = "spent"
        district_cycle = ["residential", "market_quarter", "ossuary", "residential"]
        for idx, block in enumerate(blocks):
            district = district_cycle[idx % len(district_cycle)]
            placed_buildings.extend(
                _fill_block_with_buildings(local_map, block, district,
                                           building_data, terrain_data, rng)
            )

    # ── Alleys ────────────────────────────────────────────────────────
    _add_alleys(local_map, blocks,
                0 if role == "NW" else -1,
                1 if role == "NW" else -1,
                terrain_data, rng)

    # ── WFC ground fill ──────────────────────────────────────────────
    import os
    from generation.wfc import WFCSolver

    wfc_rng = random.Random(hash((chunk.town_id, role)) & 0xFFFFFFFF)

    # Identify building footprints for exclusion
    building_cells: set[tuple[int, int]] = set()
    for bld in placed_buildings:
        for bx2 in range(bld["x"] - 1, bld["x"] + bld["w"] + 1):
            for by2 in range(bld["y"] - 1, bld["y"] + bld["h"] + 1):
                building_cells.add((bx2, by2))

    # Helper: is tile currently a road/structure (skip for WFC)?
    def _is_road_or_structure(x2: int, y2: int) -> bool:
        if not local_map.in_bounds(x2, y2):
            return True
        t2 = local_map.tiles[x2, y2]["terrain"]
        if isinstance(t2, bytes):
            t2 = t2.decode()
        # Roads — don't overwrite
        if str(t2).startswith("road"):
            return True
        # Structures (walls, floors, doors, lamps, stairs) — don't overwrite
        non_overwrit = {"wall", "wood_wall", "floor", "door_closed", "door_open",
                        "stairs_down", "stairs_up", "grey_stone", "ancient_floor",
                        "table", "gravel", "street_lamp_working",
                        "street_lamp_sputtering", "street_lamp_dead"}
        return str(t2) in non_overwrit

    # Plaza WFC (NW chunk only — around road crossing)
    base_path = os.path.join(os.path.dirname(__file__), "..", "data", "wfc")
    plaza_json = os.path.normpath(os.path.join(base_path, "town_plaza.json"))
    block_json = os.path.normpath(os.path.join(base_path, "town_block.json"))

    # WFC tile name → terrain name mapping (from plaza tileset)
    PLAZA_TERRAIN = {
        "cobble_clean":   "cobblestone",
        "cobble_cracked": "cobblestone_cracked",
        "cobble_mossy":   "cobblestone_mossy",
        "puddle":         "puddle",
        "debris":         "debris_scatter",
        "waystone_base":  "waystone_plinth",
    }
    BLOCK_TERRAIN = {
        "packed_earth":  "packed_earth",
        "dirt_path":     "dirt_path",
        "weedy_cobble":  "weedy_cobble",
        "mud_patch":     "mud",
        "tall_grass":    "tall_grass",
        "debris":        "debris_scatter",
    }

    if role == "NW" and os.path.exists(plaza_json):
        ns_cx = (ns[0] + ns[1]) // 2
        ew_cy = (ew[0] + ew[1]) // 2
        px0 = max(0, ns_cx - 8)
        py0 = max(0, ew_cy - 5)
        pw  = min(map_w, ns_cx + 8) - px0
        ph  = min(map_h, ew_cy + 5) - py0
        if pw >= 4 and ph >= 4:
            try:
                solver  = WFCSolver.from_json(plaza_json, wfc_rng)
                grid    = solver.solve(pw, ph)
                fallback_t = "cobblestone_cracked"
                for lx in range(pw):
                    for ly in range(ph):
                        wx2 = px0 + lx
                        wy2 = py0 + ly
                        if (wx2, wy2) in building_cells:
                            continue
                        if _is_road_or_structure(wx2, wy2):
                            continue
                        tile_name = grid[lx][ly] if grid else fallback_t
                        terrain_name = PLAZA_TERRAIN.get(tile_name, fallback_t)
                        _set_terrain(local_map, wx2, wy2, terrain_name, terrain_data)
            except Exception:
                pass   # WFC failure is non-fatal

    # Block interior WFC (all roles)
    if os.path.exists(block_json):
        for bx3, by3, bw3, bh3 in blocks:
            # Define interior as block rect minus 1-tile edge margin
            ix0 = bx3 + 1
            iy0 = by3 + 1
            iw  = bw3 - 2
            ih  = bh3 - 2
            if iw < 4 or ih < 4:
                continue
            try:
                solver  = WFCSolver.from_json(block_json, wfc_rng)
                grid    = solver.solve(iw, ih)
                fallback_t = "packed_earth"
                for lx in range(iw):
                    for ly in range(ih):
                        wx2 = ix0 + lx
                        wy2 = iy0 + ly
                        if (wx2, wy2) in building_cells:
                            continue
                        if _is_road_or_structure(wx2, wy2):
                            continue
                        tile_name = grid[lx][ly] if grid else fallback_t
                        terrain_name = BLOCK_TERRAIN.get(tile_name, fallback_t)
                        _set_terrain(local_map, wx2, wy2, terrain_name, terrain_data)
            except Exception:
                pass

    # ── Street lamps ─────────────────────────────────────────────────
    town_id = chunk.town_id if chunk.town_id >= 0 else 0
    _place_town_lamps(local_map, terrain_data, ns, ew, map_w, map_h, town_id)

    # ── Creature spawns ───────────────────────────────────────────────
    district_name = "bell_quarter" if role == "NW" else "residential"
    district_rects = [(district_name, (zone_x0, zone_y0, zone_w, zone_h))]
    creature_spawns = _compute_creature_spawns(local_map, district_rects, bell_state, rng)

    # ── TownData ──────────────────────────────────────────────────────
    chunk.town_data = TownData(
        name            = chunk.name or "Settlement",
        size            = "large",
        districts       = [district_name],
        bell_state      = bell_state,
        is_festival     = rng.random() < 0.2,
        waystone_pos    = waystone_pos,
        bell_tower_pos  = bell_tower_pos,
        buildings       = placed_buildings,
        creature_spawns = creature_spawns,
    )

    spawn = _find_spawn_on_street(local_map, zone_x0, zone_y0, zone_w, zone_h,
                                  street_tiles)
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

    # 2×2 multi-chunk mode when chunk has a role assigned
    if chunk.town_role:
        return generate_town_quadrant(chunk, local_map, map_w, map_h,
                                      terrain_data, building_data, rng)

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


def _plot_is_clear(local_map, ox: int, oy: int, w: int, h: int) -> bool:
    """True if every tile in the rect is still base terrain (grass/cobblestone/gravel)."""
    for x in range(ox, ox + w):
        for y in range(oy, oy + h):
            if not local_map.in_bounds(x, y):
                return False
            t = local_map.tiles[x, y]["terrain"]
            if isinstance(t, bytes):
                t = t.decode()
            if t not in ("grass", "cobblestone", "gravel", "flagstone", "road_0", "cobblestone_cracked", "cobblestone_mossy", "puddle", "debris_scatter", "packed_earth", "dirt_path", "weedy_cobble", "mud", "tall_grass"):
                return False
    return True


def _stamp_building_at(
    local_map,
    building:     dict,
    ox:           int,
    oy:           int,
    terrain_data: dict,
) -> None:
    """Stamp a building with its top-left corner at (ox, oy)."""
    layers = building.get("layers", [])
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
                if b.get("width",  10) <= remaining_w
                and b.get("height",  8) <= max_h
            ]
            if not fits:
                x += 2   # small gap skip — try with tighter remaining width
                continue

            building = rng.choice(fits)
            bldw = building.get("width",  10)
            bldh = building.get("height",  8)
            ox   = x
            oy   = start_y_fn(bldh)

            if _plot_is_clear(local_map, ox, oy, bldw, bldh):
                _stamp_building_at(local_map, building, ox, oy, terrain_data)
                placed.append({
                    "id":         building.get("id", "unknown"),
                    "x":          ox,
                    "y":          oy,
                    "w":          bldw,
                    "h":          bldh,
                    "district":   district_name,
                    "loot_table": building.get("interior_loot_table"),
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
