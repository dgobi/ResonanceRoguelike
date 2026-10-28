"""W2 exact unsaved drafts through the real worker/process/production boundary."""
import copy
import hashlib
import json
import tempfile
import unittest
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

ASSET="roguelike/data/buildings/commercial/apothecary_a.json"

class VisualTests(unittest.TestCase):
    def test_live_catalog_and_clean_noop_preview(self):
        path=ROOT/ASSET; before=path.read_bytes(); stat=path.stat()
        catalog=invoke("inspect",asset=ASSET)["result"]["catalog"]
        self.assertTrue(catalog["decor"]["crate"]["container"])
        self.assertIn("dried_herbs",catalog["decor"]);self.assertIn("storage_tools",catalog["loot_pools"])
        r=invoke("preview_draft",asset=ASSET,draft=before.decode())["result"]
        self.assertTrue(r["valid"],r["diagnostics"])
        self.assertEqual(r["draft_sha256"],hashlib.sha256(before).hexdigest())
        self.assertEqual(r["preview"]["draft_sha256"],r["draft_sha256"])
        self.assertTrue(r["preview"]["access_verified"])
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual((path.stat().st_mtime_ns,path.stat().st_ctime_ns),(stat.st_mtime_ns,stat.st_ctime_ns))

    def test_unsaved_three_layer_variant_realized_without_live_write(self):
        raw=json.loads((ROOT/ASSET).read_bytes()); raw["id"]="apothecary_w2_furnished"
        raw["layers"][3]="#.www.....#";raw["decor_layer"][2][3]="dried_herbs"
        raw["special_tiles"][0].update(x=2,decor_id="crate",loot_pools=["workshop_b_fuel"])
        raw["placement"]["targets"][2]["x"]=2
        raw["unknown_metadata"]={"nested":[[None,"keep"],[True,3]]}
        draft=json.dumps(raw,indent=2)+"\n";dest=ASSET.replace("apothecary_a","apothecary_w2_furnished")
        r=invoke("preview_draft",asset=dest,draft=draft,seed=20261023)["result"]
        self.assertTrue(r["valid"],r["diagnostics"])
        p=r["preview"];ox,oy=p["origin"]
        self.assertEqual(p["terrain"][oy+3][ox+3],"worn_stone")
        self.assertIn({"x":ox+3,"y":oy+2,"id":"dried_herbs","blocking":False},p["decor"])
        c=next(c for c in p["containers"] if (c["x"],c["y"])==(ox+2,oy+1))
        self.assertEqual(c["decor_id"],"crate");self.assertEqual([i["item_id"] for i in c["items"]],["wood_bundle"])
        self.assertFalse((ROOT/dest).exists());self.assertTrue(p["access_verified"])

    def test_real_references_blocked_anchor_collision_access_and_unsupported(self):
        raw=json.loads((ROOT/ASSET).read_bytes())
        cases=[]
        r=copy.deepcopy(raw);r["special_tiles"][0]["loot_pools"]=["missing_pool"];cases.append((r,"REFERENCE"))
        r=copy.deepcopy(raw);r["special_tiles"][0].update(x=0,y=0);cases.append((r,"PRODUCTION_PLACEMENT"))
        r=copy.deepcopy(raw);r["special_tiles"][0].update(x=9,y=3);cases.append((r,"PRODUCTION_PLACEMENT"))
        # Seal the complete row inside the legal entrance; profile syntax is
        # still valid, but actual populated access to required targets fails.
        r=copy.deepcopy(raw);r["layers"][6]="###########";cases.append((r,"ACCESS"))
        r=copy.deepcopy(raw);r["special_tiles"].append({"type":"body","x":3,"y":3});cases.append((r,"UNSUPPORTED_PREVIEW_SPECIAL"))
        for candidate,code in cases:
            result=invoke("preview_draft",asset=ASSET,draft=json.dumps(candidate))
            self.assertTrue(result["ok"],result);v=result["result"]
            self.assertFalse(v["valid"],code)
            self.assertIn(code,[d["code"] for d in v["diagnostics"]],v["diagnostics"])
            if code=="ACCESS":self.assertTrue(any(d.get("source_xy") for d in v["diagnostics"] if d["code"]==code))
            if code=="PRODUCTION_PLACEMENT":self.assertTrue(any(d.get("source_xy") is not None for d in v["diagnostics"] if d["code"]==code))

    def test_rectangular_grid_trailing_spaces_and_nested_decor_rejection(self):
        raw={"id":"w2_rectangular","width":60,"height":16,"legend":{".":"floor"," ":None},"layers":["."*59+" " for _ in range(16)],"decor_layer":[[None]*60 for _ in range(16)],"special_tiles":[{"x":58,"y":15,"type":"container","decor_id":"crate","loot_pools":["workshop_b_fuel"]}],"unknown":[[1,None],[True,"keep"]]}
        raw["decor_layer"][14][58]="dried_herbs"
        dest=ASSET.replace("apothecary_a","w2_rectangular")
        draft="\ufeff"+json.dumps(raw,indent=2).replace("\n","\r\n")+"\r\n"
        r=invoke("preview_draft",asset=dest,draft=draft)["result"]
        self.assertTrue(r["valid"],r["diagnostics"]);p=r["preview"];self.assertEqual(p["origin"],[10,13])
        self.assertEqual(p["terrain"][28][68],"floor");self.assertEqual(p["terrain"][28][69],"grass")
        self.assertFalse(p["access_verified"]);self.assertIn("access unverified",p["context"])
        raw["decor_layer"][0][0]=["dried_herbs"]
        bad=invoke("preview_draft",asset=dest,draft=json.dumps(raw))["result"]
        self.assertFalse(bad["valid"]);self.assertIsNone(bad["preview"])

    def test_preview_denies_other_routes_paths_and_duplicate_identity(self):
        readonly=invoke("preview_draft",asset="roguelike/data/layouts/starting_lab.json",draft="{}")
        self.assertTrue(readonly["ok"]);self.assertFalse(readonly["result"]["valid"])
        for asset in ("roguelike/saves/x.json","../x.json","roguelike/engine/data_loader.py"):
            self.assertFalse(invoke("preview_draft",asset=asset,draft="{}")["ok"])
        with tempfile.TemporaryDirectory(prefix="w2-data-") as directory:
            root=data_fixture(directory);before=(root/ASSET).read_bytes()
            result=invoke("preview_draft",root=root,asset=ASSET.replace("apothecary_a","new_variant"),draft=before.decode())["result"]
            self.assertFalse(result["valid"]);self.assertIn("DUPLICATE_ID",[d["code"] for d in result["diagnostics"]])
            self.assertEqual((root/ASSET).read_bytes(),before)

if __name__=="__main__":unittest.main(verbosity=2)
