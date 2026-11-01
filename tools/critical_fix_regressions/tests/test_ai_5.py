"""Full-paralysis integration risks. Doses/combat setup are controlled fixtures.

Ordinary real-damage, ownership and old-save witnesses live in verify_ai_5_play.
"""
import copy
import random
import unittest
from unittest.mock import patch
import pygame
import test_ai_3 as ai3
from engine.venom import dose, fully_paralysed, DEFAULTS, restore
from engine.combat import resolve_attack
from engine.save_components import serialize_item, restore_item
from engine.save_manager import _serialize_entity, _deserialize_entities, _validate_entities


class FullParalysisTests(unittest.TestCase):
    setUpClass = classmethod(ai3.VenomTests.setUpClass.__func__)
    setUp = ai3.VenomTests.setUp
    actor = ai3.VenomTests.actor
    hit = ai3.VenomTests.hit
    phase = ai3.VenomTests.phase
    decision = ai3.VenomTests.decision
    paralysis = ai3.VenomTests.paralysis

    def add(self, identifier):
        item=self.e.item_factory.create(identifier)
        self.assertIsNotNone(item,identifier)
        self.e.player.inventory.add(item)
        return item

    def test_fresh_defaults_and_p1_p2_saved_meaning_without_mutation(self):
        self.assertEqual(dict(warning_phases=3,paralysis_phases=3,recovery_phases=4),DEFAULTS)
        for phases in (1,2,3):
            restore(self.e.player,None);self.source.ai.profile['paralysis_phases']=phases
            self.paralysis();original=copy.deepcopy(dose(self.e.player))
            for _ in range(3):
                self.assertTrue(fully_paralysed(self.e.player))
                self.assertTrue(fully_paralysed(self.e.player.fighter))
                self.assertFalse(self.e.player.fighter.can_attack())
            self.assertEqual(original,dose(self.e.player))
            for _ in range(phases):self.phase()
            self.assertFalse(fully_paralysed(self.e.player))
            self.assertTrue(self.e.player.fighter.can_attack())

    def test_real_committers_reject_owned_use_equip_drop_floor_container_and_craft(self):
        from engine.item_transfers import drop,take_floor,take_container
        from engine.crafting import plan_craft,commit_craft
        e=self.e;wood=[self.add('wood_bundle') for _ in range(2)]
        torch=self.add('tallow_torch');remedy=self.add('venom_treatment');self.add('crude_blade')
        floor=e.item_factory.create('wood_bundle');e.local_map.floor_objects[(12,12)]=[floor]
        stored=e.item_factory.create('wood_bundle');e.local_map.container_state[(13,12)]=dict(state='open',items=[stored])
        recipe=e.data.recipes['campfire'];plan,missing=plan_craft(recipe,e.player.inventory)
        self.assertFalse(missing)
        self.paralysis();before=[serialize_item(i) for i in e.player.inventory.items];turn=e.world_time.turn
        for item in (torch,remedy):
            self.assertFalse(e.item_system.use(item,e));self.assertFalse(e.item_system.last_use_committed)
        self.assertFalse(drop(e,wood[0]));self.assertFalse(take_floor(e,floor))
        self.assertFalse(take_container(e,13,12,stored));self.assertFalse(commit_craft(e,recipe,plan))
        e.craft_screen._attempt_craft(e,recipe)
        self.assertEqual(before,[serialize_item(i) for i in e.player.inventory.items])
        self.assertEqual(turn,e.world_time.turn);self.assertEqual([floor],e.local_map.floor_objects[(12,12)])
        self.assertEqual([stored],e.local_map.container_state[(13,12)]['items'])

    def test_stale_confirmations_discard_without_cost_or_deferred_action(self):
        from engine.effect_lifecycle import confirm_consume,throw_key
        from engine.engine import GameMode
        e=self.e;wight=self.add('wight_concentrate');flint=self.add('flint_shard')
        e._pending_consume=dict(item=wight,item_def=e.data.items[wight.item_id])
        self.paralysis();turn=e.world_time.turn;exposure=e.resonance_exposure
        confirm_consume(e,pygame.K_y)
        self.assertIsNone(e._pending_consume);self.assertTrue(e.player.inventory.contains(wight))
        self.assertEqual(exposure,e.resonance_exposure)
        e._pending_throw=dict(item=flint,item_def=e.data.items[flint.item_id],kind='flint',map=e.local_map)
        e.mode=GameMode.PLACEMENT_CURSOR;throw_key(e,pygame.K_RETURN)
        self.assertIsNone(e._pending_throw);self.assertEqual(GameMode.LOCAL,e.mode)
        self.assertTrue(e.player.inventory.contains(flint))
        c=e.interaction_cursor;c._dismantle_prompt={'stale':'deliberately unreadable'}
        c._handle_dismantle_key(pygame.K_RETURN,e);self.assertIsNone(c._dismantle_prompt)
        c._selection_prompt=dict(items=[flint],selected=0,lx=12,ly=12)
        c._handle_selection_key(pygame.K_RETURN,e);self.assertIsNone(c._selection_prompt)
        e._pending_placement_tile='campfire_unlit';e._pending_placement_recipe={'invalid':'stale'}
        e.mode=GameMode.PLACEMENT_CURSOR;e._handle_key_placement(pygame.K_RETURN)
        self.assertIsNone(e._pending_placement_recipe);self.assertEqual(GameMode.LOCAL,e.mode)
        self.assertEqual(turn,e.world_time.turn)

    def test_wait_is_one_phase_no_rain_or_press_and_passive_fuel_still_consumes(self):
        from test_gameplay_g12 import use
        e=self.e;torch=self.add('tallow_torch');use(e,torch)
        torch.turns_lit=e.player.light_source._burn_turns-1
        self.paralysis();e.entities=[e.player];e._free_move_pending=True
        turn=e.world_time.turn;hunger=e.player.needs.hunger
        with patch.object(e,'_tick_rain_collection',side_effect=AssertionError('active rain collection')):
            e._handle_key_local(pygame.K_PERIOD)
        self.assertEqual(turn+1,e.world_time.turn);self.assertEqual(1,dose(e.player)['remaining'])
        self.assertFalse(e._free_move_pending);self.assertFalse(e.player.inventory.contains(torch))
        self.assertGreater(e.player.needs.hunger,hunger)
        e._handle_key_local(pygame.K_PERIOD);self.assertEqual('recovery',dose(e.player)['stage'])

    def test_defences_suppressed_for_player_and_rival_passive_av_retained(self):
        e=self.e;rival=e.creature_factory.spawn('highland_bandit',14,12);e.entities.append(rival)
        self.paralysis();rival.fighter._numbing_venom=copy.deepcopy(dose(e.player))
        body={'locations':[dict(id='torso',size=1,damage_multiplier=1)]}
        for actor in (e.player,rival):
            f=actor.fighter;f.effective_av=2
            r=resolve_attack('insect',actor.name,f,body,dict(damage_dice='1d1',damage_bonus=6),{},
                             random.Random(5),defender_dodge_chance=1,shield_def=dict(block_chance=1,block_value=100))
            self.assertFalse(r.dodged);self.assertFalse(r.blocked)
            self.assertEqual(r.damage_raw-2,r.damage_dealt);self.assertEqual(2,f.effective_av)

    def test_warning_action_settles_owed_phases_without_delayed_extra_grant(self):
        from types import SimpleNamespace
        e=self.e;self.hit();e.entities=[e.player];turn=e.world_time.turn
        action=SimpleNamespace(turn_cost=6,free_move=True)
        with patch.object(e,'_try_moveset_action',return_value=action),patch.object(e,'_weapon_action_phases',return_value=6):
            e._handle_key_local(e.display.MOVESET_KEY_1)
        self.assertEqual(turn+6,e.world_time.turn)
        self.assertEqual('recovery',dose(e.player)['stage'])
        self.assertFalse(e._free_move_pending)

    def test_no_reaction_denial_flood_and_perks_are_view_only(self):
        e=self.e;self.paralysis();count=copy.deepcopy(e.log.messages);turn=e.world_time.turn
        e._handle_key(pygame.K_h);self.assertTrue(e.health_screen.open)
        e._handle_key(pygame.K_ESCAPE)
        e._handle_key(pygame.K_l);self.assertTrue(e.lexicon_screen.open)
        e._handle_key(pygame.K_ESCAPE)
        e.player.level.perk_points=100
        perk=next(iter(e.data.perks));e.perk_screen._flat=[(perk,False,'')];e.perk_screen.selected=0
        before=copy.deepcopy(e.player.perks.acquired)
        self.assertFalse(e.perk_screen._can_afford(perk,e))
        e.perk_screen.open=True;e.perk_screen._confirming=True
        e.perk_screen.handle_key(pygame.K_DOWN,e)
        self.assertFalse(e.perk_screen._confirming)
        for _ in range(5):
            self.assertFalse(e._player_attack(self.source))
            self.assertFalse(e._grass_concealment_reaction(self.source,(self.source.x+1,self.source.y)))
            e._handle_key_local(pygame.K_DOWN);e.perk_screen._commit(e)
        self.assertEqual(count,e.log.messages);self.assertEqual(before,e.player.perks.acquired)
        self.assertEqual(100,e.player.level.perk_points);self.assertEqual(turn,e.world_time.turn)

    def test_wandering_and_hunter_no_physical_dispatch_or_banked_burst(self):
        e=self.e;v=e.creature_factory.spawn('highland_bandit',14,12);e.entities.append(v)
        self.source.perception.hostile_to=[v.perception.faction];self.paralysis(v)
        with patch.object(v.ai,'_act',side_effect=AssertionError('physical dispatch')):
            self.decision(v)
        v._ambush_ready=True;v.ai.move_accumulator=.25;e.entities=[e.player,v]
        e.data.entities['highland_bandit']['speed']=2
        e._advance_turn()
        self.assertFalse(v._ambush_ready);self.assertLess(v.ai.move_accumulator,1)
        hunter=self.actor(x=16);hunter.fighter._numbing_venom=copy.deepcopy(dose(v))
        before=hunter.ai.snapshot();self.decision(hunter)
        for key in ('withdraw_left','hold_left','approach_left','no_progress'):
            self.assertEqual(before['state'][key],hunter.ai.snapshot()['state'][key])

    def test_stock_prose_exact_refresh_preserves_custom_instances_and_strict_validation(self):
        from engine.stock_prose import KNOWN
        e=self.e;remedy=e.item_factory.create('venom_treatment');row=serialize_item(remedy)
        row['description']=next(iter(KNOWN['venom_treatment']['description']))
        restore_item(remedy,row);self.assertEqual(e.data.items[remedy.item_id]['description'],remedy.description)
        row['description']='Owner-written draught';restore_item(remedy,row)
        self.assertEqual('Owner-written draught',remedy.description)
        import pickle
        from engine.save_manager import ChunkCache,CachedChunk
        floor=e.item_factory.create('venom_treatment');floor.description=next(iter(KNOWN['venom_treatment']['description']))
        e.local_map.floor_objects[(12,12)]=[floor]
        e.local_map.container_state[(13,12)]=dict(state='open',items=[remedy])
        path=self.root/'prose-scene.pkl';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(pickle.dumps(CachedChunk(e.local_map,[])))
        loaded_map=ChunkCache._read(path).local_map
        self.assertEqual(e.data.items['venom_treatment']['description'],loaded_map.floor_objects[(12,12)][0].description)
        self.assertEqual('Owner-written draught',loaded_map.container_state[(13,12)]['items'][0].description)
        a=e.creature_factory.spawn('timed_amber_hunter',14,12);saved=_serialize_entity(a)
        saved['name']='Timed Amber Hunter';loaded=_deserialize_entities([saved],e)[0]
        self.assertEqual('Amber Whine Beetle',loaded.name)
        saved['name']='Owner Beetle';self.assertEqual('Owner Beetle',_deserialize_entities([saved],e)[0].name)
        saved['composite']['state']['withdrawal_told']='yes'
        with self.assertRaises(ValueError):_validate_entities([saved],e.creature_factory)

    def test_retreat_prose_only_after_real_step_and_survives_roundtrip(self):
        e=self.e;a=self.source;a.ai.profile['retreat_distance']=4
        with patch('engine.combat.resolve_attack',return_value=ai3.CombatResult(hit=True,damage_dealt=1)):
            a.ai.cancel(a,'fixture');a.x,a.y=13,12;self.decision(a)
        self.assertFalse(any('skitters away' in m.text for m in e.log.messages))
        for x in range(12,15):
            for y in range(11,14):
                if (x,y) not in ((12,12),(13,12)):e.local_map.set_tile(x,y,'wall',False,False)
        self.decision(a)
        self.assertFalse(any('skitters away' in m.text for m in e.log.messages))
        for x in range(12,15):
            for y in range(11,14):e.local_map.set_tile(x,y,'floor',True,True)
        self.decision(a)
        self.assertTrue(a.ai.withdrawal_told)
        count=sum('skitters away' in m.text for m in e.log.messages)
        row=_serialize_entity(a);loaded=_deserialize_entities([row],e)[0]
        e.entities.remove(a);e.entities.append(loaded);self.decision(loaded)
        self.assertEqual(count,sum('skitters away' in m.text for m in e.log.messages))

    def test_runtime_debug_override_controls_incoming_and_outgoing_formula(self):
        from components.ai import _monster_attack_result
        e=self.e
        for debug in (None,object()):
            e.debug=debug;e.log.messages.clear();e.player.fighter.hp=60
            _monster_attack_result(self.source,e.player,e,defensive=True)
            self.assertEqual(bool(debug),any('AV=' in m.text for m in e.log.messages))
            e.log.messages.clear();self.source.fighter.hp=60
            e._player_attack(self.source)
            self.assertEqual(bool(debug),any('AV=' in m.text for m in e.log.messages))
