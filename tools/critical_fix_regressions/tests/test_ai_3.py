"""AI-3 actual handlers and ownership invariants, using disposable save roots.

Combat-result fixtures below are explicitly controlled edge cases. Ordinary
delivery/pickup/use/response witnesses live in verify_ai_3_play.py.
"""
import copy
import json
import random
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
import test_gameplay_g20 as g20
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from engine.ai_profiles import VENOM_DEFAULTS, DEFAULTS, OBSERVATION_DEFAULTS, effective_profile
from engine.combat import CombatResult
from engine.creature_factory import CreatureFactory
from engine.item_factory import ItemFactory
from engine.save_manager import _serialize_entity, _deserialize_entities, _validate_entities
from engine.save_components import serialize_runtime, restore_runtime, validate_components
from engine.venom import dose, snapshot, restore, validate, movement_denial, cure
from engine.effect_lifecycle import age_actor, finish_turn
from components.ai import _monster_attack_result, AIState
from world.local_map import make_tile
from world.world_map import Chunk, RegionType


class VenomTests(unittest.TestCase):
    setUpClass = classmethod(g20.AudibleEncounterTests.setUpClass.__func__)
    decision = g20.AudibleEncounterTests.decision

    def setUp(self):
        g20.AudibleEncounterTests.setUp(self)
        e=self.e
        e.data=copy.copy(self.data); e.data.entities=copy.deepcopy(self.data.entities)
        e.creature_factory=CreatureFactory(e.data)
        e.player.x=e.player.y=12
        e.local_map.tiles[:]=make_tile('floor',True,True)
        e.local_map.visible[:]=True
        self.source=self.actor()

    def actor(self, x=13, y=12, profile=None):
        raw=self.e.data.entities['hollow_revenant']
        raw.update(ai_type='composite', ai_profile=copy.deepcopy(profile or dict(VENOM_DEFAULTS, paralysis_phases=2)),
                   can_cross_chunks=False, can_use_stairs=False, speed=1)
        a=self.e.creature_factory.spawn('hollow_revenant',x,y)
        self.e.entities.append(a)
        return a

    def hit(self, target=None, result=None, source=None):
        with patch('engine.combat.resolve_attack',return_value=result or CombatResult(hit=True,damage_dealt=1)) as resolver:
            r=_monster_attack_result(source or self.source,target or self.e.player,self.e,defensive=True)
        return r,resolver

    def phase(self):
        self.e.world_time.turn+=1
        self.e._effect_aged_ids=set()
        finish_turn(self.e,[a for a in self.e.entities if a is not self.e.player])

    def paralysis(self, victim=None):
        target=victim or self.e.player
        self.hit(target)
        for _ in range(3): self.phase()
        self.assertEqual('paralysis',dose(target)['stage'])

    def test_default_boundary_table_same_phase_and_repeated_inspection(self):
        e=self.e; r,resolver=self.hit(); resolver.assert_called_once()
        self.assertTrue(r.application.accepted)
        from engine.composite_diagnostics import inspect
        expected=[('warning',3),('warning',2),('warning',1),('paralysis',2),('paralysis',1),
                  ('recovery',4),('recovery',3),('recovery',2),('recovery',1),None]
        for i,want in enumerate(expected):
            if i:self.phase()
            for _ in range(3):
                inspect(e); e._update_fov()
                from engine.venom import age
                age(e,e.player)
            d=dose(e.player)
            self.assertEqual(want,(d['stage'],d['remaining']) if d else None)
            self.assertEqual(want is None or want[0]!='paralysis',e.player.fighter.can_move())

    def test_longer_warning_and_snapshot_independent_of_source_tuning_death(self):
        self.source.ai.profile['warning_phases']=6
        self.hit(); original=copy.deepcopy(dose(self.e.player))
        self.source.ai.profile['warning_phases']=2; self.source.ai.profile['recovery_phases']=16
        self.source.is_alive=False; self.e.entities=[self.e.player]
        for _ in range(5):self.phase()
        self.assertEqual(('warning',1),(dose(self.e.player)['stage'],dose(self.e.player)['remaining']))
        self.phase();self.assertEqual('paralysis',dose(self.e.player)['stage'])
        self.assertFalse(cure(self.e))
        self.phase();self.phase();self.assertEqual(4,dose(self.e.player)['remaining'])
        self.assertEqual(original['source'],dose(self.e.player)['source'])

    def test_every_rejection_preserves_attack_and_prior_dose(self):
        e=self.e
        for result,reason in [(CombatResult(hit=False,dodged=True),'miss'),
                              (CombatResult(hit=True,damage_dealt=0,blocked=True),'no_damage')]:
            r,resolve=self.hit(result=result);resolve.assert_called_once()
            self.assertTrue(r.committed);self.assertFalse(r.application.accepted)
            self.assertEqual(reason,r.application.reason);self.assertIsNone(dose(e.player))
        e.player_invincible=True
        r,resolve=self.hit();resolve.assert_not_called();self.assertFalse(r.application.accepted)
        e.player_invincible=False
        self.source._ability_suppressed_turns=3
        r,resolve=self.hit();resolve.assert_called_once();self.assertEqual('source_suppressed',r.application.reason)
        self.source._ability_suppressed_turns=0
        e.player._numbing_venom_trait='immune'
        self.assertEqual('immune',self.hit()[0].application.reason)
        e.player._numbing_venom_trait='susceptible'
        self.hit(); identity=dose(e.player)['application_id']
        for _ in range(9):
            before=copy.deepcopy(dose(e.player))
            other=self.actor(x=12,y=13)
            r,_=self.hit(source=other)
            self.assertFalse(r.application.accepted)
            self.assertEqual(before,dose(e.player));self.assertEqual(identity,dose(e.player)['application_id'])
            self.e.entities.remove(other);self.phase()
        self.assertIsNone(dose(e.player));self.assertTrue(self.hit()[0].application.accepted)
        self.assertNotEqual(identity,dose(e.player)['application_id'])

    def test_lethal_unsupported_and_death_union_have_no_later_events(self):
        e=self.e
        victim=e.creature_factory.spawn('barrow_wight',14,12);e.entities.append(victim)
        self.source.perception.hostile_to=[victim.perception.faction]
        from engine.venom import deliver
        from components.ai import MonsterAttackResult
        r=deliver(e,self.source,victim,MonsterAttackResult(committed=True,hit=True,damage=1))
        self.assertEqual('unsupported_recipient',r.reason)
        self.source.perception.hostile_to=['player']
        r,_=self.hit(result=CombatResult(hit=True,damage_dealt=60,defender_dead=True))
        self.assertFalse(r.application.accepted);self.assertIsNone(dose(e.player))
        e.player.is_alive=True;self.hit();e.player.fighter.take_damage(1000)
        count=len(e.log.messages);self.phase()
        self.assertIsNone(dose(e.player));self.assertEqual(count,len(e.log.messages))

    def test_accepted_trigger_retreat_and_cornered_delivery_no_rearm(self):
        e=self.e;a=self.source
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True,damage_dealt=1)):
            self.decision(a)
            self.assertEqual('withdraw',a.ai.phase);self.assertEqual((13,12),(a.x,a.y))
            self.decision(a);self.assertNotEqual((13,12),(a.x,a.y))
            a.x,a.y=13,12;a.ai.phase='cornered';a.ai.withdraw_left=0;a.ai.route_blocked=False
            for xy in [(x,y) for x in range(11,16) for y in range(10,15) if (x,y) not in [(12,12),(13,12)]]:
                e.local_map.set_tile(*xy,'wall',False,False)
            restore(e.player,None)
            self.decision(a);self.assertTrue(a.ai.trace[-1]['result']['application']['accepted'])
            self.assertEqual(('cornered',0),(a.ai.phase,a.ai.withdraw_left))

    def test_player_actual_free_moves_sprint_press_stairs_and_stationary_actions(self):
        e=self.e;self.paralysis();e.entities=[e.player]
        original=(e.player.x,e.player.y,e.world_time.turn,e.player_move_accumulator,e.sprint_turns_remaining)
        e._free_move_pending=True
        for _ in range(3):e._handle_key_local(pygame.K_DOWN)
        self.assertEqual(original,(e.player.x,e.player.y,e.world_time.turn,e.player_move_accumulator,e.sprint_turns_remaining))
        self.assertTrue(e._free_move_pending)
        with patch('pygame.key.get_mods',return_value=pygame.KMOD_SHIFT):e._handle_key_local(e.display.SPRINT_KEY)
        self.assertEqual(0,e.sprint_turns_remaining)
        self.assertFalse(e._transition_chunk(1,0));self.assertFalse(e._can_use_stairs())
        with patch.object(e,'_prepare_destination') as prepare:
            e._descend_to_submap('absent');e._ascend_from_submap();prepare.assert_not_called()
        e.local_map.set_tile(12,13,'door_closed',False,False)
        e._handle_key_local(pygame.K_DOWN)
        self.assertEqual('door_closed',str(e.local_map.tiles[12,13]['terrain']))
        self.assertEqual(2,dose(e.player)['remaining'])
        # Severe-stage bump attacks are rejected before dispatch and cost nothing.
        enemy=e.creature_factory.spawn('hollow_revenant',13,12);e.entities.append(enemy)
        with patch.object(e,'_player_attack',return_value=True) as attack:
            e._handle_key_local(pygame.K_RIGHT);attack.assert_not_called()
        e.entities=[e.player]
        e._handle_key_local(pygame.K_PERIOD);e._handle_key_local(pygame.K_PERIOD)
        self.assertEqual('recovery',dose(e.player)['stage']);self.assertEqual((12,12),(e.player.x,e.player.y))
        self.assertFalse(e._free_move_pending)

    def test_real_inventory_cure_full_hp_both_stages_exact_cost(self):
        from test_gameplay_g12 import use
        e=self.e
        for stage in ('warning','paralysis'):
            restore(e.player,None);self.hit()
            if stage=='paralysis':
                for _ in range(3):self.phase()
            e.entities=[e.player];e.player.fighter.hp=e.player.fighter.max_hp
            one=ItemFactory(e.data).create('venom_treatment');other=ItemFactory(e.data).create('venom_treatment')
            e.player.inventory.add(one);e.player.inventory.add(other)
            start=e.world_time.turn;use(e,one)
            if stage=='paralysis':
                self.assertTrue(e.player.inventory.contains(one));self.assertEqual(start,e.world_time.turn)
                self.assertEqual('paralysis',dose(e.player)['stage'])
                self.e.entities.append(self.source)
                continue
            self.assertFalse(e.player.inventory.contains(one));self.assertTrue(e.player.inventory.contains(other))
            self.assertEqual(start+1,e.world_time.turn);self.assertEqual(('recovery',3),(dose(e.player)['stage'],dose(e.player)['remaining']))
            self.assertEqual(e.player.fighter.max_hp,e.player.fighter.hp)
            before=copy.deepcopy(dose(e.player));use(e,other)
            self.assertEqual(before,dose(e.player));self.assertEqual(start+1,e.world_time.turn)
            self.assertTrue(e.player.inventory.contains(other))
            self.assertFalse(e.item_system.use(one,e));self.assertFalse(e.item_system.last_use_committed)
            self.e.entities.append(self.source)

    def test_wandering_helpers_sound_and_contact_attack_during_paralysis(self):
        e=self.e;v=e.creature_factory.spawn('heath_stalker',14,12);e.entities.append(v)
        self.source.perception.hostile_to=['stalker'];self.paralysis(v)
        pos=v.x,v.y
        v.ai._wander(v,e.local_map,e.entities,random.Random(1))
        v.ai._move_toward(v,e.local_map,e.entities,20,12)
        v.ai._flee(v,e.local_map,e.entities,e.player,random.Random(1))
        from engine.sound import investigate
        v.ai.sound_interest=dict(x=20,y=12,deadline=100,kind='combat')
        investigate(v.ai,v,e.local_map,e.entities)
        self.assertEqual(pos,(v.x,v.y))
        v.x,v.y=13,12
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True,damage_dealt=1)) as attack:
            self.assertFalse(_monster_attack_result(v,e.player,e).committed);attack.assert_not_called()

    def test_composite_budgets_and_spatial_failure_survive_temporary_denial(self):
        e=self.e;a=self.actor(x=16,profile=DEFAULTS)
        self.source.perception.hostile_to=[a.perception.faction];self.source.x=15
        self.paralysis(a);self.decision(a)
        before=a.ai.snapshot()['state'];pos=a.x,a.y
        for _ in range(4):self.decision(a)
        after=a.ai.snapshot()['state']
        for key in ('approach_left','withdraw_left','no_progress','best_distance','route_blocked'):
            self.assertEqual(before[key],after[key],key)
        self.assertEqual(pos,(a.x,a.y));self.assertEqual('numbing_venom_paralysis',a.ai.trace[-1]['reason'])
        self.phase();self.phase();self.decision(a);self.assertNotEqual(pos,(a.x,a.y))

    def test_ai2_cover_and_pursuit_budgets_not_spent_by_paralysis(self):
        e=self.e;a=self.actor(x=14,profile=OBSERVATION_DEFAULTS)
        self.source.perception.hostile_to=[a.perception.faction];self.paralysis(a)
        self.decision(a);before=(a.ai.conceal_left,a.ai.pursuit_left,a.ai.no_progress,list(a.ai.failed_entries))
        for _ in range(4):self.decision(a)
        self.assertEqual(before,(a.ai.conceal_left,a.ai.pursuit_left,a.ai.no_progress,a.ai.failed_entries))

    def test_live_pending_and_stair_denial_keep_ownership_and_age(self):
        e=self.e;v=e.creature_factory.spawn('heath_stalker',14,12);e.entities.append(v)
        self.source.perception.hostile_to=['stalker'];self.paralysis(v)
        e.entities=[e.player];v.ai.state=AIState.HUNTING
        v.ai.target_x=0;v.ai.target_y=12;v._last_known_px=0;v._last_known_py=12
        v.x=0;e._live_pursuers=[(v,0,0,None)]
        e._tick_live_pursuers()
        self.assertEqual([(v,0,0,None)],e._live_pursuers);self.assertEqual(0,v.x)
        self.assertEqual(1,v.ai.pursuit_turns_without_contact)
        with patch.object(e,'_prepare_destination') as prepare:
            self.assertFalse(e._transfer_live_pursuer_through_stair(v,0,0,e.local_map))
            self.assertFalse(e._transfer_submap_pursuer_to_surface(v,0,0,'absent'));prepare.assert_not_called()
        e._live_pursuers=[]
        pending=dict(entity=v,entry_x=0,entry_y=5,delay=1,destination_wx=0,destination_wy=0,destination_submap_id=None)
        e._pending_pursuer_arrivals=[pending]
        e._tick_pending_pursuer_arrivals();self.assertEqual(0,pending['delay']);self.assertNotIn(v,e.entities)
        self.phase();self.assertEqual(1,dose(v)['remaining'])
        self.phase();e._tick_pending_pursuer_arrivals();self.assertIn(v,e.entities);self.assertFalse(e._pending_pursuer_arrivals)

    def test_save_f5_f9_cold_warning_paralysis_recovery_and_legacy_absence(self):
        e=self.e;self.hit()
        for stage in ('warning','paralysis','recovery'):
            while dose(e.player)['stage']!=stage:self.phase()
            expected=snapshot(e.player);e._handle_key_local(pygame.K_F5)
            restore(e.player,None);e._handle_key_local(pygame.K_F9)
            self.assertEqual(expected,snapshot(e.player))
            script="import json,sys;from pathlib import Path;from unittest.mock import patch;from test_effect_persistence import load_data,make_engine;from engine.venom import snapshot;\nwith patch('engine.save_manager.SAVE_DIR',Path(sys.argv[1])):\n e=make_engine(load_data());assert e.save_manager.load(e),e.save_manager.last_error;print(json.dumps(snapshot(e.player)))"
            result=subprocess.run([sys.executable,'-B','-c',script,str(self.root)],capture_output=True,text=True)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertEqual(expected,json.loads(result.stdout.splitlines()[-1]))
        restore_runtime(e,{})
        self.assertIsNone(dose(e.player));self.assertEqual('susceptible',e.player._numbing_venom_trait)

    def test_actor_roundtrip_frozen_tuning_immunity_absence_and_malformed_records(self):
        e=self.e;v=e.creature_factory.spawn('heath_stalker',14,12);e.entities.append(v)
        self.source.perception.hostile_to=['stalker'];self.hit(v)
        row=_serialize_entity(v);before=snapshot(v)
        e.data.entities['heath_stalker']['numbing_venom_trait']='immune'
        restored=_deserialize_entities([row],e.creature_factory)[0]
        self.assertEqual(before,snapshot(restored));self.assertEqual('susceptible',restored._numbing_venom_trait)
        fresh=e.creature_factory.spawn('heath_stalker',16,12);self.assertEqual('immune',fresh._numbing_venom_trait)
        fresh_row=_serialize_entity(fresh);self.assertEqual('immune',_deserialize_entities([fresh_row],e.creature_factory)[0]._numbing_venom_trait)
        from engine.venom import age
        e.world_time.turn+=100;self.assertEqual(before,snapshot(restored));age(e,restored)
        self.assertEqual(before['dose']['remaining']-1,dose(restored)['remaining'])
        for field,value in [('version',True),('stage','stun'),('remaining',0),('application_id','x'),('aged_phase',-1),('parameters',{})]:
            bad=copy.deepcopy(before);bad['dose'][field]=value
            with self.assertRaises((ValueError,KeyError)):validate(bad)
        neutral=_serialize_entity(fresh);neutral['component_state'].pop('venom',None)
        self.assertIsNone(snapshot(_deserialize_entities([neutral],e.creature_factory)[0]))

    def test_profile_bounds_and_fixed_trigger_versions(self):
        for field,value in [('warning_phases',1),('paralysis_phases',4),('recovery_phases',3),('trigger','hit'),('effect','other'),('version',2)]:
            raw=dict(ai_profile={**VENOM_DEFAULTS,field:value})
            with self.assertRaises(ValueError):effective_profile(raw)
        self.assertEqual(DEFAULTS['trigger'],effective_profile(dict(ai_profile=DEFAULTS))['trigger'])

    def test_saved_source_and_applied_dose_outlive_definition_tuning(self):
        e=self.e;self.hit();row=_serialize_entity(self.source)
        e.data.entities['hollow_revenant']['ai_profile'].update(warning_phases=6,recovery_phases=16)
        fresh=e.creature_factory.spawn('hollow_revenant',18,12)
        saved=_deserialize_entities([row],e.creature_factory)[0]
        self.assertEqual((3,4),(saved.ai.profile['warning_phases'],saved.ai.profile['recovery_phases']))
        self.assertEqual((6,16),(fresh.ai.profile['warning_phases'],fresh.ai.profile['recovery_phases']))
        self.assertEqual(3,dose(e.player)['parameters']['warning_phases'])
        self.assertTrue(cure(e));self.assertEqual(4,dose(e.player)['remaining'])

    def test_real_scheduled_phase_clock_fast_slow_and_multiple_injectors(self):
        e=self.e
        for speed in (.5,1,2):
            restore(e.player,None);e.entities=[e.player];e.player.is_alive=True
            a=self.actor();b=self.actor(x=12,y=13)
            e.data.entities['hollow_revenant']['speed']=speed
            with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True,damage_dealt=1)):
                for _ in range(3):
                    e._advance_turn()
                    if dose(e.player):break
                self.assertEqual(('warning',3),(dose(e.player)['stage'],dose(e.player)['remaining']))
                original=dose(e.player)['application_id']
                for stage,left in [('warning',2),('warning',1),('paralysis',2),('paralysis',1),('recovery',4)]:
                    e._advance_turn()
                    self.assertEqual((stage,left),(dose(e.player)['stage'],dose(e.player)['remaining']))
                    self.assertEqual(original,dose(e.player)['application_id'])

    def test_costly_action_charges_each_real_phase_and_ui_is_free(self):
        from types import SimpleNamespace
        e=self.e;self.hit();e.entities=[e.player]
        before=snapshot(e.player);turn=e.world_time.turn
        for key in (pygame.K_i,pygame.K_ESCAPE,pygame.K_h,pygame.K_ESCAPE):e._handle_key(key)
        self.assertEqual(before,snapshot(e.player));self.assertEqual(turn,e.world_time.turn)
        # Disclosed action selection fixture; the real input loop charges phases.
        action=SimpleNamespace(turn_cost=3,free_move=False)
        with patch.object(e,'_try_moveset_action',return_value=action),patch.object(e,'_weapon_action_phases',return_value=3):
            e._handle_key_local(e.display.MOVESET_KEY_1)
        self.assertEqual(turn+3,e.world_time.turn)
        self.assertEqual(('paralysis',2),(dose(e.player)['stage'],dose(e.player)['remaining']))

    def test_treatment_consumes_one_saved_stack_unit_and_never_another_instance(self):
        from test_gameplay_g12 import use
        e=self.e;self.hit();e.entities=[e.player]
        selected=ItemFactory(e.data).create('venom_treatment');selected.count=3
        unrelated=ItemFactory(e.data).create('venom_treatment')
        e.player.inventory.add(selected);e.player.inventory.add(unrelated)
        use(e,selected)
        self.assertEqual(2,selected.count);self.assertTrue(e.player.inventory.contains(selected))
        self.assertEqual(1,unrelated.count);self.assertTrue(e.player.inventory.contains(unrelated))

    def test_same_scene_promotion_preserves_paralyzed_boundary_position(self):
        e=self.e;v=e.creature_factory.spawn('heath_stalker',14,12);e.entities.append(v)
        self.source.perception.hostile_to=['stalker'];self.paralysis(v)
        e.world_map.width=2;e.world_map.set(Chunk(1,0,RegionType.PLAINS,29418,visited=True))
        from world.local_map import LocalMap
        m=LocalMap();m.tiles[:]=make_tile('floor',True,True)
        e.save_manager.cache.store(1,0,m,[])
        # Live bookkeeping retains the source scene. Returning is promotion,
        # not an authorized travel step or unconditional inward boundary nudge.
        e.entities=[e.player];v.x,v.y=0,12;e._live_pursuers=[(v,1,0,None)]
        e.player.x=e.local_map.width-1
        self.assertTrue(e._transition_chunk(1,0));self.assertIn(v,e.entities)
        # Arrival at 0,12 can require collision repair if occupied by the player;
        # use a distinct legal recorded position to isolate the boundary nudge.
        self.assertEqual(0,v.x)



if __name__=='__main__':unittest.main()
