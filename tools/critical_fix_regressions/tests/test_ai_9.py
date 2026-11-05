"""AI-9 real-engine component matrix and adversarial lifecycle/geometry checks.

Geometry, injuries and hostile definitions are controlled test setup; decisions,
perception, movement, effects, serialization and scheduling are production paths.
"""
import copy
import unittest
from unittest.mock import patch
import test_ai_2 as ai2
from engine.ai_profiles import RECIPES, effective_profile, validate_saved, depart
from engine.enemy_components import RECIPES as HOSTS
from engine.enemy_responses import CALL, ANSWER
from engine.enemy_maneuvers import LATERAL, REGROUP, supporters
from engine.save_manager import _serialize_entity, _deserialize_entities
from engine.composite_diagnostics import inspect
from world.local_map import make_tile


class CompositionTests(unittest.TestCase):
    setUpClass = classmethod(ai2.ObservationTests.setUpClass.__func__)
    setUp = ai2.ObservationTests.setUp
    decision = ai2.ObservationTests.decision
    tick = ai2.ObservationTests.tick

    def actor(self, x=16, y=12, recipe='strike_and_withdraw', moves=(), alarms=(), **settings):
        raw = copy.deepcopy(self.e.data.entities['hollow_revenant'])
        raw.update(id='fixture_ai9_'+str(len(self.e.entities)), ai_type='composite',
                   ai_profile=dict(RECIPES[recipe]),can_cross_chunks=False,can_use_stairs=False,speed=1)
        raw['perception'].update(faction='hollow',hostile_to=['player'],sight_radius=8,hearing_radius=6,sees_in_dark=True)
        if moves is not None:
            raw['enemy_maneuvers']=dict(version=1,modules=[dict(id=k,**settings.get(k,{})) for k in moves])
        if alarms is not None:
            raw['enemy_responses']=dict(version=2,modules=[dict(id=k,**settings.get(k,{})) for k in alarms])
        self.e.data.entities[raw['id']] = raw
        a = self.e.creature_factory.spawn(raw['id'],x,y); self.e.entities.append(a)
        return a

    def phase(self, *actors):
        self.e.world_time.turn += 1
        for a in actors: self.decision(a)

    def reset_actors(self):
        self.e.entities=[self.e.player];self.e.player.x,self.e.player.y=12,12
        self.e.local_map.tiles[:]=make_tile('floor',True,True)
        self.e.world_time.turn=0;self.e._update_fov()

    def roundtrip(self,a):
        row=_serialize_entity(a);validate_saved(row,self.e.local_map)
        restored=_deserialize_entities([row],self.e.creature_factory)[0]
        self.assertEqual(row,_serialize_entity(restored))
        return row

    def test_all_twenty_pairings_act_and_mixed_host_envelopes_roundtrip(self):
        for recipe in HOSTS:
            for component in (CALL,ANSWER,LATERAL,REGROUP):
                with self.subTest(recipe=recipe,component=component):
                    self.reset_actors()
                    if component==ANSWER:
                        caller=self.actor(x=16,alarms=(CALL,))
                        a=self.actor(x=21,recipe=recipe,alarms=(ANSWER,))
                        a.perception.sight_radius=1
                        if recipe=='territorial_guard':a.ai.profile.update(defended_radius=7,excursion_radius=8)
                        self.decision(caller);self.phase(caller)
                        self.assertIsNotNone(a.ai.responses['interest'])
                        old=(a.x,a.y);self.phase(a)
                        self.assertNotEqual(old,(a.x,a.y));self.assertIsNone(a.ai.target)
                        self.assertTrue(a.ai.trace[-1]['reason'].startswith('alarm_'))
                    else:
                        a=self.actor(recipe=recipe,moves=(component,) if component in (LATERAL,REGROUP) else (),alarms=(component,) if component==CALL else ())
                        if component==LATERAL:self.actor(x=14,moves=None,alarms=None)
                        if component==REGROUP:
                            self.actor(x=18,y=13,moves=None,alarms=None)
                            a.fighter.hp=a.fighter.max_hp//2
                        old=(a.x,a.y);self.decision(a)
                        reason={CALL:'alarm_prepare',LATERAL:'lateral_approach',REGROUP:'wounded_regroup'}[component]
                        self.assertEqual(reason,a.ai.trace[-1]['reason'])
                        self.assertLessEqual(max(abs(a.x-old[0]),abs(a.y-old[1])),1)
                        if component==CALL:
                            self.phase(a);self.assertEqual(1,a.ai.responses['sequence'])
                    self.roundtrip(a)
            self.reset_actors()
            a=self.actor(recipe=recipe,moves=(LATERAL,REGROUP),alarms=(CALL,ANSWER))
            self.actor(x=18,y=13,moves=None,alarms=None)
            self.decision(a);self.assertEqual('alarm_prepare',a.ai.trace[-1]['reason'])
            a.fighter.hp=a.fighter.max_hp//2;self.phase(a)
            self.assertEqual('wounded_regroup',a.ai.trace[-1]['reason'])
            self.assertIsNone(a.ai.responses['prepared']);self.assertEqual(0,a.ai.responses['sequence'])
            self.roundtrip(a)

    def test_configuration_rejects_bad_modules_bounds_hosts_and_protected_first_optin(self):
        from engine.creature_authoring import authorize_candidate
        for recipe in HOSTS:
            self.reset_actors();a=self.actor(recipe=recipe,moves=(LATERAL,REGROUP),alarms=(CALL,ANSWER))
            raw=self.e.data.entities[a._creature_id];effective_profile(raw)
            for envelope,identifier,field in [('enemy_responses',CALL,'strength'),('enemy_maneuvers',REGROUP,'wounded_percent')]:
                for bad in (True,-1,10000,float('nan'),float('inf'),'4'):
                    candidate=copy.deepcopy(raw);candidate[envelope]['modules']=[dict(id=identifier,**{field:bad})]
                    with self.assertRaises(ValueError):effective_profile(candidate)
                for modules in ([dict(id='exec')],[dict(id=identifier,code='run')],[dict(id=identifier),dict(id=identifier)]):
                    candidate=copy.deepcopy(raw);candidate[envelope]['modules']=modules
                    with self.assertRaises(ValueError):effective_profile(candidate)
            old=copy.deepcopy(raw);old.pop('enemy_maneuvers')
            path='roguelike/data/entities/creatures/'+raw['id']+'.json'
            self.assertTrue(any(p['code']=='ENEMY_MANEUVER_ID' for p in authorize_candidate(old,raw,path,path)))
            for flag,value in [('ranged_attack',{}),('npc',True),('id','player'),('id','stone_lurker')]:
                candidate=copy.deepcopy(raw);candidate[flag]=value
                with self.assertRaises(ValueError):effective_profile(candidate)
            candidate=copy.deepcopy(raw);candidate['ai_profile']=dict(RECIPES['protective_escort'])
            candidate['perception'].update(faction='player',hostile_to=['hollow'])
            with self.assertRaises(ValueError):effective_profile(candidate)
            if recipe not in ('strike_and_withdraw','territorial_guard'):
                candidate=copy.deepcopy(raw);candidate['enemy_responses']['version']=1
                with self.assertRaises(ValueError):effective_profile(candidate)

    def test_hidden_dead_moving_foreign_support_and_hidden_prey_release_without_refill(self):
        for mode in ('hidden','dead','moved','foreign','hostile','prey'):
            self.reset_actors();a=self.actor(moves=(LATERAL,));b=self.actor(x=14,moves=None,alarms=None)
            self.decision(a);self.assertIsNotNone(a.ai.maneuvers['current'])
            if mode=='hidden':a.perception.sight_radius=0
            if mode=='dead':b.fighter.hp=0
            if mode=='moved':b.y+=2
            if mode=='foreign':b.perception.faction='other'
            if mode=='hostile':b.perception.hostile_to.append('hollow')
            if mode=='prey':self.e.player.x=40
            self.phase(a)
            self.assertIsNone(a.ai.maneuvers['current']);self.assertTrue(a.ai.maneuvers['flank_spent'])

    def test_corridor_closure_occupancy_and_two_maneuverers_finish(self):
        a=self.actor(moves=(LATERAL,));b=self.actor(x=14,moves=None,alarms=None)
        self.e.local_map.tiles[:]=make_tile('wall',False,False)
        for x in range(10,20):self.e.local_map.set_tile(x,12,'floor',True,True)
        self.decision(a);self.assertIsNone(a.ai.maneuvers['current'])
        self.assertTrue(a.ai.maneuvers['flank_spent'])
        for mode in ('door','occupied','decor'):
            self.reset_actors();a=self.actor(moves=(LATERAL,));b=self.actor(x=14,moves=None,alarms=None)
            self.decision(a);goal=a.ai.maneuvers['current']['goal']
            if mode=='door':self.e.local_map.set_tile(*goal,'door_closed',False,False)
            if mode=='occupied':self.actor(*goal,moves=None,alarms=None)
            if mode=='decor':self.e.local_map.decor[tuple(goal)]='stone_sarcophagus'
            if mode=='decor' and not self.e._decor_blocks_movement(*goal):
                self.e.local_map.set_tile(*goal,'wall',False,False)
            self.phase(a);self.assertIsNone(a.ai.maneuvers['current'])
        for kind in (LATERAL,REGROUP):
            self.reset_actors();a=self.actor(moves=(kind,));b=self.actor(x=17,y=13,moves=(kind,))
            self.actor(x=14,moves=None,alarms=None)
            if kind==REGROUP:
                a.fighter.hp=a.fighter.max_hp//2;b.fighter.hp=b.fighter.max_hp//2
            for _ in range(20):self.phase(a,b)
            self.assertIsNone(a.ai.maneuvers['current']);self.assertIsNone(b.ai.maneuvers['current'])

    def test_regroup_arrival_on_final_travel_credit_retains_paid_holds_and_save(self):
        a=self.actor(moves=(REGROUP,),regroup_when_wounded=dict(opportunity_budget=2,hold_opportunities=2))
        self.actor(x=17,y=13,moves=None,alarms=None)
        a.fighter.hp=a.fighter.max_hp//2
        self.decision(a);self.phase(a)
        current=a.ai.maneuvers['current']
        self.assertIsNotNone(current)
        self.assertEqual([a.x,a.y],current['goal'])
        self.assertEqual((0,2),(current['left'],current['hold_left']))
        row=self.roundtrip(a)
        invalid=copy.deepcopy(row);invalid['x']-=1
        with self.assertRaises(ValueError):validate_saved(invalid,self.e.local_map)
        self.phase(a)
        self.assertEqual('regroup_hold',a.ai.trace[-1]['reason'])
        self.assertEqual(1,a.ai.maneuvers['current']['hold_left']);self.roundtrip(a)
        self.phase(a)
        self.assertEqual('regroup_hold',a.ai.trace[-1]['reason'])
        self.assertIsNone(a.ai.maneuvers['current'])
        self.assertTrue(a.ai.maneuvers['regroup_spent'])

    def test_v2_exposure_cannot_add_a_second_attachment_step_or_bypass_cover(self):
        a=self.actor(recipe='observation_averse',moves=(LATERAL,),alarms=(CALL,))
        self.actor(x=14,moves=None,alarms=None)
        self.decision(a);self.assertIsNotNone(a.ai.responses['prepared'])
        self.e.player.x=15;self.e._update_fov();old=(a.x,a.y)
        self.phase(a);self.assertIsNone(a.ai.responses['prepared'])
        self.assertNotEqual('alarm_emitted',a.ai.trace[-1]['reason'])
        self.assertLessEqual(max(abs(a.x-old[0]),abs(a.y-old[1])),1)
        self.reset_actors();a=self.actor(recipe='observation_averse',moves=(LATERAL,))
        self.actor(x=14,moves=None,alarms=None)
        for _ in range(6):
            old=(a.x,a.y);self.phase(a)
            if a.ai.trace[-1]['reason']=='lateral_approach':
                self.assertLessEqual(max(abs(a.x-old[0]),abs(a.y-old[1])),1)
                self.assertEqual(1,len(a.ai.trace[-1]['steps']))
                self.assertFalse(a.ai.trace[-1]['bonus_consumed'])
            if a.ai.covered_phase==self.e.world_time.turn:
                old=(a.x,a.y);self.decision(a);self.assertEqual(old,(a.x,a.y))

    def test_required_withdraw_hold_and_territory_return_precede_all_components(self):
        for recipe in ('venom_strike_and_withdraw','patient_venom_hunt','territorial_guard'):
            self.reset_actors();a=self.actor(recipe=recipe,moves=(LATERAL,REGROUP),alarms=(CALL,ANSWER))
            self.actor(x=18,y=13,moves=None,alarms=None)
            self.decision(a);a.fighter.hp=a.fighter.max_hp//2
            if recipe=='territorial_guard':
                a.ai.cancel(a,'forced_test_return');expected='return'
            else:
                a.ai.phase='withdraw';a.ai.withdraw_left=6;a.ai.hold_left=1
                a.x=13;expected='withdraw'
            self.phase(a)
            self.assertIsNone(a.ai.maneuvers['current']);self.assertIsNone(a.ai.responses['prepared'])
            self.assertNotIn(a.ai.trace[-1]['reason'],('lateral_approach','wounded_regroup','alarm_prepare'))

    def test_patient_real_dose_regroup_retires_hunt_and_keeps_victim_effect(self):
        from engine.venom import inspect as venom_state
        a=self.actor(x=13,recipe='patient_venom_hunt',moves=(REGROUP,))
        self.actor(x=18,y=13,moves=None,alarms=None)
        self.e.player.dodge_chance=0;self.e.player.fighter.effective_av=0
        for _ in range(8):
            self.phase(a)
            if a.ai.hunt:break
        self.assertIsNotNone(a.ai.hunt)
        a.fighter.hp=a.fighter.max_hp//2
        for _ in range(6):
            self.phase(a)
            if a.ai.maneuvers['current']:break
        self.assertIsNotNone(a.ai.maneuvers['current'])
        self.assertIsNone(a.ai.hunt);self.assertEqual('player',a.ai.suppressed)
        effect=copy.deepcopy(venom_state(self.e.player))
        self.roundtrip(a);self.assertEqual(effect,venom_state(self.e.player))
        for _ in range(10):self.phase(a)
        self.assertIsNone(a.ai.hunt);self.assertTrue(a.ai.maneuvers['regroup_spent'])

    def test_charged_expiry_zero_opportunities_inspection_paralysis_and_departure(self):
        a=self.actor(moves=(REGROUP,),**{REGROUP:dict(expiry_phases=4)})
        self.actor(x=20,y=13,moves=None,alarms=None);a.fighter.hp=a.fighter.max_hp//2
        self.decision(a);saved=self.roundtrip(a);before=(a.x,a.y);left=a.ai.maneuvers['current']['left']
        for _ in range(5):inspect(self.e)
        self.assertEqual(saved,_serialize_entity(a))
        self.e.data.entities[a._creature_id]['speed']=0.01
        for _ in range(6):self.e.world_time.turn+=1;self.tick()
        self.assertEqual(before,(a.x,a.y));self.assertIsNone(a.ai.maneuvers['current'])
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
        depart(self.e);self.roundtrip(a);self.assertTrue(a.ai.maneuvers['regroup_spent'])
        self.reset_actors();a=self.actor(moves=(REGROUP,));self.actor(x=18,y=13,moves=None,alarms=None)
        a.fighter.hp=a.fighter.max_hp//2;self.decision(a);before=(a.x,a.y)
        with patch('engine.venom.fully_paralysed',return_value=True):self.phase(a)
        self.assertEqual(before,(a.x,a.y));self.assertTrue(a.ai.maneuvers['regroup_spent'])

    def test_malformed_state_and_saved_absence_cannot_acquire_definition_attachments(self):
        a=self.actor(moves=(LATERAL,),alarms=(CALL,ANSWER));self.actor(x=14,moves=None,alarms=None)
        self.decision(a);self.phase(a);self.phase(a);row=self.roundtrip(a)
        self.assertIsNotNone(row['composite']['maneuvers']['state']['current'])
        for field,value in [('left',True),('goal',[-1,0]),('supporter','other:00000001'),('deadline',0),('kind','exec')]:
            bad=copy.deepcopy(row);bad['composite']['maneuvers']['state']['current'][field]=value
            with self.assertRaises(ValueError):validate_saved(bad,self.e.local_map)
        b=self.actor(x=24,moves=None,alarms=None);old=_serialize_entity(b)
        self.e.data.entities[b._creature_id]['enemy_maneuvers']=dict(version=1,modules=[dict(id=LATERAL)])
        self.e.data.entities[b._creature_id]['enemy_responses']=dict(version=2,modules=[dict(id=CALL)])
        restored=_deserialize_entities([old],self.e.creature_factory)[0]
        self.assertIsNone(restored.ai.maneuver_config);self.assertIsNone(restored.ai.response_config)
        self.assertEqual(old,_serialize_entity(restored))

    def test_regroup_credit_rearms_only_after_recovery_or_sustained_new_encounter(self):
        a=self.actor(moves=(REGROUP,));self.actor(x=18,y=13,moves=None,alarms=None)
        a.fighter.hp=a.fighter.max_hp//2;self.decision(a)
        a.ai.cancel(a,'interruption');self.assertTrue(a.ai.maneuvers['regroup_spent'])
        for _ in range(5):self.phase(a)
        self.assertTrue(a.ai.maneuvers['regroup_spent']);self.assertIsNone(a.ai.maneuvers['current'])
        a.fighter.hp=a.fighter.max_hp;self.phase(a)
        self.assertFalse(a.ai.maneuvers['regroup_spent'])
        a.fighter.hp=a.fighter.max_hp//2
        for _ in range(10):
            self.phase(a)
            if a.ai.maneuvers['regroup_spent']:break
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
        depart(self.e);self.e.player.x=40
        self.e.world_time.turn+=100;self.phase(a)
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
        for _ in range(23):self.phase(a)
        self.assertTrue(a.ai.maneuvers['regroup_spent'])
        self.phase(a);self.assertFalse(a.ai.maneuvers['regroup_spent'])

    def test_territorial_last_credit_and_patient_expiry_cannot_be_bypassed(self):
        a=self.actor(recipe='territorial_guard',moves=(LATERAL,REGROUP),alarms=(CALL,ANSWER))
        self.actor(x=18,y=13,moves=None,alarms=None);self.decision(a)
        a.ai.territory['pursuit_left']=1;a.fighter.hp=a.fighter.max_hp//2
        old=(a.x,a.y);self.phase(a)
        self.assertLessEqual(max(abs(a.x-old[0]),abs(a.y-old[1])),1)
        self.assertEqual('return',a.ai.territory['phase']);self.assertIsNone(a.ai.maneuvers['current'])
        self.assertEqual(0,a.ai.territory['pursuit_left']);self.roundtrip(a)
        self.reset_actors();a=self.actor(x=13,recipe='patient_venom_hunt',moves=(LATERAL,REGROUP),alarms=(CALL,ANSWER))
        self.e.player.dodge_chance=0;self.e.player.fighter.effective_av=0
        for _ in range(10):
            self.phase(a)
            if a.ai.hunt:break
        self.assertIsNotNone(a.ai.hunt)
        self.e.world_time.turn=a.ai.hunt['last_useful_phase']+1
        a.fighter.hp=a.fighter.max_hp//2;self.actor(x=18,y=13,moves=None,alarms=None)
        self.decision(a)
        self.assertIsNone(a.ai.hunt);self.assertEqual('player',a.ai.suppressed)
        self.assertIsNone(a.ai.maneuvers['current']);self.assertIsNone(a.ai.responses['prepared'])

    def test_exposing_alarm_investigation_is_one_safe_step_and_savable(self):
        caller=self.actor(x=16,alarms=(CALL,));a=self.actor(x=20,recipe='observation_averse',alarms=(ANSWER,))
        a.perception.sight_radius=1
        self.decision(caller);self.phase(caller)
        self.assertIsNotNone(a.ai.responses['interest'])
        # Real torch exposure near the next cell, without granting a target.
        self.e.player.x=15;self.e.player.y=14;self.e._update_fov()
        for _ in range(5):
            old=(a.x,a.y);self.phase(a)
            self.assertLessEqual(max(abs(a.x-old[0]),abs(a.y-old[1])),1)
            self.roundtrip(a)
            if a.ai.phase=='conceal':
                self.assertIsNone(a.ai.responses['interest']);break

    def test_actual_speed_two_scheduler_and_covered_phase_limit(self):
        a=self.actor(moves=(LATERAL,REGROUP),alarms=(CALL,ANSWER))
        b=self.actor(x=14,recipe='territorial_guard',moves=None,alarms=None)
        b.ai.profile['defended_radius']=1
        self.e.data.entities[a._creature_id]['speed']=2
        before=(a.x,a.y);self.tick()
        self.assertEqual(2,a.ai.opportunities);self.assertEqual(before,(a.x,a.y))
        self.assertEqual(['alarm_prepare','alarm_windup'],[t['reason'] for t in a.ai.trace])
        self.e.world_time.turn+=1;self.tick()
        self.assertEqual(4,a.ai.opportunities);self.assertEqual(1,a.ai.responses['sequence'])
        self.assertLessEqual(max(abs(a.x-before[0]),abs(a.y-before[1])),1)
        self.roundtrip(a)
        self.reset_actors();a=self.actor(x=15,recipe='observation_averse',moves=(LATERAL,REGROUP),alarms=(CALL,ANSWER))
        a.fighter.hp=a.fighter.max_hp//2;self.actor(x=18,y=13,moves=None,alarms=None)
        self.e.data.entities[a._creature_id]['speed']=2;old=(a.x,a.y);self.tick()
        self.assertEqual(2,a.ai.opportunities);self.assertEqual('covered_this_phase',a.ai.trace[-1]['reason'])
        self.assertEqual(1,max(abs(a.x-old[0]),abs(a.y-old[1])))
        self.assertFalse(a.ai.maneuvers['regroup_spent']);self.roundtrip(a)

    def test_real_venom_paralysis_denies_attached_host_without_refilling(self):
        from components.ai import _monster_attack_result
        from engine.venom import dose,age,fully_paralysed
        a=self.actor(moves=(REGROUP,));self.actor(x=20,y=13,moves=None,alarms=None)
        a.fighter.max_hp=40;a.fighter.hp=20;self.decision(a)
        venom=self.actor(x=a.x+1,y=a.y,recipe='venom_strike_and_withdraw',moves=None,alarms=None)
        venom.perception.faction='outlaw';venom.perception.hostile_to=['hollow']
        a.fighter.effective_av=0;a.dodge_chance=0
        for _ in range(6):
            _monster_attack_result(venom,a,self.e,defensive=True)
            if dose(a):break
        self.assertIsNotNone(dose(a));self.assertTrue(a.is_alive)
        for _ in range(dose(a)['parameters']['warning_phases']):
            self.e.world_time.turn+=1;age(self.e,a)
        self.assertTrue(fully_paralysed(a));before=(a.x,a.y);credit=a.ai.maneuvers['current']['left']
        self.e.data.entities[a._creature_id]['speed']=2;self.tick()
        self.assertEqual(before,(a.x,a.y));self.assertEqual(credit,a.ai.maneuvers['current']['left'])
        self.assertTrue(a.ai.maneuvers['regroup_spent']);self.roundtrip(a)

    def test_wounded_report_waits_for_later_phase_and_interrupts_investigation_but_not_hold(self):
        caller=self.actor(alarms=(CALL,))
        a=self.actor(x=21,moves=(REGROUP,),alarms=(ANSWER,));a.perception.sight_radius=3
        self.actor(x=23,y=13,moves=None,alarms=None);a.fighter.hp=a.fighter.max_hp//2
        self.decision(caller);self.phase(caller);old=(a.x,a.y)
        self.decision(a);self.assertEqual(old,(a.x,a.y));self.assertIsNone(a.ai.maneuvers['current'])
        self.phase(a);self.assertEqual('wounded_regroup',a.ai.trace[-1]['reason']);self.assertIsNone(a.ai.responses['interest'])
        self.roundtrip(a)
        self.reset_actors();a=self.actor(moves=(LATERAL,REGROUP),alarms=(CALL,ANSWER))
        self.actor(x=18,y=13,moves=None,alarms=None);self.decision(a)
        a.ai.phase='hold';a.ai.hold_left=2;a.fighter.hp=a.fighter.max_hp//2
        self.phase(a);self.assertEqual(1,a.ai.hold_left);self.assertIsNone(a.ai.maneuvers['current'])
        self.assertEqual('holding_distance',a.ai.trace[-1]['reason'])

    def test_lateral_changes_physical_route_around_fixed_support(self):
        paths=[]
        for enabled in (False,True):
            self.reset_actors();a=self.actor(x=18,moves=(LATERAL,) if enabled else ())
            b=self.actor(x=15,recipe='territorial_guard',moves=None,alarms=None);b.ai.profile['defended_radius']=1
            path=[]
            for _ in range(6):self.phase(a);path.append((a.x,a.y))
            paths.append(path)
            if enabled:self.assertTrue(any(t['reason']=='lateral_approach' for t in a.ai.trace))
        self.assertNotEqual(paths[0],paths[1])


if __name__=='__main__':unittest.main()
