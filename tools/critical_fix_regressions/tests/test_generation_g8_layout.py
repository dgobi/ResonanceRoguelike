"""Real composition/materialization, independent frontage negatives and policy paths."""
import copy
import json
import os
from pathlib import Path
import random
import unittest
from collections import Counter
from unittest.mock import patch
import test_generation_g4 as gameplay
from generation.context import GenerationError
from generation.world_gen import generate_world
from generation.world_plan import Reservations,_plot,bands,cells,settings,validate_plan
from generation.placement import digest
from generation.settlement_layout import validate,local_connectivity
from generation.poi_selection import single_policy
from world.world_map import WorldMap
from g1_support import fingerprint

ROOT=Path(__file__).resolve().parents[3]


class G8Layout(unittest.TestCase):
    setUpClass=classmethod(gameplay.G4Gameplay.setUpClass.__func__)
    setUp=gameplay.G4Gameplay.setUp
    scene=gameplay.G4Gameplay.scene

    def data_copy(self):
        d=copy.copy(self.data)
        for name in ('settlement_layouts','settlement_profiles','g3_config','poi_profiles','structures'):setattr(d,name,copy.deepcopy(getattr(d,name)))
        return d

    def world_for(self,data=None,seed=20261023):
        w=WorldMap(128,128);w.seed=seed;generate_world(w,data or self.data,random.Random(0));return w

    def evidence(self,name,value):
        out=Path(os.environ.get('RESONANCE_TEST_EVIDENCE_DIR',self.root));out.mkdir(parents=True,exist_ok=True)
        (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

    def test_ordinary_matrix_unchanged_country_and_full_population(self):
        rows=[]
        for seed in (0,20261023,29417):
            w=self.world_for(seed=seed);plan=w.plan
            old=json.loads((ROOT/f'evidence/worldgen-g8/before/baseline/results/plan-{seed}.json').read_text())
            self.assertEqual([r for r in plan['routes'] if r['kind']=='country' and not r.get('network_role')],[r for r in old['routes'] if r['kind']=='country'])
            self.assertFalse(any(c.visited for c in w.chunks.values()))
            for s in plan['settlements']:
                normals=Counter(p['normal'] for p in plan['plots'] if p['owner']==s['id'] and p['placement'])
                self.assertTrue(set(normals)&set('NS'))
                if s['form']=='grid':self.assertTrue(set(normals)&set('EW'))
                else:self.assertFalse(set(normals)&set('EW'))
                prints={}
                for xy in s['members']:
                    r=self.scene(xy,w);self.assertGreaterEqual(len(r.actors),2)
                    self.assertFalse({(a.x,a.y) for a in r.actors}&r.local_map.protected_cells)
                    prints[str(xy)]=fingerprint(r.local_map,r.actors)
                rows.append(dict(seed=seed,settlement=s['id'],layout=s['layout']['id'],normals=normals,scenes=prints))
        self.evidence('g8-ordinary.json',dict(country_routes_exactly_equal=True,scenes_at_plan_completion=0,rows=rows))

    def test_each_layout_cardinal_frontage_and_reorder_reverse_visit_determinism(self):
        rows=[]
        for name in sorted(r['id'] for r in self.data.settlement_layouts['grid']):
            data=self.data_copy();data.settlement_layouts['grid']=[r for r in data.settlement_layouts['grid'] if r['id']==name]
            # Declared controlled optional schedule, installed buildings/permissions.
            data.settlement_profiles['profiles']['grid']['schedule']=['residential','commercial']
            w=self.world_for(data);s=w.plan['settlements'][0]
            normals={p['normal'] for p in w.plan['plots'] if p['owner']==s['id'] and p['placement']};self.assertEqual(normals,set('NESW'))
            first={tuple(xy):fingerprint((r:=self.scene(xy,w)).local_map,r.actors) for xy in s['members']}
            reverse={tuple(xy):fingerprint((r:=self.scene(xy,w)).local_map,r.actors) for xy in reversed(s['members'])};self.assertEqual(first,reverse)
            for profile in data.settlement_profiles['profiles'].values():
                for membership in profile['roles'].values():membership.reverse()
            data.settlement_layouts['grid'][0]['streets'].reverse()
            self.assertEqual(w.plan,self.world_for(data).plan)
            rows.append(dict(layout=name,normals=sorted(normals),reverse_visits=True,unordered_membership_invariant=True,controlled_schedule=['residential','commercial']))
        self.evidence('g8-cardinal-layouts.json',rows)

    def test_full_door_spans_all_normals_widths_private_and_public_negatives(self):
        data=self.data;observed=[]
        for width in (1,2,3,4,5):
            for normal in 'NESW':
                horizontal=normal in 'NS';points=[[2,21],[77,21]] if horizontal else [[40,2],[40,40]]
                road=dict(id='test-road',points=points,width=width,rects=bands(points,width));band=road['rects'][0]
                bounds={'S':[1,1,79,band[1]],'N':[1,band[3],79,42],'E':[1,1,band[0],42],'W':[band[2],1,79,42]}[normal]
                axis=0 if horizontal else 1
                lot=dict(id='test-lot',owner='test',block='test-block',bounds=bounds,join=[40,21],frontage=dict(road='test-road',segment=0,span=[3,76] if horizontal else [3,39],normal=normal),civic=False)
                def run(lot,common=None):
                    plan=dict(version=6,seed=23,settings=settings(data),plots=[],placements=[],dependencies={},routes=[road]);a=Reservations();a.add(road['id'],'road',band)
                    if common:a.add('public','common',common)
                    p=_plot(plan,a,data,'test','grid',0,0,40,21,normal,road['id'],only_assets=['market_stall_a'],identity=lot['id'],explicit_bounds=lot['bounds'],lot=lot)
                    return p,plan,a
                p,plan,a=run(lot);self.assertIsNotNone(p['placement'],p['rejected']);building=plan['placements'][0]
                narrow=copy.deepcopy(lot);narrow['frontage']['span']=[lot['join'][axis],lot['join'][axis]+1]
                p,_,_=run(narrow);self.assertIsNone(p['placement']);self.assertTrue(any('span' in r['reason'] for r in p['rejected']))
                tight=copy.deepcopy(lot);tight['bounds']=building['footprint']
                p,_,_=run(tight);self.assertIsNone(p['placement'])
                p,_,_=run(lot,building['footprint']);self.assertIsNone(p['placement'])
                observed.append(dict(normal=normal,width=width,full_width=4,positive=True,narrow_span=False,private_buffer=False,public_overlap=False))
        # Globally connected U, but the lower member's slices require exit/reentry.
        routes=[dict(rects=bands([[20,20],[20,64],[60,64],[60,20]],3))]
        with self.assertRaisesRegex(GenerationError,'inside its member chunk'):local_connectivity(routes,[0,0,160,86])
        self.evidence('g8-frontage-fixtures.json',observed)

    def test_independent_layout_and_parent_policy_versions(self):
        observed=[]
        for legacy_layout,policy in ((False,'mixed'),(False,'single'),(False,'zero'),(True,'mixed'),(True,'single')):
            d=self.data_copy()
            if legacy_layout:d.g3_config['version']=2;d.g3_config.pop('settlement_layout_version');d.g3_config.pop('country_network_version')
            if policy=='single':d.poi_profiles=single_policy(d.poi_profiles)
            if policy=='zero':d.poi_profiles.update(minimum=0,maximum=0,kind_minimum=dict(single=0,compound=0))
            w=self.world_for(d);expected=5 if legacy_layout and policy=='mixed' else 4 if legacy_layout else 7
            self.assertEqual(w.plan['version'],expected);validate_plan(w.plan,128,128)
            if policy=='zero':self.assertEqual(w.plan['sites'],[])
            if not legacy_layout:self.assertTrue(w.plan['public_spaces'])
            observed.append(dict(legacy_layout=legacy_layout,poi=policy,version=w.plan['version'],origin=w.plan['generation_revision']))
        self.evidence('g8-policy-combinations.json',observed)

    def test_invalid_geometry_and_atomic_required_capacity_failure(self):
        d=self.data_copy();d.settlement_layouts['grid'][0]['common']['rect'][2]=1000
        with self.assertRaisesRegex(GenerationError,'common'):validate(d.settlement_layouts,d)
        d=self.data_copy()
        for layout in d.settlement_layouts['grid']:layout['civic_lot']['bounds'][2]=layout['civic_lot']['bounds'][0]+3
        w=WorldMap(128,128);w.seed=20261023;before=copy.deepcopy(vars(w))
        with self.assertRaisesRegex(GenerationError,'layout alternatives exhausted'):generate_world(w,d,random.Random(0))
        self.assertEqual(vars(w),before)


if __name__=='__main__':unittest.main()
