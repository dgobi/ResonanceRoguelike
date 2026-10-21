# entities/actor.py
from __future__ import annotations
from entities.entity import Entity


class Actor(Entity):
    """
    An entity that takes turns.
    Components are attached explicitly after construction.
    """

    def __init__(
        self,
        x:    int,
        y:    int,
        tile: str,
        name: str,
    ) -> None:
        super().__init__(
            x=x, y=y,
            tile=tile,
            name=name,
            blocks_movement=True,
        )
        self.is_alive:               bool  = True
        self.fighter                       = None   # Fighter
        self.needs                         = None   # Needs
        self.corruption                    = None   # Corruption
        self.inventory                     = None   # Inventory
        self.light_source                  = None   # LightSource
        self.ai                            = None   # AI
        self.perception                    = None   # Perception
        self.language                      = None   # Language
        self.perks                         = None   # Perks
        self.equipment                     = None   # Equipment
        self.level                         = None   # LevelComponent
        self.true_sight:             bool  = False
        self.took_damage_this_turn:  bool  = False
        self.chilled_turns:          int   = 0
        self._in_concealment:        bool  = False