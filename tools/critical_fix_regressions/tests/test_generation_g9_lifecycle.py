"""Genuine pre-edit G8 provenance, resolved G9 state and atomic rejection."""
import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import unittest
import zipfile
from unittest.mock import patch
import pygame
import test_generation_g4 as gameplay
import test_generation_g3_lifecycle as lifecycle
import test_generation_g4_interactions as interactions
from test_effect_persistence import make_engine
from generation.placement import digest
from generation.context import GenerationError
from generation.country_network import touched,baseline
from generation.network_metrics import road_cells
from engine.save_manager import _serialize_player,_serialize_world
from engine.checkpoints import record
from g1_support import fingerprint

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/g9'


class G9Lifecycle(unittest.TestCase):
    setUpClass=classmethod(gameplay.G4Gameplay.setUpClass.__func__)
    setUp=gameplay.G4Gameplay.setUp
    boot=lifecycle.G3Lifecycle.boot
    visit=interactions.G4Interactions.visit
    interact=interactions.G4Interactions.interact

    def evidence(self,name,value):
        out=Path(os.environ.get('RESONANCE_TEST_EVIDENCE_DIR',self.root));out.mkdir(parents=True,exist_ok=True);(out/name).write_text(json.dumps(value,indent=2)+'\n')

    def state(self,e):
        cache=e.save_manager.cache
        return dict(world=digest(_serialize_world(e.world_map)),player=digest(_serialize_player(e)),rng=e.rng.getstate(),head=e.save_manager.store.token(),
                    active=fingerprint(e.local_map,e.entities[1:]),active_ids=[id(e.local_map),*[id(a) for a in e.entities]],
                    hot=hashlib.sha256(pickle.dumps(cache.hot)).hexdigest(),submap_hot=hashlib.sha256(pickle.dumps(cache.submap_hot)).hexdigest(),
                    files={p.relative_to(self.root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()})

    def test_genuine_g8_visited_pending_common_country_and_compound(self):
        binding=json.loads((FIXTURES/'g8-witness.json').read_text());self.assertEqual(binding['head'],'b94a0b0db3685f7484632701f0486f3b0b79101e')
        with zipfile.ZipFile(FIXTURES/'authentic-g8-checkpoint.zip') as z:
            self.assertIsNone(z.testzip());manifest=json.loads(z.read('manifest.json'));slot=self.root/'slot_0';destination=slot/'generations'/manifest['generation'];z.extractall(destination)
            for name,expected in binding['files'].items():
                raw=z.read(name);self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(expected['bytes'],expected['sha256']))
        (slot/'HEAD.json').write_text(json.dumps(dict(checkpoint_version=1,current=manifest['generation'],previous=None)))
        e=make_engine(self.data);e.data=copy.copy(e.data);e.data.country_network={};e.data.settlement_layouts={};e.data.poi_profiles={}
        with patch('generation.country_network.augment',side_effect=AssertionError('reoptimized')),patch('generation.world_plan.build_plan',side_effect=AssertionError('replanned')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error);self.assertEqual(e.world_map.plan['version'],6);self.assertEqual(digest(e.world_map.plan),binding['plan_identity'])
            for scene in binding['scenes']:
                m,actors=e._prepare_destination(*scene['chunk']);self.assertEqual(fingerprint(m,actors),scene['fingerprint']);self.assertEqual(m.generation_revision,'wg8');self.assertEqual(m.plan_provenance,scene['provenance'])
            pending=[]
            for xy in (binding['pending'],binding['country_pending']):
                m,actors=e._prepare_destination(*xy);self.assertEqual(m.plan_provenance['adapter'],'g8-to-g9-v1');self.assertEqual(m.generation_revision,'wg9');pending.append(dict(chunk=xy,fingerprint=fingerprint(m,actors)))
            self.assertTrue(e.save_manager.save(e),e.save_manager.last_error);reader=make_engine(e.data);self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error);e.debug=False;e._handle_key_local(pygame.K_F9)
            for owner in (e,reader):
                for scene in binding['scenes']+pending:self.assertEqual(fingerprint(*owner._prepare_destination(*scene['chunk'])),scene['fingerprint'])
                self.assertEqual(digest(owner.world_map.plan),binding['plan_identity'])
        self.evidence('g9-genuine-g8-restore.json',dict(passed=True,creator=binding['head'],plan=binding['plan_identity'],visited_creator='wg8',pending_adapter='g8-to-g9-v1',mutations=binding['mutations'],pending=pending,cold_and_f9=True))

    def test_saved_network_pending_policy_independence_and_late_rollback(self):
        e=self.boot();p=e.world_map.plan;r=next(r for r in p['routes'] if r.get('network_role'));old=road_cells(baseline(p)['routes']);keys=[xy for xy in touched(r) if any((x//80,y//43)==xy for x,y in road_cells([r])-old)]
        self.assertGreater(len(keys),2);first=e._prepare_destination(*keys[0]);self.assertIsNotNone(first)
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error);before=self.state(e)
        from generation.planned_scene import validate_access
        prepared=[]
        def fail(m,section,*args):
            validate_access(m,section,*args);prepared.append(len(m.road_cells));raise GenerationError('G9 injected late populated-road failure')
        with patch('generation.planned_scene.validate_access',side_effect=fail):self.assertIsNone(e._prepare_destination(*keys[1]))
        self.assertTrue(prepared and prepared[0]>0);self.assertEqual(self.state(e),before)
        e.data=copy.copy(e.data);e.data.country_network={};identity=digest(p)
        with patch('generation.country_network.augment',side_effect=AssertionError('reoptimized')):
            m,actors=e._prepare_destination(*keys[1]);expected=fingerprint(m,actors);self.assertEqual(m.generation_revision,'wg9');self.assertEqual(digest(e.world_map.plan),identity)
            self.assertTrue(e.save_manager.save(e),e.save_manager.last_error);reader=make_engine(e.data);self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error);e.debug=False;e._handle_key_local(pygame.K_F9)
            self.assertEqual(fingerprint(*e._prepare_destination(*keys[1])),expected);self.assertEqual(fingerprint(*reader._prepare_destination(*keys[1])),expected)
        self.evidence('g9-late-rollback.json',dict(passed=True,prepared_road_cells=prepared,world_player_rng_active_actors_cache_files_head_unchanged=True,recovered=True,saved_policy_independent=True,scene=expected))

    def test_checksum_consistent_network_corruptions_fail_before_install(self):
        e=self.boot();self.assertTrue(e.save_manager.save(e));checkpoint=e.save_manager.checkpoint_path();original=(checkpoint/'world.json').read_bytes();manifest=json.loads((checkpoint/'manifest.json').read_text())
        def shortcut(p):return next(r for r in p['routes'] if r.get('network_role'))
        changes=[('missing shortcut reference',lambda p:p['network']['accepted'].clear()),('foreign shortcut',lambda p:p['network']['accepted'][0].update(route='road-0')),
                 ('altered endpoint',lambda p:shortcut(p).update(a='start')),('disconnected join',lambda p:shortcut(p)['points'][0].__setitem__(0,0)),
                 ('baseline road removed',lambda p:p['routes'].pop(0)),('forged construction',lambda p:p['network'].update(added_unique_steps=0)),
                 ('forged baseline budget',lambda p:p['network'].update(baseline_unique_steps=999999)),('forged benefit',lambda p:p['network']['accepted'][0].update(after_steps=1)),
                 ('foreign role',lambda p:shortcut(p).update(network_role='foreign')),('new water geometry',lambda p:shortcut(p)['rects'].append(p['waters'][0]['rects'][0])),
                 ('protected common road',lambda p:shortcut(p)['rects'].append(p['public_spaces'][0]['rects'][0])),('incompatible origin',lambda p:p.update(generation_revision='wg8')),
                 ('unknown future version',lambda p:p.update(version=8)),('bad policy boolean',lambda p:p['network']['policy'].update(max_shortcuts=True))]
        results=[];active=e.local_map;world=e.world_map
        for label,change in changes:
            saved=json.loads(original);change(saved['plan']);raw=json.dumps(saved).encode();(checkpoint/'world.json').write_bytes(raw);manifest['files']['world.json']=record(raw);(checkpoint/'manifest.json').write_text(json.dumps(manifest));before=self.state(e)
            with self.subTest(case=label),self.assertRaises(ValueError) as error:e.save_manager._prepare(e,checkpoint)
            self.assertIs(e.local_map,active);self.assertIs(e.world_map,world);self.assertEqual(self.state(e),before);results.append(dict(case=label,error=str(error.exception)))
        (checkpoint/'world.json').write_bytes(original);manifest['files']['world.json']=record(original);(checkpoint/'manifest.json').write_text(json.dumps(manifest));self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        self.evidence('g9-checksum-corruptions.json',dict(passed=True,cases=results,recovered=True))
