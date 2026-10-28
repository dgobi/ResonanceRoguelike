"""W5F original-source authority, corpus and truthful reference regressions."""
import copy
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
sys.path.insert(0, str(ROOT / "roguelike"))
from engine import creature_authoring as ca
from engine.data_loader import DataLoader

BASE = "roguelike/data/entities/creatures/"
WIGHT = BASE + "barrow_wight.json"
ORDINARY = BASE + "hollow_revenant.json"


class CreatureCommonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()): cls.data = DataLoader(str(ROOT / "roguelike/data"))
        cls.indexes = ca.indexes_for(cls.data.root)

    def test_entire_corpus_inspection_construction_and_operation_subset(self):
        rows = [r for r in invoke("describe")["result"]["assets"] if r.get("family_id") == "creature"]
        self.assertEqual(len(rows), 14); self.assertEqual(len({r["path"] for r in rows}), 14)
        for row in rows:
            opened = invoke("inspect", asset=row["path"])["result"]
            record = opened["family"]["context"]["records"][0]; cap = record["capability"]
            actor = row["id"] not in ("player", "vine_network")
            special = row["id"] in ca.ABILITY_REGISTRY
            self.assertEqual(opened["editable"], actor, (row, opened["diagnostics"]))
            self.assertEqual(cap["constructible"], actor)
            self.assertEqual(record["factory"] is not None, actor)
            self.assertEqual(opened["family"]["effective_operations"], (["edit"] if special else ["edit", "variant"]) if actor else [])
            self.assertEqual(opened["raw"].encode(), (ROOT / row["path"]).read_bytes())

    def test_wight_inline_body_inactive_metadata_and_active_inbound_zones(self):
        opened = invoke("inspect", asset=WIGHT)["result"]; self.assertTrue(opened["valid"])
        record = opened["family"]["context"]["records"][0]
        self.assertEqual(record["capability"]["body_note"], "Body supplied by inline limbs")
        self.assertEqual(record["factory"]["special_binding"], "barrow_wight")
        self.assertFalse(record["factory"]["ability_executed"])
        self.assertTrue(all(d["severity"] == "info" for d in opened["diagnostics"]))
        self.assertTrue(any(r["route"] == "zone_creatures" and r["path"].endswith("/barrow.json") for r in record["references"]))
        self.assertEqual(len(ca.source_matches("BARROW", self.indexes["zones"])), 1)
        with tempfile.TemporaryDirectory(prefix="w5f-reference-") as folder:
            root = data_fixture(folder); path = root / WIGHT
            raw = json.loads(path.read_bytes()); raw.pop("limbs"); raw["body_id"] = "missing_required_body"
            path.write_text(json.dumps(raw), encoding="utf-8")
            result = invoke("inspect", root=root, asset=WIGHT)["result"]
            self.assertFalse(result["valid"])
            self.assertTrue(any(d["code"] == "UNKNOWN_REFERENCE" and d["field"] == "body_id" and d["severity"] == "error" for d in result["diagnostics"]))
            raw = json.loads((ROOT / WIGHT).read_bytes()); raw["body_id"] = "authored_unused_missing"
            path.write_text(json.dumps(raw), encoding="utf-8")
            zone = json.loads((root / "roguelike/data/zones/dungeon/barrow.json").read_bytes()); zone["id"] = "BARROW"
            (root / "roguelike/data/zones/dungeon/negative_duplicate.json").write_text(json.dumps(zone), encoding="utf-8")
            result = invoke("inspect", root=root, asset=WIGHT)["result"]
            self.assertTrue(result["valid"])
            self.assertTrue(any(d["code"] == "DUPLICATE_ZONE" for d in result["diagnostics"]))
            self.assertTrue(any("Authored body_id" in d["message"] and d["severity"] == "info" for d in result["diagnostics"]))

    def test_same_id_common_fields_and_ordinary_ai_variant(self):
        raw = json.loads((ROOT / WIGHT).read_bytes())
        raw.update(name="W5F Wight", description="Exact new prose", base_hp=37, armour_value=6, damage_dice="2d5", damage_bonus=-1,
                   attack_verb="tests the fixture", wander_radius=4, pursuit_timeout=7, speed=1.1)
        raw["fighter"]["max_hp"] = 37; raw["perception"].update(sight_radius=3, sees_in_dark=False)
        result = invoke("preview_draft", asset=WIGHT, source_asset=WIGHT, draft=json.dumps(raw))["result"]
        self.assertTrue(result["valid"], result["diagnostics"])
        self.assertEqual(result["family"]["effective_operations"], ["edit"])
        self.assertEqual(result["factory"]["special_binding"], "barrow_wight")
        raw = json.loads((ROOT / ORDINARY).read_bytes()); raw.update(id="w5f_ordinary", ai_type="fleeing", description="Own description")
        result = invoke("preview_draft", asset=BASE + "w5f_ordinary.json", source_asset=ORDINARY, draft=json.dumps(raw))["result"]
        self.assertTrue(result["valid"], result["diagnostics"])
        self.assertEqual(result["factory"]["instance"]["ai_class"], "FleeingAI")
        self.assertIsNone(result["factory"]["special_binding"])
        self.assertEqual(result["factory"]["instance"]["tile"], "hollow_revenant")

    def test_bounds_types_and_missing_defaults(self):
        original = copy.deepcopy(self.data.entities["barrow_wight"])
        bad = {"name": ["Player", "", True, "x" * 257], "description": [False, [], "x" * 8193],
               "damage_dice": ["1d6+1", "0d6", "1d0", "21d6", "1d101", "999999999d6", "1D6", " 1d6", True, None],
               "speed": [True, 0, -1, 0.001, 2.01, float("inf"), float("nan"), "1"],
               "armour_value": [True, -1, 1.5, 1000001], "damage_bonus": [True, -1001, 1001, 1.5],
               "pursuit_timeout": [True, -1, 10001], "wander_radius": [True, -1, 1001],
               "perception.sight_radius": [True, -1, 1001], "perception.sees_in_dark": [0, "false", None]}
        bad["butcher_yield"] = [None, {"tiers": None}, {"tiers": [None]}, {"tiers": [{"yields": None}]}, {"tiers": [{"yields": [False]}]}]
        for key, values in bad.items():
            for value in values:
                raw = copy.deepcopy(original); parts = key.split("."); parent = raw if len(parts) == 1 else raw[parts[0]]; parent[parts[-1]] = value
                data = copy.copy(self.data); data.entities = {**self.data.entities, raw["id"]: raw}
                indexes = {**self.indexes, "entities": {**self.indexes["entities"], raw["id"]: [dict(path=WIGHT, pointer="", definition=raw)]}}
                errors, _ = ca.validate_definition(raw, data, WIGHT, indexes)
                self.assertTrue(any(d["severity"] == "error" for d in errors), (key, value))
        raw = copy.deepcopy(original)
        for key in ("description", "damage_dice", "damage_bonus", "attack_verb", "speed", "pursuit_timeout"): raw.pop(key)
        self.assertEqual(ca.authorize_candidate(original, raw, WIGHT, WIGHT), [])

    def test_source_promotion_special_clones_and_namespace_collision(self):
        original = json.loads((ROOT / WIGHT).read_bytes())
        for edit in ({"id": "w5f_special_clone"}, {"tile": "hollow_revenant", "ai_type": "wandering"}, {"limbs": []}, {"callout_sounds": {}}, {"ability_range": 99}):
            raw = {**original, **edit}; target = BASE + raw["id"] + ".json"
            result = invoke("preview_draft", asset=target, source_asset=WIGHT, draft=json.dumps(raw))["result"]
            self.assertFalse(result["valid"]); self.assertEqual(result["family"]["effective_operations"], ["edit"])
        raw = json.loads((ROOT / ORDINARY).read_bytes()); raw["id"] = "Player"
        result = invoke("preview_draft", asset=BASE + "Player.json", source_asset=ORDINARY, draft=json.dumps(raw))["result"]
        self.assertFalse(result["valid"]); self.assertIn("DUPLICATE_CREATURE", [d["code"] for d in result["diagnostics"]])
        with tempfile.TemporaryDirectory(prefix="w5f-readonly-") as folder:
            root = data_fixture(folder); raw["id"] = "outside_actor"
            outside = "roguelike/data/entities/outside_actor.json"; (root / outside).write_text(json.dumps(raw), encoding="utf-8")
            opened = invoke("inspect", root=root, asset=outside)["result"]
            self.assertFalse(opened["editable"]); self.assertTrue(opened["family"]["context"]["records"][0]["capability"]["constructible"])
            self.assertIsNotNone(opened["family"]["context"]["records"][0]["factory"])
            checked = invoke("preview_draft", root=root, asset=outside, source_asset=outside, draft=opened["raw"])["result"]
            self.assertTrue(checked["valid"]); self.assertEqual(checked["family"]["effective_operations"], [])
            checked = invoke("preview_draft", root=root, asset=outside, source_asset=outside, draft=opened["raw"] + " ")["result"]
            self.assertFalse(checked["valid"])


if __name__ == "__main__": unittest.main()
