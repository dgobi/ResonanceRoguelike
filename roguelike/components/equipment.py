# components/equipment.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.item import Item

SLOTS = [
    "weapon",
    "offhand",
    "armor_head",
    "armor_torso",
    "armor_arms",
    "armor_legs",
    "belt_1",
    "belt_2",
    "belt_3",
    "light",
]


@dataclass
class Equipment:
    slots: dict = field(
        default_factory=lambda: {s: None for s in SLOTS}
    )

    def equip(self, item: "Item", slot: str) -> None:
        self.slots[slot] = item
        item.equipped = True

    def unequip(self, slot: str) -> "Item | None":
        item = self.slots.get(slot)
        if item:
            item.equipped = False
            self.slots[slot] = None
        return item

    def is_equipped(self, item: "Item") -> bool:
        return item in self.slots.values()

    def equipped_in(self, slot: str) -> "Item | None":
        return self.slots.get(slot)
