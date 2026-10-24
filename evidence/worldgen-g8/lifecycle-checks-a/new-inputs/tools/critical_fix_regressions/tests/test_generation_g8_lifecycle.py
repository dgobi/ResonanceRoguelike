"""Genuine G7 restore, checksum-consistent corruption and complete scene rollback."""
import copy
import json
import os
from pathlib import Path
import time
import unittest
import zipfile
from unittest.mock import patch
import pygame
import test_generation_g4 as gameplay
import test_generation_g3_lifecycle as lifecycle
import test_generation_g4_interactions as interactions
from test_effect_persistence import make_engine
from generation.context import GenerationError
from generation.placement import digest
from engine.save_manager import _serialize_player,_serialize_world
from engine.checkpoints import record
from g1_support import fingerprint

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/g8'


class G8Lifecycle(unittest.TestCase):
    setUpClass=classmethod(gameplay.G4Gameplay.setUpClass.__func__)
    setUp=gameplay.G4Gameplay.setUp
    boot=lifecycle.G3Lifecycle.boot
    visit=interactions.G4Interactions.visit
    interact=interactions.G4Interactions.interact

    def evidence(self,name,value):
        out=Path(os.environ.get('RESONANCE_TEST_EVIDENCE_DIR',self.root));out.mkdir(parents=True,exist_ok=True)
        (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

    def test_genuine_g7_visited_mutations_and_pending_town_compound(self):
        binding=json.loads((FIXTURES/'g7-witness.json').read_text())
        self.assertEqual(binding['head'],'8e56d36d72537e8b32c3666dd5d19723d1afdf3a')
        with zipfile.ZipFile(FIXTURES/'authentic-g7-checkpoint.zip') as z:
            manifest=json.loads(z.read('manifest.json'));slot=self.root/'slot_0';destination=slot/'generations'/manifest['generation'];z.extractall(destination)
        (slot/'HEAD.json').write_text(json.dumps(dict(checkpoint_version=1,current=manifest['generation'],previous=None)))
        e=make_engine(self.data);observed=[]
        with patch('generation.world_plan.build_plan',side_effect=AssertionError('replanning')),patch('generation.settlement_layout.compose',side_effect=AssertionError('recomposition')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error);self.assertEqual(digest(e.world_map.plan),binding['plan_identity'])
            for scene in binding['scenes']:
                m,a=e._prepare_destination(*scene['chunk']);self.assertEqual(fingerprint(m,a),scene['fingerprint']);self.assertEqual(m.generation_revision,'wg7');self.assertEqual(m.plan_provenance,scene['provenance'])
            for xy in [binding['pending'],binding['rural_pending']]:
                m,a=e._prepare_destination(*xy);self.assertEqual(m.plan_provenance['adapter'],'g7-to-g8-v1');self.assertEqual(m.plan_provenance['plan_version'],5);self.assertEqual(m.generation_revision,'wg8');observed.append(xy)
            self.assertTrue(e.save_manager.save(e),e.save_manager.last_error);e.debug=False;e._handle_key_local(pygame.K_F9)
            for scene in binding['scenes']:self.assertEqual(fingerprint(*e._prepare_destination(*scene['chunk'])),scene['fingerprint'])
            self.assertEqual(digest(e.world_map.plan),binding['plan_identity'])
        self.evidence('g8-genuine-g7-restore.json',dict(creator=binding['head'],original_plan=binding['plan_identity'],visited_creator='wg7',pending_adapter='g7-to-g8-v1',pending=observed,original_interaction_mutations=binding['mutations'],saved_bytes_unchanged=True))

    def test_pending_recipe_removal_dependency_scope_and_late_atomic_failure(self):
        e=self.boot();s=e.world_map.plan['settlements'][0];xy=s['members'][0]
        before=(digest(_serialize_world(e.world_map)),digest(_serialize_player(e)),e.rng.getstate(),e.save_manager.store.token());active=e.local_map;actors=e.entities[:]
        from generation.town_gen import _stamp_building_at
        calls=[]
        common=next(c for c in e.world_map.plan['public_spaces'] if c['owner']==s['id'])
        point=common['rects'][0][:2]
        def obstruct(m,raw,ox,oy,*args,**kwargs):
            rows=_stamp_building_at(m,raw,ox,oy,*args,**kwargs);calls.append(raw['id'])
            if len(calls)==2:m.set_tile(point[0]%80,point[1]%43,'wall',False,False)
            return rows
        with patch('generation.town_gen._stamp_building_at',side_effect=obstruct):self.assertIsNone(e._prepare_destination(*xy))
        self.assertGreaterEqual(len(calls),2);self.assertIs(e.local_map,active);self.assertEqual(e.entities,actors);self.assertIsNone(e.save_manager.cache.load(*xy))
        self.assertEqual((digest(_serialize_world(e.world_map)),digest(_serialize_player(e)),e.rng.getstate(),e.save_manager.store.token()),before)
        e.data=copy.copy(self.data);e.data.settlement_layouts={};e.data.settlement_profiles={};identity=digest(e.world_map.plan)
        with patch('generation.settlement_layout.compose',side_effect=AssertionError('recompose')):self.assertIsNotNone(e._prepare_destination(*xy))
        e.data.terrain=copy.deepcopy(self.data.terrain);e.data.terrain[common['surface']]['walkable']=False
        self.assertIsNotNone(e._prepare_destination(*xy)) # visited cache owns its state
        from engine.scene_generation import create_surface
        with self.assertRaisesRegex(GenerationError,'changed dependency terrain'):
            create_surface(e.world_map,e.world_map.get(*xy),e.data,e.item_factory,e.creature_factory,80,43)
        unaffected=s['members'][1];self.assertIsNotNone(e._prepare_destination(*unaffected));self.assertEqual(digest(e.world_map.plan),identity)
        self.evidence('g8-late-rollback.json',dict(stamped=calls,common_pass_then_late_obstruction=True,world_player_rng_active_cache_head_unchanged=True,recovered=True,removed_layout_and_selection_usable=True,public_surface_dependency_affected_only=True))

    def test_checksum_consistent_layout_corruptions_reject_before_installation(self):
        e=self.boot();self.assertTrue(e.save_manager.save(e));checkpoint=e.save_manager.checkpoint_path()
        original=(checkpoint/'world.json').read_bytes();manifest=json.loads((checkpoint/'manifest.json').read_text())
        def townplot(p):return next(r for r in p['plots'] if r.get('block'))
        changes=[('wrong frontage road',lambda p:townplot(p)['frontage'].update(road='road-0')),
                 ('wrong segment',lambda p:townplot(p)['frontage'].update(segment=9999)),
                 ('foreign lot',lambda p:p['blocks'][0]['lots'].append(next(b for b in p['blocks'] if b['owner']!=p['blocks'][0]['owner'] and b['lots'])['lots'][0])),
                 ('duplicate lot',lambda p:p['blocks'][0]['lots'].append(p['blocks'][0]['lots'][0])),
                 ('overlap private bounds',lambda p:p['blocks'][1].update(bounds=p['blocks'][0]['bounds'])),
                 ('missing public geometry',lambda p:p['public_spaces'].pop()),
                 ('foreign common civic',lambda p:p['public_spaces'][0].update(civic=p['public_spaces'][1]['civic'])),
                 ('missing common association',lambda p:p['settlements'][0]['civic'].pop('common')),
                 ('bad reservation',lambda p:next(r for r in p['reservations'] if r['purpose']=='common')['rect'].__setitem__(0,0)),
                 ('unsupported origin',lambda p:p.update(generation_revision='wg7'))]
        active=e.local_map;world=e.world_map;state=(e.save_manager.store.token(),e.rng.getstate(),digest(_serialize_player(e)));rows=[]
        for name,change in changes:
            saved=json.loads(original);change(saved['plan']);payload=json.dumps(saved).encode();(checkpoint/'world.json').write_bytes(payload);manifest['files']['world.json']=record(payload);(checkpoint/'manifest.json').write_text(json.dumps(manifest))
            with self.subTest(name=name),self.assertRaises(ValueError) as error:e.save_manager._prepare(e,checkpoint)
            rows.append(dict(case=name,error=str(error.exception)));self.assertIs(e.local_map,active);self.assertIs(e.world_map,world)
            self.assertEqual((e.save_manager.store.token(),e.rng.getstate(),digest(_serialize_player(e))),state)
        (checkpoint/'world.json').write_bytes(original);manifest['files']['world.json']=record(original);(checkpoint/'manifest.json').write_text(json.dumps(manifest))
        self.assertTrue(e.save_manager.load(e),e.save_manager.last_error);self.evidence('g8-checksum-corruptions.json',rows)

    def test_civic_handlers_native_updates_reverse_members_and_explored_save(self):
        from engine.engine import GameMode
        e=self.boot();e.debug=False;e.player_invincible=True;e.player.inventory.capacity=100
        s=e.world_map.plan['settlements'][0];common=next(c for c in e.world_map.plan['public_spaces'] if c['owner']==s['id']);xy=s['members'][0]
        self.visit(e,xy);turn=e.world_time.turn
        for _ in range(8):e._handle_key_local(pygame.K_z)
        self.assertEqual(e.world_time.turn,turn+8)
        stone,prayer=[(a%80,b%43) for a,b in common['furnishing']]
        with patch.object(type(e),'_advance_turn',lambda e:e.world_time.advance()):
            self.interact(e,stone);self.assertIn(stone,e.local_map.interacted_waystones)
            self.interact(e,prayer);self.assertTrue(any(getattr(i,'text_id',None)=='waystone_prayer_a' for i in e.player.inventory.items))
            mutations=[]
            for i,member in enumerate(reversed(s['members'])):
                self.visit(e,member);e.local_map.set_tile(2,2,'mud',True,True);mutations.append(member)
            compound=next(c for c in e.world_map.plan['sites'] if c['kind']=='compound');self.visit(e,compound['chunk'])
            containers=list(e.local_map.container_state.values());self.assertGreaterEqual(len(containers),2);self.assertIsNot(containers[0]['items'],containers[1]['items'])
            before=len(containers[0]['items']);containers[0]['items'].clear() # explicit direct fixture mutation, not interaction claim
            keys=s['members']+[compound['chunk']]
            expected={str(k):fingerprint(*e._prepare_destination(*k)) for k in keys}
            t=time.perf_counter();e._handle_key_local(pygame.K_F5);save_seconds=time.perf_counter()-t;self.assertIsNone(e.save_manager.last_error)
            checkpoint=e.save_manager.checkpoint_path();reader=make_engine(self.data);t=time.perf_counter();self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error);cold=time.perf_counter()-t
            for k in reversed(keys):self.assertEqual(fingerprint(*reader._prepare_destination(*k)),expected[str(k)])
            t=time.perf_counter();e._handle_key_local(pygame.K_F9);f9=time.perf_counter()-t
            for k in keys:self.assertEqual(fingerprint(*e._prepare_destination(*k)),expected[str(k)])
        self.evidence('g8-explored-checkpoint.json',dict(controls='fixture teleports/positioning; eight ordinary native updates, then stationary turns; actual waystone/prayer/F5/F9 handlers; direct terrain and first-child-container mutations explicitly labeled',members=mutations,compound=compound['chunk'],container_before=before,container_after=0,native_updates=8,save_seconds=save_seconds,cold_load_seconds=cold,f9_seconds=f9,scene_count=len(list((checkpoint/'chunks').glob('*.pkl'))),bytes=sum(p.stat().st_size for p in checkpoint.rglob('*') if p.is_file()),fingerprints=expected))
