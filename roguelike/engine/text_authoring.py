"""Ordinary found texts: variant-only authoring and the production reader adapter.

No gameplay code imports this module. Saved recovery identities include page/span
positions, so publication deliberately never revises an existing text identity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath

CONTRACT = "ordinary-found-text-1"
RESERVED_BASENAMES = ("text_item_map.json",)
PUBLICATION_NOTE = ("Creates a unique text ID/file. New game data loads discover it; saving does not bind it to an object or place. "
                    "Reopened texts can be inspected or copied to another variant. Same-ID revisions are deferred because saved recovery knowledge uses page/span positions.")
LIMITATIONS = "Ordinary prose only; no teaching, active deep tongue or special rendering authoring. No placement or natural acquisition proof."
VIEWS = ["text-pages", "text-references", "reader-preview"]
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
    "properties": {
        "id": {"type": "string", "readOnly": True},
        "title": {"type": "string", "title": "Reader title"},
        "condition": {"type": "string", "title": "Document condition", "default": "worn",
                      "x-suggestions": ["worn", "pristine", "damaged", "fragmentary", "stained", "weathered", "burned"],
                      "description": "Changes the panel tint and displayed condition. Pristine, worn, damaged, fragmentary and burned have tints; other strings use the worn tint. Without UI art, pristine/worn/damaged/fragmentary have borders; others use the brown fallback. Existing strings remain valid."},
        "pages": {"type": "array", "title": "Pages", "x-control": "ordered-records", "items": {
            "type": "object", "required": ["text"], "properties": {
                "text": {"type": "string", "title": "Page text", "x-control": "multiline", "x-initial": "",
                         "description": "Authored line breaks and blank paragraphs are retained. Literal [DAMAGED] renders corruption glyphs; [REDACTED] renders a solid block. Lexicon words still use production glyph/translation lookup."},
                "trailing": {"type": "boolean", "title": "Text ends here", "default": False,
                             "description": "Shows the reader's ending marker. Viewing an absent value does not insert false."},
            }}},
    }, "required": ["id", "pages"], "additionalProperties": True,
}


def capability(raw, path, pointer=""):
    reason = "Eligible ordinary text. Create a unique variant to publish."
    if pointer or not isinstance(raw, dict): reason = "Read-only: only single-object definitions are authorable."
    elif PurePosixPath(path).name.casefold() in RESERVED_BASENAMES: reason = "Read-only mapping: the loader excludes text_item_map.json at every depth."
    else:
        pages = raw.get("pages", [])
        nodes = [raw] + (pages if isinstance(pages, list) else [])
        for node in nodes:
            if not isinstance(node, dict): continue
            if "teach_words" in node:
                reason = "Read-only: teach_words changes knowledge; teaching authoring is outside this increment."; break
            if node.get("deep_tongue") not in (None, False) or ("deep_tongue" in node and type(node["deep_tongue"]) is not bool):
                reason = "Read-only: active or malformed deep_tongue mode is outside ordinary prose authoring."; break
            if "render_mode" in node and node["render_mode"] != "":
                reason = "Read-only: special or malformed render_mode (including alphabet) is outside ordinary prose authoring."; break
    return dict(contract=CONTRACT, editable=reason.startswith("Eligible"), reason=reason)


def sources(data_root):
    """Strict namespace inventory, including array locations, excluding loader maps."""
    from generation.structure_contract import read_document, StructureError
    found, malformed = {}, []
    for path in sorted((data_root / "texts").rglob("*.json")):
        # Match the loader's exact basename exclusion. A differently cased name
        # can still be loaded and must participate in namespace collision checks.
        if path.name in RESERVED_BASENAMES: continue
        relative = "roguelike/data/" + path.relative_to(data_root).as_posix()
        try: raw = read_document(path)
        except (StructureError, UnicodeError):
            malformed.append(relative); continue
        for index, row in enumerate(raw if isinstance(raw, list) else [raw]):
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                found.setdefault(row["id"], []).append(dict(path=relative, pointer=f"/{index}" if isinstance(raw, list) else "", definition=row))
            else: malformed.append(relative)
    return found, malformed


def validate_definition(raw, data, path, inventory):
    diagnostics = []
    def error(code, field, message):
        diagnostics.append(dict(severity="error", code=code, field=field, path=path,
                                asset=str(raw.get("id", "")) if isinstance(raw, dict) else "",
                                message=message, correction="Repair Source or choose a supported unique variant."))
    if not isinstance(raw, dict):
        error("TEXT_SHAPE", "", "Expected one text object."); return diagnostics
    cap = capability(raw, path)
    if not cap["editable"]: error("TEXT_CAPABILITY", "", cap["reason"])
    identifier = raw.get("id")
    if not isinstance(identifier, str) or not identifier.strip(): error("TEXT_ID", "id", "A nonempty string identity is required.")
    else:
        locations = [s for key, rows in inventory.items() if key.casefold() == identifier.casefold() for s in rows]
        if len(locations) != 1 or locations[0]["path"] != path or locations[0]["pointer"]:
            error("DUPLICATE_TEXT", "id", "Identity is ambiguous or not a single discoverable definition: " + ", ".join(s["path"] + s["pointer"] for s in locations))
        if data.texts.get(identifier) != raw: error("TEXT_LOADER_IDENTITY", "id", "Loaded text differs from this exact definition.")
    for field in ("title", "condition", "type", "reads_as"):
        if field in raw and not isinstance(raw[field], str): error("TEXT_STRING", field, "Expected a string.")
    if "lacunae" in raw and type(raw["lacunae"]) is not bool: error("TEXT_BOOLEAN", "lacunae", "Expected a boolean.")
    pages = raw.get("pages")
    if not isinstance(pages, list) or not pages:
        error("TEXT_PAGES", "pages", "At least one page object is required.")
    else:
        from engine.text_reader import parse_page
        for index, page in enumerate(pages):
            field = f"pages[{index}]"
            if not isinstance(page, dict): error("TEXT_PAGE", field, "Expected a page object."); continue
            if not isinstance(page.get("text"), str): error("TEXT_BODY", field+".text", "Expected a string body.")
            else: parse_page(page["text"])  # Production interpretation, never a parallel marker grammar.
            for key in ("trailing", "damaged"):
                if key in page and type(page[key]) is not bool: error("TEXT_BOOLEAN", field+"."+key, "Expected a boolean.")
    return diagnostics


def authoring_validate(raw, data, path, data_root):
    inventory, malformed = sources(data_root)
    result = validate_definition(raw, data, path, inventory)
    for source in malformed:
        result.append(dict(severity="error", code="TEXT_NAMESPACE", field="", path=source, asset="",
                           message="Malformed text source prevents an unambiguous namespace check.", correction="Repair that source before publication."))
    return result


def declared_references(identifier, data_root):
    """Direct declarations only; no inferred procedural or saved-instance graph."""
    if not isinstance(identifier, str) or not identifier.strip(): return []
    from generation.structure_contract import read_document, StructureError
    rows = []
    for directory in ("items", "layouts", "buildings"):
        for path in sorted((data_root / directory).rglob("*.json")):
            try: raw = read_document(path)
            except (StructureError, UnicodeError): continue
            def walk(node, pointer=""):
                if isinstance(node, dict):
                    if node.get("text_id") == identifier: rows.append(dict(path="roguelike/data/"+path.relative_to(data_root).as_posix(), pointer=pointer+"/text_id", kind="explicit text_id"))
                    for key, value in node.items(): walk(value, pointer+"/"+key.replace("~", "~0").replace("/", "~1"))
                elif isinstance(node, list):
                    for index, value in enumerate(node): walk(value, pointer+f"/{index}")
            walk(raw)
    mapping = data_root / "texts/text_item_map.json"
    if mapping.is_file():
        try:
            raw = read_document(mapping)
            for key in raw.keys():
                if key == identifier:
                    rows.append(dict(path="roguelike/data/texts/text_item_map.json", pointer="/"+key.replace("~", "~0").replace("/", "~1"), kind="text-item mapping"))
        except (StructureError, AttributeError): pass
    return rows


def authoring_context(raw, data, path, data_root, identity, digest, *, observe=False):
    records = []
    for index, record in enumerate(raw if isinstance(raw, list) and raw else [raw]):
        pointer = f"/{index}" if isinstance(raw, list) else ""
        cap = capability(record, path, pointer)
        diagnostics = authoring_validate(record, data, path, data_root)
        if cap["editable"] and any(d["severity"] == "error" for d in diagnostics):
            cap.update(editable=False, reason="Read-only: malformed or ambiguous source; inspect diagnostics.")
        if not isinstance(record, dict): record = {}
        records.append(dict(id=record.get("id", ""), pointer=pointer, definition=record, capability=cap,
                            diagnostics=diagnostics, references=declared_references(record.get("id"), data_root)))
    return dict(records=records, reference_coverage="Explicit text_id declarations in saved items, layouts and buildings, plus direct text-item mapping entries. No personal saves, dynamic selection, inferred or comprehensive graph.",
                inspection_note="type, reads_as, lacunae and page damaged are retained metadata: no active Python consumer establishes an effect. Language and alternate-render fields remain inspectable; active deep_tongue, teach_words and special render_mode are read-only.",
                binding_note="Bind a saved ID with text_id on an existing readable item (for example letter) in a separately authored layout special. Saving this definition alone does not create or place that item.")


def reference_options(context): return {}


def authoring_evidence(context):
    return dict(semantic_verified=bool(context and len(context["records"]) == 1 and context["records"][0]["capability"]["editable"]
                                      and not any(d["severity"] == "error" for d in context["records"][0]["diagnostics"])))


def authoring_preview(raw, data, root, inputs):
    return render_reader(raw, data, root, inputs)


def render_reader(raw, data, root, inputs, *, typography_candidate=None, known_words=()):
    """One bounded production frame; selection is view state, never content."""
    import base64
    import io
    import os
    from types import SimpleNamespace
    if not isinstance(inputs, dict) or set(inputs) != {"page", "scroll"} or any(type(inputs[k]) is not int for k in inputs):
        raise ValueError("Reader preview expects integer page and scroll inputs only.")
    page, scroll = inputs["page"], inputs["scroll"]
    if not 0 <= page < len(raw["pages"]) or not 0 <= scroll <= 10000000:
        raise ValueError("Reader page or scroll outside bounded range.")
    if len(raw["pages"][page]["text"]) > 65536 or len(raw.get("title", "")) > 2048:
        raise ValueError("Reader preview is bounded to 65,536 characters per page and 2,048 title characters.")
    os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    import pygame
    from components.language import Language
    from engine.display_config import DisplayConfig
    from engine.item_factory import ItemFactory
    from engine.item_system import ItemSystem
    from engine.text_reader import TextReader, parse_page
    from rendering.ui_registry import UIRegistry
    old = os.getcwd()
    try:
        os.chdir(root / "roguelike")
        pygame.init(); pygame.display.set_mode((1, 1))
        display = DisplayConfig.from_config(); display.init(project_root=root, typography_candidate=typography_candidate)
        registry = UIRegistry(); registry.load()
        if not registry.has("weathered_temple"): raise ValueError("Missing production weathered_temple UI resource.")
        reader = TextReader(); reader.init(display)
        item = ItemFactory(data).create("letter"); item.text_id = raw["id"]
        if data.items["letter"].get("render_mode") or item.on_use != "read": raise ValueError("Saved letter is no longer an ordinary reader item.")
        engine = SimpleNamespace(data=data, player=SimpleNamespace(language=Language(known_deep_words=set(known_words))), text_reader=reader, ui_registry=registry)
        ItemSystem()._use_read(item, engine)
        for _ in range(page): reader.handle_key(pygame.K_RIGHT)
        screen = pygame.Surface((960, 640)); reader.render(screen, engine)
        # A selected pixel offset is clamped by the actual reader during render.
        reader._scroll = scroll; reader.render(screen, engine)
        output = io.BytesIO(); pygame.image.save(screen, output, "preview.png")
        png = output.getvalue()
        if len(png) > 2 * 1024 * 1024: raise ValueError("Reader frame exceeded the 2 MiB artifact limit.")
        return dict(kind="reader-frame", image="data:image/png;base64,"+base64.b64encode(png).decode(), image_sha256=hashlib.sha256(png).hexdigest(),
                    width=960, height=640, inputs=inputs, page=reader._page, scroll=reader._scroll, max_scroll=reader._max_scroll,
                    viewport_height=reader._viewport_height, visible_rows=reader._visible_rows, total_rows=len(reader._layout_rows),
                    marker_types=[span["type"] for span in parse_page(raw["pages"][page]["text"]) if span["type"] != "normal"],
                    setup=("Saved letter definition; weathered_temple panel; isolated Language with " + str(len(known_words)) + " known words and no recovery; saved lexicon/UI. " + ("Candidate typography." if typography_candidate is not None else "Saved typography profile and font dependencies.") + " Disposable reader context; no personal save, time or world generation."),
                    consumer="ItemFactory.create → ItemSystem._use_read → TextReader.render", dependencies="candidate typography / saved reader files" if typography_candidate is not None else "saved files", typography=display.typography)
    finally:
        pygame.quit(); os.chdir(old)
