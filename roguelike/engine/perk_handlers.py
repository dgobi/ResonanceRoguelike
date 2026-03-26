# engine/perk_handlers.py
"""
Perk handler functions.
Each function is a pure function: (payload: dict) -> dict | None.
Handlers read player state and return an effect dict — they do NOT
mutate state directly.

Add new handlers here as perks are designed.
HANDLER_MAP at the bottom must be updated for each new handler.
"""
from __future__ import annotations
from engine.palette import *


# ------------------------------------------------------------------ #
#  Smoke test perk 1 — Hardened Step
# ------------------------------------------------------------------ #

def perk_hardened_step_tile_entered(payload: dict) -> dict | None:
    """
    'The soles of your feet have calcified. Difficult ground holds
     less purchase over you.'

    Reduces the move_cost penalty from difficult terrain by 30%.
    A property change — changes how terrain interacts with the body.
    """
    move_cost = payload.get("move_cost", 1.0)
    if move_cost <= 1.0:
        return None
    return {"move_debt_modifier": 0.70}


# ------------------------------------------------------------------ #
#  Smoke test perk 2 — Carrion Eye
# ------------------------------------------------------------------ #

def perk_carrion_eye_entity_killed(payload: dict) -> dict | None:
    """
    'Something in the back of your eyes has changed. The residue of
     the dead becomes legible.'

    When an entity is killed, heals 1 HP to the least damaged body part
    if blood is present on the floor within 3 tiles of the kill.
    """
    engine = payload.get("engine")
    x      = payload.get("x", 0)
    y      = payload.get("y", 0)

    if engine is None:
        return None

    blood_terrains = {
        "blood_pool", "ectoplasm_pool",
        "bone_dust", "ichor_seep", "verdigris_fluid",
    }

    map_w = getattr(engine, "map_width",  80)
    map_h = getattr(engine, "map_height", 43)

    found_blood = False
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            tx, ty = x + dx, y + dy
            if not (0 <= tx < map_w and 0 <= ty < map_h):
                continue
            terrain = engine.get_terrain(tx, ty)
            if terrain in blood_terrains:
                found_blood = True
                break
        if found_blood:
            break

    if not found_blood:
        return None

    return {
        "heal":          1,
        "add_message":   "The residue speaks. A wound closes slightly.",
        "message_color": BLOOD_STONE,   # blood_rose
    }


# ------------------------------------------------------------------ #
#  System handler — EXP on kill (permanent, not a perk handler)
# ------------------------------------------------------------------ #

# Maps creature difficulty tier string → numeric tier
_DIFF_TO_TIER: dict[str, int] = {
    "trivial":    -2,
    "easy":       -1,
    "standard":    0,
    "hard":        1,
    "dangerous":   2,
}

# Maps player level → approximate difficulty tier
def _level_to_tier(level: int) -> int:
    if level <= 2:  return -2
    if level <= 5:  return -1
    if level <= 10: return  0
    if level <= 16: return  1
    return 2


def system_exp_on_kill(payload: dict) -> dict | None:
    """
    Permanent system handler — awards EXP when an entity is killed.
    Not tagged _is_perk_handler; never cleared.
    """
    engine   = payload.get("engine")
    entity   = payload.get("entity")
    if engine is None or entity is None:
        return None

    level_comp = getattr(engine.player, "level", None)
    if level_comp is None:
        return None

    creature_key = getattr(entity, "tile", "") or ""
    creature_def = engine.data.entities.get(creature_key, {}) if creature_key else {}
    diff_str     = creature_def.get("difficulty", "standard")
    creature_tier = _DIFF_TO_TIER.get(diff_str, 0)
    player_tier   = _level_to_tier(level_comp.level)

    delta = creature_tier - player_tier
    delta = max(-2, min(2, delta))

    multipliers = {2: 1.5, 1: 1.2, 0: 1.0, -1: 0.5, -2: 0.1}
    base_exp = 30
    gained   = max(1, int(base_exp * multipliers[delta]))

    levelled = level_comp.add_exp(gained)

    effects: dict = {
        "add_message": f"A weight settles. (+{gained})",
        "message_color": STONE_BLUE,   # slate_mid
    }
    if levelled:
        effects["level_up"] = True

    return effects


# ------------------------------------------------------------------ #
#  Handler map — must match JSON "handler" field exactly
# ------------------------------------------------------------------ #

HANDLER_MAP: dict[str, callable] = {
    "perk_hardened_step_tile_entered":  perk_hardened_step_tile_entered,
    "perk_carrion_eye_entity_killed":   perk_carrion_eye_entity_killed,
}

# Tag all handlers so they can be cleared on perk change without
# accidentally removing non-perk handlers registered by other systems.
for _fn in HANDLER_MAP.values():
    _fn._is_perk_handler = True
