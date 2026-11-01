"""AI-1 controlled real-engine fixtures; no campaign or natural-selection claim."""
import copy
import json
import os
import random
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import test_gameplay_g20 as g20
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from components.ai import AIState, _monster_attack_entity, _monster_attack_result
from engine.ai_profiles import effective_profile, DEFAULTS
from engine.combat import CombatResult
from engine.creature_factory import CreatureFactory
from engine.local_rivals import revalidate, supported, allocate
from engine.save_manager import _serialize_entity, _deserialize_entities, _validate_entities, _validate_transfer_actor
from engine.sound import emit
from world.local_map import make_tile
from world.world_map import Chunk, RegionType, SubMap


def cold(root):
    with patch('engine.save_manager.SAVE_DIR', Path(root)):
        e = make_engine(load_data())
        assert e.save_manager.load(e), e.save_manager.last_error
        return [_serialize_entity(a) for a in e.entities if a is not e.player]


class StrikeWithdrawTests(unittest.TestCase):
    setUpClass = classmethod(g20.AudibleEncounterTests.setUpClass.__func__)

    def setUp(self):
        g20.AudibleEncounterTests.setUp(self)
        self.e.data = copy.copy(self.data)
        self.e.data.entities = copy.deepcopy(self.data.entities)
        self.e.creature_factory = CreatureFactory(self.e.data)
        self.e.player.x, self.e.player.y = 12,12
        self.e.local_map.visible[:] = True

    def actor(self, *, x=13, y=12, **profile):
        raw = self.e.data.entities['hollow_revenant']
        raw.update(ai_type='composite', ai_profile={**DEFAULTS, **profile},
                   can_cross_chunks=False, can_use_stairs=False, speed=1)
        a = self.e.creature_factory.spawn('hollow_revenant', x,y)
        self.e.entities.append(a)
        return a

    decision = g20.AudibleEncounterTests.decision

    def tick(self):
        e = self.e
        e.ai_system.process(e.entities,e.player,e.local_map,e.world_map,0,0,e.log,e.world_time,e.data,engine=e)

    def strike(self, a, result=None):
        with patch('engine.combat.resolve_attack', return_value=result or CombatResult(hit=True)) as resolver:
            self.decision(a)
        return resolver

    def test_one_resolver_truth_reject_miss_zero_damage_and_invincibility(self):
        a = self.actor()
        with patch('engine.combat.resolve_attack', return_value=CombatResult(hit=False, dodged=True)) as resolve:
            r = _monster_attack_result(a,self.e.player,self.e)
            self.assertEqual((True,False,0,'miss'),(r.committed,r.hit,r.damage,r.reason))
            resolve.assert_called_once()
        with patch('engine.combat.resolve_attack', return_value=CombatResult(hit=True,damage_dealt=0,blocked=True)) as resolve:
            r = _monster_attack_result(a,self.e.player,self.e)
            self.assertTrue(r.hit); self.assertEqual(0,r.damage); resolve.assert_called_once()
        self.e.player.dodge_chance=0
        self.e.player.fighter.effective_av=1000
        r=_monster_attack_result(a,self.e.player,self.e)
        self.assertTrue(r.hit);self.assertEqual(0,r.damage)  # real resolver, actual armour contact
        self.e.player_invincible = True
        with patch('engine.combat.resolve_attack') as resolve:
            r = _monster_attack_result(a,self.e.player,self.e)
            self.assertTrue(r.committed); self.assertFalse(r.hit); self.assertIsNone(r.damage)
            resolve.assert_not_called()
            self.assertIs(True,_monster_attack_entity(a,self.e.player,self.e))
            a.x=15
            self.assertIs(False,_monster_attack_entity(a,self.e.player,self.e))
        with patch.object(a.fighter,'can_attack',return_value=False):
            self.assertFalse(_monster_attack_result(a,self.e.player,self.e).committed)

    def test_trigger_variants_and_target_death_cancel(self):
        for trigger, hit, expected in [('hit',False,'approach'),('committed_attack',False,'withdraw'),('hit',True,'withdraw')]:
            self.e.entities=[self.e.player]
            a=self.actor(trigger=trigger)
            self.strike(a,CombatResult(hit=hit,damage_dealt=0))
            self.assertEqual(expected,a.ai.phase)
        self.e.player_invincible=True
        a.ai.cancel(a,'fixture');self.decision(a);self.assertEqual('approach',a.ai.phase)
        a.ai.profile['trigger']='committed_attack';self.decision(a);self.assertEqual('withdraw',a.ai.phase)
        self.e.player_invincible=False
        a.ai.cancel(a,'fixture');self.strike(a,CombatResult(hit=True,defender_dead=True))
        self.assertIsNone(a.ai.target);self.assertEqual('idle',a.ai.phase)

    def test_complete_cycle_and_full_hold_actions_no_free_step(self):
        a=self.actor(x=16)
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True)) as resolve:
            for _ in range(8):
                prior=(a.x,a.y);self.decision(a)
                self.assertLessEqual(max(abs(a.x-prior[0]),abs(a.y-prior[1])),1)
                if a.ai.phase=='withdraw':break
            self.assertEqual('withdraw',a.ai.phase);resolve.assert_called_once()
            strike_position=(a.x,a.y)
            self.assertEqual(1,max(abs(a.x-12),abs(a.y-12)))
            self.decision(a);self.assertNotEqual(strike_position,(a.x,a.y))
            self.assertEqual(('hold',1),(a.ai.phase,a.ai.hold_left))
            hold_position=(a.x,a.y);self.decision(a)
            self.assertEqual(('return',0),(a.ai.phase,a.ai.hold_left));self.assertEqual(hold_position,(a.x,a.y))
            self.decision(a);self.assertEqual('return',a.ai.phase)
            resolve.assert_called_once()
            self.decision(a);self.assertEqual('withdraw',a.ai.phase);self.assertEqual(2,resolve.call_count)

    def test_zero_hold_returns_on_next_granted_opportunity(self):
        a=self.actor(hold_opportunities=0)
        self.strike(a);self.decision(a)
        self.assertEqual('return',a.ai.phase)
        before=(a.x,a.y);self.decision(a)
        self.assertNotEqual(before,(a.x,a.y))
        # Already at distance at the start: no bookkeeping-only wait.
        a.ai.phase='withdraw';a.x,a.y=15,12
        self.decision(a);self.assertEqual((14,12),(a.x,a.y))

    def test_slow_normal_fast_and_disrupted_skip_cannot_bank_progress(self):
        for speed, opportunities in ((.5,0),(1,1),(2,2)):
            self.e.entities=[self.e.player]
            a=self.actor();self.e.data.entities[a._creature_id]['speed']=speed
            with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True)) as resolve:
                self.tick()
                self.assertEqual(opportunities,a.ai.opportunities)
                self.assertLessEqual(resolve.call_count,1)
                self.assertEqual(13 if speed<2 else 14,a.x)
            state=a.ai.snapshot();acc=a.ai.move_accumulator
            a._disrupted_turns=3
            for _ in range(5):self.tick()
            self.assertEqual(state,a.ai.snapshot());self.assertEqual(acc,a.ai.move_accumulator)

    def test_non_greedy_escape_replans_occupied_step_and_rejects_terrain(self):
        a=self.actor(retreat_distance=4,withdrawal_budget=8)
        m=self.e.local_map;m.tiles[:]=make_tile('wall',False,False)
        # A cul-de-sac: first step approaches prey before escaping around wall.
        cells=[(12,12),(13,12),(13,11),(12,11),(11,11),(10,11),(9,11),(8,11)]
        for xy in cells:m.set_tile(*xy,'floor',True,True)
        self.strike(a)
        self.decision(a);self.assertEqual((12,11),(a.x,a.y))
        for _ in range(8):
            if a.ai.phase!='withdraw':break
            self.decision(a)
        self.assertEqual('hold',a.ai.phase)
        a.ai.phase='withdraw';a.ai.withdraw_left=8;a.x,a.y=13,12
        blocker=self.e.creature_factory.spawn('heath_stalker',13,11);self.e.entities.append(blocker)
        blocker2=self.e.creature_factory.spawn('heath_stalker',12,11);self.e.entities.append(blocker2)
        self.decision(a);self.assertEqual((13,12),(a.x,a.y));self.assertEqual(7,a.ai.withdraw_left)
        self.e.entities.remove(blocker2);self.decision(a);self.assertEqual((12,11),(a.x,a.y))
        a.x,a.y=13,12
        m.set_tile(12,11,'ai1_forbidden',True,True);self.e.data.terrain['ai1_forbidden']={'creature_passable':False}
        self.decision(a);self.assertEqual((13,12),(a.x,a.y))

    def test_trapped_fallback_never_rearms_on_defensive_hit(self):
        a=self.actor(withdrawal_budget=2)
        m=self.e.local_map;m.tiles[:]=make_tile('wall',False,False)
        for xy in ((12,12),(13,12)):m.set_tile(*xy,'floor',True,True)
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True)) as resolve:
            self.decision(a);self.decision(a);self.decision(a)
            self.assertEqual('cornered',a.ai.phase);self.assertEqual(0,a.ai.withdraw_left)
            for _ in range(12):self.decision(a)
            self.assertEqual('cornered',a.ai.phase);self.assertEqual(0,a.ai.withdraw_left)
            self.assertEqual(13,resolve.call_count)
            m.set_tile(14,12,'floor',True,True);self.decision(a)
            self.assertEqual(('hold',14),(a.ai.phase,a.x))

    def test_move_impairment_spends_finite_withdraw_budget(self):
        a=self.actor(withdrawal_budget=2);self.strike(a)
        with patch.object(a.fighter,'can_move',return_value=False):
            for _ in range(2):self.decision(a)
            self.assertEqual((13,12),(a.x,a.y));self.assertEqual('cornered',a.ai.phase)
            self.strike(a);self.assertEqual('cornered',a.ai.phase)

    def test_too_small_budget_cannot_rearm_an_unchanged_available_route(self):
        a=self.actor(retreat_distance=8,withdrawal_budget=1)
        self.strike(a);self.decision(a)
        self.assertEqual('cornered',a.ai.phase);self.assertFalse(a.ai.route_blocked)
        position=(a.x,a.y)
        for _ in range(8):self.decision(a)
        self.assertEqual('idle',a.ai.phase);self.assertEqual(position,(a.x,a.y))

    def test_zero_timeout_target_invalidation_and_foreign_scene_cancel_whole_intent(self):
        a=self.actor(hold_opportunities=12);a.ai.profile['pursuit_timeout']=0
        self.strike(a);self.e.player.x=40;self.e.world_time.turn+=1;self.decision(a)
        self.assertEqual(('idle',None),(a.ai.phase,a.ai.target))
        self.e.player.x=12;self.strike(a);a.perception.hostile_to=[];revalidate(self.e,a)
        self.assertEqual(('idle',None),(a.ai.phase,a.ai.target))
        a.perception.hostile_to=['player'];self.strike(a)
        a.ai.target['owner']='1,0/';revalidate(self.e,a)
        self.assertEqual(('idle',None),(a.ai.phase,a.ai.target))

    def test_hold_refreshes_visible_rival_without_replacing_prey(self):
        a=self.actor(hold_opportunities=12)
        self.e.player.x,self.e.player.y=40,40
        b=self.e.creature_factory.spawn('heath_stalker',12,12);self.e.entities.append(b)
        a.perception.hostile_to=['stalker'];self.strike(a);self.decision(a)
        for turn in range(1,11):
            self.e.world_time.turn=turn;self.decision(a)
            self.assertEqual(b._individual_id,a.ai.target['id']);self.assertEqual(turn,a.ai.target['seen'])
        self.e.player.x,self.e.player.y=a.x,a.y+1;a.perception.hostile_to.append('player')
        self.decision(a);self.assertEqual(b._individual_id,a.ai.target['id'])

    def test_hidden_position_and_inclusive_world_expiry_both_roles(self):
        for rival in (False,True):
            self.e.entities=[self.e.player];self.e.player.x,self.e.player.y=12,12
            a=self.actor(hold_opportunities=12)
            self.e.data.entities[a._creature_id]['pursuit_timeout']=2
            a.ai.profile['pursuit_timeout']=2
            target=self.e.player
            if rival:
                self.e.player.x,self.e.player.y=40,40
                target=self.e.creature_factory.spawn('heath_stalker',12,12);self.e.entities.append(target)
                a.perception.hostile_to=['stalker']
            self.e.world_time.turn=10;self.strike(a);trail=copy.deepcopy(a.ai.target)
            target.x,target.y=35,35
            self.e.world_time.turn=12;self.decision(a)
            self.assertEqual(trail,a.ai.target)
            self.e.world_time.turn=13;self.decision(a)
            self.assertEqual('idle',a.ai.phase);self.assertIsNone(a.ai.target)

    def test_approach_no_progress_and_hidden_search_finish(self):
        a=self.actor(x=16)
        with patch.object(a.fighter,'can_move',return_value=False):
            for _ in range(12):self.decision(a)
        self.assertEqual('idle',a.ai.phase);self.assertEqual('player',a.ai.suppressed)
        for _ in range(10):self.decision(a)
        self.assertEqual((16,12),(a.x,a.y));self.assertIsNone(a.ai.target)
        self.e.player.x=40;self.decision(a);self.assertIsNone(a.ai.suppressed)
        self.e.player.x=14;self.decision(a);self.assertIsNotNone(a.ai.target)
        remembered=(a.ai.target['x'],a.ai.target['y']);self.e.player.x=40
        for _ in range(5):self.decision(a)
        self.assertIsNone(a.ai.target);self.assertEqual(remembered,(a.x,a.y))

    def test_rival_actor_recipient_empty_hostility_and_death_credit(self):
        e=self.e;e.player.x,e.player.y=40,40
        a=self.actor();b=e.creature_factory.spawn('highland_bandit',12,12);e.entities.append(b)
        a.perception.hostile_to=['outlaw'];b.perception.hostile_to=['hollow']
        self.assertTrue(supported(a));self.assertTrue(supported(b))
        self.strike(a);self.assertEqual(b._individual_id,a.ai.target['id'])
        self.decision(b);self.assertEqual(a._individual_id,b.ai.local_target['id'])
        a.perception.hostile_to=[];revalidate(e,a);self.assertIsNone(a.ai.target)
        self.decision(a);self.assertIsNone(a.ai.target)
        a.perception.hostile_to=['outlaw'];b.fighter.hp=1
        xp=e.player.level.exp
        with patch('engine.combat.roll_dice',return_value=100):self.decision(a)
        self.assertFalse(b.is_alive);self.assertTrue(b._death_finalized)
        self.assertEqual(xp,e.player.level.exp);self.assertIsNone(a.ai.target)
        self.assertTrue(e.local_map.floor_objects.get((b.x,b.y)))

    def test_anonymous_sound_and_readonly_diagnostics_no_action_or_refresh(self):
        from engine.composite_diagnostics import inspect
        a=self.actor();e=self.e;e.player.x,e.player.y=40,40
        self.assertEqual(1,emit(e,16,12,'flint'))
        self.assertNotIn('maker',a.ai.sound_interest)
        before=(a.x,a.y);self.decision(a)
        self.assertNotEqual(before,(a.x,a.y));self.assertEqual('anonymous_sound',a.ai.trace[-1]['reason'])
        e.player.x,e.player.y=a.x-1,a.y;self.strike(a)
        emit(e,18,12,'combat');self.assertIsNone(a.ai.sound_interest)
        state=_serialize_entity(a)
        for _ in range(20):inspect(e);e._update_fov()
        self.assertEqual(state,_serialize_entity(a))
        e.local_map.visible[:]=False
        logs=len(e.log.messages);self.decision(a)
        self.assertEqual(logs,len(e.log.messages))

    def test_save_f9_profile_edit_and_separate_process_actual_reconstruction(self):
        a=self.actor(retreat_distance=4,hold_opportunities=3);self.strike(a);self.decision(a)
        for phase in ('withdraw','hold'):
            while a.ai.phase!=phase:self.decision(a)
            expected=_serialize_entity(a)
            self.assertTrue(self.e.save_manager.save(self.e),self.e.save_manager.last_error)
            self.e.data.entities[a._creature_id]['ai_profile']['retreat_distance']=2
            fresh=self.e.creature_factory.spawn(a._creature_id,25,25)
            self.assertEqual(2,fresh.ai.profile['retreat_distance'])
            self.assertTrue(self.e.save_manager.load(self.e),self.e.save_manager.last_error)
            a=next(a for a in self.e.entities if a is not self.e.player)
            self.assertEqual(expected,_serialize_entity(a))
            env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(GAME_ROOT),str(Path(__file__).parent)]))
            code='import json;from test_ai_1 import cold;print(json.dumps(cold('+repr(str(self.root))+')))'
            process=subprocess.run([sys.executable,'-B','-c',code],env=env,cwd=GAME_ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(0,process.returncode,process.stderr)
            self.assertEqual([expected],json.loads(process.stdout.strip().splitlines()[-1]))
            if phase=='withdraw':
                while a.ai.phase=='withdraw':self.decision(a)

    def test_malformed_profile_state_and_discriminator_reject_before_install(self):
        a=self.actor();self.strike(a);row=_serialize_entity(a)
        for field,value in [('version',True),('version',2),('recipe','unknown'),('trigger',False),('retreat_distance',float('inf')),('hold_opportunities',-1),('withdrawal_budget',False)]:
            bad=copy.deepcopy(row);bad['composite']['profile'][field]=value
            with self.assertRaisesRegex(ValueError,'profile'):_validate_entities([bad],self.e.data)
        for mutate in (lambda r:r.pop('composite'),lambda r:r.update(ai_type='WanderingAI'),
                       lambda r:r['composite']['state'].update(phase='hold',target=None),
                       lambda r:r['composite']['state'].update(withdraw_left=True)):
            bad=copy.deepcopy(row);mutate(bad)
            with self.assertRaises(ValueError):_validate_entities([bad],self.e.data)
        with self.assertRaises(ValueError):_validate_transfer_actor(row)
        legacy=self.e.creature_factory.spawn('heath_stalker',16,16)
        self.assertNotIn('composite',_serialize_entity(legacy))

    def test_successful_scene_departure_only_cancels_and_never_transfers(self):
        e=self.e;a=self.actor();self.strike(a);before=_serialize_entity(a)
        e._prepare_destination=lambda *args:None
        e._descend_to_submap('absent');self.assertEqual(before,_serialize_entity(a))
        chunk=e.world_map.get(0,0);chunk.submaps.append(SubMap('ai1','cave','AI1',17,layout_id='starting_lab',surface_x=12,surface_y=12))
        del e._prepare_destination
        # Actual handlers prepare/cache/reload the ordinary authored room.
        e._descend_to_submap('ai1')
        self.assertEqual('ai1',e.current_submap_id)
        self.assertFalse(any(getattr(t[0],'_creature_id',None)=='hollow_revenant' for t in e._live_pursuers))
        self.assertFalse(e._pending_pursuer_arrivals)
        e._ascend_from_submap()
        restored=[x for x in e.entities if getattr(x,'_individual_id',None)==a._individual_id]
        self.assertEqual(1,len(restored));b=restored[0]
        self.assertEqual(('idle',None),(b.ai.phase,b.ai.target))
        self.assertEqual((a.x,a.y,a.fighter.hp),(b.x,b.y,b.fighter.hp))
        self.assertFalse(e._live_pursuers);self.assertFalse(e._pending_pursuer_arrivals)

    def test_chunk_departure_actual_handlers_and_stale_transfer_admission(self):
        from world.local_map import LocalMap
        import pygame
        e=self.e;e.player.x,e.player.y=79,12
        a=self.actor(x=78);self.strike(a);identity=a._individual_id
        before=(a.x,a.y,a.fighter.hp)
        e.world_map.width=2;e.world_map.set(Chunk(1,0,RegionType.PLAINS,29418,visited=True))
        m=LocalMap();m.tiles[:]=make_tile('grass',True,True);e.save_manager.cache.store(1,0,m,[])
        self.assertTrue(e._transition_chunk(1,0));self.assertFalse(e._live_pursuers);self.assertFalse(e._pending_pursuer_arrivals)
        self.assertTrue(e._transition_chunk(-1,0))
        matches=[x for x in e.entities if getattr(x,'_individual_id',None)==identity]
        self.assertEqual(1,len(matches));a=matches[0]
        self.assertEqual(before,(a.x,a.y,a.fighter.hp));self.assertEqual(('idle',None),(a.ai.phase,a.ai.target))
        # Deliberately stale state/flags still cannot admit the profile to bypass paths.
        e.data.entities[a._creature_id]['can_cross_chunks']=True;a.ai.state=AIState.HUNTING
        a._last_known_px,a._last_known_py=79,12;a.x=79
        e._check_entity_chunk_crossings();self.assertFalse(e._pending_pursuer_arrivals)
        a._pending_stair_use='stairs_up';e._process_creature_stair_transfers();self.assertIn(a,e.entities)
        self.assertIsNone(a._pending_stair_use)
        position=(a.x,a.y)
        e.ai_system.process_single(a,e.local_map,12,12,e.entities,e.log,engine=e)
        self.assertEqual(position,(a.x,a.y))


if __name__=='__main__':unittest.main()
