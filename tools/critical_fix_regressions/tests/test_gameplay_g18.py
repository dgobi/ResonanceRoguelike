"""Weapon timing and Press through production input and disposable checkpoints.

Arithmetic cases explicitly remove cooldown waits in a copied action definition;
real-definition persistence and ordinary-loop evidence retain authored cooldowns.
"""
import copy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pygame
from test_effect_persistence import GAME_ROOT, load_data, make_engine
from test_gameplay_g12 import use
import test_combat_routes as combat_routes
from engine.combat import CombatResult
from engine.hooks import HookEvent
from engine.save_components import validate_components
from engine.save_manager import _serialize_player, _serialize_entity


def timing(e):
    return [e.world_time.turn, e._weapon_time_balance, e._move_debt,
            e._free_move_pending, e.player_move_accumulator]


def equip(e, iid):
    item = e.item_factory.create(iid)
    assert e.player.inventory.add(item)
    e.player.equipment.equip(item, 'weapon')
    return item


def target(e, hp=1000):
    actor = e.creature_factory.spawn('hollow_revenant', e.player.x+1, e.player.y)
    actor.ai = None  # disclosed isolated timing fixture, no AI combat/balance claim
    actor.fighter.max_hp = actor.fighter.hp = hp
    e.entities.append(actor)
    return actor


def cold(root, steps=0):
    with patch('engine.save_manager.SAVE_DIR', Path(root)):
        e = make_engine(load_data()); e.debug = None; e.rng = random.Random(29417)
        assert e.save_manager.load(e), e.save_manager.last_error
        initial = timing(e)
        # Capture physical state before any follow-up; load must not replay kills.
        physical = dict(actors=[_serialize_entity(a) for a in e.entities if a is not e.player],
                        floor=sorted((list(xy), [i.item_id for i in rows])
                                     for xy, rows in e.local_map.floor_objects.items()))
        phases = []
        for _ in range(steps):
            before = e.world_time.turn
            e._handle_key(pygame.K_DOWN)
            phases.append(e.world_time.turn-before)
        # Continue a real 0.8 sequence with actual cooldown waits, if requested.
        if steps == -1:
            phases = []
            # Factory reload reattaches AI; isolate continued cost arithmetic
            # from combat survival, retaining actual phase systems/cooldowns.
            with patch.object(e.ai_system, 'process'):
                for _ in range(4):
                    for _ in range(9):
                        if not e.moveset_cooldowns.get('desperate_slash', 0): break
                        e._handle_key(pygame.K_z)
                    assert not e.moveset_cooldowns.get('desperate_slash', 0)
                    before = e.world_time.turn
                    e._handle_key(e.display.MOVESET_KEY_2)
                    phases.append(e.world_time.turn-before)
        return dict(initial=initial, final=timing(e), phases=phases, physical=physical)


class WeaponTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(); pygame.init()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='resonance-g18-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'saves'
        p = patch('engine.save_manager.SAVE_DIR', self.root)
        p.start(); self.addCleanup(p.stop)
        self.e = make_engine(self.data); self.e.debug = None
        self.e.rng = random.Random(29417)

    def process(self, steps=0):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()),
                                 '--cold', str(self.root), str(steps)],
                                capture_output=True, text=True, timeout=45, env=dict(os.environ))
        self.assertEqual(0, result.returncode, result.stdout+result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def controlled(self, costs, *, intervening=False):
        e = self.e; equip(e, 'crude_blade'); t = target(e)
        profile = copy.deepcopy(self.data.items['crude_blade'])
        action = profile['movesets'][0]; action['cooldown'] = 0
        commits = []; phases = []; start = e.world_time.turn
        with patch.object(e, '_get_equipped_weapon', return_value=profile), patch(
                'engine.combat.resolve_attack', side_effect=lambda **kw:
                commits.append(kw) or CombatResult(hit=False)):
            for cost in costs:
                action['turn_cost'] = cost
                before = e.world_time.turn
                e._handle_key(e.display.MOVESET_KEY_1)
                phases.append(e.world_time.turn-before)
                if intervening:
                    balance = e._weapon_time_balance
                    e._handle_key(pygame.K_z)
                    e._handle_key(pygame.K_DOWN)
                    e._handle_key(pygame.K_UP)
                    self.assertEqual(balance, e._weapon_time_balance)
        self.assertEqual(len(costs), len(commits))
        self.assertEqual(1000, t.fighter.hp)
        self.assertEqual(sum(phases)+(3*len(costs) if intervening else 0), e.world_time.turn-start)
        return phases

    def test_cost_table_and_exact_fifth_boundaries_without_duplicate_attacks(self):
        for costs, expected in (([1.0],[1]), ([.8],[1]), ([.8]*5,[1,1,1,1,0]),
                                ([1.2]*5,[1,1,1,1,2]), ([.8,1.2],[1,1]),
                                ([.8,1,.8,1,.8,.8,.8],[1,1,1,1,1,1,0])):
            with self.subTest(costs=costs):
                self.e = make_engine(self.data); self.e.debug = None
                self.assertEqual(expected, self.controlled(costs))
                self.assertLess(abs(self.e._weapon_time_balance), 1_000_000)

    def test_intervening_waits_and_steps_preserve_weapon_balance(self):
        self.assertEqual([1,1,1,1,0], self.controlled([.8]*5, intervening=True))
        self.assertEqual(0, self.e._weapon_time_balance)

    def test_fast_skip_and_slow_extra_run_complete_pipeline_without_repeating_contact(self):
        for balance, weapon, key, expected in ((-800000,'crude_blade',2,0),(800000,'heavy_blade',2,2)):
            with self.subTest(expected=expected):
                e = make_engine(self.data); e.debug = None; item = equip(e, weapon)
                t = target(e, hp=1); e.player.fighter.hp = 25
                e._weapon_time_balance = balance; e.player.chilled_turns = 10
                item.temporary_essence = [dict(essence='Dissolution',strength=.8,hits_remaining=3)]
                events = []
                for event in (HookEvent.ON_TURN, HookEvent.ON_DAMAGE_DEALT, HookEvent.ON_ENTITY_KILLED):
                    e.hooks.register(event, lambda payload, event=event: events.append(event))
                before = e.world_time.turn; hunger = e.player.needs.hunger
                e.local_map.processing_layer[(20,20)] = dict(item_id='wood_bundle',turns_remaining=5)
                with patch('engine.combat.resolve_attack', side_effect=combat_routes.CombatRouteTests.contact(damage=2)) as resolve:
                    e._handle_key(e.display.MOVESET_KEY_1 if key==1 else e.display.MOVESET_KEY_2)
                self.assertEqual(expected, e.world_time.turn-before)
                self.assertEqual(expected, events.count(HookEvent.ON_TURN))
                self.assertEqual(1, events.count(HookEvent.ON_DAMAGE_DEALT))
                self.assertEqual(1, events.count(HookEvent.ON_ENTITY_KILLED)); resolve.assert_called_once()
                self.assertEqual(10-expected, e.player.chilled_turns)
                self.assertEqual(5-expected, e.local_map.processing_layer[(20,20)]['turns_remaining'])
                if expected == 0: self.assertEqual(hunger,e.player.needs.hunger)
                else: self.assertGreater(e.player.needs.hunger,hunger)
                self.assertEqual(2, item.temporary_essence[0]['hits_remaining'])
                self.assertFalse(t.is_alive)

    def test_dodged_or_missed_commit_still_spends_cost_once(self):
        for dodged in (False,True):
            e = self.e; equip(e,'crude_blade'); t = target(e); e.player.fighter.hp = 25
            e._weapon_time_balance = -800000; before = e.world_time.turn
            with patch('engine.combat.resolve_attack', return_value=CombatResult(hit=False,dodged=dodged)) as resolve:
                e._handle_key(e.display.MOVESET_KEY_2)
            resolve.assert_called_once(); self.assertEqual(before,e.world_time.turn)
            self.assertEqual(0,e._weapon_time_balance); self.assertEqual(8,e.moveset_cooldowns['desperate_slash'])
            self.assertEqual(1000,t.fighter.hp)
            e.entities = [e.player]; e.moveset_cooldowns.clear()  # separate controlled case

    def test_rejected_movesets_preserve_time_press_cooldown_coating_and_target(self):
        for case in ('no-target','cooldown','hp','position','dead','zero-hp','cannot-attack'):
            with self.subTest(case=case):
                e = make_engine(self.data); e.debug = None; item = equip(e,'crude_blade'); t = target(e)
                item.temporary_essence = [dict(essence='Dissolution',strength=.8,hits_remaining=3)]
                e.player.fighter.hp = 25; e._weapon_time_balance = -400000; e._free_move_pending = True
                if case=='no-target': t.x = 40
                if case=='cooldown': e.moveset_cooldowns['desperate_slash'] = 3
                if case=='hp': e.player.fighter.hp = 60
                if case=='dead': e.player.is_alive = False
                if case=='zero-hp': e.player.fighter.hp = 0
                if case=='cannot-attack': e.player.fighter._dead = True
                profile = copy.deepcopy(self.data.items['crude_blade'])
                if case=='position':
                    profile['movesets'][1]['positioning'] = 'behind'
                    from types import SimpleNamespace
                    t.ai = SimpleNamespace(target_x=e.player.x,target_y=e.player.y)
                before = (timing(e),copy.deepcopy(e.moveset_cooldowns),copy.deepcopy(item.temporary_essence),t.fighter.hp)
                with patch.object(e,'_get_equipped_weapon',return_value=profile), patch(
                        'engine.combat.resolve_attack',side_effect=AssertionError('rejected attack')):
                    e._handle_key(e.display.MOVESET_KEY_2)
                self.assertEqual(before,(timing(e),e.moveset_cooldowns,item.temporary_essence,t.fighter.hp))

    def press(self):
        e = self.e; equip(e,'heavy_blade'); t = target(e,hp=1)
        before = e.world_time.turn
        e._handle_key(e.display.MOVESET_KEY_1)  # actual resolver and definitions
        self.assertFalse(t.is_alive); self.assertEqual(before+1,e.world_time.turn)
        self.assertTrue(e._free_move_pending)
        return e

    def test_real_press_one_step_then_paid_step_and_nonstacking_regrant(self):
        e = self.press(); before = e.world_time.turn
        e._handle_key(pygame.K_DOWN)
        self.assertEqual(before,e.world_time.turn); self.assertFalse(e._free_move_pending)
        e._handle_key(pygame.K_DOWN); self.assertEqual(before+1,e.world_time.turn)
        while e.moveset_cooldowns.get('press',0): e._handle_key(pygame.K_z)
        e._free_move_pending = True; target(e,hp=1)
        before = e.world_time.turn; e._handle_key(e.display.MOVESET_KEY_1)
        self.assertEqual(before+1,e.world_time.turn); self.assertTrue(e._free_move_pending)
        e._handle_key(pygame.K_DOWN); e._handle_key(pygame.K_DOWN)
        self.assertEqual(before+2,e.world_time.turn)

    def test_press_preserved_by_ui_save_rejected_moves_and_rejected_travel(self):
        e = self.press(); before = e.world_time.turn
        e.local_map.set_tile(e.player.x,e.player.y+1,'stone_wall',False,False)
        e._handle_key(pygame.K_DOWN)
        e._handle_key(pygame.K_i); e._handle_key(pygame.K_ESCAPE)
        e._handle_key(pygame.K_x); e._handle_key(pygame.K_ESCAPE)
        e._handle_key(pygame.K_F5); e._handle_key(pygame.K_PERIOD, '>')
        self.assertEqual(before,e.world_time.turn); self.assertTrue(e._free_move_pending)
        e.player.x = 0
        e._handle_key(pygame.K_LEFT)  # world boundary rejects
        self.assertEqual(before,e.world_time.turn); self.assertTrue(e._free_move_pending)

    def test_press_expires_for_wait_door_inventory_equipment_read_and_free_sprint(self):
        e = self.press()
        for case in ('wait','door','use','equip','read','sprint'):
            with self.subTest(case=case):
                e._free_move_pending = True; before = e.world_time.turn
                if case=='wait': e._handle_key(pygame.K_z)
                if case=='door':
                    e.local_map.set_tile(e.player.x,e.player.y+1,'door_closed',False,False)
                    e._handle_key(pygame.K_DOWN)
                    self.assertEqual('door_open',e.local_map.tiles['terrain'][e.player.x,e.player.y+1])
                if case in ('use','equip','read'):
                    iid = dict(use='herbal_dressing',equip='crude_blade',read='lab_note')[case]
                    item = e.item_factory.create(iid); e.player.inventory.add(item); e.player.fighter.hp = 25
                    if case=='read': item.text_id = 'lab_label_sarcophagus'
                    use(e,item); e.text_reader.open = False
                if case=='sprint':
                    with patch('pygame.key.get_mods',return_value=pygame.KMOD_SHIFT): e._handle_key(e.display.SPRINT_KEY)
                self.assertFalse(e._free_move_pending)
                self.assertEqual(before+(0 if case=='sprint' else 1),e.world_time.turn)

    def test_inventory_inspection_and_failed_use_preserve_press(self):
        e = self.press()
        for iid in ('wood_bundle','herbal_dressing'):
            item = e.item_factory.create(iid); e.player.inventory.add(item)
            e.player.fighter.hp = e.player.fighter.max_hp
            before = timing(e); use(e,item)
            self.assertEqual(before,timing(e)); self.assertTrue(e.player.inventory.contains(item))

    def test_real_harvest_completion_expires_press_and_settles_work_debt(self):
        e = self.press()  # real Revenant definition includes an authored harvest profile
        corpse = next(i for i in e.local_map.floor_objects[13,12] if i.source_creature)
        before = e.world_time.turn; e._move_debt = 1.25
        # Cursor entry stages selection; Enter uses the ordinary interact route.
        from engine.engine import GameMode
        e.mode = GameMode.INTERACTION_CURSOR
        e.interaction_cursor.enter([(13,12)],12,12)
        e._handle_key(pygame.K_RETURN)
        if e.interaction_cursor._selection_prompt: e._handle_key(pygame.K_RETURN)
        self.assertNotIn(corpse,e.local_map.floor_objects.get((13,12),[]))
        self.assertFalse(e._free_move_pending); self.assertGreater(e.world_time.turn,before+1)
        self.assertAlmostEqual(.25,e._move_debt)

    def test_new_press_is_granted_after_all_own_debt_phases(self):
        e = self.e; equip(e,'heavy_blade'); target(e,hp=1)
        e._move_debt = 2.25; e._free_move_pending = True
        seen = []; e.hooks.register(HookEvent.ON_TURN,lambda payload:seen.append(e._free_move_pending))
        before = e.world_time.turn; e._handle_key(e.display.MOVESET_KEY_1)
        self.assertEqual([False,False,False],seen)
        self.assertEqual(before+3,e.world_time.turn); self.assertTrue(e._free_move_pending)
        self.assertEqual(.25,e._move_debt)

    def test_committed_and_rejected_bump_attacks_resolve_press_differently(self):
        e = self.press(); t = target(e); before = timing(e)
        with patch.object(e.player.fighter,'can_attack',return_value=False): e._handle_key(pygame.K_RIGHT)
        self.assertEqual(before,timing(e))
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)) as resolve:
            e._handle_key(pygame.K_RIGHT)
        resolve.assert_called_once(); self.assertEqual(before[0]+1,e.world_time.turn)
        self.assertFalse(e._free_move_pending); self.assertEqual(1000,t.fighter.hp)

    def test_press_slow_hazard_step_keeps_debt_entry_effects_and_speed_credit(self):
        e = self.press(); e._move_debt = 1.25
        # Real authored thorns terrain, with its real surcharge.
        terrain = next((iid,row) for iid,row in self.data.terrain.items()
                       if row.get('walkable') and row.get('secondary_effect')=='thorns')
        iid,row = terrain; x,y = e.player.x,e.player.y+1
        e.local_map.set_tile(x,y,iid,True,True)
        e.player_move_accumulator = .75; e.sprint_turns_remaining = 3
        e.player_speed_bonus = .5; e.player_speed_bonus_turns = 10
        before = e.world_time.turn; hp = e.player.fighter.hp
        surcharge = max(0,row.get('move_cost',1)-1); expected = int(1.25+surcharge)
        e._handle_key(pygame.K_DOWN)
        self.assertEqual((x,y),(e.player.x,e.player.y)); self.assertLess(e.player.fighter.hp,hp)
        self.assertEqual(before+expected,e.world_time.turn); self.assertEqual(.75,e.player_move_accumulator)
        self.assertAlmostEqual(1.25+surcharge-expected,e._move_debt)
        self.assertEqual(2,e.sprint_turns_remaining); self.assertEqual(10-expected,e.player_speed_bonus_turns)
        self.assertFalse(e._free_move_pending)

    def test_press_plain_step_preserves_speed_credit_and_world_phase_durations(self):
        e = self.press(); e.player_move_accumulator = .75
        e.sprint_turns_remaining = 2; e.player_speed_bonus = .5; e.player_speed_bonus_turns = 10
        before = e.world_time.turn; cd = e.sprint_cooldown_remaining
        e._handle_key(pygame.K_DOWN)
        self.assertEqual(before,e.world_time.turn); self.assertEqual(.75,e.player_move_accumulator)
        self.assertEqual((1,10,cd),(e.sprint_turns_remaining,e.player_speed_bonus_turns,e.sprint_cooldown_remaining))
        e._handle_key(pygame.K_DOWN)
        self.assertEqual(0,e.sprint_turns_remaining); self.assertLess(e.player_move_accumulator,.75)

    def test_successful_chunk_and_stair_travel_expires_press_without_free_travel(self):
        from world.world_map import Chunk,RegionType,SubMap
        from world.local_map import LocalMap,make_tile
        e = self.press(); e.world_map.width = 2
        e.world_map.set(Chunk(1,0,RegionType.PLAINS,29418,visited=True))
        m = LocalMap(); m.tiles[:] = make_tile('grass',True,True)
        e.save_manager.cache.store(1,0,m,[])
        e.player.x = 79; before = e.world_time.turn
        e._handle_key(pygame.K_RIGHT)
        self.assertEqual(1,e.world_x); self.assertEqual(before+1,e.world_time.turn)
        self.assertFalse(e._free_move_pending)
        sub = SubMap('g18-stair','cave','G18 fixture',18,generated=True,entry_x=12,entry_y=12)
        e.world_map.get(1,0).submaps.append(sub)
        down = (e.player.x,e.player.y)
        e.local_map.set_tile(*down,'stairs_down',True,True); e.local_map.submap_links[down] = sub.submap_id
        underground = LocalMap(); underground.tiles[:] = make_tile('flagstone',True,True)
        underground.set_tile(12,12,'stairs_up',True,True)
        e.save_manager.cache.store_submap(sub.submap_id,underground,[])
        e._free_move_pending = True; before = e.world_time.turn
        e._handle_key(pygame.K_PERIOD,'>')
        self.assertEqual(sub.submap_id,e.current_submap_id); self.assertFalse(e._free_move_pending)
        self.assertEqual(before,e.world_time.turn)  # established stairs cost remains zero
        e._free_move_pending = True; e._handle_key(pygame.K_COMMA,'<')
        self.assertIsNone(e.current_submap_id); self.assertFalse(e._free_move_pending)

    def test_real_desperate_slash_save_cold_load_and_continued_fifth_skip(self):
        e = self.e; equip(e,'crude_blade'); target(e); e.player.fighter.hp = 25
        before = e.world_time.turn; e._handle_key(e.display.MOVESET_KEY_2)
        self.assertEqual(before+1,e.world_time.turn); self.assertEqual(-200000,e._weapon_time_balance)
        self.assertEqual(0,e._move_debt); self.assertEqual(7,e.moveset_cooldowns['desperate_slash'])
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        observed = self.process(-1)
        self.assertEqual(timing(e),observed['initial']); self.assertEqual([1,1,1,0],observed['phases'])
        self.assertEqual(0,observed['final'][1])

    def test_before_pending_consumed_expired_checkpoints_same_session_and_cold(self):
        e = self.e
        for state in ('before','pending','consumed','expired'):
            if state=='pending': self.press()
            if state=='consumed': e._handle_key(pygame.K_DOWN)
            if state=='expired': e._free_move_pending = True; e._handle_key(pygame.K_z)
            expected = timing(e); e._handle_key(pygame.K_F5)
            observed = self.process(2)
            self.assertEqual(expected,observed['initial'])
            self.assertEqual([0,1] if state=='pending' else [1,1],observed['phases'])
            e._weapon_time_balance = 600000; e._free_move_pending = not expected[3]
            e._handle_key(pygame.K_F9); self.assertEqual(expected,timing(e))
            physical = dict(actors=[_serialize_entity(a) for a in e.entities if a is not e.player],
                            floor=sorted((list(xy),[i.item_id for i in rows]) for xy,rows in e.local_map.floor_objects.items()))
            self.assertEqual(json.loads(json.dumps(physical)),observed['physical'])

    def test_optional_domains_and_malformed_real_publication_fail_transactionally(self):
        e = self.e; self.assertTrue(e.save_manager.save(e)); before = timing(e)
        player,world,local = e.player,e.world_map,e.local_map
        original = _serialize_player(e)
        for field,values in (('_weapon_time_balance',[True,False,1.5,'1',None,float('nan'),float('inf'),-1000000,1000000]),
                             ('_free_move_pending',[0,1,'yes',None])):
            for value in values:
                with self.subTest(field=field,value=value):
                    record = copy.deepcopy(original); record['component_state']['engine'][field] = value
                    with self.assertRaises(ValueError): validate_components(record)
                    # Valid hash/publication; failure must come from semantic load validation.
                    payloads = {p.relative_to(e.save_manager.checkpoint_path()).as_posix():p.read_bytes()
                                for p in e.save_manager.checkpoint_path().rglob('*') if p.is_file()
                                and p.name!='manifest.json'}
                    payloads['player.json'] = json.dumps(record).encode('utf-8')
                    generation,_,_ = e.save_manager.store.publish(payloads,None,e.save_manager.store.token())
                    e.save_manager.generation = generation
                    self.assertFalse(e.save_manager.load(e))
                    self.assertIs(player,e.player); self.assertIs(world,e.world_map); self.assertIs(local,e.local_map)
                    self.assertEqual(before,timing(e))

    def test_writer_rejects_malformed_timing_including_false_like_values(self):
        e = self.e
        for field,values in (('_weapon_time_balance',[False,True,0.0,float('nan'),1000000]),
                             ('_free_move_pending',[0,1,None])):
            for value in values:
                with self.subTest(field=field,value=value):
                    setattr(e,field,value)
                    self.assertFalse(e.save_manager.save(e))
                    setattr(e,field,False if field=='_free_move_pending' else 0)

    def test_missing_fields_reset_and_existing_positive_work_debt_survives(self):
        e = self.e; e._move_debt = 2.25
        self.assertTrue(e.save_manager.save(e)); saved = _serialize_player(e)
        self.assertNotIn('_weapon_time_balance',saved['component_state']['engine'])
        self.assertNotIn('_free_move_pending',saved['component_state']['engine'])
        e._weapon_time_balance = -800000; e._free_move_pending = True
        e._handle_key(pygame.K_F9)
        self.assertEqual((0,False,2.25),(e._weapon_time_balance,e._free_move_pending,e._move_debt))
        item = e.item_factory.create('crude_blade'); e.player.inventory.add(item)
        e._free_move_pending = True; before = e.world_time.turn; use(e,item)
        self.assertEqual(before+1,e.world_time.turn); self.assertEqual(2.25,e._move_debt)
        self.assertFalse(e._free_move_pending)

    def test_settlement_stops_on_death_and_cannot_grant_press_after_death(self):
        e = self.e; equip(e,'heavy_blade'); target(e,hp=1); e._move_debt = 4
        def fatal_phase():
            e.world_time.advance(); e.player.fighter.take_damage(1000); e._on_player_death()
        with patch.object(e,'_advance_turn',side_effect=fatal_phase) as advance:
            e._handle_key(e.display.MOVESET_KEY_1)
        self.assertEqual(1,advance.call_count); self.assertFalse(e._free_move_pending)
        self.assertTrue(e._player_is_dead); self.assertEqual(4,e._move_debt)


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--cold':
        pygame.init(); print(json.dumps(cold(sys.argv[2],int(sys.argv[3]))))
    else:
        unittest.main()
