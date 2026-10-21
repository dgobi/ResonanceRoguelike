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
#  Perk 3 — Marrow Drink (Viscera, cost 2)
# ------------------------------------------------------------------ #

_BLOOD_TILES: frozenset[str] = frozenset({
    "blood_pool", "bone_dust", "ectoplasm_pool",
    "ichor_seep", "verdigris_fluid",
})


def handle_marrow_drink_turn(payload: dict) -> dict | None:
    """
    'Something in you has learned to feed. It is not a pleasant thing
     to have learned.'

    Heals 1 HP per turn while standing on any blood/fluid tile.
    """
    engine = payload.get("engine")
    if engine is None:
        return None
    terrain = engine.get_terrain(engine.player.x, engine.player.y)
    if terrain not in _BLOOD_TILES:
        return None
    return {
        "heal":          1,
        "add_message":   "The residue enters. A wound closes slightly.",
        "message_color": BLOOD_STONE,
    }


# ------------------------------------------------------------------ #
#  Perk 4 — Attuned (Resonance, cost 2)
# ------------------------------------------------------------------ #

_ATTUNED_THRESHOLD = 0.3
_ATTUNED_AV_BONUS  = 2


def handle_attuned_turn(payload: dict) -> dict | None:
    """
    'The stone in your bones remembers the frequency. Blows find less
     purchase than they should.'

    +2 effective_av while resonance exposure >= 0.3.
    Applies and removes cleanly as exposure crosses the threshold.
    """
    engine = payload.get("engine")
    if engine is None:
        return None

    exposure = getattr(engine, "resonance_exposure", 0.0)
    active   = getattr(engine, "_attuned_bonus_active", False)
    fighter  = getattr(engine.player, "fighter", None)
    if fighter is None:
        return None

    if exposure >= _ATTUNED_THRESHOLD and not active:
        fighter.effective_av      += _ATTUNED_AV_BONUS
        engine._attuned_bonus_active = True
    elif exposure < _ATTUNED_THRESHOLD and active:
        fighter.effective_av      -= _ATTUNED_AV_BONUS
        engine._attuned_bonus_active = False

    return None


# ------------------------------------------------------------------ #
#  Perk 5 — The Indifference (Ontology, cost 3)
# ------------------------------------------------------------------ #

def handle_indifference_turn(payload: dict) -> dict | None:
    """
    'You have stopped flinching at what you are becoming. The change
     moves through you more cleanly now.'

    Each corruption threshold crossed grants +1 flat damage.
    Recalculated from threshold count every turn — stays correct on load.
    """
    engine = payload.get("engine")
    if engine is None:
        return None
    fighter = getattr(engine.player, "fighter", None)
    if fighter is None:
        return None
    thresholds = getattr(engine, "_corruption_thresholds", set())
    fighter.corruption_damage_bonus = len(thresholds)
    return None


# ------------------------------------------------------------------ #
#  Perk 6 — Lithic Seep (Creation, cost 2)
# ------------------------------------------------------------------ #

def handle_lithic_seep_kill(payload: dict) -> dict | None:
    """
    'What dies near you leaves a residue. You have learned to fix it
     in place.'

    On kill, places a resonance_stone at the entity's position as an
    ephemeral tile. The stone emits resonance and sparkles — it does
    not persist across chunk exits.
    """
    x = payload.get("x")
    y = payload.get("y")
    if x is None or y is None:
        return None
    return {
        "place_terrain": {"x": x, "y": y, "terrain_id": "resonance_seep"},
    }


# ------------------------------------------------------------------ #
#  Stateful perk cleanup — called by _register_player_perks before
#  clearing handlers, so bonuses don't persist after perk removal.
# ------------------------------------------------------------------ #

def cleanup_perk_state(engine) -> None:
    """Remove any transient stat modifications applied by stateful perks."""
    # Attuned: remove AV bonus if it was active
    if getattr(engine, "_attuned_bonus_active", False):
        fighter = getattr(getattr(engine, "player", None), "fighter", None)
        if fighter is not None:
            fighter.effective_av -= _ATTUNED_AV_BONUS
        engine._attuned_bonus_active = False

    # The Indifference: reset corruption damage bonus
    fighter = getattr(getattr(engine, "player", None), "fighter", None)
    if fighter is not None and getattr(fighter, "corruption_damage_bonus", 0) != 0:
        # Only reset if the perk is no longer active
        perks = getattr(getattr(engine, "player", None), "perks", None)
        if perks is None or not perks.has_perk("the_indifference"):
            fighter.corruption_damage_bonus = 0


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
#  The Hollow Road: bone_reader
# ------------------------------------------------------------------ #

def perk_bone_reader_tile_entered(payload: dict) -> dict | None:
    """Bone Reader: butchery always at max yield tier. Effect is checked
    in _interactable_butcher, not here — this handler just marks the
    perk as active so the butcher can read it."""
    return None  # actual effect in butchery handler via perks.has("bone_reader")


# ------------------------------------------------------------------ #
#  The Hollow Road: road_knowledge
# ------------------------------------------------------------------ #

_ROAD_TILES_RK = frozenset(f"road_{i}" for i in range(16)) | {"cobblestone"}

def perk_road_knowledge_tile_entered(payload: dict) -> dict | None:
    """Road Knowledge: road tiles don't consume sprint charges and
    grant +1 accumulator during sprint."""
    engine = payload.get("engine")
    if engine is None:
        return None
    terrain_id = payload.get("terrain_id", "")
    if terrain_id not in _ROAD_TILES_RK:
        return None
    if engine.sprint_turns_remaining > 0:
        # Refund the sprint charge that was consumed
        engine.sprint_turns_remaining += 1
        # Bonus accumulator
        engine.player_move_accumulator += 1.0
    return None


# ------------------------------------------------------------------ #
#  The Green Patience: deep_harvest
# ------------------------------------------------------------------ #

def perk_deep_harvest_tile_entered(payload: dict) -> dict | None:
    """Deep Harvest: 30% chance harvest doesn't deplete. Actual effect
    checked in _try_harvest via perks.has('deep_harvest')."""
    return None  # actual effect in harvest handler


# ------------------------------------------------------------------ #
#  The Green Patience: growth_sense
# ------------------------------------------------------------------ #

def perk_growth_sense_chunk_entered(payload: dict) -> dict | None:
    """Growth Sense: on first chunk entry, highlight harvestable plants."""
    engine = payload.get("engine")
    if engine is None:
        return None
    # Mark nearby harvestable decor with a brief visual pulse
    for (dx, dy), did in engine.local_map.decor.items():
        dentry = engine.data.decoratives.get(did, {})
        if dentry.get("harvestable"):
            if engine.local_map.in_bounds(dx, dy) and engine.local_map.visible[dx, dy]:
                engine.callouts.add("*", float(dx), float(dy) - 0.3,
                                    LIFE_GREEN, lifetime=1.5,
                                    font_size="creature")
    return None


# ------------------------------------------------------------------ #
#  The Bound Name: resonance_sink
# ------------------------------------------------------------------ #

def perk_resonance_sink_turn(payload: dict) -> dict | None:
    """Resonance Sink: exposure decays 50% faster, corruption threshold +0.2."""
    engine = payload.get("engine")
    if engine is None:
        return None
    # Extra decay: base is 0.008/turn, add another 0.004 (50% faster)
    engine.resonance_exposure = max(0.0, engine.resonance_exposure - 0.004)
    return None


# ------------------------------------------------------------------ #
#  The Bound Name: corruption_channel
# ------------------------------------------------------------------ #

def perk_corruption_channel_turn(payload: dict) -> dict | None:
    """Corruption Channel: set flat damage bonus based on corruption level.
    +1 at corruption >= 0.40, +2 at >= 0.70. Applied in _player_attack via
    fighter.corruption_channel_bonus (additive to weapon damage_bonus)."""
    engine = payload.get("engine")
    if engine is None:
        return None
    fighter = getattr(engine.player, "fighter", None)
    if fighter is None:
        return None
    corruption = getattr(engine, "corruption", 0.0)
    if corruption >= 0.70:
        fighter.corruption_channel_bonus = 2
    elif corruption >= 0.40:
        fighter.corruption_channel_bonus = 1
    else:
        fighter.corruption_channel_bonus = 0
    return None


# ------------------------------------------------------------------ #
#  Handler map — must match JSON "handler" field exactly
# ------------------------------------------------------------------ #

HANDLER_MAP: dict[str, callable] = {
    "perk_hardened_step_tile_entered":     perk_hardened_step_tile_entered,
    "perk_carrion_eye_entity_killed":      perk_carrion_eye_entity_killed,
    "handle_marrow_drink_turn":            handle_marrow_drink_turn,
    "handle_attuned_turn":                 handle_attuned_turn,
    "handle_indifference_turn":            handle_indifference_turn,
    "handle_lithic_seep_kill":             handle_lithic_seep_kill,
    "perk_bone_reader_tile_entered":       perk_bone_reader_tile_entered,
    "perk_road_knowledge_tile_entered":    perk_road_knowledge_tile_entered,
    "perk_deep_harvest_tile_entered":      perk_deep_harvest_tile_entered,
    "perk_growth_sense_chunk_entered":     perk_growth_sense_chunk_entered,
    "perk_resonance_sink_turn":            perk_resonance_sink_turn,
    "perk_corruption_channel_turn":         perk_corruption_channel_turn,
}

# Tag all handlers so they can be cleared on perk change without
# accidentally removing non-perk handlers registered by other systems.
for _fn in HANDLER_MAP.values():
    _fn._is_perk_handler = True
