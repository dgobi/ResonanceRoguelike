"""Actual G3 restoration, pending dependency mismatch and saved ownership."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import pygame
from test_effect_persistence import load_data,make_engine,GAME_ROOT
from generation.world_gen import generate_world
from generation.placement import digest
from generation.world_plan import address
from engine.engine import Engine
from engine.save_manager import _serialize_world
from g1_support import fingerprint


class G3Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_data()

    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        p=patch('engine.save_manager.SAVE_DIR',self.root);p.start();self.addCleanup(p.stop)
        cap=contextlib.redirect_stdout(io.StringIO());cap.__enter__();self.addCleanup(cap.__exit__,None,None,None)

    def boot(self):
        import main
        slot=self.root/'slot_0';slot.mkdir(exist_ok=True);(slot/'world.json').write_text(json.dumps({'seed':20261023}))
        captured=[];old=Path.cwd()
        try:
            os.chdir(GAME_ROOT)
            with patch.object(Engine,'run',lambda e:captured.append(e)):main.main()
        finally:os.chdir(old)
        return captured[0]

    def test_startup_and_f9_restore_never_generate_plan_or_population(self):
        import main
        e=self.boot();e.debug=False;e._handle_key_local(pygame.K_F5)
        expected=digest(_serialize_world(e.world_map));scene=fingerprint(e.local_map,e.entities[1:])
        captured=[];old=Path.cwd()
        try:
            os.chdir(GAME_ROOT)
            with patch.object(main,'generate_world',side_effect=AssertionError('restore generated world')),patch('generation.world_plan.build_plan',side_effect=AssertionError('restore planned')),patch('engine.scene_generation.populate',side_effect=AssertionError('restore populated')),patch.object(Engine,'run',lambda e:captured.append(e)):
                main.main();reader=captured[0];reader.debug=False;reader._handle_key_local(pygame.K_F9)
        finally:os.chdir(old)
        self.assertEqual(digest(_serialize_world(reader.world_map)),expected)
        self.assertEqual(fingerprint(reader.local_map,reader.entities[1:]),scene)

    def test_reference_validation_distinguishes_generated_and_unversioned_owner_maps(self):
        from world.local_map import LocalMap
        from engine.checkpoints import record
        import pickle
        e=self.boot();xy=(e.world_x+1,e.world_y)
        synthetic=LocalMap(80,43);synthetic.set_tile(3,3,'mud',True,True)
        e.save_manager.cache.store(*xy,synthetic,[])
        self.assertTrue(e.save_manager.save(e));self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        self.assertEqual(str(e.save_manager.cache.load(*xy).local_map.tiles[3,3]['terrain']),'mud')
        # A checksum-consistent missing reference on an actual G3 surface is
        # semantic corruption, not permission to bypass the plan contract.
        checkpoint=e.save_manager.checkpoint_path();scene=checkpoint/f'chunks/{e.world_x}_{e.world_y}.pkl'
        saved=pickle.loads(scene.read_bytes());self.assertEqual(saved.local_map.generation_revision,'wg6')
        del saved.local_map.plan_provenance;scene.write_bytes(pickle.dumps(saved,protocol=pickle.HIGHEST_PROTOCOL))
        manifest_path=checkpoint/'manifest.json';manifest=json.loads(manifest_path.read_text())
        manifest['files'][scene.relative_to(checkpoint).as_posix()]=record(scene.read_bytes());manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'missing required shared scene references'):e.save_manager._prepare(e,checkpoint)

    def test_pending_semantic_change_preserves_load_cached_scene_and_unaffected_placement(self):
        e=self.boot();e.debug=False
        houses=[p for p in e.world_map.plan['placements'] if p['asset']=='house_small_a']
        first=address(*houses[0]['origin'])[:2];pending=next(address(*p['origin'])[:2] for p in houses if address(*p['origin'])[:2]!=first)
        prepared=e._prepare_destination(*first);self.assertIsNotNone(prepared)
        m,_=prepared;target=next(iter(m.floor_objects));taken=m.floor_objects[target].pop()
        e.player.inventory.add(taken);m.set_tile(2,2,'mud',True,True)
        e.save_manager.cache.store(*first,m,prepared[1]);e._handle_key_local(pygame.K_F5)
        head=e.save_manager.store.token();plan=digest(e.world_map.plan)
        data=copy.copy(self.data);data.structures=copy.deepcopy(data.structures)
        data.structures['house_small_a']['legend']['w']='floor'
        e.data=data;e._handle_key_local(pygame.K_F9)
        self.assertIsNone(e.save_manager.last_error);self.assertEqual(digest(e.world_map.plan),plan)
        cached=e._prepare_destination(*first);self.assertIsNotNone(cached)
        self.assertEqual(str(cached[0].tiles[2,2]['terrain']),'mud')
        self.assertEqual(sum(len(v) for v in cached[0].floor_objects.values()),sum(len(v) for v in m.floor_objects.values()))
        unaffected=next(p for p in e.world_map.plan['placements'] if p['context']=='landmark')
        self.assertIsNotNone(e._prepare_destination(*address(*unaffected['origin'])[:2]))
        before=digest(_serialize_world(e.world_map));active=e.local_map
        self.assertIsNone(e._prepare_destination(*pending));self.assertIs(e.local_map,active)
        self.assertEqual(digest(_serialize_world(e.world_map)),before);self.assertEqual(e.save_manager.store.token(),head)
        e._handle_key_local(pygame.K_F9)
        self.assertEqual(digest(e.world_map.plan),plan);self.assertEqual(e.save_manager.store.token(),head)
        self.assertIsNone(e.save_manager.cache.load(*address(*unaffected['origin'])[:2]))

    def test_fresh_process_hash_seeds_complete_plan_and_content(self):
        code='''import contextlib,io,random,json
from test_effect_persistence import load_data
from generation.world_gen import generate_world
from generation.placement import digest
from engine.scene_generation import create_surface
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from world.world_map import WorldMap
from g1_support import fingerprint
with contextlib.redirect_stdout(io.StringIO()):
 d=load_data();w=WorldMap(128,128);w.seed=20261023
 random.seed(99);[random.random() for _ in range(127)]
 generate_world(w,d,random.Random(87))
 xy=w.plan['settlements'][0]['members'][0]
 r=create_surface(w,w.get(*xy),d,ItemFactory(d),CreatureFactory(d),80,43)
print(json.dumps([digest(w.plan),fingerprint(r.local_map,r.actors,r.metadata.town_data)]))
'''
        rows=[]
        for seed in ('0','317'):
            result=subprocess.run([sys.executable,'-c',code],env=dict(os.environ,PYTHONHASHSEED=seed),capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr);rows.append(json.loads(result.stdout))
        self.assertEqual(rows[0],rows[1])
