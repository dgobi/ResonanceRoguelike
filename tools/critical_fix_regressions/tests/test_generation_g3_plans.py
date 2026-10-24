"""G3 plans, transforms, ownership, durability and final geometry regressions."""
import contextlib
import copy
import io
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_effect_persistence import load_data,make_engine,GAME_ROOT
from g1_support import fingerprint
from generation.context import GenerationError
from generation.world_gen import generate_world
from generation.world_plan import build_plan,validate_plan,slice_plan,settings,cells,intersect,Reservations,address
from generation.placement import transform,entrance_cells,dependencies,digest,check_dependencies
from generation.structure_contract import compile_structure,StructureError
from generation.planned_scene import validate_access
from engine.scene_generation import create_surface,publish_metadata
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from engine.save_manager import _serialize_world,_deserialize_world
from world.world_map import WorldMap


class G3Plans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_data(); cls.world=WorldMap(128,128); cls.world.seed=20261023
        with contextlib.redirect_stdout(io.StringIO()): generate_world(cls.world,cls.data,random.Random(7))

    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name); p=patch('engine.save_manager.SAVE_DIR',self.root);p.start();self.addCleanup(p.stop)
        cap=contextlib.redirect_stdout(io.StringIO());cap.__enter__();self.addCleanup(cap.__exit__,None,None,None)

    def scene(self,xy,world=None,data=None):
        world=world or self.world; data=data or self.data
        return create_surface(world,world.get(*xy),data,ItemFactory(data),CreatureFactory(data),80,43)

    def test_schema_references_profiles_settings_and_all_alternatives(self):
        raw=self.data.structures['house_small_a']
        for key,value in [('version',2),('rotations',[45]),('contexts',['unknown']),('buffer',False),('approach',-1)]:
            d=copy.deepcopy(raw);d['placement'][key]=value
            with self.subTest(key=key),self.assertRaises(StructureError): compile_structure(d,'ordinary_building',self.data,category='residential')
        d=copy.deepcopy(raw);d['placement']['entrances'][0]['width']=10
        with self.assertRaisesRegex(StructureError,'span'): compile_structure(d,'ordinary_building',self.data,category='residential')
        for key,value in [('settlement_count',[4,2]),('pools',{'grid':['missing']}),('route_search_nodes',False)]:
            c=copy.deepcopy(self.data.g3_config);c[key]=value
            with self.assertRaises(GenerationError): settings(self.data,c)

    def test_complete_asymmetric_transform_under_all_permissions(self):
        from generation.structure_preview import preview
        raw=copy.deepcopy(self.data.structures['house_small_a'])
        raw['decor_layer']=[[None]*10 for _ in range(8)];raw['decor_layer'][2][3]='decor_candle'
        before=copy.deepcopy(raw)
        for rotation in (0,90,180,270):
            for mirror in (False,True):
                d=transform(raw,rotation,mirror)
                self.assertEqual(sorted(''.join(d['layers'])),sorted(''.join(raw['layers'])))
                report,m,_=preview(d,'ordinary_building',self.data,category='residential')
                self.assertTrue(report['passed']);self.assertEqual(sum(v=='decor_candle' for v in m.decor.values()),1)
                self.assertEqual(sum(len(v) for v in m.floor_objects.values()),4)
                self.assertEqual(len(m.container_state),1)
                if not mirror:
                    recovered=transform(d,(360-rotation)%360)
                    self.assertEqual(recovered['layers'],raw['layers']);self.assertEqual(recovered['special_tiles'],raw['special_tiles'])
                    self.assertEqual(recovered['placement']['entrances'],raw['placement']['entrances'])
        self.assertEqual(raw,before)
        raw['unsupported']={'x':2,'y':3}
        with self.assertRaisesRegex(GenerationError,'coordinate-bearing'): transform(raw,90)

    def test_world_graph_constraints_and_lazy_shared_forms(self):
        p=self.world.plan;self.assertTrue(validate_plan(p,128,128))
        count=p['settings']['settlement_count'];self.assertTrue(count[0]<=len(p['settlements'])<=count[1])
        self.assertEqual({s['form'] for s in p['settlements']},{'grid','roadside'})
        self.assertTrue(all(len(s['members'])>1 for s in p['settlements']))
        self.assertFalse(any(c.visited or c.town_data for c in self.world.chunks.values()))
        import math
        points=[(s['bounds'][0]/80,s['bounds'][1]/43) for s in p['settlements']]
        self.assertTrue(all(math.dist(a,b)>=12 for i,a in enumerate(points) for b in points[i+1:]))
        self.assertTrue(any(math.dist(a,(self.world.start_wx,self.world.start_wy))<=10 for a in points))
        self.assertGreater(len(p['crossings']),0)
        for s in p['settlements']:
            if s['form']=='roadside': self.assertEqual(next(r for r in p['routes'] if r['id']==s['incoming'])['kind'],'country')

    def test_plan_failure_is_atomic_and_bounded(self):
        w=WorldMap(128,128);w.seed=0;before=copy.deepcopy(vars(w));c=copy.deepcopy(self.data.g3_config);c['minimum_separation_chunks']=128;c['settlement_count']=[8,8]
        with self.assertRaisesRegex(GenerationError,'infeasible'): generate_world(w,self.data,random.Random(0),planning_settings=c)
        self.assertEqual(vars(w),before)

    def test_full_width_reciprocal_roads_and_rivers_both_axes(self):
        from generation.ports import OFFSETS,OPPOSITE,mouth
        used=set()
        for xy,ch in self.world.chunks.items():
            for edge,ports in ch.edges.items():
                for port in ports:
                    axis='x' if edge in ('east','west') else 'y'; key=(axis,port.connector_type.value)
                    if key in used: continue
                    dx,dy=OFFSETS[edge]; neighbor=self.world.get(xy[0]+dx,xy[1]+dy)
                    if neighbor is None: continue
                    a,b=self.scene(xy),self.scene((neighbor.wx,neighbor.wy))
                    side=list(mouth(edge,port.position,port.width,80,43,kind=port.connector_type.value))
                    other=list(mouth(OPPOSITE[edge],port.position,port.width,80,43,kind=port.connector_type.value))
                    self.assertEqual(len(side),port.width)
                    terrain_a=[str(a.local_map.tiles[t]['terrain']) for t in side]
                    terrain_b=[str(b.local_map.tiles[t]['terrain']) for t in other]
                    self.assertEqual(terrain_a,terrain_b,(xy,edge,port,terrain_a,terrain_b));used.add(key)
                if len(used)==4: break
            if len(used)==4: break
        self.assertEqual(len(used),4)

    def test_reservations_conflicts_and_exact_assigned_frontage(self):
        r=Reservations();r.add('road','road',[0,0,10,3])
        with self.assertRaisesRegex(GenerationError,'conflicts'):r.add('building','approach',[3,2,5,8])
        p=self.world.plan['placements'][0];xy=address(*p['origin'])[:2];s=self.scene(xy);section=slice_plan(self.world.plan,*xy)
        bad=copy.deepcopy(section);bad['placements'][0]['road']='another-nearby-road'
        with self.assertRaisesRegex(GenerationError,'frontage'):validate_access(s.local_map,bad,self.data,*xy)
        join=p['join'][0]%80,p['join'][1]%43;s.local_map.decor[join]='crate'
        with self.assertRaisesRegex(GenerationError,'approach'):validate_access(s.local_map,section,self.data,*xy)

    def test_boundary_adjacent_bridge_exact_bands_both_axes_and_unassigned_water(self):
        from world.world_map import Chunk,RegionType
        for vertical in (False,True):
            w=WorldMap(2,2);w.seed=0;w.start_wx=w.start_wy=-1;w.plan_mode='shared-v1'
            for x in range(2):
                for y in range(2):w.set(Chunk(x,y,RegionType.PLAINS,0))
            water=[0,41,80,46] if vertical else [78,0,83,43]
            road=[39,21,42,65] if vertical else [40,20,121,23]
            deck=intersect(road,[water[0]-2,water[1]-2,water[2]+2,water[3]+2])
            w.plan={'waters':[{'id':'channel','rects':[water]}],'routes':[{'id':'road','rects':[road]}],
                    'crossings':[{'id':'bridge','deck':[deck]}],'placements':[]}
            pairs=((0,0),(0,1)) if vertical else ((0,0),(1,0))
            a,b=[self.scene(p,w).local_map for p in pairs]
            aa=[(x,42) for x in range(39,42)] if vertical else [(79,y) for y in range(20,23)]
            bb=[(x,0) for x in range(39,42)] if vertical else [(0,y) for y in range(20,23)]
            self.assertEqual([str(a.tiles[p]['terrain']) for p in aa],['cobblestone']*3)
            self.assertEqual([str(b.tiles[p]['terrain']) for p in bb],['cobblestone']*3)
            self.assertTrue(all(a.walkable[p] and b.walkable[q] for p,q in zip(aa,bb)))
            w.plan['crossings']=[]
            with self.assertRaisesRegex(GenerationError,'without an assigned bridge'):self.scene((0,0),w)

    def test_migrant_first_complete_scene_and_cached_mutations_do_not_respawn(self):
        from engine.save_manager import _deserialize_entities
        xy=(self.world.start_wx,self.world.start_wy)
        direct=self.scene(xy);e=make_engine(self.data);e.world_map=copy.deepcopy(self.world)
        migrant=e.creature_factory.spawn('hollow_revenant',12,12);migrant.name='G3 migrant'
        self.assertTrue(e._transfer_submap_pursuer_to_surface(migrant,*xy,'fixture'))
        cached=e.save_manager.cache.load(*xy)
        actors=_deserialize_entities(cached.entities,e);natives=[a for a in actors if a.name!='G3 migrant']
        self.assertEqual(fingerprint(cached.local_map,natives),fingerprint(direct.local_map,direct.actors))
        self.assertEqual(sum(a.name=='G3 migrant' for a in actors),1)
        cached.local_map.floor_objects.clear();cached.local_map.set_tile(2,2,'mud',True,True)
        expected=fingerprint(cached.local_map,actors)
        e.save_manager.cache.store(*xy,cached.local_map,actors);e.save_manager.cache.evict_distant(-100,-100)
        prepared=e._prepare_destination(*xy)
        self.assertEqual(fingerprint(*prepared),expected)

    def test_order_global_draws_and_complete_scene_identity(self):
        keys=[tuple(s['members'][0]) for s in self.world.plan['settlements']]
        first={xy:fingerprint((r:=self.scene(xy)).local_map,r.actors,r.metadata.town_data) for xy in keys}
        for _ in range(100):random.random()
        second={xy:fingerprint((r:=self.scene(xy)).local_map,r.actors,r.metadata.town_data) for xy in reversed(keys)}
        self.assertEqual(first,second)

    def test_late_population_failure_no_world_plan_cache_or_owner_publication(self):
        e=make_engine(self.data);e.world_map=copy.deepcopy(self.world)
        p=e.world_map.plan['placements'][0];xy=address(*p['origin'])[:2];before=digest(_serialize_world(e.world_map));active=e.local_map;actors=list(e.entities)
        with patch('engine.scene_generation.populate',side_effect=GenerationError('late injected population failure')):
            self.assertIsNone(e._prepare_destination(*xy))
        self.assertEqual(digest(_serialize_world(e.world_map)),before);self.assertIs(e.local_map,active);self.assertEqual(e.entities,actors)
        self.assertIsNone(e.save_manager.cache.load(*xy))
        self.assertIsNotNone(e._prepare_destination(*xy));self.assertIsNotNone(e.save_manager.cache.load(*xy))

    def test_saved_plan_validation_and_legacy_modes(self):
        record=_serialize_world(self.world)
        for mutation in ('missing','version','duplicate','reference','member'):
            row=copy.deepcopy(record)
            if mutation=='missing':row['plan']=None
            elif mutation=='version':row['plan']['version']=77
            elif mutation=='duplicate':row['plan']['nodes'].append(row['plan']['nodes'][0])
            elif mutation=='reference':row['plan']['placements'][0]['road']='missing'
            else:row['plan']['settlements'][0]['members']=[]
            with self.subTest(mutation=mutation),self.assertRaises((GenerationError,ValueError)): _deserialize_world(row,WorldMap(128,128))
        for revision in (None,'wg1','wg2'):
            row=copy.deepcopy(record);row.pop('plan');row.pop('plan_mode')
            if revision is None:row.pop('generation_revision')
            else:row['generation_revision']=revision
            restored=WorldMap(128,128);_deserialize_world(row,restored)
            self.assertEqual(restored.plan_mode,'legacy');self.assertIsNone(restored.plan)
            self.assertEqual(restored.generation_revision,revision or 'legacy-unversioned')

    def test_semantic_dependency_scoping(self):
        p=self.world.plan['placements'][0];asset=p['asset'];data=copy.copy(self.data);data.structures=copy.deepcopy(data.structures)
        data.structures[asset]['description']='formatting and inactive wording';data.structures[asset]['rotatable']=False
        self.assertEqual(dependencies(data.structures[asset],data),self.world.plan['dependencies'][asset])
        unused=next(k for k in data.structures if k not in self.world.plan['dependencies']);data.structures[unused]['description']='unrelated'
        check_dependencies(p,self.world.plan,data)
        data.structures[asset]['legend']['w']='floor'
        with self.assertRaisesRegex(GenerationError,'changed dependency.*restore matching'):check_dependencies(p,self.world.plan,data)
        unaffected=next(q for q in self.world.plan['placements'] if q['asset']!=asset)
        check_dependencies(unaffected,self.world.plan,data)
