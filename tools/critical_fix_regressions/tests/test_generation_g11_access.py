"""Exterior access through composition, reciprocal metadata and bounded placement."""
import copy
import contextlib
import gzip
import io
import json
import os
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch
import numpy as np
from test_effect_persistence import load_data
from engine.save_manager import _deserialize_world, _serialize_world
from engine.scene_generation import create_surface, validate_scene
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from generation.access import reachable, validate_required_access
from generation.context import GenerationContext, GenerationError
from generation.placement import digest
from generation.wilderness import make_policy, sample
from world.world_map import WorldMap
from g1_support import fingerprint

ROOT = Path(__file__).resolve().parents[3]
BEFORE = ROOT/'evidence/worldgen-g10/before'


def world(data, revision=1):
    w = WorldMap(128,128)
    _deserialize_world(json.loads(gzip.decompress((BEFORE/'world-20261023.json.gz').read_bytes())), w)
    w.surface_schema = 1
    w.surface_policy = make_policy(data.wilderness_profiles,data,access_revision=revision)
    return w


class G11Access(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.world = world(cls.data)
        cls.items,cls.creatures = ItemFactory(cls.data),CreatureFactory(cls.data)

    def scene(self,xy,w=None):
        w = w or self.world
        return create_surface(w,w.get(*xy),self.data,self.items,self.creatures,80,43)

    def evidence(self,name,value):
        out = os.environ.get('RESONANCE_TEST_EVIDENCE_DIR')
        if out:
            p=Path(out);p.mkdir(parents=True,exist_ok=True)
            (p/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

    def test_exact_regression_reselects_without_repair_or_field_changes(self):
        old = world(self.data,0)
        started=time.perf_counter();before=self.scene((44,8),old);oldtime=time.perf_counter()-started
        from generation.wilderness import materialize
        started=time.perf_counter()
        with patch('engine.scene_generation.create_surface',side_effect=AssertionError('eager neighbor scene')), \
                patch('generation.wilderness.materialize',wraps=materialize) as made:
            after=self.scene((44,8))
        self.assertEqual(made.call_count,1)
        newtime=time.perf_counter()-started
        m=after.local_map;c=m.wilderness_access
        oldreach=reachable(before.local_map,before.spawn,self.data)
        self.assertFalse(any(x in (0,79) or y in (0,42) for x,y in oldreach))
        self.assertEqual(list(before.local_map.submap_links),[(14,5)])
        reached=validate_required_access(m,list(m.submap_links),self.data)
        self.assertIn(tuple(c['edge']),reached)
        self.assertEqual(list(m.submap_links.values()),['submap_44_8_0'])
        self.assertNotEqual(list(m.submap_links),[(14,5)])
        self.assertEqual(m.wilderness_generation['repairs'],[])
        self.assertGreater(m.generation_diagnostics[0]['access_rejections'],0)
        for key in ('terrain','biome','cover','patch','wet','moisture','elevation'):
            np.testing.assert_array_equal(sample(old,old.surface_policy,44*80,8*43)[key],
                                          sample(self.world,self.world.surface_policy,44*80,8*43)[key])
        neighbor=self.scene(c['neighbor']).local_map
        from generation.access import enterable
        self.assertTrue(enterable(neighbor,tuple(c['reciprocal']),self.data))
        self.assertEqual(self.world.plan,old.plan)
        self.assertFalse(any(ch.visited for ch in self.world.chunks.values()))
        self.evidence('g11-exact.json',dict(passed=True,before_stair=[14,5],after_stairs=list(m.submap_links),
            contract=c,diagnostics=m.generation_diagnostics,old_seconds=oldtime,new_seconds=newtime,
            base_fields_identical=True,terrain_repairs=[],neighbor_static_reciprocal=True,no_eager_neighbors=True))

    def test_discriminating_late_decor_cut_and_multiple_link_fallback(self):
        from world.local_map import LocalMap
        from generation.region_gen import _place_submap_entrance
        from types import SimpleNamespace
        m=LocalMap(20,15,generation_context=GenerationContext(1,2,(4,5,None)))
        for x in range(20):
            for y in range(15):m.set_tile(x,y,'rock',False,False)
        for xy in {(x,7) for x in range(13)}|{(x,y) for x in range(10,19) for y in range(4,11)}:
            m.set_tile(*xy,'grass',True,True)
        spawn=(12,7);m.required_access_anchors=[spawn,(0,7)]
        m.protected_cells={(x,7) for x in range(10)}
        m.surface_provenance=dict(owner='wilderness',access_revision=1)
        m.wilderness_access=dict(revision=1,chunk=[4,5],arrival=list(spawn),edge=[0,7],neighbor=[3,5],reciprocal=[19,7])
        subs=[SimpleNamespace(submap_id=f'fixture-{i}',submap_type='cave',seed=i,surface_x=-1,surface_y=-1) for i in range(2)]
        with patch('generation.entrance_gen._pick_layout',return_value=None):
            for sub in subs:_place_submap_entrance(m,sub,self.data.terrain,self.data)
        validate_scene(m,subs,self.data)
        self.assertEqual(set(m.submap_links.values()),{'fixture-0','fixture-1'})
        self.assertTrue(all(r['status']=='bare-stair-fallback' for r in m.generation_diagnostics))
        self.assertEqual(sum(str(m.tiles[x,y]['terrain'])=='rock' for x in range(20) for y in range(15)),227)
        blocked=next(k for k,v in self.data.decoratives.items() if v.get('blocks_movement'))
        m.decor[8,7]=blocked
        # The old arrival/stair predicate accepts the sealed component.
        reached=reachable(m,spawn,self.data)
        self.assertTrue(set(m.submap_links)<=reached)
        historical=copy.deepcopy(m);del historical.wilderness_access;del historical.surface_provenance
        historical.required_access_anchors=[spawn]
        validate_scene(historical,subs,self.data)
        with self.assertRaisesRegex(GenerationError,'access revision 1.*required target.*reciprocal exterior'):
            validate_scene(m,subs,self.data)
        # No-submap arrivals need the same completed-scene check.
        with self.assertRaises(GenerationError):validate_scene(m,[],self.data)
        self.evidence('g11-late-cut-fallback.json',dict(passed=True,old_validator_accepts=True,
            final_validator_rejects=True,blocking_decor=blocked,links=list(m.submap_links.values()),
            diagnostics=m.generation_diagnostics))

    def test_discovery_sample_and_targeted_road_water_world_edge(self):
        source=ROOT/'evidence/worldgen-g11/before/review-package/evidence/access/probe.json'
        selected=[tuple(r['chunk']) for r in json.loads(source.read_text())['samples']]
        targeted=[(73,99),(73,100),(0,64)]
        # A wilderness owner with actual authoritative water and a route.
        from generation.world_plan import slice_plan
        from generation.wilderness import eligible
        for ch in self.world.chunks.values():
            if eligible(ch) and ch.is_river and slice_plan(self.world.plan,ch.wx,ch.wy)['routes']:
                targeted.append((ch.wx,ch.wy));break
        rows=[]
        for xy in selected+targeted:
            with self.subTest(chunk=xy):
                t=time.perf_counter();r=self.scene(xy);elapsed=time.perf_counter()-t
                m=r.local_map;contract=m.wilderness_access
                reached=validate_required_access(m,list(m.submap_links),self.data)
                self.assertIn(tuple(contract['edge']),reached)
                self.assertTrue(self.world.in_bounds(*contract['neighbor']))
                self.assertFalse(m.wilderness_generation['repairs'])
                self.assertEqual(len(m.submap_links),len(self.world.get(*xy).submaps))
                rows.append(dict(chunk=xy,contract=contract,stairs=len(m.submap_links),seconds=elapsed,
                                 roads=len(m.road_cells),protected=len(m.protected_cells)))
        self.evidence('g11-sample.json',dict(passed=True,selection='Supplied 60-scene discovery list plus four targeted cases; not prevalence.',rows=rows))

    def test_three_complete_macro_plans_and_coarse_owners_unchanged(self):
        from generation.world_gen import generate_world
        rows=[]
        for seed in (0,20261023,29417):
            w=WorldMap(128,128);w.seed=seed
            with contextlib.redirect_stdout(io.StringIO()):generate_world(w,self.data,random.Random(seed))
            current=_serialize_world(w);current.pop('surface_schema');current.pop('surface_policy')
            original=json.loads(gzip.decompress((BEFORE/f'world-{seed}.json.gz').read_bytes()))
            self.assertEqual(json.loads(json.dumps(current)),original)
            rows.append(dict(seed=seed,plan_identity=digest(w.plan),coarse_exact=True))
        self.evidence('g11-macro.json',dict(passed=True,rows=rows))
