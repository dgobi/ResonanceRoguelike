"""Shared evidence helpers. Standard library only until worker bootstrap."""
from __future__ import annotations
import hashlib
import copy
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

SEED = 20261020
ENV = {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy",
       "PYTHONHASHSEED": str(SEED), "PYTHONIOENCODING": "utf-8",
       "PYTHONUTF8": "1", "PYGAME_HIDE_SUPPORT_PROMPT": "1"}


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def hashes(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): {"bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


class Evidence:
    def __init__(self, job):
        self.job = job
        self.record = {**{k: job[k] for k in ("run_id", "scenario", "phase", "flavor")},
                       "pid": os.getpid(), "cwd": str(Path.cwd()), "argv": sys.argv,
                       "seed": SEED, "python": sys.version, "os": platform.platform(),
                       "environment": {k: os.environ.get(k) for k in ENV},
                       "versions": {k: importlib.metadata.version(k) for k in ("pygame", "tcod", "numpy")},
                       "checks": [], "trace": [], "defects": [], "completed": False}

    def check(self, case, name, expected, observed):
        row = dict(case=case, property=name, expected=expected, observed=observed,
                   passed=observed == expected)
        self.record["checks"].append(row)
        if not row["passed"]:
            raise AssertionError(json.dumps(row))

    def defect(self, case, identity, scope, symptom):
        self.record["defects"].append(dict(case=case, id=identity, scope=scope, symptom=symptom))

    def bind_sources(self, game):
        game = Path(game).resolve()
        origins = {}
        for name, module in sorted(sys.modules.items()):
            path = getattr(module, "__file__", None)
            if not path or not name.startswith(("main", "engine.", "components.", "world.", "generation.", "entities.", "rendering.", "config")):
                continue
            p = Path(path).resolve()
            if p.suffix != ".py":
                continue
            if not p.is_relative_to(game):
                raise AssertionError(f"Wrong source binding: {name}: {p}, expected {game}")
            origins[name] = {"path": str(p), "relative": p.relative_to(game).as_posix(),
                             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        self.record["imported_sources"] = origins
        self.check("H02", "actual copied source binding", True,
                   all(n in origins for n in ("main", "engine.engine", "engine.save_manager")))


def gear(e):
    p = e.player
    rows = p.inventory.items
    def index(item):
        if item is None:
            return None
        return next((n for n, row in enumerate(rows) if row is item), "UNOWNED")
    light = p.light_source
    return {"capacity": p.inventory.capacity,
            "items": [{"id": i.item_id, "fuel": i.turns_lit, "liquid": i.liquid,
                       "volume": i.liquid_volume, "equipped": i.equipped} for i in rows],
            "slots": {slot: index(i) for slot, i in p.equipment.slots.items()},
            "armor": p.fighter.effective_av,
            "light": None if light is None else {"active": light.active,
                 "item_index": index(getattr(light, "_item_ref", None)), "radius": light.radius}}


def actor_state(a):
    return {"id": getattr(a, "_creature_id", None), "tile": a.tile,
            "position": [a.x, a.y], "hp": a.fighter.hp,
            "hibernating": getattr(a, "_hibernating", None),
            "ambush_ready": getattr(a, "_ambush_ready", False),
            "triggered": getattr(a.ai, "_triggered", None)}


def scene_state(m, actors):
    return {"marker": str(m.tiles[3, 3]["terrain"]),
            "actors": sorted([actor_state(a) for a in actors if a.name != "Player"],
                             key=lambda a: (a["id"], a["position"])),
            "floor": [{"id": i.item_id, "fuel": i.turns_lit, "liquid": i.liquid,
                       "volume": i.liquid_volume} for i in m.floor_objects.get((6, 6), [])],
            "container": copy.deepcopy(m.container_state.get((7, 7))),
            "decor": m.decor.get((7, 7)), "explored": bool(m.explored[2, 2]),
            "links": {str(k): v for k, v in sorted(m.submap_links.items())}}


def seed_runtime(e):
    import random
    import numpy
    random.seed(SEED)
    numpy.random.seed(SEED)
    e.rng.seed(SEED)
    e.ai_system._rng.seed(SEED)
    # Rendering uses wall clocks and private random generators. No image byte
    # equality or complete simulation-RNG replay is claimed by these tests.


def boot(callback, ev):
    from engine.engine import Engine
    import main
    original = Engine.run
    def run(e):
        seed_runtime(e)
        return callback(e)
    Engine.run = run
    try:
        main.main()
    finally:
        Engine.run = original

