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
    context=None,
) -> tuple[LocalMap, tuple[int, int]]:
    """
    Dispatch to the correct generator based on chunk region type.
    After generation, carve edge connectors (rivers, roads, paths).
    Returns (LocalMap, player_spawn_xy).
    """
    from generation.context import GenerationContext
    context = context or GenerationContext(getattr(chunk, 'world_seed', 0), chunk.seed, (chunk.wx, chunk.wy, None))
    rng = context.rng('terrain')

    if chunk.region_type == RegionType.FOREST:
        local_map, spawn = _generate_forest(
            map_width, map_height, terrain_data, rng, context=context
        )

    elif chunk.region_type == RegionType.TOWN:
        if data is not None:
            from generation.town_gen import generate_town
            local_map = _generate_town_base(map_width, map_height, terrain_data, context=context)
            local_map, spawn = generate_town(
                chunk         = chunk,
                local_map     = local_map,
                map_w         = map_width,
                map_h         = map_height,
                terrain_data  = terrain_data,
                building_data = data.buildings,
                name_gen      = None,
                rng           = context.rng('buildings'),
                data          = data,
            )
        else:
            local_map, spawn = _generate_town(
                map_width, map_height, terrain_data, rng, context=context
            )

    elif chunk.region_type == RegionType.SWAMP:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng, context=context,
            floor_terrain="mud", tree_chance=0.12,
        )

    elif chunk.region_type == RegionType.HEATH:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng, context=context,
            floor_terrain="varied_grass", tree_chance=0.03,
        )

    elif chunk.region_type == RegionType.MOUNTAIN:
        local_map, spawn = _generate_mountain(
            map_width, map_height, terrain_data, rng, context=context
        )

    elif chunk.region_type == RegionType.DEEP_MOUNTAIN:
        local_map, spawn = _generate_mountain(
            map_width, map_height, terrain_data, rng, context=context
        )

    elif chunk.region_type == RegionType.CAPITAL:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng, context=context,
            floor_terrain="cobblestone", tree_chance=0.0,
        )

    elif chunk.region_type == RegionType.DROWNED_WOOD:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng, context=context,
            floor_terrain="mud", tree_chance=0.20,
        )

    elif chunk.region_type == RegionType.ASH_WASTES:
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng, context=context,
            floor_terrain="varied_grass", tree_chance=0.01,
        )

    else:  # PLAINS / UNKNOWN default
        local_map, spawn = _generate_open(
            map_width, map_height, terrain_data, rng, context=context,
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
        chunk.edges, map_width, map_height, context.rng('roads'),
        town_id=getattr(chunk, "town_id", -1),
    )

    rng = context.rng('dressing')

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
    from generation.access import arrival_anchor
    spawn = arrival_anchor(local_map, spawn, data)
    local_map.required_access_anchors = [spawn]
    local_map.required_access_anchors.extend(sorted(
        xy for xy in getattr(local_map, 'road_cells', set())
        if xy[0] in (0, map_width-1) or xy[1] in (0, map_height-1)))
    if getattr(chunk, 'town_data', None):
        staged_content = chunk.town_data.item_spawns + chunk.town_data.creature_spawns
        local_map.protected_cells = set(getattr(local_map, 'protected_cells', set()))
        for spec in staged_content:
            x, y = spec['x'], spec['y']
            local_map.protected_cells.add((x, y))
            local_map.protected_cells.update((x + dx, y + dy)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if local_map.in_bounds(x + dx, y + dy)
                and (local_map.walkable[x + dx, y + dy]
                     or str(local_map.tiles[x + dx, y + dy]['terrain']) == 'door_closed'))
    for submap in chunk.submaps:
        _place_submap_entrance(local_map, submap, terrain_data, data=data)

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
    context=None,
) -> tuple[LocalMap, tuple[int, int]]:
    local_map = LocalMap(map_width, map_height, generation_context=context)
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
    context=None,
) -> tuple[LocalMap, tuple[int, int]]:
    local_map = LocalMap(map_width, map_height, generation_context=context)
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
    context=None,
) -> tuple[LocalMap, tuple[int, int]]:
    local_map = LocalMap(map_width, map_height, generation_context=context)
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
    context=None,
) -> LocalMap:
    """Grass-filled base map for the full town generator to stamp over."""
    local_map = LocalMap(map_width, map_height, generation_context=context)
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
    context=None,
) -> tuple[LocalMap, tuple[int, int]]:
    """
    Basic town generator — cobblestone base with scattered
    building footprints. Will be replaced by the full zone-based
    town generator once the structure placer is integrated.
    """
    local_map = LocalMap(map_width, map_height, generation_context=context)
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


def _place_submap_entrance(local_map, submap, terrain_data, data=None):
    """Bounded whole-footprint placement; commit a real usable stair or fail closed."""
    import copy
    from generation.access import reachable, required_anchors
    from generation.context import map_context, GenerationError
    from generation.entrance_gen import _pick_layout
    from generation.layout_stamper import stamp_layout_interior
    from rendering.decor import PLANT_DECOR_IDS
    from generation.decor_utils import clear_decor
    context = map_context(local_map)
    rng = context.rng('entrance-position', submap.submap_id, submap.seed)
    layout = _pick_layout(SUBMAP_ENTRANCE.get(submap.submap_type), rng, data=data)
    w, h = local_map.width, local_map.height
    protected = set(getattr(local_map, 'protected_cells', set()))
    protected.update(local_map.submap_links)
    protected.update(local_map.floor_objects)
    protected.update(local_map.container_state)
    protected.update(xy for xy, decor in local_map.decor.items() if decor not in PLANT_DECOR_IDS)
    protected.update((x, y) for x in range(w) for y in range(h)
                     if str(local_map.tiles[x, y]['terrain']) in
                     {'stairs_up', 'stairs_down', 'river_water', 'river_bank', 'river_stones',
                      'cobblestone', 'flagstone'} or str(local_map.tiles[x, y]['terrain']).startswith('road_'))
    decor_data = data.decoratives if data is not None else {}
    anchors = required_anchors(local_map, data)
    protected.update(anchors)

    def enterable(m, xy):
        terrain = str(m.tiles[xy]['terrain'])
        return (m.walkable[xy] or terrain == 'door_closed') and not decor_data.get(
            m.decor.get(xy), {}).get('blocks_movement', False)

    # Keep all currently legal interaction/arrival neighbours of mandatory
    # objects. Candidate footprints must not wall in an untouched object.
    objects = (set(local_map.submap_links) | set(local_map.floor_objects)
               | set(local_map.container_state)
               | {xy for xy, decor in local_map.decor.items() if decor not in PLANT_DECOR_IDS})
    for x, y in objects:
        protected.update((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                         if local_map.in_bounds(x + dx, y + dy) and enterable(local_map, (x + dx, y + dy)))

    def access(m, stair, footprint):
        reached = reachable(m, anchors[0], data)
        return stair in reached and all(p in reached for p in [*anchors, *m.submap_links])

    candidates = [(x, y) for x in range(1, w - 1) for y in range(1, h - 1)]
    rng.shuffle(candidates)
    if layout is not None:
        rows = layout['layers']
        lw, lh = max(map(len, rows)), len(rows)
        for cx, cy in candidates[:300]:
            ox, oy = cx - lw // 2, cy - lh // 2
            footprint = {(x, y) for x in range(ox, ox + lw) for y in range(oy, oy + lh)}
            if ox < 1 or oy < 1 or ox + lw >= w or oy + lh >= h or footprint & protected:
                continue
            staged = copy.deepcopy(local_map)
            for xy in footprint:
                clear_decor(staged, *xy)  # replace only natural vegetation, checked above
            stair = stamp_layout_interior(staged, layout, cx, cy, terrain_data,
                      rng=context.rng('entrance-layout', submap.submap_id, cx, cy))
            if str(staged.tiles[stair]['terrain']) != 'stairs_down' or not access(staged, stair, footprint):
                continue
            staged.submap_links[stair] = submap.submap_id
            staged.protected_cells = protected | footprint
            # Only terrain/decor changed: preserve existing object identities.
            for field in ('tiles', 'decor'):
                setattr(local_map, field, getattr(staged, field))
            local_map.submap_links[stair] = submap.submap_id
            local_map.protected_cells = staged.protected_cells
            submap.surface_x, submap.surface_y = stair
            return
    # Explicit small fallback: a bare stair on existing accessible ground, with
    # a usable neighbouring tile. Never use a generic centre or overwrite content.
    for xy in candidates[:300]:
        if xy in protected or not enterable(local_map, xy):
            continue
        if not access(local_map, xy, {xy}):
            continue
        clear_decor(local_map, *xy)
        td = terrain_data['stairs_down']
        local_map.set_tile(*xy, 'stairs_down', td['walkable'], td['transparent'])
        local_map.submap_links[xy] = submap.submap_id
        local_map.protected_cells = protected | {xy}
        local_map.generation_diagnostics = getattr(local_map, 'generation_diagnostics', []) + [
            dict(kind='entrance', submap=submap.submap_id, status='bare-stair-fallback',
                 reason='no valid authored footprint' if layout else 'no authored layout',
                 revision=context.revision)]
        submap.surface_x, submap.surface_y = xy
        return
    raise GenerationError(f'{submap.submap_id}: no valid entrance footprint or accessible fallback')


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
