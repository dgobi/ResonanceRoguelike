"""Owned light configuration. Visual radius never supplies mechanical reach.

Construction / JSON load / cache load capture old live-definition reach once.
Queries neither migrate objects nor consume them. Null/zero historical fuel uses
the existing 600-phase clock; exhaustion leaves inspection free and harmless.
"""
from __future__ import annotations
import math

MAX_RADIUS = 40
MAX_FUEL = 10000


def legacy_radius(definition):
    value = definition.get('light_radius', 0)
    return value if type(value) is int and 0 < value <= MAX_RADIUS else 0


def validate(config, owner):
    get = owner.get if isinstance(owner, dict) else lambda k, default=None: getattr(owner, k, default)
    if (not isinstance(config, dict) or set(config) != {'version', 'radius'}
            or type(config['version']) is not int or config['version'] != 1
            or type(config['radius']) is not int or not 0 <= config['radius'] <= MAX_RADIUS
            or get('on_use') != 'equip_light' or get('stackable', False) is not False
            or not isinstance(get('light_data'), dict)):
        raise ValueError('held_light: invalid effective owned light configuration')
    visual=get('light_data')
    if 'color' in visual:
        color=visual['color']
        if (not isinstance(color,(list,tuple)) or len(color)!=3
                or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=255 for v in color)):
            raise ValueError('held_light: color must contain three finite RGB channels')


def capture(item, definition):
    if hasattr(item, 'held_light'):
        validate(item.held_light, item)
    elif (item.on_use == 'equip_light' and item.stackable is False
            and isinstance(item.light_data, dict)):
        item.held_light = dict(version=1, radius=legacy_radius(definition))
        validate(item.held_light, item)


def fuel_limit(item):
    return item.burn_turns or 600


def unspent(item):
    return (type(item.turns_lit) is int and item.turns_lit >= 0
            and type(fuel_limit(item)) is int and item.turns_lit < fuel_limit(item))


def active_item(player):
    """Exact physical owner; also used for fuel and heat, independently of radius."""
    light = getattr(player, 'light_source', None)
    item = getattr(light, '_item_ref', None)
    equipment = getattr(player, 'equipment', None)
    inventory = getattr(player, 'inventory', None)
    if (not light or not light.active or item is None or equipment is None
            or inventory is None or equipment.slots.get('offhand') is not item
            or not inventory.contains(item) or not unspent(item)):
        return None
    try:
        validate(getattr(item, 'held_light', None), item)
    except ValueError:
        return None
    return item


def map_items(local_map):
    for rows in local_map.floor_objects.values():
        yield from rows
    for owner in local_map.container_state.values():
        yield from owner.get('items', [])


def prepare_map(local_map, data=None):
    """Validate every relevant cached owner before installation; preserve opaque old rows."""
    for item in map_items(local_map):
        if isinstance(item, dict):
            if 'held_light' in item:
                validate(item['held_light'], item)
            continue
        from entities.item import Item
        if not isinstance(item, Item):
            continue  # unrelated historical opaque container payload
        if hasattr(item, 'held_light'):
            from engine.save_components import serialize_item, validate_item
            validate_item(serialize_item(item), 'cached held light')
        elif data is not None:
            capture(item, data.items.get(item.item_id, {}))
