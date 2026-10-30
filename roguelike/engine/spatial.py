"""Physical attack geometry, independent of player visibility and AI awareness."""
from __future__ import annotations


def melee_contact(local_map, x1, y1, x2, y2):
    """Distinct walkable neighbors; a diagonal needs one open orthogonal side."""
    dx, dy = x2 - x1, y2 - y1
    if (max(abs(dx), abs(dy)) != 1
            or not local_map.in_bounds(x1, y1) or not local_map.in_bounds(x2, y2)):
        return False
    if not local_map.walkable[x1, y1] or not local_map.walkable[x2, y2]:
        return False
    return (not dx or not dy or bool(local_map.walkable[x2, y1])
            or bool(local_map.walkable[x1, y2]))


def combat_ready(attacker, target):
    """Existing living-fighter/impairment eligibility, before any contact effects."""
    af = getattr(attacker, "fighter", None)
    tf = getattr(target, "fighter", None)
    return bool(attacker is not target and af and tf
                and getattr(attacker, "is_alive", False)
                and getattr(target, "is_alive", False)
                and af.hp > 0 and tf.hp > 0 and not af.is_dead and not tf.is_dead
                and af.can_attack())


def melee_attack_legal(local_map, attacker, target):
    return (combat_ready(attacker, target)
            and melee_contact(local_map, attacker.x, attacker.y, target.x, target.y))


def terrain_line(local_map, x1, y1, x2, y2):
    """Crow line: walkable endpoints, transparent Bresenham interior, no sealed corner.

    For each diagonal ray step at least one orthogonal side must be transparent.
    Actors do not occlude this existing route. Rendering and FOV are irrelevant.
    Throwing retains its stricter walkable-segment policy at its own call site.
    """
    if ((x1, y1) == (x2, y2) or not local_map.in_bounds(x1, y1)
            or not local_map.in_bounds(x2, y2)
            or not local_map.walkable[x1, y1] or not local_map.walkable[x2, y2]):
        return False
    from tcod.los import bresenham
    ray = bresenham((x1, y1), (x2, y2)).tolist()
    if any(not local_map.transparent[x, y] for x, y in ray[1:-1]):
        return False
    for (ax, ay), (bx, by) in zip(ray, ray[1:]):
        if (ax != bx and ay != by
                and not local_map.transparent[bx, ay]
                and not local_map.transparent[ax, by]):
            return False
    return True


def terrain_conceals(actor, local_map, terrain_defs):
    """Derived cover fact; never replays entry effects or mutates saved state."""
    if not local_map.in_bounds(actor.x, actor.y):
        return False
    terrain = str(local_map.tiles["terrain"][actor.x, actor.y])
    return terrain_defs.get(terrain, {}).get("secondary_effect") == "concealment"
