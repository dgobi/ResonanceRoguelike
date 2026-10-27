"""W5B shared family contracts; all writes are disposable test inputs."""
import base64
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from test_bridge import ROOT, invoke
from test_authoring import data_fixture

ASSET = "roguelike/data/texts/lab/lab_note_primary_b.json"
TARGET = "roguelike/data/texts/lab/w5b_test.json"


def text_fixture(destination):
    root = data_fixture(destination)
    for name in ("Fonts", "ui"):
        shutil.copytree(ROOT / "roguelike/assets" / name, root / "roguelike/assets" / name)
    return root


class TextTests(unittest.TestCase):
    def test_corpus_discovery_eligibility_noop_and_registered_lifecycle(self):
        sys.path.insert(0, str(ROOT/"roguelike"))
        from engine.text_authoring import capability
        rows = [r for r in invoke("describe")["result"]["assets"] if r.get("family_id") == "text"]
        expected = []
        for p in sorted((ROOT/"roguelike/data/texts").rglob("*.json")):
            if p.name == "text_item_map.json": continue
            raw=json.loads(p.read_bytes()); path=p.relative_to(ROOT).as_posix()
            expected.append((path, capability(raw,path)["editable"]))
        self.assertEqual([(r["path"],r["editable"]) for r in rows],expected)
        self.assertGreaterEqual(sum(r["editable"] for r in rows),51)
        original=(ROOT/ASSET).read_bytes()
        opened=invoke("inspect",asset=ASSET)["result"]
        self.assertEqual(opened["raw"].encode(),original);self.assertTrue(opened["editable"])
        self.assertEqual(opened["family"]["descriptor"]["policy"]["operations"],["variant"])
        self.assertIn("ordered-records",json.dumps(opened["family"]["descriptor"]))
        candidate=copy.deepcopy(json.loads(original));candidate["id"]="w5b_test"
        candidate["condition"]="weathered";candidate["metadata"]={"nested":[None,True]}
        draft=json.dumps(candidate,ensure_ascii=False,indent=2).replace("\n","\r\n")+"\r\n"
        result=invoke("preview_draft",asset=TARGET,source_asset=ASSET,draft=draft)["result"]
        self.assertTrue(result["valid"],result["diagnostics"]);self.assertTrue(result["semantic_verified"])
        self.assertEqual(result["draft_sha256"],hashlib.sha256(draft.encode()).hexdigest())
        self.assertIsNone(result["family_preview"]);self.assertFalse((ROOT/TARGET).exists())
        self.assertEqual((ROOT/ASSET).read_bytes(),original)

    def test_shape_types_markers_metadata_and_candidate_capability(self):
        sys.path.insert(0,str(ROOT/"roguelike"))
        from engine.text_authoring import validate_definition
        base=json.loads((ROOT/ASSET).read_bytes())
        def check(raw):
            inventory={raw.get("id",""):[dict(path=ASSET,pointer="",definition=raw)]} if isinstance(raw,dict) else {}
            return validate_definition(raw,SimpleNamespace(texts={base["id"]:raw}),ASSET,inventory)
        cases=[[],{},dict(base,id=""),dict(base,title=None),dict(base,condition=1),dict(base,pages=[]),dict(base,pages={}),
               dict(base,pages=["body"]),dict(base,pages=[{}]),dict(base,pages=[{"text":None}]),
               dict(base,pages=[{"text":"ok","trailing":None}]),dict(base,pages=[{"text":"ok","damaged":0}]),
               dict(base,deep_tongue=True),dict(base,teach_words=[]),dict(base,render_mode="alphabet"),
               dict(base,pages=[{"text":"ok","deep_tongue":True}]),dict(base,pages=[{"text":"ok","teach_words":{}}]),
               dict(base,pages=[{"text":"ok","render_mode":"alphabet"}])]
        for raw in cases: self.assertTrue(check(raw),raw)
        for condition in ("worn","pristine","damaged","fragmentary","stained","weathered","custom preserved"):
            raw=dict(base,condition=condition,metadata={"unknown":[None,True]},pages=[dict(text='æ "quoted" \\ path\n\n[DAMAGED] [REDACTED]',metadata={"nested":[1,2]})])
            self.assertEqual(check(raw),[])
            raw["pages"][0]["trailing"]=False;self.assertEqual(check(raw),[])

    def test_original_entitlement_duplicates_reserved_basename_and_malformed_contract(self):
        with tempfile.TemporaryDirectory(prefix="w5b-source-") as directory:
            root=data_fixture(directory);raw=json.loads((root/ASSET).read_bytes())
            advanced=dict(raw,teach_words=[]);(root/ASSET).write_text(json.dumps(advanced),encoding="utf-8")
            candidate=dict(raw,id="w5b_test")
            result=invoke("preview_draft",root=root,asset=TARGET,source_asset=ASSET,draft=json.dumps(candidate))["result"]
            self.assertFalse(result["valid"]);self.assertIn("SOURCE_ENTITLEMENT",[d["code"] for d in result["diagnostics"]])
            (root/ASSET).write_text(json.dumps(raw),encoding="utf-8")
            duplicate=root/"roguelike/data/texts/duplicate.json";duplicate.write_text(json.dumps(raw),encoding="utf-8")
            self.assertFalse(invoke("inspect",root=root,asset=ASSET)["result"]["editable"])
            duplicate.unlink()
            # The loader excludes the exact lowercase name only. A differently
            # cased, loaded filename must still participate in ID collision checks.
            duplicate=root/"roguelike/data/texts/lab/TEXT_ITEM_MAP.json";duplicate.write_text(json.dumps(raw),encoding="utf-8")
            self.assertFalse(invoke("inspect",root=root,asset=ASSET)["result"]["editable"])
            duplicate.unlink()
            for malformed in ({},dict(raw,title=None),[None]):
                (root/ASSET).write_text(json.dumps(malformed),encoding="utf-8")
                response=invoke("inspect",root=root,asset=ASSET)
                self.assertTrue(response["ok"],(malformed,response))
                inspected=response["result"]
                self.assertFalse(inspected["editable"]);self.assertFalse(inspected["valid"])
                self.assertEqual(inspected["raw"],(root/ASSET).read_text())
                context=inspected["family"]["context"]
                if context: self.assertLess(len(json.dumps(context)),15000)
            (root/ASSET).write_text(json.dumps(raw),encoding="utf-8")
            for dest in ("roguelike/data/texts/text_item_map.json","roguelike/data/texts/lab/text_item_map.json"):
                result=invoke("preview_draft",root=root,asset=dest,source_asset=ASSET,draft=json.dumps(dict(raw,id="text_item_map")))["result"]
                self.assertFalse(result["valid"]);self.assertIn("TEXT_CAPABILITY",[d["code"] for d in result["diagnostics"]])
            for draft in ('{"id":','{"id":"x","id":"y","pages":[]}', '[]'):
                result=invoke("preview_draft",root=root,asset=TARGET,source_asset=ASSET,draft=draft)["result"]
                self.assertFalse(result["valid"]);self.assertEqual(result["draft_sha256"],hashlib.sha256(draft.encode()).hexdigest())
            module=root/"roguelike/engine/text_authoring.py"
            module.write_bytes(module.read_bytes()+b'\nSCHEMA["properties"]["pages"]["x-control"]="future"\n')
            opened=invoke("inspect",root=root,asset=ASSET)["result"]
            self.assertFalse(opened["editable"]);self.assertEqual(opened["raw"],(root/ASSET).read_text())

    def test_real_reader_multiple_pages_overflow_markers_and_dependency_identity(self):
        with tempfile.TemporaryDirectory(prefix="w5b-reader-") as directory:
            root=text_fixture(directory)
            raw=json.loads((root/ASSET).read_bytes());raw["id"]="w5b_test"
            raw["pages"]=[dict(text="First [DAMAGED] [REDACTED]",trailing=True),dict(text="\n".join(f"Reachable row {i} — æ" for i in range(100)))]
            draft=json.dumps(raw,ensure_ascii=False)
            def frame(page,scroll):
                r=invoke("preview_draft",root=root,asset=TARGET,source_asset=ASSET,draft=draft,preview_inputs=dict(page=page,scroll=scroll))
                self.assertTrue(r["ok"],r);self.assertTrue(r["result"]["valid"],r["result"]["diagnostics"])
                p=r["result"]["family_preview"];self.assertEqual(p["draft_sha256"],hashlib.sha256(draft.encode()).hexdigest())
                image=base64.b64decode(p["image"].split(",")[1]);self.assertTrue(image.startswith(b"\x89PNG"));self.assertEqual(hashlib.sha256(image).hexdigest(),p["image_sha256"])
                return p
            first=frame(0,0);self.assertEqual(first["marker_types"],["damaged","redacted"])
            second=frame(1,0);self.assertGreater(second["max_scroll"],0)
            seen=set(second["visible_rows"])
            for offset in range(second["viewport_height"],second["max_scroll"]+second["viewport_height"],second["viewport_height"]):
                seen.update(frame(1,offset)["visible_rows"])
            self.assertEqual(seen,set(range(second["total_rows"])))
            font=root/"roguelike/assets/ui/weathered_temple.png";font.write_bytes(font.read_bytes()+b"\0")
            after=frame(0,0);self.assertNotEqual(first["source"]["resources_sha256"],after["source"]["resources_sha256"])
            self.assertEqual(first["source"]["catalog_sha256"],after["source"]["catalog_sha256"])
            failed=invoke("preview_draft",root=root,asset=TARGET,source_asset=ASSET,draft=draft,preview_inputs=dict(page=999,scroll=0))
            self.assertFalse(failed["ok"]);self.assertFalse((root/TARGET).exists())
