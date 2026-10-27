"""W5A registered routes: real semantic checks remain the publication authority."""
import hashlib
import json
import tempfile
import unittest
import copy
import os
import sys
from types import SimpleNamespace
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

ITEM = "roguelike/data/items/components/wood_bundle.json"
RECIPE = "roguelike/data/recipes/bile_coating.json"


class ContentContractTests(unittest.TestCase):
    def test_consumed_on_use_descriptor_actual_factory_allocation_and_exchange(self):
        sys.path.insert(0, str(ROOT/"roguelike"))
        os.environ.update(SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy",PYGAME_HIDE_SUPPORT_PROMPT="1")
        import config
        config.DEBUG_MODE=False
        from components.inventory import Inventory
        from components.equipment import Equipment
        from engine.item_factory import ItemFactory
        from engine.crafting import material_candidate, plan_craft, commit_craft
        original=(ROOT/ITEM).read_bytes(); base=json.loads(original)
        keywords=json.loads((ROOT/"roguelike/data/keywords.json").read_bytes())
        requirement={"tag":"fuel","min_tier":1,"quantity":1}
        for value in ("absent",True,False):
            raw=copy.deepcopy(base)
            if value != "absent": raw["consumed_on_use"]=value
            effective=value is not False
            response=invoke("preview_draft",asset=ITEM,source_asset=ITEM,draft=json.dumps(raw))["result"]
            self.assertTrue(response["valid"],response["diagnostics"])
            field=response["family"]["descriptor"]["schema"]["properties"]["consumed_on_use"]
            self.assertEqual(field["type"],"boolean");self.assertIs(field["default"],True)
            self.assertEqual(field["title"],"Eligible for automatic ingredient selection")
            self.assertIs(response["family"]["context"]["records"][0]["factory"]["instance"]["consumed_on_use"],effective)
            data=SimpleNamespace(items={"wood_bundle":raw},keywords=keywords)
            factory=ItemFactory(data)
            for role,explicit in (("components",False),("components",True),("tools",False)):
                inv=Inventory(capacity=1000); item=factory.create("wood_bundle");self.assertTrue(inv.add(item))
                self.assertIs(item.consumed_on_use,effective)
                self.assertEqual(bool(material_candidate(item)),effective)
                self.assertTrue(material_candidate(item,"wood_bundle"))
                recipe={role:[requirement],"result_item":"wood_bundle"}
                selected,missing=plan_craft(recipe,inv,keywords,[],{0:"wood_bundle"} if explicit else None)
                eligible=effective or explicit or role=="tools"
                self.assertEqual(not missing,eligible,(value,role,explicit,missing))
                if not eligible:
                    self.assertTrue(inv.contains(item));continue
                self.assertEqual(list(selected),[item])
                self.assertEqual(selected.materials,[item] if role=="components" else [])
                output=factory.create("wood_bundle")
                engine=SimpleNamespace(player=SimpleNamespace(inventory=inv,equipment=Equipment(),light_source=None),data=data)
                self.assertTrue(commit_craft(engine,recipe,selected,[],[output]))
                self.assertEqual(inv.contains(item),role=="tools")
                self.assertTrue(inv.contains(output))
        self.assertEqual((ROOT/ITEM).read_bytes(),original)

    def test_both_routes_report_common_identity_shape_and_semantic_evidence(self):
        for family, path in (("item", ITEM), ("recipe", RECIPE)):
            opened = invoke("inspect", asset=path)["result"]
            descriptor = opened["family"]
            self.assertEqual(descriptor["id"], family)
            self.assertTrue(descriptor["compatible"], descriptor["problems"])
            self.assertEqual(descriptor["descriptor"]["schema"]["$schema"], "https://json-schema.org/draft/2020-12/schema")
            result = invoke("preview_draft", asset=path, source_asset=path, draft=opened["raw"])["result"]
            self.assertTrue(result["valid"], result["diagnostics"])
            self.assertTrue(result["semantic_verified"])
            self.assertEqual(result["family"]["descriptor_sha256"], descriptor["descriptor_sha256"])
            self.assertEqual(result["source_sha256"], hashlib.sha256(opened["raw"].encode()).hexdigest())
            self.assertEqual(result["draft_sha256"], result["source_sha256"])

    def test_original_readonly_shape_cannot_be_promoted_or_cross_family_rebound(self):
        for source, candidate in (("roguelike/data/items/tools/tallow_torch.json", ITEM), ("roguelike/data/recipes/cook_meat.json", RECIPE)):
            raw = json.loads((ROOT/candidate).read_bytes()); raw["id"] = "w5a_promoted"
            target = candidate.rsplit("/", 1)[0] + "/w5a_promoted.json"
            result = invoke("preview_draft", asset=target, source_asset=source, draft=json.dumps(raw))
            self.assertTrue(result["ok"], result)
            self.assertFalse(result["result"]["valid"])
            self.assertIn("SOURCE_ENTITLEMENT", [d["code"] for d in result["result"]["diagnostics"]])
        cross = invoke("preview_draft", asset=ITEM, source_asset=RECIPE, draft=(ROOT/ITEM).read_text())
        self.assertEqual(cross["error"]["code"], "SOURCE_ENTITLEMENT")
        forged = invoke("preview_draft", asset=ITEM, draft=(ROOT/ITEM).read_text(), family={"policy":{"operations":["edit"]}})
        self.assertEqual(forged["error"]["code"], "MALFORMED_REQUEST")

    def test_unsupported_schema_stays_inspectable_but_cannot_validate(self):
        with tempfile.TemporaryDirectory(prefix="w5a-contract-") as folder:
            root = data_fixture(folder)
            module = root/"roguelike/engine/item_authoring.py"
            module.write_bytes(module.read_bytes()+b'\nSCHEMA["allOf"] = []\n')
            opened = invoke("inspect", root=root, asset=ITEM)["result"]
            self.assertEqual(opened["raw"].encode(), (root/ITEM).read_bytes())
            self.assertFalse(opened["editable"])
            self.assertIn("unsupported schema keyword allOf", " ".join(opened["family"]["problems"]))
            checked = invoke("preview_draft", root=root, asset=ITEM, source_asset=ITEM, draft=opened["raw"])["result"]
            self.assertFalse(checked["valid"])
            self.assertIn("UNSUPPORTED_CAPABILITY", [d["code"] for d in checked["diagnostics"]])

    def test_invalid_boolean_source_is_retained_and_actual_validator_refuses(self):
        original=(ROOT/ITEM).read_text(encoding="utf-8")
        raw=json.loads(original)
        for value in (None, "false", 0, [], {}):
            draft=json.dumps({**raw,"consumed_on_use":value})
            checked=invoke("preview_draft",asset=ITEM,source_asset=ITEM,draft=draft)["result"]
            self.assertFalse(checked["valid"])
            self.assertEqual(checked["draft_sha256"],hashlib.sha256(draft.encode()).hexdigest())
            self.assertTrue(any(d["field"]=="consumed_on_use" for d in checked["diagnostics"]))
        self.assertEqual((ROOT/ITEM).read_text(encoding="utf-8"),original)
