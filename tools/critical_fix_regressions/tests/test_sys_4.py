"""SYS-4 actual engine ownership, geometry, actions and compatibility regressions."""
import copy
import hashlib
import json
import os
import pickle
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'roguelike'))

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from engine import access_profiles as profiles, access_objects as objects, access_actions as actions
from generation.floor_object_utils import (place_container, open_container,
    get_container_items, take_from_container, place_floor_object)
from engine.item_transfers import take_container
from engine.scene_generation import populate
from engine.save_manager import SaveManager
from world.local_map import LocalMap, make_tile

ROOT=GAME_ROOT.parent


def summary(e):
    return dict(turn=e.world_time.turn, player=[e.player.x,e.player.y],
        objects={str(xy):copy.deepcopy(row) for xy,row in objects.objects(e.local_map).items()},
        tiles={str(xy):[str(e.local_map.tiles[xy]['terrain']),bool(e.local_map.walkable[xy]),bool(e.local_map.transparent[xy])]
               for xy in objects.objects(e.local_map)},
        containers={str(xy):dict(state=r['state'],items=[i.item_id if not isinstance(i,dict) else i['item_id'] for i in r['items']]) for xy,r in e.local_map.container_state.items()},
        floor={str(xy):[i.item_id for i in rows] for xy,rows in e.local_map.floor_objects.items()},
        inventory=[dict(id=i.item_id,count=i.count,dose=getattr(i,'coating_dose',None)) for i in e.player.inventory.items])


class AccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();cls.data=load_data()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='sys4-test-');self.addCleanup(self.tmp.cleanup)
        with patch('engine.save_manager.SAVE_DIR',Path(self.tmp.name)/'saves'):
            self.e=make_engine(copy.deepcopy(self.data))
        self.e.debug=False;self.e._update_fov()

    def item(self, identifier):
        value=self.e.item_factory.create(identifier)
        self.assertIsNotNone(value);self.assertTrue(self.e.player.inventory.add(value));return value

    def tool(self):
        value=self.item('binding_knife');self.e.player.equipment.equip(value,'weapon');return value

    def host(self,host='screen',xy=(13,12),p=None,contents=None):
        p=p or self.e.data.access_profiles['pale_lashings']
        if host=='container':place_container(self.e.local_map,*xy,'bound_coffer',contents or [])
        row=objects.install(self.e.local_map,xy,host,p,decor_id='bound_coffer' if host=='container' else '')
        self.e._update_fov();return row

    def act(self,method='careful',xy=(13,12),dose=None):
        return actions.perform(self.e,actions.intent(self.e,xy),method,dose,
                               (actions.dose_state(dose),dose.count) if dose else None)

    def choose(self,method='careful',xy=(13,12),dose_index=0):
        # Normal E / adjacent cursor / menu handlers, followed by normal action.
        self.e._handle_key(pygame.K_e)
        c=self.e.interaction_cursor;c._cursor_x,c._cursor_y=xy
        if self.e._vessel_menu is None:self.e._handle_key(pygame.K_RETURN)
        menu=self.e._vessel_menu;self.assertIsNotNone(menu)
        prefix={'careful':('Careful','Continue'),'force':('Quick force',),'dissolution':('Dissolution',)}[method]
        menu['selected']=next(n for n,(label,_) in enumerate(menu['options']) if label.startswith(prefix))
        self.e._handle_key(pygame.K_RETURN)
        if method=='dissolution':
            self.e._vessel_menu['selected']=dose_index;self.e._handle_key(pygame.K_RETURN)

    def test_profiles_strict_bounded_and_shared_variants(self):
        p=self.e.data.access_profiles['pale_lashings']
        for key,value in [('version',True),('version',2),('work_steps',True),('work_steps',0),('work_steps',13),
                          ('cutting_tier',1.5),('dissolution_threshold',float('nan')),('dissolution_threshold',True),
                          ('screen_careful_yield','bile_coating'),('extra',1),('host_screen',1)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):profiles.validate(dict(p,**{key:value}))
        variant=dict(p,id='different_lashing',work_steps=2)
        a=self.host('screen',p=variant);b=self.host('container',(12,11),p=variant)
        self.tool();self.assertTrue(self.act());self.assertEqual((1,0),(a['progress'],b['progress']))
        self.assertTrue(self.act());self.assertEqual('careful',a['completed_by']);self.assertIsNone(b['completed_by'])
        variant['work_steps']=8;self.assertEqual(2,a['profile']['work_steps'])

    def test_secured_container_all_access_routes_and_exact_contents(self):
        item=self.e.item_factory.create('bile_coating');row=self.host('container',contents=[item])
        owner=self.e.local_map.container_state[(13,12)];original_items=owner['items']
        self.assertFalse(open_container(self.e.local_map,13,12))
        self.assertEqual([],get_container_items(self.e.local_map,13,12,self.e.item_factory))
        self.assertFalse(take_from_container(self.e.local_map,13,12,item))
        owner['state']='open' # a stale/corrupt UI state cannot bypass the access boundary
        self.assertFalse(take_container(self.e,13,12,item));owner['state']='closed'
        self.e._interactable_container(13,12);self.assertIsNone(self.e.interaction_cursor._selection_prompt)
        self.e._handle_key(pygame.K_ESCAPE)
        self.choose('force');self.assertEqual('force',row['completed_by'])
        self.assertIs(owner,self.e.local_map.container_state[(13,12)]);self.assertIs(original_items,owner['items'])
        self.e._interactable_container(13,12)
        self.assertIs(item,self.e.interaction_cursor._selection_prompt['items'][0])
        self.e.interaction_cursor._handle_selection_key(pygame.K_RETURN,self.e)
        self.assertTrue(self.e.player.inventory.contains(item));self.assertEqual('looted',owner['state'])
        self.assertFalse(take_container(self.e,13,12,item));self.assertFalse(self.e._interactable_container(13,12))

    def test_empty_coffer_and_ordinary_crates_keep_distinct_contracts(self):
        row=self.host('container');before=self.e.world_time.turn
        self.e._interactable_container(13,12);self.assertIsNotNone(self.e._vessel_menu)
        self.e._handle_key(pygame.K_ESCAPE);self.assertEqual(before,self.e.world_time.turn)
        self.choose('force');self.assertIsNotNone(row['completed_by'])
        before=self.e.world_time.turn;self.assertFalse(self.e._interactable_container(13,12));self.assertEqual(before,self.e.world_time.turn)
        item=self.e.item_factory.create('wood_bundle');place_container(self.e.local_map,12,11,'crate',[item])
        self.assertTrue(open_container(self.e.local_map,12,11));self.assertTrue(take_container(self.e,12,11,item))

    def test_individual_steps_quiet_origin_once_and_control_between(self):
        row=self.host();tool=self.tool();start=self.e.world_time.turn;origin=(self.e.player.x,self.e.player.y)
        from engine.sound import emit
        with patch('engine.sound.emit',wraps=emit) as sound:
            self.choose();self.assertEqual(start+1,self.e.world_time.turn)
            self.assertFalse(self.e.local_map.walkable[13,12]);self.assertEqual(1,row['progress'])
            self.e._handle_key(pygame.K_PERIOD);self.assertEqual(1,row['progress'])
            self.choose();self.choose()
        self.assertEqual(start+4,self.e.world_time.turn)
        self.assertEqual(origin,(self.e.player.x,self.e.player.y));self.assertTrue(self.e.player.inventory.contains(tool))
        pulses=[c for c in sound.call_args_list if c.args[3]=='access_work']
        self.assertEqual(3,len(pulses));self.assertTrue(all(c.args[1:3]==origin for c in pulses))
        self.assertTrue(self.e.local_map.walkable[13,12]);self.assertTrue(self.e.local_map.transparent[13,12])
        self.assertEqual(['wood_bundle'],[i.item_id for i in self.e.local_map.floor_objects[(13,12)]])
        self.assertFalse(self.act());self.assertEqual(1,len(self.e.local_map.floor_objects[(13,12)]))

    def test_partial_switch_uses_completing_method_without_salvage(self):
        self.tool();row=self.host();self.choose();self.choose('force')
        self.assertEqual((1,'force'),(row['progress'],row['completed_by']));self.assertFalse(self.e.local_map.floor_objects)
        row=self.host('screen',(12,11));self.choose(xy=(12,11));dose=self.item('etching_wash')
        self.choose('dissolution',(12,11));self.assertFalse(self.e.player.inventory.contains(dose))
        self.assertEqual((1,'dissolution'),(row['progress'],row['completed_by']));self.assertFalse(self.e.local_map.floor_objects)

    def test_exact_captured_dose_strength_and_six_twelve_equivalence(self):
        for hits,xy in ((6,(13,12)),(12,(12,11))):
            row=self.host('screen',xy);a=self.item('etching_wash');a.coating_dose['strength']=.2
            b=self.item('etching_wash');b.coating_dose['hits']=hits
            # Instance capability, not an item-ID allowlist.
            b.item_id='authored_dissolution_variant'
            self.e.data.items['etching_wash']['temporary_essence'][0]['strength']=1
            self.assertFalse(self.act('dissolution',xy,a));self.assertTrue(self.act('dissolution',xy,b))
            self.assertTrue(self.e.player.inventory.contains(a));self.assertFalse(self.e.player.inventory.contains(b))
            self.assertEqual('dissolution',row['completed_by'])
        for identifier in ('crow_bile','binding_wash','binding_knife'):
            item=self.item(identifier);self.assertFalse(actions.qualifies(item,self.e.data.access_profiles['pale_lashings']))
        existing=self.item('bile_coating');self.assertTrue(actions.qualifies(existing,self.e.data.access_profiles['pale_lashings']))

    def test_cancel_stale_scene_owner_tool_dose_and_paralysis_free(self):
        row=self.host();tool=self.tool();dose=self.item('etching_wash');before=summary(self.e)
        actions.offer(self.e,(13,12));self.e._handle_key(pygame.K_ESCAPE);self.assertEqual(before,summary(self.e))
        for change,undo in [
            (lambda:setattr(self.e,'world_x',9),lambda:setattr(self.e,'world_x',0)),
            (lambda:setattr(self.e.player,'x',11),lambda:setattr(self.e.player,'x',12)),
            (lambda:self.e.player.equipment.unequip('weapon'),lambda:self.e.player.equipment.equip(tool,'weapon')),
            (lambda:row.update(progress=1),lambda:row.update(progress=0))]:
            token=actions.intent(self.e,(13,12));change();self.assertFalse(actions.perform(self.e,token,'careful'));undo()
        token=actions.intent(self.e,(13,12));expected=(actions.dose_state(dose),dose.count);dose.coating_dose['hits']=12
        self.assertFalse(actions.perform(self.e,token,'dissolution',dose,expected));dose.coating_dose['hits']=6
        with patch('engine.venom.fully_paralysed',return_value=True),patch('engine.sound.emit') as sound:
            for method in ('careful','force','dissolution'):self.assertFalse(self.act(method,dose=dose))
            sound.assert_not_called()
        self.assertEqual(before,summary(self.e))

    def test_unseen_out_of_reach_and_sealed_corner_are_free(self):
        row=self.host('screen',(13,13));self.tool()
        self.e.local_map.tiles[13,12]=make_tile('wall',False,False);self.e.local_map.tiles[12,13]=make_tile('wall',False,False)
        self.e.local_map.visible[13,13]=True;self.assertFalse(self.act('force',(13,13)))
        self.e.local_map.tiles[13,12]=make_tile('grass',True,True)
        self.e.local_map.visible[13,13]=False;self.assertFalse(self.act('force',(13,13)))
        self.e.player.x=8;self.assertFalse(self.act('force',(13,13)));self.assertIsNone(row['completed_by'])

    def test_final_wood_and_dose_failures_roll_back_exact_owners(self):
        row=self.host();self.tool();self.assertTrue(self.act());self.assertTrue(self.act());before=summary(self.e)
        def partial(m,x,y,wood):place_floor_object(m,x,y,wood);return False
        with patch('generation.floor_object_utils.place_floor_object',side_effect=partial),patch('engine.sound.emit') as sound:
            self.assertFalse(self.act());sound.assert_not_called()
        self.assertEqual(before,summary(self.e));self.assertIs(row,objects.at(self.e.local_map,(13,12)))
        dose=self.item('etching_wash');before=summary(self.e)
        from engine.item_transfers import consume_throw_unit
        def consumed_failure(e,item):consume_throw_unit(e,item);return False
        with patch('engine.item_transfers.consume_throw_unit',side_effect=consumed_failure):self.assertFalse(self.act('dissolution',dose=dose))
        self.assertEqual(before,summary(self.e));self.assertTrue(self.e.player.inventory.contains(dose))
        complete=objects.complete
        def mutation_failure(*args):complete(*args);raise ValueError('injected publication failure')
        with patch('engine.access_objects.complete',side_effect=mutation_failure):self.assertFalse(self.act('dissolution',dose=dose))
        self.assertEqual(before,summary(self.e));self.assertTrue(self.act())

    def test_modern_missing_contradictory_and_unknown_state_rejects(self):
        self.host('container');self.host('screen',(12,11))
        valid=self.e.local_map
        for mutate in [lambda m:m.access_objects.pop((13,12)),lambda m:delattr(m,'access_manifest'),
                       lambda m:m.container_state[(13,12)].pop('access_owner'),
                       lambda m:m.access_objects[(12,11)].update(version=2),
                       lambda m:m.access_objects[(13,12)].update(progress=True),
                       lambda m:m.tiles.__setitem__((12,11),make_tile('grass',True,True))]:
            m=copy.deepcopy(valid);mutate(m)
            with self.assertRaises(ValueError):objects.validate_map(m)
            with self.assertRaises(ValueError):pickle.loads(pickle.dumps(m))
        historical=LocalMap();historical.tiles[:]=make_tile('grass',True,True)
        place_container(historical,1,1,'bound_coffer',[])
        # A historical decor ID alone never confers a new security contract.
        objects.validate_map(historical);self.assertFalse(objects.secured(historical,(1,1)))

    def test_population_atomic_overlap_and_mandatory_route_reject(self):
        from generation.context import GenerationError
        e=self.e;m=e.local_map;before=pickle.dumps(m)
        specs=[dict(kind='screen',x=13,y=12,access_profile='pale_lashings'),dict(kind='item',x=13,y=12,item_id='wood_bundle')]
        with self.assertRaises(GenerationError):populate(e.data,e.item_factory,e.creature_factory,m,specs)
        self.assertEqual(before,pickle.dumps(m))
        m.tiles[:]=make_tile('wall',False,False)
        for x in range(10,16):m.tiles[x,12]=make_tile('floor',True,True)
        before=pickle.dumps(m)
        with self.assertRaises(GenerationError):populate(e.data,e.item_factory,e.creature_factory,m,specs[:1])
        self.assertEqual(before,pickle.dumps(m));self.assertFalse(objects.objects(m))
        # The lower lane is a real intact alternative.
        for x in range(10,16):m.tiles[x,13]=make_tile('floor',True,True)
        receipts=[];populate(e.data,e.item_factory,e.creature_factory,m,specs[:1],receipts=receipts)
        self.assertFalse(m.walkable[13,12]);self.assertTrue(m.walkable[13,13]);objects.validate_map(m)

    def test_saved_partial_removed_captured_edits_and_independent_cold_load(self):
        row=self.host();self.tool();self.choose();before=summary(self.e)
        self.e._handle_key(pygame.K_F5);self.assertTrue(self.e.save_manager.save_exists(),self.e.save_manager.last_error)
        self.e.data.access_profiles['pale_lashings']['work_steps']=9
        self.e._handle_key(pygame.K_F9);self.assertEqual(before,summary(self.e))
        self.assertEqual(3,objects.at(self.e.local_map,(13,12))['profile']['work_steps'])
        for _ in range(2):self.choose()
        self.e._handle_key(pygame.K_F5);expected=summary(self.e)
        result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--cold',str(Path(self.tmp.name)/'saves')],cwd=GAME_ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        self.assertEqual(expected,json.loads(result.stdout.strip().splitlines()[-1]))
        # Hot/cold cache residence has no work clock.
        cache=self.e.save_manager.cache;cache.store_submap('saved_screen',copy.deepcopy(self.e.local_map),[])
        cache.submap_hot.clear();cached=cache.load_submap('saved_screen')
        self.assertEqual(expected['objects'],{str(xy):r for xy,r in objects.objects(cached.local_map).items()})

    def test_real_light_visibility_bump_and_ai_path_use_screen_geometry(self):
        from engine.illumination import scene_light
        from generation.decor_utils import place_decor
        from components.ai import _creature_can_see_player
        from components.ai import AI
        e=self.e;m=e.local_map
        sub=e.world_map.get(0,0).add_submap('barrow','Geometry witness',123);e.current_submap_id=sub.submap_id
        m.tiles[:]=make_tile('wall',False,False)
        for x in range(10,18):
            for y in range(10,16):m.tiles[x,y]=make_tile('floor',True,True)
        for y in range(10,15):m.tiles[13,y]=make_tile('wall',False,False)
        m.tiles[13,12]=make_tile('floor',True,True)
        row=self.host();place_decor(m,15,12,'campfire_lit');e._update_fov()
        self.assertFalse(scene_light(e).lit[12,12]);self.assertFalse(e.normal_player_vision()['visible'][15,12])
        actor=e.creature_factory.spawn('highland_bandit',15,12);e.entities.append(actor)
        self.assertFalse(_creature_can_see_player(actor,e.player,m,engine=e))
        e._handle_key(pygame.K_RIGHT);self.assertEqual((12,12),(e.player.x,e.player.y));self.assertIsNone(row['completed_by'])
        # Actual movement helper follows the open longer route, not the screen.
        for _ in range(2):actor.ai._move_toward(actor,m,e.entities,12,12,player=e.player)
        self.assertNotEqual((13,12),(actor.x,actor.y))
        actor.x,actor.y=15,12
        composite=e.creature_factory.spawn('barrow_lane_revenant',14,12)
        e.entities.append(composite)
        self.assertFalse(composite.ai._move(e,composite,(13,12)))
        self.assertTrue(self.act('force'));e._update_fov()
        self.assertTrue(scene_light(e).lit[12,12]);self.assertTrue(e.normal_player_vision()['visible'][15,12])
        self.assertTrue(_creature_can_see_player(actor,e.player,m,engine=e))
        self.assertTrue(composite.ai._move(e,composite,(13,12)))
        e.entities.remove(composite)
        actor.ai._move_toward(actor,m,e.entities,12,12,player=e.player)
        actor.ai._move_toward(actor,m,e.entities,12,12,player=e.player)
        self.assertEqual((13,12),(actor.x,actor.y))
        e.entities.remove(actor);e._handle_key(pygame.K_RIGHT);self.assertEqual((13,12),(e.player.x,e.player.y))
        self.assertFalse(m.explored[40,30])

    def test_selected_hosts_all_rotations_and_unchanged_predecessor(self):
        from generation.placement import transform, NORMALS
        from generation.structure_preview import preview
        d=self.e.data;old=d.structures['workshop_d'];new=d.structures['workshop_e']
        self.assertEqual(old['special_tiles'],new['special_tiles'][:-2])
        for rotation in new['placement']['rotations']:
            raw=transform(new,rotation,False);door=raw['placement']['entrances'][0];dx,dy=NORMALS[door['normal']]
            report,m,actors=preview(raw,'ordinary_building',d,category='commercial',expectations={
                'entry':dict(x=door['x']+dx,y=door['y']+dy),'targets':raw['placement']['targets']})
            self.assertTrue(report['passed']);self.assertEqual(1,len(m.access_objects));objects.validate_map(m)
        report,m,actors=preview(d.layouts['barrow_bound_store'],'authored_submap',d,derive_access=True)
        self.assertTrue(report['passed']);self.assertEqual(2,len(m.access_objects));objects.validate_map(m)

    def test_quiet_loud_listener_comparison_and_post_removal_propagation(self):
        from engine.sound import emit, clear_interest
        from components.ai import AIState
        e=self.e;self.host();self.tool()
        actor=e.creature_factory.spawn('hollow_revenant',18,12);e.entities.append(actor)
        actor.ai.state=AIState.WANDERING
        self.assertTrue(self.act());self.assertIsNone(getattr(actor.ai,'sound_interest',None))
        self.assertTrue(self.act('force'));interest=actor.ai.sound_interest
        self.assertIsNotNone(interest);self.assertEqual((12,12),(interest['x'],interest['y']))
        clear_interest(actor.ai)
        e.local_map.tiles[15,:]=make_tile('wall',False,False)
        self.assertEqual(0,emit(e,12,12,'dismantle',maker=e.player));self.assertIsNone(actor.ai.sound_interest)

    def test_genuine_legacy_containers_and_cache_remain_ordinary(self):
        baseline=json.loads((ROOT/'evidence/sys-4/legacy-baseline.json').read_text())
        archive=ROOT/'evidence/sys-4'/baseline['archive']
        self.assertEqual(baseline['sha256'],hashlib.sha256(archive.read_bytes()).hexdigest())
        with zipfile.ZipFile(archive) as z:z.extractall(self.tmp.name)
        self.e.save_manager=SaveManager(save_root=Path(self.tmp.name)/'saves')
        self.assertTrue(self.e.save_manager.load(self.e),self.e.save_manager.last_error)
        for xy,state in [((10,10),'closed'),((11,10),'open'),((12,10),'looted')]:
            self.assertEqual(state,self.e.local_map.container_state[xy]['state']);self.assertFalse(objects.secured(self.e.local_map,xy))
        self.assertNotIn((13,10),self.e.local_map.container_state)
        for cached in (self.e.save_manager.cache.load(1,0),self.e.save_manager.cache.load_submap('sys4_legacy_room')):
            self.assertFalse(objects.objects(cached.local_map));self.assertEqual('open',cached.local_map.container_state[(11,10)]['state'])


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--cold':
        pygame.init()
        with patch('engine.save_manager.SAVE_DIR',Path(sys.argv[2])):e=make_engine(load_data())
        assert e.save_manager.load(e),e.save_manager.last_error
        print(json.dumps(summary(e)))
    else:unittest.main()
