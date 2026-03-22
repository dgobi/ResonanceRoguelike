# generation/layout_stamper.py
"""
Stamps a JSON entrance layout onto a LocalMap.

All layouts are authored facing north (connection_point on the north edge).
stamp_layout() rotates the grid so the layout aligns with any edge.

Rotation convention (each step = 90° CW):
  north = 0   east = 1   south = 2   west = 3
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.local_map import LocalMap


def _set_tile(
    local_map: "LocalMap",
    x: int,
    y: int,
    terrain: str,
    terrain_data: dict,
) -> None:
    if not local_map.in_bounds(x, y):
        return
    # Derive walkable/transparent from terrain.json.
    # Any new terrain added there automatically gets correct behaviour here.
    td          = terrain_data.get(terrain, terrain_data.get("floor", {}))
    walkable    = bool(td.get("walkable",    True))
    transparent = bool(td.get("transparent", True))
    local_map.set_tile(x, y, terrain, walkable, transparent)
    # Explicit numpy overrides — set_tile stores in the structured array but
    # tcod FOV reads the separate .walkable / .transparent array views.
    local_map.walkable[x, y]    = walkable
    local_map.transparent[x, y] = transparent


def _rotate_grid_cw(layers: list[str]) -> list[str]:
    """Rotate the layer grid 90° clockwise.

    Original: H rows × W cols  →  Rotated: W rows × H cols
    rotated[new_y][new_x] = original[(H-1) - new_x][new_y]
    """
    H = len(layers)
    W = max(len(r) for r in layers)
    padded = [r.ljust(W) for r in layers]
    new_H = W
    return [
        ''.join(padded[(H - 1) - new_x][new_y] for new_x in range(H))
        for new_y in range(new_H)
    ]


def _rotate_point_cw(x: int, y: int, H: int) -> tuple[int, int]:
    """Rotate point (x, y) 90° CW in a grid of height H."""
    return (H - 1) - y, x


def stamp_layout(
    local_map: "LocalMap",
    layout: dict,
    edge: str,
    connector_pos: float,
    terrain_data: dict,
) -> tuple[int, int]:
    """
    Stamp layout onto local_map, rotating to match edge.
    Returns (spawn_x, spawn_y) in map coordinates.
    """
    layers = list(layout["layers"])
    legend = layout["legend"]
    cp = dict(layout["connection_point"])   # {"x": ..., "y": ...}
    so = dict(layout["spawn_offset"])       # {"x": ..., "y": ...}

    # Rotate grid and anchor points to match the actual edge.
    # Each rotation is 90° CW.
    n_rot = {"north": 0, "east": 1, "south": 2, "west": 3}.get(edge, 0)
    for _ in range(n_rot):
        H = len(layers)
        new_cpx, new_cpy = _rotate_point_cw(cp["x"], cp["y"], H)
        new_sox, new_soy = _rotate_point_cw(so["x"], so["y"], H)
        cp = {"x": new_cpx, "y": new_cpy}
        so = {"x": new_sox, "y": new_soy}
        layers = _rotate_grid_cw(layers)

    # Find the edge connector tile in map coordinates.
    map_w = local_map.width
    map_h = local_map.height
    if edge == "north":
        edge_x = int(connector_pos * (map_w - 2)) + 1
        edge_y = 0
    elif edge == "south":
        edge_x = int(connector_pos * (map_w - 2)) + 1
        edge_y = map_h - 1
    elif edge == "west":
        edge_x = 0
        edge_y = int(connector_pos * (map_h - 2)) + 1
    else:  # east
        edge_x = map_w - 1
        edge_y = int(connector_pos * (map_h - 2)) + 1

    # Layout origin so that connection_point lands at the edge connector.
    origin_x = edge_x - cp["x"]
    origin_y = edge_y - cp["y"]

    # Stamp each tile.
    for ly, row in enumerate(layers):
        for lx, char in enumerate(row):
            if char == " ":
                continue
            terrain = legend.get(char)
            if terrain is None:
                continue
            _set_tile(local_map, origin_x + lx, origin_y + ly,
                      terrain, terrain_data)

    return origin_x + so["x"], origin_y + so["y"]


def stamp_layout_interior(
    local_map: "LocalMap",
    layout: dict,
    centre_x: int,
    centre_y: int,
    terrain_data: dict,
) -> tuple[int, int]:
    """
    Stamp a layout centered at (centre_x, centre_y) with no edge alignment
    and no rotation.  Returns (stairs_x, stairs_y) if a stairs_down tile is
    found in the layout, otherwise returns (centre_x, centre_y).
    """
    layers = layout["layers"]
    legend = layout["legend"]
    h = len(layers)
    w = max(len(row) for row in layers)

    origin_x = centre_x - w // 2
    origin_y = centre_y - h // 2

    stairs_pos: tuple[int, int] | None = None

    for row_idx, row in enumerate(layers):
        for col_idx, ch in enumerate(row):
            terrain = legend.get(ch)
            if terrain is None:
                continue
            tx = origin_x + col_idx
            ty = origin_y + row_idx
            if not local_map.in_bounds(tx, ty):
                continue
            _set_tile(local_map, tx, ty, terrain, terrain_data)
            if terrain == "stairs_down":
                stairs_pos = (tx, ty)

    return stairs_pos if stairs_pos else (centre_x, centre_y)


def get_layout_spawn(
    layout: dict,
    edge: str,
    connector_pos: float,
    map_w: int,
    map_h: int,
) -> tuple[int, int]:
    """
    Return the spawn point for a layout without stamping any tiles.
    Mirrors the rotation + placement logic in stamp_layout.
    """
    layers = list(layout["layers"])
    cp = dict(layout["connection_point"])
    so = dict(layout["spawn_offset"])

    n_rot = {"north": 0, "east": 1, "south": 2, "west": 3}.get(edge, 0)
    for _ in range(n_rot):
        H = len(layers)
        new_cpx, new_cpy = _rotate_point_cw(cp["x"], cp["y"], H)
        new_sox, new_soy = _rotate_point_cw(so["x"], so["y"], H)
        cp = {"x": new_cpx, "y": new_cpy}
        so = {"x": new_sox, "y": new_soy}
        layers = _rotate_grid_cw(layers)

    if edge == "north":
        edge_x = int(connector_pos * (map_w - 2)) + 1
        edge_y = 0
    elif edge == "south":
        edge_x = int(connector_pos * (map_w - 2)) + 1
        edge_y = map_h - 1
    elif edge == "west":
        edge_x = 0
        edge_y = int(connector_pos * (map_h - 2)) + 1
    else:  # east
        edge_x = map_w - 1
        edge_y = int(connector_pos * (map_h - 2)) + 1

    origin_x = edge_x - cp["x"]
    origin_y = edge_y - cp["y"]
    return origin_x + so["x"], origin_y + so["y"]
