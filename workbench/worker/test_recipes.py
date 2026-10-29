"""Current recipe source, requirement and production exchange contract tests."""
import copy
import hashlib
import json
import tempfile
import unittest
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

RECIPE = "roguelike/data/recipes/bile_coating.json"


class RecipeTests(unittest.TestCase):
    def test_source_classes_noop_relationships_and_production_ambient_registry(self):
        rows = [r for r in invoke("describe")["result"]["assets"] if r["route"] == "recipe_definition"]
        self.assertEqual(len(rows), 18)
        for name, kind, writable in (("bile_coating", "Immediate item output", True), ("cook_meat", "Passive processing", True),
                                     ("campfire", "World placement", False), ("coldbell_extract_deprecated", "Deprecated / legacy", False)):
            path = f"roguelike/data/recipes/{name}.json"; before = (ROOT/path).read_bytes()
            result = invoke("inspect", asset=path)["result"]
            self.assertEqual(result["raw"].encode(),before); self.assertEqual((ROOT/path).read_bytes(),before)
            record = result["family"]["context"]["records"][0]
            self.assertEqual(record["capability"]["execution_class"],kind); self.assertEqual(result["editable"],writable)
            if writable:
                self.assertIn("burning", result["family"]["context"]["ambient_tags"])
                self.assertNotIn("burning", result["family"]["context"]["keywords"])
                self.assertIsNone(record["probe"])
        item = invoke("inspect",asset="roguelike/data/items/components/clay_pot.json")["result"]
        relation=next(r for r in item["family"]["context"]["records"][0]["recipes"] if r["id"]=="bile_coating")
        self.assertEqual(relation["fields"],["tools[0]"]); self.assertFalse(relation["produces"])

    def test_exact_variant_real_instance_selection_output_and_retained_tools(self):
        raw=json.loads((ROOT/RECIPE).read_bytes()); raw["id"]="bile_coating_w3c_test"
        raw["components"][0]["quantity"]=2
        raw["metadata"]={"keep":[[True,None],"literal text"]}
        target=RECIPE.replace("bile_coating.json",raw["id"]+".json")
        draft=json.dumps(raw,indent=2)+"\r\n"
        result=invoke("preview_draft",asset=target,source_asset=RECIPE,draft=draft)["result"]
        self.assertTrue(result["valid"],result["diagnostics"])
        probe=result["family"]["context"]["records"][0]["probe"]
        self.assertEqual(probe["source_sha256"],hashlib.sha256(draft.encode()).hexdigest())
        yes,no_items,no_ambient,_=probe["cases"]
        self.assertTrue(yes["eligible"]); self.assertTrue(yes["committed"])
        self.assertEqual(len(set(yes["selected"])),4); self.assertEqual(len(yes["materials"]),3)
        self.assertEqual(yes["after"],yes["retained_tools"]+["output-1"])
        self.assertEqual(yes["output"]["item_id"],"bile_coating"); self.assertTrue(yes["output"]["in_inventory"])
        self.assertNotIn("bile_coating", [r["item_id"] for r in yes["inventory"]])
        self.assertTrue(all(len(r["source_sha256"]) == 64 for r in yes["inventory"]))
        self.assertFalse(no_items["eligible"]); self.assertIsNone(no_items["output"])
        self.assertTrue(all(r["ambient"] for r in no_ambient["missing"]))
        self.assertEqual(no_ambient["before"],no_ambient["after"])
        self.assertFalse((ROOT/target).exists())

    def test_invalid_fields_unknown_references_and_excluded_mechanics(self):
        raw=json.loads((ROOT/RECIPE).read_bytes())
        cases=[]
        for field,value,code in (("result_item","no_such_item","OUTPUT_REFERENCE"), ("known",1,"RECIPE_FIELD"),
                                 ("passive_processing",True,"RECIPE_CLASS"), ("_deprecated",False,"UNSUPPORTED_RECIPE"),
                                 ("places_in_world",False,"UNSUPPORTED_RECIPE"), ("result_tile","campfire_unlit","UNSUPPORTED_RECIPE"),
                                 ("requires_single_item",[],"CONJUNCTION_SHAPE"), ("processing_turns",1,"UNSUPPORTED_RECIPE")):
            cases.append(({**raw,field:value},code))
        for field,values,code in (("quantity",[0,-1,True,1.5,33],"REQUIREMENT_QUANTITY"),
                                  ("min_tier",[-1,True,1.2,2**53],"REQUIREMENT_TIER"), ("tag",["missing",[]],"KEYWORD_REFERENCE")):
            for value in values:
                candidate=copy.deepcopy(raw);candidate["components"][0][field]=value;cases.append((candidate,code))
        for candidate,code in cases:
            result=invoke("preview_draft",asset=RECIPE,draft=json.dumps(candidate))["result"]
            self.assertFalse(result["valid"]); self.assertIsNone(result["family"]["context"])
            self.assertIn(code,[d["code"] for d in result["diagnostics"]],result)
        for text in ('{"id":','{"id":"x","id":"y"}', '\ufeff'+json.dumps(raw), json.dumps(raw).replace('"quantity": 1','"quantity": NaN',1)):
            self.assertFalse(invoke("preview_draft",asset=RECIPE,draft=text)["result"]["valid"])

    def test_recursive_duplicates_arrays_and_changed_item_dependencies(self):
        with tempfile.TemporaryDirectory(prefix="w3c-recipes-") as folder:
            root=data_fixture(folder); raw=json.loads((root/RECIPE).read_bytes())
            nested=root/"roguelike/data/recipes/nested";nested.mkdir()
            duplicate=nested/"duplicate.json";duplicate.write_text(json.dumps({**raw,"id":"BILE_COATING"}))
            result=invoke("inspect",root=root,asset=RECIPE)["result"]
            self.assertFalse(result["editable"])
            self.assertIn("nested/duplicate.json",next(d for d in result["diagnostics"] if d["code"]=="DUPLICATE_RECIPE")["message"])
            duplicate.write_text(json.dumps([{**raw,"id":"array_recipe"}]))
            result=invoke("inspect",root=root,asset="roguelike/data/recipes/nested/duplicate.json")["result"]
            self.assertFalse(result["editable"]);self.assertEqual(result["family"]["context"]["records"][0]["pointer"],"/0")
            output=next((root/"roguelike/data/items").rglob("bile_coating.json"))
            definition=json.loads(output.read_bytes()); output.write_text(json.dumps({**definition,"id":"removed_output"}))
            result=invoke("preview_draft",root=root,asset=RECIPE,draft=json.dumps(raw))["result"]
            self.assertFalse(result["valid"]);self.assertIn("OUTPUT_REFERENCE",[d["code"] for d in result["diagnostics"]])

if __name__ == "__main__": unittest.main()
