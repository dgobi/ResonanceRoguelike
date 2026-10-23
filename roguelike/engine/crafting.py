# engine/crafting.py
"""
Pure crafting logic — no engine state imports.

can_craft(recipe, inv, keyword_data, ambient_sources)  — test whether keyword requirements are met
attempt_craft(recipe, inv, keyword_data, ambient_sources) — consume ingredients, lowest-tier first

ambient_sources: list of {"tag": str, "tier": int} dicts representing environmental
conditions (lit torch, campfire, etc.) that satisfy requirements but are never consumed.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from components.inventory import Inventory


def _item_has_tag(item, tag: str, min_tier: int) -> bool:
    """Return True if item carries the given tag at or above min_tier."""
    for kw in getattr(item, "keywords", []):
        if kw.get("tag") == tag and kw.get("tier", 0) >= min_tier:
            return True
    return False


def _tag_tier_on_item(item, tag: str) -> int:
    """Return the tier for tag on item (for sort key). 0 if absent."""
    for kw in getattr(item, "keywords", []):
        if kw.get("tag") == tag:
            return kw.get("tier", 0)
    return 0


def _ambient_satisfies(ambient_sources: list, tag: str, min_tier: int) -> bool:
    """Return True if any ambient source satisfies this tag/tier requirement."""
    for src in (ambient_sources or []):
        if src.get("tag") == tag and src.get("tier", 0) >= min_tier:
            return True
    return False


def _item_has_all_tags(item, tags: list[dict]) -> bool:
    """Return True if item satisfies ALL tag requirements simultaneously."""
    for req in tags:
        if not _item_has_tag(item, req["tag"], req.get("min_tier", 1)):
            return False
    return True


class CraftPlan(list):
    """Exact selected instances plus the UI's component preferences."""
    def __init__(self, chosen_items=None):
        super().__init__()
        self.choices = dict(chosen_items or {})


def plan_craft(recipe, inv, keyword_data=None, ambient_sources=None, chosen_items=None):
    """Resolve all requirements without mutating owners, lowest tier first.

    Each physical instance can fill one slot. Available physical ingredients are
    used before ambient shortfall; reusable tools are selected but not consumed.
    Returns (exact selected instances, missing requirements).
    """
    remaining = list(inv.items) if inv is not None else []
    if len({id(i) for i in remaining}) != len(remaining):
        return [], [{"tag": "duplicate instance", "min_tier": 1, "have": 0, "need": 1}]
    selected, missing = CraftPlan(chosen_items), []
    for req in recipe.get("requires_ambient", []):
        if not _ambient_satisfies(ambient_sources, req["tag"], req.get("min_tier", 1)):
            missing.append(dict(tag=req["tag"], min_tier=req.get("min_tier", 1), have=0, need=1, ambient=True))
    rsi = recipe.get("requires_single_item")
    if rsi:
        tags = rsi if isinstance(rsi, list) else rsi.get("tags", [])
        quantity = 1 if isinstance(rsi, list) else rsi.get("max_quantity", 1)
        matches = [i for i in remaining if _item_has_all_tags(i, tags)]
        if len(matches) < quantity:
            missing.append(dict(tag="+".join(t["tag"] for t in tags), min_tier=max((t.get("min_tier", 1) for t in tags), default=1),
                                have=len(matches), need=quantity, single_item=True))
        else:
            for i in matches[:quantity]:
                remaining.remove(i)
                selected.append(i)
    for ci, comp in enumerate(recipe.get("components", [])):
        tag, tier, quantity = comp["tag"], comp.get("min_tier", 1), comp.get("quantity", 1)
        matches = sorted([i for i in remaining if _item_has_tag(i, tag, tier)], key=lambda i: _tag_tier_on_item(i, tag))
        if chosen_items and ci in chosen_items:
            preferred = chosen_items[ci]
            matches.sort(key=lambda i: getattr(i, "item_id", "") != preferred)
            if not any(i.item_id == preferred for i in matches):
                missing.append(dict(tag=tag, min_tier=tier, have=0, need=quantity))
        if len(matches) < quantity and not _ambient_satisfies(ambient_sources, tag, tier):
            missing.append(dict(tag=tag, min_tier=tier, have=len(matches), need=quantity))
        for i in matches[:quantity]:
            remaining.remove(i)
            selected.append(i)
    return selected, missing


def can_craft(recipe, inv, keyword_data=None, ambient_sources=None):
    _, missing = plan_craft(recipe, inv, keyword_data, ambient_sources)
    return not missing, missing


def commit_craft(engine, recipe, selected, ambient_sources=None, outputs=()):
    """Revalidate a pending exact plan, then consume and deliver together.

    No material reservation is persisted. Cancel/load simply discards the plan;
    ingredients remain in inventory until successful confirmation.
    """
    from components.inventory import Inventory
    from engine.item_transfers import exchange
    inv = engine.player.inventory
    if selected is None or any(not inv.contains(i) for i in selected):
        return False
    subset = Inventory()
    subset.items = list(selected)
    checked, missing = plan_craft(recipe, subset, ambient_sources=ambient_sources,
                                 chosen_items=getattr(selected, 'choices', None))
    if missing:
        return False
    consumed = [i for i in checked if getattr(i, "consumed_on_use", True)]
    return exchange(engine, consumed, outputs)


def attempt_craft(recipe, inv, keyword_data=None, ambient_sources=None, chosen_items=None):
    """Pure inventory API: validate the entire recipe before removing anything.

    Engine callers use commit_craft to maintain equipment and output ownership.
    """
    selected, missing = plan_craft(recipe, inv, keyword_data, ambient_sources, chosen_items)
    if missing:
        return False
    for item in selected:
        if getattr(item, "consumed_on_use", True):
            # This API has no actor with which to detach equipment safely.
            if item.equipped:
                return False
    for item in selected:
        if getattr(item, "consumed_on_use", True):
            inv.remove(item)
    return True
