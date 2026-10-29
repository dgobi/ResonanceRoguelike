"""First-party content authoring registration. Gameplay never imports this module.

JSON Schema 2020-12 shape annotations plus the bounded resonance-controls-1
vocabulary describe controls, not publication authority. Only these explicit
Python adapters run; descriptors cannot import modules or evaluate expressions.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath

DIALECT = "https://json-schema.org/draft/2020-12/schema"
VOCABULARY = "resonance-controls-1"


from engine.definition_sources import definition_sources


def schema_problems(schema):
    """Negotiate the supported subset, never silently omit an unknown control."""
    errors = []
    def visit(node, path, depth=0):
        if not isinstance(node, dict) or depth > 4:
            errors.append(f"{path}: expected bounded schema object"); return
        allowed = {"$schema", "type", "title", "description", "default", "readOnly", "minimum", "maximum",
                   "properties", "required", "items", "additionalProperties", "x-control", "x-reference", "x-view", "x-initial", "x-suggestions"}
        for key in node.keys() - allowed: errors.append(f"{path}: unsupported schema keyword {key}")
        kind = node.get("type")
        if kind not in ("string", "number", "integer", "boolean", "object", "array"):
            errors.append(f"{path}: unsupported type {kind}")
        if node.get("x-control", "scalar") not in ("scalar", "multiline", "ordered-table", "ordered-records", "keyed-number-map"):
            errors.append(f"{path}: unsupported control {node['x-control']}")
        keyed_map = node.get('x-control') == 'keyed-number-map'
        if keyed_map and (kind != 'object' or depth != 1 or not isinstance(node.get('x-reference'),str) or not isinstance(node.get('additionalProperties'),dict) or node['additionalProperties'].get('type') != 'number' or node.get('properties') != {}): errors.append(f'{path}: keyed-number-map requires one referenced root-field object with numeric values')
        if kind == "object" and depth not in (0, 2) and not keyed_map: errors.append(f"{path}: only root, keyed maps and table-row objects are supported")
        if kind == "array" and (depth != 1 or node.get("x-control") not in ("ordered-table", "ordered-records")):
            errors.append(f"{path}: only registered ordered tables are supported")
        if node.get("x-control") == "multiline" and kind != "string": errors.append(f"{path}: multiline requires a string")
        if node.get("x-control") in ("ordered-table", "ordered-records") and (kind != "array" or not isinstance(node.get("items"), dict) or node["items"].get("type") != "object"):
            errors.append(f"{path}: ordered controls require an array of objects")
        if "x-reference" in node and kind != "string" and not keyed_map: errors.append(f"{path}: reference requires a string or keyed map")
        if "x-suggestions" in node and (kind != "string" or not isinstance(node["x-suggestions"], list) or len(node["x-suggestions"]) > 32 or any(not isinstance(v, str) for v in node["x-suggestions"])):
            errors.append(f"{path}: invalid string suggestions")
        for annotation in ("default", "x-initial"):
            if annotation not in node: continue
            value = node[annotation]
            valid = (isinstance(value, str) if kind == "string" else type(value) is bool if kind == "boolean" else
                     type(value) is int if kind == "integer" else type(value) in (int, float) if kind == "number" else False)
            if not valid: errors.append(f"{path}: unsupported or mismatched effective default")
        if kind == "object":
            props = node.get("properties", {})
            if not isinstance(props, dict) or len(props) > 64:
                errors.append(f"{path}: expected at most 64 properties"); return
            for key, child in props.items(): visit(child, f"{path}.{key}", depth+1)
            if not isinstance(node.get("required", []), list) or any(k not in props for k in node.get("required", [])):
                errors.append(f"{path}: invalid required properties")
        if kind == "array": visit(node.get("items"), path+"[]", depth+1)
        if keyed_map: visit(node.get('additionalProperties'),path+'{}',depth+1)
        for key in ("minimum", "maximum"):
            if key in node and (type(node[key]) not in (float, int) or not -float('inf') < node[key] < float('inf')):
                errors.append(f"{path}: invalid {key}")
        if "readOnly" in node and type(node["readOnly"]) is not bool: errors.append(f"{path}: invalid readOnly")
        for key in ("title", "description", "x-reference", "x-view"):
            if key in node and not isinstance(node[key], str): errors.append(f"{path}: invalid {key}")
    if not isinstance(schema, dict) or schema.get("$schema") != DIALECT: errors.append("Unsupported schema dialect")
    visit(schema, "schema")
    return errors


@dataclass(frozen=True)
class Family:
    id: str
    directory: str
    module: object
    operations: tuple[str, ...]
    write_root: str
    exact_file: str | None = None

    @property
    def route(self): return getattr(self.module, "PRODUCTION_ROUTE", self.id + "_definition")

    def matches(self, path):
        if hasattr(self.module, "matches"): return self.module.matches(path)
        if self.exact_file: return path == self.exact_file
        prefix = ("roguelike", "data", *PurePosixPath(self.directory).parts)
        return PurePosixPath(path).parts[:len(prefix)] == prefix

    def descriptor(self):
        value = dict(vocabulary=VOCABULARY, schema=self.module.SCHEMA, views=self.module.VIEWS, production_route=self.route,
                     policy=dict(operations=list(self.operations), root=self.write_root, identity="id"),
                     publication_note=self.module.PUBLICATION_NOTE)
        return value, hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def envelope(self, context, *, operations=None):
        descriptor, digest = self.descriptor()
        problems = schema_problems(descriptor["schema"])
        allowed_views = {"item-properties", "references", "recipes", "use-binding", "factory", "recipe-requirements", "recipe-processing", "output", "production-receipt", "text-pages", "text-references", "reader-preview", "typography-roles", "typography-preview", "creature-properties", "creature-references", "creature-factory", "room-spatial", "world-assignment"}
        if not isinstance(descriptor["views"], list) or any(v not in allowed_views for v in descriptor["views"]):
            problems.append("Unsupported specialized view registration")
        return dict(id=self.id, contract=self.module.CONTRACT, descriptor_sha256=digest,
                    descriptor=descriptor, compatible=not problems, problems=problems,
                    references=self.module.reference_options(context) if context else {}, context=context,
                    effective_operations=self.operations_for(context) if operations is None else operations)

    def operations_for(self, context):
        if not context or len(context["records"]) != 1: return []
        if not self.eligible(context): return []
        return [op for op in context["records"][0]["capability"].get("operations", self.operations) if op in self.operations]

    def staging_path(self, asset):
        """Trusted registration maps logical documentation identity into scratch data."""
        mapper = getattr(self.module, "staging_path", None)
        return mapper(asset) if mapper else PurePosixPath(asset).relative_to("roguelike/data").as_posix()

    def authorize(self, original, candidate, source, target, data):
        adapter = getattr(self.module, "authorize_candidate", None)
        return adapter(original, candidate, source, target, data=data) if adapter else []

    def context(self, *args, resource_root=None, seed=None, **kwargs):
        if getattr(self.module, "USES_FONT_RESOURCES", False): kwargs["resource_root"] = resource_root
        if getattr(self.module, "USES_SCENE_SEED", False): kwargs["seed"] = seed if seed is not None else 20261023
        return self.module.authoring_context(*args, **kwargs)

    def validate(self, raw, data, path, data_root, *, resource_root=None):
        if getattr(self.module, "USES_FONT_RESOURCES", False):
            return self.module.authoring_validate(raw, data, path, data_root, resource_root=resource_root)
        return self.module.authoring_validate(raw, data, path, data_root)

    def preview(self, raw, data, root, inputs):
        adapter = getattr(self.module, "authoring_preview", None)
        if not adapter: raise ValueError("This family has no registered preview adapter.")
        return adapter(raw, data, root, inputs)

    def eligible(self, context):
        return bool(context and len(context["records"]) == 1 and context["records"][0]["capability"]["editable"])

    def discover(self, root):
        from generation.structure_contract import read_document, StructureError
        indexer = getattr(self.module, "source_index", None)
        sources = indexer(root / "roguelike/data") if indexer else definition_sources(root / "roguelike/data", self.directory, getattr(self.module, "RESERVED_BASENAMES", ()))
        rows = []
        discover_paths = getattr(self.module, "discover_paths", None)
        paths = discover_paths(root) if discover_paths else (root / "roguelike/data" / self.directory).rglob("*.json")
        for path in sorted(paths):
            if self.exact_file and path != root / self.exact_file: continue
            if path.name.casefold() in getattr(self.module, "RESERVED_BASENAMES", ()): continue
            relative = path.relative_to(root).as_posix()
            try: raw = read_document(path)
            except StructureError: raw = {}
            for index, record in enumerate(raw if isinstance(raw, list) else [raw]):
                record = record if isinstance(record, dict) else {}
                pointer = f"/{index}" if isinstance(raw, list) else ""
                identifier = str(record.get("id", path.stem))
                locations = [s for k, ss in sources.items() if k.casefold() == identifier.casefold() for s in ss]
                if self.exact_file: locations = [s for s in locations if s["path"] == self.exact_file]
                cap = self.module.capability(record, relative, pointer)
                rows.append(dict(path=relative, pointer=pointer, id=identifier, name=str(record.get("name", record.get("title", ""))),
                    category=("player" if identifier.casefold() == "player" else "creatures" if "/entities/creatures/" in relative else "other entities") if self.id == "creature" else str(record.get("category", "")), result_item=record.get("result_item"),
                    execution_class=cap.get("execution_class"), route=self.route, family_id=self.id,
                    editable=cap["editable"] and len(locations) == 1,
                    provenance="Selected checkout / registered content source",
                    validation="ambiguous / invalid source" if len(locations) != 1 else "not yet checked",
                    source_paths=[s["path"] + s["pointer"] for s in locations]))
        return rows


def families():
    # The sole trusted registration point. No renderer or descriptor imports.
    from engine import item_authoring, recipe_authoring, text_authoring, typography_authoring, creature_authoring, room_authoring, assignment_authoring
    return (
        Family("assignment", "generation", assignment_authoring, ("edit",), assignment_authoring.PROFILE, assignment_authoring.PROFILE),
        Family("room", "layouts", room_authoring, ("edit", "variant"), "roguelike/data/layouts/"),
        Family("creature", "entities", creature_authoring, ("edit", "variant"), "roguelike/data/entities/creatures/"),
        Family("item", "items", item_authoring, ("edit", "variant"), "roguelike/data/items/"),
        Family("recipe", "recipes", recipe_authoring, ("edit", "variant"), "roguelike/data/recipes/"),
        Family("text", "texts", text_authoring, ("variant",), "roguelike/data/texts/"),
        Family("typography", "display", typography_authoring, ("edit",), typography_authoring.PROFILE, typography_authoring.PROFILE),
    )


def family_for(path):
    return next((family for family in families() if family.matches(path)), None)
