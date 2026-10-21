"""Arc A diagnostic evidence, NOT passing regression tests or a playthrough.

Uses real main.main bootstrap, Engine, SaveManager, factories and tcod. Replaces
Engine.run only to run bounded assertions without opening a window. No AST
extraction, dependency stand-ins, event injection, or personal save access.
Exit 0 means harness completed; --assert-properties exits 1 on property failures.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from baseline import ROOT, prepare


def dump(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def scene(e):
    return {"world": [e.world_x, e.world_y], "submap": e.current_submap_id,
            "marker": str(e.local_map.tiles[3, 3]["terrain"]),
            "actors": sorted(getattr(a, "_creature_id", a.tile)
                             for a in e.entities if a is not e.player)}


def belongings(e):
    inv = e.player.inventory.items
    return {"inventory": [i.item_id for i in inv],
            "slots": {k: i.item_id if i else None for k, i in e.player.equipment.slots.items()},
            "all_equipped_owned": all(i is None or any(i is v for v in inv)
                                      for i in e.player.equipment.slots.values())}


def worker(session_name, case, phase):
    session, game = prepare(session_name, 20261020, resume=(phase == "read"))
    os.chdir(game)
    sys.path.insert(0, str(game))
    from engine.engine import Engine
    from components.equipment import Equipment
    from engine.save_manager import _serialize_entity, _deserialize_entities
    import main

    def run(e):
        result = {"case": case, "phase": phase, "pid": os.getpid(),
                  "harness_completed": True, "checks": []}
        def check(name, expected, actual):
            result["checks"].append({"property": name, "expected": expected,
                                      "observed": actual, "property_passed": actual == expected})
        if case == "scenes":
            if phase == "write":
                surface = e.save_manager.cache.load(e.world_x, e.world_y).local_map
                surface.set_tile(3, 3, "grass", True, True)
                sa = e.creature_factory.spawn("hollow_revenant", 4, 4)
                e.save_manager.cache.store(e.world_x, e.world_y, surface, [e.player, sa])
                e.local_map.set_tile(3, 3, "flagstone", True, True)
                ua = e.creature_factory.spawn("grave_thing", 5, 5)
                e.entities = [e.player, ua]
                e.save_manager.cache.store_submap(e.current_submap_id, e.local_map, e.entities)
                result["underground_before"] = scene(e)
                e.save_manager.save(e)
                result["initiating_entry"] = "SaveManager.save(engine), diagnostic full save"
                check("in-session load completes", True, e.save_manager.load(e))
            result["underground_after_load"] = scene(e)
            check("loaded underground identity and contents", ["sub_0_64_0", "flagstone", ["grave_thing"]],
                  [e.current_submap_id, scene(e)["marker"], scene(e)["actors"]])
            e._ascend_from_submap()
            result["surface_after_ascent"] = scene(e)
            check("surface identity and contents survive underground save/load/ascent",
                  [None, "grass", ["hollow_revenant"]],
                  [e.current_submap_id, scene(e)["marker"], scene(e)["actors"]])
            # Actual descent method, independent of the damaged stair tile.
            sub = e.world_map.get(e.world_x, e.world_y).submaps[0]
            e._descend_to_submap(sub.submap_id)
            result["underground_after_redescent"] = scene(e)
            check("underground identity and contents survive redescent",
                  [sub.submap_id, "flagstone", ["grave_thing"]],
                  [e.current_submap_id, scene(e)["marker"], scene(e)["actors"]])
        elif case in ("empty", "empty_slots", "equipped"):
            if phase == "write":
                p = e.player
                p.inventory.items.clear()
                p.equipment = Equipment()
                p.light_source = None
                if case == "empty_slots":
                    p.inventory.add(e.item_factory.create("crow_jerky"))
                if case == "equipped":
                    blade = e.item_factory.create("crude_blade")
                    torch = e.item_factory.create("tallow_torch")
                    p.inventory.add(blade)
                    p.inventory.add(torch)
                    p.equipment.slots["weapon"] = blade
                    p.equipment.slots["offhand"] = torch
                result["before_save"] = belongings(e)
                e.save_manager.save(e)
                # Simulate prior in-session state independently of the save.
                prior = e.item_factory.create("leather_jack")
                p.inventory.add(prior)
                p.equipment.slots["armor_torso"] = prior
                check("in-session load completes", True, e.save_manager.load(e))
            result["after_load"] = belongings(e)
            expected = {"empty": [], "empty_slots": ["crow_jerky"],
                        "equipped": ["crude_blade", "tallow_torch"]}[case]
            check("saved inventory replaces starter or prior inventory", sorted(expected),
                  sorted(result["after_load"]["inventory"]))
            check("equipped instances belong to restored inventory", True,
                  result["after_load"]["all_equipped_owned"])
            if case != "equipped":
                check("saved empty slots replace prior equipment", True,
                      all(i is None for i in e.player.equipment.slots.values()))
            else:
                check("weapon relinks to restored blade", "crude_blade",
                      result["after_load"]["slots"]["weapon"])
        elif case == "lurker":
            payload = session / "lurker.json"
            if phase == "write":
                from engine.creature_abilities import _ability_stone_lurker
                a = e.creature_factory.spawn("stone_lurker", 60, 30)
                _ability_stone_lurker(a, e)
                result["before"] = {"stable_id": a._creature_id, "tile": a.tile,
                                    "hibernating": a._hibernating}
                dump(payload, _serialize_entity(a))
            serialized = json.loads(payload.read_text())
            restored = _deserialize_entities([serialized], e)
            result["serialized"] = serialized
            check("hibernating creature serializes stable definition identity", "stone_lurker", serialized["id"])
            check("hibernating creature reconstructs with stable identity", ["stone_lurker"],
                  [a._creature_id for a in restored])
        dump(session / (phase + "-results.json"), result)
    Engine.run = run
    main.main()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prefix", default="persistence")
    p.add_argument("--worker", choices=["scenes", "empty", "empty_slots", "equipped", "lurker"])
    p.add_argument("--phase", choices=["write", "read"])
    p.add_argument("--assert-properties", action="store_true")
    a = p.parse_args()
    if a.worker:
        worker(a.prefix, a.worker, a.phase)
        return
    results = []
    for case in ("scenes", "empty", "empty_slots", "equipped", "lurker"):
        session_name = a.prefix + "-" + case
        for phase in ("write", "read"):
            proc = subprocess.run([sys.executable, __file__, "--prefix", session_name,
                                   "--worker", case, "--phase", phase], capture_output=True, text=True)
            path = ROOT / ".baseline" / session_name / (phase + "-results.json")
            row = json.loads(path.read_text()) if path.exists() else {
                "case": case, "phase": phase, "harness_completed": False}
            row["exit_code"] = proc.returncode
            row["stdout"] = proc.stdout
            row["stderr"] = proc.stderr
            results.append(row)
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [ROOT / "roguelike" / name for name in (
                  "main.py", "engine/engine.py", "engine/save_manager.py",
                  "engine/creature_factory.py", "engine/creature_abilities.py")]
              + [Path(__file__), ROOT / "tools/baseline.py"]}
    completed = all(r["harness_completed"] and r["exit_code"] == 0 for r in results)
    passed = all(c["property_passed"] for r in results for c in r.get("checks", []))
    output = {"python": sys.version, "source_hashes": hashes, "harness_completed": completed,
              "all_properties_passed": passed, "evidence_class": "full bootstrap and real methods; no window/input loop",
              "results": results}
    out = ROOT / "evidence" / (a.prefix + "-results.json")
    out.parent.mkdir(exist_ok=True)
    dump(out, output)
    print(json.dumps({"output": str(out), "harness_completed": completed,
                      "all_properties_passed": passed}))
    if not completed or (a.assert_properties and not passed):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
