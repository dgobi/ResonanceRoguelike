"""W1 process boundary tests. All edits stay in worker scratch or disposable data."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from test_bridge import ROOT, invoke

ASSET = "roguelike/data/buildings/commercial/workshop_b.json"

def data_fixture(destination):
    """Runtime test inputs only: data and required Python, never a Git/dev checkout."""
    destination = Path(destination)
    for p in (ROOT / "roguelike").rglob("*.py"):
        if any(x in p.parts for x in ("saves", "__pycache__")): continue
        target = destination / p.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    shutil.copytree(ROOT / "roguelike/data", destination / "roguelike/data")
    shutil.copy2(ROOT / "requirements-baseline.txt", destination / "requirements-baseline.txt")
    return destination

class AuthoringTests(unittest.TestCase):
    def test_discovery_matches_all_supported_candidates_and_reads_two_deep_sources(self):
        result = invoke("describe")["result"]
        actual = [a["path"] for a in result["assets"] if a["editable"] and a["route"] == "ordinary_building"]
        expected = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "roguelike/data/buildings").glob("*/*.json") if p.parent.name != "plaza")
        self.assertEqual(actual, expected)
        for asset in (ASSET, "roguelike/data/buildings/commercial/apothecary_b.json"):
            path = ROOT / asset; before = path.read_bytes(); stat = path.stat()
            inspected = invoke("inspect", asset=asset)["result"]
            self.assertTrue(inspected["valid"])
            self.assertEqual(inspected["raw"].encode("utf-8"), before)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual((path.stat().st_mtime_ns,path.stat().st_ctime_ns),(stat.st_mtime_ns,stat.st_ctime_ns))
        self.assertTrue(all(not a["editable"] for a in result["assets"] if a["route"] not in ("ordinary_building", "contextual_loot_pool", "item_definition", "recipe_definition")))

    def test_exact_draft_bytes_real_contract_and_route_rejections(self):
        raw = json.loads((ROOT / ASSET).read_text(encoding="utf-8"))
        raw["description"] = "W1 disposable description"
        raw["unknown_metadata"] = {"deep": [[1,"retained"],[None,True]]}
        draft = json.dumps(raw, ensure_ascii=False, indent=2) + "\r\n"
        result = invoke("validate_draft", asset=ASSET, draft=draft)["result"]
        self.assertTrue(result["valid"],result)
        self.assertEqual(result["draft_sha256"],hashlib.sha256(draft.encode()).hexdigest())
        self.assertFalse(result["placement_verified"]); self.assertFalse(result["population_verified"])
        cases = []
        r=copy.deepcopy(raw);r["legend"]["#"]="not_a_real_terrain";cases.append((r,"TERRAIN_USED"))
        r=copy.deepcopy(raw);r["width"]+=1;cases.append((r,"DIMENSION"))
        r=copy.deepcopy(raw);r["special_tiles"][0]["x"]=1000;cases.append((r,"COORDINATE"))
        r=copy.deepcopy(raw);r["special_tiles"].append({"x":2,"y":2,"type":"creature","creature_id":"hollow_revenant"});cases.append((r,"CREATURE_ROUTE"))
        r=copy.deepcopy(raw);r["weight"]=-1;cases.append((r,"NUMBER"))
        for candidate,code in cases:
            result=invoke("validate_draft",asset=ASSET,draft=json.dumps(candidate))["result"]
            self.assertFalse(result["valid"]);self.assertIn(code,[d["code"] for d in result["diagnostics"]])
        for draft in ('{\n"id":}', '{"id":"a",}', '{"id":"a","id":"b"}', '{"id":NaN}', '{/*no*/}'):
            r=invoke("validate_draft",asset=ASSET,draft=draft)["result"]
            self.assertFalse(r["valid"]);self.assertFalse(r["syntax_valid"])
            if draft.startswith('{\n'): self.assertEqual(r["diagnostics"][0]["line"],2)
        self.assertFalse(invoke("validate_draft",asset="roguelike/data/layouts/starting_lab.json",draft="{}")['ok'])

    def test_unique_variant_and_repair_invalid_source_without_live_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="w1-data-test-") as directory:
            root=data_fixture(directory)
            original=(root/ASSET).read_bytes()
            source=json.loads(original);source["id"]="workshop_w1_test"
            dest="roguelike/data/buildings/commercial/workshop_w1_test.json"
            r=invoke("validate_draft",root=root,asset=dest,draft=json.dumps(source))["result"]
            self.assertTrue(r["valid"],r);self.assertFalse((root/dest).exists())
            source["id"]="apothecary_b"
            r=invoke("validate_draft",root=root,asset=dest,draft=json.dumps(source))["result"]
            self.assertFalse(r["valid"]);self.assertIn("DUPLICATE_ID",[d["code"] for d in r["diagnostics"]])
            (root/ASSET).write_text('{"broken":',encoding="utf-8")
            self.assertTrue(invoke("identify",root=root)["ok"])
            self.assertTrue(invoke("describe",root=root)["ok"])
            self.assertFalse(invoke("inspect",root=root,asset=ASSET)["result"]["valid"])
            r=invoke("validate_draft",root=root,asset=ASSET,draft=original.decode())["result"]
            self.assertTrue(r["valid"],r)
            self.assertEqual((root/ASSET).read_text(),'{"broken":')

if __name__ == "__main__": unittest.main(verbosity=2)
