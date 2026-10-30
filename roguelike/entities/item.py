# entities/item.py
from __future__ import annotations
from entities.entity import Entity


def repair_selected_equipment_use(item) -> None:
    """Resolve the four shipped missing handlers when their owner uses them.

    Definition hashes and untouched visited instances remain historical until
    that ordinary action; non-null custom handlers are never replaced.
    """
    if (getattr(item, "item_id", "") in {
            "revelation_lens", "leather_satchel", "herbalist_pouch", "component_satchel"}
            and getattr(item, "on_use", None) is None):
        item.on_use = "equip_toggle"


def use_capability(item):
    """Exact-ID flint use, new or historical; never rewrite instance fields."""
    declared = getattr(item, 'on_use', None)
    if declared is None and getattr(item, 'item_id', '') == 'flint_shard':
        return 'throw_flint_shard'
    return declared


class Item(Entity):
    """
    An entity that can be picked up, carried, and used.
    Lives either on the floor (in engine.entities) or
    in an actor's inventory.
    """

    def __init__(
        self,
        x:       int,
        y:       int,
        tile:    str,
        name:    str,
        item_id: str = "",
    ) -> None:
        super().__init__(
            x=x, y=y,
            tile=tile,
            name=name,
            blocks_movement=False,
        )
        self.item_id:   str   = item_id
        self.text_id:   str   = ""
        self.weight:    float = 0.0
        self.stackable: bool  = False
        self.count:     int   = 1
        self.on_use:    str | None = None

        # Type-specific data — populated by ItemFactory
        self.nutrition:     float | None = None
        self.hydration:     float | None = None
        self.heal_amount:   int   | None = None
        self.eat_message:   str   | None = None
        self.drink_message: str   | None = None
        self.burn_turns:   int   | None = None
        self.turns_lit:    int          = 0
        self.light_data:   dict | None  = None
        self.liquid:       str  | None  = None
        self.liquid_volume:float        = 0.0
        self.qualities:    dict         = {}
        self.description:  str          = ""
        self.equipped:     bool         = False
        self.harvest_from: str | None   = None
        self.keywords:          list         = []
        self.decay_timer:       int | None   = None
        # Corpse identity — set on corpse floor objects to track source creature
        self.source_creature:   str | None   = None
        # Temporary essence coating — list of {essence, strength, hits_remaining}
        # Applied via apply_to_weapon handler. Each hit consumes one charge.
        self.temporary_essence: list         = []
        # Reusable items are excluded from automatic material selection. Recipe
        # tools are kept; explicitly selected materials are always spent.
        self.consumed_on_use:   bool         = True
