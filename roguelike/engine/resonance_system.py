# engine/resonance_system.py
from __future__ import annotations
import math
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine


# ------------------------------------------------------------------ #
#  Corruption thresholds
# ------------------------------------------------------------------ #

THRESHOLDS = [
    (0.15, "threshold_resonance_sight"),
    (0.25, "threshold_bell_sense"),
    (0.40, "threshold_waystone_glyph"),
    (0.55, "threshold_presence_sense"),
    (0.70, "threshold_deep_tongue"),
    (0.85, "threshold_creature_shift"),
]

_THRESHOLD_MESSAGES = {
    "threshold_resonance_sight":
        "The numbers behind things become legible.",
    "threshold_bell_sense":
        "You hear something before you see it.",
    "threshold_waystone_glyph":
        "The old stones have begun to address you.",
    "threshold_presence_sense":
        "You know when something is close. Even through stone.",
    "threshold_deep_tongue":
        "The deep script is no longer entirely foreign.",
    "threshold_creature_shift":
        "The transformed regard you differently. "
        "Some step aside. Some do not.",
}

# ------------------------------------------------------------------ #
#  Exposure tier thresholds and messages
# ------------------------------------------------------------------ #

_EXPOSURE_TIERS = [
    (0.85, 5, "The discharge is imminent.",
     BLOOD_STONE),       # blood_rose
    (0.65, 4, "Everything hums. Your teeth ache with it.",
     DRIED_BLOOD),        # blood_mid
    (0.45, 3, "The stones are speaking.",
     DUSTY_ROSE),       # dusty_rose
    (0.25, 2, "The resonance is perceptible now.",
     SLATE_MID),     # mist_blue
    (0.10, 1, "The grey stone hums.",
     STONE_BLUE),       # slate_mid
]


# ------------------------------------------------------------------ #
#  System handlers (permanent — registered at engine init)
# ------------------------------------------------------------------ #

def system_resonance_on_turn(payload: dict) -> dict | None:
    engine = payload["engine"]
    effects: dict = {}

    # 1. Exposure decay (suppressed below if near resonant terrain)
    engine.resonance_exposure = max(
        0.0, engine.resonance_exposure - 0.008)

    # 2. Scan local map for resonant terrain within 20 tiles
    nearest_emit, nearest_dist = _scan_resonant_terrain(engine)

    if nearest_emit > 0.0 and nearest_dist <= 20.0:
        # Suppress decay and add exposure based on proximity/strength
        # Undo the decay we already applied
        engine.resonance_exposure = min(
            engine.resonance_exposure + 0.008,
            engine.resonance_exposure + 0.008,
        )
        proximity_factor = 1.0 - (nearest_dist / 20.0)
        exposure_tick    = nearest_emit * proximity_factor * 0.015
        engine.resonance_exposure = min(
            1.5,
            engine.resonance_exposure + exposure_tick,
        )

    # 3. Wind check — cracked bells may partially discharge
    engine.wind_turn += 1
    if engine.wind_turn >= 40:
        engine.wind_turn = 0
        _check_wind_discharge(engine, effects)

    # 4. Corruption conversion at sustained high exposure
    if engine.resonance_exposure >= 0.70:
        old_corruption = engine.corruption
        engine.corruption = min(1.0, engine.corruption + 0.002)
        _check_corruption_thresholds(engine, old_corruption,
                                     engine.corruption, effects)

    # 5. Exposure tier messages — fire only on tier change
    _check_exposure_messages(engine, effects)

    # 6. Weather tick
    weather = getattr(engine, "weather", None)
    if weather is not None:
        result = weather.tick(engine.rng)
        if result and "add_message" not in effects:
            effects["add_message"]   = result[0]
            effects["message_color"] = result[1]

    return effects if effects else None


def system_resonance_on_tile_entered(payload: dict) -> dict | None:
    engine = payload["engine"]
    x      = payload["x"]
    y      = payload["y"]
    effects: dict = {}

    # Check all 8 neighbours of the player's new position
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            tx, ty = x + dx, y + dy
            if not (0 <= tx < engine.map_width and
                    0 <= ty < engine.map_height):
                continue
            terrain_id   = engine.get_terrain(tx, ty)
            terrain_data = engine.data.terrain.get(terrain_id, {})
            bell_state   = terrain_data.get("bell_state")

            if bell_state == "intact":
                from engine.discharge import trigger_discharge
                trigger_discharge(engine, tx, ty, "intact", effects)
                return effects   # one discharge per step

            elif bell_state == "cracked":
                engine.resonance_exposure = min(
                    1.5, engine.resonance_exposure + 0.12)
                if "add_message" not in effects:
                    effects["add_message"] = \
                        "The crack breathes against you."
                    effects["message_color"] = DUSTY_ROSE

    # bone_snow: each step accumulates a small amount of corruption
    weather = getattr(engine, "weather", None)
    if weather and weather.state == "bone_snow":
        corruption_tick = weather.get_mechanic("corruption_per_step", 0.003)
        old_corruption  = engine.corruption
        engine.corruption = min(1.0, engine.corruption + corruption_tick)
        player_corr = getattr(engine.player, "corruption", None)
        if player_corr is not None:
            player_corr.value = engine.corruption
        _check_corruption_thresholds(engine, old_corruption, engine.corruption, effects)

    return effects if effects else None


def system_resonance_chunk_entered(payload: dict) -> dict | None:
    engine = payload["engine"]
    thresholds = getattr(engine, "_corruption_thresholds", set())
    if "threshold_bell_sense" not in thresholds:
        return None

    # Scan incoming chunk terrain for resonant bells
    for ty in range(engine.map_height):
        for tx in range(engine.map_width):
            terrain_id   = engine.get_terrain(tx, ty)
            td           = engine.data.terrain.get(terrain_id, {})
            if td.get("bell_state") in ("intact", "cracked"):
                return {
                    "add_message":   "Something pulls at the edge of hearing.",
                    "message_color": SLATE_MID,
                }
    return None


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def _scan_resonant_terrain(engine: "Engine") -> tuple[float, float]:
    """
    Scan tiles within 20 tiles of the player for resonant terrain.
    Returns (highest_emit, distance_to_that_tile).
    """
    px, py     = engine.player.x, engine.player.y
    best_emit  = 0.0
    best_dist  = 999.0

    for dy in range(-20, 21):
        for dx in range(-20, 21):
            tx, ty = px + dx, py + dy
            if not (0 <= tx < engine.map_width and
                    0 <= ty < engine.map_height):
                continue
            terrain_id   = engine.get_terrain(tx, ty)
            terrain_data = engine.data.terrain.get(terrain_id, {})
            emit = terrain_data.get("resonance_emit", 0.0)
            if emit > 0.0:
                dist = math.sqrt(dx * dx + dy * dy)
                if emit > best_emit or (
                        emit == best_emit and dist < best_dist):
                    best_emit = emit
                    best_dist = dist

    return best_emit, best_dist


def _check_wind_discharge(engine: "Engine", effects: dict) -> None:
    """
    Check cracked bells on the current map.
    Each has a 12% base chance to partially discharge on wind turn.
    dead_calm increases range; resonance_storm increases discharge chance.
    """
    px, py     = engine.player.x, engine.player.y
    discharged = False

    weather = getattr(engine, "weather", None)
    bell_range       = 25 + (weather.get_mechanic("bell_range_bonus", 0) if weather else 0)
    discharge_chance = 0.12 + (weather.get_mechanic("discharge_chance_bonus", 0.0) if weather else 0.0)

    for ty in range(engine.map_height):
        for tx in range(engine.map_width):
            terrain_id   = engine.get_terrain(tx, ty)
            terrain_data = engine.data.terrain.get(terrain_id, {})
            if terrain_data.get("bell_state") != "cracked":
                continue
            dist = math.sqrt((tx - px) ** 2 + (ty - py) ** 2)
            if dist > bell_range:
                continue
            if engine.rng.random() < discharge_chance:
                from engine.discharge import trigger_discharge
                trigger_discharge(engine, tx, ty, "cracked", effects)
                discharged = True
                break
        if discharged:
            break


def _check_corruption_thresholds(
        engine: "Engine",
        old: float,
        new: float,
        effects: dict,
) -> None:
    """Fire once when corruption crosses each named threshold."""
    if not hasattr(engine, "_corruption_thresholds"):
        engine._corruption_thresholds = set()

    # The Indifference perk suppresses threshold messages (mechanical effects still apply)
    _perks = getattr(getattr(engine, "player", None), "perks", None)
    _suppress_messages = _perks is not None and _perks.has_perk("the_indifference")

    for threshold, key in THRESHOLDS:
        if old < threshold <= new:
            if key not in engine._corruption_thresholds:
                engine._corruption_thresholds.add(key)
                if not _suppress_messages:
                    msg = _THRESHOLD_MESSAGES[key]
                    if "add_message" not in effects:
                        effects["add_message"]   = msg
                        effects["message_color"] = DEEP_PURPLE
                    else:
                        # Queue as secondary message — append after flush
                        effects.setdefault("_queued_messages", []).append(
                            (msg, DEEP_PURPLE)
                        )
                # Deep tongue threshold — learn a body word from corruption
                if key == "threshold_deep_tongue":
                    _learn_deep_tongue_from_corruption(engine, effects)


def _check_exposure_messages(engine: "Engine", effects: dict) -> None:
    """Post an exposure tier message only when the tier changes."""
    exposure = engine.resonance_exposure
    tier = 0
    for threshold, t, _msg, _col in _EXPOSURE_TIERS:
        if exposure >= threshold:
            tier = t
            break

    last = getattr(engine, "_last_exposure_tier", 0)
    if tier == last:
        return

    engine._last_exposure_tier = tier

    if tier == 0:
        return   # silent — no message for returning to baseline

    # Find message for this tier
    for threshold, t, msg, col in _EXPOSURE_TIERS:
        if t == tier:
            if "add_message" not in effects:
                effects["add_message"]   = msg
                effects["message_color"] = col
            break


def _learn_deep_tongue_from_corruption(engine: "Engine", effects: dict) -> None:
    """Called when corruption crosses 0.70 — learn a body word."""
    lang = getattr(getattr(engine, "player", None), "language", None)
    if lang is None:
        return
    try:
        from engine.language_system import learn_from_category
        ok, wid = learn_from_category(
            "body", 1, "corruption", lang,
            engine.data.deep_tongue, engine.rng,
        )
        if ok:
            wdef = engine.data.deep_tongue.get(wid, {})
            deep = wdef.get("deep", wid)
            common = wdef.get("common", "")
            lang.translation_events[wid] = engine.world_time.turn
            # Post directly to engine log since effects pipeline may not
            # process additional messages past the threshold message
            engine.log.add(
                f"Something ancient surfaces — [{deep}]: {common}.",
                CORRUPTION_COLOUR,
            )
    except Exception:
        pass  # never crash on learning failure
