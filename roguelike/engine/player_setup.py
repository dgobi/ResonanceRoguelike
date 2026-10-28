"""Normal player components and the ordinary starting loadout, shared by launchers."""
from entities.actor import Actor
from components.fighter import Fighter
from components.needs import Needs
from components.corruption import Corruption
from components.inventory import Inventory
from components.language import Language
from components.perks import Perks
from components.equipment import Equipment
from components.level import LevelComponent

PROFILE = "ordinary-player-v1: body_player; 60 base HP from body definition; normal needs/carrying/AI; tallow_torch, crow_jerky, water_flask, crude_blade, leather_jack, moist_pebble"

def create_player(data, item_factory, x, y):
    player = Actor(x=x, y=y, tile="player", name="Player")
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

    for item_id in ("tallow_torch", "crow_jerky", "water_flask", "crude_blade", "leather_jack", "moist_pebble"):
        item = item_factory.create(item_id)
        if item is not None:
            player.inventory.add(item)
    return player
