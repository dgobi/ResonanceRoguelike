"""Read-only Workbench contract for immediate component recipes.

Gameplay does not import this module. Allocation, factory construction and exact
ownership exchange remain the production functions, not an editor simulation.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import PurePosixPath
from types import SimpleNamespace

from components.equipment import Equipment
from components.inventory import Inventory
from engine.crafting import _item_has_tag, _item_has_all_tags, _tag_tier_on_item, material_candidate, plan_craft, commit_craft
from engine.item_factory import ItemFactory
from engine.save_components import ITEM_STATE, snapshot, validate_fields

CONTRACT = "immediate-components-1"
def requirement_schema(title, reference, physical=True):
    properties = {
        "tag": {"type": "string", "title": "Tag", "x-reference": reference},
        "min_tier": {"type": "integer", "title": "Minimum tier", "minimum": 0, "maximum": 2**53-1, "default": 1},
    }
    if physical: properties["quantity"] = {"type": "integer", "title": "Quantity", "minimum": 1, "maximum": 32, "default": 1}
    return {"type": "array", "title": title, "x-control": "ordered-table",
            "items": {"type": "object", "required": ["tag"], "properties": properties}}


SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "required": ["id", "components", "result_item"],
          "properties": {
    "id": {"type": "string", "title": "Recipe ID", "readOnly": True},
    "name": {"type": "string", "title": "Recipe name"},
    "description": {"type": "string", "title": "Recipe description", "x-control": "multiline"},
    "category": {"type": "string", "title": "Recipe category", "x-reference": "categories"},
    "known": {"type": "boolean", "title": "Recipe known", "default": True,
              "description": "Known at startup. False displays an unknown recipe and blocks CraftScreen execution; no learning route is established."},
    "components": requirement_schema("Required items", "keywords"),
    "tools": requirement_schema("Tools · retained", "keywords"),
    "requires_ambient": requirement_schema("Ambient conditions", "ambient_tags", False),
    "result_item": {"type": "string", "title": "Recipe output item", "x-reference": "items", "x-view": "Output"},
}}
VIEWS = ["recipe-requirements", "output", "production-receipt"]
PUBLICATION_NOTE = "This creates an active recipe variant. New sessions recursively load it; known defaults to true and enables CraftScreen execution when requirements are met. known:false displays an unknown recipe and blocks execution. No learning route or personal-save compatibility is promised."
LIMITATIONS = "Recipe contract and output factory checked. Probe cases separately report actual eligibility and isolated production exchange; validation is not a claim of ordinary player crafting or acquisition."


def reference_options(context):
    return {**{name: [dict(id=k, label=k) for k in sorted(context[name])] for name in ("keywords", "ambient_tags", "categories")},
            "items": [dict(id=r["id"], label=r["id"] + " · " + r["name"]) for r in context["items"]]}


def authoring_validate(raw, data, path, data_root):
    return validate_definition(raw, data, path, definition_sources(data_root, "recipes"), definition_sources(data_root, "items"), writable=True)


def authoring_evidence(context):
    return dict(semantic_verified=bool(context and context["records"][0]["probe"]))
FIELDS = ["name", "description", "category", "known", "components", "tools", "requires_ambient", "result_item"]
EXCLUDED = ["_deprecated", "requires_single_item", "result_tile", "places_in_world", "processing_turns",
            "processing_source", "processing_decor", "placement_message", "completion_message", "apply_turns"]
VISIBILITY = ("DataLoader recursively loads recipe files at session startup. CraftScreen hides truthy _deprecated; "
              "known defaults to true. known:false is shown as unknown and refuses crafting. Publishing a variant "
              "in the active recipes directory changes new-session content; it is not an inert draft, a learning "
              "route or a promise about existing personal saves.")


def ambient_catalog(data):
    """Ask the actual UI ambient collector about loaded decor/light definitions.

    Ambient tags are not all in keywords.json (notably burning). These controlled
    sources disclose current code support; they do not prove player acquisition.
    """
    from rendering.craft_screen import CraftScreen
    player = SimpleNamespace(x=0, y=0, inventory=Inventory(), equipment=Equipment(), light_source=None)
    engine = SimpleNamespace(player=player, data=data, local_map=SimpleNamespace(decor={}))
    tags = {}
    def collect(source):
        for row in CraftScreen._build_ambient_sources(engine):
            tags.setdefault(row["tag"], []).append(dict(source=source, tier=row["tier"]))
    for identifier in sorted(data.decoratives):
        engine.local_map.decor = {(0, 0): identifier}
        collect("decoratives:" + identifier)
    engine.local_map.decor = {}
    for identifier, definition in sorted(data.items.items()):
        if not definition.get("provides_burning"): continue
        item = ItemFactory(data).create(identifier)
        player.inventory.items = [item]; player.equipment.slots["offhand"] = item
        player.light_source = SimpleNamespace(active=True, _item_ref=item)
        collect("items:" + identifier)
    return tags


def capability(raw, path, pointer=""):
    parts = PurePosixPath(path).parts
    kind = "Unknown"
    if isinstance(raw, dict):
        kind = ("Deprecated / legacy" if raw.get("_deprecated") else
                "World placement" if raw.get("places_in_world") or "result_tile" in raw else
                "Passive processing" if raw.get("passive_processing") else
                "Immediate item output" if raw.get("result_item") else "Unknown")
    supported = (not pointer and isinstance(raw, dict) and len(parts) >= 4
                 and parts[:3] == ("roguelike", "data", "recipes")
                 and isinstance(raw.get("result_item"), str) and bool(raw["result_item"])
                 and isinstance(raw.get("components"), list) and bool(raw["components"])
                 and raw.get("passive_processing", False) is False and not any(k in raw for k in EXCLUDED))
    return dict(contract=CONTRACT, editable=bool(supported), execution_class=kind, fields=FIELDS,
                excluded_fields=EXCLUDED, tier_min=0, tier_max=2**53-1, quantity_max=32, slots_max=64,
                reason="Immediate item output with ordered components, optional tools and ambient conditions" if supported else
                "Not supported for writing: requires a single immediate item-output object with components and no legacy, conjunction, placement or processing fields.")


def validate_definition(raw, data, path, sources, item_sources, *, writable=False):
    problems = []
    identifier = raw.get("id") if isinstance(raw, dict) else None
    def issue(code, field, message, severity="error"):
        problems.append(dict(severity=severity, code=code, path=path, asset=str(identifier or ""), field=field,
                             message=message, correction="Correct the exact source field/reference; unsupported families remain read-only."))
    if not isinstance(raw, dict) or not isinstance(identifier, str) or not identifier:
        issue("RECIPE_ID", "id", "Expected a recipe object with a nonempty string ID.")
        return problems
    collisions = [s for key, rows in sources.items() if key.casefold() == identifier.casefold() for s in rows]
    paths = [s for rows in sources.values() for s in rows if s["path"].casefold() == path.casefold()]
    if len(collisions) != 1 or len({s["path"] for s in paths}) > 1:
        issue("DUPLICATE_RECIPE", "id", "Ambiguous recipe ID or case/path collision: " +
              ", ".join(s["path"] + s["pointer"] for s in collisions + paths))
    if data.recipes.get(identifier) != raw or not any(s["path"] == path and s["definition"] == raw for s in collisions):
        issue("LOADER_IDENTITY", "id", "DataLoader did not load this exact recipe from this source.")
    if writable and not capability(raw, path)["editable"]:
        issue("UNSUPPORTED_RECIPE", "", capability(raw, path)["reason"])
    for field in ("name", "description", "category"):
        if field in raw and not isinstance(raw[field], str): issue("RECIPE_FIELD", field, "Expected a string.")
    for field in ("known", "passive_processing", "places_in_world", "_deprecated"):
        if field in raw and type(raw[field]) is not bool: issue("RECIPE_FIELD", field, "Expected a boolean.")
    slots = 0
    ambient_tags = ambient_catalog(data)
    for field in ("components", "tools", "requires_ambient"):
        rows = raw.get(field, [])
        if not isinstance(rows, list):
            issue("REQUIREMENT_ROWS", field, "Expected an ordered requirement array."); continue
        if len(rows) > 64: issue("PROBE_LIMIT", field, "Authoring supports at most 64 rows per array.")
        for i, row in enumerate(rows):
            prefix = f"{field}[{i}]"
            if not isinstance(row, dict):
                issue("REQUIREMENT_ROW", prefix, "Expected a requirement record."); continue
            registry = ambient_tags if field == "requires_ambient" else data.keywords
            if not isinstance(row.get("tag"), str) or row["tag"] not in registry:
                issue("KEYWORD_REFERENCE", prefix + ".tag", f"Unknown keyword {row.get('tag')!r}.")
            tier = row.get("min_tier", 1)
            if type(tier) is not int or not 0 <= tier <= 2**53-1:
                issue("REQUIREMENT_TIER", prefix + ".min_tier", "Expected a nonnegative exact integer; default is 1.")
            if field != "requires_ambient":
                quantity = row.get("quantity", 1)
                if type(quantity) is not int or not 1 <= quantity <= 32:
                    issue("REQUIREMENT_QUANTITY", prefix + ".quantity", "Expected 1–32 physical instances (Workbench bound); default is 1.")
                else: slots += quantity
            elif "quantity" in row:
                issue("INACTIVE_FIELD", prefix + ".quantity", "Ambient conditions do not consume quantities; the runtime ignores this field.", "warning")
    if slots > 64: issue("PROBE_LIMIT", "components/tools", "Workbench supports at most 64 physical slots; this is a tooling limit.")
    result = raw.get("result_item")
    if result is not None:
        locations = [s for key, rows in item_sources.items() if isinstance(result, str) and key.casefold() == result.casefold() for s in rows]
        if not isinstance(result, str) or result not in data.items or len(locations) != 1:
            issue("OUTPUT_REFERENCE", "result_item", f"Output {result!r} has no unique catalogue-resolved item definition.")
        else:
            try: validate_fields(snapshot(ItemFactory(data).create(result), ITEM_STATE), ITEM_STATE, "recipe output")
            except (ValueError, TypeError, KeyError) as error: issue("OUTPUT_FACTORY", "result_item", str(error))
    return problems


def candidates(raw, data, item_sources):
    """Potential tag predicates only, using actual factory instances. Preserve row order."""
    factory = ItemFactory(data)
    items = []
    for identifier in sorted(data.items):
        locations = [s for key, rows in item_sources.items() if key.casefold() == identifier.casefold() for s in rows]
        if len(locations) != 1: continue
        try:
            item = factory.create(identifier)
            validate_fields(snapshot(item, ITEM_STATE), ITEM_STATE, "candidate")
            items.append((item, locations[0]))
        except (ValueError, TypeError, KeyError): continue
    rows = []
    for role in ("components", "tools", "requires_single_item"):
        requirements = raw.get(role, [])
        if role == "requires_single_item":
            requirements = [dict(tags=requirements if isinstance(requirements, list) else requirements.get("tags", []))] if isinstance(requirements, (list, dict)) and requirements else []
        if not isinstance(requirements, list): continue
        for i, req in enumerate(requirements):
            if not isinstance(req, dict): continue
            matched = []
            for item, location in items:
                try:
                    match = (_item_has_all_tags(item, req["tags"]) if role == "requires_single_item" else
                             _item_has_tag(item, req["tag"], req.get("min_tier", 1)))
                    if match: matched.append(dict(id=item.item_id, path=location["path"], pointer=location["pointer"],
                                                  automatic_material=bool(material_candidate(item))))
                except (KeyError, TypeError, ValueError): continue
            rows.append(dict(role=role, index=i, requirement=req, matches=matched))
    return rows


def item_relations(identifier, data, recipe_sources):
    """Every declared source, including duplicates; never choose a loader winner."""
    try: item = ItemFactory(data).create(identifier)
    except (ValueError, TypeError, KeyError): item = None
    rows = []
    for key, locations in sorted(recipe_sources.items()):
        for source in locations:
            recipe = source["definition"]
            fields = []
            if item is not None:
                for role in ("components", "tools"):
                    reqs = recipe.get(role, [])
                    for i, req in enumerate(reqs if isinstance(reqs, list) else []):
                        try:
                            if _item_has_tag(item, req["tag"], req.get("min_tier", 1)): fields.append(f"{role}[{i}]")
                        except (KeyError, TypeError): continue
                single = recipe.get("requires_single_item")
                try:
                    if single and _item_has_all_tags(item, single if isinstance(single, list) else single["tags"]): fields.append("requires_single_item")
                except (KeyError, TypeError): pass
            output = recipe.get("result_item") == identifier
            if output or fields:
                rows.append(dict(id=key, path=source["path"], pointer=source["pointer"], produces=output, fields=fields,
                                 execution_class=capability(recipe, source["path"], source["pointer"])["execution_class"]))
    return rows


def probe(raw, data, item_sources, path, digest, identity):
    """Synthetic isolated inventory; unmodified catalogue instances, production plan and exchange.

    This does not invoke ordinary player input or CraftScreen._attempt_craft.
    Ambient sources are explicit synthetic records, not acquired scenery.
    """
    factory = ItemFactory(data)
    candidate_rows = candidates(raw, data, item_sources)
    fixture = []
    for row in candidate_rows:
        if row["role"] not in ("components", "tools"): continue
        matches = [m for m in row["matches"] if row["role"] == "tools" or m["automatic_material"]]
        matches.sort(key=lambda m: (m["id"] == raw["result_item"],
                                   _tag_tier_on_item(factory.create(m["id"]), row["requirement"]["tag"]), m["id"]))
        if matches:
            for _ in range(row["requirement"].get("quantity", 1)):
                fixture.append(matches[0])
    ambient = [dict(tag=r["tag"], tier=r.get("min_tier", 1)) for r in raw.get("requires_ambient", [])]
    cases = []
    for preset in ("eligible", "missing_items", "missing_ambient"):
        inv = Inventory(capacity=1000000)
        physical = []
        for n, ref in enumerate(fixture if preset != "missing_items" else []):
            item = factory.create(ref["id"])
            if not inv.add(item): raise ValueError("Fixture exceeds explicit capacity")
            definition = data.items[ref["id"]]
            physical.append((item, dict(instance=f"input-{n+1}", item_id=item.item_id, source=ref["path"], pointer=ref["pointer"],
                              definition_json_sha256=hashlib.sha256(json.dumps(definition, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                              source_sha256=hashlib.sha256((data.root / PurePosixPath(ref["path"]).relative_to("roguelike/data")).read_bytes()).hexdigest(),
                              keywords=item.keywords, consumed_on_use=item.consumed_on_use, synthetic=True)))
        ambient_case = ambient if preset != "missing_ambient" else []
        selected, missing = plan_craft(raw, inv, data.keywords, ambient_case)
        ids = {id(item): record["instance"] for item, record in physical}
        selected_ids = [ids[id(item)] for item in selected]
        materials = [ids[id(item)] for item in getattr(selected, "materials", [])]
        before = [ids[id(item)] for item in inv.items]
        output = None; committed = None
        if not missing:
            created = factory.create(raw["result_item"])
            state = snapshot(created, ITEM_STATE); validate_fields(state, ITEM_STATE, "probe output")
            engine = SimpleNamespace(player=SimpleNamespace(inventory=inv, equipment=Equipment(), light_source=None), data=data)
            committed = commit_craft(engine, raw, selected, ambient_case, [created])
            output_source = item_sources[created.item_id][0]
            output = dict(instance="output-1", item_id=created.item_id, properties=state, in_inventory=inv.contains(created),
                          source=output_source["path"], pointer=output_source["pointer"],
                          source_sha256=hashlib.sha256((data.root / PurePosixPath(output_source["path"]).relative_to("roguelike/data")).read_bytes()).hexdigest())
            ids[id(created)] = "output-1"
        cases.append(dict(preset=preset, eligible=not missing, missing=missing, inventory=[record for _, record in physical],
                          ambient=ambient_case, selected=selected_ids, materials=materials, retained_tools=[i for i in selected_ids if i not in materials] if not missing else [],
                          before=before, after=[ids[id(i)] for i in inv.items], committed=committed, output=output,
                          capacity=inv.capacity, weight_after=inv.current_weight))
    return dict(path=path, recipe_id=raw["id"], source_sha256=digest, source=identity, cases=cases,
                fixture_selection="Per row, automatic material candidates (or any tool); prefer a definition other than the output, then production tag tier and ID. Create distinct physical instances. This fixture selection does not establish acquisition.",
                consumer="engine.crafting.plan_craft -> engine.item_factory.ItemFactory.create -> engine.crafting.commit_craft -> engine.item_transfers.exchange",
                scope="Synthetic disposable inventory and ambient records; actual production allocation, factory and ownership exchange. No ordinary player controls, CraftScreen knowledge gate, acquisition, world placement, turn or campaign executed.",
                known_gate=raw.get("known", True), visibility=VISIBILITY)


from datetime import datetime, timezone
from engine.content_authoring import definition_sources

def authoring_context(raw, data, path, data_root, identity, digest, *, observe=False):
    from engine.recipe_authoring import capability, validate_definition, candidates, probe, ambient_catalog, VISIBILITY
    sources = definition_sources(data_root, "recipes")
    items = definition_sources(data_root, "items")
    records = []
    for index, definition in enumerate(raw if isinstance(raw, list) else [raw]):
        if not isinstance(definition, dict): continue
        pointer = f"/{index}" if isinstance(raw, list) else ""
        cap = capability(definition, path, pointer)
        diagnostics = validate_definition(definition, data, path, sources, items)
        if any(d["code"] in ("RECIPE_ID", "DUPLICATE_RECIPE", "LOADER_IDENTITY") for d in diagnostics):
            cap["editable"] = False; cap["reason"] = "Not supported: ambiguous or unloaded source. Inspect the diagnostic paths."
        output_id = definition.get("result_item")
        output_sources = items.get(output_id, []) if isinstance(output_id, str) else []
        observed = None
        if observe and cap["editable"] and not any(d["severity"] == "error" for d in diagnostics):
            observed = probe(definition, data, items, path, digest, identity)
            observed["observed_at_utc"] = datetime.now(timezone.utc).isoformat()
            observed["loaded_catalog_sha256"] = data.structure_catalog.identity
        records.append(dict(id=definition.get("id", ""), pointer=pointer, definition=definition, capability=cap,
                            diagnostics=diagnostics, candidates=candidates(definition, data, items), probe=observed,
                            output=dict(id=output_id, resolved=isinstance(output_id, str) and output_id in data.items and len(output_sources) == 1,
                                        sources=[dict(path=s["path"], pointer=s["pointer"]) for s in output_sources])))
    return dict(records=records, keywords=data.keywords, ambient_tags=ambient_catalog(data), visibility=VISIBILITY,
                categories=sorted({r.get("category") for r in data.recipes.values() if isinstance(r.get("category"), str)}),
                items=[dict(id=key, name=str(data.items.get(key, {}).get("name", key))) for key, ss in sorted(items.items())
                       if key in data.items and len([s for k, rows in items.items() if k.casefold() == key.casefold() for s in rows]) == 1])
