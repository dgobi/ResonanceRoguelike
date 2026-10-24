"""G4 positive contracts derived from the independently reproduced G3 failures."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
from test_effect_persistence import load_data, GAME_ROOT
from generation.context import GenerationError
from generation.world_gen import generate_world, BIOME_ZONES
from generation.world_plan import address, cells, settings, bands, Reservations, _plot
from generation.placement import digest, transform
from engine.scene_generation import create_surface
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from world.world_map import WorldMap
from g1_support import fingerprint


class G4Gameplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_data(); cls.world=WorldMap(128,128); cls.world.seed=20261023
        with contextlib.redirect_stdout(io.StringIO()): generate_world(cls.world,cls.data,random.Random(0))

    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root=Path(tmp.name)
        p=patch('engine.save_manager.SAVE_DIR',self.root); p.start(); self.addCleanup(p.stop)
        cap=contextlib.redirect_stdout(io.StringIO()); cap.__enter__(); self.addCleanup(cap.__exit__,None,None,None)

    def scene(self,xy,world=None):
        w=world or self.world
        return create_surface(w,w.get(*xy),self.data,ItemFactory(self.data),CreatureFactory(self.data),80,43)

    def test_every_member_semantics_native_policy_and_determinism(self):
        observed=[]
        for s in self.world.plan['settlements']:
            for member in s['semantics']['members']:
                xy=member['chunk']; ch=self.world.get(*xy); r=self.scene(xy); native=r.local_map.native_generation_context
                self.assertEqual(ch.name,s['semantics']['name']); self.assertEqual(r.metadata.town_data.name,ch.name)
                self.assertEqual(ch.zones,BIOME_ZONES['town']); self.assertEqual(ch.town_role,member['role'])
                self.assertEqual(ch.difficulty,member['difficulty']); self.assertEqual(ch.resonance,member['resonance'])
                self.assertEqual(native['district'],member['district'])
                self.assertGreaterEqual(len(r.actors),2); self.assertLessEqual(len(r.actors),6)
                self.assertEqual(len(r.metadata.town_data.creature_spawns),len(r.actors))
                positions={(a.x,a.y) for a in r.actors}; self.assertEqual(len(positions),len(r.actors))
                self.assertFalse(positions & r.local_map.protected_cells)
                for a in r.actors:
                    self.assertTrue(r.local_map.walkable[a.x,a.y]); self.assertIsNotNone(a.ai)
                again=self.scene(xy)
                self.assertEqual(fingerprint(r.local_map,r.actors,r.metadata.town_data),fingerprint(again.local_map,again.actors,again.metadata.town_data))
                stones=[p for p,v in r.local_map.decor.items() if v=='waystone_plinth']
                prayers=[v for objects in r.local_map.floor_objects.values() for v in objects if getattr(v,'text_id','')=='waystone_prayer_a']
                self.assertEqual(len(stones),int(member['waystone'])); self.assertEqual(len(prayers),int(member['waystone']))
                observed.append(dict(form=s['form'],chunk=xy,role=member['role'],district=member['district'],actors=len(r.actors),waystones=len(stones)))
        self.assertEqual({r['form'] for r in observed},{'grid','roadside'})
        if os.environ.get('RESONANCE_TEST_EVIDENCE_DIR'):
            (Path(os.environ['RESONANCE_TEST_EVIDENCE_DIR'])/'g4-native-members.json').write_text(json.dumps(observed,indent=2)+'\n')

    def test_final_geometry_start_clay_and_late_failure(self):
        from generation.access import reachable
        start=(self.world.start_wx,self.world.start_wy); r=self.scene(start); m=r.local_map
        stones=[p for p,v in m.decor.items() if v=='waystone_plinth']; self.assertEqual(len(stones),1)
        reached=reachable(m,r.spawn,self.data)
        self.assertTrue(any((stones[0][0]+dx,stones[0][1]+dy) in reached for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))))
        self.assertEqual(len(m.submap_links),1); self.assertTrue(set(m.submap_links)<=reached)
        crossing=next(r for r in self.world.plan['routes'] if r['id']=='road-1')['points'][1]
        r=self.scene(address(*crossing)[:2]); m=r.local_map
        clay={(x,y) for x in range(80) for y in range(43) if str(m.tiles[x,y]['terrain'])=='clay_deposit'}
        self.assertGreater(len(clay),0); self.assertFalse(clay&m.protected_cells)
        for x,y in clay:
            self.assertTrue(any(m.in_bounds(x+dx,y+dy) and str(m.tiles[x+dx,y+dy]['terrain']) in ('river_water','river_bank','river_stones') for dx in range(-3,4) for dy in range(-3,4)))
        before=digest(self.world.plan); ch=self.world.get(*start); old=copy.deepcopy(vars(ch))
        with patch('generation.planned_scene.validate_access',side_effect=GenerationError('late restored-pass failure')):
            with self.assertRaisesRegex(GenerationError,'late restored'): self.scene(start)
        self.assertEqual(vars(ch),old); self.assertEqual(digest(self.world.plan),before)


class G4Placement(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=load_data()

    def fixture(self,width=3,country=3,vertical=False,data=None):
        data=data or self.data; c=settings(data); c['pools']['grid']=['house_small_a']
        c['road_width_tiles']=country; c['street_width_tiles']=width
        road=dict(id='assigned',width=width,points=[[40,0],[40,42]] if vertical else [[0,21],[79,21]])
        road['rects']=bands(road['points'],width)
        plan=dict(seed=20261023,settings=c,routes=[road],plots=[],placements=[],dependencies={})
        authority=Reservations()
        for r in road['rects']: authority.add(road['id'],'road',r)
        return plan,authority

    def test_public_sharing_both_orders_widths_and_all_normals(self):
        for normals in (('S','N'),('N','S'),('E','W'),('W','E')):
            vertical=normals[0] in ('E','W')
            for width in (1,3,4,5):
                results=[]
                for country in (1,5):
                    p,a=self.fixture(width,country,vertical)
                    for n in normals:
                        row=_plot(p,a,self.data,'fixture','grid',0,0,40 if vertical else 20,21,n,'assigned')
                        self.assertIsNotNone(row['placement'],(normals,width,country,row['rejected']))
                    shared=cells(p['placements'][0]['approach'])&cells(p['placements'][1]['approach'])
                    public=set().union(*(cells(r) for r in p['routes'][0]['rects']))
                    self.assertTrue(shared); self.assertTrue(shared<=public)
                    results.append(p['placements'])
                self.assertEqual(results[0],results[1])

    def test_private_conflicts_wrong_road_water_and_full_span(self):
        p,a=self.fixture(); _plot(p,a,self.data,'fixture','grid',0,0,20,21,'S','assigned')
        bad=_plot(p,a,self.data,'fixture','grid',0,0,20,21,'S','assigned')
        self.assertIsNone(bad['placement']); self.assertTrue(any('conflicts' in r['reason'] for r in bad['rejected']))
        a=Reservations(); a.add('street','road',[0,20,80,23]); a.add('one','approach',[20,16,21,22],public_road='street',public_rects=[[0,20,80,23]])
        with self.assertRaises(GenerationError): a.add('two','approach',[20,17,21,22],public_road='street',public_rects=[[0,20,80,23]])
        with self.assertRaises(GenerationError): a.add('two','approach',[20,21,21,28],public_road='unrelated',public_rects=[[0,20,80,23]])
        for obstacle in ('water','wrong-road'):
            p,a=self.fixture()
            if obstacle=='water': a.add('river','water',[19,17,23,19])
            else:
                p['routes'].append(dict(id='wrong',width=1,points=[[0,2],[79,2]],rects=[[0,2,80,3]]))
            r=_plot(p,a,self.data,'fixture','grid',0,0,20,21,'S','wrong' if obstacle=='wrong-road' else 'assigned')
            self.assertIsNone(r['placement'])

    def test_weighted_coordinates_every_transform_identity_and_immutability(self):
        from generation.structure_contract import compile_structure
        from generation.structure_preview import preview
        raw=copy.deepcopy(self.data.structures['house_small_a'])
        # All branches, including branches not selected, must be transformed.
        raw['special_tiles']=[dict(type='weighted',x=1,y=6,spawn_table=[dict(type='item',item_id='letter',text_id='world_graffiti_a',weight=1,**v) for v in ({},{'x':1,'y':6},{'x':1},{'y':6})])]
        source=copy.deepcopy(raw); compile_structure(raw,'ordinary_building',self.data,category='residential')
        for rotation in (0,90,180,270):
            for mirror in (False,True):
                d=transform(raw,rotation,mirror)
                x,y=(8,6) if mirror else (1,6)
                expected=((x,y),(7-y,x),(9-x,7-y),(y,9-x))[rotation//90]
                outer=d['special_tiles'][0]; self.assertEqual((outer['x'],outer['y']),expected)
                for before,child in zip(source['special_tiles'][0]['spawn_table'],outer['spawn_table']):
                    for index,key in enumerate(('x','y')):
                        self.assertEqual(key in before,key in child)
                        if key in child:self.assertEqual(child[key],expected[index])
                for child in outer['spawn_table']:
                    selected=copy.deepcopy(d); selected['special_tiles'][0]['spawn_table']=[child]
                    report,m,_=preview(selected,'ordinary_building',self.data,category='residential')
                    self.assertTrue(report['passed']); objects=[i for rows in m.floor_objects.values() for i in rows]
                    self.assertEqual(len(objects),1); self.assertEqual(objects[0].text_id,'world_graffiti_a')
                if not mirror:
                    recovered=transform(d,(-rotation)%360)
                    self.assertEqual(recovered['special_tiles'],raw['special_tiles'])
        self.assertEqual(raw,source)
        for key in ('x','y'):
            bad=copy.deepcopy(raw); bad['special_tiles'][0]['spawn_table'][-1][key]=99
            for rotation in (0,90,180,270):
                with self.assertRaisesRegex(GenerationError,'CHOICE_COORDINATE'): transform(bad,rotation,True)

    def test_mirror_required_fit_and_asset_first_weight(self):
        data=copy.copy(self.data); data.structures=copy.deepcopy(data.structures)
        raw=data.structures['house_small_a']; raw['placement']['rotations']=[0]
        # A blocker to the left of the mirror's footprint rejects only unmirrored.
        raw['placement']['entrances'][0]['x']=1
        raw['layers'][-1]='#.########'
        for permission in (True,False):
            raw['placement']['mirror_x']=permission
            p,a=self.fixture(data=data); a.add('blocker','structure',[26,10,28,17])
            r=_plot(p,a,data,'fixture','grid',0,0,20,21,'S','assigned')
            self.assertEqual(bool(r['placement']),permission,r['rejected'])
            if permission:self.assertTrue(p['placements'][0]['mirror'])
        raw['placement']['mirror_x']=True
        p,a=self.fixture(data=data)
        # Capture the asset draw's weights: two transforms must still carry one weight.
        choices=random.Random.choices; weights=[]
        def observe(rng,population,weights=None,**kwargs):
            if weights is not None: captured.append(list(weights))
            return choices(rng,population,weights=weights,**kwargs)
        captured=[]
        with patch.object(random.Random,'choices',observe): _plot(p,a,data,'fixture','grid',0,0,20,21,'S','assigned')
        self.assertEqual(captured,[[raw['placement']['weight']]])
