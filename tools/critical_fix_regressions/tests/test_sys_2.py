"""Shared illumination production contracts, controlled scenes and disposable saves."""
import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import random
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from unittest.mock import patch
import numpy as np
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from engine.illumination import scene_light, ambient, emission
from engine.held_light import active_item
from engine.save_components import serialize_item, restore_item, validate_item
from engine.save_manager import SaveManager
from generation.decor_utils import place_decor, clear_decor
from generation.floor_object_utils import place_floor_object
from components.ai import _creature_can_see_player
from rendering.craft_screen import CraftScreen
from world.local_map import LocalMap, make_tile


class SharedLightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data = load_data()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sys2-contract-')
        self.addCleanup(self.tmp.cleanup)
        with patch('engine.save_manager.SAVE_DIR', Path(self.tmp.name)/'saves'):
            self.e = make_engine(copy.copy(self.data))
        e=self.e
        e.data.items=copy.deepcopy(self.data.items)
        e.data.terrain=copy.deepcopy(self.data.terrain)
        e.data.decoratives=copy.deepcopy(self.data.decoratives)
        e.local_map.tiles[:]=make_tile('floor',True,True)
        e.debug=False;e.world_time.turn=0
        self.underground()

    def underground(self, kind='barrow'):
        e=self.e;chunk=e.world_map.get(0,0)
        sub=chunk.add_submap(kind,'Test chamber',123)
        e.current_submap_id=sub.submap_id
        e._update_fov()
        return sub

    def torch(self, radius=6, fuel=600, used=0, iid='tallow_torch'):
        e=self.e;e.data.items[iid]=dict(e.data.items[iid],light_radius=radius,burn_turns=fuel)
        item=e.item_factory.create(iid);item.turns_lit=used
        self.assertTrue(e.player.inventory.add(item));return item

    def use(self, item, paid=False):
        self.e.item_system.use(item,self.e)
        if paid and self.e.item_system.last_use_committed:self.e._advance_turn()

    def watcher(self,x=18,y=12):
        a=self.e.creature_factory.spawn('highland_bandit',x,y)
        a.perception.sight_radius=10;a.perception.sees_in_dark=False
        self.e.entities.append(a);return a

    def sees(self,a,target=None):
        return _creature_can_see_player(a,target or self.e.player,self.e.local_map,engine=self.e)

    def test_exact_inclusive_reach_and_legacy_campfire_units(self):
        e=self.e;self.use(self.torch(radius=4))
        f=scene_light(e)
        self.assertTrue(f.lit[16,12]);self.assertFalse(f.lit[17,12])
        self.assertFalse(f.lit[16,13])
        self.assertEqual(5,emission('terrain','campfire_lit',.7))
        for v in (0,None,-1,.8,True,float('inf'),41):
            self.assertEqual(0,emission('terrain','other',v))
        e.player.light_source.active=False
        e.local_map.set_tile(20,12,'campfire_lit',True,True)
        f=scene_light(e);self.assertTrue(f.lit[25,12]);self.assertFalse(f.lit[26,12])

    def test_same_scene_actual_target_not_observer_pool(self):
        e=self.e;a=self.watcher();place_decor(e.local_map,21,12,'campfire_lit')
        f=scene_light(e);self.assertTrue(f.lit[a.x,a.y]);self.assertFalse(f.lit[12,12])
        self.assertFalse(self.sees(a));self.use(self.torch(radius=1))
        self.assertTrue(self.sees(a))
        target=copy.copy(e.player);target.x,target.y=12,16
        self.assertFalse(self.sees(a,target))

    def test_darkvision_near_sight_range_and_walls(self):
        e=self.e;a=self.watcher();self.assertFalse(self.sees(a))
        a.x=14;self.assertTrue(self.sees(a));a.x=18
        a.perception.sees_in_dark=True;self.assertTrue(self.sees(a))
        e.local_map.set_tile(15,12,'wall',False,False);self.assertFalse(self.sees(a))
        e.local_map.set_tile(15,12,'floor',True,True);a.x=23
        self.assertFalse(self.sees(a))

    def test_hidden_source_visible_region_and_opaque_corner(self):
        e=self.e;e.local_map.set_tile(14,12,'wall',False,False)
        place_decor(e.local_map,16,12,'campfire_lit')
        f=scene_light(e);v=e.normal_player_vision()['visible']
        self.assertFalse(v[16,12]);self.assertTrue(f.lit[16,12])
        self.assertTrue(f.lit[16,15]);self.assertTrue(v[16,15])
        # A directly seen source cannot reveal cells around the player's wall.
        clear_decor(e.local_map,16,12);place_decor(e.local_map,12,15,'campfire_lit')
        self.assertTrue(e.normal_player_vision()['visible'][12,15])
        self.assertFalse(e.normal_player_vision()['visible'][16,12])

    def test_obstruction_changes_refresh_without_turn_and_declared_decor_blocks(self):
        e=self.e;self.use(self.torch())
        self.assertTrue(scene_light(e).lit[17,12])
        e.local_map.set_tile(15,12,'wall',False,False)
        self.assertFalse(scene_light(e).lit[17,12])
        e.local_map.set_tile(15,12,'floor',True,True)
        self.assertTrue(scene_light(e).lit[17,12])
        e.data.decoratives['test_screen']={'blocks_sight':True}
        place_decor(e.local_map,15,12,'test_screen')
        self.assertFalse(scene_light(e).lit[17,12])

    def test_surface_submap_dark_fallback_identity_and_memory(self):
        e=self.e;e.world_time.turn=720;e.current_submap_id=None
        surface=ambient(e)[0];self.assertGreater(surface,.4)
        sub=self.underground('vault');self.assertEqual(0,ambient(e)[0])
        e.local_map.tiles['explored'][:]=False;e._update_fov()
        self.assertFalse(e.local_map.explored[30,12])
        sub.submap_type='unconfigured_enclosure';self.assertEqual(0,ambient(e)[0])
        e.current_submap_id='unresolved';scene_light(e);e._update_fov()
        self.assertEqual('unresolved',e.current_submap_id)
        self.assertEqual(0,ambient(e)[0])
        e.current_submap_id=None;self.assertEqual(surface,ambient(e)[0])
        e.world_time.turn=0;self.assertLess(ambient(e)[0],surface)

    def test_final_fog_wraith_caps_and_physical_light_independence(self):
        e=self.e;place_decor(e.local_map,21,12,'campfire_lit')
        self.assertTrue(e.normal_player_vision()['visible'][21,12])
        original=e.weather.get_mechanic
        with patch.object(e.weather,'get_mechanic',side_effect=lambda k,d=None: 5 if k=='fov_cap' else original(k,d)):
            self.assertFalse(e.normal_player_vision()['visible'][21,12])
            self.assertTrue(scene_light(e).lit[21,12])
        a=e.creature_factory.spawn('bog_wraith',13,12);a._wraith_exposure_turns=4;e.entities.append(a)
        self.assertFalse(e.normal_player_vision()['visible'][21,12])
        self.assertTrue(scene_light(e).lit[21,12])

    def test_extension_finite_and_sources_not_player_distance_filtered(self):
        e=self.e;place_decor(e.local_map,55,12,'campfire_lit')
        v=e.normal_player_vision()['visible']
        self.assertTrue(v[51,12]);self.assertTrue(v[52,12]);self.assertFalse(v[53,12])
        self.assertTrue(scene_light(e).lit[55,12])

    def test_free_queries_render_order_rng_and_owner_state(self):
        e=self.e;i=self.torch();self.use(i);a=self.watcher()
        place_decor(e.local_map,20,14,'campfire_lit')
        original=(serialize_item(i),e.world_time.turn,random.getstate(),e.rng.getstate(),a.__dict__.copy())
        expected=e.normal_player_vision()['visible'].copy();f=scene_light(e)
        for _ in range(8):
            e.entities.reverse();e._update_light_map();self.sees(a)
            self.assertTrue(np.array_equal(expected,e.normal_player_vision()['visible']))
            self.assertIs(f,scene_light(e))
        self.assertEqual(original,(serialize_item(i),e.world_time.turn,random.getstate(),e.rng.getstate(),a.__dict__.copy()))
        self.assertFalse(f.lit.flags.writeable)

    def test_no_offscene_held_emission(self):
        e=self.e;self.use(self.torch());other=LocalMap();other.tiles[:]=make_tile('floor',True,True)
        self.assertFalse(scene_light(e,other).lit.any())
        place_decor(other,20,12,'campfire_lit')
        self.assertTrue(scene_light(e,other).lit[20,12]);self.assertFalse(scene_light(e,other).lit[12,12])

    def test_same_id_switch_ward_drop_and_material_consumption(self):
        e=self.e;a=self.torch(used=13);b=self.torch(used=22)
        self.use(a,True);self.assertIs(a,active_item(e.player));self.assertEqual(14,a.turns_lit)
        self.use(b,True);self.assertIs(b,active_item(e.player));self.assertEqual(14,a.turns_lit)
        self.assertEqual(23,b.turns_lit)
        ward=e.item_factory.create('faceted_ward');e.player.inventory.add(ward);self.use(ward,True)
        self.assertIsNone(active_item(e.player));self.assertFalse(scene_light(e).emitted.any())
        self.use(a,True);self.assertIs(a,active_item(e.player))
        from engine.item_transfers import drop,consume
        self.assertTrue(drop(e,a));self.assertFalse(scene_light(e).emitted.any())
        self.use(b);self.assertTrue(consume(e,b));self.assertFalse(scene_light(e).emitted.any())

    def test_detached_spare_container_and_floor_do_not_emit_or_burn(self):
        e=self.e;i=self.torch();self.use(i);e.player.equipment.unequip('offhand')
        before=i.turns_lit;e._advance_turn();self.assertEqual(before,i.turns_lit)
        self.assertFalse(scene_light(e).emitted.any())
        e.player.inventory.remove(i);place_floor_object(e.local_map,12,12,i)
        self.assertFalse(scene_light(e).emitted.any())

    def test_expiry_precedes_ai_and_both_canonical_types_consumed(self):
        e=self.e;a=self.watcher()
        for iid in ('tallow_torch','oil_lantern'):
            i=self.torch(fuel=1,iid=iid);self.use(i);self.assertTrue(self.sees(a))
            seen=[]
            with patch.object(e.ai_system,'process',side_effect=lambda **kw:seen.append(self.sees(a))):e._advance_turn()
            self.assertEqual([False],seen);self.assertFalse(e.player.inventory.contains(i))

    def test_extinction_stops_evidence_retains_pursuit_memory(self):
        e=self.e;a=self.watcher();i=self.torch();self.use(i)
        a.ai._update_state(a,e.local_map,e.player,0,engine=e)
        memory=a.ai.memory_turns;self.assertEqual((12,12),(a._last_known_px,a._last_known_py))
        self.use(i);self.assertFalse(self.sees(a));self.assertEqual(memory,a.ai.memory_turns)
        self.assertEqual((12,12),(a._last_known_px,a._last_known_py))

    def test_exhausted_null_zero_legacy_fuel_never_heat_or_emit(self):
        e=self.e
        for fuel in (None,0,600):
            i=self.torch(fuel=fuel,used=600);before=serialize_item(i)
            self.use(i,True);self.assertFalse(e.item_system.last_use_committed)
            self.assertIsNone(active_item(e.player));self.assertEqual([],CraftScreen._build_ambient_sources(e))
            self.assertEqual(before,serialize_item(i));self.assertTrue(e.player.inventory.contains(i))
        self.assertEqual(0,e.world_time.turn)

    def test_saved_effective_mechanics_visuals_and_fuel_survive_definition_edit(self):
        e=self.e;i=self.torch(radius=9,fuel=37,used=11);self.use(i)
        row=serialize_item(i);self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        e.data.items['tallow_torch'].update(light_radius=2,burn_turns=4,light=None)
        self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        i=e.player.inventory.items[0];self.assertEqual(row,serialize_item(i))
        self.assertEqual(9,e._get_equipped_light_radius());self.assertTrue(scene_light(e).lit[21,12])

    def test_strict_malformed_owned_configuration(self):
        row=serialize_item(self.torch())
        for bad in (None,{},dict(version=True,radius=6),dict(version=2,radius=6),dict(version=1,radius=True),
                    dict(version=1,radius=0.7),dict(version=1,radius=-1),dict(version=1,radius=41),dict(version=1,radius=6,extra=1)):
            altered=copy.deepcopy(row);altered['held_light']=bad
            with self.assertRaises(ValueError):validate_item(altered,'test')

    def test_malformed_visuals_reject_json_and_pickle_before_installation(self):
        e=self.e;i=self.torch();self.use(i);before=(e.player,e.local_map,e.world_time.turn)
        row=serialize_item(i)
        for color in ('bad',[1,2],[1,2,float('inf')],[1,True,3]):
            bad=copy.deepcopy(row);bad['light_data']['color']=color
            with self.assertRaises(ValueError):validate_item(bad,'saved active light')
            baditem=copy.deepcopy(i);baditem.light_data['color']=color
            raw=pickle.dumps(baditem)
            with self.assertRaises(ValueError):pickle.loads(raw)
        self.assertEqual(before,(e.player,e.local_map,e.world_time.turn))

    def test_missing_legacy_mechanical_reach_does_not_use_visual_defaults(self):
        for radius in (0,-1,None):
            i=self.torch(radius=radius);self.use(i)
            self.assertEqual(0,self.e._get_equipped_light_radius())
            self.assertFalse(scene_light(self.e).emitted.any())
            self.assertEqual(8,i.light_data['radius'])

    def test_invalid_light_checkpoint_rejected_before_any_owner_install(self):
        e=self.e;i=self.torch();self.use(i)
        floor=self.torch();e.player.inventory.remove(floor);place_floor_object(e.local_map,13,12,floor)
        self.assertTrue(e.save_manager.save(e));source=e.save_manager.checkpoint_path()
        original={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file() and p.name!='manifest.json'}
        before=(e.player,e.local_map,e.world_map,e.world_time.turn)
        for kind in ('active_json','inactive_pickle'):
            payloads=dict(original)
            if kind=='active_json':
                row=json.loads(payloads['player.json']);row['inventory']['items'][0]['light_data']['color']='bad'
                payloads['player.json']=json.dumps(row).encode()
            else:
                name=next(n for n in payloads if n.startswith('chunks/'))
                cached=pickle.loads(payloads[name]);cached.local_map.floor_objects[(13,12)][0].light_data['color']=[1,2]
                payloads[name]=pickle.dumps(cached)
            with tempfile.TemporaryDirectory(prefix='sys2-invalid-') as tmp:
                manager=SaveManager(save_root=Path(tmp));manager.store.publish(payloads,None,None)
                self.assertFalse(manager.load(e));self.assertIn('held_light',manager.last_error)
            self.assertEqual(before,(e.player,e.local_map,e.world_map,e.world_time.turn))

    def test_historical_projection_retains_custom_effective_properties(self):
        from g1_support import semantic_item
        i=self.torch();self.assertNotIn('held_light',semantic_item(i,historical=True))
        self.assertIn('held_light',semantic_item(i))
        i.held_light['radius']=9;self.assertIn('held_light',semantic_item(i,historical=True))

    def test_saved_pickle_held_configuration_and_no_derived_mask(self):
        e=self.e;i=self.torch(radius=8,used=20);e.player.inventory.remove(i)
        place_floor_object(e.local_map,13,12,i);scene_light(e)
        raw=pickle.dumps(e.local_map);loaded=pickle.loads(raw)
        self.assertNotIn('_scene_light_cache',loaded.__dict__)
        self.assertEqual(serialize_item(i),serialize_item(loaded.floor_objects[(13,12)][0]))

    def test_heat_tier_and_stationary_fire_stay_distinct(self):
        e=self.e;self.use(self.torch(radius=20,iid='oil_lantern'))
        self.assertEqual([{'tag':'burning','tier':2}],CraftScreen._build_ambient_sources(e))
        place_decor(e.local_map,13,12,'campfire_lit')
        self.assertIn({'tag':'stationary_fire','tier':1},CraftScreen._build_ambient_sources(e))

    def test_dense_scene_bounded_reuse(self):
        e=self.e
        for x in range(2,78,5):
            for y in range(2,40,5):place_decor(e.local_map,x,y,'campfire_lit')
        began=time.perf_counter();f=scene_light(e)
        for _ in range(30):self.assertIs(f,scene_light(e))
        elapsed=time.perf_counter()-began
        self.assertLess(elapsed,2.0)
        self.assertEqual(128,len(f.sources))

    def test_genuine_baseline_json_and_cached_items(self):
        root=GAME_ROOT.parent/'evidence/sys-2';receipt=json.loads((root/'legacy-baseline.json').read_text())
        for record in receipt['records']:
            with self.subTest(active=record['active']),tempfile.TemporaryDirectory(prefix='sys2-old-') as tmp:
                archive=root/record['archive'];self.assertEqual(record['sha256'],hashlib.sha256(archive.read_bytes()).hexdigest())
                with zipfile.ZipFile(archive) as z:z.extractall(tmp)
                e=self.e;e.save_manager=SaveManager(save_root=Path(tmp)/'saves')
                self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
                for old,i in zip(record['inventory'],e.player.inventory.items):
                    row=serialize_item(i);self.assertEqual(dict(version=1,radius=6),row.pop('held_light'))
                    self.assertEqual(old,row)
                self.assertEqual(6 if record['active'] else 0,e._get_equipped_light_radius())
                floor=e.local_map.floor_objects[(13,12)][0]
                self.assertEqual(777,floor.turns_lit);self.assertEqual(6,floor.held_light['radius'])
                self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
                # A different process, with the genuine archive's now-upgraded checkpoint.
                code="""from pathlib import Path
from test_effect_persistence import load_data,make_engine
from engine.save_manager import SaveManager
e=make_engine(load_data());e.save_manager=SaveManager(save_root=Path(__import__('sys').argv[1]))
assert e.save_manager.load(e),e.save_manager.last_error
assert e.player.inventory.items[0].held_light['radius']==6
assert e.local_map.floor_objects[(13,12)][0].turns_lit==777
"""
                env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(GAME_ROOT),str(Path(__file__).parent)]))
                # Constructor must also use a disposable default root.
                code=code.replace('e=make_engine(load_data());',"from unittest.mock import patch\nwith patch('engine.save_manager.SAVE_DIR',Path(__import__('sys').argv[1])): e=make_engine(load_data())\n")
                result=subprocess.run([sys.executable,'-X','utf8','-B','-c',code,str(Path(tmp)/'saves')],cwd=GAME_ROOT,env=env,capture_output=True,text=True)
                self.assertEqual(0,result.returncode,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
