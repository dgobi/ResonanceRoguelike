# engine/starting_location.py
"""
Generate the starting underground laboratory.

Stamps data/layouts/starting_lab.json onto a LocalMap, places
special-tile items (lab notes with text_ids, the body of R.),
and returns (local_map, spawn_xy, entities).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from world.local_map import LocalMap

if TYPE_CHECKING:
    from engine.item_factory import ItemFactory


_LAYOUT_PATH = Path("data/layouts/starting_lab.json")


def _load_layout() -> dict:
    with open(_LAYOUT_PATH, encoding="utf-8") as f:
        return json.load(f)


def generate_starting_lab(
    map_w:        int,
    map_h:        int,
    terrain_data: dict,
    item_factory: "ItemFactory",
    data_loader=None,
) -> tuple["LocalMap", tuple[int, int], list]:
    """
    Build the starting underground lab.

    Returns:
        local_map  — fully stamped LocalMap (everything outside layout is wall)
        spawn      — (x, y) player starting position in map coordinates
        entities   — list of Item entities to add to the world
    """
    layout    = _load_layout()
    local_map = LocalMap(map_w, map_h)
    # LocalMap initialises everything as wall — just stamp the layout on top

    rows = layout["layers"]
    lh   = len(rows)
    lw   = max(len(r) for r in rows)

    # Centre the layout on the map
    ox = (map_w - lw) // 2
    oy = (map_h - lh) // 2

    _stamp(local_map, layout, terrain_data, ox, oy)

    # Player spawn (layout-relative → map coordinates)
    ps    = layout["player_start"]
    spawn = (ox + ps["x"], oy + ps["y"])

    # Special tile entities (containers written directly to local_map)
    entities = _build_entities(layout, item_factory, ox, oy,
                               local_map=local_map, data_loader=data_loader)

    return local_map, spawn, entities


# ------------------------------------------------------------------ #
#  Internal helpers
# ------------------------------------------------------------------ #

def _set_tile(
    local_map:    "LocalMap",
    x:            int,
    y:            int,
    terrain:      str,
    terrain_data: dict,
) -> None:
    td          = terrain_data.get(terrain, terrain_data.get("floor", {}))
    walkable    = bool(td.get("walkable",    True))
    transparent = bool(td.get("transparent", True))
    local_map.set_tile(x, y, terrain, walkable, transparent)
    local_map.walkable[x, y]    = walkable
    local_map.transparent[x, y] = transparent


def _stamp(
    local_map:    "LocalMap",
    layout:       dict,
    terrain_data: dict,
    ox:           int,
    oy:           int,
) -> None:
    import random as _random
    legend = layout["legend"]
    legend_weights = layout.get("legend_weights", {})
    rows   = layout["layers"]
    _rng = _random.Random()

    for row_idx, row in enumerate(rows):
        for col_idx, ch in enumerate(row):
            terrain = None
            if legend_weights:
                from generation.layout_stamper import _resolve_legend_weights
                terrain = _resolve_legend_weights(ch, legend_weights, _rng)
            if terrain is None:
                terrain = legend.get(ch)
            if terrain is None:
                continue   # space / null → leave existing tile (wall)
            x = ox + col_idx
            y = oy + row_idx
            if local_map.in_bounds(x, y):
                # Tiles that should be decor, not terrain
                _DECOR_IDS = {"waystone_plinth", "stele", "street_lamp_working",
                              "street_lamp_sputtering", "street_lamp_dead"}
                if terrain in _DECOR_IDS:
                    from generation.decor_utils import place_decor as _pd_lab
                    # Place floor underneath first
                    _set_tile(local_map, x, y, "floor", terrain_data)
                    _pd_lab(local_map, x, y, terrain)
                else:
                    _set_tile(local_map, x, y, terrain, terrain_data)


def _resolve_weighted_special(st: dict, rng) -> dict | None:
    """Resolve a 'type': 'weighted' special tile entry to a concrete entry."""
    table = st.get("spawn_table", [])
    if not table:
        return None
    weights = [e.get("weight", 1) for e in table]
    chosen = rng.choices(table, weights=weights, k=1)[0]
    if chosen.get("type") == "empty":
        return None
    # Build a concrete special tile entry with position from parent
    result = dict(chosen)
    result["x"] = st["x"]
    result["y"] = st["y"]
    return result


def _build_entities(
    layout:       dict,
    item_factory: "ItemFactory",
    ox:           int,
    oy:           int,
    local_map:    "LocalMap | None" = None,
    data_loader=None,
) -> list:
    import random as _random
    from entities.item import Item

    entities: list = []
    _rng = _random.Random()

    for st in layout.get("special_tiles", []):
        # Resolve weighted spawn tables
        if st.get("type") == "weighted":
            st = _resolve_weighted_special(st, _rng)
            if st is None:
                continue
        wx = ox + st["x"]
        wy = oy + st["y"]

        if st["type"] == "item":
            text_id = st.get("text_id", "")
            # text_item_map overrides item_id based on text_id
            item_id = st["item_id"]
            if text_id and data_loader and hasattr(data_loader, "text_item_map"):
                mapped = data_loader.text_item_map.get(text_id)
                if mapped:
                    item_id = mapped
                elif text_id:
                    print(f"[TEXT-MAP] unknown text_id: {text_id}, defaulting to letter")
                    item_id = "letter"
            item = item_factory.create(item_id, wx, wy)
            if item:
                item.text_id = text_id
                entities.append(item)

        elif st["type"] == "body":
            body = Item(
                x       = wx,
                y       = wy,
                tile    = "corpse",
                name    = st.get("name", "a body"),
                item_id = "",
            )
            body.weight = 0.0
            entities.append(body)

        elif st["type"] == "stele" and local_map is not None:
            # Store text_id for stele lookup by engine._find_stele_text_id
            local_map.stele_text_ids[(wx, wy)] = st.get("text_id", "")

        elif st["type"] == "container" and local_map is not None:
            from generation.floor_object_utils import place_container
            from engine.loot_roller import roll_pools
            import random
            loot_pools = data_loader.loot_pools if data_loader else {}
            items = roll_pools(
                st.get("loot_pools", []), loot_pools,
                item_factory, random.Random(),
            )
            if local_map.in_bounds(wx, wy) and local_map.tiles[wx, wy]["walkable"]:
                place_container(local_map, wx, wy, st.get("decor_id", "crate"), items)

    return entities
