"""W3A source identity, game-owned pool constraints and real population fixture."""
import copy
import hashlib
import json
import tempfile
import unittest
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

POOL = "roguelike/data/loot_pools/alchemist_reagents.json"
BUILDING = "roguelike/data/buildings/commercial/apothecary_a.json"

class PoolTests(unittest.TestCase):
    def test_live_discovery_noop_and_item_provenance(self):
        before = (ROOT / POOL).read_bytes(); meta = (ROOT / POOL).stat()
        rows = [a for a in invoke("describe")["result"]["assets"] if a["route"] == "contextual_loot_pool"]
        self.assertEqual([r["path"] for r in rows], sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "roguelike/data/loot_pools").glob("*.json")))
        r = invoke("inspect", asset=POOL)["result"]
        self.assertTrue(r["valid"], r["diagnostics"]); self.assertEqual(r["raw"].encode(), before)
        c = r["pool_context"]
        self.assertTrue(any(v["id"] == "apothecary_a" and v["x"] == 1 for v in c["references"]))
        for row in json.loads(before)["items"]:
            item = c["items"][row["item_id"]]; self.assertTrue(item["resolved"])
            s = item["sources"][0]; raw = json.loads((ROOT / s["path"]).read_bytes())
            self.assertEqual(raw if not s["pointer"] else raw[int(s["pointer"][1:])], s["definition"])
        self.assertEqual((ROOT / POOL).read_bytes(), before)
        self.assertEqual((ROOT / POOL).stat().st_mtime_ns, meta.st_mtime_ns)

    def test_authoritative_constraints_and_inactive_fields(self):
        original = json.loads((ROOT / POOL).read_bytes())
        cases = []
        for value, code in [("bad", "NUMBER"), (-1, "NUMBER"), (True, "NUMBER")]:
            r = copy.deepcopy(original); r["items"][0]["weight"] = value; cases.append((r, code))
        r = copy.deepcopy(original); r["items"][0]["item_id"] = "missing_w3a"; cases.append((r, "REFERENCE"))
        for bounds in ([4, 2], [-1, 2], [1, 2, 3], [True, 3]):
            r = copy.deepcopy(original); r["roll_count"] = bounds; cases.append((r, "POOL_COUNT"))
        for candidate, code in cases:
            v = invoke("preview_draft", asset=POOL, draft=json.dumps(candidate))["result"]
            self.assertFalse(v["valid"], v); self.assertIn(code, [d["code"] for d in v["diagnostics"]])
        r = copy.deepcopy(original); r["items"][0]["quantity"] = {"unknown": [1, 2]}; r["notes"] = [["retain", None]]
        v = invoke("preview_draft", asset=POOL, draft=json.dumps(r))["result"]
        self.assertTrue(v["valid"], v); self.assertFalse(v["population_verified"])
        self.assertTrue(any(d["code"] == "INACTIVE_POOL_FIELD" and d["severity"] == "warning" for d in v["diagnostics"]))
        self.assertEqual(v["draft_sha256"], hashlib.sha256(json.dumps(r).encode()).hexdigest())
        for draft in ('{"id":}', '{"id":"a","id":"b"}', '{"id":NaN}'):
            self.assertFalse(invoke("preview_draft", asset=POOL, draft=draft)["result"]["syntax_valid"])

    def test_variant_identity_and_loader_rejection(self):
        raw = json.loads((ROOT / POOL).read_bytes()); dest = POOL.replace("alchemist_reagents", "w3a_unique")
        duplicate = invoke("preview_draft", asset=dest, source_asset=POOL, draft=json.dumps(raw))["result"]
        self.assertFalse(duplicate["valid"]); self.assertIn("DUPLICATE_ID", [d["code"] for d in duplicate["diagnostics"]])
        raw["id"] = "w3a_unique"
        result = invoke("preview_draft", asset=dest, source_asset=POOL, draft=json.dumps(raw))["result"]
        self.assertTrue(result["valid"], result)
        # The structure reader tolerates BOM, but the production pool loader does not.
        result = invoke("preview_draft", asset=dest, source_asset=POOL, draft="\ufeff" + json.dumps(raw))["result"]
        self.assertFalse(result["valid"]); self.assertIn("LOADER_IDENTITY", [d["code"] for d in result["diagnostics"]])
        self.assertFalse((ROOT / dest).exists())
        for asset in ("roguelike/data/loot/x.json", "roguelike/data/loot_pools/../x.json", "roguelike/data/loot_pools/nested/a.json", "roguelike/saves/a.json"):
            self.assertFalse(invoke("preview_draft", asset=asset, draft="{}")["ok"])

    def test_real_two_step_chain_repeated_entries_and_zero_remaining_weight(self):
        with tempfile.TemporaryDirectory(prefix="w3a-chain-") as directory:
            root = data_fixture(directory)
            pool_path = "roguelike/data/loot_pools/w3a_chain.json"
            # Two entries of the same ID are two draws; a zero-total remainder stops.
            raw = {"id": "w3a_chain", "roll_count": [3, 3], "items": [
                {"item_id": "wood_bundle", "weight": 1}, {"item_id": "wood_bundle", "weight": 2}, {"item_id": "flint_shard", "weight": 0}]}
            draft = json.dumps(raw)
            self.assertTrue(invoke("preview_draft", root=root, asset=pool_path, source_asset=POOL, draft=draft)["result"]["valid"])
            (root / pool_path).write_text(draft, encoding="utf-8")
            source = json.loads((root / BUILDING).read_bytes()); source["id"] = "apothecary_w3a_chain"
            source["special_tiles"][0]["loot_pools"] = ["w3a_chain"]
            v = invoke("preview_draft", root=root, asset=BUILDING.replace("apothecary_a", source["id"]), draft=json.dumps(source), seed=20261023)["result"]
            self.assertTrue(v["valid"], v["diagnostics"])
            p = v["preview"]; ox, oy = p["origin"]
            container = next(c for c in p["containers"] if (c["x"], c["y"]) == (ox + 1, oy + 1))
            self.assertEqual([i["item_id"] for i in container["items"]], ["wood_bundle", "wood_bundle"])
            self.assertTrue(p["access_verified"])
            self.assertEqual((root / POOL).read_bytes(), (ROOT / POOL).read_bytes())
            self.assertEqual((root / BUILDING).read_bytes(), (ROOT / BUILDING).read_bytes())
            # A later duplicate cannot silently redirect a building's pool link.
            (root / "roguelike/data/loot_pools/w3a_duplicate.json").write_text(draft, encoding="utf-8")
            bad = invoke("preview_draft", root=root, asset=BUILDING.replace("apothecary_a", source["id"]), draft=json.dumps(source))["result"]
            self.assertFalse(bad["valid"])
            self.assertIn("POOL_SOURCE", [d["code"] for d in bad["diagnostics"]])

if __name__ == "__main__": unittest.main(verbosity=2)
