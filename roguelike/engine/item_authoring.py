"""Source-bound supplies authoring contract; never imported by gameplay.

The factory, persisted instance schema and crafting predicates own semantics.
This deliberately narrow capability adds reference/identity checks to the loader's
permissive input. It does not change loading, use, inventory ownership or saves.
"""
from __future__ import annotations
import inspect
import hashlib
import math
from pathlib import PurePosixPath
from engine.item_factory import ItemFactory
from engine.item_system import ItemSystem
from engine.save_components import ITEM_STATE, snapshot, validate_fields
from engine.crafting import _item_has_tag, _item_has_all_tags
from rendering.tile_registry import TileRegistry

CONTRACT = "usable-supplies-1"
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "required": ["id"],
    "properties": {
        "id": {"type": "string", "title": "Item ID", "readOnly": True},
        "name": {"type": "string", "title": "Item name", "description": "When absent, the factory uses this item's ID as its name."},
        "description": {"type": "string", "title": "Item description", "x-control": "multiline", "default": ""},
        "tile": {"type": "string", "title": "Existing tile", "x-reference": "tiles", "default": "generic_item"},
        "weight": {"type": "number", "title": "Item weight (kg)", "minimum": 0, "default": 0.1},
        "stackable": {"type": "boolean", "title": "Group in inventory", "default": False,
                      "description": "Groups same-ID instances in inventory display. Instances and carried weights remain separate."},
        "consumed_on_use": {"type": "boolean", "title": "Eligible for automatic ingredient selection", "default": True,
                            "description": "Enabled by default when absent. Disable to require an explicit material choice before crafting can spend this item. Recipe roles determine whether selected instances are consumed or retained; this does not change ordinary item-use disposal."},
        "keywords": {"type": "array", "title": "Keywords", "x-control": "ordered-table", "items": {
            "type": "object", "required": ["tag", "tier"], "properties": {
                "tag": {"type": "string", "title": "Keyword", "x-reference": "keywords"},
                "tier": {"type": "integer", "title": "Keyword tier", "minimum": 0, "maximum": 2**53-1, "x-initial": 1}}}},
        "nutrition": {"type": "number", "title": "Stored nutrition", "minimum": 0, "x-view": "food", "description": "Absent/null uses 300. Values at or below 1 are fractions; above 1 divide by saved hunger maximum. Whole item used, even at zero."},
        "eat_message": {"type": "string", "title": "Food use message", "x-control": "multiline", "x-view": "food", "description": "Absent/null/empty uses the ordinary generated message."},
        "hydration": {"type": "number", "title": "Stored hydration", "minimum": 0, "x-view": "drink", "description": "Absent/null uses 400. Values at or below 1 are fractions; above 1 divide by saved thirst maximum. Whole item used, even at zero."},
        "drink_message": {"type": "string", "title": "Drink use message", "x-control": "multiline", "x-view": "drink", "description": "Absent/null/empty uses the ordinary generated message."},
        "empty_form": {"type": "string", "title": "Return item", "x-reference": "return-items", "x-view": "drink", "description": "Absent/null/empty means no replacement. Exchange precedes hydration. A returned object is not automatically refillable; the canonical empty skin fills into canonical water_skin."},
        "heal_amount": {"type": "integer", "title": "Treatment healing", "minimum": 1, "maximum": 2**53-1, "x-view": "treatment", "description": "Absent/null uses 3 HP, limited by missing HP. Legacy zero also falls back to 3; new authored zero is rejected. Failed treatment retains its item and costs no turn."},
    },
}
VIEWS = ["item-properties", "references", "recipes", "use-binding", "factory"]
PUBLICATION_NOTE = "Save/reopen each supply first, then reference its saved ID in a room or pool. Saving does not enroll it in loot, harvesting, gathering or crafting. Later construction uses saved definitions; versioned owned instances retain copied fields. A running game keeps its catalogue; empty_form is read from that session's definition at use."


def reference_options(context):
    return {"keywords": [dict(id=k, label=k) for k in sorted(context["keywords"])],
            "tiles": [dict(id=k,label=k) for k in context["tiles"]],
            "return-items": [dict(id="",label="No replacement")] + context["return_items"]}


def authoring_validate(raw, data, path, data_root):
    return validate_definition(raw, data, path, definition_sources(data_root, "items"), writable=True)


def authoring_evidence(context):
    observed = context["records"][0]["factory"] if context else None
    return dict(semantic_verified=bool(observed), factory_verified=bool(observed), factory=observed)


LIMITATIONS = "Exact staged bytes loaded and an unowned item instantiated by the actual factory. No use action, pool sampling, world selection or saved instance changed."
FIELDS = ["name", "description", "tile", "weight", "stackable", "keywords", "consumed_on_use"]
CLASS_FIELDS = {"material": [], "food": ["nutrition", "eat_message"],
                "drink": ["hydration", "drink_message", "empty_form"], "treatment": ["heal_amount"]}
# Known runtime-bearing fields outside an ordinary inert component. Unknown
# metadata is retained; none is promoted to a supported mechanical control.
ADVANCED = (set(ITEM_STATE) - set(FIELDS) - {
    "on_use", "count", "text_id", "qualities", "nutrition", "hydration", "heal_amount",
    "eat_message", "drink_message", "harvest_from", "liquid", "liquid_volume"
}) | {"slot", "movesets", "on_use_effects", "damage_dice", "damage_bonus",
      "essence", "essence_strength", "crit_chance", "weight_reductions",
      "provides_burning", "light", "light_radius", "render_mode",
      "zone_radius", "zone_turns", "effects", "status", "statuses"}


def capability(raw, path, pointer=""):
    parts = PurePosixPath(path).parts
    kind = {None: "material", "eat": "food", "drink": "drink", "heal_minor": "treatment"}.get(raw.get("on_use")) if isinstance(raw,dict) and isinstance(raw.get("on_use"), (str,type(None))) else None
    route = parts[3] if len(parts)>=5 else ""
    protected = isinstance(raw,dict) and (str(raw.get("id", "")).casefold()=="empty_water_skin" or PurePosixPath(path).stem.casefold()=="empty_water_skin")
    supported = (not pointer and isinstance(raw, dict) and len(parts) >= 5
                 and parts[:3] == ("roguelike", "data", "items") and route in ("components", "butchery", "consumables")
                 and raw.get("category") == {"components":"component","butchery":"butchery","consumables":"consumable"}[route]
                 and kind is not None and (kind=="material" or route=="consumables") and not protected
                 and not (raw.keys() & (set(sum(CLASS_FIELDS.values(),[]))-set(CLASS_FIELDS.get(kind,[]))))
                 and not (raw.keys() & ADVANCED) and not raw.get("text_id")
                 and not raw.get("qualities"))
    return {"contract": CONTRACT, "editable": bool(supported), "supply_class":kind,
            "fields": FIELDS + CLASS_FIELDS.get(kind,[]),
            "reason": ("Canonical empty skin is reference-only: exact-ID filling creates canonical water_skin." if protected else
                "Ordinary inert material" if supported and kind=="material" else "Ordinary "+kind if supported else
                "Read-only: requires one ordinary material, food, drink or treatment in components/butchery/consumables without equipment, effects or special use."),
            "weight_unit": "kg", "tier_min": 0, "tier_max": 2**53-1,
            "tier_note": "Nonnegative integer from the persisted instance contract; authoring is limited to exact JavaScript integers.",
            "stack_note": "Groups same-ID instances in inventory display. Instances and carried weights remain separate; no stack-size mechanic is authored."}


def authorize_candidate(original, candidate, source, target, *, data=None):
    # Original eligibility is independently checked by the shared worker. Raw
    # edits cannot change the original class/category, including absent vs null.
    problems=[]
    if not isinstance(candidate, dict):
        return [dict(severity='error', code='ITEM_SHAPE', path=target, asset='', field='',
            message='Expected one item object; array editing is unsupported.', correction='Restore a single item object in Source.')]
    for field in ('category','on_use'):
        if (field in original)!=(field in candidate) or original.get(field)!=candidate.get(field):
            problems.append(dict(severity='error',code='ITEM_CLASS',path=target,asset=str(candidate.get('id','')),field=field,
                message='Keep the verified original category and use identity. Start from a source of the desired class.',correction='Restore the original value.'))
    return problems


def return_definition(identifier, data, sources, *, owner=None):
    if not identifier: return None, None
    if not isinstance(identifier,str): return None, 'Return ID must be a string or null.'
    if owner and identifier.casefold()==owner.casefold(): return None, 'A drink cannot return itself.'
    rows=[s for k,ss in sources.items() if k.casefold()==identifier.casefold() for s in ss]
    if len(rows)!=1 or rows[0]['pointer'] or rows[0]['definition'].get('id')!=identifier:
        return None, 'Return item is missing, ambiguous or not one object.'
    row=rows[0]; raw=row['definition']; cap=capability(raw,row['path'])
    canonical=identifier=='empty_water_skin' and row['path']=='roguelike/data/items/consumables/empty_water_skin.json'
    # The exact canonical exception is permission to reference, never to edit.
    if canonical:
        probe=dict(raw,id='ordinary_return_probe')
        eligible=capability(probe,'roguelike/data/items/consumables/ordinary_return_probe.json')['editable']
    else: eligible=cap['editable']
    if not eligible or raw.get('on_use') is not None or cap['supply_class']!='material':
        return None, 'Return must be an ordinary inert object without active use, equipment, light or effects.'
    issues=validate_definition(raw,data,row['path'],sources)
    if any(d['severity']=='error' for d in issues): return None, 'Return definition is not factory-valid: '+ '; '.join(d['message'] for d in issues)
    try: factory_preview(raw,data)
    except (ValueError, TypeError, KeyError, OverflowError) as error: return None, 'Return construction failed: '+str(error)
    return dict(id=identifier,label=str(raw.get('name',identifier))+' · '+identifier+' · '+row['path'],path=row['path'],editable=cap['editable'],sha256=hashlib.sha256((data.root/PurePosixPath(row['path']).relative_to('roguelike/data')).read_bytes()).hexdigest()), None


def effective_use(raw, data):
    handler=raw.get('on_use')
    if handler not in ('eat','drink','heal_minor'): return None
    if handler=='heal_minor':
        value=raw.get('heal_amount'); amount=value or 3
        return dict(field='heal_amount',stored=value,amount=amount,explanation=f'Stored {value!r}; effective {amount} HP, limited by missing HP. Absent/null/legacy zero falls back to 3. Full-health, dead or stale treatment uses no item or turn.')
    field,need,default,maximum=('nutrition','hunger',300,1000) if handler=='eat' else ('hydration','thirst',400,800)
    maximum=data.survival.get(need,{}).get('max',maximum)
    if type(maximum) not in (int,float) or not math.isfinite(maximum) or maximum<=0: raise ValueError('Saved survival maximum must be finite and positive.')
    value=raw.get(field); dose=default if value is None else value
    fraction=dose if dose<=1 else dose/maximum
    return dict(field=field,stored=value,dose=dose,maximum=maximum,fraction=fraction,
        configuration='roguelike/data/survival.json',configuration_sha256=hashlib.sha256((data.root/'survival.json').read_bytes()).hexdigest(),
        explanation=f'Stored {value!r}; consumer dose {dose:g}. '+('Fraction at or below 1' if dose<=1 else f'Above 1 divided by saved {need} maximum {maximum:g}')+f': {fraction:.8g} ({fraction*100:.8g}%). Restoration is clamped to current need. Whole item used, including zero; normal action time still applies.')


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
    for field in FIELDS + ["on_use", "qualities", "text_id", "nutrition", "hydration", "heal_amount", "eat_message", "drink_message", "liquid", "liquid_volume", "harvest_from"]:
        if field in raw:
            try:
                validate_fields({field: raw[field]}, {field: ITEM_STATE[field]}, "definition")
            except (ValueError, OverflowError) as error:
                issue("ITEM_FIELD", field, str(error))
    for field in ('weight','nutrition','hydration','heal_amount'):
        value=raw.get(field)
        if type(value) is int and value>2**53-1: issue('ITEM_FIELD',field,'Number exceeds exact authoring integer range.')
    if writable and raw.get('on_use')=='heal_minor' and raw.get('heal_amount') is not None:
        if type(raw['heal_amount']) is not int or not 1<=raw['heal_amount']<=2**53-1:
            issue('ITEM_FIELD','heal_amount','Authored treatment amount must be a positive exact integer; legacy zero falls back to 3.')
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
    if raw.get('on_use')=='drink' and 'empty_form' in raw:
        value=raw['empty_form']
        if value is not None and not isinstance(value,str): issue('ITEM_RETURN','empty_form','Expected a saved return ID, empty string or null.')
        elif value:
            _, error=return_definition(value,data,sources,owner=identifier)
            if error: issue('ITEM_RETURN','empty_form',error)
    if raw.get('on_use') in ('eat','drink') and not any(d['severity']=='error' for d in problems):
        try: effective_use(raw,data)
        except (ValueError, TypeError, OverflowError) as error: issue('ITEM_DOSE','',str(error))
    return problems


def factory_preview(raw, data):
    """Actual definition-to-instance result, unowned and never used interactively."""
    item = ItemFactory(data).create(raw["id"])
    if item is None: raise ValueError("ItemFactory returned no instance")
    state = snapshot(item, ITEM_STATE)
    validate_fields(state, ITEM_STATE, "factory instance")
    defaults=dict(name=raw['id'],description='',tile='generic_item',weight=0.1,stackable=False,keywords=[],consumed_on_use=True,on_use=None,
                  nutrition=None,hydration=None,heal_amount=None,eat_message=None,drink_message=None)
    comparisons = [{"field": f, "declared": raw.get(f), "present": f in raw, "effective_factory_value": raw.get(f,defaults[f]),
                    "instance": state[f], "equal": raw.get(f,defaults[f]) == state[f]}
                   for f in defaults]
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


from datetime import datetime, timezone
from engine.content_authoring import definition_sources

def authoring_context(raw, data, path, data_root, identity, digest, *, observe=False):
    from engine.item_authoring import capability, use_binding, validate_definition, factory_preview, references
    sources = definition_sources(data_root, "items")
    recipes = definition_sources(data_root, "recipes")
    pools = definition_sources(data_root, "loot_pools")
    records = []
    for index, definition in enumerate(raw if isinstance(raw, list) else [raw]):
        if not isinstance(definition, dict): continue
        pointer = f"/{index}" if isinstance(raw, list) else ""
        diagnostics = validate_definition(definition, data, path, sources)
        cap = capability(definition, path, pointer)
        ambiguous = any(d["code"] in ("DUPLICATE_ID", "LOADER_IDENTITY") for d in diagnostics)
        cap["editable"] = cap["editable"] and not ambiguous
        if ambiguous: cap["reason"] = "Read-only: ambiguous or unloaded source identity. See Validation for every path."
        observed = None
        if not any(d["severity"] == "error" for d in diagnostics):
            try:
                observed = {**factory_preview(definition, data), "definition_sha256": digest,
                            "source": identity, "path": path, "pointer": pointer,
                            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                            "loaded_catalog_sha256": data.structure_catalog.identity}
            except (ValueError, TypeError, KeyError) as error:
                diagnostics.append(dict(severity="error", code="ITEM_FACTORY", path=path, asset=str(definition.get("id", "")),
                                        field="", message=str(error), correction="Correct invalid factory fields before publication."))
        refs = []
        for pool_id, locations in sorted(pools.items()):
            for location in locations:
                entries = location["definition"].get("items", [])
                for i, entry in enumerate(entries if isinstance(entries, list) else []):
                    if isinstance(entry, dict) and entry.get("item_id") == definition.get("id"):
                        refs.append(dict(id=pool_id, path=location["path"], pointer=location["pointer"], index=i,
                                         field=f"items[{i}].item_id", unique=len(locations) == 1))
        from engine.recipe_authoring import item_relations
        returned=None
        if definition.get('on_use')=='drink' and definition.get('empty_form') and not ambiguous:
            returned,_=return_definition(definition['empty_form'],data,sources,owner=definition.get('id'))
        effective=None
        if observed:
            try: effective=effective_use(definition,data)
            except (ValueError,TypeError,OverflowError): pass
        records.append(dict(id=definition.get("id", ""), pointer=pointer, definition=definition, capability=cap,
                            effective_use=effective,return_item=returned,
                            diagnostics=diagnostics, use=use_binding(definition), pools=refs,
                            recipes=item_relations(definition.get("id"), data, recipes) if not ambiguous else [],
                            dependencies=references(definition, data, recipes) if not ambiguous else [], factory=observed))
    returns=[]
    for identifier,rows in sorted(sources.items()):
        if len(rows)!=1: continue
        raw_return=rows[0]['definition']
        if raw_return.get('on_use') is not None: continue
        returned,_=return_definition(identifier,data,sources)
        if returned: returns.append(returned)
    return {"records": records, "keywords": data.keywords, "tiles": sorted(TileRegistry(str(data.root/'tiles.json')).all_names()), "return_items":returns,
            "snapshot": "Opened source snapshot; edits require validation for refreshed references, binding and factory evidence."}
