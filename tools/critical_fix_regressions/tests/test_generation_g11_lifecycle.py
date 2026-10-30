"""Genuine G10 preservation and corrected access contract atomic restoration."""
import copy
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import unittest
import zipfile
from unittest.mock import patch
import pygame
import test_generation_g9_lifecycle as g9
from test_effect_persistence import make_engine
from generation.placement import digest
from engine.checkpoints import record
from engine.scene_generation import create_surface
from engine.save_manager import _serialize_player
from g1_support import fingerprint
from test_generation_g10_lifecycle import historical_pending_scene

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/g11'


class G11Lifecycle(unittest.TestCase):
    setUpClass=classmethod(g9.G9Lifecycle.setUpClass.__func__)
    setUp=g9.G9Lifecycle.setUp
    boot=g9.G9Lifecycle.boot
    state=g9.G9Lifecycle.state
    evidence=g9.G9Lifecycle.evidence

    def test_genuine_preedit_g10_mutation_visited_pending_load_and_f9(self):
        b=json.loads((FIXTURES/'g10-witness.json').read_text())
        self.assertEqual(b['head'],'7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b')
        with zipfile.ZipFile(FIXTURES/'authentic-g10-checkpoint.zip') as z:
            self.assertIsNone(z.testzip());manifest=json.loads(z.read('manifest.json'));slot=self.root/'slot_0'
            z.extractall(slot/'generations'/manifest['generation'])
            for name,expected in b['files'].items():
                raw=z.read(name);self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(expected['bytes'],expected['sha256']))
        (slot/'HEAD.json').write_text(json.dumps(dict(checkpoint_version=1,current=manifest['generation'],previous=None)))
        e=make_engine(self.data)
        with patch('generation.world_plan.build_plan',side_effect=AssertionError('replanned')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
            self.assertEqual(e.world_map.surface_policy,b['policy'])
            self.assertEqual(digest(_serialize_player(e)),b['player'])
            self.assertEqual(digest(e.world_map.plan),b['plan_identity'])
            for row in b['scenes']+b['pending']:
                m,actors=(historical_pending_scene(e,row,b) if row in b['pending']
                          else e._prepare_destination(*row['chunk']))
                self.assertEqual(fingerprint(m,actors),row['fingerprint'])
                self.assertFalse(hasattr(m,'wilderness_access'))
            m,_=e._prepare_destination(*b['scenes'][0]['chunk'])
            self.assertIn(tuple(b['mutation']['waystone']),m.interacted_waystones)
            self.assertTrue(e.save_manager.save(e))
            reader=make_engine(e.data);self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
            e.debug=False;e._handle_key_local(pygame.K_F9)
            for owner in (e,reader):
                for row in b['scenes']+b['pending']:
                    self.assertEqual(fingerprint(*owner._prepare_destination(*row['chunk'])),row['fingerprint'])
        self.evidence('g11-genuine-g10.json',dict(passed=True,creator=b['head'],visited=b['scenes'],pending=b['pending'],
            mutable_waystone_preserved=True,ordinary_load_and_F9=True,known_old_access_defect_retained=True))

    def test_new_contract_frozen_pending_and_checksum_consistent_negatives(self):
        e=self.boot();xy=(44,8);w=e.world_map;p=copy.deepcopy(w.surface_policy)
        self.assertEqual(p['version'],2);self.assertEqual(p['access_revision'],1)
        r=create_surface(w,w.get(*xy),e.data,e.item_factory,e.creature_factory,80,43)
        expected=fingerprint(r.local_map,r.actors);contract=r.local_map.wilderness_access
        self.assertTrue(e.save_manager.save(e));checkpoint=e.save_manager.checkpoint_path()
        original=(checkpoint/'world.json').read_bytes();manifest=json.loads((checkpoint/'manifest.json').read_text())
        cases=[]
        changes=[('missing-access',lambda p:p.pop('access_revision')),
                 ('boolean-access',lambda p:p.update(access_revision=True)),
                 ('future-access',lambda p:p.update(access_revision=2)),
                 ('downgrade-access',lambda p:(p.update(version=1),p.pop('access_revision')))]
        for label,change in changes:
            saved=json.loads(original);change(saved['surface_policy'])
            saved['surface_policy']['identity']=digest({k:v for k,v in saved['surface_policy'].items() if k!='identity'})
            raw=json.dumps(saved).encode();(checkpoint/'world.json').write_bytes(raw)
            manifest['files']['world.json']=record(raw);(checkpoint/'manifest.json').write_text(json.dumps(manifest));before=self.state(e)
            with self.assertRaises(ValueError) as error:e.save_manager._prepare(e,checkpoint)
            self.assertEqual(self.state(e),before);cases.append(dict(case=label,error=str(error.exception)))
        (checkpoint/'world.json').write_bytes(original);manifest['files']['world.json']=record(original)
        # A checksum-consistent scene cannot silently omit corrected provenance.
        scene=next(f for f in (checkpoint/'chunks').glob('*.pkl') if getattr(pickle.loads(f.read_bytes()).local_map,'surface_provenance',None))
        original_scene=scene.read_bytes();cached=pickle.loads(original_scene)
        cached.local_map.surface_provenance.pop('access_revision')
        scene.write_bytes(pickle.dumps(cached,protocol=pickle.HIGHEST_PROTOCOL))
        name=scene.relative_to(checkpoint).as_posix();manifest['files'][name]=record(scene.read_bytes())
        (checkpoint/'manifest.json').write_text(json.dumps(manifest));before=self.state(e)
        with self.assertRaisesRegex(ValueError,'surface policy provenance'):e.save_manager._prepare(e,checkpoint)
        self.assertEqual(self.state(e),before)
        scene.write_bytes(original_scene);manifest['files'][name]=record(original_scene)
        (checkpoint/'manifest.json').write_text(json.dumps(manifest))
        for installed in ({},dict(version=999),dict(version=1,profiles={})):
            data=copy.copy(e.data);data.wilderness_profiles=installed
            reader=make_engine(data);self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
            self.assertEqual(reader.world_map.surface_policy,p)
            m,actors=reader._prepare_destination(*xy)
            self.assertEqual(fingerprint(m,actors),expected);self.assertEqual(m.wilderness_access,contract)
            e.data=data;e.debug=False;e._handle_key_local(pygame.K_F9)
            self.assertEqual(fingerprint(*e._prepare_destination(*xy)),expected)
        self.evidence('g11-contract.json',dict(passed=True,cases=cases,scene_provenance_rejected=True,
            recovered=True,installed_tuning_independent=True,pending=xy,contract=contract,fingerprint=expected))

    def test_late_exterior_cut_is_atomic_and_retry_plays(self):
        e=self.boot();self.assertTrue(e.save_manager.save(e));before=self.state(e)
        head=subprocess.check_output(['git','rev-parse','HEAD'],text=True)
        from generation.planned_dressing import dress
        prepared=[]
        def sever(m,*args):
            result=dress(m,*args)
            edge=tuple(m.wilderness_access['edge']);prepared.append(dict(contract=m.wilderness_access,links=list(m.submap_links)))
            m.set_tile(*edge,'rock',False,False)
            return result
        with patch('generation.planned_dressing.dress',side_effect=sever):
            self.assertIsNone(e._prepare_destination(44,8))
        self.assertTrue(prepared);self.assertEqual(self.state(e),before)
        self.assertEqual(subprocess.check_output(['git','rev-parse','HEAD'],text=True),head)
        m,actors=e._prepare_destination(44,8)
        from generation.access import validate_required_access
        self.assertTrue(validate_required_access(m,list(m.submap_links),e.data))
        self.assertEqual(e.save_manager.store.token(),before['head'])
        self.evidence('g11-atomic.json',dict(passed=True,late=prepared,world_player_cache_rng_files_checkpoint_git_head_unchanged=True,recovered=True))
