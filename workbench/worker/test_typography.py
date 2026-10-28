"""W5E contracts, glyph negatives and real bounded production consumers."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import warnings

from test_bridge import ROOT, invoke
from test_texts import text_fixture

sys.path.insert(0, str(ROOT / "roguelike"))
os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
import pygame
import pygame.freetype
from engine.typography import (PROFILE, ROLES, ASCII, TypographyError, defaults, discover_resources,
                               initialize, load_candidate, resource)


def candidate():
    return dict(defaults(), font_ui_large="IMFellEnglish-Regular.ttf", font_ui_normal="IMFellEnglish-Italic.ttf",
                font_callout_damage="FoulisGreek.ttf", metadata={"preserve":[None,True,"λ"]})


class TypographyTests(unittest.TestCase):
    def setUp(self):
        self.previous=Path.cwd();os.chdir(ROOT / "roguelike");pygame.init();pygame.display.set_mode((1,1))

    def tearDown(self):
        pygame.quit();os.chdir(self.previous)

    def test_default_and_absent_assignments_sizes_aliases_and_whole_fallback(self):
        from engine.display_config import DisplayConfig
        shipped=json.loads((ROOT/PROFILE).read_bytes());self.assertEqual(shipped,defaults())
        display=DisplayConfig.from_config();display.init()
        self.assertEqual(len(display.typography["roles"]),13)
        for key,(_,name,size,*_) in ROLES.items():
            expected=pygame.font.Font(str(ROOT/"roguelike/assets/Fonts"/name),size)
            self.assertEqual(pygame.image.tostring(getattr(display,key).render("Default 0123",True,"white"),"RGBA"),
                             pygame.image.tostring(expected.render("Default 0123",True,"white"),"RGBA"))
        self.assertIs(display.CALLOUT_FONTS["small"],display.font_callout_damage)
        self.assertIs(display.CALLOUT_FONTS["tiny"],display.font_callout_creature)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);shutil.copytree(ROOT/"roguelike/assets/Fonts",root/"roguelike/assets/Fonts")
            absent=initialize(root);self.assertFalse((root/PROFILE).exists());self.assertFalse(absent["fallback"])
            self.assertEqual([r["requested"] for r in absent["roles"]],[r[1] for r in ROLES.values()])
            (root/PROFILE).parent.mkdir(parents=True)
            (root/"roguelike/assets/Fonts/corrupt.ttf").write_bytes(b"not a font")
            for raw in ('{invalid',json.dumps(dict(candidate(),font_ui_small="missing.ttf")),
                        json.dumps(dict(candidate(),font_ui_large="corrupt.ttf")),json.dumps(dict(defaults(),version=2))):
                (root/PROFILE).write_text(raw)
                with warnings.catch_warnings(record=True) as caught: loaded=initialize(root)
                self.assertTrue(caught);self.assertTrue(loaded["fallback"]);self.assertEqual((root/PROFILE).read_text(),raw)
                self.assertEqual([Path(r["resolved"]).name for r in loaded["roles"]],[r[1] for r in ROLES.values()])
            (root/"roguelike/assets/Fonts/Junicode.ttf").unlink()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with self.assertRaisesRegex(RuntimeError,"Junicode.ttf"):initialize(root)

    def test_packaged_freetype_real_absent_glyphs_and_role_specific_gate(self):
        rows=discover_resources(ROOT);self.assertEqual(len(rows),7)
        for row in rows:
            probe=pygame.freetype.Font(str(ROOT/"roguelike/assets/Fonts"/row["id"]),size=18,ucs4=True)
            self.assertTrue(all(m is not None for m in probe.get_metrics(ASCII)))
        negatives=[("IMFellEnglish-Regular.ttf","font_ui_tiny","↑"),("Junicode-Bold.ttf","font_ui_small","≥")]
        for face,role,char in negatives:
            path=str(ROOT/"roguelike/assets/Fonts"/face);probe=pygame.freetype.Font(path,size=18,ucs4=True)
            self.assertIsNone(probe.get_metrics(char)[0])
            # Real SDL negative control: metrics can claim a glyph for a box.
            sdl=pygame.font.Font(path,18)
            self.assertIsNotNone(sdl.metrics(char)[0])
            self.assertEqual(pygame.image.tostring(sdl.render(char,True,"white"),"RGBA"),pygame.image.tostring(sdl.render("\U0010ffff",True,"white"),"RGBA"))
            with self.assertRaises(TypographyError) as error:load_candidate(ROOT,dict(defaults(),**{role:face}))
            self.assertTrue(any(d["field"]==role and char in d["message"] for d in error.exception.diagnostics))
        self.assertFalse(load_candidate(ROOT,candidate())["fallback"])

    def test_resource_bounds_missing_corrupt_escape_and_linked_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/"roguelike/assets/Fonts";folder.mkdir(parents=True)
            (folder/"bad.ttf").write_bytes(b"not a font")
            for name in ("../Junicode.ttf","C:/font.ttf","/font.ttf","sub/font.ttf","bad\\font.ttf","missing.ttf","bad.ttf","x"*129+".ttf"):
                with self.subTest(name=name),self.assertRaises(TypographyError):load_candidate(root,dict(defaults(),font_ui_large=name))
            source=ROOT/"roguelike/assets/Fonts/Junicode.ttf"
            # A directory junction needs no Windows symlink privilege.
            linked=root/"linked"
            if os.name=="nt":
                result=subprocess.run(["cmd","/c","mklink","/J",str(linked),str(source.parent)],capture_output=True,creationflags=0x08000000)
                self.assertEqual(result.returncode,0,result.stderr)
            else:linked.symlink_to(source.parent,target_is_directory=True)
            from engine.typography import no_links
            try:
                with self.assertRaises(ValueError):no_links(linked/"Junicode.ttf")
            finally:
                if os.name=="nt":os.rmdir(linked)
                else:linked.unlink()

    def test_registered_singleton_validation_correction_and_true_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root=text_fixture(directory)
            extra=root/"roguelike/data/display/other.json";extra.write_text(json.dumps(defaults()))
            rows=[r for r in invoke("describe",root=root)["result"]["assets"] if r.get("family_id")=="typography"]
            self.assertEqual([r["path"] for r in rows],[PROFILE]);self.assertTrue(rows[0]["editable"])
            raw=candidate();draft=json.dumps(raw,ensure_ascii=False,indent=2)+"\r\n"
            result=invoke("preview_draft",root=root,asset=PROFILE,source_asset=PROFILE,draft=draft,preview_inputs={})
            self.assertTrue(result["ok"],result);r=result["result"];self.assertTrue(r["valid"],r["diagnostics"])
            self.assertEqual(r["family"]["descriptor"]["policy"]["operations"],["edit"])
            frame=r["family_preview"];self.assertEqual(frame["kind"],"typography-preview");self.assertEqual(len(frame["roles"]),13)
            self.assertEqual(frame["draft_sha256"],hashlib.sha256(draft.encode()).hexdigest())
            for name,size in (("specimen",(960,960)),("reader",(960,640))):
                png=base64.b64decode(frame[name]["image"].split(",")[1]);self.assertTrue(png.startswith(b"\x89PNG"))
                self.assertEqual(hashlib.sha256(png).hexdigest(),frame[name]["image_sha256"]);self.assertEqual((frame[name]["width"],frame[name]["height"]),size)
            self.assertEqual(frame["roles"][0]["requested"],raw["font_ui_large"])
            self.assertEqual(json.loads((root/PROFILE).read_bytes()),defaults())
            for path in ("roguelike/data/display/other.json","roguelike/data/display/nested/typography.json","roguelike/assets/Fonts/font.json"):
                self.assertFalse(invoke("preview_draft",root=root,asset=path,source_asset=PROFILE,draft=draft)["ok"])
            for invalid in (dict(raw,id="other"),dict(raw,version=2),dict(raw,version=True),dict(raw,font_ui_small="Junicode-Bold.ttf")):
                result=invoke("preview_draft",root=root,asset=PROFILE,source_asset=PROFILE,draft=json.dumps(invalid),preview_inputs={})["result"]
                self.assertFalse(result["valid"]);self.assertIsNone(result["family_preview"])
            (root/PROFILE).write_text(json.dumps(dict(defaults(),font_ui_normal="missing.ttf")))
            inspected=invoke("inspect",root=root,asset=PROFILE)["result"];self.assertTrue(inspected["editable"]);self.assertFalse(inspected["valid"])
            fixed=invoke("validate_draft",root=root,asset=PROFILE,draft=draft)["result"];self.assertTrue(fixed["valid"],fixed)
            for source in ('{invalid',json.dumps(dict(defaults(),version=2)),json.dumps(dict(defaults(),font_ui_normal=None))):
                (root/PROFILE).write_text(source);self.assertFalse(invoke("inspect",root=root,asset=PROFILE)["result"]["editable"])

    def test_42_reader_layout_probes_and_corruption_alphabet(self):
        from components.language import Language
        from engine.display_config import DisplayConfig
        from engine.text_reader import TextReader
        from rendering.ui_registry import UIRegistry
        registry=UIRegistry();registry.load()
        engine=SimpleNamespace(player=SimpleNamespace(language=Language()),data=SimpleNamespace(deep_tongue={}),ui_registry=registry)
        for face in discover_resources(ROOT):
            raw=dict(defaults(),font_ui_large=face["id"],font_ui_normal=face["id"],font_deep=face["id"])
            display=DisplayConfig.from_config();display.init(typography_candidate=raw)
            reader=TextReader();reader.init(display)
            self.assertTrue(all(m is not None for m in display.font_coverage["font_ui_normal"].get_metrics(reader._corrupt_pool)))
            for size in ((960,640),(480,320)):
                for length in (20,512,2048):
                    with self.subTest(face=face["id"],size=size,length=length):
                        title=("The unquiet bells and the city "*100)[:length]
                        reader.open_text(dict(id="probe",title=title,pages=[dict(text="Body [DAMAGED] [REDACTED]\n"+"Long ordinary words. "*120,trailing=True)]))
                        screen=pygame.Surface(size);reader.render(screen,engine);seen=set(reader._visible_rows)
                        for _ in range(300):
                            if reader._scroll==reader._max_scroll:break
                            reader.handle_key(pygame.K_PAGEDOWN);reader.render(screen,engine);seen.update(reader._visible_rows)
                        self.assertEqual(seen,set(range(len(reader._layout_rows))))
                        self.assertTrue(screen.get_rect().contains(reader._frame));self.assertTrue(reader._frame.contains(reader._viewport))
                        self.assertLessEqual(reader._viewport.bottom,reader._footer_top)
                        self.assertTrue(all(sum(f["width"] for f in row)<=reader._viewport.width for row in reader._layout_rows))
                        self.assertTrue(all(f["surface"].get_height()<=reader._line_height for row in reader._layout_rows for f in row))

    def test_actual_hud_menu_and_callout_consumers_with_selected_metrics(self):
        from engine.display_config import DisplayConfig
        from engine.message_log import MessageLog
        from engine.ui import UI
        from rendering.perk_screen import PerkScreen
        from rendering.callouts import CalloutSystem
        display=DisplayConfig.from_config();display.init(typography_candidate=candidate())
        screen=pygame.Surface((960,640),pygame.SRCALPHA);ui=UI(display);ui.init();log=MessageLog()
        for i in range(8):log.add(f"Damage {i} × 2 − 1 → {i*2-1}")
        ui.render_messages(screen,pygame.Rect(640,0,320,640),log,2)
        self.assertIs(ui._font_tiny,display.font_ui_tiny);self.assertTrue(screen.get_bounding_rect().width)
        perks=PerkScreen();perks.init(display);self.assertEqual(perks._row_height,display.font_ui_normal.get_linesize()+4)
        perks._flat=[("test",False,"Test")]
        engine=SimpleNamespace(player=SimpleNamespace(perks=None,level=SimpleNamespace(perk_points=2)),data=SimpleNamespace(perks={"test":{"name":"Stone hearing","cost":1}}))
        perks._draw_left(screen,engine,0,0,300,500,24)
        self.assertIs(perks._font_normal,display.font_ui_normal)
        calls=CalloutSystem()
        for i,key in enumerate(display.CALLOUT_FONTS):calls.add("-37" if key=="damage" else "Status",i*2,10,(255,255,255),font_size=key)
        calls.draw(screen,display.CALLOUT_FONTS,24,24,0,0,0,0,pygame.Rect(0,200,640,440));calls.update(0.1)
        self.assertEqual(len(calls._callouts),7)
        artifact=os.environ.get("W5E_ARTIFACT_DIR")
        if artifact:
            path=Path(artifact);path.mkdir(parents=True,exist_ok=True);pygame.image.save(screen,str(path/"hud-menu-callouts.png"))

    def test_saved_profile_and_selected_font_bytes_change_dependency_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=text_fixture(directory)
            opened=invoke("inspect",root=root,asset=PROFILE)["result"]
            (root/PROFILE).write_text(json.dumps(candidate()))
            changed=invoke("inspect",root=root,asset=PROFILE)["result"]
            self.assertNotEqual(opened["source"]["catalog_sha256"],changed["source"]["catalog_sha256"])
            font=root/"roguelike/assets/Fonts/FoulisGreek.ttf";font.write_bytes(font.read_bytes()+b"\0")
            changed_font=invoke("inspect",root=root,asset=PROFILE)["result"]
            self.assertNotEqual(changed["source"]["resources_sha256"],changed_font["source"]["resources_sha256"])
            # A text preview takes the saved profile, never another document draft.
            from test_texts import ASSET,TARGET
            text=json.loads((root/ASSET).read_bytes());text["id"]="w5b_test"
            result=invoke("preview_draft",root=root,asset=TARGET,source_asset=ASSET,draft=json.dumps(text),preview_inputs=dict(page=0,scroll=0))["result"]
            self.assertTrue(result["valid"]);roles=result["family_preview"]["typography"]["roles"]
            self.assertEqual(roles[0]["requested"],candidate()["font_ui_large"])


if __name__=="__main__":unittest.main()
