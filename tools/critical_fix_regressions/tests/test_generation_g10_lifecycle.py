"""Authentic G9 pending terrain, frozen new policy and atomic recovery."""
import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import unittest
import zipfile
from unittest.mock import patch
import pygame
import test_generation_g9_lifecycle as g9
from test_effect_persistence import make_engine
from generation.context import GenerationError
from generation.placement import digest
from generation.wilderness import make_policy
from engine.checkpoints import record
from engine.scene_generation import create_surface
from g1_support import fingerprint

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/g10'


def historical_relationship_inputs(data, binding):
    """Exact archived pending-generation comparison with its original inputs.

    G21 deliberately changes fresh factory attitudes. Keep the historical whole
    fingerprint/ZIP validators intact: bind only these two definition fields to
    the immutable creator revision, never rewrite saved actors or fingerprints.
    Current fresh targeting is exercised independently by test_gameplay_g21.
    """
    root=Path(__file__).resolve().parents[3]
    result=copy.copy(data);result.entities=copy.deepcopy(data.entities)
    for identifier in ('highland_bandit','heath_stalker'):
        path=f'roguelike/data/entities/creatures/{identifier}.json'
        raw=subprocess.check_output(['git','show',binding['head']+':'+path],cwd=root)
        expected=binding.get('source',{}).get(path)
        normalized=raw.replace(b'\r\n',b'\n')
        if expected is not None:
            assert expected in {hashlib.sha256(value).hexdigest() for value in
                                (raw,normalized,normalized.replace(b'\n',b'\r\n'))}
        original=json.loads(raw)['perception']
        for field in ('faction','hostile_to'):
            result.entities[identifier]['perception'][field]=copy.deepcopy(original[field])
    return result


class G10Lifecycle(unittest.TestCase):
    setUpClass=classmethod(g9.G9Lifecycle.setUpClass.__func__)
    setUp=g9.G9Lifecycle.setUp
    boot=g9.G9Lifecycle.boot
    state=g9.G9Lifecycle.state
    evidence=g9.G9Lifecycle.evidence

    def test_genuine_g9_visited_mutation_and_exact_pending_results(self):
        binding=json.loads((FIXTURES/'g9-witness.json').read_text())
        self.assertEqual(binding['head'],'f9fe901417b360bc1fda84835e0a793eaac2f6df')
        with zipfile.ZipFile(FIXTURES/'authentic-g9-checkpoint.zip') as z:
            self.assertIsNone(z.testzip());manifest=json.loads(z.read('manifest.json'));slot=self.root/'slot_0'
            z.extractall(slot/'generations'/manifest['generation'])
            for name,expected in binding['files'].items():
                raw=z.read(name);self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(expected['bytes'],expected['sha256']))
        (slot/'HEAD.json').write_text(json.dumps(dict(checkpoint_version=1,current=manifest['generation'],previous=None)))
        e=make_engine(historical_relationship_inputs(self.data,binding))
        with patch('generation.world_plan.build_plan',side_effect=AssertionError('replanned')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
            self.assertEqual(e.world_map.surface_schema,0);self.assertIsNone(e.world_map.surface_policy)
            self.assertEqual(digest(e.world_map.plan),binding['plan_identity'])
            for row in binding['scenes']+binding['pending']:
                m,actors=e._prepare_destination(*row['chunk'])
                self.assertEqual(fingerprint(m,actors),row['fingerprint']);self.assertIsNone(getattr(m,'surface_provenance',None))
            m,_=e._prepare_destination(*binding['scenes'][0]['chunk'])
            self.assertIn(tuple(binding['mutation']['waystone']),m.interacted_waystones)
            self.assertTrue(e.save_manager.save(e));reader=make_engine(e.data)
            self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
            e.debug=False;e._handle_key_local(pygame.K_F9)
            for owner in (e,reader):
                for row in binding['scenes']+binding['pending']:
                    self.assertEqual(fingerprint(*owner._prepare_destination(*row['chunk'])),row['fingerprint'])
        self.evidence('g10-genuine-g9.json',dict(passed=True,creator=binding['head'],visited=binding['scenes'],pending=binding['pending'],actual_waystone_mutation=True,cold_and_f9=True))

    def test_saved_policy_ignores_installed_edits_removal_and_restores_pending(self):
        e=self.boot();xy=(e.world_x+1,e.world_y+1);w=e.world_map;p=copy.deepcopy(w.surface_policy)
        r=create_surface(w,w.get(*xy),e.data,e.item_factory,e.creature_factory,80,43)
        expected=fingerprint(r.local_map,r.actors)
        self.assertTrue(e.save_manager.save(e));identity=digest(w.plan)
        for installed in ({},dict(version=999),dict(version=1,profiles={})):
            e.data=copy.copy(e.data);e.data.wilderness_profiles=installed
            reader=make_engine(e.data);self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
            self.assertEqual(reader.world_map.surface_policy,p)
            self.assertEqual(fingerprint(*reader._prepare_destination(*xy)),expected)
            e.debug=False;e._handle_key_local(pygame.K_F9)
            self.assertEqual(fingerprint(*e._prepare_destination(*xy)),expected)
            self.assertEqual(digest(e.world_map.plan),identity)
        self.evidence('g10-frozen-policy.json',dict(passed=True,identity=p['identity'],pending=xy,fingerprint=expected,installed_removed_malformed_changed=True))

    def test_checksum_consistent_missing_malformed_and_forged_policy_reject_atomically(self):
        e=self.boot();self.assertTrue(e.save_manager.save(e));checkpoint=e.save_manager.checkpoint_path()
        original=(checkpoint/'world.json').read_bytes();manifest=json.loads((checkpoint/'manifest.json').read_text())
        def forge(w):
            p=w['surface_policy'];p['profiles']['profiles']['forest']['cover']=4
            p['identity']=digest({k:v for k,v in p.items() if k!='identity'})
        changes=[('missing-policy',lambda w:w.pop('surface_policy')),
            ('deleted-schema',lambda w:w.pop('surface_schema')),
            ('deleted-both-contract-fields',lambda w:(w.pop('surface_schema'),w.pop('surface_policy'))),
            ('future-schema',lambda w:w.update(surface_schema=2)),
            ('unknown-algorithm',lambda w:w['surface_policy'].update(algorithm='future')),
            ('forged-identity',lambda w:w['surface_policy'].update(identity='0'*64)),
            ('checksum-consistent-invalid-range',forge)]
        results=[]
        for label,change in changes:
            saved=json.loads(original);change(saved);raw=json.dumps(saved).encode();(checkpoint/'world.json').write_bytes(raw)
            manifest['files']['world.json']=record(raw);(checkpoint/'manifest.json').write_text(json.dumps(manifest));before=self.state(e)
            with self.assertRaises(ValueError) as error:e.save_manager._prepare(e,checkpoint)
            self.assertEqual(self.state(e),before);results.append(dict(case=label,error=str(error.exception)))
        (checkpoint/'world.json').write_bytes(original);manifest['files']['world.json']=record(original)
        # Saved scene policy claims are required even though the G9 plan is valid.
        scene=next((checkpoint/'chunks').glob('*_*.pkl'));raw=scene.read_bytes();saved=pickle.loads(raw)
        if not hasattr(saved.local_map,'surface_provenance'):
            scene=next(p for p in (checkpoint/'chunks').glob('*.pkl') if hasattr(pickle.loads(p.read_bytes()).local_map,'surface_provenance'));raw=scene.read_bytes();saved=pickle.loads(raw)
        del saved.local_map.surface_provenance;scene.write_bytes(pickle.dumps(saved,protocol=pickle.HIGHEST_PROTOCOL))
        manifest['files'][scene.relative_to(checkpoint).as_posix()]=record(scene.read_bytes());(checkpoint/'manifest.json').write_text(json.dumps(manifest));before=self.state(e)
        with self.assertRaisesRegex(ValueError,'surface policy provenance'):e.save_manager._prepare(e,checkpoint)
        self.assertEqual(self.state(e),before)
        scene.write_bytes(raw);manifest['files'][scene.relative_to(checkpoint).as_posix()]=record(raw);(checkpoint/'manifest.json').write_text(json.dumps(manifest))
        self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        self.evidence('g10-policy-negatives.json',dict(passed=True,cases=results,scene_missing_provenance_rejected=True,recovered=True))

    def test_missing_required_terrain_and_post_population_failure_rollback_recovery(self):
        e=self.boot();xy=(e.world_x+1,e.world_y+1);self.assertTrue(e.save_manager.save(e));before=self.state(e)
        from generation.planned_scene import validate_access
        prepared=[]
        def reject(m,*args):
            validate_access(m,*args);prepared.append(dict(roads=len(m.road_cells),decor=len(m.decor),terrain=m.surface_provenance));raise GenerationError('G10 late populated terrain rejection')
        with patch('generation.planned_scene.validate_access',side_effect=reject):self.assertIsNone(e._prepare_destination(*xy))
        self.assertTrue(prepared);self.assertEqual(self.state(e),before)
        e.data=copy.copy(e.data);e.data.terrain=copy.deepcopy(e.data.terrain);rock=e.data.terrain.pop('rock')
        self.assertIsNone(e._prepare_destination(*xy));self.assertEqual(self.state(e),before)
        e.data.terrain['rock']=rock
        self.assertIsNotNone(e._prepare_destination(*xy));self.assertEqual(e.save_manager.store.token(),before['head'])
        self.evidence('g10-atomic-recovery.json',dict(passed=True,late=prepared,world_player_rng_cache_files_head_unchanged=True,missing_required_terrain=True,recovered=True))
