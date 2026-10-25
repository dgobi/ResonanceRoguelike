# components/inventory.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.item import Item


CATEGORY_MAP = {
    "weapon": "Weapons", "shield": "Armour & Shields", "armor": "Armour & Shields",
    "consumable": "Consumables", "preparation": "Preparations", "component": "Components",
    "butchery": "Components", "tool": "Tools",
}


def item_category(item, definitions) -> str:
    definition = definitions.get(getattr(item, "item_id", ""), {})
    if getattr(item, "on_use", "") == "read":
        return "Miscellaneous"
    if definition.get("slot") == "light":
        return "Light Sources"
    return CATEGORY_MAP.get(definition.get("category", ""), "Miscellaneous")


def effective_weight(item, category, reductions) -> float:
    reduction = reductions.get(category, reductions.get("all", 0.0))
    return getattr(item, "weight", 0.0) * (1.0 - reduction)


class Inventory:
    """
    A list of carried items.
    Weight-based capacity — everything has encumbrance.
    """

    def __init__(self, capacity: float = 20.0) -> None:
        self.capacity: float      = capacity
        self.items:    list[Item] = []
        self._equipment = None
        self._definitions = {}

    def bind_carrying(self, equipment, definitions) -> None:
        """Live references only; discounts are derived and never written to items."""
        self._equipment, self._definitions = equipment, definitions

    def reductions_for(self, items=None) -> dict:
        items = self.items if items is None else items
        bag = self._equipment.equipped_in("satchel") if self._equipment else None
        if bag is None or not any(i is bag for i in items):
            return {}
        return self._definitions.get(bag.item_id, {}).get("weight_reductions", {})

    def weight_for(self, items) -> float:
        """Project load after an exchange, including removal of an equipped bag."""
        reductions = self.reductions_for(items)
        return sum(effective_weight(i, item_category(i, self._definitions), reductions) for i in items)

    def capacity_feedback(self, item) -> str:
        return (f"Too much to carry: {self.current_weight:.2f}/{self.capacity:.2f} kg; "
                f"{self.weight_for(self.items + [item]):.2f} kg with that.")

    @property
    def current_weight(self) -> float:
        return self.weight_for(self.items)

    @property
    def is_full(self) -> bool:
        return self.current_weight >= self.capacity

    @property
    def encumbrance(self) -> float:
        """0.0 = unencumbered, 1.0 = over capacity."""
        return min(1.0, self.current_weight / self.capacity)

    def add(self, item: Item) -> bool:
        """Add item if capacity allows. Returns True on success."""
        if not self.can_add(item):
            return False
        self.items.append(item)
        return True

    def remove(self, item: Item) -> bool:
        for index, owned in enumerate(self.items):
            if owned is item:
                self.items.pop(index)
                return True
        return False

    def contains(self, item: Item) -> bool:
        return any(owned is item for owned in self.items)

    def can_add(self, item: Item) -> bool:
        return (item is not None and not self.contains(item)
                and self.weight_for(self.items + [item]) <= self.capacity)

    def has(self, item_id: str) -> bool:
        return any(getattr(i, "item_id", None) == item_id
                   for i in self.items)

    def get_by_id(self, item_id: str) -> Item | None:
        for item in self.items:
            if getattr(item, "item_id", None) == item_id:
                return item
        return None

    def __len__(self) -> int:
        return len(self.items)
