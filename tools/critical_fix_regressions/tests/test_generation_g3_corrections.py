"""G3 corrective cases, exercising real consumers and disposable checkpoints."""
import copy
import json
import os
from pathlib import Path
import pickle
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from generation.structure_preview import preview, registration, render_svg, receipt_owned
from generation.structure_contract import read_document
from generation.context import GenerationError
from engine.scene_generation import populate
from world.world_map import Chunk, RegionType
from world.local_map import LocalMap, make_tile
from g1_support import fingerprint


class G3Corrections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_data()
        cls.cottage=read_document(GAME_ROOT/'docs/examples/author_cottage_a.json')

    def test_real_town_checkpoint_and_cold_second_catalog(self):
        with tempfile.TemporaryDirectory() as tmp, patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'):
            e=make_engine(self.data); e.world_map.width=2
            e.world_map.set(Chunk(1,0,RegionType.TOWN,29417,town_id=1,town_role='N'))
            e.overmap_cursor_x,e.overmap_cursor_y=1,0; e._teleport_to_overmap_cursor()
            self.assertEqual(e.world_x,1); self.assertFalse(hasattr(e.local_map,'structure_data'))
            expected=fingerprint(e.local_map,e.entities[1:])
            # Simulate the accidental G2 attribute; reconstruction drops only that field.
            state=vars(e.local_map).copy(); state['structure_data']=self.data
            restored=LocalMap.__new__(LocalMap); restored.__setstate__(state)
            self.assertEqual(fingerprint(restored,e.entities[1:]),expected)
            e.local_map.structure_data=self.data
            self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
            raw=(e.save_manager.checkpoint_path()/'chunks/1_0.pkl').read_bytes()
            self.assertNotIn(b'DataLoader',raw); self.assertNotIn(b'StructureCatalog',raw)
            root=Path(tmp)/'catalog'; shutil.copytree(GAME_ROOT/'data',root)
            code='''from pathlib import Path
from unittest.mock import patch
from test_effect_persistence import make_engine
from engine.data_loader import DataLoader
from g1_support import fingerprint
import sys
with patch('engine.save_manager.SAVE_DIR',Path(sys.argv[1])):
 d=DataLoader(sys.argv[2]); e=make_engine(d)
 assert e.save_manager.load(e),e.save_manager.last_error
 assert e.data is d and not hasattr(e.local_map,'structure_data')
 assert fingerprint(e.local_map,e.entities[1:])==sys.argv[3]
'''
            result=subprocess.run([sys.executable,'-c',code,str(Path(tmp)/'saves'),str(root),expected],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_documented_initialization_preserves_edited_draft(self):
        if os.name!='nt': self.skipTest('Documented PowerShell workflow requires Windows')
        guide=(GAME_ROOT/'docs/STRUCTURE_AUTHORING.md').read_text(encoding='utf-8')
        start=guide.index('if (-not (Test-Path -LiteralPath authoring/author_cottage_a.json))')
        command=guide[start:guide.index('\n}',start)+2]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'authoring').mkdir()
            draft=copy.deepcopy(self.cottage); draft['owner_sentinel']='keep edited draft'
            path=root/'authoring/author_cottage_a.json'; path.write_text(json.dumps(draft))
            before=path.read_bytes()
            for _ in range(2):
                result=subprocess.run(['powershell','-NoProfile','-Command',command],cwd=root,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(path.read_bytes(),before)
            report,_,_=preview(read_document(path),'ordinary_building',self.data,category='residential')
            self.assertTrue(report['passed']); self.assertEqual(path.read_bytes(),before)

    def test_actual_arrival_and_direct_route_absence(self):
        doc={'id':'arrival','layers':['<..','...','...'],'legend':{'.':'floor','<':'stairs_up'},'player_start':{'x':1,'y':1}}
        for xy,passed in [((1,1),True),((0,0),False)]:
            report,_,_=preview(doc,'authored_submap',self.data,expectations={'targets':[{'kind':'arrival','x':xy[0],'y':xy[1]}]})
            self.assertEqual(report['passed'],passed)
        for route in ('ordinary_building','plaza','interior_entrance'):
            entry=self.data.structure_catalog.by_route[route]
            asset=next(iter(entry.values()))
            report,_,_=preview(asset.raw,route,self.data,category=asset.category)
            self.assertNotIn('spawn',report); self.assertNotIn('<title>Generated arrival',render_svg(report))
        report,_,_=preview(self.cottage,'ordinary_building',self.data,category='residential',expectations={'targets':[{'kind':'arrival','x':4,'y':6}]})
        self.assertFalse(report['passed']); self.assertIn('context required',report['access'][0]['diagnostic'])
        access=read_document(GAME_ROOT/'docs/examples/author_cottage_access.json')
        report,_,_=preview(self.cottage,'ordinary_building',self.data,category='residential',expectations=access)
        self.assertTrue(report['passed'])

    def test_relocated_registration_and_suppression_identity(self):
        doc=copy.deepcopy(self.cottage); doc['id']='g3_relocated'
        doc['special_tiles']=[{'type':'item','x':0,'y':0,'item_id':'crow_jerky'}]
        self.assertTrue(registration(doc,self.data,'residential')['passed'])
        from generation.floor_object_utils import place_floor_object
        def substitute(m,x,y,value):
            place_floor_object(m,x,y,copy.deepcopy(value))
        with patch('generation.floor_object_utils.place_floor_object',substitute):
            with self.assertRaisesRegex(GenerationError,'missing realized item'):
                registration(doc,self.data,'residential')

    def test_receipts_scene_multiplicity_text_and_container_ownership(self):
        data=copy.copy(self.data); data.scenes=dict(data.scenes,receipt_scene={'floor_objects':[{'item_id':'crow_jerky'},{'item_id':'crow_jerky'}]})
        e=make_engine(data); m=e.local_map; receipts=[]
        specs=[{'kind':'scene','scene_id':'receipt_scene','x':3,'y':3},
               {'kind':'item','item_id':'lab_note','text_id':'waystone_prayer_a','x':4,'y':3},
               {'kind':'container','x':5,'y':3,'loot_pools':[]}]
        populate(data,e.item_factory,e.creature_factory,m,specs,map_text=True,receipts=receipts)
        self.assertEqual(len(receipts[0]['objects']),2)
        self.assertTrue(all(receipt_owned(r,m) for r in receipts))
        self.assertEqual(receipts[1]['objects'][0].text_id,'waystone_prayer_a')
        m.floor_objects[3,3].pop(); self.assertFalse(receipt_owned(receipts[0],m))
        m.container_state[5,3]['items'].append(e.item_factory.create('crow_jerky',5,3))
        # Empty rolled contents are observed separately from subsequent live inventory.
        self.assertEqual(receipts[2]['kind'],'container')
