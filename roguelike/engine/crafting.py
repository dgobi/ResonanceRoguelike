# engine/crafting.py
"""
Exact-instance crafting allocation and commitment.

can_craft(recipe, inv, keyword_data, ambient_sources)  — test whether keyword requirements are met
attempt_craft(recipe, inv, keyword_data, ambient_sources) — consume ingredients, lowest-tier first

ambient_sources: list of {"tag": str, "tier": int} dicts representing environmental
conditions (lit torch, campfire, etc.) that satisfy requirements but are never consumed.
Components and single-item conjunctions are spent materials; tools are kept.
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
        self.materials = []


def conditions_for(recipe):
    """Passive work still belongs at a stationary fire, even with a lit torch."""
    conditions = list(recipe.get("requires_ambient", []))
    if recipe.get("passive_processing"):
        conditions.append(dict(tag="stationary_fire", min_tier=1))
    return conditions


def material_candidate(item, preferred=None):
    # Reusable valuables require an explicit ingredient choice before spending.
    return getattr(item, "consumed_on_use", True) or getattr(item, "item_id", None) == preferred


def _match_ingredients(slots, unavailable=()):
    """Maximum exact-instance matching across material and tool slots.

    An augmenting path can move an earlier ingredient to another valid slot.
    That avoids the greedy failure where a multi-tag item steals the only match
    for a later requirement. Environmental conditions never fill physical slots.
    """
    owners = {}

    def assign(slot_index, seen):
        for item_index in slots[slot_index]["candidates"]:
            if item_index in unavailable or item_index in seen:
                continue
            seen.add(item_index)
            previous = owners.get(item_index)
            if previous is None or assign(previous, seen):
                owners[item_index] = slot_index
                return True
        return False

    for slot_index in range(len(slots)):
        assign(slot_index, set())
    return {slot_index: item_index for item_index, slot_index in owners.items()}


def plan_craft(recipe, inv, keyword_data=None, ambient_sources=None, chosen_items=None):
    """Find a complete exact-instance allocation without mutating owners.

    Each instance fills one physical slot, including reusable tools. Prefer
    lower tiers in recipe order. An explicit material preference is
    accepted only if the rest of the recipe remains satisfiable; inventory order
    therefore cannot hide a valid allocation. Explicit component choices require
    at least one instance of the chosen definition for that component.
    """
    items = list(inv.items) if inv is not None else []
    if len({id(i) for i in items}) != len(items):
        return [], [{"tag": "duplicate instance", "min_tier": 1, "have": 0, "need": 1}]
    selected, missing = CraftPlan(chosen_items), []
    for req in conditions_for(recipe):
        if not _ambient_satisfies(ambient_sources, req["tag"], req.get("min_tier", 1)):
            missing.append(dict(tag=req["tag"], min_tier=req.get("min_tier", 1), have=0, need=1, ambient=True))

    groups, slots = [], []

    def add_requirement(tags, quantity, details, *, role="material", component=None):
        has_choice = component is not None and component in selected.choices
        preferred = selected.choices.get(component)

        def preference(index):
            item = items[index]
            tiers = tuple(_tag_tier_on_item(item, req["tag"]) for req in tags)
            item_id = getattr(item, "item_id", "")
            # Definition order is stable across inventory permutations. Identity
            # only breaks ties between otherwise equivalent live instances.
            return (has_choice and item_id != preferred, sum(tiers), tiers, item_id, id(item))

        matches = sorted((n for n, item in enumerate(items) if _item_has_all_tags(item, tags)
                          and (role == "tool" or material_candidate(item, preferred))),
                         key=preference)
        group = len(groups)
        groups.append(dict(details, need=quantity))
        for unit in range(quantity):
            # Same-component units are interchangeable: requiring the first to
            # use the chosen definition preserves the UI choice without forcing
            # the entire quantity to come from that definition.
            requires_choice = has_choice and unit == 0
            candidates = ([n for n in matches if items[n].item_id == preferred]
                          if requires_choice else matches)
            slots.append(dict(group=group, candidates=candidates, role=role))

    rsi = recipe.get("requires_single_item")
    if rsi:
        tags = rsi if isinstance(rsi, list) else rsi.get("tags", [])
        quantity = 1 if isinstance(rsi, list) else rsi.get("max_quantity", 1)
        add_requirement(tags, quantity, dict(tag="+".join(t["tag"] for t in tags),
                        min_tier=max((t.get("min_tier", 1) for t in tags), default=1), single_item=True))
    for ci, comp in enumerate(recipe.get("components", [])):
        tag, tier, quantity = comp["tag"], comp.get("min_tier", 1), comp.get("quantity", 1)
        add_requirement([dict(tag=tag, min_tier=tier)], quantity, dict(tag=tag, min_tier=tier),
                        component=ci)
    for tool in recipe.get("tools", []):
        tag, tier = tool["tag"], tool.get("min_tier", 1)
        add_requirement([dict(tag=tag, min_tier=tier)], tool.get("quantity", 1),
                        dict(tag=tag, min_tier=tier, role="tool"), role="tool")

    matching = _match_ingredients(slots)
    if len(matching) != len(slots):
        # Keep the established missing-requirement shape for the crafting UI.
        for group, details in enumerate(groups):
            have = sum(n in matching for n, slot in enumerate(slots)
                       if slot["group"] == group)
            if have < details["need"]:
                missing.append(dict(details, have=have))
        selected.extend(items[matching[n]] for n in sorted(matching))
        return selected, missing

    # Choose a deterministic lowest-tier solution among complete allocations
    # that use the maximum number of physical ingredients. Feasibility checks
    # use matching, not exponential backtracking through inventory permutations.
    physical_left, used = len(matching), set()
    for n, slot in enumerate(slots):
        options = slot["candidates"]
        suffix = slots[n + 1:]
        for candidate in options:
            if candidate in used:
                continue
            reserved = used | {candidate}
            remainder = _match_ingredients(suffix, reserved)
            if len(remainder) == physical_left - 1:
                selected.append(items[candidate])
                if slot["role"] == "material":
                    selected.materials.append(items[candidate])
                used.add(candidate)
                physical_left -= 1
                break
        else:
            raise RuntimeError("Craft allocation lost a previously validated matching")
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
    committed = exchange(engine, checked.materials, outputs)
    if committed:
        engine._free_move_pending = False
    return committed


def attempt_craft(recipe, inv, keyword_data=None, ambient_sources=None, chosen_items=None):
    """Pure inventory API: validate the entire recipe before removing anything.

    Engine callers use commit_craft to maintain equipment and output ownership.
    """
    selected, missing = plan_craft(recipe, inv, keyword_data, ambient_sources, chosen_items)
    if missing:
        return False
    if any(item.equipped for item in selected.materials):
        return False  # This API has no actor with which to detach safely.
    for item in selected.materials:
        inv.remove(item)
    return True
