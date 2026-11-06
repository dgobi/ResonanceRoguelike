"""SYS-5 physical resources and real-host integration; disposable saves only."""
from __future__ import annotations
import copy
import json
import os
import random
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import pygame
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from engine import flesh_resources as flesh
from engine.harvesting import butcher, profile_errors
from engine.save_components import serialize_item, restore_item, validate_item
from generation import floor_object_utils as floor


class ResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.original = load_data()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sys5-resource-')
        self.addCleanup(self.tmp.cleanup)
        self.saves = Path(self.tmp.name)/'saves'
        p = patch('engine.save_manager.SAVE_DIR',self.saves);p.start();self.addCleanup(p.stop)
        self.e = make_engine(copy.deepcopy(self.original))
        self.e.debug = False
        self.e.local_map.visible[:] = True
        self.a = self.e.creature_factory.spawn('grave_skirmisher',13,12)
        self.e.entities.append(self.a)

    def portion(self, count=1, identifier='crow_meat', xy=(13,13)):
        item=self.e.item_factory.create(identifier);item.count=count
        self.assertTrue(floor.place_floor_object(self.e.local_map,*xy,item))
        return item

    def corpse(self, source='plague_crow', xy=(13,13)):
        item=flesh.create_corpse(self.e.data,self.e.item_factory,source,*xy,authored=True)
        self.assertTrue(floor.place_floor_object(self.e.local_map,*xy,item))
        return item

    def feed(self,item,commit=lambda:None):
        return flesh.consume(self.e,self.a,item,(13,13),commit)

    def cutter(self,tier=2):
        tool=self.e.item_factory.create('flint_shard')
        tool.keywords=[dict(tag='cutting',tier=tier)]
        self.e.player.inventory.add(tool)
        self.e.player.equipment.equip(tool,'weapon')
        return tool

    def test_fresh_capability_and_historical_json_absence(self):
        for key in ('crow_meat','stalker_meat'):
            self.assertTrue(flesh.eligible(self.e.item_factory.create(key)))
        for key in ('animal_bone','crow_bile','flint_shard','clay_pot','bile_coating','corpse'):
            self.assertFalse(flesh.eligible(self.e.item_factory.create(key)))
        old=json.loads((GAME_ROOT.parent/'evidence/sys-5/legacy-baseline.json').read_text())['inventory'][0]
        restored=self.e.item_factory.create(old['item_id']);restore_item(restored,old)
        self.assertFalse(flesh.eligible(restored));self.assertFalse(hasattr(restored,'flesh_resource'))
        authored=copy.deepcopy(self.e.data.items['crow_meat']);authored['id']='test_new_meat'
        self.e.data.items['test_new_meat']=authored
        self.assertTrue(flesh.eligible(self.e.item_factory.create('test_new_meat')))

    def test_exact_units_competition_and_same_coordinate_replacement(self):
        meat=self.portion(2)
        self.assertTrue(self.feed(meat));self.assertEqual(meat.count,1)
        self.assertTrue(self.feed(meat));self.assertNotIn((13,13),self.e.local_map.floor_objects)
        replacement=self.portion()
        self.assertFalse(self.feed(meat));self.assertEqual(replacement.count,1)
        self.assertTrue(self.feed(replacement));self.assertFalse(self.feed(replacement))

    def test_nonfloor_and_aliased_owners_reject(self):
        item=self.portion()
        self.e.player.inventory.items.append(item)
        self.assertFalse(self.feed(item));self.e.player.inventory.items.remove(item)
        floor.place_container(self.e.local_map,16,16,'crate',[item])
        self.assertFalse(self.feed(item));floor.open_container(self.e.local_map,16,16)
        self.assertFalse(self.feed(item));self.e.local_map.container_state.clear()
        self.e.local_map.processing_layer[(15,15)]={'test_owner':item}
        self.assertFalse(self.feed(item));self.e.local_map.processing_layer.clear()
        clone=copy.deepcopy(item);self.e.player.inventory.items.append(clone)
        self.assertFalse(self.feed(item));self.e.player.inventory.items.clear()
        self.assertTrue(self.feed(item))

    def test_bad_count_position_and_contact_reject(self):
        item=self.portion()
        for count in (True,0,-1,1.5):
            item.count=count;self.assertFalse(self.feed(item))
        item.count=1;item.x=14;self.assertFalse(self.feed(item));item.x=13
        self.a.x=10;self.assertFalse(self.feed(item));self.a.x=12
        from world.local_map import make_tile
        self.e.local_map.tiles[12,13]=make_tile('stone_wall',False,False)
        self.e.local_map.tiles[13,12]=make_tile('door_closed',False,False)
        self.assertFalse(self.feed(item))
        self.e.local_map.tiles[12,13]=make_tile('floor',True,True)
        self.assertTrue(self.feed(item))

    def test_atomic_resource_and_actor_completion_failure(self):
        for corpse in (False,True):
            self.e.local_map.floor_objects.clear()
            item=self.corpse() if corpse else self.portion()
            self.a.ai.scavenging_state={'completed':0}
            old=serialize_item(item)
            def fail():
                self.a.ai.scavenging_state['completed']=9
                raise ValueError('after mutation')
            self.assertFalse(self.feed(item,fail))
            self.assertEqual(serialize_item(item),old)
            self.assertEqual(self.a.ai.scavenging_state,{'completed':0})
            self.assertIs(floor.get_floor_objects(self.e.local_map,13,13)[0],item)

    def test_place_one_preserves_capture_and_rolls_back_partial_write(self):
        item=self.e.item_factory.create('stalker_meat');item.count=3
        self.e.player.inventory.add(item);old=serialize_item(item)
        native=floor.place_floor_object
        def partial(m,x,y,i):
            native(m,x,y,i);raise ValueError('partial output fault')
        with patch.object(floor,'place_floor_object',partial):self.assertFalse(flesh.place_one(self.e,item))
        self.assertEqual(serialize_item(item),old);self.assertFalse(self.e.local_map.floor_objects)
        self.e.data.items['stalker_meat']['weight']=99
        self.assertTrue(flesh.place_one(self.e,item));self.assertEqual(item.count,2)
        portion=floor.get_floor_objects(self.e.local_map,12,12)[0]
        self.assertEqual(portion.weight,item.weight)
        self.assertNotEqual(portion.flesh_resource['uid'],item.flesh_resource['uid'])
        self.assertEqual(portion.count,1)
        self.assertTrue(flesh.place_one(self.e,item));self.assertEqual(item.count,1)
        self.assertTrue(flesh.place_one(self.e,item));self.assertFalse(self.e.player.inventory.contains(item))
        self.assertTrue(any(i is item for i in floor.get_floor_objects(self.e.local_map,12,12)))
        self.assertFalse(flesh.place_one(self.e,item))

    def test_strip_once_capture_all_tiers_and_keep_nonflesh(self):
        self.cutter()
        for source in ('plague_crow','heath_stalker'):
            for tier in (1,2,32):
                self.e.local_map.floor_objects.clear();item=self.corpse(source)
                identity,decay=item.flesh_resource['uid'],item.decay_timer
                self.assertTrue(self.feed(item));self.assertFalse(self.feed(item))
                self.assertEqual((item.flesh_resource['uid'],item.decay_timer),(identity,decay))
                self.cutter(tier)
                self.e.data.entities[source]['butcher_yield']={'tiers':[]}
                with patch('random.randint',lambda lo,hi:hi):
                    self.assertTrue(butcher(self.e,13,13,item))
                outputs=floor.get_floor_objects(self.e.local_map,13,13)
                self.assertFalse(any(flesh.eligible(i) for i in outputs))
                self.assertTrue(any(i.item_id=='animal_bone' for i in outputs))
                self.e.data.entities[source]=copy.deepcopy(self.original.entities[source])

    def test_harvest_failure_retains_stripped_state_and_exact_corpse(self):
        item=self.corpse();self.cutter();self.assertTrue(self.feed(item))
        native=floor.place_floor_object
        def partial(m,x,y,i):native(m,x,y,i);raise ValueError('output failure')
        debt=self.e._move_debt
        with patch.object(floor,'place_floor_object',partial):self.assertFalse(butcher(self.e,13,13,item))
        self.assertEqual(floor.get_floor_objects(self.e.local_map,13,13),[item])
        self.assertEqual(item.flesh_resource['state'],'stripped');self.assertEqual(self.e._move_debt,debt)

    def test_definition_rejects_invalid_flesh_and_source(self):
        creature=copy.deepcopy(self.e.data.entities['plague_crow'])
        creature['butcher_yield']['tiers'][0]['yields'][0]['flesh']=1
        self.assertTrue(profile_errors(creature,self.e.item_factory.create))
        creature['butcher_yield']['tiers'][0]['yields'][0].update(flesh=True,item_id='animal_bone')
        self.assertTrue(profile_errors(creature,self.e.item_factory.create))
        for source in ('sewer_thing','missing','bog_wraith'):
            with self.assertRaises(ValueError):flesh.resolve_source(self.e.data,source)
        self.e.data.entity_definition_sources['plague_crow'].append('duplicate.json')
        with self.assertRaises(ValueError):flesh.resolve_source(self.e.data,'plague_crow')

    def test_native_death_uses_one_corpse_and_keeps_decay(self):
        actor=self.e.creature_factory.spawn('plague_crow',16,16);self.e.entities.append(actor)
        self.e._on_entity_death(actor,observed=False);self.e._on_entity_death(actor,observed=False)
        items=floor.get_floor_objects(self.e.local_map,16,16)
        self.assertEqual(len(items),1);self.assertEqual(items[0].decay_timer,80)
        self.assertEqual(items[0].flesh_resource['source'],'plague_crow')
        self.e._handle_key(pygame.K_F5);self.assertIsNone(self.e.save_manager.last_error)
        self.e._handle_key(pygame.K_F9);self.assertIsNone(self.e.save_manager.last_error)
        self.e._handle_key(pygame.K_F5);self.assertIsNone(self.e.save_manager.last_error)

    def test_malformed_modern_and_duplicate_ids_reject(self):
        item=self.corpse();row=serialize_item(item)
        for field in ('flesh_resource','flesh_resource_version'):
            bad=copy.deepcopy(row);del bad[field]
            with self.assertRaises(ValueError):validate_item(bad,'damaged')
        bad=copy.deepcopy(row);del bad['flesh_resource']['recipe']['tiers'][0]['yields'][0]['flesh']
        with self.assertRaises(ValueError):validate_item(bad,'damaged capture')
        for timer in (-1,True,'80',None,81):
            bad=copy.deepcopy(row);bad['decay_timer']=timer
            with self.assertRaises(ValueError):validate_item(bad,'damaged timer')
        floor.place_floor_object(self.e.local_map,14,13,copy.deepcopy(item))
        self.assertFalse(self.e.save_manager.save(self.e))
        self.assertIn('duplicate',self.e.save_manager.last_error)

    def test_inventory_aliased_split_source_and_stripped_duplicate_harvest_reject(self):
        item=self.e.item_factory.create('crow_meat');item.count=3;self.e.player.inventory.add(item)
        floor.place_container(self.e.local_map,15,15,'crate',[item])
        self.assertFalse(flesh.place_one(self.e,item));self.assertEqual(item.count,3)
        self.e.local_map.container_state.clear()
        corpse=self.corpse();self.assertTrue(self.feed(corpse));self.cutter()
        floor.place_floor_object(self.e.local_map,14,13,copy.deepcopy(corpse))
        self.assertFalse(butcher(self.e,13,13,corpse));self.assertEqual(corpse.flesh_resource['state'],'stripped')

    def test_place_control_cancellation_and_stale_selection_are_free(self):
        item=self.e.item_factory.create('crow_meat');item.count=2;self.e.player.inventory.add(item)
        self.e.inventory_screen.open=True;self.e.inventory_screen._flat=[(item,False,'')]
        before=self.e.world_time.turn
        self.e._handle_key(pygame.K_p);self.assertIsNotNone(self.e._vessel_menu)
        self.e._handle_key(pygame.K_ESCAPE);self.assertEqual(self.e.world_time.turn,before)
        self.e._handle_key(pygame.K_p);item.count=1
        self.e._handle_key(pygame.K_RETURN);self.assertEqual(self.e.world_time.turn,before)
        self.e._handle_key(pygame.K_p);self.e._handle_key(pygame.K_RETURN)
        self.assertEqual(self.e.world_time.turn,before+1)
        self.assertIs(floor.get_floor_objects(self.e.local_map,12,12)[0],item)

    def test_authored_remains_trial_is_atomic_and_has_no_kill_hook(self):
        from engine.scene_generation import populate
        records=[dict(type='remains',x=18,y=18,creature_id='plague_crow')]
        self.e.local_map.set_tile(12,12,'stairs_up',True,True)
        native=floor.place_floor_object
        before=self.e.local_map.tiles.copy()
        def partial(m,x,y,i):native(m,x,y,i);raise ValueError('after partial trial write')
        with patch.object(floor,'place_floor_object',partial):
            with self.assertRaises(ValueError):
                populate(self.e.data,self.e.item_factory,self.e.creature_factory,self.e.local_map,records,authored_arrival=(12,12))
        self.assertFalse(self.e.local_map.floor_objects);self.assertTrue((before==self.e.local_map.tiles).all())
        with patch.object(self.e.hooks,'fire') as hooks:
            actors=populate(self.e.data,self.e.item_factory,self.e.creature_factory,self.e.local_map,records,authored_arrival=(12,12))
            self.assertEqual(actors,[]);hooks.assert_not_called()
        corpse=floor.get_floor_objects(self.e.local_map,18,18)[0]
        self.assertEqual(corpse.flesh_resource['source'],'plague_crow')

    def test_genuine_legacy_fixture_load_save_load(self):
        with zipfile.ZipFile(GAME_ROOT.parent/'evidence/sys-5/legacy-resources.zip') as archive:
            archive.extractall(self.tmp.name)
        from engine.save_manager import SaveManager
        self.e.save_manager=SaveManager(save_root=self.saves)
        self.assertTrue(self.e.save_manager.load(self.e),self.e.save_manager.last_error)
        self.assertFalse(any(flesh.eligible(i) for i in self.e.player.inventory.items))
        self.assertFalse(any(flesh.eligible(i) for rows in self.e.local_map.floor_objects.values() for i in rows))
        self.assertTrue(self.e.save_manager.save(self.e),self.e.save_manager.last_error)
        self.assertTrue(self.e.save_manager.load(self.e),self.e.save_manager.last_error)


class ScavengingTests(unittest.TestCase):
    setUpClass=classmethod(ResourceTests.setUpClass.__func__)
    setUp=ResourceTests.setUp
    portion=ResourceTests.portion
    corpse=ResourceTests.corpse
    def eater(self,host='strike_and_withdraw',xy=(18,12),**tuning):
        from engine.ai_profiles import DEFAULTS,TERRITORY_DEFAULTS
        definition=copy.deepcopy(self.e.data.entities['sewer_thing'])
        definition.update(id='test_scavenger',ai_type='composite',can_cross_chunks=False,can_use_stairs=False,
                          ai_profile=copy.deepcopy(DEFAULTS if host=='strike_and_withdraw' else TERRITORY_DEFAULTS),
                          enemy_scavenging={**dict(version=1,approach_opportunities=8,feed_opportunities=3),**tuning})
        definition['perception'].update(sees_in_dark=False,sight_radius=10,hostile_to=['player'])
        self.e.data.entities['test_scavenger']=definition
        a=self.e.creature_factory.spawn('test_scavenger',*xy)
        self.e.entities=[self.e.player,a];self.e.player.x=40
        return a

    def decision(self,a):
        a.ai.take_turn(a,self.e.local_map,self.e.entities,self.e.player,self.e.log,random.Random(42),1,engine=self.e)

    def test_both_hosts_approach_and_three_paid_feed_decisions(self):
        for host in ('strike_and_withdraw','territorial_guard'):
            self.e.local_map.floor_objects.clear();a=self.eater(host)
            item=self.portion(2,xy=(21,12))
            self.decision(a);self.assertEqual(a.x,19)
            self.decision(a);self.assertTrue(flesh.contact(self.e,a,(21,12)))
            for progress in (1,2):
                before=(a.x,a.y);self.decision(a)
                self.assertEqual((a.x,a.y),before);self.assertEqual(item.count,2)
                self.assertEqual(a.ai.scavenging_state['current']['feeding'],progress)
            self.decision(a);self.assertEqual(item.count,1);self.assertEqual(a.ai.scavenging_state['completed'],1)
            self.assertIsNone(a.ai.scavenging_state['current'])
            if host=='territorial_guard':
                self.assertEqual(a.ai.territory['anchor'],[18,12])
                self.decision(a);self.assertEqual(a.ai.territory['phase'],'return')

    def test_hostility_and_sound_interrupt_in_both_actual_hosts(self):
        from engine.sound import emit
        for host in ('strike_and_withdraw','territorial_guard'):
            self.e.local_map.floor_objects.clear();a=self.eater(host)
            item=self.portion(2,xy=(19,12));self.decision(a)
            self.assertEqual(a.ai.scavenging_state['current']['feeding'],1)
            emit(self.e,18,13,'dismantle',maker=self.e.player)
            self.decision(a);self.assertIsNone(a.ai.scavenging_state['current'])
            self.assertEqual(a.ai.trace[-1]['reason'],'anonymous_sound');self.assertEqual(item.count,2)
            self.e.player.x,self.e.player.y=18,13
            self.decision(a)
            if host=='territorial_guard' and a.ai.target is None:
                self.assertIn(a.ai.trace[-1]['reason'],('return_contact_defence','returning_to_post','at_post'))
                for _ in range(4):
                    if a.ai.target is not None:break
                    self.decision(a)
            self.assertIsNotNone(a.ai.target);self.assertIsNone(a.ai.scavenging_state['current'])
            self.e.player.x=40
            self.decision(a);self.assertIsNone(a.ai.scavenging_state['current'])
            self.assertEqual(item.count,2)

    def test_hidden_moved_food_is_not_followed_or_replaced(self):
        a=self.eater();item=self.portion(xy=(22,12));self.decision(a)
        captured=copy.deepcopy(a.ai.scavenging_state['current'])
        floor.remove_floor_object(self.e.local_map,22,12,item)
        floor.place_floor_object(self.e.local_map,70,12,item)
        replacement=self.portion(xy=(22,12))
        from engine.enemy_scavenging import refresh
        refresh(a.ai,self.e,a,1)
        self.assertIsNone(a.ai.scavenging_state['current'])
        self.assertEqual(captured['x'],22);self.assertEqual(replacement.count,1)

    def test_light_darkvision_and_real_geometry(self):
        a=self.eater();item=self.portion(xy=(23,12))
        self.e.world_time.turn=0
        self.e.local_map.visible[:]=True;self.e.debug_reveal=True
        self.decision(a);self.assertIsNone(a.ai.scavenging_state['current'])
        a.perception.sees_in_dark=True
        self.decision(a);self.assertIsNotNone(a.ai.scavenging_state['current'])
        from engine.enemy_scavenging import retire
        retire(a.ai,'test_reset');a.x,a.y=18,12
        for y in range(self.e.local_map.height):self.e.local_map.set_tile(21,y,'wall',False,False)
        self.decision(a);self.assertIsNone(a.ai.scavenging_state['current'])
        self.e.local_map.set_tile(21,12,'floor',True,True)
        self.decision(a);self.assertIsNotNone(a.ai.scavenging_state['current'])

    def test_defended_acquisition_and_original_excursion(self):
        a=self.eater('territorial_guard');item=self.portion(xy=(23,12))
        for _ in range(3):self.decision(a)
        self.assertIsNone(a.ai.scavenging_state['current']);self.assertEqual((a.x,a.y),(18,12))
        floor.remove_floor_object(self.e.local_map,23,12,item);floor.place_floor_object(self.e.local_map,22,12,item)
        self.decision(a);self.assertIsNotNone(a.ai.scavenging_state['current'])
        a.x=26;self.decision(a)
        self.assertIsNone(a.ai.scavenging_state['current']);self.assertEqual(a.ai.territory['phase'],'return')
        self.assertLess(a.x,26);self.assertEqual(a.ai.territory['anchor'],[18,12])

    def test_partial_attempt_roundtrip_capture_and_departure(self):
        from engine.save_manager import _serialize_entity,_deserialize_entities
        from engine.ai_profiles import validate_saved,depart
        a=self.eater();item=self.portion(2,xy=(19,12));self.decision(a)
        row=_serialize_entity(a);validate_saved(row,self.e.local_map)
        self.e.data.entities['test_scavenger']['enemy_scavenging']['feed_opportunities']=5
        restored=_deserialize_entities([row],self.e)[0];self.e.entities=[self.e.player,restored]
        self.assertEqual(restored.ai.scavenging_config['feed_opportunities'],3)
        self.decision(restored);self.assertEqual(item.count,2)
        self.decision(restored);self.assertEqual(item.count,1)
        self.decision(restored);self.assertIsNotNone(restored.ai.scavenging_state['current'])
        depart(self.e);self.assertIsNone(restored.ai.scavenging_state['current']);self.assertEqual(item.count,1)
        for remove in ('scavenging_version','scavenging'):
            bad=copy.deepcopy(row)
            if remove=='scavenging':del bad['composite'][remove]
            else:del bad[remove]
            with self.assertRaises(ValueError):validate_saved(bad,self.e.local_map)


if __name__=='__main__':unittest.main()
