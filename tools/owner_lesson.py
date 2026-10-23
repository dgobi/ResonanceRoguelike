"""Reversible Crow Jerky experiment through the real inventory-use handler.

Component/runtime diagnostic only: this deliberately does not claim real-input
coverage. Edits only a freshly copied session definition, restores exact bytes,
and verifies that restoration. Owner window exercise is documented separately.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from baseline import ROOT, prepare


def worker(game, output):
    os.chdir(game)
    sys.path.insert(0, str(game))
    import pygame
    from engine.engine import Engine
    import main
    def run(e):
        item = next(i for i in e.player.inventory.items if i.item_id == "crow_jerky")
        e.player.needs.hunger = 0.5
        before_turn = e.world_time.turn
        e.inventory_screen.open = True
        e.inventory_screen._flat = [(item, False, item.name)]
        e.inventory_screen.selected = 0
        e.inventory_screen.handle_key(pygame.K_RETURN, e)
        expected = 0.5 - item.nutrition + 0.001
        result = {"evidence_class": "real Engine + InventoryScreen.handle_key; no window or OS input",
                  "nutrition": item.nutrition, "hunger_before": 0.5,
                  "expected_hunger_after": expected, "observed_hunger_after": e.player.needs.hunger,
                  "turn_delta": e.world_time.turn - before_turn,
                  "item_removed": item not in e.player.inventory.items,
                  "property_passed": abs(e.player.needs.hunger - expected) < 1e-9
                    and e.world_time.turn == before_turn + 1 and item not in e.player.inventory.items}
        Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    Engine.run = run
    main.main()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session", default="jerky-lesson")
    p.add_argument("--worker", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.worker:
        worker(a.worker.resolve(), a.output.resolve())
        return
    session, game = prepare(a.session, 20261020)
    definition = game / "data/items/consumables/crow_jerky.json"
    before = definition.read_bytes()
    results = []
    try:
        for value in (0.35, 0.20):
            data = json.loads(before)
            data["nutrition"] = value
            definition.write_text(json.dumps(data, indent=2), encoding="utf-8")
            output = session / (str(value) + "-result.json")
            proc = subprocess.run([sys.executable, __file__, "--worker", str(game),
                                   "--output", str(output)], capture_output=True, text=True)
            if proc.returncode:
                raise RuntimeError(proc.stderr)
            results.append(json.loads(output.read_text()))
    finally:
        definition.write_bytes(before)
    result = {"results": results, "restored_exact_bytes": definition.read_bytes() == before,
              "definition_sha256": hashlib.sha256(before).hexdigest(),
              "owner_learning_outcome": "optional educational exercise; not an acceptance gate",
              "window_verification": "this component lesson does not run input; tools/verify_b1.py provides autonomous real-loop coverage",
              "source_hashes": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                  for name in ("tools/owner_lesson.py", "roguelike/engine/item_system.py",
                      "roguelike/engine/inventory_screen.py", "roguelike/components/needs.py",
                      "roguelike/engine/item_factory.py", "roguelike/data/survival.json")}}
    output = ROOT / "evidence/owner-lesson-results.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    if not all(r["property_passed"] for r in results) or not result["restored_exact_bytes"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
