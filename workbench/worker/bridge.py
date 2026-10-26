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
import subprocess
import sys
import tempfile
import time
import traceback

sys.dont_write_bytecode = True
# This small preview needs no parallel BLAS. Bound native thread-pool overhead
# before importing NumPy/tcod; the game's algorithms and data stay unchanged.
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
PROTOCOL = 1
WORKER_VERSION = "0.1.0"
ROUTE = "authored_submap"
DEPENDENCIES = {"pygame": "2.6.1", "tcod": "19.3.0", "numpy": "2.4.6",
                "cffi": "2.1.1", "pycparser": "3.11", "typing_extensions": "4.16.0"}
MAX_REQUEST = 65536


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
        if not folder.resolve().is_relative_to(root):
            fail("PATH_ESCAPE", str(folder), "Use a checkout without external source/data links.")
        if folder.is_dir():
            for base, dirs, files in os.walk(folder, followlinks=False):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for name in dirs + files:
                    p = Path(base) / name
                    if not p.resolve().is_relative_to(root):
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
    status = git("status", "--porcelain", "--", "roguelike", "requirements-baseline.txt")
    return {"root": str(root), "commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "game_dirty": None if status is None else bool(status),
            "game_source_sha256": digest.hexdigest()}


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


def asset_path(root, value):
    if not isinstance(value, str) or "\\" in value or ":" in value or ".." in value.split("/"):
        fail("PATH_ESCAPE", "Invalid asset path.", "Choose a shipped authored layout from the list.")
    relative = Path(value)
    if relative.is_absolute() or len(relative.parts) != 4 or relative.parts[:3] != ("roguelike", "data", "layouts") or relative.suffix != ".json":
        fail("UNSUPPORTED_ASSET", value, "W0 supports immediate roguelike/data/layouts/*.json only.")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root / "roguelike/data/layouts"):
        fail("PATH_ESCAPE", value, "Choose an asset inside the selected repository.")
    return path


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
    data = DataLoader(str(root / "roguelike/data"))
    identity["catalog_sha256"] = data.structure_catalog.identity
    op = request["op"]
    if op == "identify":
        return {"worker_version": WORKER_VERSION, "worker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "protocol": PROTOCOL, "source": identity, "runtime": runtime, "contract": CONTRACT_VERSION,
                "route": ROUTE, "validator": "generation.structure_contract.compile_structure",
                "preview": "generation.structure_preview.preview → engine.scene_generation.create_submap → generation.local_gen.generate_submap",
                "unavailable": ["editing/saving", "ordinary-building UI", "native world selection", "game renderer/FOV", "combat simulation"],
                "health": "ready"}
    if op == "describe":
        return {"route": ROUTE, "capabilities": CAPABILITIES[ROUTE],
                "assets": [{"path": Path(e.path).relative_to(root).as_posix(), "id": e.raw["id"], "width": e.width, "height": e.height}
                           for e in data.structure_catalog.entries if e.route == ROUTE]}
    path = asset_path(root, request.get("asset"))
    before = path.stat()
    source = path.read_bytes()
    raw = read_document(path)
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
        compiled = compile_structure(raw, ROUTE, data, path=str(selected))
        diagnostics = [d.json() for d in compiled.diagnostics]
        valid = True
    except StructureError as error:
        diagnostics = [d.json() for d in error.diagnostics]
        valid = False
    after = path.stat()
    if path.read_bytes() != source or (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        fail("SOURCE_CHANGED", "Source changed during inspection.", "Finish external edits, then reopen the project.")
    if op == "inspect":
        return {"id": raw.get("id"), "path": path.relative_to(root).as_posix(), "route": ROUTE,
                "width": len(raw["layers"][0]), "height": len(raw["layers"]), "description": raw.get("description", ""),
                "special_count": len(raw.get("special_tiles", [])), "valid": valid, "diagnostics": diagnostics,
                "raw": source.decode("utf-8-sig") if not invalid else json.dumps(raw, indent=2), "invalid_fixture": invalid,
                "sha256": hashlib.sha256(source).hexdigest(), "mtime_ns": str(before.st_mtime_ns),
                "source_unchanged": True, "source": identity}
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
    report, local_map, _ = preview(raw, ROUTE, data, seed=seed, path=str(path))
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
            "seed": seed, "scene_seed": str(report.get("scene_seed")), "scene_address": report.get("scene_address"),
            "candidate_sha256": report["candidate_identity"], "source": identity, "asset": raw["id"],
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
            "terrain_sha256": hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest(),
            "context": "Controlled authored submap; world seed supplied; address (0,0,preview-submap); centered, no rotation; global Python/NumPy RNG also seeded; no campaign opened.",
            "rendering": "Production-data-backed Workbench rendering; revealed terrain and initial objects, not Pygame/tcod or player FOV."}


def main():
    request_id = None
    start = time.perf_counter()
    try:
        line = sys.stdin.buffer.readline(MAX_REQUEST + 1)
        if len(line) > MAX_REQUEST:
            fail("MALFORMED_REQUEST", "Request exceeds 64 KiB.", "Use a W0 request.")
        request = json.loads(line)
        if not isinstance(request, dict):
            fail("MALFORMED_REQUEST", "Expected an object.", "Use the versioned W0 protocol.")
        request_id = request.get("id")
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            fail("MALFORMED_REQUEST", "Expected a correlation ID.", "Supply a short string id.")
        if type(request.get("protocol")) is not int or request["protocol"] != PROTOCOL:
            fail("PROTOCOL_MISMATCH", f"Worker requires protocol {PROTOCOL}.", "Use matching Workbench frontend, host and worker versions.")
        if request.get("op") not in ("identify", "describe", "inspect", "preview") or set(request) - {"id", "protocol", "op", "asset", "seed", "invalid_fixture"}:
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
