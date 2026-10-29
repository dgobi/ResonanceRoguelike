"""Real consumer/callers; controlled randint only in focused branch/fault tests."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame
from test_effect_persistence import load_data, make_engine
from engine.harvesting import profile_errors, select_tier
from engine.engine import GameMode
from generation import floor_object_utils as floor
from world.local_map import LocalMap
from engine.save_components import serialize_item


class HarvestConsumers(unittest.TestCase):
    @classmethod
    def setUpClass(cls): pygame.init(); cls.base = load_data()
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="w5n-harvest-"); self.addCleanup(self.tmp.cleanup)
        p = patch("engine.save_manager.SAVE_DIR", Path(self.tmp.name)/"saves"); p.start(); self.addCleanup(p.stop)
        self.data = copy.copy(self.base); self.data.entities = copy.deepcopy(self.base.entities)
        self.data.items = copy.deepcopy(self.base.items)
        self.e = make_engine(self.data); self.e.debug = None; self.e.local_map.visible[:] = True
        self.profile(dict(min_cutting_tier=0, yields=[dict(item_id="raw_meat_common", quantity_min=2, quantity_max=2)]))
    def profile(self, *tiers, **values):
        self.data.entities["sewer_thing"]["butcher_yield"] = dict(tiers=list(tiers), **values)
    def corpse(self, identifier="sewer_thing"):
        e = self.e
        actor = e.creature_factory.spawn(identifier, 12, 12); e.entities.append(actor)
        e._on_entity_death(actor)
        corpse = next(i for i in reversed(floor.get_floor_objects(e.local_map,12,12)) if getattr(i,"source_creature",None)==identifier)
        e.entities.remove(actor)
        return corpse
    def cut(self, tier=2):
        e = self.e; item = e.item_factory.create("crude_blade")
        e.player.inventory.add(item); e.item_system.use(item,e)
        item.keywords = [dict(tag="cutting",tier=tier)]
        return item
    def outputs(self): return [i for rows in self.e.local_map.floor_objects.values() for i in rows if i.item_id=="raw_meat_common"]
    def commit(self, corpse): return self.e._interactable_butcher(12,12,corpse)

    def test_exact_same_id_selection_from_pickup_and_both_cursor_routes(self):
        e = self.e; first, second = self.corpse(), self.corpse()
        other = e.item_factory.create("wood_bundle"); floor.place_floor_object(e.local_map,12,12,other)
        self.assertFalse(e._pick_up_item()); prompt=e.interaction_cursor._selection_prompt
        self.assertIs(prompt["items"][1],second);prompt["selected"]=1
        before=e.world_time.turn; e.interaction_cursor._handle_selection_key(pygame.K_RETURN,e)
        self.assertEqual(e.world_time.turn-before,5);self.assertEqual(e._move_debt,0)
        self.assertIn(first,floor.get_floor_objects(e.local_map,12,12));self.assertNotIn(second,floor.get_floor_objects(e.local_map,12,12));self.assertIn(other,floor.get_floor_objects(e.local_map,12,12))
        self.assertFalse(self.commit(second)); self.assertEqual(len(self.outputs()),2)
        # Single-item pickup and direct cursor route each carry their actual item.
        for it in list(floor.get_floor_objects(e.local_map,12,12)):
            if it is not first: floor.remove_floor_object(e.local_map,12,12,it)
        with patch.object(e,"_interactable_butcher",return_value=False) as call:
            e._pick_up_item();self.assertIs(call.call_args.args[2],first)
            e.interaction_cursor.enter([(12,12)],12,12);e.interaction_cursor._interact(e)
            self.assertIs(call.call_args.args[2],first)

    def test_stale_scene_location_and_legacy_ambiguity_never_substitute(self):
        e=self.e; first,second=self.corpse(),self.corpse()
        self.assertFalse(e._interactable_butcher(12,12))
        e._pick_up_item();prompt=e.interaction_cursor._selection_prompt
        e.current_submap_id="different-scene"
        e.interaction_cursor._handle_selection_key(pygame.K_RETURN,e)
        self.assertEqual(len(self.outputs()),0);self.assertIn(first,floor.get_floor_objects(e.local_map,12,12))
        e.current_submap_id=None
        self.assertFalse(e._interactable_butcher(12,12,first,scene=LocalMap()))
        floor.remove_floor_object(e.local_map,12,12,first)
        self.assertFalse(self.commit(first));self.assertTrue(e._interactable_butcher(12,12))
        self.assertNotIn(second,floor.get_floor_objects(e.local_map,12,12))
        e.local_map.decor[12,12]="corpse";self.assertFalse(e._interactable_butcher(12,12))

    def test_owned_copied_cutting_tier_ties_independent_rolls_and_tool_retention(self):
        e=self.e; tool=self.cut(3);self.data.items[tool.item_id]["keywords"]=[dict(tag="cutting",tier=1)]
        rows=[dict(item_id="raw_meat_common",quantity_min=1,quantity_max=2)]*2
        self.profile(dict(min_cutting_tier=1,yields=[]),dict(min_cutting_tier=2,yields=rows),dict(min_cutting_tier=2,yields=[]))
        corpse=self.corpse();before=e._move_debt
        with patch("random.randint",side_effect=[1,2]) as rng:self.assertTrue(self.commit(corpse))
        self.assertEqual(rng.call_args_list,[unittest.mock.call(1,2),unittest.mock.call(1,2)])
        self.assertEqual(len(self.outputs()),3);self.assertEqual(len({id(i) for i in self.outputs()}),3)
        self.assertEqual(e._move_debt-before,3);self.assertTrue(e.player.inventory.contains(tool));self.assertIs(e.player.equipment.slots["weapon"],tool)

    def test_unowned_or_flag_only_cutter_refuses_one_turn_and_perk_uses_actual_tier(self):
        e=self.e;tool=self.cut(5);e.player.inventory.items.remove(tool)
        self.profile(dict(min_cutting_tier=32,yields=[]));corpse=self.corpse()
        before=e.world_time.turn;e.interaction_cursor.enter([(12,12)],12,12);e.interaction_cursor._interact(e)
        self.assertEqual(e.world_time.turn,before+1);self.assertEqual(e._move_debt,0);self.assertIn(corpse,floor.get_floor_objects(e.local_map,12,12))
        e.player.inventory.add(tool);e.player.equipment.slots["weapon"]=None
        self.assertTrue(tool.equipped)  # a flag alone, without the slot, grants nothing
        self.assertTrue(self.commit(corpse));self.assertEqual(e._move_debt,0)
        self.assertIn(corpse,floor.get_floor_objects(e.local_map,12,12))
        with patch.object(e.player.perks,"has",return_value=True):self.assertTrue(self.commit(corpse))
        self.assertEqual(e._move_debt,36);self.assertFalse(self.outputs())
        e._move_debt=0;self.profile(dict(min_cutting_tier=32,yields=[dict(item_id="raw_meat_common",quantity_min=0,quantity_max=2)]));corpse=self.corpse()
        with patch.object(e.player.perks,"has",return_value=True),patch("random.randint",return_value=1):self.assertTrue(self.commit(corpse))
        self.assertEqual(len(self.outputs()),1);self.assertEqual(e._move_debt,36)

    def test_default_null_empty_profile_empty_tier_and_zero_roll(self):
        e=self.e
        for value in (None,{}):
            if value is None:self.data.entities["sewer_thing"].pop("butcher_yield",None)
            else:self.data.entities["sewer_thing"]["butcher_yield"]=value
            corpse=self.corpse();self.assertFalse(self.commit(corpse));self.assertEqual(e._move_debt,0);floor.remove_floor_object(e.local_map,12,12,corpse)
        for profile in (dict(decay_turns=None),dict(tiers=[])):
            self.data.entities["sewer_thing"]["butcher_yield"]=profile;corpse=self.corpse();self.assertTrue(self.commit(corpse));self.assertEqual(e._move_debt,0);self.assertIn(corpse,floor.get_floor_objects(e.local_map,12,12));floor.remove_floor_object(e.local_map,12,12,corpse)
        for tier in (dict(min_cutting_tier=0),dict(min_cutting_tier=0,yields=[]),dict(min_cutting_tier=0,yields=[dict(item_id="raw_meat_common",quantity_max=0)])):
            self.profile(tier);corpse=self.corpse();self.assertTrue(self.commit(corpse));self.assertNotIn(corpse,floor.get_floor_objects(e.local_map,12,12));self.assertEqual(e._move_debt,4);e._move_debt=0
        self.assertFalse(self.outputs())

    def test_faults_preserve_exact_owners_debt_and_retry_without_duplicate_rewards(self):
        for fault in ("missing","invalid","late_factory","placement_false","partial_false","partial_exception"):
            with self.subTest(fault=fault):
                e=self.e;corpse=self.corpse();other=e.item_factory.create("wood_bundle");floor.place_floor_object(e.local_map,12,12,other)
                before=list(floor.get_floor_objects(e.local_map,12,12));e._move_debt=.5
                create=e.item_factory.create;place=floor.place_floor_object
                def factory(identifier,*args,**kwargs):
                    factory.calls+=1
                    if fault=="missing":return None
                    if fault=="late_factory" and factory.calls==3:raise RuntimeError("late construction")
                    item=create(identifier,*args,**kwargs)
                    if fault=="invalid":item.keywords=None
                    return item
                factory.calls=0
                def placement(local,x,y,item):
                    placement.calls+=1
                    if placement.calls==2:
                        if fault=="partial_exception":place(local,x,y,item);raise RuntimeError("after write")
                        if fault=="partial_false":place(local,x,y,item);return False
                        if fault=="placement_false":return False
                    return place(local,x,y,item)
                placement.calls=0
                with patch.object(e.item_factory,"create",side_effect=factory),patch.object(floor,"place_floor_object",side_effect=placement):
                    self.assertFalse(self.commit(corpse))
                self.assertEqual(floor.get_floor_objects(e.local_map,12,12),before);self.assertEqual(e._move_debt,.5)
                self.assertTrue(self.commit(corpse));self.assertEqual(len(self.outputs()),2);self.assertEqual(e._move_debt,4.5)
                self.assertIn(other,floor.get_floor_objects(e.local_map,12,12));self.assertFalse(self.commit(corpse));self.assertEqual(len(self.outputs()),2)
                for item in list(floor.get_floor_objects(e.local_map,12,12)):floor.remove_floor_object(e.local_map,12,12,item)

    def test_harvest_debt_stops_draining_after_ordinary_player_death(self):
        e=self.e;corpse=self.corpse();e.interaction_cursor.enter([(12,12)],12,12)
        advance=e._advance_turn;calls=[]
        def death_during_work():
            calls.append(1);advance()
            if len(calls)==2:e._player_is_dead=True
        with patch.object(e,"_advance_turn",side_effect=death_during_work):e.interaction_cursor._interact(e)
        self.assertEqual(len(calls),2);self.assertEqual(e._move_debt,3)
        self.assertNotIn(corpse,floor.get_floor_objects(e.local_map,12,12));self.assertEqual(len(self.outputs()),2)

    def test_malformed_profiles_references_and_aggregate_limits_refuse_freely(self):
        for value in (None,dict(tiers=None),dict(decay_turns=True),dict(decay_turns=2**53),dict(tiers=[dict(min_cutting_tier=33)]),dict(tiers=[dict(yields=[dict(item_id="raw_meat_common",quantity_min=2)])]),dict(tiers=[dict(yields=[dict(item_id="raw_meat_common",quantity_max=32)]*3)])):
            self.data.entities["sewer_thing"]["butcher_yield"]=value;corpse=self.corpse();self.assertFalse(self.commit(corpse));self.assertEqual(self.e._move_debt,0);self.assertFalse(self.outputs());floor.remove_floor_object(self.e.local_map,12,12,corpse)
        self.profile(dict(min_cutting_tier=0,yields=[dict(item_id="missing")]))
        corpse=self.corpse();self.assertFalse(self.commit(corpse));self.assertEqual(self.e._move_debt,0)

    def test_death_decay_and_save_restore_preserve_copied_countdown_and_identity(self):
        e=self.e;self.profile(decay_turns=9);finite=self.corpse()
        self.profile(decay_turns=None);eternal=self.corpse()
        self.data.entities["sewer_thing"].pop("butcher_yield");default=self.corpse();self.assertEqual(default.decay_timer,200)
        e._advance_turn();self.assertEqual(finite.decay_timer,8);self.assertIsNone(eternal.decay_timer)
        before=[serialize_item(i) for i in floor.get_floor_objects(e.local_map,12,12)]
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        self.profile(decay_turns=40)
        self.assertTrue(e.save_manager.load(e),e.save_manager.last_error)
        restored=floor.get_floor_objects(e.local_map,12,12);self.assertEqual([serialize_item(i) for i in restored],before)
        self.assertEqual(restored[0].source_creature,"sewer_thing");self.assertEqual(restored[0].decay_timer,8)
        self.assertIsNone(restored[1].decay_timer)
        # Deliberate current-table removal makes these saved remains unusable,
        # without resetting their copied name/source or remaining countdown.
        self.data.entities["sewer_thing"].pop("butcher_yield")
        self.assertFalse(e._interactable_butcher(12,12,restored[0]))
        self.assertEqual([serialize_item(i) for i in restored],before)
        for value in (0,1):
            self.profile(decay_turns=value);corpse=self.corpse();e._advance_turn();self.assertNotIn(corpse,floor.get_floor_objects(e.local_map,12,12))


if __name__=="__main__": unittest.main()
