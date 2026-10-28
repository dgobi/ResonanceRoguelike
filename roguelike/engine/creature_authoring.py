"""Source-bound common Actor authoring; gameplay never imports this adapter.

Construction, editing authority and special behavior identity are separate facts.
Only the original verified source grants authority; candidates never promote it.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from engine.creature_factory import CreatureFactory, AI_TYPES
from engine.creature_abilities import ABILITY_REGISTRY
from generation.structure_contract import read_document, StructureError
from rendering.tile_registry import TileRegistry

CONTRACT = "creature-common-1"
HP_MAX = 1_000_000
FIELDS = ["name", "description", "base_hp", "fighter.max_hp", "armour_value", "damage_dice",
          "damage_bonus", "attack_verb", "perception.sight_radius", "perception.sees_in_dark",
          "wander_radius", "pursuit_timeout", "speed"]
BOUNDS = {"base_hp": (1, HP_MAX), "fighter.max_hp": (1, HP_MAX), "armour_value": (0, HP_MAX),
          "damage_bonus": (-1000, 1000), "perception.sight_radius": (0, 1000),
          "wander_radius": (0, 1000), "pursuit_timeout": (0, 10000), "speed": (0.01, 2)}
SCOPE = "Factory construction only; no AI/combat turns, balance, natural encounter, campaign or saved instance was exercised."
LIMITATIONS = SCOPE
SELECTION = ("spawn_zones is retained inactive metadata. Zone creature lists and saved authored-submap placements "
             "are separate inbound declarations, not observed encounters or proof of natural world selection. Saving a variant enrolls it nowhere.")
PUBLICATION_NOTE = ("Changes load at the next game launch/catalogue initialization. Saved actors retain stored name, HP, "
                    "armour, sight/darkvision and wander radius. Description, attack, speed and pursuit use the current "
                    "definition. HP edits do not rescale injured saves. New actors receive current constructor values; variants require explicit placement.")
VIEWS = ["creature-properties", "creature-references", "creature-factory"]
# This registered specialist uses exact-source paths and shared document commands.
SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "required": ["id"], "properties": {
    "id": {"type": "string", "title": "Stable creature ID", "readOnly": True},
    "name": {"type": "string", "title": "Name"},
    "description": {"type": "string", "title": "Description", "x-control": "multiline", "default": ""},
    "damage_dice": {"type": "string", "title": "Attack dice", "default": "1d4"},
    "attack_verb": {"type": "string", "title": "Attack verb", "default": "strikes at thee"},
    "ai_type": {"type": "string", "title": "AI (ordinary new variant only)", "readOnly": True},
    **{k: {"type": "number" if k == "speed" else "integer", "minimum": lo, "maximum": hi}
       for k, (lo, hi) in BOUNDS.items() if "." not in k}}}


def same_json(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_json(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same_json(x, y) for x, y in zip(a, b))
    if type(a) in (int, float) and type(b) in (int, float): return a == b
    return type(a) is type(b) and a == b


def source_matches(identifier, sources):
    return [s for key, rows in sources.items() if isinstance(identifier, str) and key.casefold() == identifier.casefold() for s in rows]


def indexes_for(data_root):
    from engine.content_authoring import definition_sources
    return {family: definition_sources(data_root, family) for family in ("entities", "items", "bodies", "zones")}


def capability(raw, path, pointer=""):
    raw = raw if isinstance(raw, dict) else {}
    identifier = raw.get("id"); player = isinstance(identifier, str) and identifier.casefold() == "player"
    f, p, limbs = raw.get("fighter"), raw.get("perception"), raw.get("limbs")
    shape = (isinstance(identifier, str) and bool(identifier) and not player
             and isinstance(f, dict) and isinstance(p, dict) and bool(p)
             and isinstance(raw.get("limbs", []), list) and ("body_id" not in raw or isinstance(raw["body_id"], str))
             and not any(k in raw for k in ("npc", "dialogue", "is_player", "abilities", "effects", "statuses", "spawn_trigger")))
    writable_path = PurePosixPath(path).parts[:4] == ("roguelike", "data", "entities", "creatures")
    editable = bool(shape and writable_path and not pointer)
    special = isinstance(identifier, str) and identifier in ABILITY_REGISTRY
    reason = ("Common Actor fields; identity-bound special behavior is preserved." if special else
              "Common Actor fields; same-ID edits and ordinary new-ID variants.") if editable else (
                  "Player/NPC definitions are outside the creature authoring contract." if player or any(k in raw for k in ("npc", "dialogue", "is_player")) else
                  "Non-Actor configuration: consumed by the vine system, not Actor authoring." if "spawn_trigger" in raw else
                  "Read-only: unsupported component shape, array source or source outside entities/creatures.")
    return dict(contract=CONTRACT, inspectable=True, constructible=bool(shape), editable=editable,
                duplicable=editable and not special, operations=(["edit"] if special else ["edit", "variant"]) if editable else [],
                fields=FIELDS, bounds=BOUNDS, ai_types=list(AI_TYPES), hp_min=1, hp_max=HP_MAX,
                shape="Actor with ID-bound behavior" if special else "ordinary Actor" if shape else "unsupported entity shape",
                reason=reason, special_binding=identifier if special else None,
                duplication_reason="Duplication unavailable: ABILITY_REGISTRY dispatches by stable ID; a new ID would lose this behavior." if special else "",
                body_note="Body supplied by inline limbs" if isinstance(limbs, list) and limbs else "Body supplied by body_id dependency",
                hp_note="One atomic edit keeps base_hp and fighter.max_hp equal. New Fighter starts at maximum HP.",
                description_note="Description and creature knowledge use stable definition identity; tile remains presentation only.")


def unchanged_data(raw, *, variant=False):
    value = copy.deepcopy(raw)
    for field in FIELDS + (["id", "ai_type"] if variant else []):
        parts = field.split("."); parent = value
        for part in parts[:-1]: parent = parent.get(part, {}) if isinstance(parent, dict) else {}
        if isinstance(parent, dict): parent.pop(parts[-1], None)
    return value


def authorize_candidate(original, candidate, source_path, target_path):
    cap = capability(original, source_path); variant = source_path != target_path; problems = []
    def issue(code, message):
        problems.append(dict(code=code, severity="error", path=target_path, asset=str(candidate.get("id", "")) if isinstance(candidate, dict) else "",
                             field="", message=message, correction="Restore protected source values; use an operation allowed by the original source."))
    if not cap["editable"]: issue("SOURCE_ENTITLEMENT", cap["reason"])
    if not isinstance(candidate, dict): return problems
    if variant:
        if not cap["duplicable"]: issue("OPERATION_POLICY", cap["duplication_reason"] or "Original source cannot grant variant authority.")
        identifier = candidate.get("id")
        if (not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identifier)
                or identifier.casefold() == str(original.get("id", "")).casefold()
                or PurePosixPath(target_path).name != identifier + ".json"
                or PurePosixPath(target_path).parent != PurePosixPath(source_path).parent):
            issue("VARIANT_ID", "A variant needs a different safe ID and matching file beside its source.")
        if isinstance(identifier, str) and identifier in ABILITY_REGISTRY: issue("SPECIAL_ID", "An ordinary variant cannot acquire an ID-bound special ability.")
    elif candidate.get("id") != original.get("id"): issue("IDENTITY_CHANGE", "Same-ID edits retain the exact stable identity.")
    if not same_json(unchanged_data(original, variant=variant and cap["duplicable"]), unchanged_data(candidate, variant=variant and cap["duplicable"])):
        issue("READ_ONLY_FIELD", "Only supported common fields may change; identity, tile, components and special/unknown settings remain exact. AI may change only for an ordinary new variant.")
    return problems


def dependencies(raw, data, indexes):
    refs = []
    def reference(kind, field, identifier, table, family=None, required=True, note="", active=True):
        matches = source_matches(identifier, indexes.get(family, {})) if family else []
        resolved = isinstance(identifier, str) and identifier in table
        if family:
            resolved = resolved and len(matches) == 1 and same_json(matches[0]["definition"], table[identifier])
            if resolved:
                try:
                    source = read_document(data.root / PurePosixPath(matches[0]["path"]).relative_to("roguelike/data"))
                    if matches[0]["pointer"]: source = source[int(matches[0]["pointer"][1:])]
                    resolved = same_json(source, table[identifier])
                except (StructureError, ValueError, KeyError, IndexError): resolved = False
        refs.append(dict(kind=kind, field=field, id=identifier, resolved=resolved, required=required, active=active,
                         paths=[s["path"] + s["pointer"] for s in matches], note=note))
    read_document(data.root / "tiles.json")
    reference("Presentation tile", "tile", raw.get("tile", "hollow_knight"), TileRegistry(str(data.root / "tiles.json")).all_names())
    inline = isinstance(raw.get("limbs"), list) and bool(raw["limbs"])
    reference("Unused body fallback" if inline else "Active body dependency", "body_id", raw.get("body_id", "body_human"), data.bodies, "bodies", not inline,
              ("Authored body_id" if "body_id" in raw else "Absent body_id; factory implicitly supplies body_human") +
              (". Inline limbs take precedence in combat.get_body_def; this fallback is unused." if inline else ". Required by combat.get_body_def."), active=not inline)
    butcher = raw.get("butcher_yield", {})
    tiers = butcher.get("tiers", []) if isinstance(butcher, dict) else []
    for i, tier in enumerate(tiers if isinstance(tiers, list) else []):
        yields = tier.get("yields", []) if isinstance(tier, dict) else []
        for j, entry in enumerate(yields if isinstance(yields, list) else []):
            if isinstance(entry, dict): reference("Harvest item", f"butcher_yield.tiers[{i}].yields[{j}].item_id", entry.get("item_id"), data.items, "items")
    for i, zone in enumerate(raw.get("spawn_zones", []) if isinstance(raw.get("spawn_zones"), list) else []):
        reference("Retained inactive metadata", f"spawn_zones[{i}]", zone, data.zones, "zones", False,
                  "No current runtime Python consumer. Actual zone population reads zone.creatures via CreatureFactory.spawn_for_zone.", active=False)
    return refs


def validate_definition(raw, data, path, indexes):
    problems = []; identifier = raw.get("id") if isinstance(raw, dict) else None
    def issue(code, field, message, severity="error", correction="Correct the named field/reference; the exact draft is retained."):
        problems.append(dict(code=code, field=field, message=message, severity=severity, path=path, asset=str(identifier or ""), correction=correction))
    if not isinstance(raw, dict) or not isinstance(identifier, str) or not identifier:
        issue("CREATURE_ID", "id", "Expected an entity object with a nonempty ID."); return problems, []
    matches = source_matches(identifier, indexes["entities"])
    if len(matches) != 1: issue("DUPLICATE_CREATURE", "id", "Ambiguous complete entity namespace: " + ", ".join(s["path"] + s["pointer"] for s in matches))
    if not same_json(data.entities.get(identifier), raw) or not any(s["path"] == path and same_json(s["definition"], raw) for s in matches):
        issue("LOADER_IDENTITY", "id", "DataLoader did not load this exact source definition.")
    cap = capability(raw, path)
    if not cap["constructible"]:
        issue("INSPECTION_ONLY", "", cap["reason"], "info", "Inspect Source; this shape has no creature construction/edit authority."); return problems, []
    def integer(field, value, lo, hi, code="CREATURE_FIELD"):
        if type(value) is not int or not lo <= value <= hi: issue(code, field, f"Expected an integer from {lo} to {hi}; booleans are not numbers.")
    for key, lo, hi, default in (("name", 1, 256, identifier), ("description", 0, 8192, ""), ("attack_verb", 1, 256, "strikes at thee")):
        value = raw.get(key, default)
        if not isinstance(value, str) or not lo <= len(value) <= hi: issue("CREATURE_TEXT", key, f"Expected {lo}–{hi} literal characters.")
    if raw.get("name") == "Player": issue("RESERVED_NAME", "name", "Player is reserved by snapshot and renderer identity paths.")
    f, p = raw["fighter"], raw["perception"]
    hp = raw.get("base_hp", f.get("max_hp", 10)); integer("base_hp", hp, 1, HP_MAX, "CREATURE_HP")
    integer("fighter.max_hp", f.get("max_hp", hp), 1, HP_MAX, "CREATURE_HP")
    if not same_json(hp, f.get("max_hp", hp)): issue("CREATURE_HP", "fighter.max_hp", "base_hp and fighter.max_hp must agree.")
    for key, default in (("armour_value", 0), ("damage_bonus", 0), ("wander_radius", 8), ("pursuit_timeout", 20)):
        integer(key, raw.get(key, default), *BOUNDS[key])
    for key, default in (("power", 3), ("defense", 0)): integer("fighter." + key, f.get(key, default), 0, HP_MAX)
    for key, default in (("sight_radius", 8), ("hearing_radius", 5)): integer("perception." + key, p.get(key, default), 0, 1000)
    if type(p.get("sees_in_dark", False)) is not bool: issue("CREATURE_FIELD", "perception.sees_in_dark", "Expected a boolean.")
    if not isinstance(p.get("faction", "hostile"), str) or not isinstance(p.get("hostile_to", ["player"]), list) or any(not isinstance(v, str) for v in p.get("hostile_to", [])):
        issue("CREATURE_FIELD", "perception", "Faction is a string; hostile_to is a list of strings.")
    ai = raw.get("ai_type", "wandering")
    if not isinstance(ai, str) or ai not in AI_TYPES: issue("CREATURE_AI", "ai_type", "Choose an existing registered AI class; fallback is not validated behavior.")
    speed = raw.get("speed", 1.0)
    if type(speed) not in (int, float) or not math.isfinite(speed) or not 0.01 <= speed <= 2:
        issue("CREATURE_SPEED", "speed", "Speed must be finite from 0.01 to 2; scheduling supports at most two actions per turn.")
    dice = raw.get("damage_dice", "1d4"); match = re.fullmatch(r"([1-9][0-9]?)d([1-9][0-9]{0,2})", dice) if isinstance(dice, str) else None
    if not match or not 1 <= int(match[1]) <= 20 or not 1 <= int(match[2]) <= 100:
        issue("CREATURE_DICE", "damage_dice", "Use strict NdM: count 1–20, sides 1–100, lowercase d; addition belongs in damage bonus.")
    limbs = raw.get("limbs", [])
    if not isinstance(limbs, list) or len(limbs) > 64 or any(not isinstance(v, dict) or not isinstance(v.get("id"), str)
            or type(v.get("size")) not in (int, float) or not 0 < v["size"] <= 1000
            or type(v.get("damage_multiplier", 1)) not in (int, float) or not 0 <= v.get("damage_multiplier", 1) <= 1000 for v in limbs):
        issue("CREATURE_BODY", "limbs", "Unsupported inline body shape; inspect and repair outside common-field controls.")
    butcher = raw.get("butcher_yield", {})
    if (not isinstance(butcher, dict) or not isinstance(butcher.get("tiers", []), list)
            or any(not isinstance(tier, dict) or not isinstance(tier.get("yields", []), list)
                   or any(not isinstance(entry, dict) or not isinstance(entry.get("item_id"), str)
                          for entry in tier.get("yields", [])) for tier in butcher.get("tiers", []))):
        issue("CREATURE_HARVEST", "butcher_yield", "Unsupported harvest reference shape; inspect and repair outside common-field controls.")
    refs = dependencies(raw, data, indexes)
    for ref in refs:
        if not ref["active"]: issue("INACTIVE_REFERENCE", ref["field"], ref["note"], "info", "Retained as authored; no repair is needed for an unused dependency.")
        elif not ref["resolved"]: issue("UNKNOWN_REFERENCE", ref["field"], f"Missing or ambiguous {ref['kind']}: {ref['id']!r}. " + ", ".join(ref["paths"]), "error" if ref["required"] else "warning")
    for zone in {r["id"] for r in refs if r["field"].startswith("spawn_zones[") and isinstance(r["id"], str)}:
        matches = source_matches(zone, indexes["zones"])
        if len(matches) > 1: issue("DUPLICATE_ZONE", "spawn_zones", f"Catalogue has ambiguous zone {zone!r}: " + ", ".join(s["path"] for s in matches), "warning", "Resolve the duplicate zone definition; spawn_zones does not select encounters.")
    return problems, refs


def direct_references(data, identifier):
    refs = []
    for entry in data.structure_catalog.entries:
        if entry.route != "authored_submap": continue
        for i, row in enumerate(entry.definition.get("special_tiles", [])):
            if row.get("type", row.get("kind")) == "creature" and row.get("creature_id") == identifier:
                refs.append(dict(id=entry.definition["id"], path="roguelike/data/" + PurePosixPath(str(entry.path).replace("\\", "/")).relative_to(PurePosixPath(data.root.as_posix())).as_posix(),
                                 field=f"special_tiles[{i}].creature_id", route=entry.route, x=row["x"], y=row["y"],
                                 evidence="Saved authored-submap placement: create_submap constructs this ID at the declared cell. No observed encounter or natural selection claimed."))
    for rows in indexes_for(data.root)["zones"].values():
        for source in rows:
            entries = source["definition"].get("creatures", [])
            for i, row in enumerate(entries if isinstance(entries, list) else []):
                if isinstance(row, dict) and row.get("id") == identifier:
                    refs.append(dict(id=source["definition"]["id"], path=source["path"], field=f"creatures[{i}].id", route="zone_creatures",
                                     evidence="Active declaration: spawn_for_zone checks each entry's chance in order, searches eligible terrain, and caps count. weight is not used by this consumer. No natural zone selection or observed encounter is established."))
    return refs


def factory_preview(raw, data):
    actor = CreatureFactory(data).spawn(raw["id"], 0, 0)
    if actor is None or actor.fighter is None: raise ValueError("CreatureFactory did not construct an Actor/Fighter.")
    f, p = actor.fighter, actor.perception
    return dict(creature_id=actor._creature_id, actor_class=type(actor).__module__ + "." + type(actor).__name__,
                special_binding=actor._creature_id if actor._creature_id in ABILITY_REGISTRY else None, ability_executed=False,
                body="Body supplied by inline limbs" if f.body_limbs else f.body_id,
                instance=dict(name=actor.name, tile=actor.tile, blocks_movement=actor.blocks_movement,
                    fighter=dict(hp=f.hp, max_hp=f.max_hp, power=f.power, defense=f.defense, body_id=f.body_id, limbs=f.body_limbs, armour_value=f.effective_av),
                    perception=None if p is None else dict(sight_radius=p.sight_radius, hearing_radius=p.hearing_radius, sees_in_dark=p.sees_in_dark, faction=p.faction, hostile_to=p.hostile_to),
                    ai_class=type(actor.ai).__name__, wander_radius=actor.ai.wander_radius, inventory=actor.inventory),
                definition_values={k: raw.get(k, default) for k, default in (("description", ""), ("damage_dice", "1d4"), ("damage_bonus", 0), ("attack_verb", "strikes at thee"), ("speed", 1), ("pursuit_timeout", 20))},
                comparisons=[dict(field="name → Actor.name", declared=raw.get("name"), instance=actor.name), dict(field="base_hp → Fighter.max_hp / hp", declared=raw.get("base_hp"), instance=f.max_hp), dict(field="armour_value → natural armour", declared=raw.get("armour_value", 0), instance=f.effective_av)],
                definition_semantic_sha256=hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                consumer="DataLoader → CreatureFactory.spawn → Actor / Fighter / Perception / AI", contract=CONTRACT, scope=SCOPE)


def authoring_context(raw, data, path, data_root, identity, digest, *, observe=False):
    records = []; indexes = indexes_for(data_root)
    for index, definition in enumerate(raw if isinstance(raw, list) else [raw]):
        if not isinstance(definition, dict): continue
        pointer = f"/{index}" if isinstance(raw, list) else ""; cap = capability(definition, path, pointer)
        try: diagnostics, refs = validate_definition(definition, data, path, indexes)
        except StructureError as error: diagnostics, refs = [d.json() for d in error.diagnostics], []
        if any(d["severity"] == "error" for d in diagnostics):
            cap.update(editable=False, duplicable=False, constructible=False, operations=[], reason="Invalid or ambiguous source: see the specific diagnostics; Source remains inspectable.")
        observed = None
        if observe and cap["constructible"]:
            try:
                observed = {**factory_preview(definition, data), "source": identity, "path": path, "source_sha256": digest,
                            "loaded_catalog_sha256": data.structure_catalog.identity, "observed_at_utc": datetime.now(timezone.utc).isoformat()}
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                diagnostics.append(dict(code="CREATURE_FACTORY", severity="error", path=path, asset=str(definition.get("id", "")), field="", message=str(error), correction="Repair unsupported constructor fields outside common-field editing."))
                cap.update(editable=False, duplicable=False, constructible=False, operations=[])
        records.append(dict(id=definition.get("id", ""), pointer=pointer, definition=definition, capability=cap, diagnostics=diagnostics,
                            dependencies=refs, factory=observed, references=direct_references(data, definition.get("id"))))
    return dict(records=records, selection=SELECTION)


def authoring_validate(raw, data, path, data_root):
    return validate_definition(raw, data, path, indexes_for(data_root))[0]


def authoring_evidence(context):
    observed = context["records"][0]["factory"] if context and len(context["records"]) == 1 else None
    return dict(semantic_verified=bool(observed), factory_verified=bool(observed), factory=observed)


def reference_options(context):
    return {"ai_types": [dict(id=k, label=cls.__name__) for k, cls in AI_TYPES.items()]}
