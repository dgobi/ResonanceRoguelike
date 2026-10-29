"""Harvest authority, saved dependency construction and native effective rules."""
import copy
import json
import unittest
import tempfile
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

SOURCE="roguelike/data/entities/creatures/sewer_thing.json"


class HarvestAuthoring(unittest.TestCase):
    def draft(self,raw,source=SOURCE,root=ROOT,target=None):
        return invoke("preview_draft",root=root,asset=target or source,source_asset=source,draft=json.dumps(raw))["result"]
    def test_capability_inventory_all_sources_and_reference_only_items(self):
        result=invoke("describe")["result"]
        import sys
        sys.path.insert(0,str(ROOT/"roguelike"))
        from engine.creature_authoring import capability
        rows=[]
        for path in sorted((ROOT/"roguelike/data/entities/creatures").glob("*.json")):
            raw=json.loads(path.read_bytes());cap=capability(raw,path.relative_to(ROOT).as_posix())
            rows.append(dict(id=raw["id"],harvest=cap["harvest_editable"],variant=cap["duplicable"]))
        self.assertEqual(sum(r["harvest"] for r in rows),11)
        self.assertEqual(sum(r["variant"] for r in rows),6)
        self.assertFalse(next(r["harvest"] for r in rows if r["id"]=="bog_wraith"))
        self.assertFalse(next(r["harvest"] for r in rows if r["id"]=="vine_network"))
        opened=invoke("inspect",asset=SOURCE)["result"]
        options=opened["family"]["references"]["harvest_items"]
        self.assertIn("tallow_torch",[row["id"] for row in options])
        self.assertTrue(all("roguelike/data/items/" in row["label"] for row in options))
    def test_profile_add_remove_variants_and_special_same_id(self):
        for id in ("sewer_thing","hollow_knight"):
            source=SOURCE.replace("sewer_thing",id);raw=json.loads((ROOT/source).read_bytes())
            self.assertNotIn("butcher_yield",raw)
            raw["butcher_yield"]=dict(decay_turns=None,tiers=[dict(yields=[dict(item_id="tallow_torch")])])
            self.assertTrue(self.draft(raw,source)["valid"])
            raw["id"]=id+"_w5n";target=source.replace(id+".json",raw["id"]+".json")
            self.assertEqual(self.draft(raw,source,target=target)["valid"],id=="sewer_thing")
        source=SOURCE.replace("sewer_thing","hollow_revenant");raw=json.loads((ROOT/source).read_bytes());raw.pop("butcher_yield")
        self.assertTrue(self.draft(raw,source)["valid"])
    def test_raw_original_ephemeral_shape_and_metadata_bypasses(self):
        source=SOURCE.replace("sewer_thing","bog_wraith");raw=json.loads((ROOT/source).read_bytes());raw.pop("ephemeral")
        raw["butcher_yield"]=dict(tiers=[])
        result=self.draft(raw,source);self.assertFalse(result["valid"]);self.assertIn("READ_ONLY_FIELD",[d["code"] for d in result["diagnostics"]])
        with tempfile.TemporaryDirectory(prefix="w5n-entitlement-") as temp:
            root=data_fixture(temp);raw=json.loads((root/SOURCE).read_bytes());raw["butcher_yield"]={"tiers":None};(root/SOURCE).write_text(json.dumps(raw))
            raw["butcher_yield"]={};self.assertFalse(self.draft(raw,root=root)["valid"])
            raw["butcher_yield"]={"meta":{"x":1},"tiers":[{"meta":"tier","yields":[{"item_id":"raw_meat_common","meta":"row"}]}]};(root/SOURCE).write_text(json.dumps(raw))
            changed=copy.deepcopy(raw);changed["butcher_yield"]["tiers"][0]["yields"][0]["quantity_min"]=1
            self.assertTrue(self.draft(changed,root=root)["valid"])
            changed["butcher_yield"]["tiers"][0]["yields"][0]["meta"]="changed"
            result=self.draft(changed,root=root);self.assertFalse(result["valid"]);self.assertIn("HARVEST_METADATA",[d["code"] for d in result["diagnostics"]])
    def test_effective_numeric_null_empty_and_resource_limits(self):
        import sys
        sys.path.insert(0,str(ROOT/"roguelike"))
        from engine.harvesting import profile_errors,select_tier
        for profile in ({},{"decay_turns":None},{"decay_turns":2**53-1},{"tiers":[]},{"tiers":[{}]},{"tiers":[{"yields":[]}]},{"tiers":[{"min_cutting_tier":0,"yields":[{"item_id":"x"}]}]}):
            self.assertFalse(profile_errors({"butcher_yield":profile}),profile)
        for profile in (None,[],{"decay_turns":True},{"decay_turns":2**53},{"decay_turns":1.5},{"tiers":None},{"tiers":[None]},{"tiers":[{"min_cutting_tier":33}]},{"tiers":[{"min_cutting_tier":None}]},{"tiers":[{"yields":None}]},{"tiers":[{"yields":[{"item_id":"x","quantity_min":2}]}]},{"tiers":[{"yields":[{"item_id":"x","quantity_min":True}]}]},{"tiers":[{}]*65},{"tiers":[{"yields":[{"item_id":"x","quantity_max":0}]*65}]},{"tiers":[{"yields":[{"item_id":"x","quantity_max":32}]*3}]}):
            self.assertTrue(profile_errors({"butcher_yield":profile}),profile)
        first={"min_cutting_tier":2,"yields":[{"item_id":"x"},{"item_id":"x"}]};second={"min_cutting_tier":2}
        self.assertIs(select_tier({"tiers":[first,second]},2),first)
        self.assertIs(select_tier({"tiers":[first,second]},0,True),first)
    def test_missing_case_collision_and_factory_invalid_saved_outputs(self):
        with tempfile.TemporaryDirectory(prefix="w5n-references-") as temp:
            root=data_fixture(temp);raw=json.loads((root/SOURCE).read_bytes())
            raw["butcher_yield"]=dict(tiers=[dict(yields=[dict(item_id="raw_meat_common")])])
            self.assertTrue(self.draft(raw,root=root)["valid"])
            path=root/"roguelike/data/items/components/w5n_collision.json"
            path.write_text(json.dumps(dict(id="RAW_MEAT_COMMON",name="collision")))
            result=self.draft(raw,root=root);self.assertFalse(result["valid"]);self.assertTrue(any("w5n_collision.json" in d["message"] for d in result["diagnostics"]))
            path.unlink();item=root/"roguelike/data/items/butchery/raw_meat_common.json";value=json.loads(item.read_bytes());value["weight"]=-1;item.write_text(json.dumps(value))
            self.assertFalse(self.draft(raw,root=root)["valid"])
            raw["butcher_yield"]["tiers"][0]["yields"][0]["item_id"]="missing"
            self.assertFalse(self.draft(raw,root=root)["valid"])


if __name__=="__main__":unittest.main()
