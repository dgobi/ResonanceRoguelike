# entities/item.py
from __future__ import annotations
from entities.entity import Entity


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
        # If False, item is not removed from inventory when used as a crafting component.
        # Set on tools, vessels, weapons, armour — anything that survives the process.
        self.consumed_on_use:   bool         = True