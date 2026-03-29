# generation/floor_object_utils.py
"""
Placement API for the floor objects layer.

All writes to local_map.floor_objects must go through these functions.
Floor objects are items sitting on the ground — dropped items, butchery yield,
processing completions, notes, documents. Multiple items per tile.
Never write to local_map.floor_objects directly outside this module.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.local_map import LocalMap
    from entities.item import Item


def place_floor_object(local_map: "LocalMap", lx: int, ly: int, item: "Item") -> None:
    """Add item to floor_objects at (lx, ly). Creates list if absent."""
    if not local_map.in_bounds(lx, ly):
        return
    key = (lx, ly)
    if key not in local_map.floor_objects:
        local_map.floor_objects[key] = []
    local_map.floor_objects[key].append(item)


def remove_floor_object(local_map: "LocalMap", lx: int, ly: int, item: "Item") -> None:
    """Remove specific item from floor_objects at (lx, ly)."""
    key = (lx, ly)
    if key in local_map.floor_objects:
        local_map.floor_objects[key] = [i for i in local_map.floor_objects[key] if i is not item]
        if not local_map.floor_objects[key]:
            del local_map.floor_objects[key]


def get_floor_objects(local_map: "LocalMap", lx: int, ly: int) -> list:
    """Return list of items at (lx, ly), empty list if none."""
    return local_map.floor_objects.get((lx, ly), [])


def clear_floor_objects(local_map: "LocalMap", lx: int, ly: int) -> None:
    """Remove all items at (lx, ly)."""
    local_map.floor_objects.pop((lx, ly), None)
