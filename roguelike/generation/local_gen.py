# generation/local_gen.py
from __future__ import annotations
import math
import random
import tcod.bsp
from world.local_map import LocalMap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.world_map import SubMap


def generate_submap(
    submap:       "SubMap",
    map_width:    int,
    map_height:   int,
    terrain_data: dict,
    data=None,
) -> tuple[LocalMap, list]:
    """
    Generate a LocalMap for a SubMap. Returns (local_map, entities).
    If submap.layout_id is set, stamps the named layout instead of BSP.
    Stores the player entry point on submap.entry_x/y.
    Marks submap.generated = True.
    """
    if submap.layout_id:
        local_map, entities, entry_x, entry_y = _generate_submap_from_layout(
            submap, map_width, map_height, terrain_data
        )
    else:
        local_map, entities, entry_x, entry_y = _generate_submap_bsp(
            submap, map_width, map_height, terrain_data, data=data
        )

    submap.entry_x  = entry_x
    submap.entry_y  = entry_y
    submap.generated = True
    return local_map, entities


_TEXT_TABLE_MAP: dict[str, list[str]] = {
    "barrow":       ["world_texts_official", "world_texts_scholarly"],
    "cave":         ["world_texts_common"],
    "sunken_ruin":  ["world_texts_scholarly", "world_texts_official"],
    "flooded_ruin": ["world_texts_common"],
    "deep_vault":   ["world_texts_scholarly"],
    "crypt":        ["world_texts_official"],
    "cellar":       ["world_texts_common"],
}


def _place_found_texts(
    local_map,
    rooms: list[dict],
    submap_type: str,
    seed: int,
    data,
) -> list[dict]:
    """
    Scatter readable text items in BSP dungeon rooms.
    Returns a list of layout entity dicts compatible with _spawn_layout_entities.
    """
    if not rooms or not data:
        return []
    if submap_type == "laboratory":
        return []

    table_names = _TEXT_TABLE_MAP.get(submap_type, ["world_texts_common"])
    rng = random.Random(seed ^ 0xFEED_BEEF)

    eligible = [r for r in rooms if r["w"] >= 4 and r["h"] >= 4]
    if not eligible:
        return []

    count        = rng.randint(2, min(4, len(eligible)))
    chosen_rooms = rng.sample(eligible, count)
    placed: list[dict] = []

    for room in chosen_rooms:
        rx, ry, rw, rh = room["x"], room["y"], room["w"], room["h"]

        tx, ty = rx + rw // 2, ry + rh // 2
        for _ in range(20):
            cx = rng.randint(rx + 1, rx + rw - 2)
            cy = rng.randint(ry + 1, ry + rh - 2)
            if local_map.in_bounds(cx, cy) and local_map.walkable[cx, cy]:
                tx, ty = cx, cy
                break

        table_name = rng.choice(table_names)
        table = data.loot.get(table_name)
        if not table:
            continue
        entries = table.get("entries", [])
        if not entries:
            continue
        weights = [e["weight"] for e in entries]
        entry   = rng.choices(entries, weights=weights, k=1)[0]

        if entry.get("type") == "text":
            placed.append({
                "kind":    "item",
                "item_id": "lab_note",
                "text_id": entry.get("text_id", ""),
                "x": tx,
                "y": ty,
            })

    return placed


def _generate_submap_bsp(
    submap:       "SubMap",
    map_width:    int,
    map_height:   int,
    terrain_data: dict,
    data=None,
) -> tuple[LocalMap, list, int, int]:
    """BSP dungeon generation. Returns (local_map, entities, entry_x, entry_y)."""
    local_map, (entry_x, entry_y) = generate_dungeon(
        map_width, map_height, terrain_data, seed=submap.seed
    )

    # Stamp stairs_up at the entry point
    if local_map.in_bounds(entry_x, entry_y) and local_map.walkable[entry_x, entry_y]:
        t = terrain_data.get("stairs_up", terrain_data.get("floor", {}))
        local_map.set_tile(entry_x, entry_y, "stairs_up",
                           bool(t.get("walkable", True)),
                           bool(t.get("transparent", True)))

    # Place found text items in rooms
    rooms = getattr(local_map, "_rooms", [])
    text_entities = _place_found_texts(
        local_map, rooms, submap.submap_type, submap.seed, data
    )

    return local_map, text_entities, entry_x, entry_y


def _generate_submap_from_layout(
    submap:       "SubMap",
    map_width:    int,
    map_height:   int,
    terrain_data: dict,
) -> tuple[LocalMap, list, int, int]:
    """
    Stamp a hand-crafted layout JSON as the entire submap.
    Returns (local_map, entities, entry_x, entry_y).
    """
    import json
    import pathlib

    layout_path = (
        pathlib.Path(__file__).parent.parent
        / "data" / "layouts" / f"{submap.layout_id}.json"
    )
    if not layout_path.exists():
        # Fallback to BSP if layout file is missing
        return _generate_submap_bsp(submap, map_width, map_height, terrain_data)

    with open(layout_path, encoding="utf-8") as f:
        layout = json.load(f)

    # DEBUG_MODE layout validation
    from config import DEBUG_MODE
    if DEBUG_MODE:
        _lay_w = layout.get("width", 0)
        _lay_rows = layout.get("layers", [])
        for _ri, _rr in enumerate(_lay_rows):
            if len(_rr) != _lay_w:
                print(f"[LAYOUT ERROR] {layout.get('id','?')} row {_ri} has length {len(_rr)}, expected {_lay_w}")
        _leg = layout.get("legend", {})
        _wall_ch = {ch for ch, tid in _leg.items() if tid in ("wall", "old_wall", None) or tid is None}
        for _st in layout.get("special_tiles", []):
            _stx, _sty = _st.get("x", -1), _st.get("y", -1)
            if 0 <= _sty < len(_lay_rows) and 0 <= _stx < len(_lay_rows[_sty]):
                if _lay_rows[_sty][_stx] in _wall_ch:
                    print(f"[LAYOUT ERROR] {layout.get('id','?')} special_tile at ({_stx},{_sty}) is on wall char '{_lay_rows[_sty][_stx]}'")
            else:
                print(f"[LAYOUT ERROR] {layout.get('id','?')} special_tile at ({_stx},{_sty}) is out of bounds")

    # Fill map with walls
    wall = terrain_data.get("wall", terrain_data["floor"])
    local_map = LocalMap(map_width, map_height)
    for x in range(map_width):
        for y in range(map_height):
            local_map.set_tile(x, y, "wall", wall["walkable"], wall["transparent"])

    # Stamp layout centered
    layers = layout["layers"]
    legend = layout["legend"]
    lay_h  = len(layers)
    lay_w  = max(len(row) for row in layers)
    origin_x = map_width  // 2 - lay_w // 2
    origin_y = map_height // 2 - lay_h // 2

    stairs_up_pos: tuple[int, int] | None = None

    for row_idx, row in enumerate(layers):
        for col_idx, ch in enumerate(row):
            terrain = legend.get(ch)
            if terrain is None:
                continue
            tx = origin_x + col_idx
            ty = origin_y + row_idx
            if not local_map.in_bounds(tx, ty):
                continue
            td = terrain_data.get(terrain, terrain_data.get("floor", {}))
            local_map.set_tile(
                tx, ty, terrain,
                bool(td.get("walkable", True)),
                bool(td.get("transparent", True)),
            )
            if terrain == "stairs_up":
                stairs_up_pos = (tx, ty)

    # Player start position
    ps = layout.get("player_start", {"x": lay_w // 2, "y": lay_h // 2})
    entry_x = origin_x + ps["x"]
    entry_y = origin_y + ps["y"]

    # Place a candle near the player start in the starting lab
    if getattr(submap, "layout_id", None) == "starting_lab":
        from generation.decor_utils import place_decor
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            cx, cy = entry_x + dx, entry_y + dy
            if local_map.in_bounds(cx, cy) and local_map.walkable[cx, cy]:
                place_decor(local_map, cx, cy, "decor_candle")
                break

    # If stairs_up not in layout, place via exit_direction fallback
    if stairs_up_pos is None:
        exit_dir = layout.get("exit_direction", "south")
        exit_y_l = layout.get("exit_y", lay_h - 2)
        if exit_dir in ("south", "north"):
            exit_tx = origin_x + lay_w // 2
            exit_ty = origin_y + exit_y_l
        else:
            exit_tx = origin_x + layout.get("exit_x", lay_w - 2)
            exit_ty = origin_y + lay_h // 2
        t_up = terrain_data.get("stairs_up", terrain_data.get("floor", {}))
        if local_map.in_bounds(exit_tx, exit_ty):
            local_map.set_tile(exit_tx, exit_ty, "stairs_up",
                               bool(t_up.get("walkable", True)),
                               bool(t_up.get("transparent", True)))

    # Collect entity spawns from special_tiles
    entities: list = []
    for spec in layout.get("special_tiles", []):
        sx = origin_x + spec["x"]
        sy = origin_y + spec["y"]
        if not local_map.in_bounds(sx, sy):
            continue
        if spec["type"] == "item":
            entities.append({
                "kind":    "item",
                "item_id": spec.get("item_id", ""),
                "text_id": spec.get("text_id", ""),
                "x": sx, "y": sy,
            })
        elif spec["type"] == "body":
            entities.append({
                "kind": "body",
                "name": spec.get("name", "remains"),
                "x": sx, "y": sy,
            })
        elif spec["type"] == "container":
            entities.append({
                "kind":       "container",
                "decor_id":   spec.get("decor_id", "crate"),
                "loot_pools": spec.get("loot_pools", []),
                "x": sx, "y": sy,
            })
        elif spec["type"] == "stele":
            local_map.stele_text_ids[(sx, sy)] = spec.get("text_id", "")
        elif spec["type"] == "scene":
            entities.append({
                "kind":     "scene",
                "scene_id": spec.get("scene_id", ""),
                "x": sx, "y": sy,
            })

    return local_map, entities, entry_x, entry_y


def _enforce_submap_border(local_map, map_w: int, map_h: int) -> None:
    """Seal every perimeter tile as solid wall — no BSP corridor exits at map edge."""
    for x in range(map_w):
        for y in (0, map_h - 1):
            local_map.tiles[x, y]["terrain"] = b"wall"
            local_map.walkable[x, y]    = False
            local_map.transparent[x, y] = False
    for y in range(map_h):
        for x in (0, map_w - 1):
            local_map.tiles[x, y]["terrain"] = b"wall"
            local_map.walkable[x, y]    = False
            local_map.transparent[x, y] = False


def generate_dungeon(
    map_width: int,
    map_height: int,
    terrain_data: dict,
    seed: int | None = None,
) -> tuple[LocalMap, tuple[int, int]]:
    """
    BSP dungeon generator.
    Accepts an optional seed for deterministic generation.
    """
    rng = random.Random(seed)
    local_map = LocalMap(map_width, map_height)

    bsp = tcod.bsp.BSP(x=1, y=1, width=map_width - 2, height=map_height - 2)
    bsp.split_recursive(
        depth=5,
        min_width=6,
        min_height=6,
        max_horizontal_ratio=1.5,
        max_vertical_ratio=1.5,
    )

    rooms: list[dict] = []

    for node in bsp.pre_order():
        if node.children:
            continue

        room_w = rng.randint(4, max(4, node.width  - 2))
        room_h = rng.randint(4, max(4, node.height - 2))
        room_x = node.x + rng.randint(1, max(1, node.width  - room_w - 1))
        room_y = node.y + rng.randint(1, max(1, node.height - room_h - 1))

        _carve_terrain(local_map, room_x, room_y, room_w, room_h,
                       "floor", terrain_data)

        cx = room_x + room_w // 2
        cy = room_y + room_h // 2

        if rooms:
            prev = rooms[-1]
            _carve_corridor(local_map, prev["cx"], prev["cy"],
                            cx, cy, "floor", terrain_data, rng)

        rooms.append({"x": room_x, "y": room_y,
                      "w": room_w, "h": room_h,
                      "cx": cx,    "cy": cy})

    start = rooms[0]
    local_map._rooms = rooms  # used by text placement pass
    rng2 = random.Random(seed)
    punch_edge_transitions(local_map, terrain_data, rng2)
    _enforce_submap_border(local_map, map_width, map_height)
    return local_map, (start["cx"], start["cy"])


def _carve_terrain(
    local_map: LocalMap,
    x: int, y: int, w: int, h: int,
    terrain_key: str,
    terrain_data: dict,
) -> None:
    t = terrain_data[terrain_key]
    for tx in range(x, x + w):
        for ty in range(y, y + h):
            if local_map.in_bounds(tx, ty):
                local_map.set_tile(tx, ty, terrain_key,
                                   t["walkable"], t["transparent"])


def _carve_corridor(
    local_map: LocalMap,
    x1: int, y1: int,
    x2: int, y2: int,
    terrain_key: str,
    terrain_data: dict,
    rng: random.Random,
) -> None:
    t = terrain_data[terrain_key]

    def carve(x: int, y: int) -> None:
        if local_map.in_bounds(x, y):
            local_map.set_tile(x, y, terrain_key,
                               t["walkable"], t["transparent"])

    if rng.random() < 0.5:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            carve(x, y1)
        for y in range(min(y1, y2), max(y1, y2) + 1):
            carve(x2, y)
    else:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            carve(x1, y)
        for x in range(min(x1, x2), max(x1, x2) + 1):
            carve(x, y2)

def punch_edge_transitions(
    local_map: LocalMap,
    terrain_data: dict,
    rng: random.Random,
    n_per_edge: int = 2,
    corridor_depth: int = 5,
    edge_terrain: str = "floor",
) -> None:
    """
    Punch n_per_edge openings into each map edge and carve a short
    corridor inward so the player can reach them from the interior.
    Called after any local map generation.
    edge_terrain should match the biome floor type so edge corridors
    don't leave strips of dungeon floor in wilderness chunks.
    """
    t = terrain_data.get(edge_terrain, terrain_data["floor"])
    w = local_map.width
    h = local_map.height

    def carve(x: int, y: int) -> None:
        if local_map.in_bounds(x, y):
            local_map.set_tile(x, y, edge_terrain,
                               t["walkable"], t["transparent"])

    # For each edge, pick n_per_edge random positions and carve inward
    edges = {
        "north": [(rng.randint(2, w - 3), 0)       for _ in range(n_per_edge)],
        "south": [(rng.randint(2, w - 3), h - 1)   for _ in range(n_per_edge)],
        "west":  [(0,       rng.randint(2, h - 3)) for _ in range(n_per_edge)],
        "east":  [(w - 1,   rng.randint(2, h - 3)) for _ in range(n_per_edge)],
    }

    directions = {
        "north": (0,  1),
        "south": (0, -1),
        "west":  (1,  0),
        "east":  (-1, 0),
    }

    for edge, positions in edges.items():
        dx, dy = directions[edge]
        for (ex, ey) in positions:
            for step in range(corridor_depth):
                carve(ex + dx * step, ey + dy * step)

def _walk_tiles(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    """Cardinal-only Bresenham walk at local tile scale."""
    path = [(x0, y0)]
    cx, cy = x0, y0
    dx = abs(x1 - cx); dy = abs(y1 - cy)
    sx = 1 if x1 > cx else -1
    sy = 1 if y1 > cy else -1
    err = dx - dy
    while (cx, cy) != (x1, y1):
        e2 = 2 * err
        if e2 > -dy:
            err -= dy; cx += sx
        elif e2 < dx:
            err += dx; cy += sy
        else:
            err -= dy; cx += sx
        path.append((cx, cy))
    return path


def _road_pairs(connections: list[str]) -> list[tuple[str, str]]:
    """
    Decompose connection directions into entry/exit pairs.
    1 connection → dead end (centre→edge).
    2 connections → single through path.
    3 connections → T-junction (3 spokes from centre).
    4 connections → crossroads (N↔S, E↔W).
    """
    if len(connections) == 1:
        return [("centre", connections[0])]
    if len(connections) == 2:
        return [(connections[0], connections[1])]
    if len(connections) == 3:
        return [(c, "centre") for c in connections]
    if len(connections) == 4:
        pairs: list[tuple[str,str]] = []
        if "N" in connections and "S" in connections:
            pairs.append(("N", "S"))
        if "E" in connections and "W" in connections:
            pairs.append(("E", "W"))
        paired = {d for p in pairs for d in p}
        for c in connections:
            if c not in paired:
                pairs.append((c, "centre"))
        return pairs
    return []


def _road_endpoint(direction: str, w: int, h: int,
                   rng: random.Random) -> tuple[int, int]:
    """Local tile entry/exit point for a road direction. Slight rng jitter."""
    mid_x, mid_y = w // 2, h // 2
    jitter = rng.randint(-2, 2)
    if direction == "N":      return (mid_x + jitter, 0)
    if direction == "S":      return (mid_x + jitter, h - 1)
    if direction == "E":      return (w - 1, mid_y + jitter)
    if direction == "W":      return (0, mid_y + jitter)
    # centre
    return (mid_x, mid_y)


def _local_road_walk(x0: int, y0: int, x1: int, y1: int,
                     w: int, h: int, rng: random.Random) -> list[tuple[int, int]]:
    """
    Walk x0,y0 → x1,y1 at local tile scale with a single midpoint displacement
    for gentle winding. Returns a cardinal-step path.
    """
    mx, my = (x0 + x1) // 2, (y0 + y1) // 2
    dx, dy = x1 - x0, y1 - y0
    length = math.sqrt(dx * dx + dy * dy)

    if length > 8:
        perp_x = -dy / length
        perp_y =  dx / length
        offset = rng.uniform(0.10, 0.20) * length
        if rng.random() < 0.5:
            offset = -offset
        mx = int(mx + perp_x * offset)
        my = int(my + perp_y * offset)
        mx = max(1, min(w - 2, mx))
        my = max(1, min(h - 2, my))

    path: list[tuple[int, int]] = []
    path.extend(_walk_tiles(x0, y0, mx, my))
    path.extend(_walk_tiles(mx, my, x1, y1)[1:])
    return path


def _carve_road_path(
    path: list[tuple[int, int]],
    local_map: "LocalMap",
    terrain_data: dict,
    w: int,
    h: int,
) -> set[tuple[int, int]]:
    """
    Write road_0 tiles along path with 3-tile width (centre + 1 either side
    perpendicular to direction of travel). Never overwrites river_water.
    Returns the full set of road path tiles (including those skipped due to river).
    """
    all_road_tiles: set[tuple[int, int]] = set()
    road = terrain_data.get("road_0", terrain_data.get("cobblestone", terrain_data["floor"]))
    for i, (tx, ty) in enumerate(path):
        if i < len(path) - 1:
            nx, ny = path[i + 1]
        elif i > 0:
            nx, ny = path[i - 1]
            nx, ny = 2 * tx - nx, 2 * ty - ny   # extrapolate
        else:
            nx, ny = tx, ty

        ddx, ddy = nx - tx, ny - ty

        offsets = [(0, 0)]
        if ddx != 0:       # travelling E/W — widen N/S
            offsets += [(0, -1), (0, 1)]
        elif ddy != 0:     # travelling N/S — widen E/W
            offsets += [(-1, 0), (1, 0)]

        for ox, oy in offsets:
            fx, fy = tx + ox, ty + oy
            if 0 <= fx < w and 0 <= fy < h and local_map.in_bounds(fx, fy):
                all_road_tiles.add((fx, fy))
                cur = str(local_map.tiles[fx, fy]["terrain"])
                if cur != "river_water":
                    local_map.set_tile(fx, fy, "road_0",
                                       road["walkable"], road["transparent"])
    return all_road_tiles


def _carve_road_network(
    local_map: "LocalMap",
    terrain_data: dict,
    connections: list[str],
    w: int,
    h: int,
    rng: random.Random,
) -> set[tuple[int, int]]:
    """
    Carve road terrain for all connection pairs in this chunk.
    Uses the pair model so corners/T-junctions/crossroads are correct.
    Returns the full set of road path tiles (including those over river).
    """
    all_tiles: set[tuple[int, int]] = set()
    pairs = _road_pairs(connections)
    for a, b in pairs:
        p0 = _road_endpoint(a, w, h, rng)
        p1 = _road_endpoint(b, w, h, rng)
        path = _local_road_walk(p0[0], p0[1], p1[0], p1[1], w, h, rng)
        all_tiles |= _carve_road_path(path, local_map, terrain_data, w, h)
    return all_tiles


def carve_connectors(
    local_map: LocalMap,
    terrain_data: dict,
    edges: dict,
    map_width: int,
    map_height: int,
    rng: random.Random,
    town_id: int = -1,
) -> None:
    """
    Read edge connectors from a chunk and carve their features
    into the local map. Called after base terrain generation.
    Roads are handled as a network (all connections at once) so corners,
    T-junctions and crossroads produce correct geometry. Town chunks skip
    road carving — town_gen manages their road terrain.
    """
    from world.world_map import ConnectorType

    EDGE_TO_DIR = {"north": "N", "south": "S", "east": "E", "west": "W"}

    # Collect all road and river edges first; carve as networks
    road_edges: list[str] = []
    river_edges: list[str] = []

    for edge, connectors in edges.items():
        for connector in connectors:
            if connector.connector_type == ConnectorType.RIVER:
                if edge in EDGE_TO_DIR and EDGE_TO_DIR[edge] not in river_edges:
                    river_edges.append(EDGE_TO_DIR[edge])
            elif connector.connector_type == ConnectorType.ROAD:
                if edge in EDGE_TO_DIR and EDGE_TO_DIR[edge] not in road_edges:
                    road_edges.append(EDGE_TO_DIR[edge])
            elif connector.connector_type == ConnectorType.PATH:
                _carve_path_connector(
                    local_map, terrain_data,
                    edge, connector.position,
                    map_width, map_height, rng,
                )

    # Carve rivers as paired network (same pairing model as roads)
    if river_edges:
        _carve_river_network(
            local_map, terrain_data, river_edges,
            map_width, map_height, rng,
        )

    # Carve road network — skip town chunks (town_gen handles their roads)
    _road_path_tiles: set[tuple[int, int]] = set()
    if road_edges and town_id == -1:
        _road_path_tiles = _carve_road_network(
            local_map, terrain_data, road_edges,
            map_width, map_height, rng,
        )
    elif road_edges and town_id >= 0:
        # Town chunk: connect external road entry points to the nearest
        # existing town road/path tile so the road network is seamless.
        _connect_external_roads_to_town(
            local_map, terrain_data, road_edges,
            map_width, map_height, rng,
        )

    # Post-process: place river bank tiles at road-river crossings (fords)
    if _road_path_tiles and river_edges and town_id == -1:
        _place_ford_crossings(local_map, terrain_data, map_width, map_height, rng,
                              _road_path_tiles)


_TOWN_ROAD_TILES = frozenset({
    "road_0", "cobblestone", "flagstone", "cobblestone_cracked",
    "cobblestone_mossy", "weedy_cobble", "gravel", "dirt_path", "packed_earth",
})

_TOWN_ROAD_OVERWRITE = frozenset({
    "grass", "varied_grass", "tall_grass", "mud", "packed_earth",
})


def _connect_external_roads_to_town(
    local_map: "LocalMap",
    terrain_data: dict,
    road_edges: list[str],
    map_width: int,
    map_height: int,
    rng: random.Random,
) -> None:
    """Connect external road entry points to the nearest town road tile.

    For each road edge direction, compute the edge entry point, find the
    nearest existing town road tile, and walk a road_0 path between them.
    Only overwrites soft terrain — never buildings, walls, or water.
    """
    road_td = terrain_data.get("road_0", terrain_data.get("cobblestone",
                               terrain_data.get("floor", {})))
    if not road_td:
        return

    for direction in road_edges:
        # Entry point at chunk edge
        ex, ey = _road_endpoint(direction, map_width, map_height, rng)

        # Find nearest town road tile by Manhattan distance
        best_dist = map_width + map_height
        best_x, best_y = map_width // 2, map_height // 2
        for sy in range(map_height):
            for sx in range(map_width):
                if not local_map.in_bounds(sx, sy):
                    continue
                t = local_map.tiles[sx, sy]["terrain"]
                if isinstance(t, bytes):
                    t = t.decode()
                t = str(t)
                if t in _TOWN_ROAD_TILES:
                    d = abs(sx - ex) + abs(sy - ey)
                    if d < best_dist:
                        best_dist = d
                        best_x, best_y = sx, sy

        # Walk from entry to nearest town road, placing road_0 tiles
        path = _walk_tiles(ex, ey, best_x, best_y)
        for (px, py) in path:
            if not local_map.in_bounds(px, py):
                continue
            t = local_map.tiles[px, py]["terrain"]
            if isinstance(t, bytes):
                t = t.decode()
            t = str(t)
            if t in _TOWN_ROAD_TILES:
                continue  # already a road tile
            if t in _TOWN_ROAD_OVERWRITE:
                local_map.set_tile(px, py, "road_0",
                                   bool(road_td.get("walkable", True)),
                                   bool(road_td.get("transparent", True)))
            # Widen by 1 tile perpendicular (3-wide road appearance)
            _idx = path.index((px, py))
            if _idx < len(path) - 1:
                _nx, _ny = path[_idx + 1]
                _ddx, _ddy = _nx - px, _ny - py
            elif _idx > 0:
                _ppx, _ppy = path[_idx - 1]
                _ddx, _ddy = px - _ppx, py - _ppy
            else:
                _ddx, _ddy = 0, 0
            for ox, oy in ([(0, -1), (0, 1)] if _ddx != 0 else [(-1, 0), (1, 0)]):
                wx, wy = px + ox, py + oy
                if not local_map.in_bounds(wx, wy):
                    continue
                wt = local_map.tiles[wx, wy]["terrain"]
                if isinstance(wt, bytes):
                    wt = wt.decode()
                wt = str(wt)
                if wt in _TOWN_ROAD_OVERWRITE:
                    local_map.set_tile(wx, wy, "road_0",
                                       bool(road_td.get("walkable", True)),
                                       bool(road_td.get("transparent", True)))


def _place_ford_crossings(
    local_map: "LocalMap",
    terrain_data: dict,
    map_width: int,
    map_height: int,
    rng: random.Random,
    road_path_tiles: set[tuple[int, int]],
) -> None:
    """Place a natural-looking ford where road crosses river.

    The ford is mostly water with occasional stone poking through —
    a shallow crossing, not a stone bridge.

    road_path_tiles includes ALL tiles the road intended to cover, including
    those that were skipped during carving because they were river_water.
    """
    river_water_id = "river_water"
    river_bank_id  = "river_bank"
    road_tile_id   = "road_0"
    bank_td = terrain_data.get(river_bank_id, terrain_data.get("floor", {}))
    road_td = terrain_data.get(road_tile_id, terrain_data.get("cobblestone",
                               terrain_data.get("floor", {})))
    if not bank_td:
        return

    # Phase 1: probabilistic ford tiles on the road path itself
    # 70% leave as water, 18% bank (wet stone), 12% road (stone poking through)
    ford_tiles: set[tuple[int, int]] = set()
    for (x, y) in road_path_tiles:
        if not local_map.in_bounds(x, y):
            continue
        cur = str(local_map.tiles[x, y]["terrain"])
        if cur == river_water_id:
            ford_tiles.add((x, y))
            roll = rng.random()
            if roll < 0.70:
                pass  # leave as river_water — ford is mostly water
            elif roll < 0.88:
                local_map.set_tile(x, y, river_bank_id,
                                   bool(bank_td.get("walkable", True)),
                                   bool(bank_td.get("transparent", True)))
            else:
                local_map.set_tile(x, y, road_tile_id,
                                   bool(road_td.get("walkable", True)),
                                   bool(road_td.get("transparent", True)))

    # Phase 2: scatter bank tiles in the 1-tile margin on either side of
    # the road path within the river — irregular shoreline approach.
    for (fx, fy) in ford_tiles:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = fx + dx, fy + dy
            if not (0 <= nx < map_width and 0 <= ny < map_height):
                continue
            if (nx, ny) in road_path_tiles:
                continue  # already handled above
            if str(local_map.tiles[nx, ny]["terrain"]) == river_water_id:
                if rng.random() < 0.30:
                    local_map.set_tile(nx, ny, river_bank_id,
                                       bool(bank_td.get("walkable", True)),
                                       bool(bank_td.get("transparent", True)))


def _edge_to_tile(
    edge: str,
    position: float,
    map_width: int,
    map_height: int,
) -> tuple[int, int]:
    """
    Convert an edge name + 0.0-1.0 position to a tile coordinate.
    """
    if edge == "north":
        return int(position * (map_width - 2)) + 1, 0
    elif edge == "south":
        return int(position * (map_width - 2)) + 1, map_height - 1
    elif edge == "west":
        return 0, int(position * (map_height - 2)) + 1
    elif edge == "east":
        return map_width - 1, int(position * (map_height - 2)) + 1
    return map_width // 2, map_height // 2


def _opposite_edge(edge: str) -> str:
    return {"north": "south", "south": "north",
            "east": "west",   "west": "east"}[edge]


def _river_endpoint(direction: str, w: int, h: int,
                    rng: random.Random) -> tuple[int, int]:
    """Local tile entry/exit point for a river direction. Same pattern as roads."""
    mid_x, mid_y = w // 2, h // 2
    jitter = rng.randint(-2, 2)
    if direction == "N":  return (mid_x + jitter, 0)
    if direction == "S":  return (mid_x + jitter, h - 1)
    if direction == "E":  return (w - 1, mid_y + jitter)
    if direction == "W":  return (0, mid_y + jitter)
    return (mid_x, mid_y)  # centre


def _carve_river_pair(
    local_map: LocalMap,
    terrain_data: dict,
    x0: int, y0: int,
    x1: int, y1: int,
    map_width: int,
    map_height: int,
    rng: random.Random,
) -> None:
    """
    Carve a river corridor from (x0,y0) to (x1,y1).
    Core: 4-6 tiles half-width of river_water. Bank: 2-3 tiles of
    river_bank and river_stones. Uses midpoint displacement for winding.
    """
    rw = terrain_data.get("river_water",  terrain_data.get("shallow_water", terrain_data["floor"]))
    rb = terrain_data.get("river_bank",   terrain_data.get("gravel",        terrain_data["floor"]))
    rs = terrain_data.get("river_stones", terrain_data.get("gravel",        terrain_data["floor"]))

    # Half-width: 4-6 tiles, deterministic from start position
    half_width = 4 + ((x0 * 7 + y0 * 13) % 3)

    # Midpoint displacement for mild winding
    mid_x = (x0 + x1) // 2 + rng.randint(-6, 6)
    mid_y = (y0 + y1) // 2 + rng.randint(-6, 6)
    mid_x = max(2, min(map_width  - 3, mid_x))
    mid_y = max(2, min(map_height - 3, mid_y))

    def _stamp_at(cx: int, cy: int) -> None:
        outer = half_width + 3
        for ox in range(-outer, outer + 1):
            for oy in range(-outer, outer + 1):
                nx, ny = cx + ox, cy + oy
                if not local_map.in_bounds(nx, ny):
                    continue
                dist_sq = ox * ox + oy * oy
                if dist_sq <= half_width * half_width:
                    local_map.set_tile(nx, ny, "river_water",
                                       rw["walkable"], rw["transparent"])
                elif dist_sq <= outer * outer:
                    cur = str(local_map.tiles[nx, ny]["terrain"])
                    if cur == "river_water":
                        continue
                    if (nx * 7 + ny * 13) % 10 < 3:
                        local_map.set_tile(nx, ny, "river_stones",
                                           rs["walkable"], rs["transparent"])
                    else:
                        local_map.set_tile(nx, ny, "river_bank",
                                           rb["walkable"], rb["transparent"])

    # Walk the path: start -> mid -> end
    path = _walk_tiles(x0, y0, mid_x, mid_y) + _walk_tiles(mid_x, mid_y, x1, y1)[1:]
    for px, py in path:
        _stamp_at(px, py)


def _carve_river_network(
    local_map: LocalMap,
    terrain_data: dict,
    connections: list[str],
    w: int, h: int,
    rng: random.Random,
) -> None:
    """
    Carve river terrain for all connection pairs in this chunk.
    Uses same pair model as roads so bends/T-junctions/crossroads are correct.
    """
    pairs = _road_pairs(connections)
    for a, b in pairs:
        p0 = _river_endpoint(a, w, h, rng)
        p1 = _river_endpoint(b, w, h, rng)
        _carve_river_pair(local_map, terrain_data,
                          p0[0], p0[1], p1[0], p1[1],
                          w, h, rng)



def _carve_path_connector(
    local_map: LocalMap,
    terrain_data: dict,
    entry_edge: str,
    position: float,
    map_width: int,
    map_height: int,
    rng: random.Random,
) -> None:
    """
    Carve a dirt path from entry edge to opposite edge.
    More meandering than a road, uses floor/grass terrain.
    """
    floor = terrain_data.get("varied_grass", terrain_data["floor"])
    start_x, start_y = _edge_to_tile(
        entry_edge, position, map_width, map_height
    )
    exit_edge = _opposite_edge(entry_edge)
    end_x, end_y = _edge_to_tile(
        exit_edge, position + rng.uniform(-0.15, 0.15),
        map_width, map_height,
    )
    end_x = max(1, min(map_width  - 2, end_x))
    end_y = max(1, min(map_height - 2, end_y))

    x, y = start_x, start_y
    while (x, y) != (end_x, end_y):
        if local_map.in_bounds(x, y):
            local_map.set_tile(
                x, y, "varied_grass",
                floor["walkable"],
                floor["transparent"],
            )

        dx = 0 if end_x == x else (1 if end_x > x else -1)
        dy = 0 if end_y == y else (1 if end_y > y else -1)

        if dx != 0 and dy != 0:
            if rng.random() < 0.6:
                dx = 0
            else:
                dy = 0

        if rng.random() < 0.3:
            if entry_edge in ("north", "south"):
                dx = rng.choice([-1, 0, 1])
            else:
                dy = rng.choice([-1, 0, 1])

        new_x = x + dx
        new_y = y + dy
        if not local_map.in_bounds(new_x, new_y):
            break
        x, y = new_x, new_y