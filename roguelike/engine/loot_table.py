# engine/loot_table.py
from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.data_loader import DataLoader
    from engine.item_factory import ItemFactory


class LootResolver:
    """
    Resolves loot table IDs into lists of item IDs.
    Supports weighted random selection and nested table references.
    Also supports "type": "text" entries via resolve_with_texts().
    """

    def __init__(self, data: DataLoader) -> None:
        self.data = data

    def _n_rolls(self, table: dict, rng: random.Random) -> int:
        rolls = table.get("rolls", [1, 1])
        if isinstance(rolls, int):
            return rolls
        min_rolls, max_rolls = rolls
        return rng.randint(min_rolls, max_rolls)

    def roll(
        self,
        table_id: str,
        rng: random.Random | None = None,
        depth: int = 0,
    ) -> list[str]:
        """
        Roll on a loot table and return a list of item IDs.
        Text entries are skipped — use resolve_with_texts() for those.
        depth guards against infinite recursion in nested tables.
        """
        if depth > 5:
            return []

        rng = rng or random.Random()
        table = self.data.loot.get(table_id)
        if not table:
            print(f"Warning: loot table '{table_id}' not found.")
            return []

        n_rolls  = self._n_rolls(table, rng)
        entries  = table["entries"]
        weights  = [e["weight"] for e in entries]
        results: list[str] = []

        for _ in range(n_rolls):
            entry = rng.choices(entries, weights=weights, k=1)[0]
            if "item" in entry:
                results.append(entry["item"])
            elif entry.get("type") == "text":
                pass   # handled by resolve_with_texts()
            elif "table" in entry:
                results.extend(
                    self.roll(entry["table"], rng, depth + 1)
                )

        return results

    def resolve_with_texts(
        self,
        table_id:     str,
        item_factory: "ItemFactory",
        x:            int,
        y:            int,
        rng:          random.Random | None = None,
        depth:        int = 0,
    ) -> list:
        """
        Roll on a loot table and return fully constructed Item objects.
        Handles "type": "text" entries by creating lab_note items with
        the text_id field populated, as well as regular item entries.
        """
        if depth > 5:
            return []

        rng = rng or random.Random()
        table = self.data.loot.get(table_id)
        if not table:
            print(f"Warning: loot table '{table_id}' not found.")
            return []

        n_rolls  = self._n_rolls(table, rng)
        entries  = table["entries"]
        weights  = [e["weight"] for e in entries]
        results  = []

        for _ in range(n_rolls):
            entry = rng.choices(entries, weights=weights, k=1)[0]

            if entry.get("type") == "text":
                text_id = entry.get("text_id", "")
                item = item_factory.create("lab_note")
                if item:
                    item.x       = x
                    item.y       = y
                    item.text_id = text_id
                    results.append(item)

            elif "item" in entry:
                item = item_factory.create(entry["item"])
                if item:
                    item.x = x
                    item.y = y
                    results.append(item)

            elif "table" in entry:
                results.extend(
                    self.resolve_with_texts(
                        entry["table"], item_factory, x, y, rng, depth + 1
                    )
                )

        return results