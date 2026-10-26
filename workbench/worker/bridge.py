"""W0 single-request JSONL worker. Rules are imported from the selected checkout.

One process per request keeps module/data snapshots coherent and makes cancellation
bounded. Only stdout is protocol; all game diagnostics go to stderr.
"""
from __future__ import annotations
import contextlib
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
PROTOCOL = 4
WORKER_VERSION = "0.4.0"
ROUTE = "authored_submap"
EDIT_ROUTE = "ordinary_building"
POOL_ROUTE = "contextual_loot_pool"
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
    return {"root": str(root), "commit": git("rev-parse", "HEAD") if owned_git else None,
            "branch": git("branch", "--show-current") if owned_git else None,
            "game_dirty": None if status is None else bool(status),
            "game_source_sha256": digest.hexdigest(), "catalog_sha256": catalog}


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
    if relative.is_absolute() or not (layout or building or pool) or relative.suffix != ".json":
        fail("UNSUPPORTED_ASSET", value, "Select an ordinary building, contextual pool or read-only authored layout.")
    path = (root / relative).resolve(strict=not new)
    if not path.is_relative_to(root / "roguelike/data"):
        fail("PATH_ESCAPE", value, "Choose an asset inside the selected repository.")
    return path


def discover(root):
    """Same immediate-folder convention as StructureCatalog, including invalid candidates."""
    from generation.structure_contract import ELIGIBILITY, read_document, StructureError
    rows = []
    candidates = list((root / "roguelike/data/layouts").glob("*.json"))
    candidates += list((root / "roguelike/data/buildings").glob("*/*.json"))
    candidates += list((root / "roguelike/data/loot_pools").glob("*.json"))
    for p in sorted(candidates):
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
    return rows


def definition_sources(data_root, family):
    """Mirror _load_dir's object/array file convention, without choosing a duplicate winner."""
    sources = {}
    for path in sorted((data_root / family).rglob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for index, row in enumerate(raw if isinstance(raw, list) else [raw]):
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                sources.setdefault(row["id"], []).append({"path": "roguelike/data/" + path.relative_to(data_root).as_posix(),
                    "pointer": f"/{index}" if isinstance(raw, list) else "", "definition": row})
    return sources


def pool_diagnostics(raw, data, path, data_root):
    """Use the game's existing container-pool validator, adding source identity checks.

    DataLoader silently skips malformed files and overwrites duplicate IDs. Those
    behaviors cannot safely authorize editing a particular source file.
    """
    from generation.structure_contract import Validator
    from types import SimpleNamespace
    identifier = raw.get("id") if isinstance(raw, dict) else None
    validator = Validator(SimpleNamespace(items=data.items, loot_pools={identifier: raw}) if isinstance(identifier, str) else data,
                          path, str(identifier or "<pool>"), EDIT_ROUTE)
    if not isinstance(identifier, str) or not identifier:
        validator.issue("POOL_ID", "id", "Pool requires a nonempty string id.", "Set a unique pool ID.")
        return [d.json() for d in validator.diagnostics]
    validator.pool(identifier, "pool")
    sources = definition_sources(data_root, "loot_pools")
    locations = sources.get(identifier, [])
    if len(locations) != 1 or locations[0]["path"] != path or locations[0]["pointer"]:
        validator.issue("DUPLICATE_ID", "id", f"Pool {identifier!r} does not resolve uniquely to {path}: " +
                        ", ".join(s["path"] + s["pointer"] for s in locations), "Use a unique ID in one object file.")
    if data.loot_pools.get(identifier) != raw:
        validator.issue("LOADER_IDENTITY", "id", f"DataLoader did not load the exact definition {identifier!r} from {path}.",
                        "Use plain UTF-8 JSON accepted by DataLoader; resolve duplicate IDs or skipped files.")
    item_sources = definition_sources(data_root, "items")
    rows = raw.get("items", [])
    for i, row in enumerate(rows if isinstance(rows, list) else []):
        item_id = row.get("item_id") if isinstance(row, dict) else None
        if isinstance(item_id, str) and item_id in data.items:
            records = item_sources.get(item_id, [])
            if len(records) != 1 or records[0]["definition"] != data.items[item_id]:
                validator.issue("ITEM_SOURCE", f"items[{i}].item_id", f"Item {item_id!r} has ambiguous source definitions.", "Resolve the duplicate item ID outside Workbench.")
    for key in raw.keys() - {"id", "description", "items", "roll_count"}:
        validator.issue("INACTIVE_POOL_FIELD", key, f"{key!r} is preserved; loot_roller does not consume it.", "No runtime effect is claimed.", "warning")
    return [d.json() for d in validator.diagnostics]


def pool_context(root, data, identifier):
    items = {}
    for item_id, records in definition_sources(root / "roguelike/data", "items").items():
        if item_id not in data.items:
            continue
        unique = len(records) == 1 and records[0]["definition"] == data.items[item_id]
        items[item_id] = {"id": item_id, "name": str(data.items[item_id].get("name", item_id)),
                          "sources": records, "resolved": unique}
    refs = []
    for entry in data.structure_catalog.entries:
        if entry.route != EDIT_ROUTE:
            continue
        for index, record in enumerate(entry.definition.get("special_tiles", [])):
            if record.get("type", record.get("kind")) == "container" and identifier in record.get("loot_pools", []):
                refs.append({"id": entry.definition["id"], "path": "roguelike/data/buildings/" + entry.category + "/" + Path(entry.path).name,
                             "field": f"special_tiles[{index}].loot_pools", "x": record["x"], "y": record["y"],
                             "decor_id": record.get("decor_id", "crate")})
    return {"items": dict(sorted(items.items())), "references": sorted(refs, key=lambda r: (r["path"], r["field"])),
            "consumer": "roguelike/engine/loot_roller.py:roll_pool → ItemFactory.create; engine/scene_generation.py:populate",
            "validator": "roguelike/generation/structure_contract.py:Validator.pool",
            "rules": "Weighted draws without replacement by entry; repeated item IDs remain separate entries. Roll count defaults to [1,1], is capped to entry count, and stops when remaining total weight is zero. Missing weight defaults to 1. Each referenced pool rolls independently. No quantity/condition fields are consumed."}


def pool_validation(request, root, scratch, identity):
    from engine.data_loader import DataLoader
    from generation.structure_contract import read_document, StructureError
    path = asset_path(root, request["asset"], new=True)
    draft = request.get("draft")
    if not isinstance(draft, str) or len(draft.encode("utf-8")) > 1024 * 1024:
        fail("MALFORMED_REQUEST", "Expected UTF-8 draft up to 1 MiB.", "Use a bounded pool definition.")
    copied = scratch / "data"
    shutil.copytree(root / "roguelike/data", copied)
    selected = copied / path.relative_to(root / "roguelike/data")
    selected.write_bytes(draft.encode("utf-8"))
    diagnostics = []; syntax = False
    try:
        raw = read_document(selected)
        syntax = True
        data = DataLoader(str(copied))
        diagnostics = pool_diagnostics(raw, data, request["asset"], copied)
    except StructureError as error:
        diagnostics = [d.json() for d in error.diagnostics]
        if isinstance(error.__cause__, json.JSONDecodeError):
            for d in diagnostics: d.update(line=error.__cause__.lineno, column=error.__cause__.colno)
    for d in diagnostics:
        d["path"] = d["path"].replace(str(copied), "roguelike/data").replace("\\", "/")
    after = source_identity(root)
    if any(after[k] != identity[k] for k in ("game_source_sha256", "catalog_sha256")):
        fail("SOURCE_CHANGED", "Dependencies changed during pool validation.", "Validate again.")
    valid = syntax and not any(d["severity"] == "error" for d in diagnostics)
    return {"valid": valid, "syntax_valid": syntax, "contract_valid": valid, "references_valid": valid,
            "placement_verified": False, "population_verified": False, "diagnostics": diagnostics,
            "draft_sha256": hashlib.sha256(draft.encode("utf-8")).hexdigest(), "route": POOL_ROUTE,
            "contract": "g2-2", "worker_version": WORKER_VERSION, "source": identity, "path": request["asset"],
            "worker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "preview": None,
            "limitations": "Exact pool accepted by DataLoader and Validator.pool. No contents sampled here. Link a building variant and run Preview draft for actual container population. Saving a pool does not assign any container or select any structure."}


def draft_validation(request, root, scratch, identity):
    from engine.data_loader import DataLoader
    from generation.structure_contract import read_document, compile_structure, StructureError
    path = asset_path(root, request.get("asset"), new=True)
    if path.parent.name == "loot_pools":
        return pool_validation(request, root, scratch, identity)
    if path.parent.parent.name != "buildings":
        fail("UNSUPPORTED_ASSET", "Drafts require ordinary_building.", "Use a supported building.")
    draft = request.get("draft")
    if not isinstance(draft, str) or len(draft.encode("utf-8")) > 1024 * 1024:
        fail("MALFORMED_REQUEST", "Expected UTF-8 draft up to 1 MiB.", "Use a bounded building definition.")
    # A disposable data equivalent invokes the real loader including global ID
    # uniqueness and current dependencies. Never replace the live definition.
    copied = scratch / "data"
    shutil.copytree(root / "roguelike/data", copied)
    selected = copied / path.relative_to(root / "roguelike/data")
    selected.write_bytes(draft.encode("utf-8"))
    diagnostics = []; syntax = False; valid = False; generated = None
    contract_valid = False
    try:
        raw = read_document(selected)
        syntax = True
        data = DataLoader(str(copied))
        compiled = compile_structure(raw, EDIT_ROUTE, data, path=str(selected), category=path.parent.name)
        diagnostics = [d.json() for d in compiled.diagnostics]; valid = contract_valid = True
        # A declared pool link must identify a real definition, not an incidental
        # last-write-wins loader result from two files with the same ID.
        pool_sources = definition_sources(copied, "loot_pools")
        for i, record in enumerate(raw.get("special_tiles", [])):
            if record.get("type", record.get("kind")) != "container":
                continue
            for n, identifier in enumerate(record.get("loot_pools", [])):
                if len(pool_sources.get(identifier, [])) != 1:
                    diagnostics.append(dict(severity="error", code="POOL_SOURCE", path=request["asset"], asset=raw["id"],
                        field=f"special_tiles[{i}].loot_pools[{n}]", message=f"Pool {identifier!r} has no unique loaded source definition.",
                        correction="Resolve duplicate or skipped pool definitions before linking.", source_xy=[record["x"],record["y"]], layer="specials"))
                    valid = contract_valid = False
        if request["op"] == "preview_draft" and valid:
            generated, problems = building_preview(raw, data, request.get("seed", 20261023), request["asset"], path.parent.name, identity)
            diagnostics.extend(problems)
            valid = generated["passed"] and not any(d["severity"] == "error" for d in diagnostics)
    except StructureError as error:
        valid = False
        diagnostics = [d.json() for d in error.diagnostics]
        cause = error.__cause__
        if isinstance(cause, json.JSONDecodeError):
            for d in diagnostics: d.update(line=cause.lineno, column=cause.colno)
    for d in diagnostics:
        d["path"] = d["path"].replace(str(copied), "roguelike/data").replace("\\", "/")
    after = source_identity(root)
    if any(after[key] != identity[key] for key in ("game_source_sha256", "catalog_sha256")):
        fail("SOURCE_CHANGED", "Game source or dependency data changed during draft validation.", "Validate again.")
    if generated:
        generated["draft_sha256"] = hashlib.sha256(draft.encode("utf-8")).hexdigest()
    return {"valid": valid, "syntax_valid": syntax, "contract_valid": contract_valid, "references_valid": contract_valid,
            "placement_verified": bool(generated and generated["passed"]), "population_verified": bool(generated and generated["passed"]), "diagnostics": diagnostics,
            "draft_sha256": hashlib.sha256(draft.encode("utf-8")).hexdigest(), "route": EDIT_ROUTE,
            "contract": "g2-2", "worker_version": WORKER_VERSION,
            "worker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "source": identity,
            "path": request["asset"], "preview": generated,
            "limitations": ("Centered direct building stamp and initial population; static access from the declared main entrance to required targets and direct containers when available. No natural selection, rotated placement, player FOV or balance proof."
                            if generated else "Structure and dependency checks only; no reachability, selection, placement or population proof.")}


def building_preview(raw, data, seed, path, category, identity):
    """Read-only adapter around existing game stamping, population and access APIs."""
    from generation.structure_preview import preview
    from generation.placement import NORMALS
    from generation.context import GenerationError
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        fail("MALFORMED_REQUEST", "Invalid preview seed.", "Use an integer from 0 to 2147483647.")
    profile = raw.get("placement", {})
    entrances = sorted((e for e in profile.get("entrances", []) if e["required"]), key=lambda e: (e["role"] != "main", e["id"]))
    targets = [dict(t, name=f"placement.targets[{i}]") for i, t in enumerate(profile.get("targets", [])) if t["required"]]
    # Observe all directly editable containers, even when an old asset has no
    # placement target for one. Reach/interaction semantics remain game-owned.
    targets += [dict(x=s["x"], y=s["y"], kind="container", name=f"special_tiles[{i}]") for i, s in enumerate(raw.get("special_tiles", [])) if s.get("type", s.get("kind")) == "container"]
    expectations = None
    if entrances:
        e = entrances[0]; dx, dy = NORMALS[e["normal"]]
        expectations = {"entry": {"x": e["x"] + dx, "y": e["y"] + dy}, "targets": targets}
    random.seed(seed)
    import numpy as np
    np.random.seed(seed)
    start = time.perf_counter()
    def problem(code, field, message, xy=None, layer="specials"):
        return dict(severity="error", code=code, path=path, asset=raw["id"], field=field,
                    message=message, correction="Inspect the source cell/record and rerun the production preview.", source_xy=xy, layer=layer)
    try:
        report, local_map, _ = preview(raw, EDIT_ROUTE, data, seed=seed, path=path, category=category, expectations=expectations)
    except GenerationError as error:
        match = re.search(r" special\[(\d+)\]", str(error))
        index = int(match[1]) if match else None
        record = raw.get("special_tiles", [])[index] if index is not None and index < len(raw.get("special_tiles", [])) else None
        return {"passed": False, "valid": False}, [problem("PRODUCTION_PLACEMENT", f"special_tiles[{index}]" if record else "special_tiles", str(error), [record["x"], record["y"]] if record else None)]
    problems = []
    ox, oy = report["origin"]
    for row in report["access"]:
        if not row["passed"]:
            xy = [row["xy"][0]-ox,row["xy"][1]-oy] if "xy" in row else None
            problems.append(problem("ACCESS", row["target"], f"Production access check failed: {row['target']}", xy, "specials" if row.get("kind") == "container" else "terrain"))
    for row in report["occupant_diagnostics"]:
        problems.append(problem(row["code"], "special_tiles", json.dumps(row), [row["xy"][0]-ox,row["xy"][1]-oy]))
    for d in report["source_diagnostics"]:
        if d["code"] == "DEFERRED_SPECIAL":
            problems.append(problem("UNSUPPORTED_PREVIEW_SPECIAL",d["field"],d["message"]))
    rows=report["terrain"]
    assert len(rows)==43 and all(len(r)==80 for r in rows)
    for y,row in enumerate(rows):
        for x,t in enumerate(row): assert t==str(local_map.tiles[x,y]["terrain"])
    result={**report, "valid": True, "passed": report["passed"] and not problems, "width":80, "height":43,
            "legend":{t:{"walkable":bool(data.terrain[t].get("walkable",True)),"transparent":bool(data.terrain[t].get("transparent",True))} for t in sorted({t for row in rows for t in row})},
            "source":identity,"seed":seed,"scene_seed":str(local_map.generation_context.scene_seed),"scene_address":list(local_map.generation_context.address),
            "candidate_sha256":report["candidate_identity"],"terrain_sha256":hashlib.sha256(json.dumps(rows,separators=(",",":")).encode()).hexdigest(),
            "elapsed_ms":round((time.perf_counter()-start)*1000,2),
            "context":f"Unsaved ordinary_building; centered at {ox},{oy}; no rotation. generation.town_gen._stamp_building_at → engine.scene_generation.populate. Seed {seed}. " + ("Static game access checks from declared main entrance." if expectations else "No declared required entrance: access unverified."),
            "rendering":"Revealed production terrain and factory-created initial objects; no campaign or natural selection.",
            "access_verified": bool(expectations) and all(r["passed"] for r in report["access"]),
            "draft_sha256":None}
    return result, problems


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
    from generation.structure_preview import preview
    if CONTRACT_VERSION != "g2-2":
        fail("CONTRACT_MISMATCH", f"Unsupported structure contract {CONTRACT_VERSION}.", "Update the Workbench adapter after reviewing this game's contract.")
    op = request["op"]
    if op in ("validate_draft", "preview_draft"):
        return draft_validation(request, root, scratch, identity)
    catalog_error = None
    try:
        data = DataLoader(str(root / "roguelike/data"))
        identity["catalog_sha256"] = data.structure_catalog.identity
    except StructureError as error:
        data = None; catalog_error = error
        identity["catalog_sha256"] = None
    if op == "identify":
        return {"worker_version": WORKER_VERSION, "worker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "protocol": PROTOCOL, "source": identity, "runtime": runtime, "contract": CONTRACT_VERSION,
                "route": ROUTE, "validator": "generation.structure_contract.compile_structure",
                "preview": "generation.structure_preview.preview → engine.scene_generation.create_submap → generation.local_gen.generate_submap",
                "edit_route": EDIT_ROUTE,
                "unavailable": ["layout editing/saving", "item/recipe editing", "native world selection", "game renderer/FOV", "combat simulation"],
                "health": "catalog needs repair" if catalog_error else "ready",
                "diagnostics": [d.json() for d in catalog_error.diagnostics] if catalog_error else []}
    if op == "describe":
        return {"route": ROUTE, "capabilities": CAPABILITIES[ROUTE],
                "assets": discover(root), "unsupported": ["plaza (read-only)", "entrances", "item editing", "legacy loot tables", "recipes", "creatures", "generation profiles"]}
    path = asset_path(root, request.get("asset"))
    before = path.stat()
    source = path.read_bytes()
    route = EDIT_ROUTE if path.parent.parent.name == "buildings" else ROUTE
    category = path.parent.name if route == EDIT_ROUTE else None
    raw_error = None
    try:
        raw = read_document(path)
    except StructureError as error:
        raw = {}; raw_error = error
    if path.parent.name == "loot_pools":
        if op != "inspect" or request.get("invalid_fixture"):
            fail("UNSUPPORTED_OPERATION", "Pool inspection does not generate a map.", "Preview a building to observe its actual containers.")
        diagnostics = ([d.json() for d in (raw_error or catalog_error).diagnostics] if raw_error or catalog_error
                       else pool_diagnostics(raw, data, request["asset"], root / "roguelike/data"))
        if path.read_bytes() != source:
            fail("SOURCE_CHANGED", "Pool changed during inspection.", "Reopen the pool.")
        return {"id": raw.get("id", path.stem), "path": request["asset"], "route": POOL_ROUTE,
                "description": str(raw.get("description", "")), "valid": not any(d["severity"] == "error" for d in diagnostics),
                "diagnostics": diagnostics, "raw": source.decode("utf-8"), "sha256": hashlib.sha256(source).hexdigest(),
                "mtime_ns": str(before.st_mtime_ns), "source_unchanged": True, "source": identity,
                "pool_context": pool_context(root, data, raw.get("id")) if data else None}
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
        valid = True
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
                "catalog": ({"terrain": {k: {"walkable":bool(v.get("walkable",True)),"transparent":bool(v.get("transparent",True))} for k,v in data.terrain.items()},
                             "decor": {k:{"name":str(v.get("name",k)),"container":v.get("container") is True,"blocks_movement":bool(v.get("blocks_movement",False))} for k,v in data.decoratives.items()},
                             "loot_pools":sorted(data.loot_pools)} if data and route == EDIT_ROUTE else None)}
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
        if request.get("op") not in ("identify", "describe", "inspect", "preview", "validate_draft", "preview_draft") or set(request) - {"id", "protocol", "op", "asset", "seed", "invalid_fixture", "draft"}:
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
