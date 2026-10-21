# components/inventory.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.item import Item


class Inventory:
    """
    A list of carried items.
    Weight-based capacity — everything has encumbrance.
    """

    def __init__(self, capacity: float = 20.0) -> None:
        self.capacity: float      = capacity
        self.items:    list[Item] = []

    @property
    def current_weight(self) -> float:
        return sum(getattr(i, "weight", 0.0) for i in self.items)

    @property
    def is_full(self) -> bool:
        return self.current_weight >= self.capacity

    @property
    def encumbrance(self) -> float:
        """0.0 = unencumbered, 1.0 = over capacity."""
        return min(1.0, self.current_weight / self.capacity)

    def add(self, item: Item) -> bool:
        """Add item if capacity allows. Returns True on success."""
        if self.current_weight + getattr(item, "weight", 0.0) > self.capacity:
            return False
        self.items.append(item)
        return True

    def remove(self, item: Item) -> bool:
        if item in self.items:
            self.items.remove(item)
            return True
        return False

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