"""Exact-instance ownership changes on the game's single event thread.

Inventory, floor/legacy entities and containers own items. Equipment/light are
references into inventory. Preflight failures leave owners and derived state alone.
Take-all is a sequence of individual transfers: rejected items stay at source.
"""
from __future__ import annotations


def detach_equipment(engine, item):
    from engine.item_system import _recompute_effective_av
    equipment = engine.player.equipment
    for slot, occupant in equipment.slots.items():
        if occupant is item:
            equipment.unequip(slot)
    item.equipped = False
    light = engine.player.light_source
    if light is not None and getattr(light, '_item_ref', None) is item:
        light.active = False
        engine.player.light_source = None
        engine._update_fov()
    _recompute_effective_av(engine.player, engine.data)


def consume(engine, item):
    if not engine.player.inventory.remove(item):
        return False
    detach_equipment(engine, item)
    return True


def consume_throw_unit(engine, item):
    """Throw one owned unit, retaining any historical stack and its identity."""
    if (not engine.player.inventory.contains(item)
            or type(item.count) is not int or item.count < 1):
        return False
    if item.count > 1:
        item.count -= 1
        return True
    return consume(engine, item)


def exchange(engine, consumed, outputs=()):
    """Commit a checked recipe/replacement as one inventory list update."""
    inv = engine.player.inventory
    consumed, outputs = list(consumed), list(outputs)
    if (len({id(i) for i in consumed}) != len(consumed)
            or any(not inv.contains(i) for i in consumed)
            or len({id(i) for i in outputs}) != len(outputs)
            or any(i is None or inv.contains(i) for i in outputs)):
        return False
    remaining = [i for i in inv.items if not any(i is old for old in consumed)]
    weight = inv.weight_for(remaining + outputs)
    # Removal alone must remain possible even when already overburdened.
    if outputs and weight > inv.capacity:
        return False
    inv.items[:] = remaining + outputs
    for item in consumed:
        detach_equipment(engine, item)
    return True


def drop(engine, item):
    from generation.floor_object_utils import place_floor_object
    inv = engine.player.inventory
    if not inv.contains(item):
        return False
    if not place_floor_object(engine.local_map, engine.player.x, engine.player.y, item):
        return False
    inv.remove(item)
    detach_equipment(engine, item)
    return True


def take_floor(engine, item):
    from generation.floor_object_utils import remove_floor_object
    inv = engine.player.inventory
    if getattr(item, 'source_creature', None) or not inv.can_add(item):
        return False
    positions = [pos for pos, rows in engine.local_map.floor_objects.items()
                 for row in rows if row is item]
    legacy = sum(row is item for row in engine.entities)
    if len(positions) + legacy != 1:
        return False  # stale selection or ambiguous source; never mint a copy
    inv.add(item)
    if positions:
        remove_floor_object(engine.local_map, *positions[0], item)
    else:
        engine.entities.remove(item)
    item.x, item.y = engine.player.x, engine.player.y
    item.equipped = False
    return True


def take_container(engine, x, y, item):
    from generation.floor_object_utils import take_from_container
    inv = engine.player.inventory
    entry = engine.local_map.container_state.get((x, y))
    if (not entry or entry.get('state') != 'open' or not inv.can_add(item)
            or sum(i is item for i in entry['items']) != 1):
        return False
    # Source and capacity are now validated; neither operation yields control.
    take_from_container(engine.local_map, x, y, item)
    inv.add(item)
    item.x, item.y = engine.player.x, engine.player.y
    item.equipped = False
    return True
