"""Source entitlement, exact construction, dependencies and existing G17 route."""
import copy
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

CREATURE = "roguelike/data/entities/creatures/hollow_revenant.json"


class CreatureTests(unittest.TestCase):
    def test_loaded_catalog_noop_player_and_advanced_read_only(self):
        described = invoke("describe")["result"]["assets"]
        rows = [r for r in described if r["route"] == "creature_definition"]
        self.assertEqual(len(rows), 14)
        self.assertEqual(len([r for r in rows if r["category"] == "creatures"]), 13)
        self.assertEqual([r["id"] for r in rows if r["editable"]], ["hollow_revenant"])
        for path, editable in ((CREATURE, True), (CREATURE.replace("hollow_revenant", "hollow_knight"), False),
                               (CREATURE.replace("hollow_revenant", "vine_network"), False), ("roguelike/data/entities/player.json", False)):
            before = (ROOT/path).read_bytes()
            inspected = invoke("inspect", asset=path)["result"]
            self.assertEqual(inspected["raw"].encode(), before)
            self.assertEqual(inspected["editable"], editable)
            self.assertEqual((ROOT/path).read_bytes(), before)
            self.assertIsNone(inspected["creature_context"]["records"][0]["factory"])

    def test_real_factory_exact_hp_and_source_fidelity(self):
        source = (ROOT/CREATURE).read_bytes().decode()
        draft = source.replace('"id": "hollow_revenant"', '"id": "hollow_revenant_w4a_test"').replace('"base_hp": 14', '"base_hp": 19').replace('"max_hp": 14', '"max_hp": 19')
        path = CREATURE.replace(".json", "_w4a_test.json")
        result = invoke("preview_draft", asset=path, source_asset=CREATURE, draft=draft)["result"]
        self.assertTrue(result["valid"], result["diagnostics"])
        record = result["creature_context"]["records"][0]
        self.assertEqual(record["definition"], json.loads(draft))
        factory = record["factory"]
        self.assertEqual(factory["source_sha256"], hashlib.sha256(draft.encode()).hexdigest())
        self.assertEqual(factory["instance"]["fighter"]["hp"], 19)
        self.assertEqual(factory["instance"]["fighter"]["max_hp"], 19)
        self.assertEqual(factory["instance"]["ai_class"], "WanderingAI")
        self.assertEqual(factory["instance"]["perception"]["faction"], "hollow")
        self.assertEqual(factory["instance"]["inventory"], None)
        self.assertFalse((ROOT/path).exists())
        self.assertEqual((ROOT/CREATURE).read_bytes().decode(), source)

    def test_immutable_raw_fields_ranges_duplicate_keys_and_source_promotion(self):
        source = json.loads((ROOT/CREATURE).read_bytes())
        for key, value in (("description", "cannot change"), ("ai_type", "ambush"), ("tile", "missing"), ("category", "npc"), ("blocks_movement", 1)):
            raw = {**source, key:value}
            result = invoke("preview_draft", asset=CREATURE, source_asset=CREATURE, draft=json.dumps(raw))["result"]
            self.assertFalse(result["valid"])
            self.assertIn("READ_ONLY_FIELD", [d["code"] for d in result["diagnostics"]])
        # JSON serializers may render a numeric 1.0 as 1; this is not a type change.
        normalized = json.dumps(source).replace('"damage_multiplier": 1.0', '"damage_multiplier": 1')
        self.assertTrue(invoke("preview_draft", asset=CREATURE, source_asset=CREATURE, draft=normalized)["result"]["valid"])
        for hp in (0, -1, True, 1.5, 1000001):
            raw = copy.deepcopy(source); raw["base_hp"] = hp; raw["fighter"]["max_hp"] = hp
            result = invoke("preview_draft", asset=CREATURE, source_asset=CREATURE, draft=json.dumps(raw))["result"]
            self.assertFalse(result["valid"])
            self.assertIn("CREATURE_HP", [d["code"] for d in result["diagnostics"]])
        for text in ('{"id":', '{"id":"a","id":"b"}', json.dumps(source).replace('"base_hp": 14', '"base_hp": NaN')):
            self.assertFalse(invoke("preview_draft", asset=CREATURE, source_asset=CREATURE, draft=text)["result"]["valid"])
        raw = copy.deepcopy(source); raw["fighter"]["max_hp"] = 99
        self.assertFalse(invoke("preview_draft", asset=CREATURE, source_asset=CREATURE, draft=json.dumps(raw))["result"]["valid"])
        self.assertFalse(invoke("preview_draft", asset=CREATURE, source_asset=CREATURE.replace("hollow_revenant", "hollow_knight"), draft=json.dumps(source))["result"]["valid"])
        self.assertFalse(invoke("preview_draft", asset=CREATURE, source_asset="roguelike/data/entities/player.json", draft=json.dumps(source))["ok"])

    def test_case_collision_array_malformed_dependency_and_unknown_tile(self):
        with tempfile.TemporaryDirectory(prefix="w4a-creatures-") as directory:
            root = data_fixture(directory)
            raw = json.loads((root/CREATURE).read_bytes())
            duplicate = root/"roguelike/data/entities/creatures/collision.json"
            duplicate.write_text(json.dumps({**raw, "id":"HOLLOW_REVENANT"}))
            r = invoke("inspect", root=root, asset=CREATURE)["result"]
            self.assertFalse(r["editable"]); self.assertIn("DUPLICATE_CREATURE", [d["code"] for d in r["diagnostics"]])
            duplicate.write_text(json.dumps([{**raw, "id":"array_creature"}]))
            self.assertFalse(invoke("inspect", root=root, asset=duplicate.relative_to(root).as_posix())["result"]["editable"])
            duplicate.unlink()
            (root/CREATURE).write_text(json.dumps({**raw, "tile":"unknown_tile"}))
            r=invoke("inspect", root=root, asset=CREATURE)["result"]
            self.assertFalse(r["valid"]); self.assertIn("UNKNOWN_REFERENCE", [d["code"] for d in r["diagnostics"]])
            (root/CREATURE).write_text(json.dumps(raw))
            item=next((root/"roguelike/data/items").rglob("revenant_husk.json"))
            original=item.read_text();item.write_text(original.replace('"id":', '"id":"duplicate_key", "id":',1))
            r=invoke("preview_draft", root=root, asset=CREATURE, source_asset=CREATURE, draft=json.dumps(raw))["result"]
            self.assertFalse(r["valid"]);self.assertIsNone(r["creature_context"])

    def test_variant_g17_legal_actor_blocked_cell_and_direct_references(self):
        os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
        sys.path.insert(0, str(ROOT/"roguelike"))
        import config
        config.DEBUG_MODE=False
        from engine.data_loader import DataLoader
        from generation.structure_preview import preview
        from generation.context import GenerationError
        with tempfile.TemporaryDirectory(prefix="w4a-g17-") as directory, contextlib.redirect_stdout(io.StringIO()):
            root=data_fixture(directory)
            raw=json.loads((root/CREATURE).read_bytes()); raw["id"]="revenant_g17_w4a"; raw["base_hp"]=19; raw["fighter"]["max_hp"]=19
            target=root/"roguelike/data/entities/creatures/revenant_g17_w4a.json"; target.write_text(json.dumps(raw))
            room=json.loads((ROOT/"roguelike/docs/examples/g17_authored_creature_room.json").read_bytes())
            actor_record=next(s for s in room["special_tiles"] if s.get("type")=="creature")
            actor_record["creature_id"]=raw["id"]
            layout=root/"roguelike/data/layouts/w4a_g17.json"; layout.write_text(json.dumps(room))
            data=DataLoader(str(root/"roguelike/data"))
            report, _, actors=preview(room,"authored_submap",data,path=str(layout))
            self.assertTrue(report["passed"])
            self.assertEqual([(a._creature_id,a.fighter.max_hp) for a in actors],[(raw["id"],19)])
            ref=invoke("inspect",root=root,asset=target.relative_to(root).as_posix())["result"]["creature_context"]["records"][0]["references"]
            self.assertEqual(len(ref),1);self.assertEqual(ref[0]["route"],"authored_submap")
            actor_record["x"],actor_record["y"]=2,5  # Existing return stair/arrival.
            with self.assertRaises(GenerationError): preview(room,"authored_submap",data,path=str(layout))
            self.assertFalse(any(r.get("id")==raw["id"] for z in data.zones.values() for r in z.get("creatures",[])))


if __name__ == "__main__": unittest.main()
