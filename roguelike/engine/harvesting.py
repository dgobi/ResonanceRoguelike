"""Native harvest rules shared by gameplay and authoring (no editor imports).

Absence, empty objects and empty selected tiers intentionally differ. Lists are
ordered: max() keeps the first equal threshold and each output is its own roll.
"""
from __future__ import annotations

MAX_ROWS = 64
MAX_OUTPUTS = 64
MAX_TIER = 32
MAX_DECAY = 2**53 - 1
DEFAULTS = dict(decay_turns=200, min_cutting_tier=1, quantity_min=0, quantity_max=1)
RULES = dict(defaults=DEFAULTS, max_rows=MAX_ROWS, max_outputs=MAX_OUTPUTS,
             max_tier=MAX_TIER, max_decay=MAX_DECAY,
             meaning=("Absent profile or {}: free refusal; a nonempty profile without tiers: one-turn insufficient-tool refusal. "
                      "Decay absent: 200 active-map ticks; null: no decay; zero/one: next active tick. "
                      "Highest qualifying cutting threshold wins; first equal row wins. bone_reader qualifies every row, "
                      "but cost uses the owned tool's copied tier: max(1, 5 - (actual tier - threshold)). "
                      "Each output independently rolls an inclusive quantity range, absent 0–1. "
                      "A selected empty/zero-yield tier consumes the corpse at normal cost."))


def profile_errors(creature, resolve_item=None):
    """Return (field, reason) pairs; an optional resolver constructs unowned items."""
    errors = []
    if "butcher_yield" not in creature:
        return errors
    profile = creature["butcher_yield"]
    def bad(field, message): errors.append(("butcher_yield" + field, message))
    def integer(field, value, maximum):
        if type(value) is not int or not 0 <= value <= maximum:
            bad(field, f"Expected an exact integer from 0 to {maximum}; booleans/null are invalid.")
            return False
        return True
    if not isinstance(profile, dict):
        bad("", "Expected an optional native object; null is not absence.")
        return errors
    decay = profile.get("decay_turns", DEFAULTS["decay_turns"])
    if decay is not None: integer(".decay_turns", decay, MAX_DECAY)
    tiers = profile.get("tiers", [])
    if not isinstance(tiers, list) or len(tiers) > MAX_ROWS:
        bad(".tiers", f"Expected an ordered list of at most {MAX_ROWS} records (or omission).")
        return errors
    for i, tier in enumerate(tiers):
        field = f".tiers[{i}]"
        if not isinstance(tier, dict):
            bad(field, "Expected a tier record."); continue
        integer(field + ".min_cutting_tier", tier.get("min_cutting_tier", 1), MAX_TIER)
        rows = tier.get("yields", [])
        if not isinstance(rows, list) or len(rows) > MAX_ROWS:
            bad(field + ".yields", f"Expected an ordered list of at most {MAX_ROWS} records (or omission).")
            continue
        total = 0
        for j, row in enumerate(rows):
            where = field + f".yields[{j}]"
            if not isinstance(row, dict):
                bad(where, "Expected an output record."); continue
            lo, hi = row.get("quantity_min", 0), row.get("quantity_max", 1)
            valid_lo = integer(where + ".quantity_min", lo, MAX_TIER)
            valid_hi = integer(where + ".quantity_max", hi, MAX_TIER)
            if valid_hi: total += hi
            if valid_lo and valid_hi and lo > hi:
                bad(where, "Effective minimum exceeds maximum (omitted quantities default to 0 / 1).")
            identifier = row.get("item_id")
            if not isinstance(identifier, str) or not identifier:
                bad(where + ".item_id", "Choose a uniquely resolved saved factory-valid item.")
            elif resolve_item:
                try: resolve_item(identifier)
                except Exception as error: bad(where + ".item_id", str(error))
        if total > MAX_OUTPUTS:
            bad(field + ".yields", f"Effective maxima permit {total} physical outputs; limit is {MAX_OUTPUTS}.")
    return errors


def validate_output(item, identifier):
    from entities.item import Item
    from engine.save_components import ITEM_STATE, snapshot, validate_fields
    if not isinstance(item, Item) or item.item_id != identifier:
        raise ValueError(f"Factory did not construct item {identifier!r}.")
    validate_fields(snapshot(item, ITEM_STATE), ITEM_STATE, "harvest output " + identifier)
    return item


def construct_output(data, factory, identifier, x=0, y=0):
    matches = [key for key in data.items if key.casefold() == identifier.casefold()]
    sources = getattr(data, "item_definition_sources", None)
    paths = [p for key, rows in sources.items() if key.casefold() == identifier.casefold() for p in rows] if sources is not None else None
    if matches != [identifier] or paths is not None and len(paths) != 1:
        raise ValueError(f"Missing, ambiguous or case-colliding harvest item {identifier!r}: {paths or matches}.")
    return validate_output(factory.create(identifier, x=x, y=y), identifier)


def owned_cutters(player):
    """Exact inventory-owned equipped slots; copied keywords govern harvesting."""
    inv, equip = getattr(player, "inventory", None), getattr(player, "equipment", None)
    result = []
    if inv is None or equip is None: return result
    for slot in ("weapon", "offhand"):
        item = equip.slots.get(slot)
        if item is None or not inv.contains(item) or not getattr(item, "equipped", False): continue
        tiers = [kw["tier"] for kw in getattr(item, "keywords", [])
                 if isinstance(kw, dict) and kw.get("tag") == "cutting"
                 and type(kw.get("tier")) is int and 0 <= kw["tier"] <= MAX_DECAY]
        if tiers and not any(owned is item for owned, _ in result): result.append((item, max(tiers)))
    return result


def select_tier(profile, cutting_tier, bone_reader=False):
    qualified = [tier for tier in profile.get("tiers", [])
                 if bone_reader or tier.get("min_cutting_tier", 1) <= cutting_tier]
    return max(qualified, key=lambda t: t.get("min_cutting_tier", 1)) if qualified else None


def decay_turns(creature):
    """Death copies a countdown; existing corpses never call this on restore."""
    profile = creature.get("butcher_yield", {})
    # External malformed data must not break death finalization.
    value = profile.get("decay_turns", 200) if isinstance(profile, dict) else 200
    return value if value is None or type(value) is int and 0 <= value <= MAX_DECAY else 200


def butcher(engine, x, y, corpse=None, *, scene=None, address=None):
    """Stage all physical rewards, publish atomically, then consume exact remains.

    False is a free refusal/failure. True owns the ordinary action's first turn;
    only successful harvesting adds the remaining move debt. RNG is not rewound.
    """
    import random
    from generation import floor_object_utils as floor
    from engine.message_log import MSG_DEFAULT
    def refuse(message):
        engine.log.add(message, MSG_DEFAULT)
        return False
    current_address = (engine.world_x, engine.world_y, engine.current_submap_id)
    if (scene is not None and scene is not engine.local_map
            or address is not None and address != current_address
            or not engine.interaction_cursor.can_reach(engine, x, y)):
        return refuse("Those remains are no longer within reach in this scene.")
    present = floor.get_floor_objects(engine.local_map, x, y)
    if corpse is None:
        corpses = [item for item in present if getattr(item, "source_creature", None)]
        if len(corpses) != 1:
            return refuse("Select one actual corpse; these remains are missing or ambiguous.")
        corpse = corpses[0]
    if (not getattr(corpse, "source_creature", None)
            or not any(item is corpse for item in present) or (corpse.x, corpse.y) != (x, y)):
        return refuse("Those exact remains are no longer here.")
    creature = engine.data.entities.get(corpse.source_creature, {})
    errors = profile_errors(creature)
    if errors: return refuse("Cannot harvest invalid remains: " + "; ".join(f"{f}: {m}" for f, m in errors))
    profile = creature.get("butcher_yield")
    if not profile: return refuse("This cannot be butchered.")
    cutters = owned_cutters(engine.player)
    actual = max((tier for _, tier in cutters), default=0)
    perks = getattr(engine.player, "perks", None)
    best = select_tier(profile, actual, bool(perks and perks.has("bone_reader")))
    if best is None:
        engine.log.add("Thy equipped tool is insufficient for this task.", MSG_DEFAULT)
        return True
    # Freshness is physical: a factory must not give us a pre-existing object.
    preexisting = [item for rows in engine.local_map.floor_objects.values() for item in rows]
    preexisting += list(getattr(engine.player.inventory, "items", [])) + list(engine.entities)
    preexisting += [item for entry in getattr(engine.local_map, "container_state", {}).values() for item in entry.get("items", [])]
    staged, quantities = [], []
    try:
        # Even a zero roll must reference a valid, constructible item.
        for row in best.get("yields", []):
            probe = construct_output(engine.data, engine.item_factory, row["item_id"], x, y)
            if any(item is probe for item in preexisting): raise ValueError("Factory returned an owned instance.")
        for row in best.get("yields", []):
            identifier = row["item_id"]
            quantity = random.randint(row.get("quantity_min", 0), row.get("quantity_max", 1))
            for _ in range(quantity):
                item = construct_output(engine.data, engine.item_factory, identifier, x, y)
                if any(owned is item for owned in preexisting + staged):
                    raise ValueError("Factory returned a reused physical instance.")
                staged.append(item)
            quantities.append((identifier, quantity))
        for item in staged:
            if not floor.place_floor_object(engine.local_map, x, y, item):
                raise ValueError("Floor placement refused a harvest output.")
            if not any(owned is item for owned in floor.get_floor_objects(engine.local_map, x, y)):
                raise ValueError("Floor placement did not publish its output.")
    except Exception as error:
        # A failing placement may have written before returning/raising. Remove
        # only attempt-owned instances, wherever that boundary published them.
        for xy in list(engine.local_map.floor_objects):
            for item in staged: floor.remove_floor_object(engine.local_map, *xy, item)
        return refuse(f"Harvest failed; the remains are intact: {error}")
    floor.remove_floor_object(engine.local_map, x, y, corpse)
    cost = max(1, 5 - (actual - best.get("min_cutting_tier", 1)))
    engine._move_debt += cost - 1
    tools = " and ".join(item.name for item, _ in cutters) or "bare hands"
    engine.log.add(f"You butcher the {creature.get('name', corpse.source_creature)} using {tools}.", MSG_DEFAULT)
    for identifier, quantity in quantities:
        if quantity:
            engine.log.add(f"  {engine.data.items[identifier].get('name', identifier).capitalize()} x{quantity}.", MSG_DEFAULT)
    if not staged: engine.log.add("  The remains yield nothing useful.", MSG_DEFAULT)
    return True
