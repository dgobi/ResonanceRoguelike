"""G20 controlled rule checks. Real runtime, temporary saves, staged geometry.

Ordinary acquisition/expedition evidence is recorded separately by verify_g20.
"""
import copy
import json
import os
import pickle
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pygame
from test_effect_persistence import load_data, make_engine
from test_gameplay_g12 import use
from test_gameplay_g18 import equip, target, timing
from components.ai import AIState, _monster_attack_entity
from engine.combat import CombatResult
from engine.sound import emit, propagation, current_interest, INTEREST_TURNS
from engine.save_components import serialize_item, validate_actor_runtime, restore_actor_runtime
from engine.save_manager import _serialize_entity, _deserialize_entities
from engine.effect_lifecycle import throw_key
from world.local_map import LocalMap, make_tile
from world.world_map import Chunk, RegionType, SubMap


def snapshot(e):
    return dict(turn=e.world_time.turn, timing=timing(e),
                actors=[_serialize_entity(a) for a in e.entities if a is not e.player],
                items=[serialize_item(i) for i in e.player.inventory.items])


def cold(root):
    with patch('engine.save_manager.SAVE_DIR', Path(root)):
        e = make_engine(load_data()); e.debug = None
        assert e.save_manager.load(e), e.save_manager.last_error
        return snapshot(e)


class AudibleEncounterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(); pygame.init()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='resonance-g20-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'saves'
        p = patch('engine.save_manager.SAVE_DIR', self.root)
        p.start(); self.addCleanup(p.stop)
        self.e = make_engine(self.data); self.e.debug = None
        self.e.rng = random.Random(29417)
        self.e.reality_bubble.update(0, 0, self.e.world_map)
        self.e.player.x, self.e.player.y = 40, 40

    def actor(self, iid='hollow_revenant', x=12, y=12):
        a = self.e.creature_factory.spawn(iid, x, y)
        a.ai.wander_radius = 0; a.ai.set_home(x, y)
        self.e.entities.append(a)
        return a

    def decision(self, a):
        e = self.e
        a.ai.take_turn(a, e.local_map, e.entities, e.player, e.log, random.Random(1), 1, engine=e)

    def test_propagation_open_corner_sealed_wall_door_and_monotonic_hearing(self):
        e=self.e; m=e.local_map; m.tiles[:]=make_tile('wall',False,False)
        for xy in ((10,10),(11,10),(12,10),(12,11),(12,12)):
            m.set_tile(*xy,'flagstone',True,True)
        a=self.actor(x=12,y=12)
        self.assertEqual(4,propagation(m,10,10,20)[12,12])
        a.perception.hearing_radius=3
        self.assertEqual(0,emit(e,10,10,'flint'))
        a.perception.hearing_radius=4
        self.assertEqual(1,emit(e,10,10,'flint'))
        for hearing in (5,6,8,20,1000):
            a.perception.hearing_radius=hearing; self.assertEqual(1,emit(e,10,10,'flint'))
        a.ai.sound_interest=None; a.perception.hearing_radius=0
        self.assertEqual(0,emit(e,10,10,'bell_intact'))
        a.perception.hearing_radius=6
        m.set_tile(12,10,'door_closed',False,False)
        self.assertEqual(7,propagation(m,10,10,20)[12,12])
        self.assertEqual(0,emit(e,10,10,'flint'))
        self.assertEqual(1,emit(e,10,10,'combat'))
        m.set_tile(12,10,'wall',False,False)
        self.assertNotIn((12,12),propagation(m,10,10,48))
        m.set_tile(11,11,'flagstone',True,True)
        m.set_tile(11,10,'wall',False,False)
        self.assertNotIn((11,11),propagation(m,10,10,48))

    def test_one_bounded_flood_for_all_listeners_and_actual_bell_source(self):
        e=self.e; a=self.actor(x=14,y=12); self.actor(x=16,y=12)
        e.local_map.set_tile(12,12,'bell_intact',False,False)
        with patch('engine.sound.propagation',wraps=propagation) as flood:
            from engine.discharge import trigger_discharge
            trigger_discharge(e,12,12,'intact',{})
        flood.assert_called_once()
        self.assertEqual([12,12],[a.ai.sound_interest['x'],a.ai.sound_interest['y']])
        self.assertGreater(e.resonance_exposure,0)
        self.assertIsNone(getattr(a,'_last_known_px',None))
        # The nonwalkable bell has a reachable approach; no walkable bell target.
        self.decision(a)
        self.assertEqual((13,12),(a.x,a.y)); self.assertIsNone(a.ai.sound_interest)
        e.local_map.set_tile(11,11,'wall',False,False)
        self.assertEqual({},propagation(e.local_map,11,11,48,bell=True))

    def test_heard_source_not_hidden_player_and_receipt_has_no_action(self):
        e=self.e; a=self.actor(); before=(a.x,a.y,a.ai.move_accumulator,e.world_time.turn)
        emit(e,16,12,'flint')
        self.assertEqual(before,(a.x,a.y,a.ai.move_accumulator,e.world_time.turn))
        e.player.x,e.player.y=50,30
        self.decision(a)
        self.assertEqual(AIState.INVESTIGATING,a.ai.state)
        self.assertEqual((13,12),(a.x,a.y)); self.assertIsNone(getattr(a,'_last_known_px',None))
        self.assertIsNone(a.ai.target_x); self.assertEqual(0,a.ai.memory_turns)
        for _ in range(3): self.decision(a)
        self.assertEqual((16,12),(a.x,a.y)); self.assertIsNone(a.ai.sound_interest)
        self.assertEqual(AIState.WANDERING,a.ai.state)

    def test_zero_coordinates_do_not_become_player_targets_or_stair_intent(self):
        e=self.e; a=self.actor(x=2,y=0)
        e.local_map.set_tile(0,0,'stairs_down',True,True)
        emit(e,0,0,'flint')
        self.decision(a); self.decision(a)
        self.assertEqual((0,0),(a.x,a.y)); self.assertIsNone(a.ai.sound_interest)
        self.assertIsNone(getattr(a,'_pending_stair_use',None))
        self.assertIsNone(getattr(a,'_last_known_px',None))

    def test_sound_only_actor_stays_with_chunk_and_expires_on_return(self):
        e=self.e; e.world_map.width=2
        e.world_map.set(Chunk(1,0,RegionType.PLAINS,29418,visited=True))
        destination=LocalMap();destination.tiles[:]=make_tile('grass',True,True)
        e.save_manager.cache.store(1,0,destination,[])
        e.player.x,e.player.y=79,12; a=self.actor(x=79,y=14)
        e.local_map.set_tile(79,13,'wall',False,False)
        emit(e,75,14,'flint');self.decision(a);position=(a.x,a.y)
        self.assertEqual(AIState.INVESTIGATING,a.ai.state)
        e._handle_key(pygame.K_RIGHT)
        self.assertEqual([],e._live_pursuers);self.assertEqual([],e._pending_pursuer_arrivals)
        self.assertEqual([e.player],e.entities)
        e.world_time.turn+=INTEREST_TURNS+1;e._free_move_pending=True
        e._handle_key(pygame.K_LEFT)
        a=next(a for a in e.entities if a is not e.player)
        self.assertEqual(position,(a.x,a.y));self.assertIsNone(a.ai.sound_interest)

    def test_sound_only_actor_stays_with_stair_scene(self):
        e=self.e;e.player.x,e.player.y=12,12;a=self.actor(x=14,y=14)
        e.local_map.set_tile(13,13,'wall',False,False)
        emit(e,17,14,'flint');self.decision(a)
        sub=SubMap('g20-stair','cave','G20 scene fixture',19,generated=True,entry_x=12,entry_y=12)
        e.world_map.get(0,0).submaps.append(sub)
        e.local_map.submap_links[12,12]=sub.submap_id;e.local_map.set_tile(12,12,'stairs_down',True,True)
        underground=LocalMap();underground.tiles[:]=make_tile('grass',True,True)
        e.save_manager.cache.store_submap(sub.submap_id,underground,[])
        e._handle_key(pygame.K_PERIOD,'>')
        self.assertEqual(sub.submap_id,e.current_submap_id)
        self.assertEqual([],e._live_pursuers);self.assertEqual([],e._pending_pursuer_arrivals)
        self.assertEqual([e.player],e.entities)
        e._ascend_from_submap();self.assertEqual(2,len(e.entities))

    def test_event_during_ai_respects_order_and_actual_two_attack_budget(self):
        e=self.e;e.player.x,e.player.y=14,12
        first=self.actor(x=10,y=10);attacker=self.actor(x=13,y=12);last=self.actor(x=10,y=14)
        for y in range(10,14):e.local_map.set_tile(12,y,'wall',False,False)
        for a in (first,attacker,last):a.ai.move_accumulator=.2
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)):
            e.ai_system.process(e.entities,e.player,e.local_map,e.world_map,0,0,e.log,e.world_time,e.data,engine=e)
        self.assertEqual((10,10),(first.x,first.y));self.assertEqual(AIState.WANDERING,first.ai.state)
        self.assertIsNotNone(first.ai.sound_interest)
        self.assertEqual(AIState.INVESTIGATING,last.ai.state);self.assertNotEqual((10,14),(last.x,last.y))
        e.entities=[e.player,attacker];e.data=copy.copy(self.data);e.data.entities=copy.deepcopy(self.data.entities)
        e.data.entities['hollow_revenant']['speed']=2;attacker.ai.move_accumulator=0
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)),patch('engine.sound.emit',wraps=emit) as pulse:
            e.ai_system.process(e.entities,e.player,e.local_map,e.world_map,0,0,e.log,e.world_time,e.data,engine=e)
            self.assertEqual(2,pulse.call_count)

    def test_actual_trail_supersedes_and_ignored_lure_never_resurrects(self):
        e=self.e; a=self.actor(); emit(e,16,12,'flint')
        e.player.x,e.player.y=15,12; self.decision(a)
        self.assertIsNone(a.ai.sound_interest); self.assertIsNotNone(a._last_known_px)
        e.player.x,e.player.y=40,40
        emit(e,10,12,'bell_intact'); self.assertIsNone(a.ai.sound_interest)
        for _ in range(15): self.decision(a)
        self.assertIsNone(a.ai.sound_interest); self.assertNotEqual(AIState.INVESTIGATING,a.ai.state)

    def test_replacement_stronger_then_equal_latest_and_weaker_no_refresh(self):
        e=self.e; a=self.actor(); emit(e,16,12,'flint'); first=copy.deepcopy(a.ai.sound_interest)
        e.world_time.advance(); emit(e,17,12,'flint')
        self.assertEqual(first,a.ai.sound_interest)
        emit(e,12,16,'flint')
        self.assertEqual([12,16,first['deadline']+1],
                         [a.ai.sound_interest[k] for k in ('x','y','deadline')])
        emit(e,17,12,'combat'); self.assertEqual('combat',a.ai.sound_interest['kind'])

    def test_world_deadline_unreachable_free_ui_and_speed_independence(self):
        e=self.e; a=self.actor(); emit(e,17,12,'flint')
        deadline=a.ai.sound_interest['deadline']; start=e.world_time.turn
        # Close a ring after the event: interest stays finite even unreachable.
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            e.local_map.set_tile(12+dx,12+dy,'wall',False,False)
        for _ in range(20): self.decision(a); e._update_fov()
        self.assertEqual(deadline,a.ai.sound_interest['deadline']); self.assertEqual(start,e.world_time.turn)
        self.assertEqual((12,12),(a.x,a.y))
        for _ in range(INTEREST_TURNS): e.world_time.advance()
        self.assertIsNotNone(current_interest(a.ai,e.world_time.turn))
        e.world_time.advance(); e._update_fov()
        self.assertIsNone(a.ai.sound_interest); self.assertEqual(AIState.WANDERING,a.ai.state)
        for speed in (.5,2):
            emit(e,12,12,'flint'); a.ai.move_accumulator=speed
            e.world_time.turn=a.ai.sound_interest['deadline']+1
            self.decision(a); self.assertIsNone(a.ai.sound_interest)

    def test_special_ambush_fleeing_dormant_and_self_sound_keep_their_rules(self):
        e=self.e; a=self.actor('stone_lurker'); b=self.actor('heath_stalker',13,12)
        from components.ai import FleeingAI
        b.ai=FleeingAI()
        c=self.actor(x=14); c.ai.state=AIState.DORMANT
        emit(e,12,12,'bell_intact')
        for actor in (a,b,c): self.assertIsNone(actor.ai.sound_interest)
        self.assertFalse(hasattr(a,'_hibernating')); self.assertFalse(a.ai._triggered)
        a=self.actor(x=15); emit(e,15,12,'combat',maker=a)
        self.assertIsNone(a.ai.sound_interest)

    def test_visible_reaction_feedback_never_identifies_hidden_listener(self):
        e=self.e; a=self.actor(); e.local_map.tiles['visible'][:]=False
        emit(e,16,12,'flint'); before=len(e.log.messages); self.decision(a)
        self.assertEqual(before,len(e.log.messages))
        a.ai.state=AIState.WANDERING; e.local_map.tiles['visible'][:]=True
        self.decision(a)
        self.assertIn('turns toward a sound',e.log.messages[-1].text)

    def test_f9_and_separate_process_cold_load_restore_interest_and_clock(self):
        e=self.e; a=self.actor(); emit(e,16,12,'flint'); self.decision(a)
        e._free_move_pending=True; e._weapon_time_balance=-200000
        self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
        expected=snapshot(e)
        proc=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--cold',str(self.root)],
                            capture_output=True,text=True,timeout=45,env=dict(os.environ))
        self.assertEqual(0,proc.returncode,proc.stdout+proc.stderr)
        self.assertEqual(expected,json.loads(proc.stdout.strip().splitlines()[-1]))
        e.world_time.turn=100; a.ai.sound_interest=None
        e._handle_key(pygame.K_F9); self.assertEqual(expected,snapshot(e))
        # Expiry at restored clock, no load/reaction action or replay.
        e.world_time.turn=expected['turn']+INTEREST_TURNS+1; e._update_fov()
        self.assertTrue(e.save_manager.save(e)); expected=snapshot(e)
        self.assertTrue(e.save_manager.load(e)); self.assertEqual(expected,snapshot(e))

    def test_strict_optional_sound_state_and_old_absent_fingerprint(self):
        e=self.e; a=self.actor(); old=_serialize_entity(a)
        self.assertNotIn('sound_interest',old['component_state']['ai'])
        emit(e,16,12,'flint'); restore_actor_runtime(a,old)
        self.assertIsNone(a.ai.sound_interest); self.assertEqual(old,_serialize_entity(a))
        emit(e,16,12,'flint'); row=_serialize_entity(a)
        for field,value in (('x',-1),('x',True),('y',10000),('deadline',-1),('deadline',1.5),
                            ('strength',0),('strength',True),('kind','player'),('extra',1)):
            invalid=copy.deepcopy(row); invalid['component_state']['ai']['sound_interest'][field]=value
            with self.assertRaises(ValueError): validate_actor_runtime(invalid)
        invalid=copy.deepcopy(row); del invalid['component_state']['ai']['sound_interest']['y']
        with self.assertRaises(ValueError): _deserialize_entities([invalid],e)

    def test_validly_published_malformed_sound_rejects_transactionally(self):
        e=self.e; a=self.actor(); emit(e,16,12,'flint')
        self.assertTrue(e.save_manager.save(e)); before=snapshot(e)
        player,world,local=e.player,e.world_map,e.local_map
        payloads={p.relative_to(e.save_manager.checkpoint_path()).as_posix():p.read_bytes()
                  for p in e.save_manager.checkpoint_path().rglob('*') if p.is_file() and p.name!='manifest.json'}
        name=next(k for k in payloads if k.endswith('.pkl'))
        scene=pickle.loads(payloads[name]); scene.entities[0]['component_state']['ai']['sound_interest']['x']=True
        payloads[name]=pickle.dumps(scene)
        generation,_,_=e.save_manager.store.publish(payloads,None,e.save_manager.store.token())
        e.save_manager.generation=generation
        self.assertFalse(e.save_manager.load(e))
        self.assertIs(player,e.player); self.assertIs(world,e.world_map); self.assertIs(local,e.local_map)
        self.assertEqual(before,snapshot(e))

    def test_real_gather_inventory_cursor_consumption_changes_creature_route(self):
        e=self.e; e.player.x,e.player.y=12,12; e.local_map.set_tile(12,12,'flint_rock',True,True)
        # Fixed ordinary RNG, real gather roll and depletion, no factory insertion.
        e.rng=random.Random(1)
        e._update_fov()
        from engine.engine import GameMode
        e.mode=GameMode.INTERACTION_CURSOR; e.interaction_cursor.enter([(12,12)],12,12)
        before=e.world_time.turn
        with patch('engine.sound.emit') as pulse: e._handle_key(pygame.K_RETURN); pulse.assert_not_called()
        shard=e.player.inventory.get_by_id('flint_shard')
        self.assertIsNotNone(shard); self.assertEqual('flint_rock_depleted',str(e.local_map.tiles['terrain'][12,12]))
        self.assertEqual(before+1,e.world_time.turn)
        a=self.actor(x=17,y=15)
        # Genuine LOS break, open path around a corner; ordinary actor stats.
        for y in range(12,16): e.local_map.set_tile(14,y,'wall',False,False)
        e._update_fov(); use(e,shard); e._placement_cursor_x,e._placement_cursor_y=13,16
        e._handle_key(pygame.K_RETURN)
        self.assertFalse(e.player.inventory.contains(shard)); self.assertIsNotNone(a.ai.sound_interest)
        start=(a.x,a.y)
        e._handle_key(pygame.K_z)
        self.assertNotEqual(start,(a.x,a.y)); self.assertEqual(AIState.INVESTIGATING,a.ai.state)
        self.assertIsNone(getattr(a,'_last_known_px',None))

    def test_old_carried_shard_restores_exact_fields_and_new_inventory_use(self):
        e=self.e; item=e.item_factory.create('flint_shard'); item.on_use=None
        item.description='Historical cutting chip'; item.count=3; item.stackable=True
        self.assertTrue(e.player.inventory.add(item)); original=serialize_item(item)
        self.assertTrue(e.save_manager.save(e)); self.assertTrue(e.save_manager.load(e))
        item=e.player.inventory.items[0]; self.assertEqual(original,serialize_item(item))
        self.assertIn(dict(tag='cutting',tier=1),item.keywords)
        e._free_move_pending=True; before=timing(e); use(e,item)
        self.assertIsNone(item.on_use); self.assertEqual(before,timing(e))
        self.assertEqual(original,serialize_item(item)); self.assertIs(e._pending_throw['item'],item)
        e.local_map.tiles['visible'][:]=True
        e._placement_cursor_x,e._placement_cursor_y=41,40
        throw_key(e,pygame.K_RETURN)
        self.assertEqual(2,item.count); self.assertEqual(before[0]+1,e.world_time.turn)
        self.assertFalse(e._free_move_pending); self.assertEqual([],e.local_map.disruption_zones)
        self.assertIsNone(item.on_use)
        item.on_use='read'; from entities.item import use_capability
        self.assertEqual('read',use_capability(item))

    def test_cursor_free_steps_blocked_stale_scene_and_exact_owned_consumption(self):
        e=self.e; item=e.item_factory.create('flint_shard'); e.player.inventory.add(item)
        e._free_move_pending=True; before=timing(e); use(e,item)
        with patch('engine.sound.emit') as pulse:
            throw_key(e,pygame.K_RIGHT); throw_key(e,pygame.K_ESCAPE)
            self.assertEqual(before,timing(e)); self.assertTrue(e.player.inventory.contains(item))
            use(e,item); e._placement_cursor_x,e._placement_cursor_y=45,40
            e.local_map.tiles['visible'][:]=False; throw_key(e,pygame.K_RETURN)
            e.local_map.tiles['visible'][:]=True
            e.local_map.set_tile(42,40,'wall',False,False); throw_key(e,pygame.K_RETURN)
            e.local_map.set_tile(42,40,'flagstone',True,True)
            e._pending_throw['map']=LocalMap(); throw_key(e,pygame.K_RETURN)
            e._pending_throw['map']=e.local_map
            e.player.inventory.remove(item); throw_key(e,pygame.K_RETURN)
            pulse.assert_not_called(); self.assertEqual(before,timing(e))
            e.player.inventory.add(item); throw_key(e,pygame.K_RETURN)
            pulse.assert_called_once_with(e,45,40,'flint',maker=e.player)
        self.assertFalse(e.player.inventory.contains(item)); self.assertEqual(before[0]+1,e.world_time.turn)

    def test_committed_combat_pulses_once_across_zero_one_multiple_phases(self):
        e=self.e; e.player.x,e.player.y=12,12; equip(e,'crude_blade'); a=target(e)
        # Real commitment boundary; isolated outcome does not claim combat balance.
        with patch('engine.sound.emit') as pulse, patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)):
            e._player_attack(a); self.assertEqual(1,pulse.call_count)
            a.x=14; self.assertFalse(e._player_attack(a)); self.assertEqual(1,pulse.call_count)
            a.x=13; self.assertTrue(_monster_attack_entity(a,e.player,e)); self.assertEqual(2,pulse.call_count)
        for weapon,cost in (('binding_knife',.8),('crude_blade',1),('heavy_blade',1.2)):
            equip(e,weapon); e._weapon_time_balance=0
            # Copied no-cooldown definition isolates settlement, preserving real dispatch.
            definition=copy.deepcopy(e._get_equipped_weapon())
            for action in definition['movesets']: action['cooldown']=0; action['turn_cost']=cost
            e.moveset_cooldowns={}
            with patch.object(e,'_get_equipped_weapon',return_value=definition), patch('engine.sound.emit') as pulse:
                for _ in range(5): e._handle_key(e.display.MOVESET_KEY_1)
                self.assertEqual(5,pulse.call_count,weapon)

    def test_crate_pulse_only_after_successful_checked_dismantle(self):
        from generation.floor_object_utils import place_container
        from engine.engine import GameMode
        e=self.e;e.player.x,e.player.y=12,12;equip(e,'crude_blade')
        place_container(e.local_map,13,12,'crate',[]);e._update_fov()
        def cursor():
            e.mode=GameMode.INTERACTION_CURSOR;e.interaction_cursor.enter([(13,12)],12,12)
        with patch('engine.sound.emit',wraps=emit) as pulse:
            cursor();e._handle_key(pygame.K_x);e._handle_key(pygame.K_ESCAPE);pulse.assert_not_called()
            cursor();e._handle_key(pygame.K_x);e._handle_key(pygame.K_RETURN)
            pulse.assert_called_once_with(e,13,12,'dismantle',maker=e.player)
            self.assertNotIn((13,12),e.local_map.container_state)
            self.assertEqual('wood_bundle',e.local_map.floor_objects[13,12][0].item_id)
            cursor();e._handle_key(pygame.K_x);self.assertEqual(1,pulse.call_count)


if __name__ == '__main__':
    if '--cold' in sys.argv:
        print(json.dumps(cold(sys.argv[sys.argv.index('--cold')+1])))
    else:
        unittest.main()
