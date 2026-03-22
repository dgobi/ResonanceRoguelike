# generation/local_gen.py
from __future__ import annotations
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
) -> None:
    """
    Punch n_per_edge openings into each map edge and carve a short
    corridor inward so the player can reach them from the interior.
    Called after any local map generation.
    """
    t = terrain_data["floor"]
    w = local_map.width
    h = local_map.height

    def carve(x: int, y: int) -> None:
        if local_map.in_bounds(x, y):
            local_map.set_tile(x, y, "floor",
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

def carve_connectors(
    local_map: LocalMap,
    terrain_data: dict,
    edges: dict,
    map_width: int,
    map_height: int,
    rng: random.Random,
) -> None:
    """
    Read edge connectors from a chunk and carve their features
    into the local map. Called after base terrain generation.
    """
    from world.world_map import ConnectorType

    for edge, connectors in edges.items():
        for connector in connectors:
            if connector.connector_type == ConnectorType.RIVER:
                _carve_river_connector(
                    local_map, terrain_data,
                    edge, connector.position,
                    map_width, map_height, rng,
                )
            elif connector.connector_type == ConnectorType.ROAD:
                _carve_road_connector(
                    local_map, terrain_data,
                    edge, connector.position,
                    map_width, map_height, rng,
                )
            elif connector.connector_type == ConnectorType.PATH:
                _carve_path_connector(
                    local_map, terrain_data,
                    edge, connector.position,
                    map_width, map_height, rng,
                )


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


def _carve_river_connector(
    local_map: LocalMap,
    terrain_data: dict,
    entry_edge: str,
    position: float,
    map_width: int,
    map_height: int,
    rng: random.Random,
) -> None:
    """
    Carve a river from the entry edge toward the opposite edge or
    a natural interior terminus (a pool). Rivers are 2-3 tiles wide
    and meander slightly.
    """
    water = terrain_data.get("water", terrain_data["floor"])
    start_x, start_y = _edge_to_tile(
        entry_edge, position, map_width, map_height
    )
    exit_edge = _opposite_edge(entry_edge)
    end_x, end_y = _edge_to_tile(
        exit_edge, position + rng.uniform(-0.1, 0.1),
        map_width, map_height,
    )
    end_x = max(1, min(map_width  - 2, end_x))
    end_y = max(1, min(map_height - 2, end_y))

    # Carve a meandering path
    x, y = start_x, start_y
    while (x, y) != (end_x, end_y):
        # Carve a 2-wide river
        for ox in range(-1, 2):
            for oy in range(-1, 2):
                nx, ny = x + ox, y + oy
                if local_map.in_bounds(nx, ny):
                    local_map.set_tile(
                        nx, ny, "water",
                        water["walkable"],
                        water["transparent"],
                    )

        # Step toward exit with slight drift
        dx = 0 if end_x == x else (1 if end_x > x else -1)
        dy = 0 if end_y == y else (1 if end_y > y else -1)

        if dx != 0 and dy != 0:
            if rng.random() < 0.5:
                dx = 0
            else:
                dy = 0

        if rng.random() < 0.2:
            drift_choices = []
            if entry_edge in ("north", "south"):
                drift_choices = [(-1, 0), (1, 0)]
            else:
                drift_choices = [(0, -1), (0, 1)]
            if drift_choices:
                dx, dy = rng.choice(drift_choices)

        new_x = x + dx
        new_y = y + dy
        if not local_map.in_bounds(new_x, new_y):
            break
        x, y = new_x, new_y

def _carve_road_connector(
    local_map: LocalMap,
    terrain_data: dict,
    entry_edge: str,
    position: float,
    map_width: int,
    map_height: int,
    rng: random.Random,
) -> None:
    """
    Carve a road from the entry edge to the opposite edge.
    Roads are 1 tile wide, cobblestone, mostly straight.
    """
    cobble = terrain_data.get("cobblestone", terrain_data["floor"])
    start_x, start_y = _edge_to_tile(
        entry_edge, position, map_width, map_height
    )
    exit_edge = _opposite_edge(entry_edge)
    end_x, end_y = _edge_to_tile(
        exit_edge, position, map_width, map_height
    )

    x, y = start_x, start_y
    while (x, y) != (end_x, end_y):
        if local_map.in_bounds(x, y):
            local_map.set_tile(
                x, y, "cobblestone",
                cobble["walkable"],
                cobble["transparent"],
            )

        dx = 0 if end_x == x else (1 if end_x > x else -1)
        dy = 0 if end_y == y else (1 if end_y > y else -1)

        if dx != 0 and dy != 0:
            if rng.random() < 0.5:
                dx = 0
            else:
                dy = 0

        new_x = x + dx
        new_y = y + dy
        if not local_map.in_bounds(new_x, new_y):
            break
        x, y = new_x, new_y


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
    floor = terrain_data.get("grass", terrain_data["floor"])
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
                x, y, "grass",
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