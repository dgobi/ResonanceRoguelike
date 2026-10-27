"""Read-only Workbench adapter. Gameplay never imports this module.

The ordinary revenant family exposes only actor name and mirrored HP. Identity,
source shape and immutable data are checked before constructing a disposable Actor.
No turns, world, inventory or save owner is created here.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import PurePosixPath

from engine.creature_factory import CreatureFactory, AI_TYPES
from engine.creature_abilities import ABILITY_REGISTRY
from generation.structure_contract import read_document, StructureError
from rendering.tile_registry import TileRegistry

CONTRACT = "revenant-hp-1"
FIELDS = ["name", "base_hp", "fighter.max_hp"]
HP_MAX = 1_000_000  # Explicit authoring bound, not a gameplay limit.
SCOPE = ("Factory construction only; no AI/combat turns, difficulty measurement, "
         "natural encounter, campaign or saved instance was exercised.")
SELECTION = ("A new definition does not join worldgen pools, replace existing instances, "
             "or change an authored room. Direct layout references are declarations. "
             "spawn_zones is retained metadata, not proof of generator selection.")


def capability(raw, path, pointer=""):
    parts = PurePosixPath(path).parts
    f = raw.get("fighter") if isinstance(raw, dict) else None
    supported = (not pointer and isinstance(raw, dict) and len(parts) >= 5
                 and parts[:4] == ("roguelike", "data", "entities", "creatures")
                 and isinstance(raw.get("id"), str) and raw["id"].casefold() != "player"
                 and raw["id"] not in ABILITY_REGISTRY
                 and raw.get("tile") == "hollow_revenant" and raw.get("ai_type") == "wandering"
                 and isinstance(f, dict) and type(raw.get("base_hp")) is int
                 and type(f.get("max_hp")) is int and raw["base_hp"] == f["max_hp"]
                 and isinstance(raw.get("perception"), dict)
                 and isinstance(raw.get("limbs"), list) and bool(raw["limbs"])
                 and not any(k in raw for k in ("npc", "dialogue", "is_player", "abilities", "effects", "statuses", "spawn_trigger")))
    return dict(contract=CONTRACT, editable=bool(supported), fields=FIELDS, hp_min=1, hp_max=HP_MAX,
                shape="ordinary revenant / mirrored HP" if supported else "unsupported entity shape",
                reason="Ordinary revenant: actor name and effective HP" if supported else
                    "Read-only: requires one ordinary hollow_revenant tile / wandering definition with mirrored HP, outside player/NPC and special-ability contracts.",
                hp_note="CreatureFactory prefers base_hp over fighter.max_hp. This control changes both; Fighter starts hp at max_hp.",
                description_note="Read-only: LookMode resolves descriptions by actor.tile, so a new ID sharing a tile still displays the tile-linked definition's prose.")


def unchanged_data(raw):
    value = copy.deepcopy(raw)
    for key in ("id", "name", "base_hp"):
        value.pop(key, None)
    if isinstance(value.get("fighter"), dict):
        value["fighter"].pop("max_hp", None)
    return value


def same_json(a, b):
    """JSON has one number type, but booleans must never compare equal to 0/1."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_json(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same_json(x, y) for x, y in zip(a, b))
    if type(a) in (int, float) and type(b) in (int, float):
        return a == b
    return type(a) is type(b) and a == b


def source_matches(identifier, sources):
    return [s for key, rows in sources.items() if isinstance(identifier, str) and key.casefold() == identifier.casefold() for s in rows]


def dependencies(raw, data, indexes):
    """Resolve actual registries; faction strings are memberships, not registry IDs."""
    refs = []
    def reference(kind, field, identifier, table, family=None, required=True, note=""):
        matches = source_matches(identifier, indexes.get(family, {})) if family else []
        resolved = isinstance(identifier, str) and identifier in table
        if family:
            resolved = resolved and len(matches) == 1 and matches[0]["definition"] == table[identifier]
            if resolved:
                try:
                    source = read_document(data.root / PurePosixPath(matches[0]["path"]).relative_to("roguelike/data"))
                    if matches[0]["pointer"]:
                        source = source[int(matches[0]["pointer"][1:])]
                    resolved = source == table[identifier]
                except (StructureError, ValueError, KeyError, IndexError):
                    resolved = False
        refs.append(dict(kind=kind, field=field, id=identifier, resolved=resolved, required=required,
                         paths=[s["path"] + s["pointer"] for s in matches], note=note))
    # Strictly check duplicate JSON keys before using the production registry.
    read_document(data.root / "tiles.json")
    reference("Tile registry", "tile", raw.get("tile", "hollow_knight"), TileRegistry(str(data.root / "tiles.json")).all_names())
    inline = isinstance(raw.get("limbs"), list) and bool(raw["limbs"])
    reference("Body fallback", "body_id", raw.get("body_id", "body_human"), data.bodies, "bodies", not inline,
              "Inline limbs take precedence in combat.get_body_def; an unresolved unused fallback is disclosed." if inline else "Factory default is body_human.")
    butcher = raw.get("butcher_yield", {})
    for i, tier in enumerate(butcher.get("tiers", []) if isinstance(butcher, dict) else []):
        for j, entry in enumerate(tier.get("yields", []) if isinstance(tier, dict) else []):
            if isinstance(entry, dict):
                reference("Declared harvest item", f"butcher_yield.tiers[{i}].yields[{j}].item_id", entry.get("item_id"), data.items, "items")
    for i, zone in enumerate(raw.get("spawn_zones", []) if isinstance(raw.get("spawn_zones"), list) else []):
        reference("Spawn-zone declaration", f"spawn_zones[{i}]", zone, data.zones, "zones", False,
                  "No spawn_zones consumer exists in current game Python; zone.creatures and other explicit selectors are separate.")
    return refs


def validate_definition(raw, data, path, indexes, *, original=None, original_path=None, writable=False):
    problems = []
    identifier = raw.get("id") if isinstance(raw, dict) else None
    def issue(code, field, message, severity="error"):
        problems.append(dict(code=code, field=field, message=message, severity=severity, path=path,
                             asset=str(identifier or ""), correction="Repair the source/reference or use a supported new-ID creature variant."))
    if not isinstance(raw, dict) or not isinstance(identifier, str) or not identifier:
        issue("CREATURE_ID", "id", "Expected a creature object with a nonempty ID.")
        return problems, []
    matches = source_matches(identifier, indexes["entities"])
    if len(matches) != 1:
        issue("DUPLICATE_CREATURE", "id", "Ambiguous entity ID, including case collisions: " + ", ".join(s["path"] + s["pointer"] for s in matches))
    if data.entities.get(identifier) != raw or not any(s["path"] == path and s["definition"] == raw for s in matches):
        issue("LOADER_IDENTITY", "id", "DataLoader did not load this exact source definition.")
    if identifier.casefold() == "player":
        issue("PLAYER_DEFINITION", "id", "Player definitions are outside creature construction and publication.")
        return problems, []
    if writable:
        if not isinstance(original, dict) or not capability(original, original_path or "")["editable"]:
            issue("UNSUPPORTED_SOURCE", "", "Original source identity/shape does not grant creature authoring.")
        if not capability(raw, path)["editable"]:
            issue("UNSUPPORTED_CREATURE", "", capability(raw, path)["reason"])
        if isinstance(original, dict) and not same_json(unchanged_data(raw), unchanged_data(original)):
            issue("READ_ONLY_FIELD", "", "Only id (new variant), name, base_hp and fighter.max_hp may change. All complex/unknown data and description are read-only.")
    if not isinstance(raw.get("name"), str) or not 1 <= len(raw["name"]) <= 256:
        issue("CREATURE_NAME", "name", "Actor name requires 1–256 literal characters.")
    f = raw.get("fighter", {})
    if not isinstance(f, dict):
        issue("CREATURE_FIELD", "fighter", "Expected a fighter object."); f = {}
    hp = raw.get("base_hp", f.get("max_hp", 10))
    if type(hp) is not int or not 1 <= hp <= HP_MAX:
        issue("CREATURE_HP", "base_hp", f"Effective HP must be an integer from 1 to {HP_MAX}; this is an authoring bound.")
    for field, value in (("fighter.power", f.get("power", 3)), ("fighter.defense", f.get("defense", 0)), ("armour_value", raw.get("armour_value", 0))):
        if type(value) is not int or not 0 <= value <= HP_MAX:
            issue("CREATURE_FIELD", field, "Expected a bounded nonnegative integer for factory inspection.")
    if not isinstance(raw.get("ai_type", "wandering"), str) or raw.get("ai_type", "wandering") not in AI_TYPES:
        issue("CREATURE_AI", "ai_type", "Unknown AI type; factory fallback does not establish supported behavior.")
    perception = raw.get("perception", {})
    if not isinstance(perception, dict):
        issue("CREATURE_FIELD", "perception", "Expected a perception object.")
    elif perception:
        for key, default in (("sight_radius", 8), ("hearing_radius", 5)):
            value = perception.get(key, default)
            if type(value) is not int or not 0 <= value <= 1000:
                issue("CREATURE_FIELD", "perception." + key, "Expected an integer radius from 0 to 1000 for bounded inspection.")
        if type(perception.get("sees_in_dark", False)) is not bool or not isinstance(perception.get("faction", "hostile"), str):
            issue("CREATURE_FIELD", "perception", "Expected boolean sees_in_dark and literal string faction.")
        hostile = perception.get("hostile_to", ["player"])
        if not isinstance(hostile, list) or any(not isinstance(v, str) for v in hostile):
            issue("CREATURE_FIELD", "perception.hostile_to", "Expected a list of faction strings.")
    wander = raw.get("wander_radius", 8)
    if type(wander) is not int or not 0 <= wander <= 1000:
        issue("CREATURE_FIELD", "wander_radius", "Expected an integer radius from 0 to 1000 for bounded inspection.")
    refs = dependencies(raw, data, indexes)
    for ref in refs:
        if not ref["resolved"]:
            issue("UNKNOWN_REFERENCE", ref["field"], f"Missing or ambiguous {ref['kind']}: {ref['id']!r}. " + ", ".join(ref["paths"]) + " " + ref["note"],
                  "error" if ref["required"] else "warning")
    return problems, refs


def direct_references(data, identifier):
    refs = []
    for entry in data.structure_catalog.entries:
        if entry.route != "authored_submap":
            continue
        for i, row in enumerate(entry.definition.get("special_tiles", [])):
            if row.get("type", row.get("kind")) == "creature" and row.get("creature_id") == identifier:
                refs.append(dict(id=entry.definition["id"], path="roguelike/data/" + PurePosixPath(str(entry.path).replace("\\", "/")).relative_to(PurePosixPath(data.root.as_posix())).as_posix(),
                                 field=f"special_tiles[{i}].creature_id", route=entry.route, x=row["x"], y=row["y"],
                                 evidence="Declared direct authored-submap reference; no natural selection or live encounter observed."))
    return refs


def factory_preview(raw, data):
    actor = CreatureFactory(data).spawn(raw["id"], 0, 0)
    if actor is None or actor.fighter is None:
        raise ValueError("CreatureFactory did not construct an Actor/Fighter.")
    f = actor.fighter
    effective = raw.get("base_hp", raw.get("fighter", {}).get("max_hp", 10))
    if actor._creature_id != raw["id"] or actor.name != raw.get("name", raw["id"]) or f.hp != effective or f.max_hp != effective:
        raise ValueError("Factory result does not match source identity/name/effective HP.")
    p = actor.perception
    return dict(creature_id=actor._creature_id, actor_class=type(actor).__module__ + "." + type(actor).__name__,
                instance=dict(name=actor.name, tile=actor.tile, blocks_movement=actor.blocks_movement,
                              fighter=dict(hp=f.hp, max_hp=f.max_hp, power=f.power, defense=f.defense, body_id=f.body_id, limbs=f.body_limbs, armour_value=f.effective_av),
                              perception=None if p is None else dict(sight_radius=p.sight_radius, hearing_radius=p.hearing_radius, sees_in_dark=p.sees_in_dark, faction=p.faction, hostile_to=p.hostile_to),
                              ai_class=type(actor.ai).__name__, inventory=actor.inventory),
                comparisons=[dict(field="name → Actor.name", declared=raw.get("name"), instance=actor.name),
                             dict(field="base_hp → Fighter.max_hp / hp", declared=raw.get("base_hp"), instance=f.max_hp),
                             dict(field="fighter.max_hp (fallback, shadowed by base_hp)", declared=raw.get("fighter", {}).get("max_hp"), instance=f.hp)],
                definition_semantic_sha256=hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                consumer="engine.data_loader.DataLoader → engine.creature_factory.CreatureFactory.spawn → Actor / Fighter / Perception / AI",
                contract=CONTRACT, scope=SCOPE)
