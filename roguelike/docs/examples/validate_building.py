"""Read-only smoke check for the documented ordinary town-building format.

Imports the supplied game's actual loader, stampers, and item/loot APIs. Copies
data into a temporary directory, adds the example there, and generates maps in
memory. Does not import main, open a window, read saves, or modify game source.
This intentionally checks the currently working item/container subset; it is not
a production schema validator or a replacement for visual/playability review.
"""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reachable(local_map, data, start=(0, 0)):
    """Use runtime eight-way movement, openable doors and blocking decor."""
    queue = deque([start])
    visited = {start}
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0),
                       (1, 0), (-1, 1), (0, 1), (1, 1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in visited or not local_map.in_bounds(nx, ny):
                continue
            terrain = str(local_map.tiles[nx, ny]["terrain"])
            if not local_map.walkable[nx, ny] and terrain != "door_closed":
                continue
            decor = data.decoratives.get(local_map.decor.get((nx, ny)), {})
            if decor.get("blocks_movement", False):
                continue
            visited.add((nx, ny))
            queue.append((nx, ny))
    return visited


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True, help="Directory containing main.py and data/")
    parser.add_argument("--building", type=Path, default=Path(__file__).with_name("author_cottage_a.json"))
    parser.add_argument("--output", type=Path, help="Optional JSON evidence path outside the game")
    args = parser.parse_args()
    game = args.game.resolve()
    source = args.building.resolve()
    require((game / "main.py").is_file(), "--game must point to the roguelike directory")
    if args.output:
        require(not args.output.resolve().is_relative_to(game), "Evidence output must be outside game source")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(game))
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    import config
    config.DEBUG_MODE = False  # Process-local diagnostic setting, no file edit.
    from engine.data_loader import DataLoader
    from engine.item_factory import ItemFactory
    from engine.loot_roller import roll_pools
    from generation.floor_object_utils import place_container, place_floor_object
    from generation.region_gen import generate_region
    from generation.town_gen import _stamp_building_at
    from world.local_map import LocalMap
    from world.world_map import Chunk, RegionType

    definition = json.loads(source.read_text(encoding="utf-8"))
    category = definition.get("category")
    require(category in ("residential", "storage", "commercial", "civic", "religious", "ruins", "wilderness"),
            "This checker covers ordinary buildings in one of the seven existing categories, not plazas")
    identifier = definition.get("id")
    require(isinstance(identifier, str) and identifier and all(c.isalnum() or c == "_" for c in identifier),
            "Use a nonempty letters/digits/underscore id")
    rows = definition.get("layers")
    require(isinstance(rows, list) and bool(rows) and all(isinstance(r, str) for r in rows),
            "layers must be a nonempty list of strings")
    width, height = len(rows[0]), len(rows)
    require(width > 0 and all(len(r) == width for r in rows), "Make every row equally wide")
    require(definition.get("width", width) == width and definition.get("height", height) == height,
            "Declared width/height must match the grid")
    require(width <= 78 and height <= 41, "Keep the building within an 80 x 43 map with a border")
    legend = definition.get("legend")
    require(isinstance(legend, dict), "legend must be an object")
    require(all(isinstance(k, str) and len(k) == 1 for k in legend), "Legend keys must be single characters")
    require(all(c in legend for row in rows for c in row), "Every used character needs a legend entry")
    require(all(v is None or isinstance(v, str) for v in legend.values()), "Town legend values are terrain ids or null")

    messages = io.StringIO()
    results = []
    original_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="resonance-building-check-") as temporary:
        root = Path(temporary)
        # Only authored data, never a save tree or source checkout, is copied.
        shutil.copytree(game / "data", root / "data")
        installed = root / "data/buildings" / category / (identifier + ".json")
        if installed.exists():
            require(installed.read_bytes() == source.read_bytes(), "This id/filename already exists with different content")
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_bytes(source.read_bytes())
        try:
            os.chdir(root)
            with redirect_stdout(messages):
                data = DataLoader(str(root / "data"))
            require(identifier in data.structures, "The flat loader did not register this id")
            loaded = [b for b in data.buildings.get(category, []) if b.get("id") == identifier]
            require(len(loaded) == 1, "The category loader must contain exactly one instance of the id")
            require(sum(b.get("id") == identifier for category_rows in data.buildings.values() for b in category_rows) == 1,
                    "The id is duplicated in another building category")
            require(all(v is None or v in data.terrain for v in legend.values()), "A legend terrain id is unknown")
            decor = definition.get("decor_layer", [])
            if decor:
                require(len(decor) == height and all(isinstance(r, list) and len(r) == width for r in decor),
                        "decor_layer must be a rectangular list of lists of full ids/null; painter strings are incompatible")
                require(all(v is None or isinstance(v, str) and v in data.decoratives for row in decor for v in row),
                        "A decor id is unknown; use decoratives.json ids")
            for spec in definition.get("special_tiles", []):
                x, y = spec.get("x"), spec.get("y")
                require(type(x) is int and type(y) is int and 0 <= x < width and 0 <= y < height,
                        "Every special tile needs integer x/y inside the layout")
                require(spec.get("type") in ("item", "container"),
                        "This working-subset check accepts item and container specials only; see the guide for other types")
                terrain = legend[rows[y][x]]
                require(terrain in data.terrain and data.terrain[terrain].get("walkable", False),
                        "Place items and containers on explicit walkable floor")
                if spec["type"] == "item":
                    require(spec.get("item_id") in data.items, "Unknown item_id")
                    if spec.get("text_id"):
                        require(spec["text_id"] in data.texts, "Unknown text_id")
                        require(spec["text_id"] in data.text_item_map, "Add a text_item_map entry for town text items")
                else:
                    container_id = spec.get("decor_id", "barrel")
                    require(data.decoratives.get(container_id, {}).get("container") is True,
                            "Container decor_id must identify an actual container")
                    require(isinstance(spec.get("loot_pools", []), list) and
                            all(p in data.loot_pools for p in spec.get("loot_pools", [])), "Unknown loot pool")
            factory = ItemFactory(data)
            for flip in (False, True):
                local_map = LocalMap(80, 43)
                for x in range(80):
                    for y in range(43):
                        local_map.set_tile(x, y, "grass", True, True)
                ox, oy = (80 - width) // 2, (43 - height) // 2
                specs = _stamp_building_at(local_map, definition, ox, oy, data.terrain, flip_v=flip)
                require(len(specs) == len(definition.get("special_tiles", [])), "A supported special tile was dropped")
                random_source = random.Random(20261023)
                for spec in specs:
                    x, y = spec["x"], spec["y"]
                    if spec["kind"] == "container":
                        items = roll_pools(spec["loot_pools"], data.loot_pools, factory, random_source)
                        place_container(local_map, x, y, spec["decor_id"], items)
                    else:
                        item_id = data.text_item_map.get(spec.get("text_id"), spec["item_id"])
                        item = factory.create(item_id, x, y)
                        require(item is not None, "ItemFactory failed to create a placed item")
                        if spec.get("text_id"):
                            item.text_id = spec["text_id"]
                        require(place_floor_object(local_map, x, y, item), "Floor placement failed")
                accessible = reachable(local_map, data)
                for y, row in enumerate(rows):
                    for x, char in enumerate(row):
                        terrain = legend[char]
                        yy = height - 1 - y if flip else y
                        pos = (ox + x, oy + yy)
                        if terrain and (data.terrain[terrain].get("walkable") or terrain == "door_closed"):
                            deco = data.decoratives.get(local_map.decor.get(pos), {})
                            if not deco.get("blocks_movement", False):
                                require(pos in accessible, f"Interior tile {x},{y} is unreachable with doors treated as openable")
                results.append({"check": "stamp, materialize and reach interior", "flip_v": flip,
                                "item_specs": len(specs), "containers": len(local_map.container_state),
                                "floor_items": sum(map(len, local_map.floor_objects.values())), "passed": True})
            # Isolate one category to prove the *actual random generation path*
            # can select it; this does not estimate ordinary-world frequency.
            data.buildings = {category: [definition]}
            role = "C" if category in ("civic", "religious") else "NW" if category in ("ruins", "wilderness") else "N"
            chunk = Chunk(10, 10, RegionType.TOWN, seed=20261023, biome_id="town", town_id=1, town_role=role)
            with redirect_stdout(messages):
                local_map, spawn = generate_region(chunk, 80, 43, data.terrain, data=data)
            matches = [b for b in chunk.town_data.buildings if b["id"] == identifier]
            require(bool(matches), "No building fit the isolated random placement fixture; shrink it or inspect its category")
            require(local_map.in_bounds(*spawn), "Generated player spawn is out of bounds")
            results.append({"check": "actual generate_region town selection", "role": role,
                            "placements": len(matches), "item_spawns": len(chunk.town_data.item_spawns), "passed": True})
        finally:
            os.chdir(original_cwd)
    report = {"passed": True, "game_source": str(game), "building": str(source),
              "building_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "checks": results, "diagnostics": messages.getvalue(),
              "limitations": "Headless data/placement smoke only. No complete game-loop, rendered appearance, or world-frequency claim."}
    if args.output:
        args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
