"""W0 single-request JSONL worker. Rules are imported from the selected checkout.

One process per request keeps module/data snapshots coherent and makes cancellation
bounded. Only stdout is protocol; all game diagnostics go to stderr.
"""
from __future__ import annotations
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

sys.dont_write_bytecode = True
# This small preview needs no parallel BLAS. Bound native thread-pool overhead
# before importing NumPy/tcod; the game's algorithms and data stay unchanged.
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
PROTOCOL = 8
WORKER_VERSION = "0.9.0"
ROUTE = "authored_submap"
EDIT_ROUTE = "ordinary_building"
POOL_ROUTE = "contextual_loot_pool"
ITEM_ROUTE = "item_definition"
RECIPE_ROUTE = "recipe_definition"
CREATURE_ROUTE = "creature_definition"
LAYOUT_CONTRACT = "authored-room-2"
G17_EXAMPLE = "roguelike/docs/examples/g17_authored_creature_room.json"
G17_ACCESS = "roguelike/docs/examples/g17_authored_creature_room.access.json"
DEPENDENCIES = {"pygame": "2.6.1", "tcod": "19.3.0", "numpy": "2.4.6",
                "cffi": "2.1.1", "pycparser": "3.11", "typing_extensions": "4.16.0"}
MAX_REQUEST = 4 * 1024 * 1024


class BridgeError(Exception):
    def __init__(self, code, message, remedy):
        self.code, self.message, self.remedy = code, message, remedy
        super().__init__(message)


def fail(code, message, remedy):
    raise BridgeError(code, message, remedy)


def checked_root(value):
    root = Path(value).resolve(strict=True)
    for name in ("roguelike/engine/data_loader.py", "roguelike/generation/structure_contract.py",
                 "roguelike/generation/structure_preview.py", "roguelike/data/terrain.json", "requirements-baseline.txt"):
        path = root / name
        if not path.is_file() or not path.resolve().is_relative_to(root):
            fail("INVALID_PROJECT", f"Missing or external {name}", "Select the Resonance repository root.")
    # The active data loader recursively discovers files. Refuse junction/symlink
    # escapes before invoking it; no personal save tree is traversed.
    for folder in (root / "roguelike").iterdir():
        if folder.name in ("saves", "__pycache__"):
            continue
        if not folder.resolve().is_relative_to(root) or folder.resolve().is_relative_to(root / "roguelike/saves"):
            fail("PATH_ESCAPE", str(folder), "Use a checkout without external source/data links.")
        if folder.is_dir():
            for base, dirs, files in os.walk(folder, followlinks=False):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for name in dirs + files:
                    p = Path(base) / name
                    if not p.resolve().is_relative_to(root) or p.resolve().is_relative_to(root / "roguelike/saves"):
                        fail("PATH_ESCAPE", str(p), "Remove the external source/data link.")
    return root


def source_identity(root):
    def git(*args):
        try:
            return subprocess.check_output(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(root), *args], cwd=root, stderr=subprocess.DEVNULL,
                                           timeout=5, creationflags=0x08000000 if os.name == "nt" else 0).decode().strip()
        except (OSError, subprocess.SubprocessError):
            return None
    files = sorted(p for p in (root / "roguelike").rglob("*.py") if "__pycache__" not in p.parts and "saves" not in p.parts)
    digest = hashlib.sha256()
    for p in files:
        digest.update(p.relative_to(root).as_posix().encode()); digest.update(p.read_bytes())
    top = git("rev-parse", "--show-toplevel")
    owned_git = top is not None and Path(top).resolve() == root
    status = git("status", "--porcelain", "--", "roguelike", "requirements-baseline.txt") if owned_git else None
    data_root = root / "roguelike/data"
    catalog = hashlib.sha256(json.dumps([
        (p.relative_to(data_root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(data_root.rglob("*.json"))], separators=(",", ":")).encode()).hexdigest()
    resources = hashlib.sha256()
    for directory in ("assets/Fonts", "assets/ui"):
        for p in sorted((root / "roguelike" / directory).rglob("*")):
            if p.is_file(): resources.update(p.relative_to(root).as_posix().encode()); resources.update(p.read_bytes())
    return {"root": str(root), "commit": git("rev-parse", "HEAD") if owned_git else None,
            "branch": git("branch", "--show-current") if owned_git else None,
            "game_dirty": None if status is None else bool(status),
            "game_source_sha256": digest.hexdigest(), "catalog_sha256": catalog, "resources_sha256": resources.hexdigest()}


def runtime_check():
    if sys.version_info[:2] != (3, 11):
        fail("RUNTIME_MISMATCH", f"Python {platform.python_version()} is outside W0's tested 3.11 runtime.",
             "Use the pinned CPython 3.11 environment or the packaged runtime.")
    versions = {}
    for name, expected in DEPENDENCIES.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            fail("MISSING_DEPENDENCY", f"Missing {name}=={expected}.", "Install requirements-baseline.txt in the selected Python environment.")
        versions[name] = actual
        if actual != expected:
            fail("DEPENDENCY_MISMATCH", f"{name}: expected {expected}, found {actual}.", "Use the exact pinned game dependencies.")
    # Metadata alone does not prove native wheels and their DLLs can load.
    import pygame, tcod, numpy, cffi
    return {"python": platform.python_version(), "executable": sys.executable, "dependencies": versions, "compatible": True, "numeric_threads": 1}


def install_guard(root, scratch):
    """Defense against incidental production writes; not a sandbox for hostile Python."""
    save_root = root / "roguelike/saves"
    def resolve(value):
        return None if isinstance(value, int) else Path(os.fsdecode(value)).resolve()
    def writable(value):
        p = resolve(value)
        if p is not None and not p.is_relative_to(scratch):
            raise PermissionError(f"Workbench read-only boundary: {p}")
    def audit(event, args):
        if event == "open":
            p = resolve(args[0])
            if p is not None and p.is_relative_to(save_root):
                raise PermissionError("Workbench never opens personal saves")
            mode, flags = args[1], args[2]
            if (mode and any(c in mode for c in "wax+")) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                writable(args[0])
        elif event in ("os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.utime"):
            writable(args[0])
        elif event in ("os.rename", "os.link", "os.symlink"):
            writable(args[0]); writable(args[1])
        elif event in ("subprocess.Popen", "os.system"):
            raise PermissionError("No subprocesses in game preview operations")
    sys.addaudithook(audit)


def asset_path(root, value, *, new=False):
    if not isinstance(value, str) or "\\" in value or ":" in value or ".." in value.split("/"):
        fail("PATH_ESCAPE", "Invalid asset path.", "Choose a shipped authored layout from the list.")
    relative = Path(value)
    from generation.structure_contract import ELIGIBILITY
    layout = len(relative.parts) == 4 and relative.parts[:3] == ("roguelike", "data", "layouts")
    building = (len(relative.parts) == 5 and relative.parts[:3] == ("roguelike", "data", "buildings")
                and relative.parts[3] in ELIGIBILITY.keys() - {"plaza"})
    pool = len(relative.parts) == 4 and relative.parts[:3] == ("roguelike", "data", "loot_pools")
    from engine.content_authoring import family_for
    family = family_for(value)
    creature = len(relative.parts) >= 4 and relative.parts[:3] == ("roguelike", "data", "entities")
    example = value == G17_EXAMPLE and not new
    if relative.is_absolute() or not (layout or building or pool or family or creature or example) or relative.suffix != ".json":
        fail("UNSUPPORTED_ASSET", value, "Select an ordinary building, contextual pool or read-only authored layout.")
    path = (root / relative).resolve(strict=not new)
    if not path.is_relative_to(root / "roguelike/data") and not (example and path == root / G17_EXAMPLE):
        fail("PATH_ESCAPE", value, "Choose an asset inside the selected repository.")
    return path


def discover(root, data=None):
    """Same immediate-folder convention as StructureCatalog, including invalid candidates."""
    from generation.structure_contract import ELIGIBILITY, read_document, StructureError
    rows = []
    candidates = list((root / "roguelike/data/buildings").glob("*/*.json"))
    for p in sorted(candidates):
        if p.parent.name != "plaza": continue
        category = p.parent.name if p.parent.parent.name == "buildings" else None
        pool = p.parent.name == "loot_pools"
        editable = pool or category in ELIGIBILITY.keys() - {"plaza"}
        route = POOL_ROUTE if pool else EDIT_ROUTE if editable else "plaza" if category == "plaza" else ROUTE
        try:
            raw = read_document(p)
            if not isinstance(raw, dict): raw = {}
            diagnostics = []
        except StructureError as error:
            raw = {}; diagnostics = [d.json() for d in error.diagnostics]
        rows.append({"path": p.relative_to(root).as_posix(), "id": raw.get("id") if isinstance(raw.get("id"), str) else p.stem,
                     "name": str(raw.get("name", raw.get("description", ""))), "category": category,
                     "route": route, "editable": editable,
                     "width": raw.get("width") if type(raw.get("width")) is int else None,
                     "height": raw.get("height") if type(raw.get("height")) is int else None,
                     "provenance": "Selected checkout / content file", "validation": "invalid" if diagnostics else "not yet checked",
                     "diagnostics": diagnostics})
    from engine.content_authoring import families
    for family in families(): rows.extend(family.discover(root))
    return rows


def definition_sources(data_root, family):
    from engine.content_authoring import definition_sources as sources
    return sources(data_root, family)


def pool_diagnostics(raw, data, path, data_root):
    # Compatibility for old probes; publication has only the registered owner.
    from engine.pool_authoring import authoring_validate
    return authoring_validate(raw, data, path, data_root)


def capability_diagnostics(envelope, path):
    return [dict(severity="error", code="UNSUPPORTED_CAPABILITY", path=path, asset="", field="contract",
                 message=message, correction="Use a compatible game-owned descriptor; inspect exact Source.") for message in envelope["problems"]]


def unique_diagnostics(diagnostics):
    """Remove only exact shared-path duplicates, including all location metadata."""
    seen = set(); result = []
    for diagnostic in diagnostics:
        key = json.dumps(diagnostic, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key); result.append(diagnostic)
    return result


def family_validation(family, request, root, scratch, identity):
    from engine.data_loader import DataLoader
    from engine.content_authoring import family_for
    from generation.structure_contract import read_document, StructureError
    source_asset = request.get("source_asset") or request["asset"]
    path = asset_path(root, request["asset"], new=request["asset"] != source_asset)
    draft = request.get("draft")
    if not isinstance(draft, str) or len(draft.encode("utf-8")) > 1024 * 1024:
        fail("MALFORMED_REQUEST", "Expected UTF-8 draft up to 1 MiB.", "Use a bounded definition.")
    source_family = family_for(source_asset)
    if not source_family or source_family.id != family.id:
        fail("SOURCE_ENTITLEMENT", "Candidate and original must belong to the same registered family.", "Open the original discovered source.")
    original = asset_path(root, source_asset)
    digest = hashlib.sha256(draft.encode("utf-8")).hexdigest()
    diagnostics = []; context = None; syntax = False
    rendered = None
    original_operations = []
    envelope = family.envelope(None)
    diagnostics += capability_diagnostics(envelope, source_asset)
    copied = scratch / "data"
    try:
        reader = getattr(family.module, "read_source", read_document)
        original_raw = reader(original)
        from engine.pool_authoring import load_authoring_data
        original_data = family.module.load_authoring_data(root / "roguelike/data") if family.id == "selection" else load_authoring_data(root / "roguelike/data") if family.id in ("pool","building") else DataLoader(str(root / "roguelike/data"))
        original_context = family.context(original_raw, original_data, source_asset, root / "roguelike/data", identity, hashlib.sha256(original.read_bytes()).hexdigest(), resource_root=root)
        original_operations = family.operations_for(original_context)
        unchanged_inspection = getattr(family.module, "READONLY_CONSTRUCTION", False) and source_asset == request["asset"] and draft.encode("utf-8") == original.read_bytes()
        if not family.eligible(original_context) and not unchanged_inspection:
            diagnostics.append(dict(severity="error", code="SOURCE_ENTITLEMENT", path=source_asset, asset="", field="",
                message="Original discovered source is read-only; changing candidate shape cannot upgrade it.", correction="Choose a supported unambiguous original source."))
        if family.id in ("building", "selection"):
            from generation.structure_contract import Diagnostic
            if not family.eligible(original_context):
                raise StructureError([Diagnostic(**{k:d[k] for k in ('severity','code','path','asset','field','message','correction')}) for d in diagnostics])
            try: authority_candidate=json.loads(draft if family.id == "selection" else draft.lstrip("\ufeff"))
            except ValueError: authority_candidate=None
            if authority_candidate is not None:
                authority=family.authorize(original_raw,authority_candidate,source_asset,request["asset"],original_data)
                if family.id == "building": authority += family.module.target_problems(authority_candidate,source_asset,request["asset"],root/"roguelike/data")
                if authority: raise StructureError([Diagnostic(**d) for d in authority])
        shutil.copytree(root / "roguelike/data", copied)
        selected = copied / family.staging_path(request["asset"])
        selected.write_bytes(draft.encode("utf-8"))
        raw = reader(selected); syntax = True
        data = load_authoring_data(copied) if family.id=="pool" else DataLoader(str(copied))
        if not unchanged_inspection:
            diagnostics += family.authorize(original_raw, raw, source_asset, request["asset"], data)
        diagnostics += family.validate(raw, data, request["asset"], copied, resource_root=root)
        if not any(d["severity"] == "error" for d in diagnostics):
            context = family.context(raw, data, request["asset"], copied, identity, digest, observe=True, resource_root=root, seed=request.get("seed"))
            diagnostics += [d for record in context["records"] for d in record["diagnostics"]]
            if request.get("preview_inputs") is not None and not any(d["severity"] == "error" for d in diagnostics):
                rendered = family.preview(raw, data, root, request["preview_inputs"])
                rendered.update(draft_sha256=digest, path=request["asset"], source=identity,
                                contract=family.module.CONTRACT, descriptor_sha256=envelope["descriptor_sha256"],
                                runtime=dict(python=platform.python_version(), dependencies=DEPENDENCIES),
                                observed_at_utc=datetime.now(timezone.utc).isoformat())
    except StructureError as error:
        diagnostics += [d.json() for d in error.diagnostics]
        if isinstance(error.__cause__, json.JSONDecodeError):
            for d in diagnostics: d.update(line=error.__cause__.lineno, column=error.__cause__.colno)
    for d in diagnostics: d["path"] = d["path"].replace(str(copied), "roguelike/data").replace("\\", "/")
    diagnostics = unique_diagnostics(diagnostics)
    after = source_identity(root)
    if any(after[k] != identity[k] for k in ("game_source_sha256", "catalog_sha256", "resources_sha256")):
        fail("SOURCE_CHANGED", "Dependencies changed during validation.", "Reopen and validate again.")
    evidence = family.module.authoring_evidence(context)
    if evidence.get("preview"):
        evidence["preview"].update(original_source_path=source_asset,original_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                                  layout_contract=envelope["contract"],descriptor_sha256=envelope["descriptor_sha256"],
                                  runtime=dict(python=platform.python_version(),dependencies=DEPENDENCIES))
    valid = syntax and evidence["semantic_verified"] and not any(d["severity"] == "error" for d in diagnostics)
    result = dict(valid=valid, syntax_valid=syntax, contract_valid=valid, references_valid=valid,
                diagnostics=diagnostics, draft_sha256=digest, route=family.route, contract="g2-3",
                family=family.envelope(context, operations=original_operations), source_asset=source_asset,
                source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                worker_version=WORKER_VERSION, worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                path=request["asset"], source=identity, population_verified=False, preview=None, family_preview=rendered,
                limitations=family.module.LIMITATIONS)
    result.update(evidence)
    return result


def draft_validation(request, root, scratch, identity):
    from engine.data_loader import DataLoader
    from generation.structure_contract import read_document, compile_structure, StructureError
    from engine.content_authoring import family_for
    family = family_for(request["asset"])
    if family:
        return family_validation(family, request, root, scratch, identity)
    fail("UNSUPPORTED_ASSET", "Draft source is not registered.", "Open a registered content source.")



def run(request, root, scratch):
    identity = source_identity(root)
    runtime = runtime_check()
    install_guard(root, scratch)
    sys.path.insert(0, str(root / "roguelike"))
    os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
    import config
    config.DEBUG_MODE = False
    from engine.data_loader import DataLoader
    from generation.structure_contract import CONTRACT_VERSION, CAPABILITIES, compile_structure, read_document, StructureError
    from engine.content_authoring import families, family_for
    from engine.creature_authoring import CONTRACT as CREATURE_CONTRACT
    from generation.structure_preview import preview
    registered = families()
    imported_sources = {}
    for name in ("config", "engine.data_loader", "generation.structure_contract", "generation.structure_preview", "engine.content_authoring", "engine.creature_authoring", *(f.module.__name__ for f in registered)):
        module_path = Path(sys.modules[name].__file__).resolve()
        if not module_path.is_relative_to(root / "roguelike"):
            fail("SOURCE_IMPORT_MISMATCH", f"{name} was imported outside the selected project.", "Use the selected current checkout with the pinned isolated interpreter.")
        imported_sources[name] = module_path.relative_to(root).as_posix()
    runtime.update(imports_verified=True, game_imports=imported_sources)
    if CONTRACT_VERSION != "g2-3":
        fail("CONTRACT_MISMATCH", f"Unsupported structure contract {CONTRACT_VERSION}.", "Update the Workbench adapter after reviewing this game's contract.")
    op = request["op"]
    if op in ("validate_draft", "preview_draft"):
        return draft_validation(request, root, scratch, identity)
    catalog_error = None
    try:
        selected_family = family_for(request.get("asset", ""))
        if selected_family and selected_family.id == "selection" or op in ("identify", "describe"):
            from engine.selection_authoring import load_authoring_data as selection_data
            data = selection_data(root / "roguelike/data")
        else:
            data = DataLoader(str(root / "roguelike/data"))
        identity["catalog_sha256"] = data.structure_catalog.identity
    except StructureError as error:
        data = None; catalog_error = error
        # Retain the measured source stamp when the loader rejects a catalog.
        # Erasing it would misreport unchanged malformed input as SOURCE_CHANGED
        # and prevent the existing inspect-only repair/diagnostic path.
        selected_family=family_for(request.get("asset", ""))
        if op=="inspect" and selected_family and selected_family.id in ("pool","building"):
            from engine.pool_authoring import load_authoring_data
            data=load_authoring_data(root / "roguelike/data");catalog_error=None
    if op == "identify":
        return {"worker_version": WORKER_VERSION, "worker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "protocol": PROTOCOL, "source": identity, "runtime": runtime, "contract": CONTRACT_VERSION,
                "route": ROUTE, "validator": "generation.structure_contract.compile_structure",
                "preview": "generation.structure_preview.preview → engine.scene_generation.create_submap → generation.local_gen.generate_submap",
                "edit_route": EDIT_ROUTE,
                "families": [f.envelope(None) for f in registered],
                "creature_contract": CREATURE_CONTRACT,
                "layout_contract": LAYOUT_CONTRACT,
                "unavailable": ["authored-submap inactive decor-layer authoring", "advanced item/world-placement recipe editing", "native world selection", "game renderer/FOV", "combat simulation"],
                "health": "catalog needs repair" if catalog_error else "ready",
                "diagnostics": [d.json() for d in catalog_error.diagnostics] if catalog_error else []}
    if op == "describe":
        return {"route": ROUTE, "capabilities": CAPABILITIES[ROUTE],
                "assets": discover(root, data), "unsupported": ["plaza (read-only)", "entrances", "advanced item editing", "legacy loot tables", "world-placement/legacy/deprecated recipe editing", "advanced creature editing", "generation profiles"]}
    path = asset_path(root, request.get("asset"))
    before = path.stat()
    source = path.read_bytes()
    route = EDIT_ROUTE if path.parent.parent.name == "buildings" else ROUTE
    category = path.parent.name if route == EDIT_ROUTE else None
    raw_error = None
    try:
        source_family = family_for(request["asset"])
        raw = getattr(source_family.module, "read_source", read_document)(path) if source_family else read_document(path)
    except StructureError as error:
        raw = {}; raw_error = error
    family = family_for(request["asset"])
    if family:
        spatial = family.route in (ROUTE,EDIT_ROUTE)
        if op not in (("inspect", "preview") if spatial else ("inspect",)):
            fail("UNSUPPORTED_OPERATION", "Registered content uses exact-source validation.", "Open the source and validate its draft.")
        if request.get("invalid_fixture"):
            if not spatial or op != "inspect": fail("UNSUPPORTED_OPERATION", "Invalid fixture requires a spatial inspection.", "Inspect the room.")
            raw = dict(raw, width=len(raw["layers"][0])+1)
        context = family.context(raw, data, request["asset"], root / "roguelike/data", identity, hashlib.sha256(source).hexdigest(), observe=getattr(family.module, "OBSERVE_INSPECTION", False), resource_root=root, seed=request.get("seed")) if data and not raw_error else None
        diagnostics = ([d.json() for d in (raw_error or catalog_error).diagnostics] if raw_error or catalog_error else
                       [d for r in context["records"] for d in r["diagnostics"]])
        envelope = family.envelope(context)
        diagnostics += capability_diagnostics(envelope, request["asset"])
        after = source_identity(root)
        if path.read_bytes() != source or any(after[k] != identity[k] for k in ("game_source_sha256", "catalog_sha256", "resources_sha256")):
            fail("SOURCE_CHANGED", "Source or dependency changed during inspection.", "Reopen the document.")
        single = raw if isinstance(raw, dict) else {}
        layers = single.get("layers")
        width = len(layers[0]) if isinstance(layers,list) and layers and isinstance(layers[0],str) else None
        height = len(layers) if isinstance(layers,list) else None
        if op == "preview":
            result = context.get("preview") if context else None
            return result or dict(valid=False,diagnostics=diagnostics)
        return dict(id=single.get("id", path.stem), path=request["asset"], route=family.route,
                    description=str(single.get("description", "")), valid=not any(d["severity"] == "error" for d in diagnostics),
                    editable=family.eligible(context) and envelope["compatible"], family=envelope,
                    **({"pool_context":context} if family.id=="pool" else {}),
                    **({"catalog":context["catalog"]} if spatial and context else {}),
                    diagnostics=unique_diagnostics(diagnostics), raw=json.dumps(raw,indent=2) if request.get("invalid_fixture") else source.decode("utf-8"), sha256=hashlib.sha256(source).hexdigest(),
                    mtime_ns=str(before.st_mtime_ns), source_unchanged=True, source=identity,
                    width=single.get("width",width),height=single.get("height",height),
                    special_count=len(single["special_tiles"]) if isinstance(single.get("special_tiles"),list) else 0, **family.module.authoring_evidence(context))
    invalid = request.get("invalid_fixture", False)
    if type(invalid) is not bool or (invalid and op != "inspect"):
        fail("MALFORMED_REQUEST", "Invalid fixture flag.", "Use inspect with a boolean invalid_fixture.")
    selected = path
    if invalid:
        # Complete disposable JSON, fed through the identical read/compile route.
        raw["width"] = len(raw["layers"][0]) + 1
        selected = scratch / "invalid-dimension.json"
        selected.write_text(json.dumps(raw), encoding="utf-8")
        raw = read_document(selected)
    try:
        if raw_error: raise raw_error
        if catalog_error: raise catalog_error
        compiled = compile_structure(raw, route, data, path=str(selected), category=category)
        diagnostics = [d.json() for d in compiled.diagnostics]
        from engine.pool_authoring import container_dependencies
        diagnostics += container_dependencies(raw,data,request["asset"],root / "roguelike/data")
        valid = not any(d["severity"]=="error" for d in diagnostics)
    except StructureError as error:
        diagnostics = [d.json() for d in error.diagnostics]
        valid = False
    after = path.stat()
    if path.read_bytes() != source or (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        fail("SOURCE_CHANGED", "Source changed during inspection.", "Finish external edits, then reopen the project.")
    if op == "inspect":
        raw = raw if isinstance(raw, dict) else {}
        return {"id": raw.get("id") if isinstance(raw.get("id"), str) else path.stem,
                "path": path.relative_to(root).as_posix(), "route": route, "category": category,
                "width": raw.get("width") if type(raw.get("width")) is int else None,
                "height": raw.get("height") if type(raw.get("height")) is int else None, "description": str(raw.get("description", "")),
                "special_count": len(raw.get("special_tiles", [])) if isinstance(raw.get("special_tiles", []), list) else 0,
                "valid": valid, "diagnostics": diagnostics,
                "raw": source.decode("utf-8") if not invalid else json.dumps(raw, indent=2), "invalid_fixture": invalid,
                "sha256": hashlib.sha256(source).hexdigest(), "mtime_ns": str(before.st_mtime_ns),
                "source_unchanged": True, "source": identity,
                "editable": route == EDIT_ROUTE,
                "layout_contract": LAYOUT_CONTRACT if route == ROUTE else None,
                "catalog": __import__("engine.room_authoring",fromlist=["catalog"]).catalog(data, root / "roguelike/data") if data else None}
    if not valid:
        return {"valid": False, "diagnostics": diagnostics}
    seed = request.get("seed", 20261023)
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        fail("MALFORMED_REQUEST", "Seed must be an integer between 0 and 2147483647.", "Enter a supported seed.")
    # Bound legacy global RNG consumers in this disposable process as well as
    # passing the production GenerationContext seed. No gameplay replay promise.
    random.seed(seed)
    import numpy as np
    np.random.seed(seed)
    start = time.perf_counter()
    report, local_map, _ = preview(raw, route, data, seed=seed, path=str(path), category=category)
    rows = report["terrain"]
    assert local_map.width == 80 and local_map.height == 43 and len(rows) == 43 and all(len(r) == 80 for r in rows)
    for y, row in enumerate(rows):
        for x, tile in enumerate(row):
            assert tile == str(local_map.tiles[x, y]["terrain"])
    legend = {tile: {"walkable": bool(data.terrain[tile].get("walkable", True)),
                     "transparent": bool(data.terrain[tile].get("transparent", True))} for tile in sorted({t for r in rows for t in r})}
    return {"valid": True, "width": 80, "height": 43, "terrain": rows, "legend": legend,
            "decor": report["decor"], "items": report["items"], "containers": report["containers"], "actors": report["actors"],
            "spawn": report.get("spawn"), "origin": report["origin"], "passed": report["passed"],
            "occupant_diagnostics": report["occupant_diagnostics"], "generation_revision": report["generation_revision"],
            "seed": seed, "scene_seed": str(report.get("scene_seed", local_map.generation_context.scene_seed)),
            "scene_address": report.get("scene_address", list(local_map.generation_context.address)),
            "candidate_sha256": report["candidate_identity"], "source": identity, "asset": raw["id"],
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
            "terrain_sha256": hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest(),
            "context": f"Controlled {route}; centered, no rotation; global Python/NumPy RNG seeded; no campaign opened. Direct consumer population only; no natural selection or access proof.",
            "rendering": "Production-data-backed Workbench rendering; revealed terrain and initial objects, not Pygame/tcod or player FOV."}


def main():
    request_id = None
    start = time.perf_counter()
    try:
        line = sys.stdin.buffer.readline(MAX_REQUEST + 1)
        if len(line) > MAX_REQUEST:
            fail("MALFORMED_REQUEST", "Request exceeds 4 MiB.", "Use a bounded request.")
        request = json.loads(line)
        if not isinstance(request, dict):
            fail("MALFORMED_REQUEST", "Expected an object.", "Use the versioned W0 protocol.")
        request_id = request.get("id")
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            fail("MALFORMED_REQUEST", "Expected a correlation ID.", "Supply a short string id.")
        if type(request.get("protocol")) is not int or request["protocol"] != PROTOCOL:
            fail("PROTOCOL_MISMATCH", f"Worker requires protocol {PROTOCOL}.", "Use matching Workbench frontend, host and worker versions.")
        if request.get("op") not in ("identify", "describe", "inspect", "preview", "validate_draft", "preview_draft") or set(request) - {"id", "protocol", "op", "asset", "seed", "invalid_fixture", "draft", "source_asset", "preview_inputs"}:
            fail("MALFORMED_REQUEST", "Unsupported operation or fields.", "Only identify, describe, inspect and preview are available.")
        if len(sys.argv) != 3 or sys.argv[1] != "--root":
            fail("INVALID_PROJECT", "Expected one --root argument.", "Launch through the Workbench host.")
        root = checked_root(sys.argv[2])
        with tempfile.TemporaryDirectory(prefix="resonance-w0-") as directory:
            scratch = Path(directory).resolve()
            os.chdir(scratch)
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    result = run(request, root, scratch)
            finally:
                # Windows cannot remove a process's current working directory.
                # Preserve the original structured error on every failure path.
                os.chdir(Path(tempfile.gettempdir()))
        response = {"protocol": PROTOCOL, "id": request_id, "ok": True, "result": result}
    except Exception as error:
        if isinstance(error, BridgeError):
            detail = {"code": error.code, "message": error.message, "remedy": error.remedy}
        elif isinstance(error, ModuleNotFoundError):
            detail = {"code": "MISSING_DEPENDENCY", "message": str(error), "remedy": "Rebuild the pinned runtime; ensure the selected checkout is complete."}
        elif isinstance(error, (json.JSONDecodeError, UnicodeError)):
            detail = {"code": "MALFORMED_REQUEST", "message": str(error), "remedy": "Send one UTF-8 JSON request."}
        else:
            traceback.print_exc(file=sys.stderr)
            detail = {"code": "PREVIEW_FAILED", "message": str(error), "remedy": "Check the selected source, dependencies and production diagnostics; reopen to retry."}
            if hasattr(error, "diagnostics"):
                detail["diagnostics"] = [d.json() for d in error.diagnostics]
        response = {"protocol": PROTOCOL, "id": request_id, "ok": False, "error": detail}
    response["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 2)
    sys.stdout.write(json.dumps(response, ensure_ascii=True, allow_nan=False) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
