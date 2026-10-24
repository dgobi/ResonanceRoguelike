"""Independent topology fixtures and ordinary G9 preservation/admission behavior."""
import copy
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_effect_persistence import load_data
from generation.context import GenerationError
from generation.country_network import DEFAULT,policy,baseline,search,stage,check_geometry,touched,augment
from generation.network_metrics import centerline_edges,topology,distances,physical_cells,pair_id,terminals,road_cells
from generation.world_plan import bands,validate_plan
from generation.world_gen import generate_world
from generation.placement import digest
from world.world_map import WorldMap

ROOT=Path(__file__).resolve().parents[3]


def route(points,name='road',width=3):
    return dict(id=name,points=points,rects=bands(points,width),kind='country',width=width)


def small(roads=()):
    return dict(routes=list(roads),crossings=[],waters=[],settlements=[],sites=[],placements=[],reservations=[],nodes=[])


class NetworkGeometry(unittest.TestCase):
    def test_anisotropic_search_reuse_has_real_cost_and_finite_exhaustion(self):
        chunks={(x,y):SimpleNamespace(biome_id='plains',submaps=[],is_capital=False,is_river=False) for x in range(4) for y in range(4)}
        world=SimpleNamespace(chunks=chunks,get=lambda x,y:chunks.get((x,y)))
        a=dict(id='a',chunk=[0,0]);b=dict(id='b',chunk=[1,1])
        old=route([[40,21],[40,107],[120,107],[120,64]])
        path,n,status=search(world,small([old]),a,b,16)
        self.assertEqual(sum(80*abs(x[0]-y[0])+43*abs(x[1]-y[1]) for x,y in zip(path,path[1:])),123)
        self.assertEqual(status,'found');self.assertLessEqual(n,16)
        self.assertEqual(search(world,small([old]),a,b,1),(None,1,'search expansion limit'))
        chunks[1,0].submaps=['owned'];chunks[0,1].is_river=True
        self.assertEqual(search(world,small(),a,b,16)[2],'no legal macro corridor')

    def test_union_intersection_rings_and_parallel_contracted_runs(self):
        crossing=[route([[0,2],[4,2]]),route([[2,0],[2,4]]),route([[1,2],[3,2]])]
        edges=centerline_edges(crossing);t=topology(edges)
        self.assertEqual((len(edges),t['components'],t['cycle_rank'],t['cut_edge_steps']),(8,1,0,8))
        ring=centerline_edges([route([[0,0],[2,0],[2,2],[0,2],[0,0]])]);t=topology(ring)
        self.assertEqual((t['unique_centerline_steps'],t['cycle_rank'],t['cut_edge_steps'],len(t['runs'])),(8,1,0,1))
        self.assertEqual(t['runs'][0]['a'],t['runs'][0]['b'])
        parallel=topology(ring,[(0,0),(2,2)])['runs'];self.assertEqual(len(parallel),2);self.assertEqual([r['steps'] for r in parallel],[4,4])
        with self.assertRaisesRegex(GenerationError,'diagonal'):centerline_edges([route([[0,0],[0,1]])|dict(points=[[0,0],[1,1]])])
        with self.assertRaisesRegex(GenerationError,'disconnected'):distances({(0,0),(1,1)},[dict(id='a',xy=[0,0]),dict(id='b',xy=[1,1])])

    def test_full_width_corner_and_private_ownership_and_local_disconnect(self):
        original=small();original['settlements']=[dict(members=[[1,0]])]
        with self.assertRaisesRegex(GenerationError,'protected owner'):check_geometry(original,original,route([[79,3],[79,35]]))
        original=small();original['reservations']=[dict(owner='common',purpose='common',rect=[21,21,23,23])]
        with self.assertRaisesRegex(GenerationError,'private/common'):check_geometry(original,original,route([[10,20],[20,20],[20,30]]))
        original=small()
        with self.assertRaisesRegex(GenerationError,'disconnected locally'):check_geometry(original,original,route([[20,20],[20,64],[60,64],[60,20]]))

    def test_existing_deck_reuse_no_new_water_and_reservation_order(self):
        old=route([[10,21],[70,21]]);original=small([old]);original['waters']=[dict(id='water',rects=[[38,0,43,43]])]
        original['crossings']=[dict(id='bridge',road='road',water='water',deck=[[36,20,45,23]])]
        original['reservations']=[dict(id='old-road',owner='road',purpose='road',rect=old['rects'][0]),dict(id='old-approach',owner='building',purpose='approach',rect=[10,21,13,25])]
        proposed=route([[10,21],[70,21],[70,35]],'new')
        staged=stage(original,original,proposed)
        self.assertEqual(len(staged['crossings']),2)
        self.assertEqual(staged['reservations'][-1],original['reservations'][-1])
        self.assertEqual(road_cells([dict(rects=c['deck']) for c in staged['crossings']])-road_cells([dict(rects=c['deck']) for c in original['crossings']]),set())
        with self.assertRaisesRegex(GenerationError,'existing owned bridge'):check_geometry(original,original,route([[10,10],[70,10]],'new'))

    def test_strict_policy(self):
        for key,value in [('version',True),('version',2),('max_shortcuts',True),('max_shortcuts',3),('min_saved_steps',-1),('max_added_fraction',float('nan')),('max_added_fraction',.251),('min_relative_improvement',float('inf')),('candidate_pair_limit',0),('search_expansion_limit',16385),('world_expansion_budget',65537),('unknown',1)]:
            with self.subTest(key=key,value=value),self.assertRaises(GenerationError):policy(dict(DEFAULT,**{key:value}))
        self.assertEqual(policy(DEFAULT),DEFAULT)


class G9Network(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=load_data()

    def evidence(self,name,value):
        if os.environ.get('RESONANCE_TEST_EVIDENCE_DIR'):
            p=Path(os.environ['RESONANCE_TEST_EVIDENCE_DIR'])/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2)+'\n')

    def world(self,seed=20261023,data=None,metrics=None):
        w=WorldMap(128,128);w.seed=seed;generate_world(w,data or self.data,random.Random(92),planning_metrics=metrics);return w

    def test_ordinary_preservation_benefit_and_every_touched_scene(self):
        from engine.scene_generation import create_surface
        from engine.item_factory import ItemFactory
        from engine.creature_factory import CreatureFactory
        from g1_support import fingerprint
        rows=[]
        for seed in (0,20261023,29417):
            m={};w=self.world(seed,metrics=m);p=w.plan;b=baseline(p)
            self.assertEqual(json.loads(json.dumps(b)),json.loads((ROOT/f'evidence/worldgen-g9/before/baseline/results/plan-{seed}.json').read_text()))
            self.assertFalse(any(ch.visited for ch in w.chunks.values()))
            before=distances(physical_cells(b),terminals(b));after=distances(physical_cells(p),terminals(p))
            self.assertTrue(all(after[k]<=v for k,v in before.items()))
            self.assertLessEqual(p['network']['added_unique_steps'],p['network']['baseline_unique_steps']*.25)
            if seed==20261023:
                key=pair_id('settlement-1','capital-gateway');self.assertEqual(before[key],23625);self.assertLessEqual(after[key],before[key]/2)
            prints={};slices={}
            for xy in sorted({xy for r in p['routes'] if r.get('network_role') for xy in touched(r)}):
                scene=create_surface(w,w.get(*xy),self.data,ItemFactory(self.data),CreatureFactory(self.data),80,43)
                prints[str(xy)]=fingerprint(scene.local_map,scene.actors);slices[xy]=scene.local_map.road_cells
                self.assertFalse({(a.x,a.y) for a in scene.actors}&scene.local_map.road_cells)
            for (x,y),points in slices.items():
                if (x+1,y) in slices:self.assertEqual({b for a,b in points if a==79},{b for a,b in slices[x+1,y] if a==0})
                if (x,y+1) in slices:self.assertEqual({a for a,b in points if b==42},{a for a,b in slices[x,y+1] if b==0})
            if slices:
                reverse_world=self.world(seed)
                for xy in reversed(sorted(slices)):
                    scene=create_surface(reverse_world,reverse_world.get(*xy),self.data,ItemFactory(self.data),CreatureFactory(self.data),80,43)
                    self.assertEqual(fingerprint(scene.local_map,scene.actors),prints[str(xy)])
            rows.append(dict(seed=seed,network=p['network'],before=before,after=after,scenes=prints,reverse_first_visits_equal=True,metrics=m['network']))
        self.evidence('g9-ordinary-touched.json',rows)

    def test_disabled_zero_budget_and_exhaustion_keep_complete_baseline(self):
        rows=[]
        for overrides,outcome in [({'max_shortcuts':0},'disabled'),({'max_added_fraction':0},'zero construction budget'),({'world_expansion_budget':1},'global expansion budget exhausted'),({'search_expansion_limit':1},'bounded search exhausted without qualifying candidate')]:
            d=copy.copy(self.data);d.country_network=dict(DEFAULT,**overrides);w=self.world(data=d)
            self.assertEqual(w.plan['network']['outcome'],outcome);self.assertEqual(w.plan['network']['accepted'],[])
            self.assertEqual(json.loads(json.dumps(baseline(w.plan))),json.loads((ROOT/'evidence/worldgen-g9/before/baseline/results/plan-20261023.json').read_text()))
            rows.append(dict(policy=overrides,result=w.plan['network']))
        self.evidence('g9-optional-outcomes.json',rows)

    def test_new_contract_parent_policies_and_explicit_legacy_settings(self):
        from generation.poi_selection import single_policy
        rows=[]
        for selected in ('mixed','single','zero','historical-g8'):
            d=copy.copy(self.data);d.g3_config=copy.deepcopy(d.g3_config);d.poi_profiles=copy.deepcopy(d.poi_profiles);d.country_network=dict(DEFAULT,max_shortcuts=0)
            if selected=='single':d.poi_profiles=single_policy(d.poi_profiles)
            if selected=='zero':d.poi_profiles.update(minimum=0,maximum=0,kind_minimum=dict(single=0,compound=0))
            if selected=='historical-g8':d.g3_config['version']=3;d.g3_config.pop('country_network_version')
            w=self.world(data=d);self.assertEqual(w.plan['version'],6 if selected=='historical-g8' else 7);self.assertTrue(w.plan['public_spaces'])
            if selected=='zero':self.assertEqual(w.plan['sites'],[])
            rows.append(dict(poi=selected,version=w.plan['version'],origin=w.plan['generation_revision']))
        self.evidence('g9-policy-combinations.json',rows)

    def test_two_connections_union_marginal_benefit_and_exact_shared_budget(self):
        # Declared controlled fixture: ordinary seed 3 with reduced admission
        # thresholds. This does not replace the three shipped-policy samples.
        d=copy.copy(self.data);d.country_network=dict(DEFAULT,min_saved_steps=1,min_relative_improvement=.01)
        w=self.world(3,d);p=w.plan;n=p['network'];self.assertEqual(len(n['accepted']),2)
        old=baseline(p);roads=[r for r in p['routes'] if r.get('network_role')];base=centerline_edges(r for r in old['routes'] if r['kind']=='country')
        first,second=[centerline_edges([r]) for r in roads];overlap=(first&second)-base;self.assertTrue(overlap)
        self.assertEqual(n['added_unique_steps'],len((first|second)-base));self.assertLess(n['added_unique_steps'],len(first-base)+len(second-base))
        partial=stage(old,old,roads[0],w);nodes=[r for r in terminals(p) if r['id'] in (roads[1]['a'],roads[1]['b'])];key=n['accepted'][1]['pair']
        original_distance=distances(physical_cells(old),nodes)[key];marginal=distances(physical_cells(partial),nodes)[key]
        self.assertLess(marginal,original_distance);self.assertEqual(n['accepted'][1]['before_steps'],marginal)
        exact=copy.deepcopy(p);total=n['added_unique_steps'];denominator=n['baseline_unique_steps']
        exact['network']['policy']['max_added_fraction']=(total+.25)/denominator;exact['network']['construction_limit_steps']=total;validate_plan(exact,128,128)
        exact['network']['policy']['max_added_fraction']=(total-.25)/denominator;exact['network']['construction_limit_steps']=total-1
        with self.assertRaisesRegex(GenerationError,'over-budget'):validate_plan(exact,128,128)
        bad=copy.deepcopy(p);bad['network']['accepted'][1]['before_steps']=original_distance
        with self.assertRaisesRegex(GenerationError,'forged physical benefit'):validate_plan(bad,128,128)
        self.evidence('g9-two-link-marginal-budget.json',dict(controlled_seed=3,policy=d.country_network,accepted=n['accepted'],overlapping_new_steps=len(overlap),total_union_steps=total,original_second_pair_distance=original_distance,marginal_second_pair_distance=marginal,exact_budget_pass=True,one_step_below_rejected=True,double_credited_benefit_rejected=True))

    def test_real_existing_bridge_reuse_replays_normal_reservations(self):
        old=baseline(self.world().plan)
        # Geometry-only controlled duplicate: no construction or utility claim.
        # Admission separately rejects duplicates, but this exercises a genuine
        # existing deck through the same stage and normal validator as proposals.
        r=copy.deepcopy(next(r for r in old['routes'] if r['id']=='road-1'))
        r.update(id='controlled-deck-reuse',required=False)
        staged=stage(old,old,r);validate_plan(staged,128,128)
        added=[c for c in staged['crossings'] if c['road']==r['id']]
        self.assertTrue(added)
        original_decks=road_cells([dict(rects=c['deck']) for c in old['crossings']])
        self.assertFalse(road_cells([dict(rects=c['deck']) for c in added])-original_decks)
        self.assertEqual([v for v in staged['reservations'] if v['owner']!=r['id']],old['reservations'])
        self.evidence('g9-real-deck-replay.json',dict(passed=True,controlled_geometry_only=True,new_physical_bridge_cells=0,new_crossing_ownership_rows=len(added),normal_validate_plan_passed=True,original_reservations_preserved=True))
