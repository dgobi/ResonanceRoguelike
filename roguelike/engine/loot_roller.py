# engine/loot_roller.py
"""
Pure function module for rolling items from loot pool definitions.

Loot rolling is deterministic given an RNG seed. No engine imports.
"""
from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.item_factory import ItemFactory


def roll_pool(pool_def: dict, item_factory: "ItemFactory", rng: random.Random | None = None) -> list:
    """Roll items from a single pool definition. Returns list of Item objects."""
    rng = rng or random.Random()

    roll_range = pool_def.get("roll_count", [1, 1])
    roll_min = roll_range[0]
    roll_max = roll_range[1] if len(roll_range) > 1 else roll_min
    count = rng.randint(roll_min, roll_max)

    entries = list(pool_def.get("items", []))
    if not entries or count <= 0:
        return []

    # Weighted sample without replacement
    count = min(count, len(entries))
    results = []
    pool = list(entries)
    for _ in range(count):
        if not pool:
            break
        weights = [e.get("weight", 1) for e in pool]
        total = sum(weights)
        if total <= 0:
            break
        r = rng.random() * total
        cumulative = 0.0
        chosen_idx = 0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                chosen_idx = i
                break
        chosen = pool.pop(chosen_idx)
        item_id = chosen.get("item_id", "")
        if item_id:
            item = item_factory.create(item_id)
            if item is not None:
                results.append(item)

    return results


def roll_pools(
    pool_ids: list[str],
    all_pools: dict,
    item_factory: "ItemFactory",
    rng: random.Random | None = None,
) -> list:
    """Roll from multiple pools, combining results."""
    rng = rng or random.Random()
    results = []
    for pool_id in pool_ids:
        pool_def = all_pools.get(pool_id)
        if pool_def is None:
            print(f"Warning: loot pool '{pool_id}' not found.")
            continue
        results.extend(roll_pool(pool_def, item_factory, rng))
    return results
