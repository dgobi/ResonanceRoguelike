"""AI-7 controlled real-engine risks. Ordinary-input witnesses are separate."""
import copy
import unittest
from unittest.mock import patch
import test_ai_1 as ai1
from engine.ai_profiles import ESCORT_DEFAULTS, effective_profile, validate_saved, depart
from engine.save_manager import _serialize_entity, _deserialize_entities, _validate_escort_scene
from engine.escort_commands import offer, confirm, yield_to_player, registered
from engine.combat import CombatResult
from engine.composite_diagnostics import inspect
from engine.local_rivals import allocate


class EscortTests(unittest.TestCase):
    setUpClass=classmethod(ai1.StrikeWithdrawTests.setUpClass.__func__)
    setUp=ai1.StrikeWithdrawTests.setUp
    decision=ai1.StrikeWithdrawTests.decision
    tick=ai1.StrikeWithdrawTests.tick

    def actor(self,x=15,y=12,**profile):
        raw=copy.deepcopy(self.e.data.entities['hollow_revenant'])
        raw.update(id='fixture_escort',ai_type='composite',ai_profile={**ESCORT_DEFAULTS,**profile},
                   can_cross_chunks=False,can_use_stairs=False,speed=1)
        raw['perception'].update(faction='player',hostile_to=['hollow'])
        self.e.data.entities['fixture_escort']=raw
        a=self.e.creature_factory.spawn('fixture_escort',x,y)
        self.e.entities.append(a)
        return a

    def threat(self,x=17,y=12):
        a=self.e.creature_factory.spawn('hollow_revenant',x,y)
        self.e.entities.append(a)
        return a

    def prompt(self,a):
        c=self.e.interaction_cursor
        c.enter([(a.x,a.y)],self.e.player.x,self.e.player.y)
        self.assertTrue(offer(c,self.e))
        return c

    def test_strict_recipe_alignment_bounds_and_host(self):
        raw=copy.deepcopy(self.e.data.entities['hollow_revenant'])
        raw['ai_profile']=dict(ESCORT_DEFAULTS)
        raw.update(can_cross_chunks=False,can_use_stairs=False)
        for change in ({'follow_spacing':True},{'follow_spacing':3},{'protection_radius':6},
                       {'excursion_radius':9},{'pursuit_budget':0},{'initial_order':'attack'},
                       {'scene_scope':'world'},{'utility':1}):
            with self.assertRaises(ValueError): effective_profile(dict(ai_profile={**ESCORT_DEFAULTS,**change}))
        with self.assertRaises(ValueError): effective_profile(raw)
        raw['perception'].update(faction='player',hostile_to=['player'])
        with self.assertRaises(ValueError): effective_profile(raw)
        raw['perception']['hostile_to']=[]
        self.assertEqual(6,effective_profile(raw)['version'])
        raw['ranged_attack']={}
        with self.assertRaises(ValueError): effective_profile(raw)

    def test_follow_moves_only_on_opportunities_hold_binds_actual_post(self):
        a=self.actor(x=17);before=(a.x,a.y)
        a.ai.refresh_evidence(self.e,a,1)
        self.assertEqual(before,(a.x,a.y))
        for _ in range(6):self.decision(a)
        self.assertLessEqual(abs(a.x-self.e.player.x),2)
        self.e.player.x=a.x-1
        c=self.prompt(a);c._order_prompt['selected']=1
        before_turn=self.e.world_time.turn
        with patch.object(self.e,'_advance_turn',side_effect=lambda:setattr(self.e.world_time,'turn',self.e.world_time.turn+1)) as step:
            self.assertTrue(confirm(c,self.e));step.assert_called_once()
        self.assertEqual(before_turn+1,self.e.world_time.turn)
        post=[a.x,a.y];self.assertEqual(post,a.ai.escort['post'])
        self.e.player.x=35
        for _ in range(12):self.decision(a)
        self.assertEqual(post,[a.x,a.y]);self.assertEqual('hold',a.ai.escort['order'])
        self.assertNotEqual([17,12],post)

    def test_ward_sight_not_player_screen_or_noise_and_finite_loss(self):
        a=self.actor(x=18);self.decision(a);w=copy.deepcopy(a.ai.escort['ward'])
        self.e.player.x=35;self.e.debug_reveal=True
        with patch('components.protective_escort.sees_ward',return_value=False):
            for _ in range(3):self.decision(a)
            self.assertEqual(w,a.ai.escort['ward'])
            self.e.world_time.turn=w['deadline']+1
            self.decision(a)
            self.assertIsNone(a.ai.escort['ward']);self.assertEqual('follow',a.ai.escort['order'])
            self.assertNotEqual(35,a.x)
        self.e.player.x=a.x-3;self.decision(a)
        self.assertEqual(self.e.player.x,a.ai.escort['ward']['x'])

    def test_threat_retention_neutral_and_no_player_target(self):
        a=self.actor(initial_order='hold');b=self.threat(x=18)
        neutral=self.e.creature_factory.spawn('highland_bandit',14,11);self.e.entities.append(neutral)
        self.decision(a);self.assertEqual(b._individual_id,a.ai.target['id'])
        another=self.threat(x=17,y=14)
        retained=a.ai.target['id'];self.decision(a)
        self.assertEqual(retained,a.ai.target['id'])
        self.assertNotEqual('player',a.ai.target['role'])
        self.assertIsNone(getattr(neutral,'_individual_id',None))

    def test_finite_pursuit_returns_and_unchanged_unreachable_stays_retired(self):
        a=self.actor(initial_order='hold',pursuit_budget=2);b=self.threat(x=18)
        with patch.object(a.ai,'_move',return_value=False):
            for _ in range(20):self.decision(a)
            self.assertIsNone(a.ai.target)
            self.assertEqual(1,len(a.ai.escort['retired']))
            self.assertEqual((15,12),(a.x,a.y))
        b.x=19;self.decision(a)
        self.assertIsNotNone(a.ai.target)

    def test_every_route_step_respects_excursion_and_collision(self):
        a=self.actor(initial_order='hold');self.decision(a)
        a.x=21
        self.assertFalse(a.ai._move(self.e,a,(22,12)))
        b=self.threat(x=20)
        self.assertFalse(a.ai._move(self.e,a,(20,12)))
        m=self.e.local_map
        for xy in ((21,11),(20,12)):m.set_tile(*xy,'wall',False,False)
        self.assertFalse(a.ai._move(self.e,a,(20,11)))

    def test_real_resolver_targets_escort_and_nonplayer_kill_has_remains(self):
        a=self.actor(x=13,initial_order='hold');b=self.threat(x=14)
        self.e.player.x=35
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True,damage_dealt=2)) as r:
            self.decision(a);r.assert_called_once()
        # Real attacks and real death, no injected outcome in this part.
        a.fighter.effective_av=0;a.fighter.hp=1
        for _ in range(30):
            self.decision(b)
            if not a.is_alive:break
        self.assertFalse(a.is_alive)
        self.assertTrue(any(getattr(i,'source_creature',None)=='fixture_escort' for rows in self.e.local_map.floor_objects.values() for i in rows))

    def test_yield_swap_and_terrain_entry_cost_and_no_attack(self):
        a=self.actor(x=13);e=self.e
        # One-cell corridor forces reciprocal legal swap.
        for x in range(11,15):
            for y in (11,13):e.local_map.set_tile(x,y,'wall',False,False)
        e.local_map.set_tile(14,12,'wall',False,False)
        tid=str(e.local_map.tiles[13,12]['terrain']);e.data.terrain[tid]=dict(e.data.terrain[tid],move_cost=3)
        with patch.object(e,'_player_attack') as attack:
            self.assertTrue(yield_to_player(e,a));attack.assert_not_called()
        self.assertEqual((13,12),(e.player.x,e.player.y));self.assertEqual((12,12),(a.x,a.y))
        self.assertGreaterEqual(e._move_debt,2)

    def test_yield_fails_free_for_paralysis_decor_and_foreign_scene(self):
        a=self.actor(x=13);before=(self.e.player.x,a.x,self.e.world_time.turn,a.fighter.hp)
        with patch.object(a.fighter,'can_move',return_value=False):self.assertFalse(yield_to_player(self.e,a))
        self.assertEqual(before,(self.e.player.x,a.x,self.e.world_time.turn,a.fighter.hp))
        self.decision(a);a.ai.escort['owner']='1,1/foreign'
        self.assertFalse(yield_to_player(self.e,a))

    def test_stale_commands_cancel_without_time_or_other_actor_changes(self):
        a=self.actor(x=13);c=self.prompt(a);state=a.ai.snapshot();a.x=14
        with patch.object(self.e,'_advance_turn') as advance:
            self.assertFalse(confirm(c,self.e));advance.assert_not_called()
        self.assertEqual(state,a.ai.snapshot())
        a.x=13;c=self.prompt(a);self.e.entities.remove(a)
        self.assertFalse(confirm(c,self.e));self.assertEqual(state,a.ai.snapshot())

    def test_player_paralysis_blocks_confirmation_escort_paralysis_spends_no_budget(self):
        a=self.actor(x=13);c=self.prompt(a);state=a.ai.snapshot()
        with patch('engine.venom.fully_paralysed',return_value=True),patch.object(self.e,'_advance_turn') as advance:
            self.assertFalse(confirm(c,self.e));advance.assert_not_called()
            self.decision(a)
        self.assertEqual(state['state']['escort']['pursuit_left'],a.ai.escort['pursuit_left'])

    def test_save_round_trip_strict_mutants_and_scene_owner(self):
        a=self.actor(initial_order='hold');b=self.threat();self.decision(a)
        row=_serialize_entity(a);validate_saved(row,self.e.local_map)
        restored=_deserialize_entities([row],self.e)[0]
        self.assertEqual(row,_serialize_entity(restored))
        for change in ('order','counter','ward','target','owner','identity','alignment','unknown'):
            bad=copy.deepcopy(row);t=bad['composite']['state']['escort']
            if change=='order':t['order']='attack'
            if change=='counter':t['pursuit_left']=True
            if change=='ward':t['ward']['provenance']='noise'
            if change=='target':bad['composite']['state']['target']['role']='player'
            if change=='owner':t['owner']='1,1/foreign'
            if change=='identity':bad['composite']['state']['target']['id']='0,0/:99999999bad'
            if change=='alignment':bad['hostile_to']=['player']
            if change=='unknown':t['telepathy']=True
            with self.assertRaises(ValueError,msg=change):validate_saved(bad,self.e.local_map)
        with self.assertRaises(ValueError):_validate_escort_scene([row],'1_1',{'chunks':{'0,0':{}}})

    def test_departure_preserves_post_order_hp_and_identity_inspection_pure(self):
        a=self.actor(initial_order='hold');self.threat();self.decision(a)
        before=_serialize_entity(a);inspect(self.e);inspect(self.e)
        self.assertEqual(before,_serialize_entity(a))
        depart(self.e);after=_serialize_entity(a)
        for k in ('x','y','fighter','individual_id'):self.assertEqual(before[k],after[k])
        for k in ('order','post'):self.assertEqual(before['composite']['state']['escort'][k],a.ai.escort[k])
        self.assertIsNone(a.ai.target);self.assertIsNone(a.ai.escort['ward'])

    def test_two_escorts_never_overlap_or_swap_each_other(self):
        a=self.actor(x=16);b=self.actor(x=17)
        for _ in range(60):
            self.decision(a);self.decision(b)
            self.assertEqual(3,len({(a.x,a.y),(b.x,b.y),(self.e.player.x,self.e.player.y)}))
        poses=(a.x,a.y,b.x,b.y)
        for _ in range(20):self.decision(a);self.decision(b)
        self.assertEqual(poses,(a.x,a.y,b.x,b.y))

    def test_stale_confirmation_matrix_is_free_and_cannot_fall_through(self):
        for kind in ('dead','foreign','unseen','blocked_diagonal','player_moved','replaced_ai'):
            self.setUp();a=self.actor(x=13);c=self.prompt(a);before=a.ai.snapshot();turn=self.e.world_time.turn
            if kind=='dead':a.is_alive=False
            if kind=='foreign':a.ai.escort['owner']='1,1/foreign'
            if kind=='unseen':self.e.local_map.visible[a.x,a.y]=False
            if kind=='blocked_diagonal':
                a.y=13
                c._order_prompt['position']=(13,13)
                self.e.local_map.set_tile(13,12,'wall',False,False);self.e.local_map.set_tile(12,13,'wall',False,False)
            if kind=='player_moved':self.e.player.y=11
            if kind=='replaced_ai':a.ai=None
            with patch.object(self.e,'_advance_turn') as tick:
                self.assertFalse(confirm(c,self.e),kind);tick.assert_not_called()
            self.assertEqual(turn,self.e.world_time.turn)
            if kind not in ('replaced_ai','foreign'):self.assertEqual(before,a.ai.snapshot())

    def test_real_venom_scheduler_denies_yield_and_recovery_has_no_banked_step(self):
        from components.ai import _monster_attack_result
        from engine.venom import fully_paralysed,dose
        from engine.effect_lifecycle import finish_turn
        a=self.actor(x=13,initial_order='hold');self.decision(a)
        source=self.e.creature_factory.spawn('patient_amber_hunter',14,12);self.e.entities.append(source)
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True,damage_dealt=1)):
            result=_monster_attack_result(source,a,self.e,defensive=True)
        self.assertTrue(result.application.accepted)
        def age():
            self.e.world_time.turn+=1;self.e._effect_aged_ids=set();finish_turn(self.e,[a,source])
        for _ in range(3):age()
        self.assertTrue(fully_paralysed(a));before=(a.x,a.y);self.e.entities.remove(source)
        budget=a.ai.escort['rejoin_left']
        for _ in range(3):
            self.assertFalse(yield_to_player(self.e,a));self.tick()
            self.assertEqual(before,(a.x,a.y));self.assertLess(a.ai.move_accumulator,1)
            self.assertEqual(budget,a.ai.escort['rejoin_left']);age()
        self.assertEqual('recovery',dose(a)['stage'])
        opportunities=a.ai.opportunities;self.tick();self.assertEqual(opportunities+1,a.ai.opportunities)

    def test_escort_kill_uses_real_damage_and_no_player_only_hooks(self):
        a=self.actor(x=13,initial_order='hold');b=self.threat(x=14);b.fighter.hp=1
        from engine.hooks import HookEvent
        original=self.e.hooks.fire
        with patch.object(self.e.hooks,'fire',wraps=original) as fire:
            for _ in range(20):
                self.decision(a)
                if not b.is_alive:break
            self.assertFalse(b.is_alive)
            self.assertFalse(any(call.args[0]==HookEvent.ON_ENTITY_KILLED for call in fire.call_args_list))
        self.assertTrue(any(getattr(i,'source_creature',None)=='hollow_revenant' for rows in self.e.local_map.floor_objects.values() for i in rows))

    def test_failed_departure_and_effective_profile_are_unchanged(self):
        a=self.actor(initial_order='hold');self.threat();self.decision(a);before=a.ai.snapshot()
        self.e._try_ascend();self.assertEqual(before,a.ai.snapshot())
        row=_serialize_entity(a)
        self.e.data.entities['fixture_escort']['ai_profile'].update(initial_order='follow',pursuit_budget=1)
        b=_deserialize_entities([row],self.e)[0]
        self.assertEqual(before,b.ai.snapshot())

    def test_sound_never_identifies_or_locates_ward_and_blocked_retry_is_bounded(self):
        from engine.sound import emit
        a=self.actor(initial_order='hold');self.decision(a);a.x=18
        self.e.player.x=35
        with patch.object(a.ai,'_route',return_value=(None,None)):
            for _ in range(9):self.decision(a)
        self.assertEqual('blocked',a.ai.escort['phase'])
        ward=copy.deepcopy(a.ai.escort['ward'])
        with patch('components.protective_escort.sees_ward',return_value=False),patch.object(a.ai,'_route',wraps=a.ai._route) as route:
            emit(self.e,17,12,'combat')
            for _ in range(10):self.decision(a)
            route.assert_not_called()
            self.assertEqual(ward,a.ai.escort['ward']);self.assertIsNone(a.ai.target)

    def test_saved_protection_requires_a_ward_reference_and_fresh_identity_owns_its_scene(self):
        a=self.actor(x=14,initial_order='follow');self.threat(x=16);self.decision(a);self.decision(a)
        row=_serialize_entity(a);self.assertIsNotNone(row['composite']['state']['target'])
        bad=copy.deepcopy(row);bad['composite']['state']['escort']['ward']=None
        with self.assertRaises(ValueError):validate_saved(bad,self.e.local_map)
        self.e.entities=[self.e.player];a=self.actor();allocate(self.e,[a]);row=_serialize_entity(a)
        row['individual_id']='1,1/foreign:00000001'
        with self.assertRaises(ValueError):_validate_escort_scene([row],'0_0',{'chunks':{'0,0':{}}})


if __name__=='__main__':unittest.main()
