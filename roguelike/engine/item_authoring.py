"""Read-only ordinary-component authoring contract; never imported by gameplay.

The factory, persisted instance schema and crafting predicates own semantics.
This deliberately narrow capability adds reference/identity checks to the loader's
permissive input. It does not change loading, use, inventory ownership or saves.
"""
from __future__ import annotations
import inspect
from pathlib import PurePosixPath
from engine.item_factory import ItemFactory
from engine.item_system import ItemSystem
from engine.save_components import ITEM_STATE, snapshot, validate_fields
from engine.crafting import _item_has_tag, _item_has_all_tags
from rendering.tile_registry import TileRegistry

CONTRACT = "component-1"
FIELDS = ["name", "description", "weight", "stackable", "keywords"]
# Known runtime-bearing fields outside an ordinary inert component. Unknown
# metadata is retained; none is promoted to a supported mechanical control.
ADVANCED = (set(ITEM_STATE) - set(FIELDS) - {
    "tile", "on_use", "consumed_on_use", "count", "text_id", "qualities"
}) | {"slot", "movesets", "on_use_effects", "damage_dice", "damage_bonus",
      "essence", "essence_strength", "crit_chance", "weight_reductions",
      "provides_burning", "light", "light_radius", "empty_form", "render_mode",
      "zone_radius", "zone_turns", "effects", "status", "statuses"}


def capability(raw, path, pointer=""):
    parts = PurePosixPath(path).parts
    supported = (not pointer and isinstance(raw, dict) and len(parts) >= 5
                 and parts[:4] == ("roguelike", "data", "items", "components")
                 and raw.get("category") == "component" and not raw.get("on_use")
                 and not (raw.keys() & ADVANCED) and not raw.get("text_id")
                 and not raw.get("qualities"))
    return {"contract": CONTRACT, "editable": bool(supported), "fields": FIELDS,
            "reason": "Ordinary inert component" if supported else
                "Read-only: requires one ordinary component object under items/components, without advanced use/equipment fields.",
            "weight_unit": "kg", "tier_min": 0, "tier_max": 2**53-1,
            "tier_note": "Nonnegative integer from the persisted instance contract; authoring is limited to exact JavaScript integers.",
            "stack_note": "Groups same-ID instances in inventory display. Instances and carried weights remain separate; no stack-size mechanic is authored."}


def use_binding(raw):
    declared = raw.get("on_use")
    handler = getattr(ItemSystem, f"_use_{declared}", None) if isinstance(declared, str) else None
    found = callable(handler)
    return {"declared": declared, "status": "Not applicable" if not declared else "Handler found" if found else "Unknown handler",
            "consumer": "roguelike/engine/item_system.py:ItemSystem.use",
            "handler": f"ItemSystem._use_{declared}" if found else None,
            "line": inspect.getsourcelines(handler)[1] if found else None,
            "scope": "Source-checked dynamic dispatch only. Inventory ownership, equipment repair, turn and handler preconditions are not exercised.",
            "notes": (["on_use_effects is declared JSON; ItemFactory and ItemSystem do not consume that list."] if "on_use_effects" in raw else []) +
                     (["consumed_on_use controls automatic crafting-material eligibility; use-handler return values govern ordinary use consumption."] if "consumed_on_use" in raw else [])}


def validate_definition(raw, data, path, sources, *, writable=False):
    """Check one loaded definition without mutating it or constructing an owner."""
    problems = []
    identifier = raw.get("id") if isinstance(raw, dict) else None
    def issue(code, field, message, severity="error"):
        problems.append(dict(severity=severity, code=code, field=field, path=path,
            asset=str(identifier or ""), message=message,
            correction="Correct this field/reference in the current source; advanced families remain read-only."))
    if not isinstance(raw, dict) or not isinstance(identifier, str) or not identifier:
        issue("ITEM_ID", "id", "Expected one item object with a nonempty string ID.")
        return problems
    locations = sources.get(identifier, [])
    collisions = [s for key, rows in sources.items() if key.casefold() == identifier.casefold() for s in rows]
    if len(locations) != 1 or len(collisions) != 1:
        issue("DUPLICATE_ID", "id", "Ambiguous item ID (including case collisions): " +
              ", ".join(s["path"] + s["pointer"] for s in collisions))
    if data.items.get(identifier) != raw or not any(s["path"] == path and s["definition"] == raw for s in locations):
        issue("LOADER_IDENTITY", "id", "DataLoader did not load this exact definition from this source.")
    if writable and not capability(raw, path)["editable"]:
        issue("UNSUPPORTED_ITEM", "category", capability(raw, path)["reason"])
    # Use the actual game instance validators, including bool-vs-number and
    # finite/nonnegative rules. Default fields are supplied by the factory later.
    for field in FIELDS + ["tile", "on_use", "consumed_on_use", "qualities", "text_id"]:
        if field in raw:
            try:
                validate_fields({field: raw[field]}, {field: ITEM_STATE[field]}, "definition")
            except ValueError as error:
                issue("ITEM_FIELD", field, str(error))
    keywords = raw.get("keywords", [])
    if isinstance(keywords, list):
        for i, kw in enumerate(keywords):
            if not isinstance(kw, dict): continue
            if not isinstance(kw.get("tag"), str) or kw["tag"] not in data.keywords:
                issue("KEYWORD_REFERENCE", f"keywords[{i}].tag", f"Unknown keyword {kw.get('tag')!r}.")
            tier = kw.get("tier")
            if type(tier) is int and tier > 2**53-1:
                issue("ITEM_FIELD", f"keywords[{i}].tier", "Tier exceeds exact authoring integer range.")
    for field, table in (("tile", TileRegistry(str(data.root / "tiles.json")).all_names()), ("text_id", data.texts)):
        if raw.get(field) and (not isinstance(raw[field], str) or raw[field] not in table):
            issue("ITEM_REFERENCE", field, f"Unknown declared {field} {raw[field]!r}.")
    binding = use_binding(raw)
    if binding["status"] == "Unknown handler":
        issue("UNKNOWN_HANDLER", "on_use", f"No actual dispatch handler for {raw['on_use']!r}.")
    return problems


def factory_preview(raw, data):
    """Actual definition-to-instance result, unowned and never used interactively."""
    item = ItemFactory(data).create(raw["id"])
    if item is None: raise ValueError("ItemFactory returned no instance")
    state = snapshot(item, ITEM_STATE)
    validate_fields(state, ITEM_STATE, "factory instance")
    comparisons = [{"field": f, "declared": raw[f], "instance": state[f], "equal": raw[f] == state[f]}
                   for f in FIELDS if f in raw]
    if not all(row["equal"] for row in comparisons):
        raise ValueError("Factory output differs from the supported definition fields")
    return {"item_id": item.item_id, "instance": state, "comparisons": comparisons,
            "consumer": "engine.data_loader.DataLoader -> engine.item_factory.ItemFactory.create -> entities.item.Item",
            "scope": "Observed unowned factory instance. No inventory/use/turn, acquisition, world selection or save migration was executed."}


def references(raw, data, source_index):
    """Declared IDs and potential tag matches; no full craft plan or simulation."""
    rows = []
    for field, table in (("tile", TileRegistry(str(data.root / "tiles.json")).all_names()), ("text_id", data.texts)):
        if raw.get(field):
            rows.append(dict(kind="Declared reference", field=field, id=raw[field], resolved=isinstance(raw[field], str) and raw[field] in table))
    for i, kw in enumerate(raw.get("keywords", []) if isinstance(raw.get("keywords", []), list) else []):
        if isinstance(kw, dict): rows.append(dict(kind="Declared reference", field=f"keywords[{i}].tag", id=kw.get("tag"), resolved=isinstance(kw.get("tag"), str) and kw["tag"] in data.keywords))
    # Predicates operate on the actual factory output. A match only establishes
    # one ingredient/tool predicate, never quantity, availability or a craft.
    try:
        item = ItemFactory(data).create(raw["id"])
        validate_fields(snapshot(item, ITEM_STATE), ITEM_STATE, "reference instance")
    except (ValueError, TypeError, KeyError):
        return rows
    for identifier, recipe in sorted(data.recipes.items()):
        paths = [s["path"] + s["pointer"] for s in source_index.get(identifier, [])]
        if recipe.get("result_item") == raw["id"]:
            rows.append(dict(kind="Declared recipe output", field="result_item", id=identifier, paths=paths))
        for role in ("components", "tools"):
            for i, req in enumerate(recipe.get(role, [])):
                try:
                    match = _item_has_tag(item, req["tag"], req.get("min_tier", 1))
                    if match: rows.append(dict(kind="Potential tag match", field=f"{role}[{i}]", id=identifier, paths=paths,
                                              note="Quantity, other ingredients, ambient conditions, recipe knowledge and ownership unverified."))
                except (KeyError, TypeError):
                    continue
        conjunction = recipe.get("requires_single_item")
        if isinstance(conjunction, (dict, list)):
            try:
                if _item_has_all_tags(item, conjunction if isinstance(conjunction, list) else conjunction["tags"]):
                    rows.append(dict(kind="Potential tag match", field="requires_single_item.tags", id=identifier, paths=paths,
                                     note="Only the single-item tag conjunction is checked; craftability unverified."))
            except (KeyError, TypeError): pass
    return rows
