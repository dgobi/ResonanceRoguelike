"""Consume explicit road/river mouths while keeping wandering inside a chunk."""
from __future__ import annotations
from generation.ports import OFFSETS, mouth, resolve_mouth


def carve_feature(local_map, terrain_data, ports, kind, rng):
    from generation.local_gen import _local_road_walk, _walk_tiles
    w, h = local_map.width, local_map.height
    guard = min(9 if kind == 'river' else 3, (min(w, h) - 3) // 2)
    strips = {edge: set() for edge in OFFSETS}
    bank_strips = {edge: set() for edge in OFFSETS}
    for edge, connector in ports:
        _, width, _ = resolve_mouth(edge, connector.position, connector.width, w, h, kind)
        for depth in range(guard):
            strips[edge].update(mouth(edge, connector.position, width, w, h, depth))
            bank_strips[edge].update(mouth(edge, connector.position, width, w, h, depth, bank=3))

    def allowed(x, y, banks=False):
        if not local_map.in_bounds(x, y): return False
        checks = {'north': y, 'south': h - 1 - y, 'west': x, 'east': w - 1 - x}
        masks = bank_strips if banks else strips
        # Only a declared mouth may touch a boundary. The full straight approach
        # below joins it inward, including near-corner ports whose banks lie
        # close to an unrelated edge.
        return all(depth != 0 or (x, y) in masks[edge] for edge, depth in checks.items())

    core, banks = set(), set()
    hub = w // 2, h // 2
    for edge, connector in ports:
        _, width, center = resolve_mouth(edge, connector.position, connector.width, w, h, kind)
        half = width // 2
        depth = min(guard + half + 1, min(w, h) // 2 - 1)
        inward = {'north': (center, depth), 'south': (center, h - 1 - depth),
                  'west': (depth, center), 'east': (w - 1 - depth, center)}[edge]
        # Straight approach: no independent boundary jitter, and width is exact.
        for d in range(depth + 1):
            core.update(p for p in mouth(edge, connector.position, width, w, h, d) if allowed(*p))
            if kind == 'river':
                banks.update(p for p in mouth(edge, connector.position, width, w, h, d, bank=3) if allowed(*p, True))
        path = _local_road_walk(*inward, *hub, w, h, rng)
        for i, (x, y) in enumerate(path):
            if kind == 'river':
                for dx in range(-half - 3, half + 4):
                    for dy in range(-half - 3, half + 4):
                        if dx * dx + dy * dy <= half * half and allowed(x + dx, y + dy):
                            core.add((x + dx, y + dy))
                        elif dx * dx + dy * dy <= (half + 3) ** 2 and allowed(x + dx, y + dy, True):
                            banks.add((x + dx, y + dy))
            else:
                next_xy = path[min(i + 1, len(path) - 1)]
                horizontal = next_xy[0] != x
                for offset in range(-half, width - half):
                    xy = (x, y + offset) if horizontal else (x + offset, y)
                    if allowed(*xy): core.add(xy)
                if allowed(x, y): core.add((x, y))
    def paint(xy, terrain):
        td = terrain_data[terrain]
        local_map.set_tile(*xy, terrain, td.get('walkable', True), td.get('transparent', True))
    for xy in sorted(banks - core):
        if str(local_map.tiles[xy]['terrain']) != 'river_water':
            paint(xy, 'river_stones' if (xy[0] * 7 + xy[1] * 13) % 10 < 3 else 'river_bank')
    for xy in sorted(core):
        if kind == 'river' or str(local_map.tiles[xy]['terrain']) != 'river_water':
            paint(xy, 'river_water' if kind == 'river' else 'road_0')
    setattr(local_map, kind + '_cells', core)
    local_map.protected_cells = getattr(local_map, 'protected_cells', set()) | core | banks
    return core


def reserve_town_routes(local_map, chunk, terrain_data, street_tiles, context):
    """Connect every shared mouth to a real reserved street before packing buildings."""
    from generation.ports import town_ports
    from generation.local_gen import _walk_tiles
    from world.world_map import ConnectorType
    w, h = local_map.width, local_map.height
    ports = town_ports(context.world_seed, chunk.town_id, chunk.town_role, w, h)
    for edge, connectors in chunk.edges.items():
        for connector in connectors:
            if connector.connector_type == ConnectorType.ROAD:
                _, width, _ = resolve_mouth(edge, connector.position, connector.width, w, h)
                ports[edge].append((connector.position, width))
    corner = chunk.town_role in ('NW', 'NE', 'SW', 'SE')
    terrain = 'dirt_path' if corner else 'cobblestone'
    td = terrain_data[terrain]
    if not street_tiles:
        street_tiles.add((w // 2, h // 2))
    targets = sorted(p for p in street_tiles if 4 <= p[0] < w - 4 and 4 <= p[1] < h - 4)
    if not targets: targets = [(w // 2, h // 2)]
    for edge, bands in ports.items():
        for position, width in sorted(set(bands)):
            approach = [p for depth in range(5) for p in mouth(edge, position, width, w, h, depth)]
            for p in approach: street_tiles.add(p)
            start = list(mouth(edge, position, width, w, h, 4))[width // 2]
            target = min(targets, key=lambda p: (abs(p[0] - start[0]) + abs(p[1] - start[1]), p))
            path = _walk_tiles(*start, *target)
            for x, y in path:
                for dx in range(-(width // 2), width - width // 2):
                    # Interior widening cannot invent a new boundary mouth.
                    p = x + dx, y
                    if 0 < p[0] < w - 1 and 0 < p[1] < h - 1: street_tiles.add(p)
    for x, y in sorted(street_tiles):
        if local_map.in_bounds(x, y):
            local_map.set_tile(x, y, terrain, td['walkable'], td['transparent'])
    local_map.street_cells = street_tiles
    local_map.road_cells = set(street_tiles)
    local_map.protected_cells = getattr(local_map, 'protected_cells', set()) | street_tiles
