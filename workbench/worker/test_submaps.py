"""W4C source entitlement and real G17 compiler/scene tests in disposable data."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from test_authoring import data_fixture
from test_bridge import ROOT, invoke

ASSET = "roguelike/data/layouts/w4c_room.json"
EXAMPLE = "roguelike/docs/examples/g17_authored_creature_room.json"


class SubmapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="w4c-submap-")
        self.addCleanup(self.temp.cleanup)
        self.root = data_fixture(self.temp.name)
        self.raw = json.loads((ROOT / EXAMPLE).read_bytes())
        self.raw["id"] = "w4c_room"
        self.raw["metadata"] = {"nested": [True, None, [2, 1]]}
        self.save()

    def save(self):
        self.original = (json.dumps(self.raw, indent=2) + "\r\n").encode()
        (self.root / ASSET).write_bytes(self.original)

    def check(self, raw=None, **args):
        result = invoke("preview_draft", root=self.root, source_asset=ASSET, asset=ASSET,
                        draft=json.dumps(raw or self.raw), seed=20261026, **args)
        self.assertEqual((self.root / ASSET).read_bytes(), self.original)
        return result

    def test_actual_actor_translation_definition_hash_and_single_file_reopen(self):
        opened = invoke("inspect", root=self.root, asset=ASSET)["result"]
        self.assertTrue(opened["editable"])
        self.assertNotIn("player", [c["id"] for c in opened["catalog"]["creatures"]])
        self.assertEqual(opened["raw"].encode(), self.original)
        raw=copy.deepcopy(self.raw);raw["special_tiles"][0]["x"]=6
        result=self.check(raw)["result"];self.assertTrue(result["valid"],result)
        p=result["preview"];actor=p["population_receipts"][0]
        self.assertEqual(p["actors"], [{"x":41,"y":20,"id":"hollow_revenant"}])
        self.assertEqual(actor["source_xy"],[6,2]);self.assertEqual(actor["xy"],[41,20])
        self.assertEqual(actor["actor_classes"],["Actor"]);self.assertEqual(actor["actual_count"],1)
        self.assertEqual(actor["actors"][0]["fighter"]["hp"],14)
        definition=json.loads((self.root/"roguelike/data/entities/creatures/hollow_revenant.json").read_bytes())
        from hashlib import sha256
        self.assertEqual(actor["creature_definition"]["sha256"],sha256(json.dumps(definition,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        raw["id"]="w4c_variant";dest="roguelike/data/layouts/w4c_variant.json";text=json.dumps(raw)
        r=invoke("preview_draft",root=self.root,asset=dest,source_asset=ASSET,draft=text)["result"]
        self.assertTrue(r["valid"],r);self.assertFalse((self.root/dest).exists())
        # Worker never publishes. Host native/Rust tests own atomic publication.
        (self.root/dest).write_bytes(text.encode())
        reopened=invoke("inspect",root=self.root,asset=dest)["result"]
        self.assertEqual(reopened["sha256"],hashlib.sha256(text.encode()).hexdigest())
        self.assertTrue(invoke("preview",root=self.root,asset=dest)["result"]["passed"])

    def test_g17_schema_errors_and_raw_scope(self):
        cases=[]
        for value in ["missing", "player", None]:
            r=copy.deepcopy(self.raw);r["special_tiles"][0]["creature_id"]=value;cases.append(r)
        for value in [True,1.5,-1,11]:
            r=copy.deepcopy(self.raw);r["special_tiles"][0]["x"]=value;cases.append(r)
        r=copy.deepcopy(self.raw);r["special_tiles"][0]["kind"]="item";cases.append(r)
        r=copy.deepcopy(self.raw);r["special_tiles"][0]={"type":"weighted","x":7,"y":2,"spawn_table":[{"type":"creature","creature_id":"hollow_revenant","weight":1}]};cases.append(r)
        for raw in cases:
            result=self.check(raw)
            self.assertTrue(result["ok"], result);self.assertFalse(result["result"]["valid"],result)
            self.assertIsNone(result["result"]["preview"])
        for text in ('{"id":', '[]', 'null'):
            r=invoke("preview_draft",root=self.root,asset=ASSET,source_asset=ASSET,draft=text)
            self.assertTrue(r["ok"],r);self.assertFalse(r["result"]["valid"])
        for field,value in [("player_start",{"x":1,"y":1}), ("metadata",{})]:
            r=copy.deepcopy(self.raw);r[field]=value
            self.assertEqual(self.check(r)["error"]["code"],"LAYOUT_FIELD")
        r=copy.deepcopy(self.raw);r["special_tiles"][1]["x"]=6
        self.assertEqual(self.check(r)["error"]["code"],"LAYOUT_FIELD")
        r=copy.deepcopy(self.raw);r["metadata"]["nested"][0]=1
        self.assertEqual(self.check(r)["error"]["code"],"LAYOUT_FIELD")

    def test_production_occupancy_order_arrival_stairs_decor_water_and_corridor(self):
        # All context changes happen before opening, never via marker draft mutation.
        self.raw["special_tiles"].append(dict(type="container",x=3,y=3,decor_id="crate",loot_pools=[]))
        self.raw["legend"]["~"]="deep_water"
        self.raw["layers"][3]="#...~.....#"
        self.raw["legend"][">"]="stairs_down"
        self.raw["layers"][4]="#.>.......#"
        self.save()
        for xy in [(0,0),(3,3),(4,3),(2,4),(2,5),(8,4)]:
            raw=copy.deepcopy(self.raw);raw["special_tiles"][0].update(x=xy[0],y=xy[1])
            result=self.check(raw)["result"]
            self.assertFalse(result["valid"],(xy,result));self.assertIsNone(result["preview"])
            self.assertEqual(next(d for d in result["diagnostics"] if d["severity"] == "error")["source_xy"],list(xy))
        raw=copy.deepcopy(self.raw);raw["special_tiles"][0].update(x=4,y=3,creature_id="drowned_revenant")
        self.assertTrue(self.check(raw)["result"]["valid"])
        raw["special_tiles"][0].update(x=0,y=0)
        self.assertFalse(self.check(raw)["result"]["valid"])
        raw=copy.deepcopy(self.raw);raw["special_tiles"].append(copy.deepcopy(raw["special_tiles"][0]))
        self.assertFalse(self.check(raw)["result"]["valid"])
        # Actual arrival on ordinary floor, independent of a physical stair.
        self.raw["player_start"]={"x":1,"y":1};self.save()
        raw=copy.deepcopy(self.raw);raw["special_tiles"][0].update(x=1,y=1)
        self.assertFalse(self.check(raw)["result"]["valid"])
        # A hostile corridor guard is legal; static access does not treat actors as walls.
        self.raw["layers"]=["###########","#.........#","#####.#####","#.........#","#.........#","#.<.......#","###########"]
        self.save()
        raw=copy.deepcopy(self.raw);raw["special_tiles"][0].update(x=5,y=2)
        self.assertTrue(self.check(raw)["result"]["valid"])

    def test_source_entitlement_example_and_unsupported_source_cannot_promote(self):
        self.assertTrue(invoke("inspect",asset=EXAMPLE)["result"]["editable"])
        example=invoke("preview",asset=EXAMPLE)["result"]
        self.assertTrue(example["passed"]);self.assertTrue(example["access_source"]["sha256"])
        self.raw["legend_weights"]={};self.save()
        self.assertFalse(invoke("inspect",root=self.root,asset=ASSET)["result"]["editable"])
        raw=copy.deepcopy(self.raw);raw.pop("legend_weights")
        self.assertEqual(self.check(raw)["error"]["code"],"READ_ONLY_LAYOUT")
        for asset in ["roguelike/data/layouts/starting_lab.json"]:
            response=invoke("preview_draft",asset="roguelike/data/layouts/forged.json",source_asset=asset,draft=json.dumps(raw))
            self.assertFalse(response["ok"])


if __name__ == "__main__": unittest.main()
