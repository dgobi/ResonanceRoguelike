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


def place_floor_object(local_map: "LocalMap", lx: int, ly: int, item: "Item") -> bool:
    """Add item to floor_objects at (lx, ly). Creates list if absent."""
    if not local_map.in_bounds(lx, ly) or any(
            existing is item for rows in local_map.floor_objects.values() for existing in rows):
        return False
    key = (lx, ly)
    if key not in local_map.floor_objects:
        local_map.floor_objects[key] = []
    local_map.floor_objects[key].append(item)
    item.x, item.y = lx, ly
    return True


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


# ------------------------------------------------------------------ #
#  Container API
# ------------------------------------------------------------------ #

def empty_crate_owner(local_map: "LocalMap", lx: int, ly: int):
    """Only matching, genuinely empty live crates support dismantling."""
    entry = local_map.container_state.get((lx, ly))
    if (local_map.decor.get((lx, ly)) == "crate"
            and isinstance(entry, dict) and entry.get("decor_id") == "crate"
            and entry.get("state") in ("closed", "open", "looted")
            and isinstance(entry.get("items"), list) and not entry["items"]):
        return entry
    return None


def dismantle_empty_crate(local_map: "LocalMap", lx: int, ly: int,
                          owner: dict, wood: "Item") -> bool:
    """Place one output before removing its exact empty source; roll back failure."""
    from entities.item import Item
    from generation.decor_utils import clear_decor
    if (not isinstance(owner, dict) or empty_crate_owner(local_map, lx, ly) is not owner
            or not isinstance(wood, Item) or wood.item_id != "wood_bundle"
            or any(i is wood for rows in local_map.floor_objects.values() for i in rows)):
        return False
    try:
        placed = place_floor_object(local_map, lx, ly, wood)
    except Exception:
        placed = False
    if not placed:
        # Also handle a placement failure after a partial write.
        remove_floor_object(local_map, lx, ly, wood)
        return False
    clear_decor(local_map, lx, ly)
    del local_map.container_state[(lx, ly)]
    return True


def place_container(
    local_map: "LocalMap",
    lx: int,
    ly: int,
    decor_id: str,
    item_list: list,
) -> None:
    """Place a closed container with items at (lx, ly)."""
    from generation.decor_utils import place_decor
    if not local_map.in_bounds(lx, ly):
        return
    if len({id(it) for it in item_list}) != len(item_list):
        raise ValueError("Duplicate container item instance")
    local_map.container_state[(lx, ly)] = {
        "state": "closed",
        "items": list(item_list),
        "decor_id": decor_id,
    }
    place_decor(local_map, lx, ly, decor_id)


def open_container(local_map: "LocalMap", lx: int, ly: int) -> bool:
    """Transition container from closed to open. Returns True if opened.
    Visual does not change — container state is tracked in container_state."""
    entry = local_map.container_state.get((lx, ly))
    if not entry or entry["state"] != "closed":
        return False
    entry["state"] = "open"
    return True


def take_from_container(local_map: "LocalMap", lx: int, ly: int, item) -> bool:
    """Remove the exact live item from an open container."""
    entry = local_map.container_state.get((lx, ly))
    if not entry or entry.get("state") != "open":
        return False
    for i, owned in enumerate(entry["items"]):
        if owned is item:
            entry["items"].pop(i)
            if not entry["items"]:
                entry["state"] = "looted"
            return True
    return False


def get_container_items(local_map: "LocalMap", lx: int, ly: int, item_factory) -> list:
    """Return current items in an open container as Item objects."""
    entry = local_map.container_state.get((lx, ly))
    if not entry or entry["state"] not in ("open", "closed"):
        return []
    # Old B1/B2/B3 maps contain definition rows. Resolve them once, atomically,
    # then retain live instances like floor_objects (the map is pickled).
    from engine.save_components import validate_item, restore_item
    results = []
    for d in entry["items"]:
        if isinstance(d, dict):
            validate_item(d, "container item")
            item = item_factory.create(d.get("item_id", ""))
            if item is None:
                raise ValueError("Unknown container item definition")
            restore_item(item, d)
            item.x, item.y = lx, ly
            results.append(item)
        else:
            results.append(d)
    entry["items"] = results
    return list(results)  # UI snapshots never own the list or recreate its items
