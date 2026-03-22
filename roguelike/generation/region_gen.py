# generation/region_gen.py
from __future__ import annotations
import random
from world.local_map import LocalMap
from world.world_map import Chunk, RegionType
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
            floor_terrain="grass", tree_chance=0.03,
        )

    elif chunk.region_type == RegionType.MOUNTAIN:
        local_map, spawn = _generate_mountain(
            map_width, map_height, terrain_data, rng
        )

    else:  # PLAINS default
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng,
            floor_terrain="grass", tree_chance=0.06,
        )

    # Carve rivers, roads, paths from edge connectors
    carve_connectors(
        local_map, terrain_data,
        chunk.edges, map_width, map_height, rng,
    )

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
    floor_terrain: str = "grass",
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

    punch_edge_transitions(local_map, terrain_data, rng)
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
                    local_map.tiles[x, y]["terrain"] = b"grass"
                    local_map.walkable[x, y]    = True
                    local_map.transparent[x, y] = True


def _generate_forest(
    map_width: int,
    map_height: int,
    terrain_data: dict,
    rng: random.Random,
) -> tuple[LocalMap, tuple[int, int]]:
    local_map = LocalMap(map_width, map_height)
    grass = terrain_data["grass"]
    tree  = terrain_data["tree"]

    for x in range(map_width):
        for y in range(map_height):
            if rng.random() < 0.35:
                local_map.set_tile(x, y, "tree",
                                   tree["walkable"], tree["transparent"])
            else:
                local_map.set_tile(x, y, "grass",
                                   grass["walkable"], grass["transparent"])

    cx, cy = map_width // 2, map_height // 2
    for x in range(cx - 2, cx + 3):
        for y in range(cy - 2, cy + 3):
            if local_map.in_bounds(x, y):
                local_map.set_tile(x, y, "grass",
                                   grass["walkable"], grass["transparent"])

    _ensure_forest_connectivity(local_map, map_width, map_height)
    punch_edge_transitions(local_map, terrain_data, rng)
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

    punch_edge_transitions(local_map, terrain_data, rng)
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
            local_map.set_tile(x, y, "grass",
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
    for x in range(map_width):
        for y in range(map_height):
            local_map.set_tile(x, y, "cobblestone",
                               cobble["walkable"], cobble["transparent"])

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

    if layout is not None:
        # Search for a walkable interior centre position
        placed = False
        for _ in range(300):
            cx = sub_rng.randint(margin, w - margin - 1)
            cy = sub_rng.randint(margin, h - margin - 1)
            if local_map.walkable[cx, cy]:
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
            if local_map.walkable[x, y]:
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