# generation/region_gen.py
from __future__ import annotations
import random
from world.local_map import LocalMap
from world.world_map import Chunk, RegionType, ConnectorType
from generation.local_gen import (
    punch_edge_transitions,
    carve_connectors,
)

# Maps submap_type → entrance structure type for visual marker on surface map
SUBMAP_ENTRANCE: dict[str, str] = {
    "barrow":      "barrow_mound",
    "cave":        "rock_face_cut",
    "vault":       "sunken_ruin",
    "sunken_ruin": "sunken_ruin",
    "flooded_ruin":"drowned_threshold",
    "deep_vault":  "barrow_mound",
    "cellar":      "sunken_ruin",
    "crypt":       "sunken_ruin",
    "laboratory":  "sunken_ruin",
}


def generate_region(
    chunk: Chunk,
    map_width: int,
    map_height: int,
    terrain_data: dict,
    data=None,              # DataLoader — required for full town generation
) -> tuple[LocalMap, tuple[int, int]]:
    """
    Dispatch to the correct generator based on chunk region type.
    After generation, carve edge connectors (rivers, roads, paths).
    Returns (LocalMap, player_spawn_xy).
    """
    rng = random.Random(chunk.seed)

    if chunk.region_type == RegionType.FOREST:
        local_map, spawn = _generate_forest(
            map_width, map_height, terrain_data, rng
        )

    elif chunk.region_type == RegionType.TOWN:
        if data is not None:
            from generation.town_gen import generate_town
            local_map = _generate_town_base(map_width, map_height, terrain_data)
            local_map, spawn = generate_town(
                chunk         = chunk,
                local_map     = local_map,
                map_w         = map_width,
                map_h         = map_height,
                terrain_data  = terrain_data,
                building_data = data.buildings,
                name_gen      = None,
                rng           = rng,
            )
        else:
            local_map, spawn = _generate_town(
                map_width, map_height, terrain_data, rng
            )

    elif chunk.region_type == RegionType.SWAMP:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng,
            floor_terrain="mud", tree_chance=0.12,
        )

    elif chunk.region_type == RegionType.HEATH:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng,
            floor_terrain="varied_grass", tree_chance=0.03,
        )

    elif chunk.region_type == RegionType.MOUNTAIN:
        local_map, spawn = _generate_mountain(
            map_width, map_height, terrain_data, rng
        )

    elif chunk.region_type == RegionType.DEEP_MOUNTAIN:
        local_map, spawn = _generate_mountain(
            map_width, map_height, terrain_data, rng
        )

    elif chunk.region_type == RegionType.CAPITAL:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng,
            floor_terrain="cobblestone", tree_chance=0.0,
        )

    elif chunk.region_type == RegionType.DROWNED_WOOD:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng,
            floor_terrain="mud", tree_chance=0.20,
        )

    elif chunk.region_type == RegionType.ASH_WASTES:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng,
            floor_terrain="varied_grass", tree_chance=0.01,
        )

    else:  # PLAINS / UNKNOWN default
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng,
            floor_terrain="varied_grass", tree_chance=0.06,
        )

    # B1: Tall grass scatter — before connectors so roads don't get covered
    _GRASS = {"varied_grass", "grass"}
    _MUD   = {"mud"}
    if chunk.region_type == RegionType.FOREST:
        _scatter_terrain(local_map, terrain_data, rng, _GRASS, "tall_grass",
                         n_clusters=8,  cluster_r=4)
        _scatter_terrain(local_map, terrain_data, rng, _GRASS, "shallow_water",
                         n_clusters=3,  cluster_r=3)
    elif chunk.region_type == RegionType.SWAMP:
        _scatter_terrain(local_map, terrain_data, rng, _MUD,   "tall_grass",
                         n_clusters=5,  cluster_r=3)
        _scatter_terrain(local_map, terrain_data, rng, _MUD,   "shallow_water",
                         n_clusters=12, cluster_r=5)
    elif chunk.region_type == RegionType.DROWNED_WOOD:
        _scatter_terrain(local_map, terrain_data, rng, _MUD,   "shallow_water",
                         n_clusters=10, cluster_r=5)
    elif chunk.region_type == RegionType.HEATH:
        _scatter_terrain(local_map, terrain_data, rng, _GRASS, "tall_grass",
                         n_clusters=6,  cluster_r=3)
    elif chunk.region_type not in (RegionType.TOWN, RegionType.CAPITAL,
                                   RegionType.MOUNTAIN, RegionType.DEEP_MOUNTAIN):
        # PLAINS / ASH_WASTES / default open
        _scatter_terrain(local_map, terrain_data, rng, _GRASS, "tall_grass",
                         n_clusters=14, cluster_r=4)

    # Carve rivers, roads, paths from edge connectors
    carve_connectors(
        local_map, terrain_data,
        chunk.edges, map_width, map_height, rng,
        town_id=getattr(chunk, "town_id", -1),
    )

    # B2: Dead wood scatter near trees (surface wilderness only)
    if (chunk.region_type not in (RegionType.TOWN, RegionType.CAPITAL)
            and "dead_wood" in terrain_data):
        _scatter_dead_wood(local_map, terrain_data, rng)

    # B3: Flint outcrops — biome-driven rate (surface wilderness only)
    if (chunk.region_type not in (RegionType.TOWN, RegionType.CAPITAL)
            and "flint_rock" in terrain_data and data is not None):
        biome_def = data.biomes.get(chunk.biome_id, {})
        flint_rate = biome_def.get("flint_scatter_rate", 0.0)
        if flint_rate > 0.0:
            _scatter_flint(local_map, terrain_data, rng, flint_rate)

    # B4: Waystones — after connectors so road terrain is present
    if chunk.region_type not in (RegionType.TOWN, RegionType.CAPITAL):
        _place_waystones(local_map, terrain_data, chunk, rng)

    # B5: Clay deposits — scatter near river tiles (wilderness only)
    if (chunk.region_type not in (RegionType.TOWN, RegionType.CAPITAL)
            and "clay_deposit" in terrain_data):
        _scatter_clay(local_map, terrain_data, rng)

    # Place submap entrances AFTER connectors so roads can't overwrite stairs
    for submap in chunk.submaps:
        _place_submap_entrance(local_map, submap, terrain_data)

    return local_map, spawn


# ------------------------------------------------------------------ #
#  Generators
# ------------------------------------------------------------------ #

def _generate_open(
    map_width: int,
    map_height: int,
    terrain_data: dict,
    rng: random.Random,
    floor_terrain: str = "varied_grass",
    tree_chance: float = 0.06,
) -> tuple[LocalMap, tuple[int, int]]:
    local_map = LocalMap(map_width, map_height)
    floor = terrain_data[floor_terrain]
    tree  = terrain_data["tree"]

    for x in range(map_width):
        for y in range(map_height):
            if rng.random() < tree_chance:
                local_map.set_tile(x, y, "tree",
                                   tree["walkable"], tree["transparent"])
            else:
                local_map.set_tile(x, y, floor_terrain,
                                   floor["walkable"], floor["transparent"])

    cx, cy = map_width // 2, map_height // 2
    local_map.set_tile(cx, cy, floor_terrain,
                       floor["walkable"], floor["transparent"])

    punch_edge_transitions(local_map, terrain_data, rng, edge_terrain=floor_terrain)
    return local_map, (cx, cy)


def _ensure_forest_connectivity(local_map: LocalMap, map_w: int, map_h: int) -> None:
    """
    BFS flood-fill from centre.  Any non-walkable tile that has 3+ walkable
    visited neighbours is cleared to grass — opens up isolated pockets.
    """
    from collections import deque

    start = (map_w // 2, map_h // 2)
    # If centre is not walkable, spiral out to find nearest walkable tile
    if not local_map.walkable[start]:
        found = False
        for r in range(1, 20):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    nx, ny = start[0] + dx, start[1] + dy
                    if local_map.in_bounds(nx, ny) and local_map.walkable[nx, ny]:
                        start = (nx, ny)
                        found = True
                        break
                if found:
                    break
            if found:
                break

    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque([start])
    visited.add(start)
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (local_map.in_bounds(nx, ny)
                    and local_map.walkable[nx, ny]
                    and (nx, ny) not in visited):
                visited.add((nx, ny))
                queue.append((nx, ny))

    # Clear blocked tiles surrounded by ≥3 reachable walkable neighbours
    for x in range(map_w):
        for y in range(map_h):
            if not local_map.walkable[x, y]:
                neighbours = sum(
                    1 for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
                    if (x + dx, y + dy) in visited
                )
                if neighbours >= 3:
                    local_map.set_tile(x, y, "varied_grass", True, True)


def _generate_forest(
    map_width: int,
    map_height: int,
    terrain_data: dict,
    rng: random.Random,
) -> tuple[LocalMap, tuple[int, int]]:
    local_map = LocalMap(map_width, map_height)
    grass = terrain_data["varied_grass"]
    tree  = terrain_data["tree"]

    for x in range(map_width):
        for y in range(map_height):
            if rng.random() < 0.35:
                local_map.set_tile(x, y, "tree",
                                   tree["walkable"], tree["transparent"])
            else:
                local_map.set_tile(x, y, "varied_grass",
                                   grass["walkable"], grass["transparent"])

    cx, cy = map_width // 2, map_height // 2
    for x in range(cx - 2, cx + 3):
        for y in range(cy - 2, cy + 3):
            if local_map.in_bounds(x, y):
                local_map.set_tile(x, y, "varied_grass",
                                   grass["walkable"], grass["transparent"])

    _ensure_forest_connectivity(local_map, map_width, map_height)
    punch_edge_transitions(local_map, terrain_data, rng, edge_terrain="varied_grass")
    return local_map, (cx, cy)


def _generate_mountain(
    map_width: int,
    map_height: int,
    terrain_data: dict,
    rng: random.Random,
) -> tuple[LocalMap, tuple[int, int]]:
    local_map = LocalMap(map_width, map_height)
    rock   = terrain_data["rock"]
    gravel = terrain_data["gravel"]

    for x in range(map_width):
        for y in range(map_height):
            if rng.random() < 0.45:
                local_map.set_tile(x, y, "rock",
                                   rock["walkable"], rock["transparent"])
            else:
                local_map.set_tile(x, y, "gravel",
                                   gravel["walkable"], gravel["transparent"])

    # Carve a winding pass through the centre
    cx, cy = map_width // 2, 0
    while cy < map_height:
        for ox in range(-1, 2):
            nx = cx + ox
            if local_map.in_bounds(nx, cy):
                local_map.set_tile(nx, cy, "gravel",
                                   gravel["walkable"], gravel["transparent"])
        cy += 1
        if rng.random() < 0.3:
            cx = max(2, min(map_width - 3, cx + rng.randint(-1, 1)))

    spawn_x = map_width  // 2
    spawn_y = map_height // 2
    local_map.set_tile(spawn_x, spawn_y, "gravel",
                       gravel["walkable"], gravel["transparent"])

    punch_edge_transitions(local_map, terrain_data, rng, edge_terrain="gravel")
    return local_map, (spawn_x, spawn_y)


def _generate_town_base(
    map_width: int,
    map_height: int,
    terrain_data: dict,
) -> LocalMap:
    """Grass-filled base map for the full town generator to stamp over."""
    local_map = LocalMap(map_width, map_height)
    grass = terrain_data["grass"]
    for x in range(map_width):
        for y in range(map_height):
            local_map.set_tile(x, y, "varied_grass",
                               grass["walkable"], grass["transparent"])
    return local_map


def _generate_town(
    map_width: int,
    map_height: int,
    terrain_data: dict,
    rng: random.Random,
) -> tuple[LocalMap, tuple[int, int]]:
    """
    Basic town generator — cobblestone base with scattered
    building footprints. Will be replaced by the full zone-based
    town generator once the structure placer is integrated.
    """
    local_map = LocalMap(map_width, map_height)
    cobble = terrain_data.get("cobblestone", terrain_data["floor"])
    wall   = terrain_data["wall"]
    floor  = terrain_data["floor"]

    # Cobblestone base
    grass = terrain_data["grass"]

    for x in range(map_width):
        for y in range(map_height):
            local_map.set_tile(x, y, "varied_grass",
                            grass["walkable"], grass["transparent"])

    # Scatter a few building footprints
    n_buildings = rng.randint(4, 8)
    for _ in range(n_buildings):
        bw = rng.randint(5, 10)
        bh = rng.randint(4, 8)
        bx = rng.randint(2, map_width  - bw - 2)
        by = rng.randint(2, map_height - bh - 2)

        # Walls
        for x in range(bx, bx + bw):
            for y in range(by, by + bh):
                if (x == bx or x == bx + bw - 1 or
                        y == by or y == by + bh - 1):
                    local_map.set_tile(x, y, "wall",
                                       wall["walkable"], wall["transparent"])
                else:
                    local_map.set_tile(x, y, "floor",
                                       floor["walkable"], floor["transparent"])

        # Door on a random wall
        door_side = rng.choice(["north", "south", "east", "west"])
        if door_side == "north":
            dx, dy = bx + bw // 2, by
        elif door_side == "south":
            dx, dy = bx + bw // 2, by + bh - 1
        elif door_side == "west":
            dx, dy = bx, by + bh // 2
        else:
            dx, dy = bx + bw - 1, by + bh // 2

        t = terrain_data["door_closed"]
        local_map.set_tile(dx, dy, "door_closed",
                           t["walkable"], t["transparent"])

    cx, cy = map_width // 2, map_height // 2
    local_map.set_tile(cx, cy, "cobblestone",
                       cobble["walkable"], cobble["transparent"])

    punch_edge_transitions(local_map, terrain_data, rng)
    return local_map, (cx, cy)


def _place_submap_entrance(
    local_map:    LocalMap,
    submap,
    terrain_data: dict,
) -> None:
    """
    Stamp the appropriate entrance structure (barrow_mound, rock_face_cut, or
    sunken_ruin) at a walkable interior position, then register the stairs_down
    tile it contains in local_map.submap_links.
    Placement is deterministic per submap seed and avoids map edges.
    """
    from generation.entrance_gen import _pick_layout
    from generation.layout_stamper import stamp_layout_interior

    entrance_type = SUBMAP_ENTRANCE.get(submap.submap_type)
    sub_rng = random.Random(submap.seed ^ 0xBEEF_CAFE)

    layout = _pick_layout(entrance_type, sub_rng) if entrance_type else None

    w = local_map.width
    h = local_map.height
    # Keep layout center at least 20 tiles from any edge so the structure fits
    margin = 20

    _BLOCKED_TERRAIN = (
        {"river_water", "river_bank", "river_stones", "cobblestone",
         "cobblestone_cracked", "cobblestone_mossy"}
        | {f"road_{i}" for i in range(16)}
    )

    if layout is not None:
        # Search for a walkable interior centre position
        placed = False
        for _ in range(300):
            cx = sub_rng.randint(margin, w - margin - 1)
            cy = sub_rng.randint(margin, h - margin - 1)
            if local_map.walkable[cx, cy] and \
               str(local_map.tiles[cx, cy]["terrain"]) not in _BLOCKED_TERRAIN:
                stairs_x, stairs_y = stamp_layout_interior(
                    local_map, layout, cx, cy, terrain_data
                )
                local_map.submap_links[(stairs_x, stairs_y)] = submap.submap_id
                submap.surface_x = stairs_x
                submap.surface_y = stairs_y
                placed = True
                break

        if not placed:
            # Fallback: stamp at centre
            cx, cy = w // 2, h // 2
            stairs_x, stairs_y = stamp_layout_interior(
                local_map, layout, cx, cy, terrain_data
            )
            local_map.submap_links[(stairs_x, stairs_y)] = submap.submap_id
            submap.surface_x = stairs_x
            submap.surface_y = stairs_y
    else:
        # No layout available — place a bare stairs_down tile
        t = terrain_data.get("stairs_down", terrain_data["floor"])
        for _ in range(200):
            x = sub_rng.randint(margin, w - margin - 1)
            y = sub_rng.randint(margin, h - margin - 1)
            if local_map.walkable[x, y] and \
               str(local_map.tiles[x, y]["terrain"]) not in _BLOCKED_TERRAIN:
                local_map.set_tile(x, y, "stairs_down",
                                   t["walkable"], t["transparent"])
                local_map.submap_links[(x, y)] = submap.submap_id
                submap.surface_x = x
                submap.surface_y = y
                return
        # Fallback
        cx, cy = w // 2, h // 2
        local_map.set_tile(cx, cy, "stairs_down",
                           t["walkable"], t["transparent"])
        local_map.submap_links[(cx, cy)] = submap.submap_id
        submap.surface_x = cx
        submap.surface_y = cy


# ------------------------------------------------------------------ #
#  Terrain scatter helpers (B1, B2)
# ------------------------------------------------------------------ #

def _scatter_terrain(
    local_map:      LocalMap,
    terrain_data:   dict,
    rng:            random.Random,
    source_terrains: set[str],
    target_terrain: str,
    n_clusters:     int,
    cluster_r:      int = 4,
) -> None:
    """
    Place clustered patches of target_terrain over source_terrain tiles.
    Each cluster is a blob centred on a random source tile with a
    radial probability falloff so the edges are ragged.
    """
    if target_terrain not in terrain_data:
        return
    tgt = terrain_data[target_terrain]

    w, h = local_map.width, local_map.height
    eligible = [
        (x, y)
        for x in range(1, w - 1)
        for y in range(1, h - 1)
        if str(local_map.tiles[x, y]["terrain"]) in source_terrains
    ]
    if not eligible:
        return

    for _ in range(n_clusters):
        cx, cy = rng.choice(eligible)
        for dx in range(-cluster_r, cluster_r + 1):
            for dy in range(-cluster_r, cluster_r + 1):
                dist = (dx * dx + dy * dy) ** 0.5
                if dist > cluster_r:
                    continue
                prob = 1.0 - (dist / cluster_r) ** 1.5
                if rng.random() > prob:
                    continue
                tx, ty = cx + dx, cy + dy
                if not local_map.in_bounds(tx, ty):
                    continue
                if str(local_map.tiles[tx, ty]["terrain"]) in source_terrains:
                    local_map.set_tile(tx, ty, target_terrain,
                                       tgt["walkable"], tgt["transparent"])


# ------------------------------------------------------------------ #
#  Waystone placement helper (B4)
# ------------------------------------------------------------------ #

_ROAD_TERRAIN = {"cobblestone"} | {f"road_{i}" for i in range(16)}


def _place_waystones(
    local_map:    LocalMap,
    terrain_data: dict,
    chunk:        Chunk,
    rng:          random.Random,
) -> None:
    """
    Place 1-2 waystone_plinth tiles adjacent to road terrain.
    Crossroads chunks (4 road edges) always get a waystone at the
    road intersection. Other road chunks get one at 25% probability.
    """
    if "waystone_plinth" not in terrain_data:
        return

    # Count road-type edge connectors
    road_edges = [
        edge for edge, conns in chunk.edges.items()
        if any(c.connector_type == ConnectorType.ROAD for c in conns)
    ]
    if not road_edges:
        return

    is_crossroads = len(road_edges) >= 4
    if not is_crossroads and rng.random() > 0.25:
        return

    n_waystones = 2 if is_crossroads else 1
    wt = terrain_data["waystone_plinth"]
    w, h = local_map.width, local_map.height

    # Find tiles adjacent to road terrain
    road_adjacent: list[tuple[int, int]] = []
    for x in range(1, w - 1):
        for y in range(1, h - 1):
            if str(local_map.tiles[x, y]["terrain"]) in _ROAD_TERRAIN:
                continue  # skip road tiles themselves
            if not local_map.walkable[x, y]:
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if local_map.in_bounds(nx, ny) and \
                        str(local_map.tiles[nx, ny]["terrain"]) in _ROAD_TERRAIN:
                    road_adjacent.append((x, y))
                    break

    if not road_adjacent:
        return

    # Collect positions already occupied by a waystone (terrain or decor)
    rng.shuffle(road_adjacent)
    placed = 0
    existing_wt: set[tuple[int, int]] = {
        (x, y)
        for x in range(w) for y in range(h)
        if str(local_map.tiles[x, y]["terrain"]) == "waystone_plinth"
    }
    # Also check decor layer for existing waystones
    for (dx, dy), did in getattr(local_map, "decor", {}).items():
        if did == "waystone_plinth":
            existing_wt.add((dx, dy))
    used: set[tuple[int, int]] = set(existing_wt)
    from generation.decor_utils import place_decor as _pd_ws
    for (x, y) in road_adjacent:
        if (x, y) in existing_wt:
            continue  # already a waystone here
        # Keep waystones at least 5 tiles apart from each other and existing ones
        if any(abs(x - ux) + abs(y - uy) < 5 for ux, uy in used):
            continue
        _pd_ws(local_map, x, y, "waystone_plinth")
        used.add((x, y))
        placed += 1
        if placed >= n_waystones:
            break
    wx = getattr(chunk, "wx", "?")
    wy = getattr(chunk, "wy", "?")
    print(f"[gen] waystones placed in chunk ({wx},{wy}): {placed}")


# ------------------------------------------------------------------ #
#  Wilderness scatter: dead wood and flint outcrops
# ------------------------------------------------------------------ #

_BLOCKED_SCATTER = (
    {"tree", "rock", "wall", "water", "river_water", "river_bank", "river_stones",
     "waystone_plinth", "cobblestone", "cobblestone_cracked", "cobblestone_mossy",
     "mud", "door_closed", "door_open"}
    | {f"road_{i}" for i in range(16)}
)
def _scatter_dead_wood(
    local_map:    LocalMap,
    terrain_data: dict,
    rng:          random.Random,
) -> None:
    """
    For each tree tile, with 8% probability place a dead_wood tile on one
    randomly chosen walkable adjacent tile that is open ground.
    """
    dw_entry = terrain_data.get("dead_wood", {})
    dw_walk  = dw_entry.get("walkable", True)
    dw_trans = dw_entry.get("transparent", True)
    w, h = local_map.width, local_map.height

    _ADJ = [(-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1)]

    for x in range(1, w - 1):
        for y in range(1, h - 1):
            t = str(local_map.tiles[x, y]["terrain"])
            if t != "tree":
                continue
            if rng.random() >= 0.08:
                continue
            # Pick a random walkable adjacent tile that is open ground
            candidates = []
            rng.shuffle(_ADJ)
            for dx, dy in _ADJ:
                nx, ny = x + dx, y + dy
                if not local_map.in_bounds(nx, ny):
                    continue
                nt = str(local_map.tiles[nx, ny]["terrain"])
                if local_map.walkable[nx, ny] and nt not in _BLOCKED_SCATTER:
                    candidates.append((nx, ny))
            if candidates:
                px, py = rng.choice(candidates)
                local_map.set_tile(px, py, "dead_wood", dw_walk, dw_trans)


def _scatter_flint(
    local_map:    LocalMap,
    terrain_data: dict,
    rng:          random.Random,
    rate:         float,
) -> None:
    """
    Scatter flint_rock tiles across walkable, non-blocked ground at the
    given per-tile probability. Each placed tile has a 30% chance to spawn
    a second adjacent one.
    """
    fo_entry = terrain_data.get("flint_rock", {})
    fo_walk  = fo_entry.get("walkable", True)
    fo_trans = fo_entry.get("transparent", True)
    w, h = local_map.width, local_map.height

    _ADJ4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def _try_place(fx: int, fy: int) -> bool:
        if not local_map.in_bounds(fx, fy):
            return False
        ft = str(local_map.tiles[fx, fy]["terrain"])
        if not local_map.walkable[fx, fy]:
            return False
        if ft in _BLOCKED_SCATTER or ft == "flint_rock":
            return False
        local_map.set_tile(fx, fy, "flint_rock", fo_walk, fo_trans)
        return True

    for x in range(1, w - 1):
        for y in range(1, h - 1):
            t = str(local_map.tiles[x, y]["terrain"])
            if not local_map.walkable[x, y]:
                continue
            if t in _BLOCKED_SCATTER or t == "flint_rock":
                continue
            if rng.random() >= rate:
                continue
            if _try_place(x, y):
                # Cluster: 30% chance of a second adjacent tile
                if rng.random() < 0.3:
                    nbrs = list(_ADJ4)
                    rng.shuffle(nbrs)
                    for dx, dy in nbrs:
                        if _try_place(x + dx, y + dy):
                            break


def _scatter_clay(
    local_map:    LocalMap,
    terrain_data: dict,
    rng:          random.Random,
) -> None:
    """
    Scatter clay_deposit tiles on walkable ground within 2 tiles of river_water.
    At most 4 deposits per chunk. Each placed tile has a 40% chance for a second.
    """
    cl_entry = terrain_data.get("clay_deposit", {})
    cl_walk  = cl_entry.get("walkable", True)
    cl_trans = cl_entry.get("transparent", True)
    w, h     = local_map.width, local_map.height

    _RIVER_TILES = {"river_water", "river_bank", "river_stones"}
    _ADJ4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    # Collect tiles adjacent to river water
    candidates: list[tuple[int, int]] = []
    for x in range(1, w - 1):
        for y in range(1, h - 1):
            t = str(local_map.tiles[x, y]["terrain"])
            if not local_map.walkable[x, y]:
                continue
            if t in _BLOCKED_SCATTER or t in _RIVER_TILES:
                continue
            # Check for river_water within 2 tiles (Chebyshev)
            near_river = any(
                local_map.in_bounds(x + dx, y + dy)
                and str(local_map.tiles[x + dx, y + dy]["terrain"]) in _RIVER_TILES
                for dx in range(-2, 3)
                for dy in range(-2, 3)
            )
            if near_river:
                candidates.append((x, y))

    rng.shuffle(candidates)
    placed = 0
    for cx, cy in candidates:
        if placed >= 4:
            break
        t = str(local_map.tiles[cx, cy]["terrain"])
        if t in _BLOCKED_SCATTER or t == "clay_deposit":
            continue
        local_map.set_tile(cx, cy, "clay_deposit", cl_walk, cl_trans)
        placed += 1
        # Cluster: 40% chance of a second adjacent tile
        if rng.random() < 0.4:
            nbrs = list(_ADJ4)
            rng.shuffle(nbrs)
            for ddx, ddy in nbrs:
                nx, ny = cx + ddx, cy + ddy
                if not local_map.in_bounds(nx, ny):
                    continue
                nt = str(local_map.tiles[nx, ny]["terrain"])
                if not local_map.walkable[nx, ny]:
                    continue
                if nt in _BLOCKED_SCATTER or nt == "clay_deposit":
                    continue
                local_map.set_tile(nx, ny, "clay_deposit", cl_walk, cl_trans)
                break