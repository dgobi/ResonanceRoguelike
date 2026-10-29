"""W3B current-source identity, narrow capability and real factory evidence."""
import copy
import hashlib
import json
import tempfile
import unittest
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

ITEM = "roguelike/data/items/components/wood_bundle.json"
POOL = "roguelike/data/loot_pools/workshop_b_fuel.json"

class ItemTests(unittest.TestCase):
    def test_recursive_catalogue_noop_complex_sources_and_truthful_binding(self):
        assets = invoke("describe")["result"]["assets"]
        rows = [a for a in assets if a["route"] == "item_definition"]
        self.assertEqual(len(rows), 79)
        self.assertEqual([r["path"] for r in rows], sorted(r["path"] for r in rows))
        from collections import Counter
        self.assertEqual(len([r for r in rows if r["editable"]]),54)
        self.assertEqual(Counter(r['category'] for r in rows if r['editable']),dict(component=4,butchery=18,consumable=20,weapon=6,armor=2,shield=1,equipment=3))
        for asset in (ITEM, "roguelike/data/items/tools/tallow_torch.json", "roguelike/data/items/weapons/binding_knife.json",
                      "roguelike/data/items/consumables/resonant_tincture.json"):
            path = ROOT / asset; before = path.read_bytes(); meta = path.stat()
            r = invoke("inspect", asset=asset)["result"]
            self.assertEqual(r["raw"].encode(), before)
            self.assertEqual(path.read_bytes(), before); self.assertEqual(path.stat().st_mtime_ns, meta.st_mtime_ns)
            c = r["family"]["context"]["records"][0]
            self.assertEqual(c["capability"]["editable"], asset == ITEM or 'binding_knife' in asset)
            self.assertIsNotNone(c["factory"], c["diagnostics"])
            self.assertEqual(c["use"]["status"], "Not applicable" if asset == ITEM else "Handler found")
            if asset == ITEM:
                self.assertTrue(any(p["id"] == "workshop_b_fuel" and p["index"] == 0 for p in c["pools"]))
                self.assertTrue(any(d["id"] == "campfire" and d["kind"] == "Potential tag match" for d in c["dependencies"]))
            if "tincture" in asset: self.assertIn("do not consume", c["use"]["notes"][0])

    def test_game_owned_fields_and_raw_invalid_cases(self):
        raw = json.loads((ROOT / ITEM).read_bytes())
        for field, values in {"weight": [-1, "heavy", True, float("nan"), float("inf"), 1e309],
                              "keywords": [[{"tag": "missing", "tier": 1}], [{"tag": [], "tier": 1}],
                                           [{"tag": "fuel", "tier": -1}], [{"tag": "fuel", "tier": 1.5}],
                                           [{"tag": "fuel", "tier": True}]],
                              "category": ["weapon"], "on_use": ["missing_handler"], "stackable": ["yes"]}.items():
            for value in values:
                candidate = {**raw, field: value}
                response = invoke("preview_draft", asset=ITEM, draft=json.dumps(candidate))
                self.assertTrue(response["ok"], response)
                self.assertFalse(response["result"]["valid"], candidate)
                self.assertFalse(response["result"]["factory_verified"])
        for text in ('{"id":', '{"id":"a","id":"b"}', '\ufeff' + json.dumps(raw)):
            r = invoke("preview_draft", asset=ITEM, draft=text)["result"]
            self.assertFalse(r["valid"], r)
        for field in ("movesets", "light", "on_use_effects"):
            r = invoke("preview_draft", asset=ITEM, draft=json.dumps({**raw, field: []}))["result"]
            self.assertIn("UNSUPPORTED_ITEM", [d["code"] for d in r["diagnostics"]])

    def test_duplicate_case_collision_array_discovery_and_unknown_handler(self):
        with tempfile.TemporaryDirectory(prefix="w3b-identity-") as folder:
            root = data_fixture(folder); raw = json.loads((root / ITEM).read_bytes())
            nested = root / "roguelike/data/items/components/nested"; nested.mkdir()
            duplicate = nested / "duplicate.json"; duplicate.write_text(json.dumps(raw), encoding="utf-8")
            r = invoke("inspect", root=root, asset=ITEM)["result"]
            self.assertFalse(r["editable"])
            d = next(d for d in r["diagnostics"] if d["code"] == "DUPLICATE_ID")
            self.assertIn(ITEM, d["message"]); self.assertIn("nested/duplicate.json", d["message"])
            self.assertFalse(invoke("preview_draft", root=root, asset=POOL, draft=(root/POOL).read_text())["result"]["valid"])
            raw["id"] = "WOOD_BUNDLE"; duplicate.write_text(json.dumps(raw), encoding="utf-8")
            self.assertFalse(invoke("inspect", root=root, asset=ITEM)["result"]["editable"])
            raw["id"] = "nested_component"; raw["on_use"] = "does_not_exist"
            duplicate.write_text(json.dumps([raw]), encoding="utf-8")
            catalog = invoke("describe", root=root)["result"]["assets"]
            row = next(r for r in catalog if r["id"] == raw["id"])
            self.assertEqual(row["pointer"], "/0"); self.assertFalse(row["editable"])
            r = invoke("inspect", root=root, asset=row["path"])["result"]["family"]["context"]["records"][0]
            self.assertEqual(r["use"]["status"], "Unknown handler"); self.assertIsNone(r["factory"])

    def test_exact_new_item_new_pool_and_production_instantiation(self):
        with tempfile.TemporaryDirectory(prefix="w3b-chain-") as folder:
            root = data_fixture(folder)
            before = {p: (root/p).read_bytes() for p in (ITEM, POOL)}
            raw = json.loads(before[ITEM]); raw.update(id="wood_bundle_w3b_test", weight=1.75)
            raw["unknown_metadata"] = {"deep": [[None, True], ["authored text", 9]]}
            draft = json.dumps(raw, ensure_ascii=False, indent=2) + "\r\n"
            dest = ITEM.replace("wood_bundle", raw["id"])
            r = invoke("preview_draft", root=root, asset=dest, source_asset=ITEM, draft=draft)["result"]
            self.assertTrue(r["valid"], r); self.assertTrue(r["factory_verified"])
            self.assertEqual(r["draft_sha256"], hashlib.sha256(draft.encode()).hexdigest())
            self.assertEqual(r["factory"]["instance"]["weight"], 1.75)
            self.assertEqual(r["factory"]["item_id"], raw["id"]); self.assertFalse((root/dest).exists())
            # Host publication is separately exercised natively; this fixture
            # installs exact reviewed bytes solely to check current loader/factory.
            (root/dest).write_bytes(draft.encode())
            pool = json.loads(before[POOL]); pool["id"] = "workshop_b_fuel_w3b_test"; pool["items"][0]["item_id"] = raw["id"]
            pool_dest = POOL.replace("workshop_b_fuel", pool["id"])
            text = json.dumps(pool)
            self.assertTrue(invoke("preview_draft", root=root, asset=pool_dest, source_asset=POOL, draft=text)["result"]["valid"])
            (root/pool_dest).write_text(text, encoding="utf-8")
            reopened = invoke("inspect", root=root, asset=dest)["result"]
            c = reopened["family"]["context"]["records"][0]
            self.assertEqual(c["factory"]["instance"]["weight"], 1.75)
            self.assertEqual(c["pools"][0]["id"], pool["id"])
            self.assertEqual(reopened["raw"].encode(), draft.encode())
            for p, b in before.items(): self.assertEqual((root/p).read_bytes(), b)

if __name__ == "__main__": unittest.main(verbosity=2)
