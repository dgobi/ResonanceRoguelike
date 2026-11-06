"""SYS-1 contracts; controlled geometry and disposable saves, production consumers."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import pygame
import test_ai_9 as ai9
from engine.save_manager import _serialize_entity
from engine.ai_profiles import validate_saved
from engine import vessels
from engine.save_components import serialize_item,restore_item,validate_item
from engine.crafting import plan_craft
from rendering.craft_screen import CraftScreen
from generation.decor_utils import place_decor
from generation.floor_object_utils import place_floor_object


class VesselTests(unittest.TestCase):
    setUpClass = classmethod(ai9.CompositionTests.setUpClass.__func__)
    def setUp(self):
        ai9.CompositionTests.setUp(self)
        self.e.data.items=copy.deepcopy(self.e.data.items)
        self.e.data.recipes=copy.deepcopy(self.e.data.recipes)
        from engine.item_factory import ItemFactory
        self.e.item_factory=ItemFactory(self.e.data)
        self.e.player.inventory.bind_carrying(self.e.player.equipment,self.e.data.items)

    def pot(self,ml=0,capacity=500,heat=True):
        i=self.e.item_factory.create('clay_pot');i.vessel['config']['capacity_ml']=capacity
        if not heat:i.keywords=[k for k in i.keywords if k['tag']!='heatproof']
        vessels.set_water(i,ml);self.e.player.inventory.add(i);return i

    def prep(self,ml=250):
        e=self.e;pot=self.pot(ml)
        bone=e.item_factory.create('resonant_bone_fragment');e.player.inventory.add(bone)
        place_decor(e.local_map,13,12,'campfire_lit')
        return pot,bone

    def start(self):
        e=self.e;r=e.data.recipes['resonant_bone_tincture']
        selected,missing=plan_craft(r,e.player.inventory,ambient_sources=CraftScreen._build_ambient_sources(e))
        self.assertFalse(missing,missing)
        e._start_processing_placement(r,selected);e._placement_cursor_x,e._placement_cursor_y=12,11
        e._handle_key(pygame.K_RETURN)
        return e.local_map.processing_layer[(12,11)]

    def test_water_conservation_weight_capacity_and_identical_instances(self):
        e=self.e;a=self.pot();b=self.pot(100,1000)
        e.local_map.set_tile(12,11,'shallow_water',True,True)
        # Use an existing drinkable terrain ID from the loaded catalogue.
        water=next(k for k,v in e.data.terrain.items() if v.get('drinkable'))
        e.local_map.set_tile(12,11,water,True,True);e._update_fov()
        weight=e.player.inventory.current_weight
        self.assertTrue(vessels.handle(e,'fill',a,250,xy=(12,11)))
        self.assertAlmostEqual(weight+.25,e.player.inventory.current_weight)
        self.assertTrue(vessels.handle(e,'fill',a,250,xy=(12,11)))
        self.assertFalse(vessels.handle(e,'fill',a,1,xy=(12,11)))
        self.assertTrue(vessels.handle(e,'transfer',a,250,destination=b))
        self.assertEqual((250,350),(a.vessel['water_ml'],b.vessel['water_ml']))
        self.assertAlmostEqual(weight+.5,e.player.inventory.current_weight)
        for destination,amount in ((a,50),(b,0),(b,1000)):
            before=(serialize_item(a),serialize_item(b),e.world_time.turn)
            self.assertFalse(vessels.handle(e,'transfer',a,amount,destination=destination))
            self.assertEqual(before,(serialize_item(a),serialize_item(b),e.world_time.turn))
        self.assertNotEqual(vessels.label(a),vessels.label(b))

    def test_menu_free_cancellation_and_paid_drink_empty_fill(self):
        from engine.vessel_menu import open_item
        e=self.e;a=self.pot(500);e.player.needs.thirst=.8
        turn=e.world_time.turn;open_item(e,a);e._handle_key(pygame.K_ESCAPE)
        self.assertEqual(turn,e.world_time.turn);self.assertEqual(500,a.vessel['water_ml'])
        open_item(e,a)
        for _ in range(2):e._handle_key(pygame.K_DOWN)
        e._handle_key(pygame.K_RETURN)
        self.assertEqual(turn+1,e.world_time.turn);self.assertEqual(250,a.vessel['water_ml'])
        expected=.8-250/e.player.needs._t_max
        self.assertGreaterEqual(e.player.needs.thirst,expected)
        self.assertLess(e.player.needs.thirst,expected+.01)  # ordinary weather/turn thirst still ticks
        self.assertEqual([a],e.player.inventory.items)
        open_item(e,a)
        for _ in range(3):e._handle_key(pygame.K_DOWN)
        e._handle_key(pygame.K_RETURN)
        self.assertEqual(turn+1,e.world_time.turn)
        e._handle_key(pygame.K_RETURN)
        self.assertEqual(turn+2,e.world_time.turn);self.assertEqual(0,a.vessel['water_ml'])

    def test_stale_owned_scene_reach_capacity_and_paralysis_are_free(self):
        e=self.e;a=self.pot(250);b=self.pot();before=serialize_item(a)
        captured=vessels.context(e);e.world_x+=1
        self.assertFalse(vessels.handle(e,'empty',a,captured=captured));e.world_x-=1
        e.player.inventory.remove(b)
        self.assertFalse(vessels.handle(e,'transfer',a,100,destination=b))
        self.assertFalse(vessels.handle(e,'fill',a,100,xy=(40,40)))
        with patch('engine.venom.fully_paralysed',return_value=True):
            for action in ('drink','empty','fill','transfer'):
                self.assertFalse(vessels.handle(e,action,a,100,destination=b,xy=(12,11)))
        self.assertEqual(before,serialize_item(a));self.assertEqual(0,e.world_time.turn)

    def test_strict_configuration_saved_state_and_effective_capacity(self):
        a=self.pot(250);row=serialize_item(a)
        for key,bad in [('version',True),('version',2),('capacity_ml',True),('capacity_ml',0),('capacity_ml',float('inf')),('contents','tincture'),('extra',1)]:
            cfg=dict(vessels.CLAY);cfg[key]=bad
            with self.assertRaises(ValueError):vessels.configuration(cfg)
        for key,bad in [('water_ml',True),('water_ml',501),('water_ml',-1),('contents',None),('extra',0),('id','bad')]:
            badrow=copy.deepcopy(row);badrow['vessel'][key]=bad
            with self.assertRaises(ValueError):validate_item(badrow,'test')
        self.e.data.items['clay_pot']=dict(self.e.data.items['clay_pot'],vessel=dict(vessels.CLAY,capacity_ml=100))
        restored=self.e.item_factory.create('clay_pot');restore_item(restored,row)
        self.assertEqual(row,serialize_item(restored))

    def test_legacy_clay_nonempty_unknown_and_skin_are_preserved(self):
        for iid,liquid,volume in [('clay_pot',None,0),('clay_pot','unknown',.5),('water_skin','water',1)]:
            i=self.e.item_factory.create(iid);row=serialize_item(i);row.pop('vessel',None)
            row.update(liquid=liquid,liquid_volume=volume,name='Owned name')
            restore_item(i,row)
            self.assertEqual((liquid,volume,'Owned name'),(i.liquid,i.liquid_volume,i.name))
            self.assertEqual(iid=='clay_pot' and liquid is None,bool(vessels.state(i)))

    def test_exact_material_conjunction_heat_water_and_selected_physical_vessel(self):
        e=self.e;a,bone=self.prep();r=e.data.recipes['resonant_bone_tincture'];ambient=CraftScreen._build_ambient_sources(e)
        b=self.pot(500);c=self.pot(250,heat=False)
        selected,missing=plan_craft(r,e.player.inventory,ambient_sources=ambient,chosen_items={'vessel':a})
        self.assertFalse(missing);self.assertIs(a,selected.vessel);self.assertEqual([bone],selected.materials)
        for vessel in (b,c):
            self.assertTrue(plan_craft(r,e.player.inventory,ambient_sources=ambient,chosen_items={'vessel':vessel})[1])
        bone.keywords=[dict(tag='bony',tier=2)]
        other=e.item_factory.create('resonant_bone_fragment');other.keywords=[dict(tag='resonant',tier=2)];e.player.inventory.add(other)
        self.assertTrue(plan_craft(r,e.player.inventory,ambient_sources=ambient)[1])

    def test_pending_cancellation_and_mutated_batch_are_atomic(self):
        e=self.e;a,bone=self.prep();r=e.data.recipes['resonant_bone_tincture'];ambient=CraftScreen._build_ambient_sources(e)
        selected,_=plan_craft(r,e.player.inventory,ambient_sources=ambient)
        e._start_processing_placement(r,selected);e._handle_key(pygame.K_ESCAPE)
        self.assertEqual([a,bone],e.player.inventory.items);self.assertEqual(0,e.world_time.turn)
        e._start_processing_placement(r,selected);e._placement_cursor_x,e._placement_cursor_y=12,11
        vessels.set_water(a,249);e._handle_key(pygame.K_RETURN)
        self.assertEqual([a,bone],e.player.inventory.items);self.assertEqual(249,a.vessel['water_ml'])
        self.assertFalse(e.local_map.processing_layer);self.assertEqual(0,e.world_time.turn)

    def test_job_single_owner_restore_completion_and_no_replay(self):
        e=self.e;a,bone=self.prep();identity=a.vessel['id'];job=self.start()
        self.assertEqual(34,job['turns_remaining']);self.assertEqual([],e.player.inventory.items)
        self.assertIs(a,job['vessel_job']['vessel']);self.assertEqual(0,a.vessel['water_ml'])
        self.assertFalse(vessels.handle(e,'drink',a))
        e._handle_key(pygame.K_F5);e._handle_key(pygame.K_F9)
        job=e.local_map.processing_layer[(12,11)];self.assertEqual(identity,job['vessel_job']['vessel'].vessel['id'])
        for _ in range(34):e._handle_key(pygame.K_PERIOD)
        self.assertFalse(e.local_map.processing_layer)
        rows=e.local_map.floor_objects[(12,11)]
        self.assertEqual(['clay_pot','resonant_bone_tincture'],[i.item_id for i in rows])
        self.assertEqual(identity,rows[0].vessel['id'])
        e._handle_key(pygame.K_PERIOD);self.assertEqual(2,len(rows))
        e._handle_key(pygame.K_F5);e._handle_key(pygame.K_F9)
        self.assertEqual(2,len(e.local_map.floor_objects[(12,11)]))

    def test_missing_output_marker_and_failed_delivery_retain_recoverable_job(self):
        from engine.vessel_jobs import abandon
        e=self.e;a,bone=self.prep();job=self.start();job['turns_remaining']=0
        e.local_map.decor.pop((12,11),None)
        output=e.data.items.pop('resonant_bone_tincture')
        e._tick_processing_map(e.local_map,active=True)
        self.assertIs(job,e.local_map.processing_layer[(12,11)])
        e.data.items['resonant_bone_tincture']=output
        from generation.floor_object_utils import place_floor_object as real
        def partial(m,x,y,i):real(m,x,y,i);return False
        with patch('generation.floor_object_utils.place_floor_object',side_effect=partial):
            e._tick_processing_map(e.local_map,active=True)
        self.assertFalse(e.local_map.floor_objects);self.assertIs(job,e.local_map.processing_layer[(12,11)])
        self.assertTrue(abandon(e,(12,11),job,vessels.context(e)))
        self.assertEqual([a],e.local_map.floor_objects[(12,12)])
        self.assertFalse(abandon(e,(12,11),job,vessels.context(e)))

    def test_duplicate_ownership_and_malformed_busy_job_reject_before_save(self):
        e=self.e;a,bone=self.prep();job=self.start()
        e.player.inventory.items.append(copy.deepcopy(a))
        self.assertFalse(e.save_manager.save(e));self.assertIn('duplicate ownership',e.save_manager.last_error)
        e.player.inventory.items.clear();job['vessel_job']['requirement']['water_ml']=True
        self.assertFalse(e.save_manager.save(e));self.assertIn('vessel process',e.save_manager.last_error)

    def test_review_failures_reject_before_commit_and_menu_renders(self):
        from engine.vessel_menu import open_item,render
        from engine.vessels import validate_map
        from rendering.ui_registry import UIRegistry
        from test_effect_persistence import GAME_ROOT
        old=os.getcwd();self.addCleanup(os.chdir,old);os.chdir(GAME_ROOT)
        pygame.display.set_mode((1280,900))
        e=self.e;a,bone=self.prep();e.display.init();e.ui_registry=UIRegistry();e.ui_registry.load()
        open_item(e,a)
        for size in ((800,600),(1280,900)):
            render(e,pygame.Surface(size))
        e._handle_key(pygame.K_ESCAPE)
        r=copy.deepcopy(e.data.recipes['resonant_bone_tincture']);r['processing_decor']=[]
        selected,_=plan_craft(r,e.player.inventory,ambient_sources=CraftScreen._build_ambient_sources(e))
        e._start_processing_placement(r,selected);e._placement_cursor_x,e._placement_cursor_y=12,11
        e._handle_key(pygame.K_RETURN)
        self.assertEqual([a,bone],e.player.inventory.items);self.assertEqual(250,a.vessel['water_ml'])
        self.assertEqual(0,e.world_time.turn);self.assertFalse(e.local_map.processing_layer)
        e.local_map.container_state[(14,12)]=dict(state='closed',items=[{'item_id':'water_skin'}],decor_id='crate')
        validate_map(e.local_map)
        job=self.start();original=copy.deepcopy(job)
        for key,bad in [('source',[]),('on_fire',True),('decor_id',[]),('completion_message','{bad}')]:
            job[key]=bad
            with self.assertRaises(ValueError):validate_map(e.local_map)
            job[key]=original[key]
        job['vessel_job']['vessel'].vessel=None
        with self.assertRaises(ValueError):validate_map(e.local_map)

    def test_genuine_pre_sys1_archive_loads_legacy_job_and_items(self):
        import tempfile,zipfile,hashlib
        from test_effect_persistence import make_engine,load_data
        root=Path(__file__).resolve().parents[3]/'evidence/sys-1'
        record=json.loads((root/'legacy-baseline.json').read_text())
        archive=root/record['archive'];self.assertEqual(record['sha256'],hashlib.sha256(archive.read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory(prefix='sys1-legacy-load-') as tmp:
            with zipfile.ZipFile(archive) as z:z.extractall(tmp)
            with patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'):e=make_engine(load_data())
            self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
            for original,i in zip(record['inventory'],e.player.inventory.items):
                actual=serialize_item(i);s=actual.pop('vessel',None)
                self.assertEqual(original,actual)
                self.assertEqual(i.item_id=='clay_pot',s is not None)
            self.assertEqual(record['jobs'][0]['record'],e.local_map.processing_layer[(12,11)])
            for _ in range(34):e._tick_processing_map(e.local_map,active=True)
            self.assertEqual(['resonant_bone_tincture'],[i.item_id for i in e.local_map.floor_objects[(12,11)]])

    def test_hot_aliases_tick_once_and_cold_work_freezes_until_revisited(self):
        from engine.save_manager import CachedChunk
        e=self.e;a,bone=self.prep();job=self.start();cache=e.save_manager.cache
        cache.hot[(e.world_x,e.world_y)]=CachedChunk(e.local_map,[])
        cache.submap_hot['fixture_alias']=CachedChunk(e.local_map,[])
        e._handle_key(pygame.K_PERIOD);self.assertEqual(33,job['turns_remaining'])
        cache.hot.clear();cache.submap_hot.clear()
        m=copy.deepcopy(e.local_map);j=m.processing_layer[(12,11)]
        e.local_map.processing_layer.clear();e.local_map.decor.pop((12,11),None)
        cache.store_hot_only(100,100,m,[]);cache.submap_hot['fixture_alias']=cache.hot[(100,100)]
        e._handle_key(pygame.K_PERIOD);self.assertEqual(32,j['turns_remaining'])
        cache.submap_hot.clear();cache.evict_distant(e.world_x,e.world_y)
        for _ in range(4):e._handle_key(pygame.K_PERIOD)
        self.assertNotIn((100,100),cache.hot)
        restored=cache.load(100,100).local_map
        self.assertEqual(32,restored.processing_layer[(12,11)]['turns_remaining'])
        for _ in range(32):e._handle_key(pygame.K_PERIOD)
        self.assertFalse(restored.processing_layer)
        self.assertEqual(['clay_pot','resonant_bone_tincture'],[i.item_id for i in restored.floor_objects[(12,11)]])
        self.assertEqual(a.vessel['id'],restored.floor_objects[(12,11)][0].vessel['id'])

    def test_abandonment_confirmation_cancel_and_stale_selection_pay_correctly(self):
        from engine.vessel_menu import offer_job,open_item
        e=self.e;a,bone=self.prep();job=self.start();turn=e.world_time.turn
        self.assertTrue(offer_job(e,(12,11)));e._handle_key(pygame.K_ESCAPE)
        self.assertEqual(turn,e.world_time.turn);self.assertIs(job,e.local_map.processing_layer[(12,11)])
        self.assertTrue(offer_job(e,(12,11)));e._handle_key(pygame.K_RETURN)
        self.assertEqual(turn+1,e.world_time.turn);self.assertFalse(e.local_map.processing_layer)
        self.assertEqual([a],e.local_map.floor_objects[(12,12)]);self.assertEqual(0,a.vessel['water_ml'])
        self.assertFalse(offer_job(e,(12,11)))
        b=self.pot(250);open_item(e,b)
        for _ in range(3):e._handle_key(pygame.K_DOWN)
        e._handle_key(pygame.K_RETURN);vessels.set_water(b,500);e._handle_key(pygame.K_RETURN)
        self.assertEqual(500,b.vessel['water_ml']);self.assertEqual(turn+1,e.world_time.turn)

    def test_protected_bindings_reusable_state_and_timer_bounds_remain_strict(self):
        e=self.e
        for iid in ('flint_shard','revelation_lens','herbalist_pouch'):
            row=dict(e.data.items[iid],vessel=vessels.CLAY,stackable=False,consumed_on_use=False,on_use=None)
            with self.assertRaises(ValueError):vessels.validate_definition(row)
        a,bone=self.prep();row=serialize_item(a)
        for change in ({'consumed_on_use':True},{'on_use':'throw_flint_shard'}):
            with self.assertRaises(ValueError):validate_item(dict(row,**change),'incompatible vessel')
            legacy=dict(row,**change);legacy.pop('vessel');i=e.item_factory.create('clay_pot');restore_item(i,legacy)
            self.assertIsNone(vessels.state(i))
            self.assertEqual(change,{k:getattr(i,k) for k in change})
        job=self.start();job['turns_remaining']=10001
        with self.assertRaises(ValueError):vessels.validate_map(e.local_map)

    def test_filled_vessel_floor_container_roundtrip_and_capacity_denial(self):
        from engine.item_transfers import drop,take_floor,take_container
        e=self.e;a=self.pot(500);original=serialize_item(a)
        self.assertTrue(drop(e,a));self.assertFalse(e.player.inventory.contains(a))
        e._handle_key(pygame.K_F5);e._handle_key(pygame.K_F9)
        a=e.local_map.floor_objects[(12,12)][0];self.assertEqual(original,serialize_item(a))
        e.player.inventory.capacity=.7
        self.assertFalse(take_floor(e,a));self.assertIn(a,e.local_map.floor_objects[(12,12)])
        e.player.inventory.capacity=20;self.assertTrue(take_floor(e,a));self.assertEqual(original,serialize_item(a))
        # Explicit container fixture is a genuine owning location, not a copy.
        e.player.inventory.remove(a);e.local_map.container_state[(12,11)]=dict(state='open',items=[a],decor_id='crate')
        e._handle_key(pygame.K_F5);e._handle_key(pygame.K_F9)
        a=e.local_map.container_state[(12,11)]['items'][0]
        self.assertEqual(original,serialize_item(a));self.assertTrue(take_container(e,12,11,a))
        self.assertFalse(e.local_map.container_state[(12,11)]['items'])
        self.assertAlmostEqual(1.1,e.player.inventory.current_weight)
        from components.inventory import effective_weight
        self.assertAlmostEqual(.55,effective_weight(a,'Components',{'Components':.5}))
        e.local_map.set_tile(12,11,'shallow_water',True,True);e._update_fov()
        vessels.set_water(a,250);e.player.inventory.capacity=.9
        before=serialize_item(a);self.assertFalse(vessels.handle(e,'fill',a,250,xy=(12,11)))
        self.assertEqual(before,serialize_item(a))

    def test_malformed_checkpoint_rejects_before_installing_player_or_scene(self):
        import tempfile,pickle
        from engine.save_manager import SaveManager
        e=self.e;a,bone=self.prep();self.start();self.assertTrue(e.save_manager.save(e))
        source=e.save_manager.checkpoint_path()
        original={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file() and p.name!='manifest.json'}
        before=(e.player,e.local_map,e.world_map,e.world_time.turn)
        for kind in ('malformed_busy','duplicate_owner'):
            payloads=dict(original);scene=next(n for n in payloads if n.startswith('chunks/'))
            cached=pickle.loads(payloads[scene]);job=cached.local_map.processing_layer[(12,11)]
            if kind=='malformed_busy':job['vessel_job']['vessel'].vessel['water_ml']=True
            else:cached.local_map.floor_objects[(12,12)]=[copy.deepcopy(job['vessel_job']['vessel'])]
            payloads[scene]=pickle.dumps(cached)
            with tempfile.TemporaryDirectory(prefix='sys1-invalid-save-') as tmp:
                manager=SaveManager(save_root=Path(tmp));manager.store.publish(payloads,None,None)
                self.assertFalse(manager.load(e));self.assertIn('vessel',manager.last_error)
            self.assertEqual(before,(e.player,e.local_map,e.world_map,e.world_time.turn))

    def test_new_descriptor_free_clay_stays_inert_across_json_and_pickle(self):
        import pickle
        e=self.e;e.data.items['clay_pot'].pop('vessel')
        fresh=e.item_factory.create('clay_pot');self.assertIsNone(vessels.state(fresh))
        row=serialize_item(fresh);self.assertEqual(1,row['vessel_absent_version']);validate_item(row,'new clay')
        loaded=e.item_factory.create('clay_pot');restore_item(loaded,row)
        self.assertEqual(row,serialize_item(loaded));self.assertIsNone(vessels.state(loaded))
        self.assertEqual(row,serialize_item(pickle.loads(pickle.dumps(fresh))))
        for bad in (True,2,None):
            with self.assertRaises(ValueError):validate_item(dict(row,vessel_absent_version=bad),'bad absence')
        old=dict(row);old.pop('vessel_absent_version');restore_item(loaded,old)
        self.assertEqual(500,loaded.vessel['config']['capacity_ml'])

    def test_legacy_single_output_destination_and_new_blocked_job_recovery(self):
        e=self.e;a,bone=self.prep();job=self.start();job['turns_remaining']=0
        for xy in ((5,5),(12,11)):e.local_map.set_tile(*xy,'wall',False,False)
        e.local_map.processing_layer[(5,5)]=dict(item_id='dried_bitter_herb',turns_remaining=0,decor_id='',source='drying')
        e._tick_processing_map(e.local_map,active=True)
        self.assertNotIn((5,5),e.local_map.processing_layer)
        self.assertEqual(['dried_bitter_herb'],[i.item_id for i in e.local_map.floor_objects[(5,5)]])
        self.assertIs(job,e.local_map.processing_layer[(12,11)])
        self.assertNotIn((12,11),e.local_map.floor_objects)
        e.local_map.set_tile(12,11,'floor',True,True)
        e._tick_processing_map(e.local_map,active=True)
        self.assertFalse(e.local_map.processing_layer)
        self.assertIs(a,e.local_map.floor_objects[(12,11)][0])
        self.assertEqual(['clay_pot','resonant_bone_tincture'],[i.item_id for i in e.local_map.floor_objects[(12,11)]])

    def test_historical_opaque_container_roundtrip_does_not_relax_vessel_validation(self):
        e=self.e;owner=dict(items=['fixture',{'historical':'opaque'}],looted=True)
        e.local_map.container_state[(8,8)]=copy.deepcopy(owner)
        e._handle_key(pygame.K_F5);self.assertTrue(e.save_manager.save_exists(),e.save_manager.last_error)
        e.local_map.container_state[(8,8)]['items'].clear();e._handle_key(pygame.K_F9)
        self.assertEqual(owner,e.local_map.container_state[(8,8)])
        for invalid in ({'vessel':None},{'vessel_absent_version':False}):
            e.local_map.container_state[(8,8)]['items'].append(invalid)
            self.assertFalse(e.save_manager.save(e));self.assertIn('vessel',e.save_manager.last_error)
            e.local_map.container_state[(8,8)]['items'].pop()

    def test_saved_clay_dependency_upgrade_is_exact_one_way_and_stock_is_versioned(self):
        from generation.placement import dependencies,check_dependencies
        from generation.context import GenerationError
        e=self.e;old=copy.copy(e.data);old.items=copy.deepcopy(e.data.items)
        original=Path(__file__).resolve().parents[1]/'fixtures/sys1/pre-sys1-clay.json'
        old.items['clay_pot']=json.loads(original.read_bytes())
        raw=e.data.structures['apothecary_b'];p=dict(id='saved-old-shop',asset='apothecary_b',dependency='shop')
        plan=dict(dependencies=dict(shop=dependencies(raw,old)))
        current=dict(dependencies=dict(shop=dependencies(raw,e.data)))
        self.assertNotEqual(plan,current)
        self.assertIs(raw,check_dependencies(p,plan,e.data))
        self.assertIs(raw,check_dependencies(p,current,e.data))
        for changed in (dict(e.data.items['clay_pot'],weight=.7),dict(e.data.items['clay_pot'],vessel=dict(vessels.CLAY,capacity_ml=501)),dict(e.data.items['clay_pot'],vessel=dict(vessels.CLAY,version=True))):
            d=copy.copy(e.data);d.items=dict(e.data.items,clay_pot=changed)
            with self.assertRaises(GenerationError):check_dependencies(p,plan,d)
        # A new plan does not silently accept later removal of the descriptor.
        with self.assertRaises(GenerationError):check_dependencies(p,current,old)
        expected=copy.deepcopy(raw);expected['id']='apothecary_c'
        expected['special_tiles'][1]['loot_pools']=['alchemist_preparation']
        self.assertEqual(expected,e.data.structures['apothecary_c'])
        additions={'copper_steeping_kettle','waxed_water_flask','steeping_note'}
        self.assertFalse(additions & {r['item_id'] for r in e.data.loot_pools['alchemist_shop']['items']})
        self.assertTrue(additions <= {r['item_id'] for r in e.data.loot_pools['alchemist_preparation']['items']})

    def test_semantic_identity_projection_preserves_capability_and_water_differences(self):
        from g1_support import semantic_item
        a=self.pot();b=copy.deepcopy(a);b.vessel=vessels.create(vessels.CLAY)
        self.assertNotEqual(serialize_item(a),serialize_item(b))
        self.assertEqual(semantic_item(a),semantic_item(b))
        historical=semantic_item(a,historical=True)
        self.assertNotIn('vessel',historical)
        self.assertIn('vessel',semantic_item(a))
        vessels.set_water(b,1)
        self.assertNotEqual(semantic_item(a),semantic_item(b))
        self.assertNotEqual(historical,semantic_item(b,historical=True))
        vessels.set_water(b,0);b.vessel['config']['capacity_ml']=501
        self.assertNotEqual(historical,semantic_item(b,historical=True))
        b.vessel['water_ml']=True
        with self.assertRaises(ValueError):semantic_item(b,historical=True)


class RegroupLifecycleTests(unittest.TestCase):
    setUpClass = classmethod(ai9.CompositionTests.setUpClass.__func__)
    setUp = ai9.CompositionTests.setUp

    def test_engine_exhausted_hold_concealment_restore_and_cold_continuation(self):
        e = self.e
        a = e.creature_factory.spawn('barrow_shy_listener',16,12)
        e.entities.append(a)
        a.ai.maneuver_config['modules'][0]['opportunity_budget'] = 2
        a.fighter.hp = 7
        b = e.creature_factory.spawn('hollow_revenant',17,13)
        e.entities.append(b)
        # Fixture-only stationary supporter, no policy or visibility overrides.
        e.data.entities['hollow_revenant']['speed'] = 0
        for _ in range(2): e._handle_key(pygame.K_PERIOD)
        c = a.ai.maneuvers['current']
        self.assertEqual((0,2),(c['left'],c['hold_left']))
        self.assertEqual(c['goal'],[a.x,a.y])
        validate_saved(_serialize_entity(a),e.local_map)
        e._handle_key(pygame.K_F5)
        self.assertTrue(e.save_manager.save_exists(),e.save_manager.last_error)
        # Uninterrupted holds remain legal and paid, including after F9.
        e._handle_key(pygame.K_F9); a=e.entities[1]
        for remaining in (1,0):
            before=e.world_time.turn;e._handle_key(pygame.K_PERIOD)
            self.assertEqual(before+1,e.world_time.turn)
            self.assertEqual('regroup_hold',a.ai.trace[-1]['reason'])
            self.assertEqual(remaining,(a.ai.maneuvers['current'] or {}).get('hold_left',0))
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
        e._handle_key(pygame.K_F9); a=e.entities[1]
        # Expose the final-credit goal through actual normal vision. Player
        # position is disclosed fixture setup; all decisions/actions are real.
        e.player.x,e.player.y=16,12;e._update_fov()
        self.assertTrue(e.normal_player_vision()['visible'][a.x,a.y])
        old=(a.x,a.y);turn=e.world_time.turn;e._handle_key(pygame.K_PERIOD)
        self.assertEqual(turn+1,e.world_time.turn)
        self.assertNotEqual(old,(a.x,a.y))
        self.assertEqual('seek_concealment',a.ai.trace[-1]['reason'])
        self.assertEqual(1,len(a.ai.trace[-1]['steps']))
        self.assertFalse(a.ai.trace[-1]['bonus_consumed'])
        self.assertIsNone(a.ai.maneuvers['current'])
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
        before=_serialize_entity(a);validate_saved(before,e.local_map)
        e._handle_key(pygame.K_F5);e._handle_key(pygame.K_F9)
        self.assertEqual(before,_serialize_entity(e.entities[1]))
        script = """
import json,pygame
from pathlib import Path
from unittest.mock import patch
from test_effect_persistence import make_engine,load_data
from engine.save_manager import _serialize_entity
from engine.ai_profiles import validate_saved
pygame.init()
with patch('engine.save_manager.SAVE_DIR',Path(__import__('sys').argv[1])): e=make_engine(load_data())
e.debug=False
assert e.save_manager.load(e),e.save_manager.last_error
a=e.entities[1];before=_serialize_entity(a)
assert not e.normal_player_vision()['visible'][a.x,a.y]
e._handle_key(pygame.K_PERIOD)
validate_saved(_serialize_entity(a),e.local_map)
assert a.ai.maneuvers['current'] is None and a.ai.maneuvers['regroup_spent']
print(json.dumps(before))
"""
        result=subprocess.run([sys.executable,'-X','utf8','-B','-c',script,str(self.root)],
                              capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(before,json.loads(result.stdout.splitlines()[-1]))

    def test_defensive_continuation_rejects_exhausted_off_goal_without_moving(self):
        from engine.enemy_maneuvers import _continue, REGROUP
        t=ai9.CompositionTests();t.e=self.e
        a=t.actor(moves=(REGROUP,),regroup_when_wounded=dict(opportunity_budget=2))
        t.actor(x=17,y=13,moves=None,alarms=None);a.fighter.hp=7
        t.decision(a);t.phase(a)
        a.x-=1;old=(a.x,a.y)
        with self.assertRaises(ValueError):validate_saved(_serialize_entity(a),self.e.local_map)
        self.assertIsNone(_continue(a.ai,self.e,a,[],1))
        self.assertEqual(old,(a.x,a.y));self.assertIsNone(a.ai.maneuvers['current'])
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
