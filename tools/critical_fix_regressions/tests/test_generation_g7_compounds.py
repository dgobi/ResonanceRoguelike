"""Resolved compound geometry, strict ownership and actual saved-scene boundaries."""
import copy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import unittest
import zipfile
from unittest.mock import patch
import pygame
from test_effect_persistence import load_data,make_engine
import test_generation_g4 as gameplay
import test_generation_g3_lifecycle as lifecycle
import test_generation_g4_interactions as interactions
from generation.context import GenerationError
from generation.compounds import validate_recipe,certify,fit,geometry,connected_cells
from generation.compound_preview import preview
from generation.parent_selection import resolve,eligible
from generation.world_plan import Reservations,settings,validate_plan,bands,cells
from generation.world_gen import generate_world
from generation.placement import digest,dependencies
from world.world_map import WorldMap
from engine.save_manager import _serialize_world,_serialize_player
from engine.checkpoints import record
from engine.engine import GameMode
from g1_support import fingerprint

ROOT=Path(__file__).resolve().parents[3]
FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/g7'


class G7Compounds(unittest.TestCase):
    setUpClass=classmethod(gameplay.G4Gameplay.setUpClass.__func__)
    setUp=gameplay.G4Gameplay.setUp
    scene=gameplay.G4Gameplay.scene
    boot=lifecycle.G3Lifecycle.boot
    visit=interactions.G4Interactions.visit
    interact=interactions.G4Interactions.interact
    render=interactions.G4Interactions.render

    def evidence(self,name,record):
        out=Path(os.environ.get('RESONANCE_TEST_EVIDENCE_DIR',self.root))
        (out/name).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')

    def data_copy(self):
        data=copy.copy(self.data);data.compounds=copy.deepcopy(self.data.compounds);data.poi_profiles=copy.deepcopy(self.data.poi_profiles);data.structures=copy.deepcopy(self.data.structures)
        return data

    def world_for(self,data,seed=20261023):
        w=WorldMap(128,128);w.seed=seed;generate_world(w,data,random.Random(99));return w

    def controlled(self,same=False):
        data=self.data_copy();recipe=copy.deepcopy(data.compounds['wayside_shrine_court'])
        if same:
            recipe['id']='twin_offerings';recipe['slots'][1]['assets']=[dict(asset='roadside_shrine_a',weight=1)]
            data.compounds[recipe['id']]=recipe
        data.poi_profiles.update(minimum=2,maximum=2,kind_minimum=dict(single=0,compound=2),choices=[dict(kind='compound',recipe=recipe['id'],weight=1,cap=2)])
        return data

    def boot_data(self,data):
        import main
        with patch.object(main,'DataLoader',return_value=data):return self.boot()

    def test_all_recipe_rotations_full_population_and_optional_admission_omission(self):
        observations=[]
        for recipe in self.data.compounds.values():
            for rotation in recipe['rotations']:
                normal=geometry(recipe,rotation)['gate']['normal']
                result=preview(self.data,20261023,recipe,normal=normal,rotation=rotation)
                site=result['plan']['sites'][0];self.assertEqual(site['rotation'],rotation)
                self.assertTrue(all(s['placement'] for s in site['slots']))
                for slot in site['slots']:
                    p=next(p for p in result['plan']['placements'] if p['id']==slot['placement'])
                    self.assertIn(p['rotation'],self.data.structures[p['asset']]['placement']['rotations']);self.assertIsNone(p['road'])
                    self.assertEqual(p['access']['path'],slot['path']);self.assertTrue(slot['goals'])
                receipts=result['previews'][0]['receipts'];self.assertTrue(receipts)
                self.assertTrue(all(any(r['record_id'].startswith(s['placement']+':') for r in receipts) for s in site['slots']))
                observations.append(dict(recipe=recipe['id'],rotation=rotation,normal=normal,site=site,receipts=receipts))
        self.assertEqual({o['normal'] for o in observations},set('NESW'))
        for mode in ('capacity','budget'):
            recipe=copy.deepcopy(self.data.compounds['homestead_workyard'])
            if mode=='capacity':recipe['slots'][2]['buildable']=[27,0,44,2]
            else:recipe['fit_budget']=2
            result=preview(self.data,20261023,recipe,normal='S');site=result['plan']['sites'][0]
            self.assertIsNone(site['slots'][2]['placement']);self.assertIsNotNone(site['slots'][2]['omission'])
            self.assertFalse(any('stores' in r['owner'] for r in result['plan']['reservations']))
            self.assertNotIn(site['id']+'-slot-stores-building',next(r['members'] for r in result['plan']['reservations'] if r['owner']==site['id'] and r['purpose']=='envelope'))
            observations.append(dict(optional_omission=mode,site=site))
        self.evidence('g7-recipe-transforms.json',observations)

    def test_recipe_validation_negative_authored_definitions(self):
        changes=[('unknown child',lambda r:r['slots'][0]['assets'][0].update(asset='absent')),
            ('weight',lambda r:r['slots'][0]['assets'][0].update(weight=float('nan'))),
            ('duplicate slot',lambda r:r['slots'][1].update(id=r['slots'][0]['id'])),
            ('missing path',lambda r:r['slots'][0].update(path='foreign')),
            ('out of envelope',lambda r:r['slots'][0].update(buildable=[-1,0,8,8])),
            ('private overlap',lambda r:r['slots'][1].update(buildable=r['slots'][0]['buildable'])),
            ('common space',lambda r:r['slots'][0].update(buildable=[0,0,8,12])),
            ('disconnected path',lambda r:r['paths'][0].update(rects=[[1,8,7,10],[8,11,17,14]])),
            ('blocked gate',lambda r:r['gate'].update(x=0,y=0,normal='N',width=1)),
            ('unbounded budget',lambda r:r.update(fit_budget=999999)),
            ('forbidden transform',lambda r:r['slots'][0].update(assets=[dict(asset='house_hearth_a',weight=1)]))]
        observations=[]
        for name,change in changes:
            raw=copy.deepcopy(self.data.compounds['wayside_shrine_court']);change(raw)
            with self.subTest(name=name),self.assertRaises(GenerationError) as error:certify(validate_recipe(raw,self.data),self.data,settings(self.data))
            observations.append(dict(case=name,error=str(error.exception)))
        data=self.data_copy()
        for t in data.structures['roadside_shrine_a']['placement']['targets']:t['required']=False
        with self.assertRaisesRegex(GenerationError,'compound.*child slot.*required usable target'):validate_recipe(data.compounds['wayside_shrine_court'],data)
        self.evidence('g7-invalid-recipes.json',observations)

    def test_kind_policy_feasibility_weights_caps_and_explicit_opt_out(self):
        for changes in (dict(kind_minimum=dict(single=1,compound=2)),dict(kind_minimum=dict(single=True,compound=1)),dict(choices=[dict(kind='single',asset='hunter_cabin',weight=1,cap=2)]),dict(fit_budget=0)):
            data=self.data_copy();data.poi_profiles.update(changes)
            with self.subTest(changes=changes),self.assertRaises(GenerationError):resolve(data)
        data=self.data_copy();data.poi_profiles.update(minimum=0,maximum=0,kind_minimum=dict(single=0,compound=0))
        self.assertEqual(self.world_for(data).plan['sites'],[])
        data=self.controlled();w=self.world_for(data);self.assertEqual(len(w.plan['sites']),2)
        self.assertTrue(all(s['kind']=='compound' for s in w.plan['sites']))
        self.assertFalse(eligible(w.plan,[0,0]))
        p=copy.deepcopy(w.plan);p['sites']=p['sites'][:1]
        self.assertAlmostEqual(eligible(p,p['sites'][0]['attachment']['join'])[0][1],.2)
        self.assertEqual(len([p for p in w.plan['plots'] if p['owner']=='landmark']),1)

    def test_independent_geometry_and_narrow_reservation_permissions(self):
        pts={(0,0),(1,0),(2,1),(3,1)}
        self.assertEqual(connected_cells(pts,(0,0)),{(0,0),(1,0)})
        a=Reservations();a.add('parent','envelope',[0,0,20,20],members=['parent','child-a','child-b','path'],gate=[9,19,11,20])
        a.add('path','path',[0,10,20,12],container='parent')
        a.add('child-a','structure',[1,1,7,8],container='parent')
        a.add('child-a','approach',[3,7,4,11],('child-a',),container='parent',public_road='path',public_rects=[[0,10,20,12]])
        for owner,purpose,rect in [('child-b','structure',[6,1,9,8]),('foreign','structure',[12,1,15,8]),('child-b','structure',[18,1,21,8]),('child-b','structure',[10,8,15,11])]:
            with self.subTest(owner=owner,rect=rect),self.assertRaises(GenerationError):a.add(owner,purpose,rect,container='parent')
        a.add('child-b','structure',[12,1,18,8],container='parent')
        self.assertFalse(a.conflicts([12,12,13,13],container='parent',member='child-b'))

    def test_required_child_and_parent_budget_fail_without_state_residue(self):
        data=self.data_copy();data.poi_profiles['fit_budget']=1;w=WorldMap(128,128);w.seed=20261023;before=copy.deepcopy(vars(w))
        with self.assertRaisesRegex(GenerationError,'POI minimum failure'):generate_world(w,data,random.Random(0))
        self.assertEqual(vars(w),before)
        r=validate_recipe(self.data.compounds['wayside_shrine_court'],self.data);c=settings(self.data)
        road=dict(id='r',kind='country',width=3,points=[[0,21],[79,21]],rects=bands([[0,21],[79,21]],3))
        p=dict(seed=0,settings=c,routes=[road],crossings=[],paths=[],plots=[],placements=[],dependencies={},poi_policy=dict(id='test'))
        a=Reservations();a.add('r','road',road['rects'][0]);before=copy.deepcopy((p,a.rows,a.index))
        candidate=dict(join=[40,21],normal='S',road='r',segment=0,tangent=[1,0],side='north')
        result,work=fit(p,a,self.data,r,candidate,'parent',0,1)
        self.assertIsNone(result);self.assertEqual(work['child_trials'],1);self.assertTrue(work['budget_exhausted']);self.assertEqual((p,a.rows,a.index),before)
        with patch('generation.world_plan.dependencies',side_effect=GenerationError('late dependency rejection')):
            result,work=fit(p,a,self.data,r,candidate,'parent',0,24)
        self.assertIsNone(result);self.assertEqual((p,a.rows,a.index),before)
        self.evidence('g7-atomic-fit.json',dict(failed_work=work,unchanged=True))

    def test_canonical_memberships_process_hash_seeds_and_irrelevant_history(self):
        data=self.data_copy();data.poi_profiles['choices'].reverse();data.poi_profiles['locations'].reverse()
        for r in data.compounds.values():
            r['paths'].reverse();r['rotations'].reverse()
            for s in r['slots']:s['assets'].reverse();s['rotations'].reverse()
        random.seed(817);[random.random() for _ in range(200)]
        self.assertEqual(digest(self.world_for(data).plan),digest(self.world.plan))
        script='import contextlib,io,random; from engine.data_loader import DataLoader; from generation.world_gen import generate_world; from generation.placement import digest; from world.world_map import WorldMap\nwith contextlib.redirect_stdout(io.StringIO()):\n d=DataLoader("roguelike/data"); w=WorldMap(128,128); w.seed=20261023; generate_world(w,d,random.Random(222))\nprint(digest(w.plan))'
        outputs=[]
        for seed in ('0','1','999'):
            env=dict(os.environ,PYTHONHASHSEED=seed,PYTHONPATH=str(ROOT/'roguelike'))
            result=subprocess.run([sys.executable,'-X','utf8','-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr);outputs.append(result.stdout.strip())
        self.assertEqual(outputs,[digest(self.world.plan)]*3)
        self.evidence('g7-hash-seeds.json',dict(hash_seeds=[0,1,999],identities=outputs))

    def test_checksum_consistent_corruption_rejected_before_installation(self):
        e=self.boot_data(self.controlled());self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        checkpoint=e.save_manager.checkpoint_path();original=(checkpoint/'world.json').read_bytes();manifest=json.loads((checkpoint/'manifest.json').read_bytes())
        changes=[('foreign child',lambda p:p['sites'][0]['slots'][0].update(placement=p['sites'][1]['slots'][0]['placement'])),
            ('missing slot',lambda p:p['sites'][0]['slots'].pop(0)),('duplicate parent',lambda p:p['sites'].append(copy.deepcopy(p['sites'][0]))),
            ('foreign path',lambda p:p['sites'][0]['slots'][0].update(path=p['sites'][1]['paths'][0])),
            ('foreign path owner',lambda p:p['paths'][0].update(owner=p['sites'][1]['id'])),
            ('missing path',lambda p:p['paths'].pop(0)),('wrong gate',lambda p:p['sites'][0]['gate'].update(x=0)),
            ('envelope escape',lambda p:p['sites'][0]['envelope'].__setitem__(2,p['sites'][0]['envelope'][2]-1)),
            ('required flags',lambda p:p['sites'][0]['slots'][0].update(required=False)),
            ('invalid goals',lambda p:p['sites'][0]['slots'][0].update(goals=[])),
            ('bad effective transform',lambda p:p['sites'][0]['slots'][0].update(effective_rotations=[])),
            ('wrong parent road',lambda p:p['sites'][0]['attachment'].update(road='road-0')),
            ('foreign containment',lambda p:next(r for r in p['reservations'] if r['purpose']=='envelope')['members'].append('foreign')),
            ('count tamper',lambda p:p['site_selection'].update(accepted=0))]
        active=e.local_map;world=e.world_map;head=e.save_manager.store.token();rng=e.rng.getstate();player=digest(_serialize_player(e));out=[]
        for name,change in changes:
            saved=json.loads(original);change(saved['plan']);payload=json.dumps(saved).encode();(checkpoint/'world.json').write_bytes(payload);manifest['files']['world.json']=record(payload);(checkpoint/'manifest.json').write_text(json.dumps(manifest))
            with self.subTest(name=name),self.assertRaises(ValueError) as error:e.save_manager._prepare(e,checkpoint)
            out.append(dict(case=name,error=str(error.exception)));self.assertIs(e.local_map,active);self.assertIs(e.world_map,world)
            self.assertEqual((e.save_manager.store.token(),e.rng.getstate(),digest(_serialize_player(e))),(head,rng,player))
        (checkpoint/'world.json').write_bytes(original);manifest['files']['world.json']=record(original);(checkpoint/'manifest.json').write_text(json.dumps(manifest));self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        self.evidence('g7-real-preparation-negatives.json',out)

    def test_authentic_g6_visited_pending_checkpoint_without_replanning(self):
        binding=json.loads((FIXTURES/'g6-witness.json').read_text())
        with zipfile.ZipFile(FIXTURES/'authentic-g6-checkpoint.zip') as z:
            manifest=json.loads(z.read('manifest.json'));slot=self.root/'slot_0';destination=slot/'generations'/manifest['generation'];z.extractall(destination)
        (slot/'HEAD.json').write_text(json.dumps(dict(checkpoint_version=1,current=manifest['generation'],previous=None)))
        e=make_engine(self.data)
        with patch('generation.world_plan.build_plan',side_effect=AssertionError('replanned')),patch('generation.compounds.fit',side_effect=AssertionError('recomposed')):
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error);self.assertEqual(digest(e.world_map.plan),binding['plan_identity']);self.assertEqual(e.world_map.plan['version'],4)
            visited=e._prepare_destination(*binding['visited']);self.assertEqual(fingerprint(*visited),binding['visited_fingerprint']);self.assertEqual(visited[0].generation_revision,'wg6')
            self.assertEqual(visited[0].plan_provenance,binding['visited_provenance'])
            pending=e._prepare_destination(*binding['pending']);self.assertIsNotNone(pending);self.assertEqual(pending[0].plan_provenance['adapter'],'g6-to-g7-v1')
            self.assertEqual(pending[0].generation_revision,'wg7');self.assertEqual(digest(e.world_map.plan),binding['plan_identity'])
            self.assertTrue(e.save_manager.save(e),e.save_manager.last_error);e.debug=False;e._handle_key_local(pygame.K_F9)
            self.assertEqual(fingerprint(*e._prepare_destination(*binding['visited'])),binding['visited_fingerprint'])
        self.evidence('g7-authentic-g6-restore.json',dict(plan_identity=binding['plan_identity'],visited_revision='wg6',pending_adapter='g6-to-g7-v1',mutation_preserved=True,plan_unchanged=True))

    def test_same_asset_children_and_same_recipe_parents_real_transfers_cold_and_f9(self):
        data=self.controlled(same=True);e=self.boot_data(data);e.debug=False;e.player_invincible=True;e.player.inventory.capacity=100
        sites=e.world_map.plan['sites'];self.assertEqual(len(sites),2)
        first={tuple(s['chunk']):fingerprint((r:=self.scene(s['chunk'],e.world_map)).local_map,r.actors) for s in sites}
        second={tuple(s['chunk']):fingerprint((r:=self.scene(s['chunk'],e.world_map)).local_map,r.actors) for s in reversed(sites)}
        self.assertEqual(first,second);mutations=[];states=[];items=[]
        with patch.object(type(e),'_advance_turn',lambda e:e.world_time.advance()):
            for site in reversed(sites):
                self.visit(e,site['chunk']);owned=[]
                for index,slot in enumerate(site['slots']):
                    p=next(p for p in e.world_map.plan['placements'] if p['id']==slot['placement']);target=next(t for t in p['targets'] if t['kind']=='container');xy=(target['x']%80,target['y']%43)
                    state=e.local_map.container_state[xy];before=len(state['items']);self.assertGreater(before,0);states.append(state);items.extend(state['items'])
                    self.interact(e,xy);self.assertIsNotNone(e.interaction_cursor._selection_prompt)
                    e.mode=GameMode.INTERACTION_CURSOR;e._handle_key(pygame.K_RETURN);e.mode=GameMode.LOCAL;e.interaction_cursor._selection_prompt=None
                    self.assertEqual(len(state['items']),before-1);owned.append(xy)
                    mutations.append(dict(parent=site['id'],child=p['id'],before=before,after=len(state['items']),interaction='real one-item transfer with fixture positioning'))
                self.assertIsNot(states[-1],states[-2]);self.assertIsNot(states[-1]['items'],states[-2]['items'])
                e.local_map.set_tile(2,2,'mud' if site==sites[0] else 'grass',True,True)
            self.assertEqual(len({id(i) for i in items}),len(items))
            t=time.perf_counter();e._handle_key_local(pygame.K_F5);save_seconds=time.perf_counter()-t;self.assertIsNone(e.save_manager.last_error)
            saved={tuple(s['chunk']):fingerprint(*e._prepare_destination(*s['chunk'])) for s in sites}
            for site in sites:
                m,_=e._prepare_destination(*site['chunk']);m.set_tile(2,2,'rock',False,False)
                for index,container in enumerate(m.container_state.values()):
                    if index%2:container['items'].clear()
            reader=make_engine(data);t=time.perf_counter();self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error);cold_seconds=time.perf_counter()-t
            for site in reversed(sites):self.assertEqual(fingerprint(*reader._prepare_destination(*site['chunk'])),saved[tuple(site['chunk'])])
            e._handle_key_local(pygame.K_F9);self.assertIsNone(e.save_manager.last_error)
            for site in sites:self.assertEqual(fingerprint(*e._prepare_destination(*site['chunk'])),saved[tuple(site['chunk'])])
        checkpoint=e.save_manager.checkpoint_path()
        self.evidence('g7-independent-children.json',dict(controls='two identical-recipe parents, two same-asset children per complete scene; fixture positioning, stationary turns; real transfer/save/cold-load/F9',mutations=mutations,reverse_visits=True,
            checkpoint_scope='two explored compound scenes plus actual startup scenes',scene_count=len(list((checkpoint/'chunks').glob('*.pkl'))),bytes=sum(p.stat().st_size for p in checkpoint.rglob('*') if p.is_file()),save_seconds=save_seconds,cold_seconds=cold_seconds))

    def test_saved_resolution_dependency_scope_and_late_second_child_atomicity(self):
        e=self.boot();site=next(s for s in e.world_map.plan['sites'] if s['kind']=='compound');xy=site['chunk'];children=[p for p in e.world_map.plan['placements'] if p.get('parent')==site['id']]
        state=(digest(_serialize_world(e.world_map)),digest(_serialize_player(e)),e.rng.getstate(),e.save_manager.store.token());active=e.local_map;actors=e.entities[:]
        from generation.town_gen import _stamp_building_at
        calls=[]
        def obstruct(m,raw,ox,oy,*args,**kwargs):
            rows=_stamp_building_at(m,raw,ox,oy,*args,**kwargs);calls.append(raw['id'])
            if len(calls)==2:
                a=children[0]['approach'];rows.append(dict(kind='container',decor_id='crate',loot_pools=['storage_general'],x=a[0]%80,y=a[1]%43,record_id='injected-late-child-obstruction'))
            return rows
        with patch('generation.town_gen._stamp_building_at',side_effect=obstruct):self.assertIsNone(e._prepare_destination(*xy))
        self.assertGreaterEqual(len(calls),2);self.assertIs(e.local_map,active);self.assertEqual(e.entities,actors)
        self.assertEqual((digest(_serialize_world(e.world_map)),digest(_serialize_player(e)),e.rng.getstate(),e.save_manager.store.token()),state);self.assertIsNone(e.save_manager.cache.load(*xy))
        e.data=self.data_copy();e.data.compounds={};e.data.poi_profiles={};identity=digest(e.world_map.plan)
        with patch('generation.compounds.fit',side_effect=AssertionError('recomposed')):self.assertIsNotNone(e._prepare_destination(*xy))
        asset=children[0]['asset'];e.data.structures[asset]['layers'][0]=e.data.structures[asset]['layers'][0].replace('#','.')
        self.assertIsNotNone(e._prepare_destination(*xy));self.assertEqual(digest(e.world_map.plan),identity)
        with self.assertRaisesRegex(GenerationError,'changed dependency structure:'+asset):
            from engine.scene_generation import create_surface
            create_surface(e.world_map,e.world_map.get(*xy),e.data,e.item_factory,e.creature_factory,80,43)
        unaffected=next(p for p in e.world_map.plan['sites'] if p['kind']=='single')
        if next(p['asset'] for p in e.world_map.plan['placements'] if p['id']==unaffected['placement'])!=asset:self.assertIsNotNone(e._prepare_destination(*unaffected['chunk']))
        self.evidence('g7-late-child-rollback.json',dict(stamped_children=calls,state_unchanged=True,recovered=True,resolved_plan_identity=identity,recipe_and_policy_absent_pending_succeeded=True))

    def test_ordinary_compound_updates_and_both_production_views(self):
        observations=[]
        for recipe in self.data.compounds.values():
            data=self.data_copy();data.poi_profiles.update(minimum=1,maximum=1,kind_minimum=dict(single=0,compound=1),choices=[dict(kind='compound',recipe=recipe['id'],weight=1,cap=2)])
            # A fresh disposable campaign for each controlled recipe.
            import tempfile
            with tempfile.TemporaryDirectory() as root,patch('engine.save_manager.SAVE_DIR',Path(root)):
                original=self.root;self.root=Path(root)
                try:e=self.boot_data(data)
                finally:self.root=original
                e.debug=False;e.player_invincible=True;e.rng=random.Random(20261023);site=e.world_map.plan['sites'][0];self.visit(e,site['chunk'])
                self.assertIsNone(e.world_map.get(*site['chunk']).town_data);self.assertIsNone(e.local_map.native_generation_context)
                turn=e.world_time.turn
                for _ in range(8):e._handle_key_local(pygame.K_z)
                self.assertEqual(e.world_time.turn,turn+8)
                out=Path(os.environ.get('RESONANCE_TEST_EVIDENCE_DIR',self.root))
                from g7_visuals import render_compound
                render_compound(e,site,out/('g7-'+recipe['id']+'-production.png'))
                observations.append(dict(recipe=recipe['id'],site=site['id'],native_turns=8,controls='controlled recipe selection; fixture travel; ordinary AI/survival enabled, player invincible; actual production renderer at full-chunk review zoom, visibility revealed for overview only'))
        self.evidence('g7-native-views.json',observations)
