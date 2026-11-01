"""AI-2 real-engine invariants. Geometry/effects staged; campaigns never opened."""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import test_gameplay_g20 as g20
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from engine.ai_profiles import OBSERVATION_DEFAULTS, effective_profile
from engine.creature_factory import CreatureFactory
from engine.save_manager import _serialize_entity, _deserialize_entities, _validate_entities
from engine.composite_diagnostics import inspect
from engine.spatial import melee_attack_legal
from world.local_map import make_tile


class ObservationTests(unittest.TestCase):
    setUpClass = classmethod(g20.AudibleEncounterTests.setUpClass.__func__)
    def setUp(self):
        g20.AudibleEncounterTests.setUp(self)
        e=self.e
        e.data=copy.copy(self.data);e.data.entities=copy.deepcopy(self.data.entities)
        e.data.terrain=copy.deepcopy(self.data.terrain)
        e.creature_factory=CreatureFactory(e.data)
        e.player.x,e.player.y=12,12
        e.local_map.tiles[:]=make_tile('floor',True,True)
        e.world_time.turn=0  # disclosed dark-seal midnight, normal radius 3
        e._update_fov()

    decision=g20.AudibleEncounterTests.decision

    def actor(self, x=18, y=12, **profile):
        raw=self.e.data.entities['hollow_revenant']
        raw.update(ai_type='composite',ai_profile={**OBSERVATION_DEFAULTS,**profile},
                   can_cross_chunks=False,can_use_stairs=False,speed=1)
        a=self.e.creature_factory.spawn('hollow_revenant',x,y)
        self.e.entities.append(a)
        return a

    def tick(self):
        e=self.e
        e.ai_system.process(e.entities,e.player,e.local_map,e.world_map,0,0,e.log,e.world_time,e.data,engine=e)

    def corridor(self, cells):
        self.e.local_map.tiles[:]=make_tile('wall',False,False)
        for xy in cells:self.e.local_map.set_tile(*xy,'floor',True,True)

    def test_normal_query_matches_publication_and_is_read_only(self):
        e=self.e;a=self.actor()
        from engine.item_factory import ItemFactory
        torch=ItemFactory(e.data).create('tallow_torch')
        e.player.inventory.add(torch)
        for mutation in ('night','torch','wall','door','player','secondary','weather','aura','overmap'):
            if mutation=='torch':e.item_system.use(torch,e)
            if mutation=='wall':e.local_map.set_tile(15,12,'wall',False,False)
            if mutation=='door':e.local_map.set_tile(15,12,'door_open',True,True)
            if mutation=='player':e.player.y+=1
            if mutation=='secondary':e.local_map.decor[(14,13)]='campfire_lit'
            if mutation=='weather':
                e.weather=copy.copy(e.weather)
                e.weather.get_mechanic=lambda k,d=None: 2 if k=='fov_cap' else d
            if mutation=='aura':
                w=e.creature_factory.spawn('bog_wraith',13,13);e.entities.append(w);e._update_wraith_aura()
            # Baseline publication owns refresh/memory; query cannot replay them.
            e._update_fov();expected=e.local_map.visible.copy()
            old=(e.world_time.turn,copy.deepcopy(e.local_map.tiles),
                 [_serialize_entity(x) for x in e.entities if x is not e.player],
                 [m.text for m in e.log.messages],copy.deepcopy(e._wraith_aura_state))
            for _ in range(2):
                np.testing.assert_array_equal(expected,e.normal_player_vision()['visible'])
                inspect(e)
            self.assertEqual(old[0],e.world_time.turn)
            np.testing.assert_array_equal(old[1],e.local_map.tiles)
            self.assertEqual(old[2],[_serialize_entity(x) for x in e.entities if x is not e.player])
            self.assertEqual(old[3],[m.text for m in e.log.messages]);self.assertEqual(old[4],e._wraith_aura_state)
        from engine.engine import GameMode
        e.mode=GameMode.OVERMAP;e._update_fov()
        self.assertTrue(e.local_map.visible.all())
        self.assertFalse(e.normal_player_vision()['visible'].all())

    def test_extra_step_zero_one_and_once_across_fast_opportunities(self):
        for allowance,speed,expected,decisions in ((0,1,1,1),(1,1,2,1),(1,2,3,2), (1,.5,0,0)):
            self.e.entities=[self.e.player]
            a=self.actor(unseen_extra_step=allowance)
            self.e.data.entities[a._creature_id]['speed']=speed
            self.tick()
            self.assertEqual(expected,18-a.x,(allowance,speed,a.ai.trace))
            self.assertEqual(decisions,a.ai.opportunities)
            if speed==.5:
                self.e.world_time.turn+=1;self.tick();self.assertEqual(16,a.x)
            self.assertLessEqual(sum(len(t['steps']) for t in a.ai.trace),3)

    def test_exposure_first_step_and_bonus_contact_never_attack(self):
        a=self.actor(x=16)
        self.decision(a)
        self.assertEqual((15,12),(a.x,a.y));self.assertEqual('watched',a.ai.trace[-1]['reason'])
        self.assertEqual(1,len(a.ai.trace[-1]['steps']))
        self.assertIn([15,12],a.ai.failed_entries)
        # Narrow player vision via real underground input allows unseen legal contact.
        self.e._compute_fov_base=lambda:1
        self.e.current_submap_id='fixture'
        a.ai.cancel(a,'fixture');a.x,a.y=15,13
        with patch('engine.combat.resolve_attack') as attack:
            self.decision(a)
            attack.assert_not_called()
        self.assertEqual(2,len(a.ai.trace[-1]['steps']))
        self.assertTrue(melee_attack_legal(self.e.local_map,a,self.e.player))
        self.e.world_time.turn+=1
        self.decision(a);self.assertEqual('melee',a.ai.trace[-1]['action'])

    def test_observation_without_prey_and_empty_hostility_hides(self):
        a=self.actor(x=14);a.perception.hostile_to=[]
        self.decision(a)
        self.assertIsNone(a.ai.target);self.assertIn(a.ai.phase,('conceal','covered'))
        self.assertEqual('seek_concealment',a.ai.trace[-1]['reason'])
        for _ in range(8):
            self.e.world_time.turn+=1;self.decision(a)
            if a.ai.phase=='covered':break
        self.assertEqual('covered',a.ai.phase);self.assertIsNone(a.ai.target)
        _validate_entities([_serialize_entity(a)],self.e.data,self.e.local_map)

    def test_matched_no_cover_fallbacks_real_melee_and_cower(self):
        self.corridor([(12,12),(13,12)])
        for fallback in ('defensive_melee','cower'):
            self.e.entities=[self.e.player];a=self.actor(x=13,no_cover=fallback)
            hp=self.e.player.fighter.hp
            for _ in range(3):self.decision(a)
            self.assertEqual((13,12),(a.x,a.y));self.assertEqual('cower',a.ai.phase)
            self.assertEqual(fallback=='defensive_melee',any(t['result'] and t['result']['committed'] for t in a.ai.trace))
            if fallback=='cower':self.assertEqual(hp,self.e.player.fighter.hp)

    def test_committed_cover_non_greedy_route_occupancy_and_finite_impairment(self):
        # Walk north first, crossing another exposed cell, then around the corner.
        self.corridor([(12,12),(13,12),(13,11),(13,10),(14,10),(15,10),(16,10)])
        a=self.actor(x=13,concealment_budget=4)
        self.decision(a);self.assertNotEqual((13,12),(a.x,a.y));goal=a.ai.cover_goal[:]
        # A full budget is not reinstalled on every replan/visibility transition.
        left=a.ai.conceal_left
        with patch.object(a.fighter,'can_move',return_value=False):
            for _ in range(5):self.e.world_time.turn+=1;self.decision(a)
        self.assertEqual(0,a.ai.conceal_left);self.assertEqual('cower',a.ai.phase)
        self.assertLess(left,4)
        for _ in range(5):self.decision(a)
        self.assertEqual(0,a.ai.conceal_left)
        self.e.local_map.set_tile(14,12,'floor',True,True)
        self.decision(a);self.assertGreater(a.ai.conceal_left,0)

    def test_no_stable_hide_expose_cycle_same_sight_cannot_rearm(self):
        a=self.actor(x=14,concealment_budget=8,pursuit_budget=20)
        for _ in range(100):
            self.e.world_time.turn+=1;self.decision(a)
        self.assertLessEqual(a.ai.conceal_left,8)
        self.assertTrue(a.ai.target is None or a.ai.phase in ('covered','cower'),a.ai.snapshot())
        pos=(a.x,a.y);opportunities=a.ai.opportunities
        for _ in range(10):self.e.world_time.turn+=1;self.decision(a)
        self.assertEqual(pos,(a.x,a.y));self.assertEqual(opportunities+10,a.ai.opportunities)

    def test_hidden_prey_evidence_not_refreshed_by_watch_and_expires(self):
        a=self.actor(x=14);self.decision(a)
        evidence=copy.deepcopy(a.ai.target)
        self.e.player.x=40
        # Keep exposure independent from prey sight using a real secondary source.
        self.e.world_time.turn=evidence['deadline']
        self.decision(a)
        self.assertEqual(evidence,a.ai.target)
        self.e.world_time.turn+=1;self.tick()
        self.assertIsNone(a.ai.target)
        self.assertIn(a.ai.last_cancellation,('evidence_expired','empty_trail'))

    def test_dead_ineligible_and_rival_targets_do_not_break_self_concealment(self):
        a=self.actor(x=14);self.decision(a);a.perception.hostile_to=[]
        self.decision(a);self.assertIsNone(a.ai.target)
        a.perception.hostile_to=['stalker']
        rival=self.e.creature_factory.spawn('heath_stalker',15,12);self.e.entities.append(rival)
        self.decision(a);self.assertEqual('creature',a.ai.target['role'])
        rival.fighter.hp=0;self.decision(a);self.assertIsNone(a.ai.target)

    def test_suppression_disruption_and_no_banked_bonus(self):
        a=self.actor();a._ability_suppressed_turns=5
        self.tick();self.assertEqual(17,a.x);self.assertIsNone(a.ai.bonus_phase)
        a._disrupted_turns=5;s=a.ai.snapshot();fraction=a.ai.move_accumulator
        self.e.world_time.turn+=1;self.tick()
        self.assertEqual(s['state']['opportunities'],a.ai.opportunities)
        self.assertEqual(s['state']['bonus_phase'],a.ai.bonus_phase)
        self.assertEqual(fraction,a.ai.move_accumulator)
        a._disrupted_turns=a._ability_suppressed_turns=0
        self.e.world_time.turn+=1;self.tick()
        self.assertLessEqual(17-a.x,2)

    def test_per_step_grass_actual_reaction_and_no_duplicate_fast_strike(self):
        from test_gameplay_g18 import equip
        equip(self.e,'crude_blade')
        # Diagonal contact outside a radius-one underground normal vision circle.
        self.e._compute_fov_base=lambda:1;self.e.current_submap_id='fixture'
        a=self.actor(x=15,y=13);self.e.data.entities[a._creature_id]['speed']=2
        self.e.local_map.set_tile(13,13,'tall_grass',True,True)
        self.e.data.terrain['tall_grass']={'secondary_effect':'concealment'}
        with patch.object(self.e,'_player_attack',wraps=self.e._player_attack) as attack:
            self.tick()
        self.assertEqual(1,attack.call_count)
        self.assertEqual(self.e.world_time.turn,a.ai.reaction_phase)
        self.assertEqual(2,sum(len(t['steps']) for t in a.ai.trace))
        self.assertEqual('movement_interrupted',a.ai.trace[0]['reason'])
        self.assertTrue(a.ai.per_step_reactions)

    def test_reaction_first_step_death_and_rejection_are_truthful(self):
        from test_gameplay_g18 import equip
        equip(self.e,'crude_blade')
        self.e._compute_fov_base=lambda:1;self.e.current_submap_id='fixture'
        for rejected in (False,True):
            self.e.entities=[self.e.player]
            a=self.actor(x=14,y=13)
            self.e.local_map.set_tile(13,13,'tall_grass',True,True)
            self.e.data.terrain['tall_grass']={'secondary_effect':'concealment'}
            def reaction(victim):
                if not rejected:victim.fighter.hp=0
                return not rejected
            with patch.object(self.e,'_player_attack',side_effect=reaction):self.tick()
            self.assertEqual(not rejected,a.ai.trace[-1]['steps'][0]['reaction'])
            self.assertEqual(1,len(a.ai.trace[-1]['steps']))
            self.assertEqual(None if rejected else 0,a.ai.reaction_phase)

    def test_save_profile_commitment_and_same_phase_spent_marker(self):
        a=self.actor();self.decision(a)
        self.assertEqual(0,a.ai.bonus_phase)
        row=_serialize_entity(a);_validate_entities([row],self.e.data,self.e.local_map)
        self.e.data.entities[a._creature_id]['ai_profile']['unseen_extra_step']=0
        restored=_deserialize_entities([row],self.e)[0]
        self.assertEqual(a.ai.snapshot(),restored.ai.snapshot())
        fresh=self.e.creature_factory.spawn(a._creature_id,20,12)
        self.assertEqual(0,fresh.ai.profile['unseen_extra_step']);self.assertEqual(1,restored.ai.profile['unseen_extra_step'])
        self.e.entities=[self.e.player,restored];self.decision(restored)
        self.assertLessEqual(len(restored.ai.trace[-1]['steps']),1)
        for field,value in [('bonus_phase',True),('failed_entries',[[0,0]]*9),('phase','withdraw'),('conceal_left',33)]:
            bad=copy.deepcopy(row);bad['composite']['state'][field]=value
            with self.assertRaises(ValueError):_validate_entities([bad],self.e.data,self.e.local_map)

    def test_f5_f9_and_cold_load_conceal_and_lost_sight(self):
        a=self.actor(x=14);self.decision(a)
        for stage in ('conceal','lost_sight'):
            if stage=='lost_sight':self.e.player.x=40;self.e.world_time.turn+=1;self.tick()
            self.e.save_manager.save(self.e)
            expected=_serialize_entity(a)['composite']
            self.assertTrue(self.e.save_manager.load(self.e),self.e.save_manager.last_error)
            a=next(x for x in self.e.entities if x is not self.e.player)
            self.assertEqual(expected,_serialize_entity(a)['composite'])
            code="from test_ai_2 import cold; import json; print('AI2_COLD='+json.dumps(cold("+repr(str(self.root))+")))"
            env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(GAME_ROOT),str(Path(__file__).parent)]))
            out=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True)
            self.assertEqual(0,out.returncode,out.stderr)
            actual=json.loads(out.stdout.split('AI2_COLD=')[1])
            self.assertEqual(expected,actual[0]['composite'])

    def test_departure_clears_local_commitment_and_preserves_spent_credit(self):
        from engine.ai_profiles import depart, local_only
        a=self.actor();self.decision(a);identity=a._individual_id;hp=a.fighter.hp;position=(a.x,a.y)
        a._can_cross_chunks=a._can_use_stairs=True
        depart(self.e)
        self.assertEqual(('idle',None,0.0), (a.ai.phase,a.ai.target,a.ai.move_accumulator))
        self.assertEqual((identity,hp,position),(a._individual_id,a.fighter.hp,(a.x,a.y)))
        self.assertEqual(0,a.ai.bonus_phase)
        from engine.ai_system import AISystem
        AISystem().process_single(a,self.e.local_map,12,12,self.e.entities,self.e.log,engine=self.e)
        self.assertEqual(position,(a.x,a.y));self.assertTrue(local_only(a))

    def test_actual_success_reject_departure_and_revisit_preserve_actor(self):
        from world.world_map import SubMap
        e=self.e;a=self.actor(x=14);self.decision(a);before=_serialize_entity(a)
        e._prepare_destination=lambda *args:None
        e._descend_to_submap('absent');self.assertEqual(before,_serialize_entity(a))
        del e._prepare_destination
        e.world_map.get(0,0).submaps.append(SubMap('ai2','cave','AI2',17,layout_id='starting_lab',surface_x=12,surface_y=12))
        e._descend_to_submap('ai2');self.assertEqual('ai2',e.current_submap_id)
        self.assertFalse(e._live_pursuers);self.assertFalse(e._pending_pursuer_arrivals)
        e._ascend_from_submap()
        rows=[x for x in e.entities if getattr(x,'_individual_id',None)==a._individual_id]
        self.assertEqual(1,len(rows));b=rows[0]
        self.assertEqual(('idle',None,None),(b.ai.phase,b.ai.target,b.ai.cover_goal))
        self.assertEqual((a.x,a.y,a.fighter.hp),(b.x,b.y,b.fighter.hp))

    def test_anonymous_sound_no_acceleration_and_occupied_cover_replans(self):
        from engine.sound import emit
        e=self.e;e.player.x=e.player.y=40;a=self.actor(x=18)
        emit(e,16,12,'combat');self.decision(a)
        self.assertEqual('anonymous_sound',a.ai.trace[-1]['reason'])
        self.assertIsNone(a.ai.target);self.assertIsNone(a.ai.bonus_phase)
        self.assertEqual(1,len(a.ai.trace[-1]['steps']))
        # Invalidate a retained reachable goal with a real occupant. No refill.
        e.player.x=e.player.y=12;a.x,a.y=13,12
        self.corridor([(12,12),(13,12),(13,11),(13,10),(14,10),(15,10),(16,10)])
        self.decision(a);left=a.ai.conceal_left;goal=a.ai.cover_goal
        if a.ai.phase=='conceal':
            blocker=e.creature_factory.spawn('heath_stalker',*goal);e.entities.append(blocker)
            self.decision(a);self.assertLessEqual(a.ai.conceal_left,left)
            self.assertNotEqual(goal,a.ai.cover_goal)

    def test_one_pursuit_opportunity_is_usable_and_hidden_occupied_point_approached(self):
        a=self.actor(pursuit_budget=1)
        self.decision(a);self.assertEqual(16,a.x);self.assertEqual(0,a.ai.pursuit_left)
        self.e.world_time.turn+=1;self.decision(a)
        self.assertIsNone(a.ai.target);self.assertEqual('pursuit_exhausted',a.ai.last_cancellation)
        # Real occlusion hides prey still on its remembered cell; approach remains legal.
        self.e.entities=[self.e.player];a=self.actor(x=14)
        self.decision(a)
        self.e.local_map.set_tile(13,12,'wall',False,False)
        for _ in range(4):
            self.e.world_time.turn+=1;self.decision(a)
        self.assertTrue(any(t['action']=='move' for t in a.ai.trace))

    def test_material_change_retains_a_still_useful_cover_destination(self):
        self.corridor([(12,12),(13,12),(13,11),(13,10),(14,10),(15,10),(16,10)])
        a=self.actor(x=13);self.decision(a)
        self.assertEqual('conceal',a.ai.phase);goal=a.ai.cover_goal[:]
        # A changed opening is material but does not expose or block the goal.
        self.e.local_map.set_tile(11,12,'floor',True,True)
        self.e.world_time.turn+=1;self.decision(a)
        self.assertEqual(goal,a.ai.cover_goal)


def cold(root):
    with patch('engine.save_manager.SAVE_DIR',Path(root)):
        e=make_engine(load_data())
        assert e.save_manager.load(e),e.save_manager.last_error
        return [_serialize_entity(a) for a in e.entities if a is not e.player]


if __name__=='__main__':unittest.main()
