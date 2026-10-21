"""Copy the game into a named disposable CWD; never import from the owner's saves.

Run from the project root with the isolated interpreter. --observe adds logging
and a bounded diagnostic command file; ordinary mode calls main.py unchanged.
Existing sessions require --resume. Nothing is deleted or overwritten on setup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def prepare(name, seed, resume=False):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Use only letters, numbers, underscores and hyphens for session")
    session = ROOT / ".baseline" / name
    game = session / "roguelike"
    marker = session / "disposable-session.json"
    if session.exists():
        if not resume or not marker.is_file() or not game.is_dir():
            raise ValueError("Session already exists; choose a new name or --resume a marked session")
        return session, game
    session.mkdir(parents=True)
    shutil.copytree(ROOT / "roguelike", game,
                    ignore=shutil.ignore_patterns("saves", "__pycache__", "*.pyc", "game_out.txt"))
    manifest = {p.relative_to(game).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(game.rglob("*")) if p.is_file()}
    marker.write_text(json.dumps({"seed": seed, "source_hashes": manifest}, indent=2), encoding="utf-8")
    # The existing bootstrap reads this seed; no player.json means NEW GAME.
    save = game / "saves" / "slot_0"
    save.mkdir(parents=True)
    (save / "world.json").write_text(json.dumps({"seed": seed}), encoding="utf-8")
    return session, game


def snapshot(e):
    p = e.player
    return {
        "seed": e.world_map.seed, "turn": e.world_time.turn,
        "world": [e.world_x, e.world_y], "submap": e.current_submap_id,
        "position": [p.x, p.y], "hp": p.fighter.hp,
        "hunger": p.needs.hunger, "thirst": p.needs.thirst,
        "fov_base": e._compute_fov_base(), "visible_tiles": int(e.local_map.visible.sum()),
        "inventory": [{"id": i.item_id, "nutrition": i.nutrition} for i in p.inventory.items],
        "equipment": {k: v.item_id if v else None for k, v in p.equipment.slots.items()},
        "equipment_owned": all(v is None or any(v is i for i in p.inventory.items)
                               for v in p.equipment.slots.values()),
        "actors": [{"id": getattr(a, "_creature_id", None), "tile": a.tile,
                    "pos": [a.x, a.y], "hp": getattr(getattr(a, "fighter", None), "hp", None)}
                   for a in e.entities if a is not p],
        "floor": {f"{x},{y}": [getattr(i, "item_id", "") for i in items]
                  for (x, y), items in e.local_map.floor_objects.items()},
        "decor": {f"{x},{y}": v for (x, y), v in e.local_map.decor.items()},
        "screens": {n: getattr(getattr(e, n), "open", False)
                    for n in ("inventory_screen", "craft_screen", "text_reader")},
        "mode": e.mode.value, "messages": [m.text for m in e.log.recent(8)],
    }


def observe(session):
    import pygame
    from engine.engine import Engine
    trace = session / "observations.jsonl"
    current = {}
    command_mtime = None

    def record(kind, **extra):
        state = snapshot(current["engine"])
        with trace.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": kind, **extra, "state": state}) + "\n")
        (session / "latest-state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    original_run = Engine.run
    def run(e):
        current["engine"] = e
        record("bootstrap", initiating_entry="main.main", pid=os.getpid())
        return original_run(e)
    Engine.run = run

    for name in ("_handle_key", "_try_ascend", "_try_descend"):
        original = getattr(Engine, name)
        def traced(e, *args, _original=original, _name=name, **kwargs):
            before = snapshot(e)
            try:
                return _original(e, *args, **kwargs)
            finally:
                record("input_dispatch", handler=_name,
                       key=pygame.key.name(args[0]) if args else None, before=before)
        setattr(Engine, name, traced)

    original_get = pygame.event.get
    def events(*args, **kwargs):
        nonlocal command_mtime
        path = session / "diagnostic-command.json"
        if path.exists() and path.stat().st_mtime_ns != command_mtime:
            command_mtime = path.stat().st_mtime_ns
            cmd = json.loads(path.read_text(encoding="utf-8-sig"))
            e = current["engine"]
            record("diagnostic_before", command=cmd)
            action = cmd["action"]
            if action == "save":
                e.save_manager.save(e)
            elif action == "capture":
                name = cmd["name"]
                if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
                    raise ValueError("Invalid capture name")
                pygame.image.save(pygame.display.get_surface(), str(session / (name + ".png")))
            elif action == "position":
                x, y = cmd["x"], cmd["y"]
                if not e.local_map.in_bounds(x, y) or not e.local_map.walkable[x, y]:
                    raise ValueError("Fixture position must be in bounds and walkable")
                e.player.x, e.player.y = x, y
                e._update_fov()
            elif action == "give":
                for item_id in cmd["items"]:
                    item = e.item_factory.create(item_id)
                    if item is None or not e.player.inventory.add(item):
                        raise ValueError("Fixture item missing or capacity exceeded: " + item_id)
            elif action == "hunger":
                e.player.needs.hunger = float(cmd["value"])
            elif action == "spawn":
                a = e.creature_factory.spawn(cmd["id"], cmd["x"], cmd["y"])
                if a is None:
                    raise ValueError("Unknown creature")
                e.entities.append(a)
            else:
                raise ValueError("Unknown diagnostic action: " + action)
            record("diagnostic_after", command=cmd)
        return original_get(*args, **kwargs)
    pygame.event.get = events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--observe", action="store_true")
    args = parser.parse_args()
    session, game = prepare(args.session, args.seed, args.resume)
    print("Disposable CWD:", game, flush=True)
    if args.prepare_only:
        return
    os.chdir(game)
    sys.path.insert(0, str(game))
    if args.observe:
        observe(session)
    runpy.run_path(str(game / "main.py"), run_name="__main__")


if __name__ == "__main__":
    main()
