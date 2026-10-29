"""Real CraftScreen, allocator, placement, and owning-map completion repairs."""
import copy, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from test_effect_persistence import load_data, make_engine
from engine.crafting import plan_craft, commit_craft
from engine.processing_text import completion_text, validate_completion_template
from rendering.craft_screen import CraftScreen

class PreparationRepairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=load_data();pygame.init()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='w5k-preparation-');self.addCleanup(self.tmp.cleanup)
        p=patch('engine.save_manager.SAVE_DIR',Path(self.tmp.name));p.start();self.addCleanup(p.stop)
        self.e=make_engine(self.data);self.e.debug=None
        self.recipe=copy.deepcopy(self.data.recipes['cook_meat']);self.recipe['processing_turns']=3
        self.meat=self.e.item_factory.create('raw_meat_common');self.meat.consumed_on_use=False
        self.e.player.inventory.add(self.meat);self.e.local_map.decor[(12,11)]='campfire_lit'

    def choose(self):
        s=self.e.craft_screen;s.open=True;s._attempt_craft(self.e,self.recipe)
        self.assertTrue(s._choosing);self.assertEqual(len(s._choice_prompts[0]['options']),1)
        s.handle_key(pygame.K_RETURN,self.e)
        return s

    def test_sole_protected_component_affirmative_choice_cancel_and_first_tick(self):
        e=self.e;turn=e.world_time.turn
        self.assertTrue(plan_craft(self.recipe,e.player.inventory,ambient_sources=CraftScreen._build_ambient_sources(e))[1])
        s=e.craft_screen;s.open=True;s._attempt_craft(e,self.recipe)
        s.handle_key(pygame.K_ESCAPE,e);self.assertTrue(e.player.inventory.contains(self.meat));self.assertEqual(turn,e.world_time.turn)
        self.choose();e._handle_key(pygame.K_ESCAPE)
        self.assertTrue(e.player.inventory.contains(self.meat));self.assertEqual(turn,e.world_time.turn)
        self.choose();e._placement_cursor_x,e._placement_cursor_y=12,12
        e._handle_key(pygame.K_RETURN);self.assertTrue(e.player.inventory.contains(self.meat));self.assertEqual(turn,e.world_time.turn)
        e._placement_cursor_x,e._placement_cursor_y=12,11;e._handle_key(pygame.K_RETURN)
        self.assertFalse(e.player.inventory.contains(self.meat));self.assertEqual(turn+1,e.world_time.turn)
        self.assertEqual(2,e.local_map.processing_layer[(12,11)]['turns_remaining'])
        self.assertEqual('campfire_lit',e.local_map.decor[(12,11)])
        e._handle_key(pygame.K_z);e._handle_key(pygame.K_z)
        self.assertNotIn((12,11),e.local_map.processing_layer)
        self.assertEqual(['cooked_meat'],[i.item_id for i in e.local_map.floor_objects[(12,11)]])

    def test_picker_and_placement_recheck_conditions_and_exact_owned_instance(self):
        for failure in ('picker_heat','placement_owner','placement_heat'):
            with self.subTest(failure=failure):
                e=make_engine(self.data);e.debug=None;meat=e.item_factory.create('raw_meat_common');meat.consumed_on_use=False;e.player.inventory.add(meat)
                e.local_map.decor[(12,11)]='campfire_lit';turn=e.world_time.turn
                s=e.craft_screen;s.open=True;s._attempt_craft(e,self.recipe)
                if failure=='picker_heat':e.local_map.decor.clear()
                s.handle_key(pygame.K_RETURN,e)
                if failure=='placement_owner':
                    e.player.inventory.remove(meat);sibling=e.item_factory.create('raw_meat_common');sibling.consumed_on_use=False;e.player.inventory.add(sibling)
                if failure=='placement_heat':e.local_map.decor.clear()
                if failure!='picker_heat':e._handle_key(pygame.K_RETURN)
                self.assertFalse(e.local_map.processing_layer);self.assertEqual(turn,e.world_time.turn)
                self.assertEqual(1,len(e.player.inventory.items))

    def due(self,text='Ready {item_name}'):
        e=self.e;e.local_map.decor[(14,12)]='drying_herb'
        record=dict(item_id='cooked_meat',turns_remaining=1,decor_id='drying_herb',source='drying',completion_message=text,on_fire=False)
        e.local_map.processing_layer[(14,12)]=record
        return record

    def test_completion_valid_and_historical_bad_text_produce_exactly_once(self):
        for text in ('Ready {item_name}','Ready {unknown}','{item_name!r}','{'):
            self.e.local_map.floor_objects.clear();self.due(text)
            self.e._tick_processing_map(self.e.local_map,active=True)
            self.e._tick_processing_map(self.e.local_map,active=True)
            self.assertEqual(1,len(self.e.local_map.floor_objects[(14,12)]));self.assertFalse(self.e.local_map.processing_layer)
            self.assertNotIn((14,12),self.e.local_map.decor)
        self.assertEqual(completion_text('{unknown}','meal'),'meal is ready.')

    def test_missing_and_invalid_output_retain_due_work_marker_without_log_flood(self):
        e=self.e;record=self.due();data=copy.copy(self.data);data.items=dict(self.data.items);e.data=e.item_factory.data=data
        original=data.items.pop('cooked_meat')
        for _ in range(3):e._tick_processing_map(e.local_map,active=True)
        self.assertIs(record,e.local_map.processing_layer[(14,12)]);self.assertEqual(record['turns_remaining'],0)
        self.assertEqual('drying_herb',e.local_map.decor[(14,12)]);self.assertFalse(e.local_map.floor_objects)
        self.assertEqual(1,sum(m.count for m in e.log.messages if 'unfinished work remains' in m.text))
        data.items['cooked_meat']={**original,'weight':True}
        e._tick_processing_map(e.local_map,active=True);self.assertIs(record,e.local_map.processing_layer[(14,12)])
        # A fresh catalogue, with the reference restored, resumes without restart.
        from engine.item_factory import ItemFactory
        e.data=load_data();e.item_factory=ItemFactory(e.data)
        e._tick_processing_map(e.local_map,active=True)
        self.assertFalse(e.local_map.processing_layer);self.assertEqual(1,len(e.local_map.floor_objects[(14,12)]))

    def test_conjunction_quantities_overlap_and_retained_tools_use_distinct_instances(self):
        from entities.item import Item
        from components.inventory import Inventory
        def item(name,protected=False):
            i=Item(0,0,'generic_item',name,name);i.keywords=[dict(tag='edible',tier=2),dict(tag='vital',tier=2)];i.consumed_on_use=not protected;return i
        recipe=dict(requires_single_item=dict(tags=[dict(tag='edible'),dict(tag='vital')],max_quantity=2),components=[dict(tag='vital')],tools=[dict(tag='edible')])
        inv=Inventory(100);inv.items=[item(str(n)) for n in range(3)]
        self.assertTrue(plan_craft(recipe,inv)[1]);inv.items.append(item('tool',True))
        selected,missing=plan_craft(recipe,inv);self.assertFalse(missing);self.assertEqual(len({id(i) for i in selected}),4)
        e=self.e;e.player.inventory=inv;self.assertTrue(commit_craft(e,recipe,selected,[]));self.assertEqual(['tool'],[i.item_id for i in inv.items])
        inv.items=[item('protected',True)];self.assertTrue(plan_craft(dict(requires_single_item=[dict(tag='edible')]),inv)[1])

    def test_real_turn_ticks_distinct_hot_owners_once_and_leaves_cold_map_frozen(self):
        from engine.save_manager import CachedChunk
        from world.local_map import LocalMap
        e=self.e;active=e.local_map;surface=LocalMap();underground=LocalMap();cold=LocalMap()
        record=dict(item_id='cooked_meat',turns_remaining=2,decor_id='',source='drying',completion_message='{item_name}',on_fire=False)
        for m in (active,surface,underground,cold):m.processing_layer[(14,12)]=copy.deepcopy(record)
        cache=e.save_manager.cache
        cache.hot[(0,0)]=CachedChunk(active,[]);cache.hot[(1,0)]=CachedChunk(surface,[])
        cache.submap_hot['distinct']=CachedChunk(underground,[]);cache.submap_hot['alias']=CachedChunk(surface,[])
        # The cold map is intentionally absent from the live owner cache.
        e._handle_key(pygame.K_z)
        for m in (active,surface,underground):self.assertEqual(1,m.processing_layer[(14,12)]['turns_remaining'])
        self.assertEqual(2,cold.processing_layer[(14,12)]['turns_remaining'])
        e._handle_key(pygame.K_z)
        for m in (active,surface,underground):
            self.assertFalse(m.processing_layer);self.assertEqual(1,len(m.floor_objects[(14,12)]))
        self.assertFalse(cold.floor_objects)

if __name__=='__main__':unittest.main()
