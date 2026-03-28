# generation/world_gen.py
from __future__ import annotations
import math
import random
from world.world_map import WorldMap, Chunk, RegionType, ConnectorType, SubMap
from world.name_gen import assign_chunk_name


# ------------------------------------------------------------------ #
#  Zone compositions per biome — used by local region generator
# ------------------------------------------------------------------ #

BIOME_ZONES: dict[str, list[tuple[str, float]]] = {
    "plains":        [("heath",      0.6), ("deepwood",  0.1)],
    "forest":        [("deepwood",   0.6), ("briarwood", 0.3), ("mere",      0.1)],
    "swamp":         [("mere",       0.7), ("deepwood",  0.2), ("dead_ground",0.1)],
    "heath":         [("heath",      0.8), ("highstone", 0.2)],
    "mountain":      [("highstone",  0.7), ("barrow",    0.2), ("vault",     0.1)],
    "deep_mountain": [("highstone",  0.5), ("vault",     0.3), ("barrow",    0.2)],
    "drowned_wood":  [("mere",       0.6), ("deepwood",  0.3), ("dead_ground",0.1)],
    "ash_wastes":    [("dead_ground",0.6), ("heath",     0.3), ("highstone", 0.1)],
    "town":          [("hearth",    0.45), ("market",    0.20), ("sanctum",  0.15),
                      ("gate_ward", 0.10), ("pale_quarter",0.05),("undercroft",0.05)],
    "capital":       [("hearth",    0.40), ("market",    0.25), ("sanctum",  0.15),
                      ("gate_ward", 0.10), ("pale_quarter",0.05),("undercroft",0.05)],
}

# Submap probability per biome
SUBMAP_WEIGHTS: dict[str, float] = {
    "plains":        0.06,
    "forest":        0.10,
    "swamp":         0.12,
    "heath":         0.15,
    "mountain":      0.18,
    "drowned_wood":  0.12,
    "ash_wastes":    0.08,
    "deep_mountain": 0.0,
    "town":          0.0,
    "capital":       0.0,
}

# Submap type distribution per biome
SUBMAP_TYPES: dict[str, dict[str, int]] = {
    "plains":       {"barrow": 3,  "vault": 1},
    "forest":       {"barrow": 2,  "cave": 2, "vault": 1},
    "swamp":        {"barrow": 1,  "cave": 2, "vault": 1},
    "heath":        {"barrow": 4,  "cave": 1},
    "mountain":     {"cave": 4,    "vault": 2, "barrow": 1},
    "drowned_wood": {"cave": 2,    "vault": 2},
    "ash_wastes":   {"vault": 2,   "barrow": 2},
}


# ------------------------------------------------------------------ #
#  Top-level pipeline
# ------------------------------------------------------------------ #

def generate_world(world_map: WorldMap, data, rng: random.Random,
                   name_gen=None) -> WorldMap:
    """
    Full world generation pipeline.
    Steps run in strict order — each step depends on the previous.
    """
    world_map.name_gen = name_gen

    # Pre-create all chunks with default values
    for wx in range(world_map.width):
        for wy in range(world_map.height):
            chunk = Chunk(
                wx          = wx,
                wy          = wy,
                region_type = RegionType.PLAINS,
                seed        = rng.randint(0, 999999),
            )
            world_map.set(chunk)

    _place_vukh(world_map, rng)
    _generate_elevation(world_map, rng)
    _generate_moisture(world_map, rng)
    _generate_rivers(world_map, rng)
    _assign_biomes(world_map, data)
    _calculate_resonance(world_map)
    _place_capital(world_map, rng)
    _place_starting_location(world_map, rng)
    _place_towns(world_map, rng)             # Step 9
    _generate_roads(world_map, rng)          # Step 10
    _calculate_difficulty_bands(world_map)   # Step 11

    # Post-processing — zones, submaps, names, myth
    _assign_zones(world_map)
    _assign_submaps(world_map, rng)
    _assign_names(world_map)
    _generate_world_myth(world_map, rng)

    return world_map


# ------------------------------------------------------------------ #
#  Step 1 — VUKH
# ------------------------------------------------------------------ #

def _place_vukh(world_map: WorldMap, rng: random.Random) -> None:
    """
    VUKH always at world centre. Occupies 2×2 chunks.
    Peak tiles: deep_mountain. Adjacent ring (3×3): mountain.
    """
    cx = world_map.width  // 2
    cy = world_map.height // 2
    world_map.vukh_x = cx
    world_map.vukh_y = cy

    # 3×3 ring around peak → mountain first
    for dx in range(-1, 3):
        for dy in range(-1, 3):
            if 0 <= dx <= 1 and 0 <= dy <= 1:
                continue  # peak handled below
            c = world_map.get(cx + dx, cy + dy)
            if c:
                c.elevation   = 0.85
                c.biome_id    = "mountain"
                c.region_type = RegionType.MOUNTAIN

    # 2×2 peak → deep_mountain
    for dx in range(2):
        for dy in range(2):
            c = world_map.get(cx + dx, cy + dy)
            if c:
                c.elevation         = 1.0
                c.biome_id          = "deep_mountain"
                c.region_type       = RegionType.DEEP_MOUNTAIN
                c.is_locus          = False
                c.distance_from_peak = 0.0
                if dx == 0 and dy == 0:
                    c.name = "VUKH"
                world_map.chunk_names[(cx + dx, cy + dy)] = "Vukh"


# ------------------------------------------------------------------ #
#  Step 2 — Elevation
# ------------------------------------------------------------------ #

def _generate_elevation(world_map: WorldMap, rng: random.Random) -> None:
    """
    Elevation radiates from VUKH using inverse distance + noise.
    VUKH = 1.0. World edge approaches 0.0.
    """
    cx, cy   = world_map.vukh_x, world_map.vukh_y
    max_dist = ((world_map.width // 2) ** 2 +
                (world_map.height // 2) ** 2) ** 0.5

    for wx in range(world_map.width):
        for wy in range(world_map.height):
            chunk = world_map.get(wx, wy)
            if not chunk or chunk.elevation == 1.0:
                continue  # skip VUKH peak
            dist = ((wx - cx) ** 2 + (wy - cy) ** 2) ** 0.5
            base  = max(0.0, 1.0 - (dist / max_dist) * 1.2)
            noise = (rng.random() - 0.5) * 0.30
            chunk.elevation         = max(0.0, min(1.0, base + noise))
            chunk.distance_from_peak = dist


# ------------------------------------------------------------------ #
#  Step 3 — Moisture
# ------------------------------------------------------------------ #

def _generate_moisture(world_map: WorldMap, rng: random.Random) -> None:
    """
    Base moisture from noise. Higher elevation = slightly drier.
    """
    for wx in range(world_map.width):
        for wy in range(world_map.height):
            chunk = world_map.get(wx, wy)
            if not chunk:
                continue
            base        = rng.random()
            rain_shadow = chunk.elevation * 0.3
            chunk.moisture = max(0.0, min(1.0, base - rain_shadow))


# ------------------------------------------------------------------ #
#  Shared path utility
# ------------------------------------------------------------------ #

def _walk(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int,int]]:
    """
    Cardinal-only Bresenham walk from (x0,y0) to (x1,y1).
    Every consecutive pair is a single cardinal step — no diagonals.
    """
    path = []
    cx, cy = x0, y0
    path.append((cx, cy))
    dx = abs(x1 - cx); dy = abs(y1 - cy)
    sx = 1 if x1 > cx else -1
    sy = 1 if y1 > cy else -1
    err = dx - dy
    while (cx, cy) != (x1, y1):
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            cx  += sx
        elif e2 < dx:
            err += dx
            cy  += sy
        else:
            err -= dy
            cx  += sx
        path.append((cx, cy))
    return path


# ------------------------------------------------------------------ #
#  Step 4 — Rivers
# ------------------------------------------------------------------ #

def _generate_rivers(world_map: WorldMap, rng: random.Random) -> None:
    """
    Four primary rivers radiate from VUKH at N/E/S/W bearings (±20° jitter each).
    Two tributaries at NE/SW bearings, shorter, connecting to nearest existing river chunk.
    River chunks: is_river=True, moisture boosted to min 0.7.
    """
    cx, cy = world_map.vukh_x, world_map.vukh_y
    world_radius = min(world_map.width, world_map.height) / 2.0

    vukh_set = {(cx + dx, cy + dy) for dx in range(2) for dy in range(2)}

    def _stamp_river_connection(wx: int, wy: int, nx: int, ny: int) -> None:
        """Stamp direction from (wx,wy) toward (nx,ny) on chunk.river_connections."""
        if not world_map.in_bounds(wx, wy):
            return
        chunk = world_map.get(wx, wy)
        if not chunk:
            return
        if   nx == wx + 1: d = "E"
        elif nx == wx - 1: d = "W"
        elif ny == wy + 1: d = "S"
        elif ny == wy - 1: d = "N"
        else: return  # non-adjacent — skip
        if d not in chunk.river_connections:
            chunk.river_connections.append(d)

    def _walk_river(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int,int]]:
        """
        Walk from (x0,y0) to (x1,y1) one cardinal step at a time.
        Prefers moves that do NOT place the new chunk adjacent to an
        existing is_river chunk (other than the chunk just left or our
        own current walk path). Falls back to dirty direct move.
        """
        path     = [(x0, y0)]
        path_set = {(x0, y0)}
        cx, cy   = x0, y0
        max_len  = (abs(x1 - x0) + abs(y1 - y0)) * 2 + 4

        while (cx, cy) != (x1, y1) and len(path) < max_len:
            dx = x1 - cx
            dy = y1 - cy

            candidates: list[tuple[int,int]] = []
            if dx > 0: candidates.append((cx + 1, cy))
            if dx < 0: candidates.append((cx - 1, cy))
            if dy > 0: candidates.append((cx, cy + 1))
            if dy < 0: candidates.append((cx, cy - 1))

            def has_river_neighbour(nx: int, ny: int) -> bool:
                for ax, ay in [(nx+1,ny),(nx-1,ny),(nx,ny+1),(nx,ny-1)]:
                    if (ax, ay) == (cx, cy):
                        continue  # predecessor — ok
                    if (ax, ay) in path_set:
                        continue  # our own trail — ok
                    if not world_map.in_bounds(ax, ay):
                        continue
                    c = world_map.get(ax, ay)
                    if c and c.is_river:
                        return True
                return False

            def valid(nx: int, ny: int) -> bool:
                if not world_map.in_bounds(nx, ny):
                    return False
                c = world_map.get(nx, ny)
                if c is None:
                    return False
                if c.biome_id == "deep_mountain":
                    return False
                if getattr(c, "town_id", -1) != -1:   # avoid town chunks
                    return False
                return True

            clean = [c for c in candidates if valid(*c) and not has_river_neighbour(*c)]
            dirty = [c for c in candidates if valid(*c) and     has_river_neighbour(*c)]

            if clean:
                next_chunk = min(clean, key=lambda c: abs(c[0]-x1) + abs(c[1]-y1))
            elif dirty:
                next_chunk = min(dirty, key=lambda c: abs(c[0]-x1) + abs(c[1]-y1))
            else:
                break

            cx, cy = next_chunk
            path.append((cx, cy))
            path_set.add((cx, cy))

        return path

    def _stamp_path(sparse_path: list) -> None:
        """
        Rasterise a sparse river path to a fully adjacent chunk path
        using _walk_river (separation-aware), mark is_river on every
        chunk incrementally (so each segment's walker sees the previous
        segment), and stamp bidirectional connections.
        VUKH chunks are never marked is_river.
        """
        if len(sparse_path) < 2:
            return

        full_path: list[tuple[int,int]] = []

        for i in range(len(sparse_path) - 1):
            ax, ay = sparse_path[i]
            bx, by = sparse_path[i + 1]
            seg = _walk_river(ax, ay, bx, by)
            if full_path:
                full_path.extend(seg[1:])
            else:
                full_path.extend(seg)

            # Mark is_river immediately so the NEXT segment's walker
            # sees these chunks as river and avoids running parallel.
            for wx, wy in seg:
                if not world_map.in_bounds(wx, wy):
                    continue
                if (wx, wy) in vukh_set:
                    continue
                chunk = world_map.get(wx, wy)
                if chunk:
                    if getattr(chunk, "town_id", -1) != -1:
                        continue   # skip town chunks
                    chunk.is_river = True
                    chunk.moisture = max(0.7, chunk.moisture)

        # Stamp bidirectional connections on the complete path
        for i, (wx, wy) in enumerate(full_path):
            if not world_map.in_bounds(wx, wy):
                continue
            if (wx, wy) in vukh_set:
                continue
            curr_chunk = world_map.get(wx, wy)
            if getattr(curr_chunk, "town_id", -1) != -1:
                continue   # skip town chunks
            if i > 0:
                px, py = full_path[i - 1]
                if (px, py) not in vukh_set:
                    prev_chunk = world_map.get(px, py)
                    if getattr(prev_chunk, "town_id", -1) != -1:
                        continue   # skip if prev is also a town chunk
                    # Only stamp if the two chunks are actually adjacent
                    if abs(wx - px) + abs(wy - py) == 1:
                        _stamp_river_connection(wx, wy, px, py)
                        _stamp_river_connection(px, py, wx, wy)

    def _midpoint_waypoints(
        sx: int, sy: int, tx: int, ty: int,
        curvature: float,
        n_steps: int = 3,
    ) -> list[tuple[int, int]]:
        """
        Generate waypoints from (sx,sy) to (tx,ty) using iterative midpoint
        displacement (curvature controls max displacement as fraction of segment len).
        Returns a list of (wx,wy) world-grid points including start and end.
        """
        pts: list[tuple[float, float]] = [(float(sx), float(sy)), (float(tx), float(ty))]
        for _ in range(n_steps):
            new_pts: list[tuple[float, float]] = [pts[0]]
            for i in range(len(pts) - 1):
                ax, ay = pts[i]
                bx, by = pts[i + 1]
                mx = (ax + bx) / 2.0
                my = (ay + by) / 2.0
                seg_len = math.sqrt((bx - ax) ** 2 + (by - ay) ** 2)
                # Perpendicular direction
                pdx = -(by - ay) / max(seg_len, 0.001)
                pdy =  (bx - ax) / max(seg_len, 0.001)
                disp = rng.uniform(-curvature, curvature) * seg_len
                new_pts.append((mx + pdx * disp, my + pdy * disp))
                new_pts.append((bx, by))
            pts = new_pts
        return [(int(round(x)), int(round(y))) for x, y in pts]

    # ------------------------------------------------------------------ #
    #  Four primary rivers — N / E / S / W bearings with ±20° jitter
    # ------------------------------------------------------------------ #
    primary_bearings = [0, 90, 180, 270]   # N, E, S, W

    for base_bearing in primary_bearings:
        jitter  = rng.randint(-20, 20)
        bearing = base_bearing + jitter
        angle_rad = math.radians(bearing)

        # Start: one step outside the VUKH 2×2 block in bearing direction
        # VUKH block spans (cx, cy) to (cx+1, cy+1).
        # sin/cos give fractional offsets; we snap to cardinal and shift by 2
        # so the start is just outside the 2×2 footprint.
        raw_dx = math.sin(angle_rad)
        raw_dy = -math.cos(angle_rad)
        # Decide which face of the 2×2 we exit from
        if abs(raw_dx) >= abs(raw_dy):
            # Exiting east or west
            start_x = cx + (2 if raw_dx > 0 else -1)
            start_y = cy + round(raw_dy)
        else:
            # Exiting north or south
            start_x = cx + round(raw_dx)
            start_y = cy + (2 if raw_dy > 0 else -1)
        start_x = max(1, min(world_map.width  - 2, start_x))
        start_y = max(1, min(world_map.height - 2, start_y))

        # Target: project bearing to ~80% of world radius
        reach = world_radius * 0.80
        tx = int(cx + math.sin(angle_rad) * reach)
        ty = int(cy - math.cos(angle_rad) * reach)
        tx = max(2, min(world_map.width  - 3, tx))
        ty = max(2, min(world_map.height - 3, ty))

        waypoints = _midpoint_waypoints(start_x, start_y, tx, ty,
                                        curvature=0.40, n_steps=3)
        _stamp_path(waypoints)

    # ------------------------------------------------------------------ #
    #  Two tributaries — NE / SW bearings, 45% radius, join nearest river
    # ------------------------------------------------------------------ #
    trib_bearings = [45, 225]   # NE, SW

    for base_bearing in trib_bearings:
        jitter    = rng.randint(-15, 15)
        bearing   = base_bearing + jitter
        angle_rad = math.radians(bearing)

        raw_dx = math.sin(angle_rad)
        raw_dy = -math.cos(angle_rad)
        if abs(raw_dx) >= abs(raw_dy):
            start_x = cx + (2 if raw_dx > 0 else -1)
            start_y = cy + round(raw_dy)
        else:
            start_x = cx + round(raw_dx)
            start_y = cy + (2 if raw_dy > 0 else -1)
        start_x = max(1, min(world_map.width  - 2, start_x))
        start_y = max(1, min(world_map.height - 2, start_y))

        # Target: nearest existing river chunk in approximate bearing direction
        reach_px = math.sin(angle_rad) * world_radius * 0.45
        reach_py = -math.cos(angle_rad) * world_radius * 0.45
        probe_x  = int(cx + reach_px)
        probe_y  = int(cy + reach_py)
        probe_x  = max(2, min(world_map.width  - 3, probe_x))
        probe_y  = max(2, min(world_map.height - 3, probe_y))

        # Find the closest is_river chunk within ±40° of bearing direction
        best_tx, best_ty = probe_x, probe_y
        best_dist = float("inf")
        search_r  = int(world_radius * 0.50)
        for wx in range(max(0, probe_x - search_r), min(world_map.width,  probe_x + search_r)):
            for wy in range(max(0, probe_y - search_r), min(world_map.height, probe_y + search_r)):
                c = world_map.get(wx, wy)
                if c and c.is_river and (wx, wy) not in vukh_set:
                    d = (wx - probe_x) ** 2 + (wy - probe_y) ** 2
                    if d < best_dist:
                        best_dist = d
                        best_tx, best_ty = wx, wy

        waypoints = _midpoint_waypoints(start_x, start_y, best_tx, best_ty,
                                        curvature=0.35, n_steps=2)
        _stamp_path(waypoints)

    # Boost moisture for river-adjacent chunks
    for wx in range(world_map.width):
        for wy in range(world_map.height):
            chunk = world_map.get(wx, wy)
            if chunk and chunk.is_river:
                for adx in [-1, 0, 1]:
                    for ady in [-1, 0, 1]:
                        adj = world_map.get(wx + adx, wy + ady)
                        if adj and not adj.is_river:
                            adj.moisture = min(1.0, adj.moisture + 0.2)

    # Also stamp river EdgeConnectors for local generation
    _stamp_river_connectors(world_map, rng)


def _stamp_river_connectors(world_map: WorldMap, rng: random.Random) -> None:
    """
    For each river chunk, stamp EdgeConnectors on boundaries shared
    with other river chunks so the local generator can carve water.
    """
    EDGE_OFFSETS = {
        "north": (0, -1), "south": (0, 1),
        "east":  (1,  0), "west": (-1,  0),
    }
    OPPOSITE = {"north": "south", "south": "north",
                "east":  "west",  "west":  "east"}

    for wx in range(world_map.width):
        for wy in range(world_map.height):
            chunk = world_map.get(wx, wy)
            if not chunk or not chunk.is_river:
                continue
            river_id = f"river_{wx}_{wy}"
            position = round(rng.uniform(0.3, 0.7), 2)
            for edge, (odx, ody) in EDGE_OFFSETS.items():
                nb = world_map.get(wx + odx, wy + ody)
                if nb and nb.is_river:
                    chunk.add_connector(edge, ConnectorType.RIVER,
                                        position, river_id)


def _stamp_road_connectors(world_map: WorldMap) -> None:
    """
    For each road tile, stamp EdgeConnectors on boundaries shared with adjacent
    road tiles so the local generator can carve cobblestone road terrain.
    Uses the 'connections' field already written by _build_road.
    """
    EDGE_DIR = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
    DIR_EDGE = {"N": "north", "S": "south", "E": "east", "W": "west"}

    for (wx, wy), road_info in world_map.road_tiles.items():
        chunk = world_map.get(wx, wy)
        if not chunk:
            continue
        road_id = f"road_{wx}_{wy}"
        for direction in road_info.get("connections", []):
            edge = DIR_EDGE.get(direction)
            if not edge:
                continue
            odx, ody = EDGE_DIR[direction]
            nb = world_map.get(wx + odx, wy + ody)
            if nb and (wx + odx, wy + ody) in world_map.road_tiles:
                chunk.add_connector(edge, ConnectorType.ROAD, 0.5, road_id)


# ------------------------------------------------------------------ #
#  Step 5 — Biome assignment
# ------------------------------------------------------------------ #

def _assign_biomes(world_map: WorldMap, data) -> None:
    """
    Match each chunk to a biome based on elevation + moisture.
    Chunks already tagged (VUKH peak/ring) are skipped.
    """
    biomes     = list(data.biomes.values())
    auto_biomes = [b for b in biomes
                   if b["id"] not in ("deep_mountain", "capital", "town")]

    for wx in range(world_map.width):
        for wy in range(world_map.height):
            chunk = world_map.get(wx, wy)
            if not chunk:
                continue
            if chunk.biome_id == "deep_mountain":
                continue  # VUKH peak — already assigned
            if chunk.biome_id == "mountain" and chunk.elevation >= 0.85:
                continue  # VUKH ring — keep as mountain

            elev = chunk.elevation
            mois = chunk.moisture

            best_biome = None
            best_score = -1.0

            for biome in auto_biomes:
                e_min, e_max = biome["elevation_range"]
                m_min, m_max = biome["moisture_range"]

                if not (e_min <= elev <= e_max):
                    continue
                if not (m_min <= mois <= m_max):
                    continue

                e_center = (e_min + e_max) / 2.0
                m_center = (m_min + m_max) / 2.0
                e_half   = max(0.001, (e_max - e_min) / 2.0)
                m_half   = max(0.001, (m_max - m_min) / 2.0)
                e_score  = 1.0 - abs((elev - e_center) / e_half)
                m_score  = 1.0 - abs((mois - m_center) / m_half)
                score    = (e_score + m_score) / 2.0

                if chunk.is_river and biome.get("river_adjacent", False):
                    score += 0.3

                if score > best_score:
                    best_score = score
                    best_biome = biome

            if best_biome:
                chunk.biome_id    = best_biome["id"]
                chunk.region_type = RegionType.from_biome_id(best_biome["id"])
                chunk.resonance   = best_biome["base_resonance"]
                chunk.difficulty  = best_biome["difficulty_base"]
            else:
                chunk.biome_id    = "plains"
                chunk.region_type = RegionType.PLAINS
                chunk.resonance   = 0.20
                chunk.difficulty  = 0.15


# ------------------------------------------------------------------ #
#  Step 6 — Resonance calculation
# ------------------------------------------------------------------ #

def _calculate_resonance(world_map: WorldMap) -> None:
    """
    Final resonance = biome base × distance modifier × river modifier.
    Closer to VUKH = higher resonance regardless of biome.
    """
    cx, cy   = world_map.vukh_x, world_map.vukh_y
    max_dist = ((world_map.width // 2) ** 2 +
                (world_map.height // 2) ** 2) ** 0.5

    for wx in range(world_map.width):
        for wy in range(world_map.height):
            chunk = world_map.get(wx, wy)
            if not chunk:
                continue
            dist      = chunk.distance_from_peak
            dist_mod  = max(0.3, 1.0 - (dist / max_dist) * 0.7)
            river_mod = 1.2 if chunk.is_river else 1.0
            chunk.resonance  = min(1.0, chunk.resonance * dist_mod * river_mod)
            chunk.difficulty = min(1.0, chunk.difficulty * dist_mod)


# ------------------------------------------------------------------ #
#  Step 7 — Capital placement
# ------------------------------------------------------------------ #

def _place_capital(world_map: WorldMap, rng: random.Random) -> None:
    """
    Capital (Valdremor) surrounds VUKH in an uneven ring.
    3-5 chunk radius, avoiding deep_mountain tiles.
    """
    cx, cy = world_map.vukh_x, world_map.vukh_y
    radius = rng.randint(4, 6)

    candidates = []
    for wx in range(world_map.width):
        for wy in range(world_map.height):
            dist = ((wx - cx) ** 2 + (wy - cy) ** 2) ** 0.5
            if dist <= radius:
                chunk = world_map.get(wx, wy)
                if chunk and chunk.biome_id != "deep_mountain":
                    candidates.append((wx, wy))

    keep = rng.randint(
        int(len(candidates) * 0.7),
        max(int(len(candidates) * 0.7), int(len(candidates) * 0.9)),
    )
    capital_chunks = rng.sample(candidates, min(keep, len(candidates)))

    for wx, wy in capital_chunks:
        chunk = world_map.get(wx, wy)
        if chunk:
            chunk.biome_id    = "capital"
            chunk.region_type = RegionType.CAPITAL
            chunk.is_capital  = True
            chunk.resonance   = 0.70
            chunk.difficulty  = 0.85

    world_map.capital_chunks = set(capital_chunks)


# ------------------------------------------------------------------ #
#  Step 8 — Starting location
# ------------------------------------------------------------------ #

def _place_starting_location(world_map: WorldMap, rng: random.Random) -> None:
    """
    Player starts in a forest chunk far from VUKH (≥60% max distance).
    Must not be river, capital, or deep_mountain.
    The lab SubMap is attached here.
    """
    cx, cy      = world_map.vukh_x, world_map.vukh_y
    world_radius = min(world_map.width, world_map.height) // 2
    min_dist     = world_radius * 0.55

    candidates = []
    for wx in range(world_map.width):
        for wy in range(world_map.height):
            chunk = world_map.get(wx, wy)
            if not chunk:
                continue
            if chunk.biome_id != "forest":
                continue
            if chunk.is_river or chunk.is_capital:
                continue
            dist = ((wx - cx) ** 2 + (wy - cy) ** 2) ** 0.5
            if dist < min_dist:
                continue
            candidates.append((wx, wy))

    if not candidates:
        # Fallback — furthest plains/forest chunk at half min_dist
        for wx in range(world_map.width):
            for wy in range(world_map.height):
                chunk = world_map.get(wx, wy)
                if chunk and chunk.biome_id in ("forest", "plains"):
                    dist = ((wx - cx) ** 2 + (wy - cy) ** 2) ** 0.5
                    if dist >= min_dist * 0.5:
                        candidates.append((wx, wy))

    if not candidates:
        # Last resort — any non-vukh chunk
        candidates = [
            (wx, wy)
            for (wx, wy), chunk in world_map.chunks.items()
            if chunk.biome_id != "deep_mountain"
        ]

    start_wx, start_wy = rng.choice(candidates)
    world_map.start_wx = start_wx
    world_map.start_wy = start_wy

    chunk = world_map.get(start_wx, start_wy)
    if chunk:
        # Clear any auto-generated submaps and place the lab
        chunk.submaps    = []
        chunk.biome_id   = "forest"
        chunk.region_type = RegionType.FOREST
        chunk.zones      = list(BIOME_ZONES.get("forest", []))
        chunk.name       = "the waking forest"
        chunk.name_register = "common"

        lab_sub = SubMap(
            submap_id   = f"sub_{start_wx}_{start_wy}_0",
            submap_type = "laboratory",
            name        = "Vrath Sketh",
            seed        = world_map.seed ^ 0x0AB1,
            layout_id   = "starting_lab",
        )
        chunk.submaps = [lab_sub]


# ------------------------------------------------------------------ #
#  Step 9 — Town placement
# ------------------------------------------------------------------ #

def _place_towns(world_map: WorldMap, rng: random.Random) -> None:
    """
    Place 2-4 towns as 3×3 chunk footprints scattered across the world.
    Quadrant-balanced: at most one town per NW/NE/SW/SE quadrant; allows
    empty quadrants when town count is fewer than 4.
    Centre chunk of each 3×3 is the town anchor.
    """
    from world.name_gen import assign_chunk_name

    cx, cy = world_map.vukh_x, world_map.vukh_y
    sx, sy = world_map.start_wx, world_map.start_wy

    vukh_set = {(cx + dx, cy + dy) for dx in range(2) for dy in range(2)}

    STRICT_EXCLUDE   = {"deep_mountain", "capital", "ash_wastes", "swamp"}
    RELAXED_EXCLUDE  = {"deep_mountain", "capital"}
    MIN_DIST_VUKH    = 6
    N_TOWNS          = rng.randint(2, 4)
    PREFERRED_BIOMES = {"forest", "heath", "plains"}
    world_radius     = min(world_map.width, world_map.height) // 2
    MAX_DIST_STRICT  = world_radius * 0.72
    MAX_DIST_RELAXED = world_radius * 0.85
    MIN_DIST_TOWNS   = 12  # minimum distance between town centres (wx+1,wy+1)

    def footprint_clear(wx: int, wy: int, exclude: set, max_dist: float) -> bool:
        """Check 3×3 footprint — biome/distance/overlap validity."""
        for dx in range(3):
            for dy in range(3):
                p = (wx + dx, wy + dy)
                if not world_map.in_bounds(wx + dx, wy + dy):
                    return False
                chunk = world_map.get(wx + dx, wy + dy)
                if not chunk:
                    return False
                if p in vukh_set:
                    return False
                if p in world_map.capital_chunks:
                    return False
                if chunk.is_river:
                    return False
                if chunk.biome_id in exclude:
                    return False
        # Distance check uses the NW corner as reference
        dist_vukh = math.sqrt((wx - cx) ** 2 + (wy - cy) ** 2)
        return MIN_DIST_VUKH <= dist_vukh <= max_dist

    def score_entry(wx: int, wy: int) -> float:
        centre_chunk = world_map.get(wx + 1, wy + 1)
        return 2.0 if (centre_chunk and centre_chunk.biome_id in PREFERRED_BIOMES) else 1.0

    def build_quad_cands(quad_chunks: list[tuple[int,int]]) -> list[tuple[int,int,float]]:
        """Build candidate list for one quadrant with strict→relaxed→expanded fallback."""
        strict = [
            (wx, wy, score_entry(wx, wy))
            for wx, wy in quad_chunks
            if footprint_clear(wx, wy, STRICT_EXCLUDE, MAX_DIST_STRICT)
        ]
        if len(strict) >= 3:
            return strict
        relaxed = [
            (wx, wy, score_entry(wx, wy))
            for wx, wy in quad_chunks
            if footprint_clear(wx, wy, RELAXED_EXCLUDE, MAX_DIST_STRICT)
        ]
        if relaxed:
            return relaxed
        # Expand radius for sparse quadrants
        return [
            (wx, wy, score_entry(wx, wy))
            for wx, wy in quad_chunks
            if footprint_clear(wx, wy, RELAXED_EXCLUDE, MAX_DIST_RELAXED)
        ]

    # NW-corner anchor positions for 3×3 footprints (need 2 tiles of margin on each side)
    raw_nw, raw_ne, raw_sw, raw_se = [], [], [], []
    for wx in range(world_map.width - 2):
        for wy in range(world_map.height - 2):
            # Quadrant is determined by the centre chunk (wx+1, wy+1)
            if wx + 1 < cx:
                (raw_nw if wy + 1 < cy else raw_sw).append((wx, wy))
            else:
                (raw_ne if wy + 1 < cy else raw_se).append((wx, wy))

    q_nw = sorted(build_quad_cands(raw_nw), key=lambda c: -c[2])
    q_ne = sorted(build_quad_cands(raw_ne), key=lambda c: -c[2])
    q_sw = sorted(build_quad_cands(raw_sw), key=lambda c: -c[2])
    q_se = sorted(build_quad_cands(raw_se), key=lambda c: -c[2])

    placed_towns: list[tuple[int, int]] = []  # NW corner of each 3×3

    def too_close(wx: int, wy: int) -> bool:
        """Centre-to-centre distance must be >= MIN_DIST_TOWNS."""
        ncx, ncy = wx + 1, wy + 1
        for tx, ty in placed_towns:
            tcx, tcy = tx + 1, ty + 1
            d = math.sqrt((ncx - tcx) ** 2 + (ncy - tcy) ** 2)
            if d < MIN_DIST_TOWNS:
                return True
        return False

    # Place at most one town per quadrant; stop when N_TOWNS reached.
    # Shuffle quadrant order so no quadrant is always tried first.
    quads = [q_nw, q_ne, q_sw, q_se]
    rng.shuffle(quads)
    for quad in quads:
        if len(placed_towns) >= N_TOWNS:
            break
        for wx, wy, _ in quad:
            if not too_close(wx, wy):
                placed_towns.append((wx, wy))
                break

    # Guarantee one town within 14 chunks of player start
    near_start = any(
        math.sqrt((wx + 1 - sx) ** 2 + (wy + 1 - sy) ** 2) <= 14
        for wx, wy in placed_towns
    )
    if not near_start:
        all_cands = sorted(
            [
                (wx, wy, score_entry(wx, wy))
                for wx in range(world_map.width - 2)
                for wy in range(world_map.height - 2)
                if footprint_clear(wx, wy, STRICT_EXCLUDE, MAX_DIST_STRICT)
            ],
            key=lambda c: -c[2],
        )
        for wx, wy, _ in all_cands:
            dist_start = math.sqrt((wx + 1 - sx) ** 2 + (wy + 1 - sy) ** 2)
            if 6 <= dist_start <= 14 and not too_close(wx, wy):
                placed_towns.append((wx, wy))
                break

    world_map.town_groups    = {}
    world_map.town_chunk_ids = {}

    # 3×3 roles: (name, dx, dy) — centre is "C" at (1,1)
    ROLES = [
        ("NW", 0, 0), ("N",  1, 0), ("NE", 2, 0),
        ("W",  0, 1), ("C",  1, 1), ("E",  2, 1),
        ("SW", 0, 2), ("S",  1, 2), ("SE", 2, 2),
    ]

    for town_id, (nw_wx, nw_wy) in enumerate(placed_towns):
        # Derive town name from centre chunk seed
        centre_chunk = world_map.get(nw_wx + 1, nw_wy + 1)
        seed = centre_chunk.seed if centre_chunk else (nw_wx * 31 + nw_wy * 37)
        town_name, _ = assign_chunk_name("town", seed)

        group: list[tuple[int, int]] = []
        for role, dx, dy in ROLES:
            wx, wy  = nw_wx + dx, nw_wy + dy
            chunk   = world_map.get(wx, wy)
            if not chunk:
                continue
            chunk.biome_id    = "town"
            chunk.region_type = RegionType.TOWN
            chunk.resonance   = 0.50
            chunk.difficulty  = 0.45
            chunk.town_id     = town_id
            chunk.town_role   = role
            chunk.name        = town_name
            world_map.chunk_names[(wx, wy)] = town_name
            group.append((wx, wy))
            world_map.town_chunk_ids[(wx, wy)] = town_id

        world_map.town_groups[town_id] = group

    world_map.town_chunks = {
        coord
        for group in world_map.town_groups.values()
        for coord in group
    }

    # Rivers run before towns — clear any river marks that landed on town chunks.
    # Also strip RIVER EdgeConnectors so the local generator doesn't carve water
    # through town ground.
    for wx, wy in world_map.town_chunks:
        chunk = world_map.get(wx, wy)
        if not chunk:
            continue
        chunk.is_river = False
        for edge in list(chunk.edges.keys()):
            chunk.edges[edge] = [
                c for c in chunk.edges[edge]
                if c.connector_type != ConnectorType.RIVER
            ]


# ------------------------------------------------------------------ #
#  Step 10 — Road generation
# ------------------------------------------------------------------ #

def _generate_roads(world_map: WorldMap, rng: random.Random) -> None:
    """
    Primary roads: each town NW anchor → nearest capital chunk.
    Secondary roads: up to 4 nearest town pairs within 16 chunks.
    Also a secondary road from player start → nearest town NW anchor.
    """
    capital_chunks = getattr(world_map, "capital_chunks", set())
    town_groups    = getattr(world_map, "town_groups",    {})
    if not capital_chunks and not town_groups:
        return

    # Centre chunk per town group (role "C" is at dx=1,dy=1 offset in 3×3 footprint)
    town_anchors: list[tuple[int,int]] = []
    for group in town_groups.values():
        for wx, wy in group:
            chunk = world_map.get(wx, wy)
            if chunk and getattr(chunk, "town_role", None) == "C":
                town_anchors.append((wx, wy))
                break

    def _stamp_road_connection(wx: int, wy: int, nx: int, ny: int) -> None:
        """Stamp the direction from (wx,wy) toward (nx,ny) on road tile."""
        if (wx, wy) not in world_map.road_tiles:
            return
        if   nx == wx + 1: d = "E"
        elif nx == wx - 1: d = "W"
        elif ny == wy + 1: d = "S"
        elif ny == wy - 1: d = "N"
        else: return
        conns = world_map.road_tiles[(wx, wy)]["connections"]
        if d not in conns:
            conns.append(d)

    def _build_road(x0: int, y0: int, x1: int, y1: int, road_type: str) -> None:
        """
        Build a road from (x0,y0) to (x1,y1) with a single midpoint bend.
        All consecutive chunks are guaranteed adjacent (cardinal steps only).
        """
        mx = (x0 + x1) // 2
        my = (y0 + y1) // 2
        dx = x1 - x0
        dy = y1 - y0
        length = math.sqrt(dx * dx + dy * dy)

        if length > 4:
            perp_x = -dy / length
            perp_y =  dx / length
            offset = rng.uniform(0.15, 0.30) * length
            if rng.random() < 0.5:
                offset = -offset
            mx = int(mx + perp_x * offset)
            my = int(my + perp_y * offset)
            mx = max(2, min(world_map.width  - 3, mx))
            my = max(2, min(world_map.height - 3, my))

        path: list[tuple[int,int]] = []
        path.extend(_walk(x0, y0, mx, my))
        path.extend(_walk(mx, my, x1, y1)[1:])

        # Skip if more than 20% of path crosses deep_mountain
        deep_count = sum(
            1 for wx, wy in path
            if world_map.in_bounds(wx, wy) and
               (c := world_map.get(wx, wy)) and c.biome_id == "deep_mountain"
        )
        if deep_count > len(path) * 0.2:
            return

        # Write road tiles
        for wx, wy in path:
            if not world_map.in_bounds(wx, wy):
                continue
            if (wx, wy) not in world_map.road_tiles:
                world_map.road_tiles[(wx, wy)] = {"type": road_type, "connections": []}
            elif road_type == "primary":
                world_map.road_tiles[(wx, wy)]["type"] = "primary"

        # Stamp bidirectional connections on all consecutive pairs
        for i in range(1, len(path)):
            wx, wy = path[i]
            px, py = path[i - 1]
            _stamp_road_connection(wx, wy, px, py)
            _stamp_road_connection(px, py, wx, wy)

    # Track road connections per town centre — max 2 per town total.
    town_road_count: dict[tuple[int,int], int] = {t: 0 for t in town_anchors}

    def _town_can_connect(anchor: tuple[int,int]) -> bool:
        return town_road_count.get(anchor, 0) < 2

    def _record_town_road(anchor: tuple[int,int]) -> None:
        town_road_count[anchor] = town_road_count.get(anchor, 0) + 1

    # Primary roads: each town centre → nearest capital chunk (1 connection)
    if capital_chunks:
        for tx, ty in town_anchors:
            nearest = min(
                capital_chunks,
                key=lambda c: (c[0] - tx) ** 2 + (c[1] - ty) ** 2,
            )
            _build_road(tx, ty, nearest[0], nearest[1], "primary")
            _record_town_road((tx, ty))

    # Secondary road: player start → nearest town that still has capacity
    sx, sy = world_map.start_wx, world_map.start_wy
    if town_anchors:
        eligible = [t for t in town_anchors if _town_can_connect(t)]
        if eligible:
            nearest_town = min(
                eligible,
                key=lambda t: (t[0] - sx) ** 2 + (t[1] - sy) ** 2,
            )
            _build_road(sx, sy, nearest_town[0], nearest_town[1], "secondary")
            _record_town_road(nearest_town)

    # Secondary roads: closest town-anchor pairs within 16 chunks, max 1 connection each
    pairs = sorted(
        (math.sqrt((ax - bx) ** 2 + (ay - by) ** 2), ax, ay, bx, by)
        for i, (ax, ay) in enumerate(town_anchors)
        for bx, by in town_anchors[i + 1:]
        if math.sqrt((ax - bx) ** 2 + (ay - by) ** 2) <= 16
    )
    for _, ax, ay, bx, by in pairs:
        if not _town_can_connect((ax, ay)) or not _town_can_connect((bx, by)):
            continue
        _build_road(ax, ay, bx, by, "secondary")
        _record_town_road((ax, ay))
        _record_town_road((bx, by))

    # Stamp road EdgeConnectors so local map generator carves cobblestone roads
    _stamp_road_connectors(world_map)


# ------------------------------------------------------------------ #
#  Step 11 — Difficulty bands
# ------------------------------------------------------------------ #

def _calculate_difficulty_bands(world_map: WorldMap) -> None:
    """
    Final difficulty pass combining biome base, distance from VUKH,
    town/capital proximity, and river modifier.
    """
    max_dist = ((world_map.width  // 2) ** 2 +
                (world_map.height // 2) ** 2) ** 0.5

    for wx in range(world_map.width):
        for wy in range(world_map.height):
            chunk = world_map.get(wx, wy)
            if not chunk:
                continue

            dist_mod    = max(0.2, 1.0 - (chunk.distance_from_peak / max_dist) * 0.8)
            town_mod    = 1.3 if chunk.biome_id == "town"    else 1.0
            capital_mod = 1.5 if chunk.biome_id == "capital" else 1.0
            river_mod   = 1.1 if chunk.is_river               else 1.0

            chunk.difficulty = min(1.0,
                chunk.difficulty * dist_mod * town_mod * capital_mod * river_mod
            )


# ------------------------------------------------------------------ #
#  Post-processing — zones, submaps, names, myth
# ------------------------------------------------------------------ #

def _assign_zones(world_map: WorldMap) -> None:
    """Assign zone compositions from biome_id for all chunks without zones."""
    for (wx, wy), chunk in world_map.chunks.items():
        if not chunk.zones:
            chunk.zones = list(BIOME_ZONES.get(chunk.biome_id,
                                               [("heath", 1.0)]))


def _assign_submaps(world_map: WorldMap, rng: random.Random) -> None:
    """Assign random dungeon submaps to eligible chunks."""
    for (wx, wy), chunk in world_map.chunks.items():
        if chunk.submaps:
            continue  # already has lab or was manually set
        biome  = chunk.biome_id
        chance = SUBMAP_WEIGHTS.get(biome, 0.0)
        if chance <= 0.0:
            continue
        sub_rng = random.Random(chunk.seed ^ 0xABCD1234)
        if sub_rng.random() >= chance:
            continue
        types_map = SUBMAP_TYPES.get(biome, {"barrow": 1})
        stype     = sub_rng.choices(list(types_map.keys()),
                                    weights=list(types_map.values()), k=1)[0]
        sseed     = sub_rng.randint(0, 999999)
        sname, _  = assign_chunk_name("dungeon", sseed)
        chunk.add_submap(stype, sname, sseed)


def _assign_names(world_map: WorldMap) -> None:
    """Name every unnamed chunk."""
    for chunk in world_map.chunks.values():
        if not chunk.name:
            chunk.name, chunk.name_register = assign_chunk_name(
                chunk.region_type.value, chunk.seed
            )


def _generate_world_myth(world_map: WorldMap, rng: random.Random) -> None:
    """
    Generate WorldMyth. Locus is fixed at VUKH — not random.
    """
    from world.world_myth import generate_world_myth
    from world import name_gen

    # WorldMyth uses a distinct RNG derived from the world seed
    submap_chunks = [
        (wx, wy) for (wx, wy), chunk in world_map.chunks.items()
        if chunk.submaps
    ]
    cx, cy = world_map.vukh_x, world_map.vukh_y
    submap_chunks.sort(key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))

    myth = generate_world_myth(world_map.seed, submap_chunks, name_gen)

    # Override locus to VUKH
    myth.locus_wx   = world_map.vukh_x
    myth.locus_wy   = world_map.vukh_y
    myth.locus_name = "VUKH"

    vukh_chunk = world_map.get(world_map.vukh_x, world_map.vukh_y)
    if vukh_chunk:
        vukh_chunk.is_locus = True

    world_map.myth = myth
