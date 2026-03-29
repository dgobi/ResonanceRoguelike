# engine/item_factory.py
from __future__ import annotations
import random
from entities.item import Item
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.data_loader import DataLoader


class ItemFactory:
    """
    Assembles Item instances from JSON definitions.
    Single source of truth for item construction.
    """

    def __init__(self, data: DataLoader) -> None:
        self.data = data

    def create(
        self,
        item_id: str,
        x:       int = 0,
        y:       int = 0,
    ) -> Item | None:
        defn = self.data.items.get(item_id)
        if not defn:
            print(f"Warning: item '{item_id}' not found.")
            return None

        item             = Item(
            x       = x,
            y       = y,
            tile    = defn.get("tile", "generic_item"),
            name    = defn.get("name", item_id),
            item_id = item_id,
        )
        item.weight      = defn.get("weight",    0.1)
        item.stackable   = defn.get("stackable", False)
        item.on_use      = defn.get("on_use",    None)
        item.text_id     = defn.get("text_id",   "")
        item.description = defn.get("description", "")

        # Consumable properties
        item.nutrition    = defn.get("nutrition",    None)
        item.hydration    = defn.get("hydration",    None)
        item.heal_amount  = defn.get("heal_amount",  None)
        item.eat_message  = defn.get("eat_message",  None)
        item.drink_message = defn.get("drink_message", None)
        item.harvest_from = defn.get("harvest_from", None)

        # Light source properties
        item.burn_turns  = defn.get("burn_turns",  None)
        item.light_data  = defn.get("light",       None)

        # Liquid container properties
        item.liquid        = defn.get("liquid",        None)
        item.liquid_volume = defn.get("liquid_volume", 0.0)

        # Tool qualities
        item.qualities = defn.get("qualities", {})

        # Crafting keyword tags
        item.keywords = defn.get("keywords", [])

        # Whether this item is consumed when used as a crafting component.
        # Default True (consumable). Set False on tools, weapons, vessels, armour.
        item.consumed_on_use = defn.get("consumed_on_use", True)

        return item

    def create_at_player(
        self,
        item_id: str,
        engine:  "Engine",
    ) -> Item | None:
        """Convenience — create item at player position."""
        return self.create(
            item_id,
            engine.player.x,
            engine.player.y,
        )