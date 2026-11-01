"""AI-4 commitment, lawful cues, shared positioning and explicit save contract.

Controlled damage fixtures isolate edge cases. The ordinary-play driver obtains
its own real sting and predatory attack, pickup, treatment and occlusion inputs.
"""
import copy
import unittest
from unittest.mock import patch
import test_ai_3 as ai3
from engine.ai_profiles import HUNT_DEFAULTS, VENOM_DEFAULTS, DEFAULTS, validate_saved
from engine.venom import dose, cure
from engine.save_manager import _serialize_entity, _deserialize_entities, _validate_entities
from engine.combat import CombatResult
from world.local_map import make_tile
from components.patient_hunt import observe


class PatientHuntTests(unittest.TestCase):
    setUpClass = classmethod(ai3.VenomTests.setUpClass.__func__)
    decision = ai3.VenomTests.decision
    actor = ai3.VenomTests.actor
    hit = ai3.VenomTests.hit
    phase = ai3.VenomTests.phase

    def setUp(self):
        ai3.VenomTests.setUp(self)
        self.e.entities.remove(self.source)
        self.source=self.actor(profile=HUNT_DEFAULTS)

    def sting(self):
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True,damage_dealt=1)):
            self.decision(self.source)
        self.assertIsNotNone(self.source.ai.hunt)
        return copy.deepcopy(self.source.ai.hunt)

    def tick(self):
        self.e.world_time.turn+=1
        self.decision(self.source)
        self.e._effect_aged_ids=set()
        from engine.effect_lifecycle import finish_turn
        finish_turn(self.e,[a for a in self.e.entities if a is not self.e.player])

    def test_exact_window_and_no_free_action_then_real_predatory_damage(self):
        e=self.e;a=self.source;h=self.sting()
        self.assertEqual((13,12),(a.x,a.y))
        self.assertEqual((484,485),(h['first_observation_phase'],h['last_useful_phase']))
        for _ in range(3):self.tick()
        self.assertEqual('paralysis',dose(e.player)['stage'])
        self.assertEqual('monitor',a.ai.phase)
        self.assertEqual(2,max(abs(a.x-e.player.x),abs(a.y-e.player.y)))
        self.tick();self.assertEqual('move',a.ai.trace[-1]['action'])
        before=e.player.fighter.hp
        # Real resolver, no injected result for the exploit attack.
        import random
        e.rng=random.Random(17)
        self.tick()
        r=a.ai.trace[-1]
        self.assertEqual('melee',r['action']);self.assertTrue(r['result']['committed'])
        self.assertLess(e.player.fighter.hp,before)
        self.assertEqual('recovery',dose(e.player)['stage'])
        self.tick();self.assertIsNone(a.ai.hunt)
        self.assertEqual('hunt_window_expired',a.ai.last_cancellation)
        self.assertEqual('player',a.ai.suppressed)

    def test_rejected_delivery_does_not_bind_or_withdraw(self):
        self.e.player._numbing_venom_trait='immune'
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True,damage_dealt=1)):
            self.decision(self.source)
        self.assertIsNone(self.source.ai.hunt)
        self.assertEqual('approach',self.source.ai.phase)

    def test_hidden_cure_no_notification_then_expected_absence_and_rearm(self):
        e=self.e;a=self.source;h=self.sting()
        self.tick()
        # Terrain occlusion is real creature sight; debug reveal is irrelevant.
        e.local_map.transparent[:]=False;e.local_map.visible[:]=True
        self.assertTrue(cure(e));self.assertEqual(h,a.ai.hunt)
        ev=observe(a.ai,e,a,e.player,1)
        self.assertIsNone(ev['cue'])
        e.world_time.turn=484
        # Querying hidden prey cannot read the victim's authoritative stage.
        with patch('engine.venom.movement_denial',side_effect=AssertionError('hidden poll')):
            self.assertIsNone(observe(a.ai,e,a,e.player,1)['cue'])
        e.local_map.transparent[:]=True
        self.decision(a)
        self.assertEqual('expected_impairment_absent',a.ai.last_cancellation)
        for _ in range(3):self.decision(a)
        self.assertIsNone(a.ai.target);self.assertEqual('player',a.ai.suppressed)
        e.player.x=60;self.decision(a);self.assertIsNone(a.ai.suppressed)
        e.player.x=12;self.decision(a);self.assertIsNotNone(a.ai.target)

    def test_wait_movement_block_warning_darkness_and_debug_reveal_are_not_cues(self):
        e=self.e;a=self.source;self.sting()
        self.assertEqual('no_paralysis',observe(a.ai,e,a,e.player,1)['cue'])
        for _ in range(3):self.decision(a)
        self.assertNotEqual('return',a.ai.phase)
        self.assertEqual(480,e.world_time.turn)
        self.assertEqual(3,dose(e.player)['remaining'])
        e.player.x=19;a.perception.sight_radius=12;a.perception.sees_in_dark=False
        self.assertIsNone(observe(a.ai,e,a,e.player,0.01)['cue'])

    def test_fresh_cure_between_close_and_attack_prevents_stale_predation(self):
        e=self.e;a=self.source;self.sting()
        for _ in range(4):self.tick()
        self.assertEqual('return',a.ai.phase)
        cure(e);hp=e.player.fighter.hp;self.tick()
        self.assertEqual(hp,e.player.fighter.hp)
        self.assertEqual('expected_impairment_absent',a.ai.last_cancellation)

    def test_sight_loss_between_confirmation_and_attack_uses_only_memory(self):
        e=self.e;a=self.source;self.sting()
        for _ in range(4):self.tick()
        e.local_map.transparent[:]=False;e.player.x=40
        hp=e.player.fighter.hp;self.tick()
        self.assertEqual(hp,e.player.fighter.hp)
        self.assertNotEqual('engage',a.ai.trace[-1]['reason'])
        if a.ai.target:self.assertEqual(12,a.ai.target['x'])

    def test_same_prey_other_application_can_qualify_without_uuid_attribution(self):
        e=self.e;a=self.source;h=self.sting()
        for _ in range(3):self.tick()
        dose(e.player)['application_id']='f'*32
        dose(e.player)['source']['individual']='0,0/:99999999'
        self.tick()
        self.assertEqual('return',a.ai.phase)
        self.assertEqual(h,a.ai.hunt)
        e.world_time.turn=486;self.decision(a)
        self.assertIsNone(a.ai.hunt)

    def test_nearer_intruder_does_not_replace_retained_ordinary_prey(self):
        e=self.e;a=self.source;e.player.x=40
        victim=e.creature_factory.spawn('highland_bandit',12,12);e.entities.append(victim)
        a.perception.hostile_to=[victim.perception.faction,'player']
        h=self.sting();identity=a.ai.target['id']
        self.tick();e.player.x=a.x;e.player.y=a.y+1
        self.decision(a)
        self.assertEqual(identity,a.ai.target['id']);self.assertEqual(h,a.ai.hunt)
        self.assertIsNotNone(dose(victim))

    def test_missing_dead_or_foreign_scene_prey_invalidates_without_curing(self):
        for mode in ('missing','dead','foreign'):
            with self.subTest(mode=mode):
                self.setUp();e=self.e;a=self.source;self.sting();original=copy.deepcopy(dose(e.player))
                if mode=='missing':e.entities.remove(e.player)
                elif mode=='dead':e.player.is_alive=False
                else:e.world_x+=1
                a.ai.resolve_target(e,a)
                self.assertIsNone(a.ai.hunt);self.assertEqual(original,dose(e.player))

    def test_blocking_decor_all_shared_recipes_and_changed_commit(self):
        e=self.e;a=self.source
        # Narrow corridor reproduces the reported inherited v1/v3 defect.
        e.local_map.tiles[:]=make_tile('wall',False,False)
        for x in range(10,18):e.local_map.tiles[x,12]=make_tile('floor',True,True)
        for profile in (DEFAULTS,VENOM_DEFAULTS,HUNT_DEFAULTS):
            a.ai.profile.update(profile)
            e.local_map.decor[(14,12)]='campfire_unlit'
            self.assertTrue(e._decor_blocks_movement(14,12))
            step,length=a.ai._route(e,a,lambda x,y:x>=15)
            self.assertIsNone(step)
            del e.local_map.decor[(14,12)]
            step,_=a.ai._route(e,a,lambda x,y:x>=15)
            self.assertEqual((14,12),step)
            e.local_map.decor[(14,12)]='campfire_unlit'
            self.assertFalse(a.ai._move(e,a,step))
            del e.local_map.decor[(14,12)]
            self.assertEqual((13,12),(a.x,a.y))

    def test_reacquisition_exhaustion_and_source_paralysis_preserve_budgets(self):
        e=self.e;a=self.source;h=self.sting();self.tick()
        e.local_map.transparent[:]=False
        left=a.ai.approach_left
        with patch('engine.venom.movement_denial',side_effect=lambda who:'numbing_venom_paralysis' if who is a else None):
            for _ in range(3):self.decision(a)
        self.assertEqual(left,a.ai.approach_left);self.assertEqual(0,a.ai.no_progress)
        with patch.object(a.ai,'_route',return_value=(None,None)):
            for _ in range(8):self.decision(a)
        self.assertIsNone(a.ai.hunt);self.assertEqual('reacquisition_exhausted',a.ai.last_cancellation)
        self.assertEqual(h['last_useful_phase'],485)

    def test_saved_confirmed_cue_cannot_authorize_resumed_cured_attack(self):
        e=self.e;a=self.source;self.sting()
        for _ in range(4):self.tick()
        row=_serialize_entity(a);restored=_deserialize_entities([row],e)[0]
        e.entities.remove(a);e.entities.append(restored)
        self.assertIsNone(restored.ai.hunt_evidence)
        cure(e);hp=e.player.fighter.hp;self.decision(restored)
        self.assertEqual(hp,e.player.fighter.hp)
        self.assertEqual('expected_impairment_absent',restored.ai.last_cancellation)

    def test_slow_fast_evaluations_and_disrupted_resume_cannot_extend_deadline(self):
        e=self.e;a=self.source;h=self.sting()
        # Scheduler refresh runs even when no decision is granted/disrupted.
        a._disrupted_turns=20
        e.world_time.turn=h['last_useful_phase']+1
        a.ai.refresh_evidence(e,a,1)
        self.assertIsNone(a.ai.hunt)
        a._disrupted_turns=0
        for _ in range(5):self.decision(a)
        self.assertIsNone(a.ai.hunt)

    def test_insect_targetable_body_real_damage_death_and_registered_remains(self):
        e=self.e
        a=e.creature_factory.spawn('amber_sting_beetle',13,13);e.entities.append(a)
        from engine.combat import get_body_def,select_location
        import random
        body=get_body_def(a.fighter,e.data.bodies)
        self.assertEqual(9,len(body['locations']))
        picked={select_location(body,random.Random(i))['id'] for i in range(300)}
        self.assertEqual({x['id'] for x in body['locations']},picked)
        a.fighter.take_damage(1000);e._on_entity_death(a)
        remains=e.local_map.floor_objects[(13,13)]
        self.assertTrue(any(getattr(x,'source_creature',None)=='amber_sting_beetle' for x in remains))
        corpse=next(x for x in remains if getattr(x,'source_creature',None)=='amber_sting_beetle')
        from engine.save_components import serialize_item
        self.assertEqual('amber_sting_beetle',serialize_item(corpse)['source_creature'])

    def test_immobility_and_disruption_do_not_replenish_or_extend_window(self):
        e=self.e;a=self.source;h=self.sting();left=a.ai.withdraw_left
        with patch('engine.venom.movement_denial',side_effect=lambda who:'numbing_venom_paralysis' if who is a else None):
            for _ in range(3):self.decision(a)
        self.assertEqual(left,a.ai.withdraw_left);self.assertEqual(h,a.ai.hunt)
        a._ability_suppressed_turns=10
        for _ in range(5):self.tick()
        self.assertEqual(h,a.ai.hunt)
        e.world_time.turn=486
        a.ai.refresh_evidence(e,a,1)
        self.assertIsNone(a.ai.hunt)

    def test_blocked_retreat_exhausts_without_rearm_on_geometry_or_recovery(self):
        a=self.source;self.sting()
        with patch.object(a.ai,'_route',return_value=(None,None)):
            for _ in range(6):self.decision(a)
        self.assertIsNone(a.ai.hunt)
        self.assertEqual('withdrawal_exhausted',a.ai.last_cancellation)
        for _ in range(3):self.decision(a)
        self.assertIsNone(a.ai.hunt);self.assertIsNone(a.ai.target)

    def test_timed_comparison_ignores_symptoms_and_patient_window(self):
        e=self.e;a=self.source;a.ai.profile.update(return_policy='after_hold',hold_opportunities=9)
        self.sting();cure(e)
        for _ in range(8):self.tick()
        self.assertIsNotNone(a.ai.hunt);self.assertEqual('hold',a.ai.phase)
        self.assertIsNone(a.ai.hunt_evidence)
        for _ in range(4):self.tick()
        self.assertEqual('timed_return_complete',a.ai.last_cancellation)

    def test_timed_hold_exhaustion_cannot_recreate_a_targetless_return(self):
        e=self.e;a=self.source;a.ai.profile.update(return_policy='after_hold',hold_opportunities=9)
        self.sting();self.tick();self.assertEqual('hold',a.ai.phase)
        e.player.x=a.x-1;e.player.y=a.y;a.ai.withdraw_left=1
        with patch.object(a.ai,'_route',return_value=(None,None)):
            self.decision(a)
        self.assertEqual('idle',a.ai.phase);self.assertIsNone(a.ai.hunt)
        _validate_entities([_serialize_entity(a)],e.data,e.local_map)

    def test_save_reconstruction_and_strict_hunt_validation(self):
        e=self.e;a=self.source;self.sting();self.tick()
        row=_serialize_entity(a);_validate_entities([row],e.data,e.local_map)
        restored=_deserialize_entities([row],e)[0]
        self.assertEqual(a.ai.snapshot(),restored.ai.snapshot())
        self.assertIsNone(restored.ai.hunt_evidence)
        for field,value in [('version',True),('first_observation_phase',3),('last_useful_phase',99),
                            ('source_id','0,0/:99999999'),('application_id','x'),('owner','9,9/')]:
            bad=copy.deepcopy(row);bad['composite']['state']['hunt'][field]=value
            with self.assertRaises(ValueError):validate_saved(bad,e.local_map)
        bad=copy.deepcopy(row);bad['composite']['state']['target']['dose']='hidden'
        with self.assertRaises(ValueError):validate_saved(bad,e.local_map)

    def test_inspection_is_pure_and_scene_departure_cancels_only_hunt(self):
        e=self.e;a=self.source;self.sting();self.tick()
        from engine.composite_diagnostics import inspect
        before=copy.deepcopy(_serialize_entity(a));victim=copy.deepcopy(dose(e.player))
        for _ in range(4):inspect(e)
        self.assertEqual(before,_serialize_entity(a));self.assertEqual(victim,dose(e.player))
        from engine.ai_profiles import depart
        depart(e);self.assertIsNone(a.ai.hunt);self.assertEqual(victim,dose(e.player))


if __name__=='__main__':unittest.main()
