"""Explicit B2 instance fields; definitions and executable hooks are not snapshots.

Additive development-v2 fields. Missing extension blocks mean the B1 defaults;
present blocks are complete versioned records, never partially applied overlays.
Optional additive actor fields retain v1 compatibility and reset when absent.
"""
from __future__ import annotations
import copy
import math
import ast


# name: (default for an absent runtime attribute, validator kind)
ENGINE_STATE = {
    "true_sight_turns": (0, "count"),
    "player_speed_bonus": (0.0, "number"),
    "player_speed_bonus_turns": (0, "count"),
    "_move_debt": (0.0, "number"),
    "rain_collection_progress": (0, "count"),
    "_wraith_overcorrect_turns": (0, "count"),
    "wind_turn": (0, "count"),
    "_last_exposure_tier": (0, "count"),
    "_last_chunk_entry": ((0, 0), "point"),
}
ENGINE_OPTIONAL_STATE = {
    "_weapon_time_balance": (0, "weapon_balance"),
    "_free_move_pending": (False, "bool"),
}
PLAYER_STATE = {
    "chilled_turns": (0, "count"), "_sickness_turns": (0, "count"),
    "_in_concealment": (False, "bool"), "_wraith_warned": (False, "bool"),
}
ACTOR_STATE = {
    "chilled_turns": (0, "count"), "_sickness_turns": (0, "count"),
    "_last_known_px": (None, "coordinate?"), "_last_known_py": (None, "coordinate?"),
    "_arrival_cooldown": (0, "count"), "_just_arrived": (False, "bool"),
    "_pending_stair_use": (None, "string?"),
    "_ability_suppressed_turns": (0, "count"), "_disrupted_turns": (0, "count"),
}
# Additions must not make an existing development-v2/component-v1 record
# unreadable. These fields are validated when present and defaulted on load.
ACTOR_OPTIONAL_STATE = {
    "_wraith_exposure_turns": (0, "count"),
    "_surface_exit_x": (None, "coordinate?"),
    "_surface_exit_y": (None, "coordinate?"),
    "_surface_exit_wx": (None, "coordinate?"),
    "_surface_exit_wy": (None, "coordinate?"),
}
AI_STATE = {
    "target_x": (None, "coordinate?"), "target_y": (None, "coordinate?"),
    "memory_turns": (0, "count"), "alert_memory": (10, "count"),
}
AI_OPTIONAL_STATE = {"sound_interest": (None, "sound?")}
ITEM_STATE = {
    "name": ("", "string"), "tile": ("generic_item", "string"),
    "weight": (0.0, "number"), "stackable": (False, "bool"), "count": (1, "count"),
    "on_use": (None, "string?"), "text_id": ("", "string?"),
    "nutrition": (None, "number?"), "hydration": (None, "number?"),
    "heal_amount": (None, "number?"), "eat_message": (None, "string?"),
    "drink_message": (None, "string?"), "burn_turns": (None, "count?"),
    "turns_lit": (0, "count"), "light_data": (None, "object?"),
    "liquid": (None, "string?"), "liquid_volume": (0.0, "number"),
    "qualities": ({}, "object"), "description": ("", "string"),
    "harvest_from": (None, "string?"), "keywords": ([], "keywords"),
    "decay_timer": (None, "count?"), "source_creature": (None, "string?"),
    "temporary_essence": ([], "coatings"), "consumed_on_use": (True, "bool"),
    "_temp_av_bonus": (0, "number"), "_temp_av_hits": (0, "count"),
}


def _valid(value, kind):
    if kind.endswith("?"):
        return value is None or _valid(value, kind[:-1])
    if kind == "bool":
        return type(value) is bool
    if kind == "sound":
        from config import MAP_WIDTH, MAP_HEIGHT
        from engine.sound import STRENGTH
        return (isinstance(value, dict)
                and set(value) == {'x', 'y', 'deadline', 'strength', 'kind'}
                and type(value['x']) is int and 0 <= value['x'] < MAP_WIDTH
                and type(value['y']) is int and 0 <= value['y'] < MAP_HEIGHT
                and type(value['deadline']) is int and value['deadline'] >= 0
                and type(value['strength']) is int and value['strength'] > 0
                and isinstance(value['kind'], str) and value['kind'] in STRENGTH)
    if kind == "count":
        return type(value) is int and value >= 0
    if kind == "coordinate":
        return type(value) is int
    if kind == "weapon_balance":
        return type(value) is int and -1_000_000 < value < 1_000_000
    if kind == "point":
        return isinstance(value, (list, tuple)) and len(value) == 2 and all(type(v) is int for v in value)
    if kind == "number":
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    if kind == "string":
        return isinstance(value, str)
    if kind == "object":
        return isinstance(value, dict)
    if kind == "strings":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if kind == "keywords":
        return isinstance(value, list) and all(isinstance(v, dict)
            and isinstance(v.get("tag"), str) and _valid(v.get("tier"), "count") for v in value)
    if kind == "coatings":
        return isinstance(value, list) and all(isinstance(v, dict)
            and isinstance(v.get("essence"), str) and _valid(v.get("strength"), "number")
            and _valid(v.get("hits_remaining"), "count") for v in value)
    raise ValueError(kind)


def snapshot(obj, schema):
    return {key: copy.deepcopy(getattr(obj, key, default))
            for key, (default, _) in schema.items()}


def validate_fields(record, schema, label, complete=True):
    if not isinstance(record, dict):
        raise ValueError(f"{label} must be an object")
    for key, (_, kind) in schema.items():
        if key not in record and not complete:
            continue
        if key not in record or not _valid(record[key], kind):
            raise ValueError(f"{label}.{key}: invalid or missing {kind}")


def restore(obj, record, schema):
    for key, (default, _) in schema.items():
        setattr(obj, key, copy.deepcopy(record.get(key, default)))


def validate_block(record, schemas, label):
    if not isinstance(record, dict) or type(record.get("version")) is not int or record["version"] != 1:
        raise ValueError(f"{label}: supported component version is integer 1")
    for key, schema in schemas.items():
        validate_fields(record.get(key), schema, label + "." + key)


def serialize_item(item):
    return {"item_id": item.item_id, "item_state_version": 1, **snapshot(item, ITEM_STATE)}


def validate_item(row, label):
    if "item_state_version" in row:
        if type(row["item_state_version"]) is not int or row["item_state_version"] != 1:
            raise ValueError(label + ": supported item_state_version is integer 1")
        validate_fields(row, ITEM_STATE, label)
    else:
        # B1 used null for an empty coating list. Old rows have no promise for
        # fields they never stored; reconstruct those from the current factory.
        legacy = dict(row)
        if legacy.get("temporary_essence") is None:
            legacy.pop("temporary_essence", None)
        validate_fields(legacy, ITEM_STATE, label, complete=False)


def restore_item(item, row):
    for key in ITEM_STATE:
        if key in row:
            value = row[key]
            if key == "temporary_essence" and value is None:
                value = []
            setattr(item, key, copy.deepcopy(value))


def serialize_runtime(engine):
    state = snapshot(engine, ENGINE_STATE)
    # Neutral additions stay absent, preserving genuine historical fingerprints.
    state.update({key: value for key, value in snapshot(engine, ENGINE_OPTIONAL_STATE).items()
                  if type(value) is not type(ENGINE_OPTIONAL_STATE[key][0])
                  or value != ENGINE_OPTIONAL_STATE[key][0]})
    return {"version": 1, "engine": state,
            "player": snapshot(engine.player, PLAYER_STATE)}


def restore_runtime(engine, data):
    record = data.get("component_state", {})
    restore(engine, record.get("engine", {}), ENGINE_STATE)
    restore(engine, record.get("engine", {}), ENGINE_OPTIONAL_STATE)
    restore(engine.player, record.get("player", {}), PLAYER_STATE)


def validate_components(data):
    if "component_state" in data:
        validate_block(data["component_state"], {"engine": ENGINE_STATE, "player": PLAYER_STATE}, "component_state")
        validate_fields(data["component_state"]["engine"], ENGINE_OPTIONAL_STATE,
                        "component_state.engine", complete=False)
    fighter = data.get("fighter")
    if not isinstance(fighter, dict):
        raise ValueError("fighter must be an object")
    validate_fields(fighter, {key: (0, "number") for key in ("hp", "max_hp", "power", "defense")}, "fighter")
    for key in ("needs", "corruption", "language", "perks", "level", "resonance", "weather"):
        if data.get(key) is not None and not isinstance(data[key], dict):
            raise ValueError(key + " must be an object or null")
    if data.get("needs") is not None:
        validate_fields(data["needs"], {"hunger": (0, "number"), "thirst": (0, "number")}, "needs")
    if data.get("corruption") is not None:
        validate_fields(data["corruption"], {"value": (0, "number")}, "corruption")
        validate_fields(data["corruption"], {"value": (0, "number"), "whisper_cooldown": (0, "count")}, "corruption", complete=False)
    if data.get("perks") is not None:
        validate_fields(data["perks"], {"acquired": ([], "strings"), "perk_state": ({}, "object"), "affinity_scores": ({}, "object")}, "perks")
    if data.get("language") is not None:
        language = data["language"]
        validate_fields(language, {"known_deep_words": ([], "strings"), "translation_events": ({}, "object"),
            "taught_texts": ([], "strings"), "recovered_text": ({}, "object"), "shown_lexicon_hint": (False, "bool")},
            "language", complete=False)
        for key in language.get("recovered_text", {}):
            try:
                parsed = ast.literal_eval(key)
                if not isinstance(parsed, tuple):
                    raise ValueError("not a tuple")
                hash(parsed)
            except (ValueError, SyntaxError, TypeError) as error:
                raise ValueError("language.recovered_text: invalid span key") from error


def serialize_actor_runtime(actor):
    result = {"version": 1, "actor": snapshot(actor, ACTOR_STATE)}
    result["actor"].update(snapshot(actor, ACTOR_OPTIONAL_STATE))
    if getattr(actor, "ai", None) is not None:
        result["ai"] = snapshot(actor.ai, AI_STATE)
        result["ai"].update({k: v for k, v in snapshot(actor.ai, AI_OPTIONAL_STATE).items()
                             if v is not None})
    return result


def validate_actor_runtime(row, local_map=None):
    if "component_state" in row:
        schemas = {"actor": ACTOR_STATE}
        if row.get("ai_type"):
            schemas["ai"] = AI_STATE
        validate_block(row["component_state"], schemas, "actor.component_state")
        validate_fields(row["component_state"]["actor"], ACTOR_OPTIONAL_STATE,
                        "actor.component_state.actor", complete=False)
        if row.get("ai_type"):
            validate_fields(row["component_state"]["ai"], AI_OPTIONAL_STATE,
                            "actor.component_state.ai", complete=False)
            interest = row["component_state"]["ai"].get('sound_interest')
            if (interest is not None and local_map is not None
                    and not local_map.in_bounds(interest['x'], interest['y'])):
                raise ValueError('actor.component_state.ai.sound_interest: source outside owning scene')
        actor_state = row["component_state"]["actor"]
        for x_key, y_key in (("_surface_exit_x", "_surface_exit_y"),
                             ("_surface_exit_wx", "_surface_exit_wy")):
            if (actor_state.get(x_key) is None) != (actor_state.get(y_key) is None):
                raise ValueError("actor.component_state.actor: incomplete " + x_key + "/" + y_key)


def restore_actor_runtime(actor, row):
    record = row.get("component_state", {})
    restore(actor, record.get("actor", {}), ACTOR_STATE)
    restore(actor, record.get("actor", {}), ACTOR_OPTIONAL_STATE)
    if actor.ai is not None:
        restore(actor.ai, record.get("ai", {}), AI_STATE)
        restore(actor.ai, record.get("ai", {}), AI_OPTIONAL_STATE)
