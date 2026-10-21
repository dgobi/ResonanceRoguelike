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


def can_craft(
    recipe: dict,
    inv: "Inventory",
    keyword_data: dict | None = None,
    ambient_sources: list | None = None,
) -> tuple[bool, list]:
    """
    Return (craftable, missing_list).

    missing_list entries: {"tag": str, "min_tier": int, "have": int, "need": int}

    One item unit satisfies one component slot unit. Items are claimed greedily
    in component order, lowest-tier qualifying item first per slot.

    ambient_sources provide unlimited virtual items of a given tag/tier — they
    satisfy requirements but are never claimed or consumed.

    requires_ambient slots MUST be satisfied by ambient_sources only — no
    inventory items count toward them.

    requires_single_item: one item must have ALL listed tags simultaneously.
    """
    # Check requires_ambient first — these are not consumed and must come from environment
    for req in recipe.get("requires_ambient", []):
        tag      = req["tag"]
        min_tier = req.get("min_tier", 1)
        if not _ambient_satisfies(ambient_sources or [], tag, min_tier):
            return (False, [{"tag": tag, "min_tier": min_tier, "have": 0, "need": 1, "ambient": True}])

    remaining  = list(inv.items)
    missing    = []

    # requires_single_item: find one item with ALL tags, consume it
    # Accepts both list format [{"tag":..., "min_tier":...}] and dict format {"tags":[...]}
    rsi = recipe.get("requires_single_item")
    if rsi:
        if isinstance(rsi, list):
            tags = rsi  # list of {"tag": str, "min_tier": int} dicts
            quantity = 1
        else:
            tags     = rsi.get("tags", [])
            quantity = rsi.get("max_quantity", 1)
        qualifying = [item for item in remaining if _item_has_all_tags(item, tags)]
        if len(qualifying) < quantity:
            missing.append({
                "tag": "+".join(t["tag"] if isinstance(t, dict) else str(t) for t in tags),
                "min_tier": max((t.get("min_tier", 1) if isinstance(t, dict) else 1 for t in tags), default=1),
                "have": len(qualifying), "need": quantity,
                "single_item": True,
            })
        else:
            for item in qualifying[:quantity]:
                remaining.remove(item)

    # Standard components — each claims separate items from remaining pool
    components = recipe.get("components", [])
    for comp in components:
        tag      = comp["tag"]
        min_tier = comp.get("min_tier", 1)
        quantity = comp.get("quantity", 1)

        qualifying = sorted(
            [item for item in remaining if _item_has_tag(item, tag, min_tier)],
            key=lambda i: _tag_tier_on_item(i, tag),
        )
        have = len(qualifying)
        if have < quantity:
            # Check if ambient sources can cover the shortfall (unlimited supply)
            if _ambient_satisfies(ambient_sources or [], tag, min_tier):
                # Ambient satisfies entire slot — consume nothing from inventory
                for item in qualifying:
                    remaining.remove(item)
            else:
                missing.append({
                    "tag": tag, "min_tier": min_tier,
                    "have": have, "need": quantity,
                })
        else:
            # Claim these items so they can't satisfy another slot
            for item in qualifying[:quantity]:
                remaining.remove(item)

    return (len(missing) == 0, missing)


def attempt_craft(
    recipe: dict,
    inv: "Inventory",
    keyword_data: dict | None = None,
    ambient_sources: list | None = None,
    chosen_items: dict | None = None,
) -> None:
    """
    Consume ingredients matching recipe components.
    Caller must verify can_craft first.
    Consumes lowest-tier qualifying items first to preserve higher-tier materials.
    Ambient sources are never consumed.

    chosen_items: optional dict mapping component index → item_id.
    When provided, that specific item_id is preferred for that component slot.
    """
    remaining = list(inv.items)

    # requires_single_item: consume items with ALL tags
    rsi = recipe.get("requires_single_item")
    if rsi:
        if isinstance(rsi, list):
            tags = rsi
            quantity = 1
        else:
            tags     = rsi.get("tags", [])
            quantity = rsi.get("max_quantity", 1)
        qualifying = [item for item in remaining if _item_has_all_tags(item, tags)]
        for item in qualifying[:quantity]:
            remaining.remove(item)
            if getattr(item, "consumed_on_use", True):
                inv.remove(item)

    for ci, comp in enumerate(recipe.get("components", [])):
        tag      = comp["tag"]
        min_tier = comp.get("min_tier", 1)
        quantity = comp.get("quantity", 1)

        qualifying = sorted(
            [item for item in remaining if _item_has_tag(item, tag, min_tier)],
            key=lambda i: _tag_tier_on_item(i, tag),
        )

        # If player chose a specific item_id for this component, prioritise it
        if chosen_items and ci in chosen_items:
            preferred_id = chosen_items[ci]
            preferred = [i for i in qualifying if getattr(i, "item_id", "") == preferred_id]
            others    = [i for i in qualifying if getattr(i, "item_id", "") != preferred_id]
            qualifying = preferred + others

        if len(qualifying) < quantity and _ambient_satisfies(ambient_sources or [], tag, min_tier):
            # Ambient satisfies this slot — consume whatever physical items qualify, then stop
            for item in qualifying:
                remaining.remove(item)
                if getattr(item, "consumed_on_use", True):
                    inv.remove(item)
        else:
            for item in qualifying[:quantity]:
                remaining.remove(item)
                if getattr(item, "consumed_on_use", True):
                    inv.remove(item)
