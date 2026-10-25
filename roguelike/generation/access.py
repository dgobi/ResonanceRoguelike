"""Player static access: eight-way movement, openable doors, blocking decor.

Actors are dynamic occupants. Interaction reach is deliberately a separate rule.
"""
from collections import deque
from generation.context import GenerationError


def enterable(local_map, xy, data=None):
    decor = getattr(data, 'decoratives', {})
    return (local_map.in_bounds(*xy)
            and (local_map.walkable[xy] or str(local_map.tiles[xy]['terrain']) == 'door_closed')
            and not decor.get(local_map.decor.get(xy), {}).get('blocks_movement', False))


def reachable(local_map, start, data=None):
    seen = {tuple(start)} if enterable(local_map, tuple(start), data) else set()
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                xy = x + dx, y + dy
                if xy not in seen and enterable(local_map, xy, data):
                    seen.add(xy)
                    queue.append(xy)
    return seen


def arrival_anchor(local_map, spawn, data=None):
    """Resolve the generated arrival before adding stairs; never choose a new stair."""
    candidates = [(x, y) for x in range(local_map.width) for y in range(local_map.height)
                  if enterable(local_map, (x, y), data)]
    if not candidates:
        raise GenerationError('surface: no enterable arrival component')
    return min(candidates, key=lambda p: (max(abs(p[0]-spawn[0]), abs(p[1]-spawn[1])), p))


def required_anchors(local_map, data=None):
    anchors = getattr(local_map, 'required_access_anchors', None)
    if anchors is not None:
        if not anchors:
            raise GenerationError('surface: required access anchors are empty')
        return list(anchors)
    # Standalone placement API: an exterior arrival, never the selected stair.
    for x in range(local_map.width):
        for y in range(local_map.height):
            if (x in (0, local_map.width-1) or y in (0, local_map.height-1)) and enterable(local_map, (x, y), data):
                return [(x, y)]
    raise GenerationError('surface: supply a meaningful required_access_anchors entry')


def validate_required_access(local_map, targets, data=None):
    anchors = required_anchors(local_map, data)
    contract = getattr(local_map, 'wilderness_access', None)
    provenance = getattr(local_map, 'surface_provenance', {}) or {}
    corrected = provenance.get('access_revision') == 1 and provenance.get('owner') == 'wilderness'
    if corrected:
        if not contract or contract.get('revision') != 1:
            raise GenerationError('wilderness access revision 1: missing exterior obligation')
        edge, arrival = tuple(contract['edge']), tuple(contract['arrival'])
        if edge not in anchors or arrival not in anchors or not (
                edge[0] in (0,local_map.width-1) or edge[1] in (0,local_map.height-1)):
            raise GenerationError(f'wilderness {contract["chunk"]} access revision 1: lost arrival/exterior obligation')
    reached = reachable(local_map, anchors[0], data)
    for xy in [*anchors, *targets]:
        if tuple(xy) not in reached:
            if corrected:
                raise GenerationError(f'wilderness {contract["chunk"]} access revision 1: required target {tuple(xy)} '
                                      f'disconnected from arrival {anchors[0]} / reciprocal exterior {contract["edge"]}')
            raise GenerationError(f'surface: required target {tuple(xy)} is unreachable from arrival {anchors[0]}')
    return reached
