"""G19 controlled contact, ambush lifecycle and terrain perception fixtures.

Actors/terrain are staged; deterministic combat results isolate commitment from
balance. Only temporary save roots are opened. No natural encounter claim.
"""
import copy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pygame
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from test_gameplay_g18 import equip, timing
import test_combat_routes as combat_routes
from components.ai import (_monster_attack_entity, _creature_can_see_player,
                           _player_concealed, AIState)
from engine.combat import CombatResult
from engine.creature_abilities import _ability_stone_lurker
from engine.save_manager import _serialize_entity
from engine.spatial import melee_contact, terrain_line
from world.local_map import LocalMap, make_tile
from world.world_map import Chunk, RegionType, SubMap


def physical(e):
    return dict(timing=timing(e), position=[e.player.x, e.player.y],
                hp=e.player.fighter.hp, cover=_player_concealed(e.player, e.local_map, e),
                actors=[_serialize_entity(a) for a in e.entities if a is not e.player])


def cold(root):
    with patch('engine.save_manager.SAVE_DIR', Path(root)):
        e = make_engine(load_data()); e.debug = None
        assert e.save_manager.load(e), e.save_manager.last_error
        snapshot=physical(e)
        e.reality_bubble.update(e.world_x,e.world_y,e.world_map)
        for a in e.entities:
            if not getattr(a,'_ambush_ready',False): continue
            def tick():
                e.ai_system.process(e.entities,e.player,e.local_map,e.world_map,
                                    e.world_x,e.world_y,e.log,e.world_time,e.data,engine=e)
            hp=e.player.fighter.hp
            with patch.object(a.ai,'take_turn'), patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)) as resolve:
                tick(); assert a._ambush_ready; resolve.assert_not_called()
                assert hp==e.player.fighter.hp
                a.x,a.y=e.player.x+1,e.player.y
                e.local_map.set_tile(a.x,a.y,'grass',True,True)
                tick(); assert not a._ambush_ready; tick(); resolve.assert_called_once()
        return snapshot


class ContactAndCoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(); pygame.init()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='resonance-g19-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'saves'
        save = patch('engine.save_manager.SAVE_DIR', self.root)
        save.start(); self.addCleanup(save.stop)
        self.e = make_engine(self.data); self.e.debug = None
        self.e.rng = random.Random(29417)
        self.e.reality_bubble.update(0,0,self.e.world_map)

    def actor(self, iid='hollow_revenant', x=13, y=12):
        a = self.e.creature_factory.spawn(iid, x, y)
        self.e.entities.append(a)
        return a

    def tick(self):
        e = self.e
        e.ai_system.process(e.entities, e.player, e.local_map, e.world_map,
                            e.world_x, e.world_y, e.log, e.world_time, e.data, engine=e)

    def seen(self, a, local_map=None, player=None, light=1):
        e = self.e
        return _creature_can_see_player(a, player or e.player,
                                       local_map or e.local_map, light, engine=e)

    def cover(self):
        return _player_concealed(self.e.player, self.e.local_map, self.e)

    def test_contact_geometry_all_neighbors_bounds_coincidence_and_distance(self):
        m = self.e.local_map
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                self.assertEqual(bool(dx or dy), melee_contact(m,12,12,12+dx,12+dy))
        for end in ((14,12),(15,12),(12,14),(15,15),(-1,12),(m.width,12)):
            self.assertFalse(melee_contact(m,12,12,*end),end)
            self.assertFalse(melee_contact(m,*end,12,12),end)
        self.assertTrue(melee_contact(m,0,0,1,1))
        self.assertFalse(melee_contact(m,-1,0,0,0))
        self.assertFalse(melee_contact(m,m.width-1,0,m.width,0))
        m.tiles['visible'][:] = False
        self.assertTrue(melee_contact(m,12,12,13,12))

    def test_player_routes_reject_geometry_without_time_contact_or_press_side_effects(self):
        e = self.e; item = equip(e,'crude_blade'); a = self.actor(); a.ai = None
        e.player.fighter.hp = 25
        profile = copy.deepcopy(self.data.items['crude_blade'])
        # An arbitrary authored range increase must not unlock ranged melee.
        profile['movesets'][0]['range'] = 99
        cases = ('distance2','distance3','same','edge','door','solid','corner')
        for case in cases:
            for route in ('ordinary','moveset'):
                with self.subTest(case=case,route=route):
                    e.local_map.tiles[:] = make_tile('grass',True,True)
                    e.player.x,e.player.y = 12,12; a.x,a.y = 13,12
                    if case=='distance2': a.x=14
                    if case=='distance3': a.x=15
                    if case=='same': a.x=12
                    if case=='edge': e.player.x=0; a.x=-1
                    if case in ('door','solid'):
                        e.local_map.set_tile(a.x,a.y,'door_closed' if case=='door' else 'wall',False,False)
                    if case=='corner':
                        a.y=13
                        e.local_map.set_tile(13,12,'wall',False,False)
                        e.local_map.set_tile(12,13,'door_closed',False,False)
                    e._free_move_pending=True; e._weapon_time_balance=-400000
                    e._move_debt=.25; e.moveset_cooldowns={}
                    item.temporary_essence=[dict(essence='Dissolution',strength=.8,hits_remaining=3)]
                    before=(timing(e),copy.deepcopy(item.temporary_essence),a.fighter.hp,
                            e.player.fighter.hp,copy.deepcopy(e._pending_blood))
                    with patch('engine.combat.resolve_attack') as resolve, patch.object(
                            e,'_get_equipped_weapon',return_value=profile):
                        result=(e._player_attack(a) if route=='ordinary' else
                                e._try_moveset_action(e.display.MOVESET_KEY_1))
                    self.assertFalse(result); resolve.assert_not_called()
                    self.assertEqual(before,(timing(e),item.temporary_essence,a.fighter.hp,
                                             e.player.fighter.hp,e._pending_blood))
                    self.assertEqual({},e.moveset_cooldowns)

    def test_both_player_routes_accept_cardinal_diagonal_and_one_open_corner(self):
        e=self.e; equip(e,'crude_blade'); a=self.actor(); a.ai=None
        for xy in ((13,12),(13,13)):
            for route in ('ordinary','moveset'):
                a.x,a.y=xy; e.moveset_cooldowns={}
                e.local_map.set_tile(13,12,'grass',True,True)
                if xy==(13,13): e.local_map.set_tile(13,12,'door_closed',False,False)
                with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False,dodged=True)) as resolve:
                    result=(e._player_attack(a) if route=='ordinary' else
                            e._try_moveset_action(e.display.MOVESET_KEY_1))
                self.assertTrue(result); resolve.assert_called_once()

    def test_monster_direct_calls_validate_life_impairment_distance_and_barriers(self):
        e=self.e; a=self.actor(); hp=e.player.fighter.hp
        for case in ('dead','target-dead','zero-hp','no-fighter','impaired','disrupted','distance','same','door','corner'):
            with self.subTest(case=case):
                a.is_alive=True; e.player.is_alive=True; a.fighter.hp=20
                a.x,a.y=13,12; a._disrupted_turns=0
                e.local_map.tiles[:]=make_tile('grass',True,True)
                if case=='dead': a.is_alive=False
                if case=='target-dead': e.player.is_alive=False
                if case=='zero-hp': a.fighter.hp=0
                if case=='disrupted': a._disrupted_turns=2
                if case=='distance': a.x=15
                if case=='same': a.x=12
                if case=='door': e.local_map.set_tile(13,12,'door_closed',False,False)
                if case=='corner':
                    a.y=13; e.local_map.set_tile(13,12,'wall',False,False)
                    e.local_map.set_tile(12,13,'wall',False,False)
                with patch('engine.combat.resolve_attack') as resolve, patch.object(
                        a.fighter,'can_attack',return_value=case!='impaired'), patch.object(
                        e.player,'fighter',None if case=='no-fighter' else e.player.fighter):
                    self.assertFalse(_monster_attack_entity(a,e.player,e))
                resolve.assert_not_called()
        self.assertEqual(hp,e.player.fighter.hp)

    def test_grass_entry_automatic_strike_rejects_corner_without_success_or_contact(self):
        e=self.e; item=equip(e,'crude_blade'); a=self.actor(x=14,y=13); a.ai=None
        e.local_map.set_tile(13,13,'tall_grass',True,True)
        e.local_map.set_tile(13,12,'wall',False,False)
        e.local_map.set_tile(12,13,'door_closed',False,False)
        item.temporary_essence=[dict(essence='Dissolution',strength=.8,hits_remaining=3)]
        def step(**kw): a.x=13
        before=e.world_time.turn
        with patch.object(e.ai_system,'process',side_effect=step), patch('engine.combat.resolve_attack') as resolve:
            e._advance_turn()
        resolve.assert_not_called(); self.assertEqual(before+1,e.world_time.turn)
        self.assertEqual(3,item.temporary_essence[0]['hits_remaining'])
        self.assertFalse(any(m.text=='It steps into your reach through the grass.' for m in e.log.messages))

    def test_grass_entry_legal_strike_preserves_its_free_time_policy(self):
        e=self.e; equip(e,'crude_blade'); a=self.actor(x=14,y=12); a.ai=None
        e.local_map.set_tile(13,12,'tall_grass',True,True)
        def step(**kw): a.x=13
        before=e.world_time.turn
        with patch.object(e.ai_system,'process',side_effect=step), patch('engine.combat.resolve_attack',
                return_value=CombatResult(hit=False)) as resolve: e._advance_turn()
        resolve.assert_called_once(); self.assertEqual(before+1,e.world_time.turn)

    def test_crow_open_envelope_and_projectile_survive_independently_of_visibility(self):
        e=self.e; a=self.actor('plague_crow',15,12)
        e.local_map.tiles['visible'][:]=False
        for xy,projectiles in (((13,12),0),((13,13),0),((14,12),1),((15,12),1),((14,14),1)):
            a.x,a.y=xy
            with patch('engine.combat.resolve_attack',side_effect=combat_routes.CombatRouteTests.contact(damage=1)) as resolve, \
                    patch.object(e,'spawn_projectile') as projectile:
                self.assertTrue(_monster_attack_entity(a,e.player,e))
            resolve.assert_called_once(); self.assertEqual(projectiles,projectile.call_count)
        # Renderer capability is deliberately absent; legality and damage remain.
        class Headless:
            def __getattr__(self,name):
                if name=='spawn_projectile': raise AttributeError(name)
                return getattr(e,name)
        hp=e.player.fighter.hp
        with patch('engine.combat.resolve_attack',side_effect=combat_routes.CombatRouteTests.contact(damage=2)):
            self.assertTrue(_monster_attack_entity(a,e.player,Headless()))
        self.assertEqual(hp-2,e.player.fighter.hp)

    def test_crow_rejects_blocked_corner_closed_door_and_outside_envelope(self):
        e=self.e; a=self.actor('plague_crow',15,12)
        for case in ('opaque','door','corner','too-far','diagonal-far','same','out-of-bounds'):
            with self.subTest(case=case):
                e.local_map.tiles[:]=make_tile('grass',True,True); a.x,a.y=15,12
                if case in ('opaque','door'): e.local_map.set_tile(14,12,'wall' if case=='opaque' else 'door_closed',False,False)
                if case=='corner':
                    a.x,a.y=14,14
                    e.local_map.set_tile(13,12,'wall',False,False)
                    e.local_map.set_tile(12,13,'door_closed',False,False)
                if case=='too-far': a.x=16
                if case=='diagonal-far': a.x,a.y=15,13
                if case=='same': a.x=12
                if case=='out-of-bounds': a.x=-1
                hp=e.player.fighter.hp; logs=len(e.log.messages)
                with patch('engine.combat.resolve_attack') as resolve, patch.object(e,'spawn_projectile') as projectile:
                    self.assertFalse(_monster_attack_entity(a,e.player,e))
                resolve.assert_not_called(); projectile.assert_not_called()
                self.assertEqual(hp,e.player.fighter.hp); self.assertEqual(logs,len(e.log.messages))
        e.local_map.tiles[:]=make_tile('grass',True,True); a.x,a.y=14,14
        e.local_map.set_tile(13,12,'wall',False,False)
        self.assertTrue(terrain_line(e.local_map,12,12,14,14))

    def test_crow_ai_selection_keeps_three_tile_envelope(self):
        e=self.e; a=self.actor('plague_crow',15,12)
        a.ai._update_state(a,e.local_map,e.player,1,engine=e)
        self.assertEqual(AIState.ATTACKING,a.ai.state)
        a.x=16
        a.ai._update_state(a,e.local_map,e.player,1,engine=e)
        self.assertEqual(AIState.HUNTING,a.ai.state)

    def test_crow_open_path_real_combat_damages_player_and_blocked_path_does_not(self):
        from test_equipment_w5m import BranchRng
        e=self.e; a=self.actor('plague_crow',15,12); e.rng=BranchRng(.9)
        e.player.dodge_chance=0; hp=e.player.fighter.hp
        self.assertTrue(_monster_attack_entity(a,e.player,e))
        self.assertLess(e.player.fighter.hp,hp)
        hp=e.player.fighter.hp
        e.local_map.set_tile(14,12,'door_closed',False,False)
        self.assertFalse(_monster_attack_entity(a,e.player,e))
        self.assertEqual(hp,e.player.fighter.hp)

    def test_lurker_wake_at_three_arms_but_does_not_trigger_or_attack(self):
        e=self.e; a=self.actor('stone_lurker',15,12)
        e.local_map.set_tile(14,12,'wall',False,False)
        hp=e.player.fighter.hp
        with patch('engine.combat.resolve_attack') as resolve: self.tick()
        resolve.assert_not_called(); self.assertEqual(hp,e.player.fighter.hp)
        self.assertFalse(a._hibernating); self.assertTrue(a._ambush_ready)
        self.assertFalse(a.ai._triggered); self.assertEqual('stone_lurker',a.tile)
        self.assertEqual(.5,a.ai.move_accumulator)
        self.tick(); self.assertFalse(a.ai._triggered)
        self.assertEqual((15,12),(a.x,a.y))

    def test_pending_bonus_survives_corner_suppression_disruption_and_impairment(self):
        e=self.e; a=self.actor('stone_lurker',13,13); _ability_stone_lurker(a,e)
        for case in ('corner','door','suppressed','disrupted','impaired'):
            with self.subTest(case=case):
                e.local_map.tiles[:]=make_tile('grass',True,True)
                a._ability_suppressed_turns=0; a._disrupted_turns=0
                if case=='corner':
                    e.local_map.set_tile(13,12,'wall',False,False)
                    e.local_map.set_tile(12,13,'wall',False,False)
                if case=='door': e.local_map.set_tile(a.x,a.y,'door_closed',False,False)
                if case=='suppressed': a._ability_suppressed_turns=2
                if case=='disrupted': a._disrupted_turns=2
                with patch.object(a.ai,'take_turn'), patch.object(a.fighter,'can_attack',return_value=case!='impaired'), \
                        patch('engine.combat.resolve_attack') as resolve: self.tick()
                resolve.assert_not_called(); self.assertTrue(a._ambush_ready)
        a._ability_suppressed_turns=a._disrupted_turns=0
        e.local_map.tiles[:]=make_tile('grass',True,True)
        with patch.object(a.ai,'take_turn'), patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)) as resolve:
            self.tick(); self.tick()
        resolve.assert_called_once(); self.assertFalse(a._ambush_ready)

    def test_bonus_consumed_once_for_miss_dodge_zero_damage_and_normal_budget_distinct(self):
        for result in (CombatResult(hit=False),CombatResult(hit=False,dodged=True),CombatResult(hit=True,damage_dealt=0)):
            e=self.e; e.entities=[e.player]; a=self.actor('stone_lurker',13,12)
            a.ai.move_accumulator=.5; _ability_stone_lurker(a,e)
            with patch.object(a.ai,'take_turn') as normal, patch('engine.combat.resolve_attack',return_value=result) as bonus:
                self.tick(); self.assertFalse(a._ambush_ready); self.tick(); self.tick()
            bonus.assert_called_once(); self.assertEqual(2,normal.call_count)
            self.assertAlmostEqual(0,a.ai.move_accumulator)

    def test_stationary_cover_wait_ui_rejection_and_committed_attack(self):
        e=self.e; a=self.actor(x=19); e.local_map.set_tile(12,12,'tall_grass',True,True)
        e.player._in_concealment=False  # cover query must override stale flags
        e._free_move_pending=True; e._weapon_time_balance=-200000
        self.assertFalse(self.seen(a)); before=e.world_time.turn
        with patch.object(a.ai,'_act'):
            for _ in range(3): e._handle_key(pygame.K_z)
        self.assertEqual(before+3,e.world_time.turn); self.assertFalse(e._free_move_pending)
        self.assertEqual(-200000,e._weapon_time_balance); self.assertFalse(self.seen(a))
        self.assertEqual(AIState.WANDERING,a.ai.state)
        before=timing(e); e._handle_key(pygame.K_x); e._handle_key(pygame.K_ESCAPE)
        e._handle_key(pygame.K_i); e._handle_key(pygame.K_i)
        e._handle_key(pygame.K_F5)
        e._handle_key(e.display.MOVESET_KEY_1)  # unarmed rejection
        self.assertEqual(before,timing(e)); self.assertTrue(self.cover())
        b=self.actor(x=13); b.ai=None; equip(e,'crude_blade')
        with patch.object(e.ai_system,'process'), patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)):
            e._handle_key(pygame.K_RIGHT)
        self.assertEqual(before[0]+1,e.world_time.turn); self.assertFalse(self.seen(a))

    def test_enter_wait_leave_and_changed_terrain_query_current_position(self):
        e=self.e; a=self.actor(x=19); a.ai=None
        e.local_map.set_tile(12,13,'tall_grass',True,True)
        e._handle_key(pygame.K_DOWN); self.assertTrue(self.cover()); self.assertFalse(self.seen(a))
        for _ in range(3): e._handle_key(pygame.K_z); self.assertFalse(self.seen(a))
        e._handle_key(pygame.K_UP); self.assertFalse(self.cover()); self.assertTrue(self.seen(a))
        e.player._in_concealment=True
        self.assertTrue(self.seen(a))
        before=timing(e); hp=e.player.fighter.hp
        e.local_map.set_tile(12,12,'tall_grass',True,True); self.assertFalse(self.seen(a))
        e.local_map.set_tile(12,12,'grass',True,True); self.assertTrue(self.seen(a))
        self.assertEqual(before,timing(e)); self.assertEqual(hp,e.player.fighter.hp)

    def test_free_press_step_reconciles_cover_without_a_phase(self):
        e=self.e; e.data=copy.copy(self.data); e.data.terrain=copy.deepcopy(self.data.terrain)
        # Explicit unit-cost cover fixture isolates the skipped world phase;
        # authored grass's 1.5 surcharge remains covered by G18 composition tests.
        e.data.terrain['tall_grass']['move_cost']=1
        for y in (12,13): e.local_map.set_tile(12,y,'tall_grass',True,True)
        for key,expected in ((pygame.K_DOWN,True),(pygame.K_DOWN,False),(pygame.K_UP,True)):
            e._free_move_pending=True; before=timing(e)
            e._handle_key(key)
            self.assertEqual(before[0],e.world_time.turn); self.assertEqual(expected,self.cover())
            self.assertFalse(e._free_move_pending)

    def test_close_observer_darkness_and_existing_pursuit_memory(self):
        e=self.e; a=self.actor(x=19); e.local_map.set_tile(12,12,'tall_grass',True,True)
        self.assertFalse(self.seen(a)); a.x=13; self.assertTrue(self.seen(a))
        radius=a.perception.sight_radius; a.perception.sight_radius=1
        self.assertTrue(self.seen(a))  # minimum effective cover sight remains one
        a.perception.sight_radius=radius
        a.x=19; e.local_map.set_tile(12,12,'grass',True,True)
        a.ai._update_state(a,e.local_map,e.player,1,engine=e)
        self.assertEqual(AIState.HUNTING,a.ai.state)
        e.local_map.set_tile(12,12,'tall_grass',True,True)
        a.ai._update_state(a,e.local_map,e.player,1,engine=e)
        self.assertEqual(AIState.ALERTED,a.ai.state); self.assertEqual(12,a._last_known_px)
        self.assertEqual(2,a.ai.pursuit_turns_without_contact)
        for _ in range(30): a.ai._update_state(a,e.local_map,e.player,1,engine=e)
        self.assertIsNone(a._last_known_px); self.assertEqual(AIState.WANDERING,a.ai.state)
        crow=self.actor('plague_crow',19,12)
        self.assertTrue(self.seen(crow)); self.assertFalse(self.seen(crow,light=0))
        a.x=13; self.assertTrue(self.seen(a,light=0))  # Revenant darkvision

    def test_perception_uses_supplied_map_and_phantom_is_not_physical_player(self):
        e=self.e; a=self.actor(x=19)
        other=LocalMap(); other.tiles[:]=make_tile('tall_grass',True,True)
        self.assertFalse(self.seen(a,local_map=other)); self.assertTrue(self.seen(a))
        a._last_known_px=12; a._last_known_py=12; a.ai.state=AIState.HUNTING
        a.ai._update_state(a,other,e.player,1,engine=e)
        self.assertEqual(2,a.ai.pursuit_turns_without_contact)
        phantom=SimpleNamespace(x=12,y=12,is_alive=True,fighter=None,_in_concealment=True)
        self.assertFalse(_player_concealed(phantom,other,e))
        with patch('engine.combat.resolve_attack') as resolve:
            e.ai_system.process_single(a,other,12,12,[a],e.log,1,engine=e)
        resolve.assert_not_called()

    def test_cover_and_pending_consumed_uninitialized_lurker_cold_and_f9(self):
        e=self.e; a=self.actor('stone_lurker',15,12)
        for state in ('uninitialized','hibernating','pending','consumed'):
            if state=='hibernating':
                a.x=20; _ability_stone_lurker(a,e)
            if state=='pending':
                a.x=15; _ability_stone_lurker(a,e)
                e.local_map.set_tile(14,12,'wall',False,False)
            if state=='consumed':
                a.x=13; e.local_map.set_tile(13,12,'grass',True,True)
                with patch.object(a.ai,'take_turn'), patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)):
                    self.tick()
                self.assertFalse(a._ambush_ready)
            e.local_map.set_tile(12,12,'tall_grass' if state!='consumed' else 'grass',True,True)
            e._weapon_time_balance=-200000; e._free_move_pending=True
            e.player._in_concealment=state=='consumed'  # stale in either direction
            e._handle_key(pygame.K_F5); expected=physical(e)
            proc=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--cold',str(self.root)],
                                capture_output=True,text=True,timeout=45,env=dict(os.environ))
            self.assertEqual(0,proc.returncode,proc.stdout+proc.stderr)
            self.assertEqual(expected,json.loads(proc.stdout.strip().splitlines()[-1]))
            e.player.x,e.player.y=25,25; e._weapon_time_balance=600000; e._free_move_pending=False
            e._handle_key(pygame.K_F9); self.assertEqual(expected,physical(e))
            a=next(x for x in e.entities if x is not e.player)
            if state=='pending':
                with patch('engine.combat.resolve_attack') as resolve, patch.object(a.ai,'take_turn'): self.tick()
                resolve.assert_not_called(); self.assertTrue(a._ambush_ready)

    def test_chunk_arrival_return_and_stairs_query_destination_without_entry_replay(self):
        e=self.e; e.world_map.width=2
        e.world_map.set(Chunk(1,0,RegionType.PLAINS,29418,visited=True))
        destination=LocalMap(); destination.tiles[:]=make_tile('grass',True,True)
        destination.set_tile(0,12,'tall_grass',True,True)
        e.save_manager.cache.store(1,0,destination,[])
        e.player.x=79; before=e.world_time.turn; hp=e.player.fighter.hp
        e._handle_key(pygame.K_RIGHT)
        self.assertTrue(self.cover()); self.assertEqual(before+1,e.world_time.turn)
        e._handle_key(pygame.K_LEFT); self.assertFalse(self.cover())
        self.assertEqual(before+2,e.world_time.turn); self.assertEqual(hp,e.player.fighter.hp)
        sub=SubMap('g19-stair','cave','G19 cover fixture',19,generated=True,entry_x=12,entry_y=12)
        e.world_map.get(0,0).submaps.append(sub)
        xy=(e.player.x,e.player.y); e.local_map.submap_links[xy]=sub.submap_id
        e.local_map.set_tile(*xy,'stairs_down',True,True)
        underground=LocalMap(); underground.tiles[:]=make_tile('grass',True,True)
        underground.set_tile(12,12,'tall_grass',True,True)
        e.save_manager.cache.store_submap(sub.submap_id,underground,[])
        before=timing(e); e._handle_key(pygame.K_PERIOD,'>')
        self.assertEqual(sub.submap_id,e.current_submap_id); self.assertTrue(self.cover())
        self.assertEqual(before,timing(e)); self.assertEqual(hp,e.player.fighter.hp)
        e._ascend_from_submap(); self.assertFalse(self.cover()); self.assertEqual(before,timing(e))

    def test_scene_cache_return_retains_pending_consumed_and_uninitialized_lurkers(self):
        e=self.e
        sub=SubMap('g19-owners','cave','G19 actor fixture',19,generated=True,entry_x=12,entry_y=12)
        e.world_map.get(0,0).submaps.append(sub)
        underground=LocalMap(); underground.tiles[:]=make_tile('grass',True,True)
        e.save_manager.cache.store_submap(sub.submap_id,underground,[])
        a=self.actor('stone_lurker',15,12); _ability_stone_lurker(a,e)
        consumed=self.actor('stone_lurker',16,12); _ability_stone_lurker(consumed,e)
        consumed._hibernating=False; consumed.tile='stone_lurker'; consumed._ambush_ready=False
        consumed.ai._triggered=True
        self.actor('stone_lurker',20,12)
        expected=physical(e)
        e._descend_to_submap(sub.submap_id)
        self.assertEqual([e.player],e.entities)
        e._ascend_from_submap()
        self.assertEqual(expected,physical(e))


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--cold':
        root=Path(sys.argv[2]).resolve()
        assert not root.is_relative_to(GAME_ROOT)
        print(json.dumps(cold(root)))
    else: unittest.main()
