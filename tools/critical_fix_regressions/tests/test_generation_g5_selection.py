"""Resolved composition, bounded fitting and real checkpoint preflight."""
import copy
import gzip
import json
from collections import Counter
from pathlib import Path
import random
import unittest
from unittest.mock import patch
import test_generation_g4 as gameplay
import test_generation_g3_lifecycle as lifecycle
from generation.context import GenerationError
from generation.placement import digest
from generation.world_gen import generate_world
from generation.world_plan import _plot, validate_plan, address
from generation.settlement_selection import resolve, validate, eligible
from engine.checkpoints import record
from engine.save_manager import _serialize_world
from world.world_map import WorldMap
from g1_support import fingerprint


class G5Selection(unittest.TestCase):
    setUpClass=classmethod(gameplay.G4Gameplay.setUpClass.__func__)
    setUp=gameplay.G4Gameplay.setUp
    scene=gameplay.G4Gameplay.scene
    boot=lifecycle.G3Lifecycle.boot

    def test_default_roles_caps_and_single_landmark(self):
        plan=self.world.plan;self.assertEqual(plan['version'],7)
        for s in plan['settlements']:
            plots=[p for p in plan['plots'] if p['owner']==s['id']]
            ids={p['placement'] for p in plots};placements=[p for p in plan['placements'] if p['id'] in ids]
            counts=Counter(p['role'] for p in placements);assets=Counter(p['asset'] for p in placements)
            profile=plan['selection']['profiles'][s['form']]
            self.assertGreaterEqual(counts['residential'],1);self.assertGreaterEqual(counts['commercial'],1)
            for rows in profile['roles'].values():
                for rule in rows:self.assertLessEqual(assets[rule['asset']],rule['max_per_settlement'])
            self.assertGreater(len(assets),4)
        self.assertEqual(sum(n['id']=='landmark' for n in plan['nodes']),1)
        self.assertEqual(sum(p.get('role')=='landmark' for p in plan['placements']),1)

    def test_schema_invalid_selection_and_atomic_bounded_infeasibility(self):
        for change in (lambda p:p['profiles']['grid']['roles']['residential'][0].update(weight=float('nan')),
                       lambda p:p['profiles']['roadside']['roles']['commercial'][0].update(max_per_settlement=True),
                       lambda p:p['profiles']['grid']['roles']['residential'][0].update(asset='missing'),
                       lambda p:p['profiles']['grid']['minimum'].update(residential=8),
                       lambda p:p['profiles']['grid']['roles']['residential'].append(p['profiles']['grid']['roles']['residential'][0])):
            data=copy.copy(self.data);data.settlement_profiles=copy.deepcopy(self.data.settlement_profiles)
            change(data.settlement_profiles)
            # The minimum=8 case needs a smaller total cap to be incoherent.
            if data.settlement_profiles['profiles']['grid']['minimum']['residential']==8:
                for row in data.settlement_profiles['profiles']['grid']['roles']['residential']:row['max_per_settlement']=1
            with self.assertRaises(GenerationError):resolve(data)
        data=copy.copy(self.data);data.settlement_profiles=copy.deepcopy(self.data.settlement_profiles)
        data.structures=copy.deepcopy(self.data.structures)
        for row in data.settlement_profiles['profiles']['grid']['roles']['commercial']:
            data.structures[row['asset']]['placement']['rotations']=[90]
        data.settlement_profiles['profiles']['grid']['required_fit_budget']=7
        w=WorldMap(128,128);w.seed=20261023;before=copy.deepcopy(vars(w))
        with self.assertRaisesRegex(GenerationError,'required role minima infeasible.*7/7'):
            generate_world(w,data,random.Random(0))
        self.assertEqual(vars(w),before)

    def test_caps_weight_precedence_and_soft_fallback(self):
        # The production fitter sees base * role * neighbor penalty once per asset.
        plan,authority=gameplay.G4Placement.fixture(self)
        plan.update(selection=resolve(self.data),settlements=[dict(id='fixture',form='grid')])
        profile=plan['selection']['profiles']['grid']
        profile['roles']['residential']=[dict(asset='house_small_a',base_weight=2,weight=3,max_per_settlement=2)]
        profile['repeat_multiplier']=.25
        captured=[];choose=random.Random.choices
        def observe(rng,population,weights=None,**kw):
            captured.append(list(weights));return choose(rng,population,weights=weights,**kw)
        with patch.object(random.Random,'choices',observe):
            first=_plot(plan,authority,self.data,'fixture','grid',0,0,20,21,'S','assigned',role='residential',slot_order=0)
            second=_plot(plan,authority,self.data,'fixture','grid',0,0,20,21,'N','assigned',role='residential',slot_order=1)
        self.assertEqual(captured,[[6],[1.5]])
        self.assertTrue(first['placement']);self.assertTrue(second['placement']);self.assertIn('soft fallback',second['repetition'])
        third=_plot(plan,authority,self.data,'fixture','grid',0,0,56,21,'S','assigned',role='residential',slot_order=2)
        self.assertIsNone(third['placement']);self.assertIn('hard per-settlement cap',third['rejected'][0]['reason'])
        profile['roles']['residential'][0]['max_per_settlement']=3
        failed=_plot(plan,authority,self.data,'fixture','grid',0,0,20,21,'S','assigned',role='residential',slot_order=3)
        self.assertIsNone(failed['placement'])
        self.assertTrue(eligible(plan,'fixture','residential',4)[0])

    def test_real_checkpoint_new_fields_and_role_corruption_rejected(self):
        e=self.boot();self.assertTrue(e.save_manager.save(e));checkpoint=e.save_manager.checkpoint_path()
        original=(checkpoint/'world.json').read_bytes();manifest=json.loads((checkpoint/'manifest.json').read_bytes())
        for mutate in (lambda p:p.pop('selection'),lambda p:p['plots'][0].pop('role'),
                       lambda p:p['placements'][0].pop('frontage_entrance'),
                       lambda p:p['plots'][1].update(role='civic'),
                       lambda p:p['placements'][0].update(role='support'),
                       lambda p:p['plots'][0].update(owner='landmark')):
            saved=json.loads(original);mutate(saved['plan']);payload=json.dumps(saved).encode()
            (checkpoint/'world.json').write_bytes(payload);manifest['files']['world.json']=record(payload)
            (checkpoint/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):e.save_manager._prepare(e,checkpoint)

    def test_required_backtracking_reserves_the_only_residential_frontage(self):
        from generation.settlement_selection import populate_settlement
        data=copy.copy(self.data);data.structures=copy.deepcopy(self.data.structures)
        data.structures['house_small_a']['placement']['rotations']=[0]
        data.structures['market_stall_a']['placement']['rotations']=[0,180]
        plan,authority=gameplay.G4Placement.fixture(self)
        settlement=dict(id='fixture',form='roadside',plots=[],civic=None)
        plan.update(selection=resolve(data),settlements=[settlement],diagnostics=[])
        profile=plan['selection']['profiles']['roadside']
        for role,aid in [('residential','house_small_a'),('commercial','market_stall_a')]:
            profile['roles'][role]=[dict(asset=aid,base_weight=1,weight=1,max_per_settlement=2)]
        slots=[(0,0,20,21,'S','assigned',0),(0,0,20,21,'N','assigned',1)]
        populate_settlement(plan,authority,data,settlement,slots)
        roles={p['role']:p['normal'] for p in plan['plots']}
        self.assertEqual(roles,dict(residential='S',commercial='N'))
        self.assertGreater(plan['diagnostics'][0]['attempts'],2)

    def test_selection_only_edits_keep_pending(self):
        e=self.boot();plan_identity=digest(e.world_map.plan)
        pending=tuple(e.world_map.plan['settlements'][0]['members'][0])
        result=self.scene(pending,e.world_map);expected=fingerprint(result.local_map,result.actors)
        self.assertTrue(e.save_manager.save(e))
        e.data.settlement_profiles=copy.deepcopy(e.data.settlement_profiles)
        profile=e.data.settlement_profiles['profiles']['grid'];profile['repeat_multiplier']=.9
        profile['roles']['residential'].reverse();profile['roles']['residential'][0]['weight']=8
        profile['roles']['commercial'][0]['max_per_settlement']=1
        with patch('generation.world_plan.build_plan',side_effect=AssertionError('reselected')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
            self.assertEqual(digest(e.world_map.plan),plan_identity)
            self.assertEqual(fingerprint(*e._prepare_destination(*pending)),expected)

    def test_old_g4_plan_and_scene_provenance(self):
        # Authentic G4 geometry in a synthetic disposable envelope. Saved wg4
        # scenes retain their old adapter; unseen scenes truthfully use wg5.
        fixture=Path(__file__).resolve().parents[1]/'fixtures/g5/g4_plan_20261023.json.gz'
        w=copy.deepcopy(self.world);w.plan=json.loads(gzip.decompress(fixture.read_bytes()));w.generation_revision='wg4'
        from generation.world_plan import publish_plan
        w.town_chunks.clear();w.town_chunk_ids.clear();w.town_groups.clear();publish_plan(w,w.plan)
        before=digest(w.plan);keys=[tuple(s['members'][0]) for s in w.plan['settlements'][:2]]
        first={xy:fingerprint((r:=self.scene(xy,w)).local_map,r.actors,r.metadata.town_data) for xy in keys}
        second={xy:fingerprint((r:=self.scene(xy,w)).local_map,r.actors,r.metadata.town_data) for xy in reversed(keys)}
        self.assertEqual(first,second);self.assertEqual(digest(w.plan),before)
        e=self.boot();start=(w.start_wx,w.start_wy)
        w.get(*start).submaps=copy.deepcopy(e.world_map.get(*start).submaps);e.world_map=w
        from generation.world_plan import slice_plan
        m=e.save_manager.cache.load(*start).local_map;section=slice_plan(w.plan,*start)
        m.generation_revision='wg4';w.get(*start).generation_revision='wg4'
        m.plan_provenance=dict(mode='shared-v1',plan_revision='wg4',plan_version=2,plan_identity=before,
            dependency_projection='structure-v1',adapter='g4-v1',
            **{k:[r['id'] for r in section[k]] for k in ('routes','crossings','placements')})
        m.set_tile(2,2,'mud',True,True);e.save_manager.cache.store(*start,m,[])
        created=e._prepare_destination(*keys[0]);self.assertIsNotNone(created)
        self.assertEqual(created[0].plan_provenance['adapter'],'g4-to-g9-v1')
        saved=fingerprint(*created);self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        with patch('generation.world_plan.build_plan',side_effect=AssertionError('replanned')),patch('engine.scene_generation.populate',side_effect=AssertionError('repopulated')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
            self.assertEqual(fingerprint(*e._prepare_destination(*keys[0])),saved)
            self.assertEqual(str(e._prepare_destination(*start)[0].tiles[2,2]['terrain']),'mud')
            self.assertEqual(e._prepare_destination(*start)[0].generation_revision,'wg4')
        self.assertEqual(digest(e.world_map.plan),before)
