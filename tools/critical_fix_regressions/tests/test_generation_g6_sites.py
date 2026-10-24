"""G6 policy, independent physical oracles, assigned contents and save ownership."""
import copy
import gzip
import json
import os
from pathlib import Path
import random
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
from generation.placement import digest,transform
from generation.poi_selection import resolve,eligible,candidates,populate,junctions,single_policy
from generation.road_network import PhysicalRoads
from generation.world_plan import validate_plan,bands,address,Reservations,member_chunks
from generation.world_gen import generate_world
from generation.poi_preview import site_preview
from generation.structure_preview import preview
from world.world_map import WorldMap
from engine.checkpoints import record
from engine.engine import GameMode
from engine.save_manager import _serialize_world
from g1_support import fingerprint

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/g6'


class G6Network(unittest.TestCase):
    def graph(self,rows,bridge=None):
        return PhysicalRoads(dict(routes=[dict(rects=bands(points,width)) for points,width in rows],
                                  crossings=[dict(deck=[bridge])] if bridge else []))

    def test_independent_physical_oracles(self):
        cases=[('T',[([[0,0],[8,0]],1),([[4,0],[4,4]],1)],1,(0,0),(4,4),8),
               ('cross',[([[0,2],[8,2]],1),([[4,0],[4,4]],1)],1,(0,2),(4,4),6),
               ('band-only',[([[0,0],[4,0]],3),([[5,1],[5,4]],3)],1,(0,0),(5,4),9),
               ('retraced',[([[0,0],[8,0],[0,0]],1)],1,(0,0),(8,0),8),
               ('disconnected',[([[0,0],[3,0]],1),([[5,0],[8,0]],1)],2,(0,0),(8,0),None),
               ('corner-only',[([[0,0],[3,0]],1),([[4,1],[4,4]],1)],2,(0,0),(4,4),None)]
        for name,rows,components,start,end,length in cases:
            with self.subTest(name=name):
                graph=self.graph(rows);self.assertEqual(len(graph.component_sizes),components)
                self.assertEqual(graph.connected(start,end),length is not None)
                if length is not None:self.assertEqual(len(graph.path(start,end))-1,length)
        graph=self.graph([([[0,0],[3,0]],1),([[5,0],[8,0]],1)],bridge=[3,0,6,1])
        self.assertEqual(len(graph.component_sizes),1);self.assertEqual(len(graph.path((0,0),(8,0)))-1,8)


class G6Sites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_effect_persistence import load_data
        cls.data=load_data();cls.data.poi_profiles=single_policy(cls.data.poi_profiles)
        cls.world=WorldMap(128,128);cls.world.seed=20261023;generate_world(cls.world,cls.data,random.Random(0))
    setUp=gameplay.G4Gameplay.setUp
    scene=gameplay.G4Gameplay.scene
    def boot(self):
        import main
        # This suite explicitly retains G6 single-site policy semantics. Current
        # materialization still runs, including historical adapter assertions.
        with patch.object(main,'DataLoader',return_value=self.data):return lifecycle.G3Lifecycle.boot(self)
    visit=interactions.G4Interactions.visit
    interact=interactions.G4Interactions.interact
    render=interactions.G4Interactions.render

    def data_policy(self,**changes):
        data=copy.copy(self.data);data.poi_profiles=copy.deepcopy(self.data.poi_profiles);data.poi_profiles.update(changes)
        return data

    def world_for(self,data,seed=20261023):
        world=WorldMap(128,128);world.seed=seed;generate_world(world,data,random.Random(9));return world

    def test_policy_ranges_caps_and_valid_cap_limited_shortfall(self):
        for key,value in [('minimum',True),('minimum',5),('maximum',9),('fit_budget',0),('enumeration_limit',float('inf')),('repeat_multiplier',float('nan')),('locations',['town'])]:
            with self.subTest(key=key),self.assertRaises(GenerationError):resolve(self.data_policy(**{key:value}))
        for rule in [dict(asset='missing',weight=1,cap=2),dict(asset='hunter_cabin',weight=0,cap=2),dict(asset='hunter_cabin',weight=1,cap=True),dict(asset='hunter_cabin',weight=1,cap=1)]:
            with self.subTest(rule=rule),self.assertRaises(GenerationError):resolve(self.data_policy(assets=[rule]))
        # A cap total below desired is valid when the minimum can still be met.
        data=self.data_policy(assets=[dict(asset='hunter_cabin',weight=1,cap=2)],minimum=2,maximum=4)
        observed=[]
        for seed in (0,20261023,29417):
            plan=self.world_for(data,seed).plan;observed.append(plan['site_selection'])
            self.assertEqual(len(plan['sites']),2)
            self.assertEqual(len({s['chunk'][0]*128+s['chunk'][1] for s in plan['sites']}),2)
            if plan['site_selection']['desired']>2:self.assertEqual(plan['site_selection']['shortfall_reason'],'hard cohort caps exhausted')
        self.assertTrue(any(r['desired']>2 for r in observed))
        plan=self.world_for(self.data_policy(fit_budget=2)).plan
        self.assertEqual((plan['site_selection']['desired'],len(plan['sites'])),(3,2))
        self.assertEqual(plan['site_selection']['shortfall_reason'],'fit budget exhausted')

    def test_minimum_failure_publishes_no_world_and_zero_is_explicit(self):
        data=self.data_policy(fit_budget=1);world=WorldMap(128,128);world.seed=20261023;before=copy.deepcopy(vars(world))
        with self.assertRaisesRegex(GenerationError,'POI minimum failure'):generate_world(world,data,random.Random(0))
        self.assertEqual(vars(world),before)
        zero=self.world_for(self.data_policy(minimum=0,maximum=0))
        self.assertEqual(zero.plan['sites'],[]);self.assertEqual(zero.plan['site_selection']['desired'],0)

    def test_fitter_dependency_failure_has_no_orphan_reservations(self):
        from generation.world_plan import _plot
        plan,authority=gameplay.G4Placement.fixture(self);before=copy.deepcopy(authority.rows)
        with patch('generation.world_plan.dependencies',side_effect=GenerationError('controlled consumed-definition failure')):
            plot=_plot(plan,authority,self.data,'fixture','grid',0,0,20,21,'S','assigned')
        self.assertIsNone(plot['placement']);self.assertEqual(plan['placements'],[]);self.assertEqual(plan['dependencies'],{})
        self.assertEqual(authority.rows,before)

    def test_equivalent_memberships_candidates_and_nearest_repeat(self):
        data=self.data_policy();data.poi_profiles['assets'].reverse();data.poi_profiles['locations'].reverse()
        self.assertEqual(digest(self.world_for(data).plan),digest(self.world.plan))
        plan=self.world.plan;rows,stats=candidates(plan,plan['poi_policy'])
        other=copy.deepcopy(plan);other['routes'].reverse()
        self.assertEqual((rows,stats),candidates(other,other['poi_policy']))
        p=copy.deepcopy(plan);p['poi_policy']['assets']=[dict(asset='hunter_cabin',base_weight=2,weight=3,cap=2),dict(asset='shepherds_hut_a',base_weight=1,weight=1,cap=2)]
        p['poi_policy']['repeat_multiplier']=.2
        p['placements']=[dict(id='one',asset='hunter_cabin'),dict(id='two',asset='shepherds_hut_a')]
        p['sites']=[dict(id='site-a',placement='one',attachment=dict(join=[10,10])),dict(id='site-b',placement='two',attachment=dict(join=[30,10]))]
        weights={a:w for a,w,_ in eligible(p,[20,10])}
        self.assertAlmostEqual(weights['hunter_cabin'],1.2);self.assertEqual(weights['shepherds_hut_a'],1)
        p['sites'].append(dict(id='site-c',placement='one',attachment=dict(join=[50,10])))
        self.assertNotIn('hunter_cabin',[r[0] for r in eligible(p,[10,10])])
        self.assertEqual(len(junctions(dict(routes=[dict(id='r',kind='country',width=3,points=[[0,0],[8,0],[0,0]])]))),0)

    def test_all_initial_assets_direct_transforms_and_assigned_normals(self):
        observations=[]
        for rule in self.data.poi_profiles['assets']:
            raw=self.data.structures[rule['asset']]
            for rotation in raw['placement']['rotations']:
                for mirror in ([False,True] if raw['placement']['mirror_x'] else [False]):
                    moved=transform(raw,rotation,mirror);e=next(e for e in moved['placement']['entrances'] if e['required'])
                    report,_,_=preview(moved,'ordinary_building',self.data,category='wilderness',expectations=dict(entry=dict(x=e['x'],y=e['y']),targets=moved['placement']['targets']))
                    self.assertTrue(report['passed']);observations.append(dict(asset=raw['id'],rotation=rotation,mirror=mirror,kind='direct'))
            for normal in 'NESW':
                result=site_preview(self.data,20261023,raw,normal=normal)
                self.assertEqual(len(result['plan']['sites']),1);self.assertTrue(result['passed'])
                site=result['plan']['sites'][0];self.assertEqual(site['attachment']['normal'],normal)
                self.assertTrue(result['previews'][0]['receipts']);observations.append(dict(asset=raw['id'],normal=normal,kind='complete assigned site',site=site))
        if os.environ.get('RESONANCE_TEST_EVIDENCE_DIR'):
            (Path(os.environ['RESONANCE_TEST_EVIDENCE_DIR'])/'g6-cohort.json').write_text(json.dumps(observations,indent=2)+'\n')

    def test_malformed_sites_fail_real_preparation_with_valid_checksums(self):
        e=self.boot();self.assertTrue(e.save_manager.save(e));checkpoint=e.save_manager.checkpoint_path()
        original=(checkpoint/'world.json').read_bytes();manifest=json.loads((checkpoint/'manifest.json').read_bytes())
        changes=[lambda p:p.pop('sites'),lambda p:p['sites'].append(copy.deepcopy(p['sites'][0])),
            lambda p:p['sites'].pop(),lambda p:p['sites'][0].update(profile='other'),
            lambda p:p['sites'][0].update(chunk=p['sites'][1]['chunk']),lambda p:p['sites'][0].update(goal=True),
            lambda p:p['sites'][0]['attachment'].update(road='road-0'),lambda p:p['sites'][0]['attachment'].update(segment=999999),
            lambda p:p['sites'][0]['attachment'].update(join=[0,0]),lambda p:p['sites'][0]['attachment'].update(side='other'),
            lambda p:p['plots'].append(dict(p['plots'][-1],id='orphan-site-plot')),lambda p:p['nodes'].append(dict(p['nodes'][-1],id='site-orphan'))]
        head=e.save_manager.store.token();active=e.local_map;world=e.world_map
        for change in changes:
            saved=json.loads(original);change(saved['plan']);payload=json.dumps(saved).encode()
            (checkpoint/'world.json').write_bytes(payload);manifest['files']['world.json']=record(payload)
            (checkpoint/'manifest.json').write_text(json.dumps(manifest))
            with self.subTest(change=change),self.assertRaises(ValueError):e.save_manager._prepare(e,checkpoint)
            self.assertIs(e.local_map,active);self.assertIs(e.world_map,world);self.assertEqual(e.save_manager.store.token(),head)

    def test_blocked_required_service_and_content_on_primary_approach(self):
        source=Path(__file__).resolve().parents[3]/'roguelike/docs/examples/g5_landmark.json'
        for entrance_id in ('main','service'):
            raw=json.loads(source.read_text());e=next(e for e in raw['placement']['entrances'] if e['id']==entrance_id)
            row=raw['layers'][e['y']];raw['layers'][e['y']]=row[:e['x']]+'.'+row[e['x']+1:]
            raw['special_tiles'].append(dict(type='container',x=e['x'],y=e['y'],decor_id='coffer',loot_pools=['shrine_offering']))
            with self.subTest(entrance=entrance_id),self.assertRaisesRegex(GenerationError,'approach is blocked|entrance span is inaccessible'):
                site_preview(self.data,20261023,raw,normal='S')

    def test_authentic_g5_checkpoint_and_pending_adapter_without_replanning(self):
        binding=json.loads((FIXTURES/'g5-witness.json').read_text())
        with zipfile.ZipFile(FIXTURES/'authentic-g5-checkpoint.zip') as z:
            manifest=json.loads(z.read('manifest.json'));slot=self.root/'slot_0';destination=slot/'generations'/manifest['generation']
            z.extractall(destination)
        (slot/'HEAD.json').write_text(json.dumps(dict(checkpoint_version=1,current=manifest['generation'],previous=None)))
        e=make_engine(self.data)
        with patch('generation.world_plan.build_plan',side_effect=AssertionError('replanned')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
            self.assertEqual(digest(e.world_map.plan),binding['plan_identity']);self.assertNotIn('sites',e.world_map.plan)
            visited=e._prepare_destination(*binding['visited'])
            self.assertEqual(fingerprint(*visited),binding['visited_fingerprint'])
            self.assertEqual(visited[0].generation_revision,'wg5');self.assertEqual(visited[0].plan_provenance['adapter'],'g5-v1')
            pending=e._prepare_destination(*binding['pending']);self.assertIsNotNone(pending)
            self.assertEqual(pending[0].plan_provenance['adapter'],'g5-to-g8-v1')
            self.assertEqual(digest(e.world_map.plan),binding['plan_identity'])
            self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
            e.debug=False;e._handle_key_local(pygame.K_F9);self.assertIsNone(e.save_manager.last_error)
            self.assertEqual(fingerprint(*e._prepare_destination(*binding['visited'])),binding['visited_fingerprint'])

    def test_same_asset_independence_reverse_visits_real_transfers_cold_and_f9(self):
        data=self.data_policy(minimum=2,maximum=2,assets=[dict(asset='roadside_shrine_a',weight=1,cap=2)])
        import main
        with patch.object(main,'DataLoader',return_value=data):e=lifecycle.G3Lifecycle.boot(self)
        e.debug=False;e.player_invincible=True;e.player.inventory.capacity=100
        sites=e.world_map.plan['sites'];self.assertEqual(len(sites),2)
        first={tuple(s['chunk']):fingerprint((r:=self.scene(s['chunk'],e.world_map)).local_map,r.actors) for s in sites}
        second={tuple(s['chunk']):fingerprint((r:=self.scene(s['chunk'],e.world_map)).local_map,r.actors) for s in reversed(sites)}
        self.assertEqual(first,second);observations=[];owned=[]
        with patch.object(type(e),'_advance_turn',lambda e:e.world_time.advance()):
            for i,site in enumerate(reversed(sites)):
                self.visit(e,site['chunk']);p=next(p for p in e.world_map.plan['placements'] if p['id']==site['placement'])
                target=next(t for t in p['targets'] if t['kind']=='container');xy=(target['x']%80,target['y']%43)
                state=e.local_map.container_state[xy];before=len(state['items']);self.assertGreater(before,0)
                self.interact(e,xy);self.assertIsNotNone(e.interaction_cursor._selection_prompt)
                e.mode=GameMode.INTERACTION_CURSOR;e._handle_key(pygame.K_RETURN);e.mode=GameMode.LOCAL;e.interaction_cursor._selection_prompt=None
                self.assertLess(len(state['items']),before);owned.append(state)
                e.local_map.set_tile(2,2,'mud' if i==0 else 'grass',True,True)
                out=Path(os.environ.get('RESONANCE_TEST_EVIDENCE_DIR',self.root))
                self.render(e,out/f'g6-site-{i}-production.png')
                observations.append(dict(site=site['id'],chunk=site['chunk'],before=before,remaining=len(state['items'])))
            self.assertIsNot(owned[0],owned[1]);self.assertIsNot(owned[0]['items'],owned[1]['items'])
            started=time.perf_counter();e._handle_key_local(pygame.K_F5);self.assertIsNone(e.save_manager.last_error)
            checkpoint_seconds=time.perf_counter()-started
            saved={tuple(s['chunk']):fingerprint(*e._prepare_destination(*s['chunk'])) for s in sites}
            for s in sites:e._prepare_destination(*s['chunk'])[0].set_tile(2,2,'rock',False,False)
            reader=make_engine(data);started=time.perf_counter();self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
            cold_seconds=time.perf_counter()-started
            for s in sites:self.assertEqual(fingerprint(*reader._prepare_destination(*s['chunk'])),saved[tuple(s['chunk'])])
            e._handle_key_local(pygame.K_F9)
            for s in sites:self.assertEqual(fingerprint(*e._prepare_destination(*s['chunk'])),saved[tuple(s['chunk'])])
            (out/'g6-independent-owners.json').write_text(json.dumps(dict(controls='two-shrine policy, fixture teleport/positioning, stationary AI; real content transfer, travel, F5/F9 and cold load',sites=observations,
                checkpoint_scope='explored two-site controlled campaign',scene_count=sum(1 for _ in (e.save_manager.checkpoint_path()/'chunks').glob('*.pkl')),
                checkpoint_seconds=checkpoint_seconds,cold_seconds=cold_seconds,checkpoint_bytes=sum(p.stat().st_size for p in e.save_manager.checkpoint_path().rglob('*') if p.is_file())),indent=2)+'\n')

    def test_saved_policy_pending_dependencies_and_late_failure_atomicity(self):
        e=self.boot();sites=e.world_map.plan['sites'];site=sites[0];xy=tuple(site['chunk']);p=next(p for p in e.world_map.plan['placements'] if p['id']==site['placement'])
        before=digest(_serialize_world(e.world_map));head=e.save_manager.store.token();active=e.local_map;actors=e.entities[:]
        with patch('generation.planned_scene.validate_access',side_effect=GenerationError('late site access failure')):self.assertIsNone(e._prepare_destination(*xy))
        self.assertEqual(digest(_serialize_world(e.world_map)),before);self.assertEqual(e.save_manager.store.token(),head)
        self.assertIs(e.local_map,active);self.assertEqual(e.entities,actors);self.assertIsNone(e.save_manager.cache.load(*xy))
        identity=digest(e.world_map.plan);e.data.poi_profiles={}
        self.assertIsNotNone(e._prepare_destination(*xy));self.assertEqual(digest(e.world_map.plan),identity)
        e.data=copy.copy(e.data);e.data.structures=copy.deepcopy(e.data.structures)
        e.data.structures[p['asset']]['layers'][0]=e.data.structures[p['asset']]['layers'][0].replace('#','.')
        self.assertIsNotNone(e._prepare_destination(*xy))
        other=next(s for s in sites if s!=site);other_p=next(p for p in e.world_map.plan['placements'] if p['id']==other['placement'])
        if other_p['asset']!=p['asset']:self.assertIsNotNone(e._prepare_destination(*other['chunk']))
        pending=copy.deepcopy(e.world_map)
        from engine.scene_generation import create_surface
        from engine.item_factory import ItemFactory
        from engine.creature_factory import CreatureFactory
        with self.assertRaisesRegex(GenerationError,'changed dependency structure:'+p['asset']):
            create_surface(pending,pending.get(*xy),e.data,ItemFactory(e.data),CreatureFactory(e.data),80,43)

    def test_rural_sites_have_ordinary_updates_without_town_ownership(self):
        e=self.boot();e.debug=False;e.player_invincible=True;e.rng=random.Random(20261023)
        site=e.world_map.plan['sites'][0];self.visit(e,site['chunk']);chunk=e.world_map.get(*site['chunk'])
        self.assertIsNone(chunk.town_data);self.assertIsNone(e.local_map.native_generation_context)
        turn=e.world_time.turn
        for _ in range(8):e._handle_key_local(pygame.K_z)
        self.assertEqual(e.world_time.turn,turn+8);self.assertEqual(chunk.biome_id,self.world.get(*site['chunk']).biome_id)
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        reader=make_engine(self.data);self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
        self.assertEqual(reader.world_map.plan['sites'],e.world_map.plan['sites'])
