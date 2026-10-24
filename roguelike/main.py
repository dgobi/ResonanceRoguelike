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
    from engine.save_manager import SaveManager
    try:
        startup, saved_seed = SaveManager().startup_state()
    except Exception as error:
        print(f"Startup load failed: {error}")
        raise SystemExit(1) from error
    display      = DisplayConfig.from_config()
    data         = DataLoader("data")
    registry     = TileRegistry("data/tiles.json", mode=display.render_mode)

    import random as _random

    # Determine world seed.
    # New game: generate a fresh random seed so each world is unique.
    # Load:     read the stored seed from world.json so regenerated chunks
    #           are consistent with the original world.
    world_seed = saved_seed if saved_seed is not None else _random.randint(0, 2**32 - 1)

    # Seed the global random module as a safety net (generation uses
    # Random(seed) instances, but this covers any stray global calls).
    _random.seed(world_seed)

    rng           = _random.Random(world_seed)
    world_map     = WorldMap(WORLD_WIDTH, WORLD_HEIGHT)
    world_map.seed = world_seed
    if startup != "load":
        world_map = generate_world(world_map, data, rng)
    start_wx      = world_map.start_wx
    start_wy      = world_map.start_wy
    world_map.mark_explored_radius(start_wx, start_wy, radius=1)
    chunk = world_map.get(start_wx, start_wy)
    if chunk:
        chunk.visited = True

    item_factory = ItemFactory(data)

    # Loading restores validated checkpoint scenes; it does not generate replacements.
    from world.local_map import LocalMap
    surface_map = LocalMap(MAP_WIDTH, MAP_HEIGHT)
    start_x, start_y = MAP_WIDTH // 2, MAP_HEIGHT // 2
    surface_actors = []
    if startup != "load" and chunk:
        from engine.creature_factory import CreatureFactory
        from engine.scene_generation import create_surface, publish_metadata
        result = create_surface(world_map, chunk, data, item_factory,
                                CreatureFactory(data), MAP_WIDTH, MAP_HEIGHT)
        surface_map, surface_actors = result.local_map, result.actors
        start_x, start_y = result.spawn
        publish_metadata(chunk, result.metadata)
        chunk.generation_revision = surface_map.generation_revision

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
        entities=[player] + surface_actors,
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
    if startup == "load":
        if not engine.save_manager.load(engine):
            print(f"Startup load failed: {engine.save_manager.last_error}")
            raise SystemExit(1)
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

    prepared = engine._prepare_destination(engine.world_x, engine.world_y, start_sub.submap_id)
    if prepared is None:
        return
    lab_map, spawned = prepared

    # Cache the surface so ascending later restores it
    engine.save_manager.cache.store(
        engine.world_x, engine.world_y,
        surface_map, engine.entities,
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
