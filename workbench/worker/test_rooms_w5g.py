"""W5G real registered policy, carrier/arrival and receipt-owned access negatives."""
import copy, json, tempfile, unittest
from pathlib import Path
from test_bridge import ROOT, invoke
from test_authoring import data_fixture
SOURCE="roguelike/data/layouts/w5g_room.json"
TEMPLATE="roguelike/docs/examples/g17_authored_creature_room.json"

class RoomTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="w5g-room-");self.addCleanup(self.temp.cleanup)
        self.root=data_fixture(self.temp.name)
        self.raw=json.loads((ROOT/TEMPLATE).read_bytes());self.raw["id"]="w5g_room"
        self.raw["metadata"]={"nested":[True,None,"λ"]}
        self.save()
    def save(self): (self.root/SOURCE).write_text(json.dumps(self.raw),encoding="utf-8")
    def check(self,raw,source=SOURCE,target=SOURCE):
        response=invoke("preview_draft",root=self.root,asset=target,source_asset=source,draft=json.dumps(raw,ensure_ascii=False),seed=20261027)
        self.assertTrue(response["ok"],response)
        return response["result"]
    def test_registered_discovery_immediate_sources_operations_and_original_promotion(self):
        rows=[r for r in invoke("describe",root=self.root)["result"]["assets"] if r.get("family_id")=="room"]
        self.assertEqual(len([r for r in rows if r["path"]==SOURCE]),1)
        opened=invoke("inspect",root=self.root,asset=SOURCE)["result"]
        self.assertEqual(opened["route"],"authored_submap");self.assertEqual(opened["family"]["effective_operations"],["edit","variant"])
        self.assertEqual(opened["family"]["descriptor"]["production_route"],"authored_submap")
        for protected in ("starting_lab","other"):
            path="roguelike/data/layouts/"+("renamed_lab.json" if protected=="starting_lab" else "starting_lab.json")
            (self.root/path).write_text(json.dumps({**self.raw,"id":protected}),encoding="utf-8")
            candidate={**self.raw,"id":"promoted"}
            result=self.check(candidate,source=path,target="roguelike/data/layouts/promoted.json")
            self.assertFalse(result["valid"])
            self.assertIn("SOURCE_ENTITLEMENT" if protected=="other" else "DUPLICATE_ID",[d["code"] for d in result["diagnostics"]])
            (self.root/path).unlink()
        nested=self.root/"roguelike/data/layouts/nested";nested.mkdir();(nested/"nested.json").write_text(json.dumps({**self.raw,"id":"nested"}))
        self.assertFalse(any(r["path"].endswith("nested/nested.json") for r in invoke("describe",root=self.root)["result"]["assets"]))
        self.assertFalse(invoke("preview_draft",root=self.root,asset="roguelike/docs/examples/other.json",source_asset=SOURCE,draft="{}")['ok'])
    def test_closed_door_authored_and_actual_arrival_with_and_without_creatures(self):
        for creature in (False,True):
            raw=copy.deepcopy(self.raw);rows=[list(r) for r in raw["layers"]];rows[3][3]="+";raw["layers"]=["".join(r) for r in rows];raw["legend"]["+"]="door_closed";raw["player_start"]={"x":3,"y":3}
            if not creature: raw["special_tiles"]=[s for s in raw["special_tiles"] if s["type"]!="creature"]
            result=self.check(raw);self.assertTrue(result["valid"],result["diagnostics"])
            p=result["preview"];self.assertEqual(p["authored_start"],[38,21]);self.assertEqual(p["spawn"],[37,20]);self.assertTrue(all(r["passed"] for r in p["access"]))
        raw=copy.deepcopy(self.raw);raw.update(width=80,height=43,layers=["#"*80 for _ in range(43)],player_start={"x":0,"y":0},special_tiles=[])
        raw["layers"][41]="#"*78+"<"+"#"
        result=self.check(raw);self.assertFalse(result["valid"]);self.assertIn("invalid actual player arrival",str(result["diagnostics"]))
    def test_receipt_owned_overlapping_items_relocation_and_container_access(self):
        raw=copy.deepcopy(self.raw);raw["special_tiles"] += [dict(type="item",x=7,y=2,item_id="wood_bundle"),dict(type="item",x=0,y=0,item_id="letter",text_id="lab_note_primary_b")]
        result=self.check(raw);self.assertTrue(result["valid"],result["diagnostics"])
        rows=result["preview"]["population_receipts"];self.assertEqual(len(rows),5)
        self.assertEqual(rows[-1]["source_xy"],[0,0]);self.assertTrue(rows[-1]["relocated"]);self.assertNotEqual(rows[-1]["xy"],[35,18]);self.assertEqual(rows[-1]["objects"][0]["item_id"],"letter")
        self.assertEqual(rows[-1]["objects"][0]["text_id"],"lab_note_primary_b")
        self.assertTrue(all(r.get("receipt_owned",True) for r in result["preview"]["access"]))
        self.assertEqual(len(next(r for r in result["preview"]["items"] if (r["x"],r["y"])==(42,20))["items"]),2)
        for kind in ("container","creature"):
            bad=copy.deepcopy(self.raw);bad["special_tiles"].append(copy.deepcopy(bad["special_tiles"][2 if kind=="container" else 0]));self.assertFalse(self.check(bad)["valid"])
        blocked=copy.deepcopy(self.raw);grid=[list(r) for r in blocked["layers"]]
        for x in range(7,10):
            for y in range(3,6): grid[y][x]="#"
        grid[4][8]=".";blocked["layers"]=["".join(r) for r in grid]
        result=self.check(blocked);self.assertFalse(result["valid"]);self.assertTrue(any(r["kind"]=="container" and not r["passed"] for r in result["preview"]["access"]))
    def test_route_specific_explicit_readable_carrier_and_false_binding(self):
        text=json.loads((self.root/"roguelike/data/texts/lab/lab_note_primary_b.json").read_bytes());text["id"]="w5g_route_text"
        (self.root/"roguelike/data/texts/lab/w5g_route_text.json").write_text(json.dumps(text),encoding="utf-8")
        mapping=self.root/"roguelike/data/texts/text_item_map.json";mapped=json.loads(mapping.read_text());mapped["w5g_route_text"]="missing_mapped_carrier";mapping.write_text(json.dumps(mapped),encoding="utf-8")
        raw=copy.deepcopy(self.raw);raw["special_tiles"].append(dict(type="item",x=1,y=1,item_id="letter",text_id="w5g_route_text"))
        result=self.check(raw);self.assertTrue(result["valid"],result["diagnostics"])
        self.assertEqual(result["preview"]["population_receipts"][-1]["objects"][0]["item_id"],"letter")
        raw["special_tiles"][-1]["item_id"]="wood_bundle";result=self.check(raw);self.assertFalse(result["valid"]);self.assertIn("FALSE_READABLE",[d["code"] for d in result["diagnostics"]])
        path="roguelike/data/buildings/commercial/workshop_b.json";building=json.loads((self.root/path).read_bytes());building["special_tiles"].append(dict(type="item",x=2,y=2,item_id="letter",text_id="w5g_route_text"))
        ordinary=invoke("preview_draft",root=self.root,asset=path,draft=json.dumps(building))["result"]
        self.assertFalse(ordinary["valid"]);self.assertTrue(any("text_item_map" in d["field"] for d in ordinary["diagnostics"]))
    def test_bounds_legend_missing_and_ambiguous_dependencies_and_layout_alias(self):
        for mutate in (lambda r:r.update(width=81),lambda r:r["legend"].pop("."),lambda r:r["special_tiles"][1].update(item_id="absent"),lambda r:r["special_tiles"][0].update(x=99)):
            raw=copy.deepcopy(self.raw);mutate(raw);self.assertFalse(self.check(raw)["valid"])
        alias=self.root/"roguelike/data/layouts/alias.json";alias.write_text(json.dumps({**self.raw,"id":"W5G_ROOM"}),encoding="utf-8")
        self.assertFalse(invoke("inspect",root=self.root,asset=SOURCE)["result"]["editable"]);alias.unlink()
        item=json.loads((self.root/"roguelike/data/items/components/wood_bundle.json").read_bytes());item["id"]="WOOD_BUNDLE"
        (self.root/"roguelike/data/items/components/alias.json").write_text(json.dumps(item),encoding="utf-8")
        self.assertFalse(self.check(self.raw)["valid"])
    def test_explicit_and_fallback_return_precedence_and_blocked_return(self):
        raw=copy.deepcopy(self.raw);raw.update(exit_direction="north",exit_x=1,exit_y=1)
        p=self.check(raw)["preview"];self.assertEqual([(s["x"],s["y"]) for s in p["stairs"] if s["terrain"]=="stairs_up"],[(37,23)])
        raw["layers"]=[r.replace("<",".") for r in raw["layers"]]
        for direction,expected in (("north",(40,19)),("south",(40,19)),("east",(36,21)),("west",(36,21))):
            raw["exit_direction"]=direction;result=self.check(raw);self.assertTrue(result["valid"],result["diagnostics"]);self.assertIn(expected,[(s["x"],s["y"]) for s in result["preview"]["stairs"]])
        raw.update(player_start={"x":1,"y":1},special_tiles=[],layers=["###########","#.#########","###########","###########","###########","##<########","###########"])
        self.assertFalse(self.check(raw)["valid"])

if __name__=="__main__": unittest.main()
