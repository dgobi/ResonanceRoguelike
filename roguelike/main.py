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
WORLD_SEED   = 42


def main() -> None:
    display      = DisplayConfig.from_config()
    data         = DataLoader("data")
    registry     = TileRegistry("data/tiles.json", mode=display.render_mode)

    import random as _random
    rng           = _random.Random(WORLD_SEED)
    world_map     = WorldMap(WORLD_WIDTH, WORLD_HEIGHT)
    world_map.seed = WORLD_SEED
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

    # Place 2 waystones within 3-6 tiles of player spawn — establishes the mechanic
    import math as _math
    wt_def = data.terrain.get("waystone_plinth", {})
    if wt_def:
        _placed = 0
        _attempts = 0
        while _placed < 2 and _attempts < 50:
            _attempts += 1
            _dist  = rng.randint(3, 6)
            _angle = rng.uniform(0, 2 * _math.pi)
            _tx = int(start_x + _math.cos(_angle) * _dist)
            _ty = int(start_y + _math.sin(_angle) * _dist)
            if not surface_map.in_bounds(_tx, _ty):
                continue
            if not surface_map.walkable[_tx, _ty]:
                continue
            surface_map.set_tile(_tx, _ty, "waystone_plinth",
                                 wt_def.get("walkable", False),
                                 wt_def.get("transparent", True))
            _placed += 1

    player = Actor(x=start_x, y=start_y, tile="player", name="Player")
    player.fighter    = Fighter(max_hp=30, power=5, defense=1)
    body_def = data.bodies.get("body_player", {})
    player.fighter.body_id = "body_player"
    if body_def:
        player.fighter.initialize_from_body(body_def)
    player.needs      = Needs()
    player.corruption = Corruption()
    player.inventory  = Inventory(capacity=20.0)
    player.language   = Language()
    player.perks      = Perks()
    player.equipment  = Equipment()
    player.level      = LevelComponent()
    player.true_sight = False

    # Starting inventory
    torch       = item_factory.create("tallow_torch")
    jerky       = item_factory.create("crow_jerky")
    flask       = item_factory.create("water_flask")
    crude_blade = item_factory.create("crude_blade")
    leather_jack = item_factory.create("leather_jack")
    if torch:        player.inventory.add(torch)
    if jerky:        player.inventory.add(jerky)
    if flask:        player.inventory.add(flask)
    if crude_blade:  player.inventory.add(crude_blade)
    if leather_jack: player.inventory.add(leather_jack)

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
    spawned = engine._spawn_layout_entities(lab_entities)

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


if __name__ == "__main__":
    while True:
        try:
            main()
            break
        except SystemExit as _e:
            if getattr(_e, "code", None) == 2:
                continue   # new game requested — re-run main()
            raise
