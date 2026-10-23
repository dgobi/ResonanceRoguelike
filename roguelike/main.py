# main.py
from config import MAP_WIDTH, MAP_HEIGHT
from engine.display_config import DisplayConfig
from engine.data_loader import DataLoader
from rendering.tile_registry import TileRegistry
from generation.world_gen import generate_world
from generation.region_gen import generate_region
from world.world_map import WorldMap
from generation.local_gen import generate_submap
from entities.actor import Actor
from engine.engine import Engine
from components.fighter import Fighter
from components.needs import Needs
from components.corruption import Corruption
from components.inventory import Inventory
from components.language import Language
from components.perks import Perks
from components.equipment import Equipment
from components.level import LevelComponent
from engine.item_factory import ItemFactory


WORLD_WIDTH  = 128
WORLD_HEIGHT = 128


def main() -> None:
    display      = DisplayConfig.from_config()
    data         = DataLoader("data")
    registry     = TileRegistry("data/tiles.json", mode=display.render_mode)

    import random as _random
    import json   as _json
    from pathlib import Path as _Path

    # Determine world seed.
    # New game: generate a fresh random seed so each world is unique.
    # Load:     read the stored seed from world.json so regenerated chunks
    #           are consistent with the original world.
    _save_world_path = _Path("saves") / "slot_0" / "world.json"
    if _save_world_path.exists():
        try:
            _w = _json.loads(_save_world_path.read_text(encoding="utf-8"))
            world_seed = int(_w.get("seed", 0)) or _random.randint(0, 2**32 - 1)
        except Exception:
            world_seed = _random.randint(0, 2**32 - 1)
    else:
        world_seed = _random.randint(0, 2**32 - 1)

    # Seed the global random module as a safety net (generation uses
    # Random(seed) instances, but this covers any stray global calls).
    _random.seed(world_seed)

    rng           = _random.Random(world_seed)
    world_map     = WorldMap(WORLD_WIDTH, WORLD_HEIGHT)
    world_map.seed = world_seed
    world_map     = generate_world(world_map, data, rng)
    start_wx      = world_map.start_wx
    start_wy      = world_map.start_wy
    world_map.mark_explored_radius(start_wx, start_wy, radius=1)
    chunk = world_map.get(start_wx, start_wy)
    if chunk:
        chunk.visited = True

    item_factory = ItemFactory(data)

    # Generate the surface local map (forest with sunken_ruin entrance)
    if chunk:
        surface_map, (start_x, start_y) = generate_region(
            chunk, MAP_WIDTH, MAP_HEIGHT, data.terrain
        )
    else:
        from world.local_map import LocalMap
        surface_map = LocalMap(MAP_WIDTH, MAP_HEIGHT)
        start_x, start_y = MAP_WIDTH // 2, MAP_HEIGHT // 2

    # Place 1 waystone adjacent to road, within 8 tiles of chunk centre.
    # Guard: skip if region_gen already placed one (e.g. forest chunk on a road).
    import math as _math
    wt_def = data.terrain.get("waystone_plinth", {})
    _existing_wt = any(
        str(surface_map.tiles[_cx, _cy]["terrain"]) == "waystone_plinth"
        for _cx in range(surface_map.width)
        for _cy in range(surface_map.height)
    )
    # Also check decor layer for waystone_plinth (post-conversion)
    if not _existing_wt:
        _existing_wt = any(
            v == "waystone_plinth"
            for v in getattr(surface_map, "decor", {}).values()
        )
    if wt_def and not _existing_wt:
        _road_terrain = {f"road_{i}" for i in range(16)}
        _cx, _cy = surface_map.width // 2, surface_map.height // 2
        # Find road tiles within 8 of centre
        _road_tiles: list[tuple[int, int]] = []
        for _rx in range(max(1, _cx - 8), min(surface_map.width - 1, _cx + 9)):
            for _ry in range(max(1, _cy - 8), min(surface_map.height - 1, _cy + 9)):
                if str(surface_map.tiles[_rx, _ry]["terrain"]) in _road_terrain:
                    _road_tiles.append((_rx, _ry))
        # Find walkable non-road tiles adjacent to road, nearest to centre
        _candidates: list[tuple[int, int, float]] = []
        for _rx, _ry in _road_tiles:
            for _dx, _dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                _ax, _ay = _rx + _dx, _ry + _dy
                if not surface_map.in_bounds(_ax, _ay):
                    continue
                if str(surface_map.tiles[_ax, _ay]["terrain"]) in _road_terrain:
                    continue
                if not surface_map.walkable[_ax, _ay]:
                    continue
                _d = _math.sqrt((_ax - _cx) ** 2 + (_ay - _cy) ** 2)
                _candidates.append((_ax, _ay, _d))
        if _candidates:
            from generation.decor_utils import place_decor as _pd_ws_main
            _candidates.sort(key=lambda c: c[2])
            _wx, _wy, _ = _candidates[0]
            _pd_ws_main(surface_map, _wx, _wy, "waystone_plinth")
        else:
            # Fallback: place near player start (original logic)
            _placed = 0
            _attempts = 0
            while _placed < 1 and _attempts < 50:
                _attempts += 1
                _dist  = rng.randint(3, 6)
                _angle = rng.uniform(0, 2 * _math.pi)
                _tx = int(start_x + _math.cos(_angle) * _dist)
                _ty = int(start_y + _math.sin(_angle) * _dist)
                if not surface_map.in_bounds(_tx, _ty):
                    continue
                if not surface_map.walkable[_tx, _ty]:
                    continue
                from generation.decor_utils import place_decor as _pd_ws_fb
                _pd_ws_fb(surface_map, _tx, _ty, "waystone_plinth")
                _placed += 1

    player = Actor(x=start_x, y=start_y, tile="player", name="Player")
    body_def = data.bodies.get("body_player", {})
    base_hp  = body_def.get("base_hp", 60)
    player.fighter         = Fighter(max_hp=base_hp, power=5, defense=1)
    player.fighter.body_id = "body_player"
    player.needs      = Needs()
    player.corruption = Corruption()
    player.inventory  = Inventory(capacity=20.0)
    player.language   = Language()
    player.perks      = Perks()
    player.equipment  = Equipment()
    player.level      = LevelComponent()
    player.true_sight   = False
    player.dodge_chance = 0.05   # 5% base dodge — read by combat system

    # Starting inventory
    torch        = item_factory.create("tallow_torch")
    jerky        = item_factory.create("crow_jerky")
    flask        = item_factory.create("water_flask")
    crude_blade  = item_factory.create("crude_blade")
    leather_jack = item_factory.create("leather_jack")
    pebble       = item_factory.create("moist_pebble")   # talisman — for testability
    if torch:        player.inventory.add(torch)
    if jerky:        player.inventory.add(jerky)
    if flask:        player.inventory.add(flask)
    if crude_blade:  player.inventory.add(crude_blade)
    if leather_jack: player.inventory.add(leather_jack)
    if pebble:       player.inventory.add(pebble)

    engine = Engine(
        player=player,
        local_map=surface_map,
        entities=[player],
        registry=registry,
        world_map=world_map,
        world_x=start_wx,
        world_y=start_wy,
        data=data,
        display=display,
    )

    # Light the starting torch
    if torch:
        engine.item_system.use(torch, engine)

    # Load save if exists — skip the lab descent if a save is loaded
    if engine.save_manager.save_exists():
        engine.save_manager.load(engine)
    else:
        # No save: descend directly into the starting lab
        _start_in_lab(engine, surface_map)

    # FOV integrity check — catches silent _compute_fov_base() failures at startup
    if engine.current_submap_id is None:
        _test_radius = engine._compute_fov_base()
        if _test_radius < 3:
            print(f"[STARTUP WARNING] _compute_fov_base() returned {_test_radius} on surface. FOV may be broken.")
            print("Check for diagnostic code, file writes, or silent exceptions in _compute_fov_base().")

    engine.run()


def _start_in_lab(engine: Engine, surface_map) -> None:
    """
    Place the player inside the starting lab submap on a fresh game.
    The surface map is stored in the chunk cache so ascending works normally.
    """
    chunk = engine.world_map.get(engine.world_x, engine.world_y)
    if not chunk or not chunk.submaps:
        return

    start_sub = chunk.submaps[0]

    # Generate the lab submap
    lab_map, lab_entities = generate_submap(
        start_sub, MAP_WIDTH, MAP_HEIGHT, engine.data.terrain, data=engine.data
    )
    spawned = engine._spawn_layout_entities(lab_entities, local_map=lab_map)

    # Cache the surface so ascending later restores it
    engine.save_manager.cache.store(
        engine.world_x, engine.world_y,
        surface_map, [engine.player],
    )

    # Set return point to the stairs_down entrance on the surface
    engine.surface_return_x = start_sub.surface_x
    engine.surface_return_y = start_sub.surface_y

    # Switch to lab map
    engine.local_map        = lab_map
    engine.entities         = [engine.player] + spawned
    engine.current_submap_id = start_sub.submap_id

    # Place player at the sarcophagus (player_start in layout)
    engine.player.x = start_sub.entry_x
    engine.player.y = start_sub.entry_y

    # Recompute FOV now that we're on the lab map
    engine._update_fov()


if __name__ == "__main__":
    while True:
        try:
            main()
            break
        except SystemExit as _e:
            if getattr(_e, "code", None) == 2:
                continue   # new game requested — re-run main()
            raise
