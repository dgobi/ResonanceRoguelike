"""AI-8 adversarial real-engine fixtures; staged geometry is explicit."""
import copy
import unittest
from unittest.mock import patch
import test_ai_1 as ai1
from engine.ai_profiles import DEFAULTS, TERRITORY_DEFAULTS, effective_profile, validate_saved, depart
from engine.enemy_responses import CALL, ANSWER, REGISTRY, configuration, emit, accepts
from engine.save_manager import _serialize_entity, _deserialize_entities, _validate_escort_scene
from engine.sound import emit as noise
from engine.local_rivals import allocate
from engine.combat import CombatResult


class ResponseTests(unittest.TestCase):
    setUpClass=classmethod(ai1.StrikeWithdrawTests.setUpClass.__func__)
    setUp=ai1.StrikeWithdrawTests.setUp
    decision=ai1.StrikeWithdrawTests.decision
    tick=ai1.StrikeWithdrawTests.tick

    def actor(self,x=16,y=12,recipe='strike_and_withdraw',modules=(CALL,),**settings):
        raw=copy.deepcopy(self.e.data.entities['hollow_revenant'])
        raw.update(id='fixture_response_'+str(len(self.e.entities)),ai_type='composite',
                   ai_profile=dict(TERRITORY_DEFAULTS if recipe=='territorial_guard' else DEFAULTS),
                   can_cross_chunks=False,can_use_stairs=False,speed=1,
                   enemy_responses=dict(version=1,modules=[dict(id=k,**settings.get(k,{})) for k in modules]))
        raw['perception'].update(faction='hollow',hostile_to=['player'],sight_radius=7,hearing_radius=6,sees_in_dark=True)
        self.e.data.entities[raw['id']]=raw
        a=self.e.creature_factory.spawn(raw['id'],x,y);self.e.entities.append(a)
        return a

    def phase(self,*actors):
        self.e.world_time.turn+=1
        for a in actors:self.decision(a)

    def pair(self,recipe='strike_and_withdraw',both=False):
        a=self.actor(recipe=recipe,modules=(CALL,ANSWER) if both else (CALL,))
        b=self.actor(x=24,modules=(CALL,ANSWER) if both else (ANSWER,))
        return a,b

    def test_paid_windup_speed_two_later_response_and_no_target_broadcast(self):
        a,b=self.pair();start=(a.x,a.y,b.x,b.y)
        self.decision(a);self.assertEqual('alarm_prepare',a.ai.trace[-1]['action'])
        self.decision(a);self.assertIsNone(b.ai.responses['interest'])
        self.assertEqual(start,(a.x,a.y,b.x,b.y))
        self.phase(a);i=copy.deepcopy(b.ai.responses['interest'])
        self.assertEqual([16,12],[i['incident']['x'],i['incident']['y']])
        self.assertEqual({'id','source','owner','faction','x','y','emitted'},set(i['incident']))
        self.assertIsNone(b.ai.target);self.decision(b);self.assertEqual(24,b.x)
        self.phase(b);self.assertLess(b.x,24);self.assertIsNone(b.ai.target)
        self.assertIn(i['incident']['id'],b.ai.responses['recent'])

    def test_sight_break_disruption_paralysis_and_dead_cancels(self):
        for mode in ('sight','disrupted','paralysed','dead','suppressed'):
            with self.subTest(mode=mode):
                self.e.entities=[self.e.player];a,b=self.pair();self.decision(a)
                if mode=='sight':self.e.player.x=40
                if mode=='disrupted':a._disrupted_turns=2
                if mode=='paralysed':
                    with patch('engine.venom.fully_paralysed',return_value=True):self.phase(a)
                else:
                    if mode=='dead':a.fighter.hp=0
                    if mode=='suppressed':a._ability_suppressed_turns=2
                    self.phase(a)
                self.assertIsNone(a.ai.responses['prepared']);self.assertIsNone(b.ai.responses['interest'])
                self.e.player.x=12

    def test_both_modules_do_not_echo_on_receipt_arrival_or_other_caller(self):
        a,b=self.pair(both=True);self.decision(a);self.phase(a)
        self.e.player.x=40
        for _ in range(18):self.phase(a,b)
        self.assertEqual(1,a.ai.responses['sequence']);self.assertEqual(0,b.ai.responses['sequence'])
        self.assertIsNone(b.ai.responses['interest']);self.assertIsNone(b.ai.target)
        self.assertLessEqual(len(b.ai.responses['recent']),16)

    def test_same_faction_modules_hearing_and_doors_are_required(self):
        for case in ('valid','foreign','no_module','deaf','wall','attenuated'):
            with self.subTest(case=case):
                self.e.entities=[self.e.player];a,b=self.pair()
                if case=='foreign':b.perception.faction='outlaw'
                if case=='no_module':b.ai.response_config=None;b.ai.responses=None
                if case=='deaf':b.perception.hearing_radius=0
                if case in ('wall','attenuated'):
                    # Full-height barrier excludes a competing open route.
                    for y in range(self.e.local_map.height):self.e.local_map.set_tile(20,y,'wall',False,False)
                    if case=='attenuated':
                        self.e.local_map.set_tile(20,12,'door_closed',False,False);b.perception.hearing_radius=1
                self.decision(a);self.phase(a)
                self.assertEqual(case=='valid',b.ai.responses is not None and b.ai.responses['interest'] is not None)
                if case in ('wall','attenuated'):
                    for y in range(self.e.local_map.height):self.e.local_map.set_tile(20,y,'flagstone',True,True)

    def test_reuse_territorial_caller_and_territorial_recipient_domain_and_return(self):
        a,b=self.pair(recipe='territorial_guard');self.decision(a);self.phase(a)
        self.assertIsNotNone(b.ai.responses['interest'])
        self.e.entities=[self.e.player]
        a=self.actor(x=16);b=self.actor(x=19,recipe='territorial_guard',modules=(ANSWER,))
        b.perception.sight_radius=1
        self.decision(a);self.phase(a);self.assertIsNotNone(b.ai.responses['interest'])
        self.e.player.x=40;self.phase(b);self.assertLess(b.x,19)
        for _ in range(16):self.phase(b)
        self.assertEqual((19,12),(b.x,b.y));self.assertIsNone(b.ai.responses['interest'])
        a.ai.responses['called']=False;a.ai.responses['cooldown_until']=0
        a.x=10;self.e.player.x=12;self.decision(a);self.phase(a)
        self.assertIsNone(b.ai.responses['interest'])
        b.ai.cancel(b,'fixture_return');self.assertIn(b.ai.territory['phase'],('return','blocked'))
        event=dict(id=a._individual_id+'@99',source=a._individual_id,owner=a.ai.responses['owner'],faction='hollow',x=19,y=12,emitted=self.e.world_time.turn)
        self.assertEqual('territorial_commitment',accepts(b.ai,b,event,self.e))

    def test_own_sight_restores_same_recipe_and_no_hidden_attack(self):
        a,b=self.pair();self.decision(a);self.phase(a)
        self.e.player.x=40
        for _ in range(2):self.phase(b)
        self.assertIsNone(b.ai.target)
        self.e.player.x=b.x-1
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=False)) as attack:
            self.phase(b);attack.assert_called_once()
        self.assertEqual('strike_and_withdraw',b.ai.profile['recipe']);self.assertIsNone(b.ai.responses['interest'])

    def test_finite_route_failure_expiry_and_anonymous_priority(self):
        a,b=self.pair();self.decision(a);self.phase(a);interest=copy.deepcopy(b.ai.responses['interest'])
        noise(self.e,25,12,'combat');self.assertIsNone(b.ai.sound_interest)
        self.e.player.x=40
        with patch.object(b.ai,'_route',return_value=(None,None)):
            self.phase(b);self.phase(b)
        self.assertIsNone(b.ai.responses['interest'])
        event=interest['incident'];event['emitted']=self.e.world_time.turn
        self.assertEqual('duplicate',accepts(b.ai,b,event,self.e))
        b.ai.responses['interest']=interest
        self.e.world_time.turn=interest['deadline']+1;b.ai.refresh_evidence(self.e,b,1)
        self.assertIsNone(b.ai.responses['interest'])

    def test_cooldown_flicker_and_evidence_refresh_never_spends_or_calls(self):
        a,b=self.pair();self.decision(a);prepared=a.ai.responses['prepared']
        for _ in range(20):a.ai.refresh_evidence(self.e,a,1)
        self.assertEqual(prepared,a.ai.responses['prepared']);self.assertIsNone(b.ai.responses['interest'])
        self.phase(a);self.e.player.x=40;self.e.world_time.turn+=1;a.ai.refresh_evidence(self.e,a,1);self.e.player.x=12
        for _ in range(30):
            self.e.world_time.turn+=1;a.ai.refresh_evidence(self.e,a,1)
        self.assertEqual(1,a.ai.responses['sequence'])
        self.e.player.x=40
        for _ in range(13):
            self.e.world_time.turn+=1;a.ai.refresh_evidence(self.e,a,1)
        self.assertFalse(a.ai.responses['called'])
        a.ai.cancel(a,'fixture_new_encounter');self.e.player.x=12;self.phase(a);self.phase(a)
        self.assertEqual(2,a.ai.responses['sequence'])

    def test_exact_save_restore_effective_settings_and_absent_historical_attachment(self):
        a,b=self.pair();self.decision(a)
        for stage in ('prepared','called'):
            if stage=='called':self.phase(a)
            for actor in (a,b):
                row=_serialize_entity(actor);validate_saved(row,self.e.local_map)
                definition=self.e.data.entities[actor._creature_id];definition['enemy_responses']['modules']=[]
                restored=_deserialize_entities([row],self.e)[0]
                self.assertEqual(row,_serialize_entity(restored))
        row=_serialize_entity(a);row['composite'].pop('responses')
        self.assertNotIn('responses',_serialize_entity(_deserialize_entities([row],self.e)[0])['composite'])
        depart(self.e);self.assertIsNone(b.ai.responses['interest']);self.assertIsNone(a.ai.responses['prepared'])

    def test_strict_attachment_shapes_types_eligibility_and_unknown_keys(self):
        a=self.actor();raw=copy.deepcopy(self.e.data.entities[a._creature_id])
        for value in (None,{},dict(version=True,modules=[]),dict(version=1,modules=[dict(id=CALL),dict(id=CALL)]),
                      dict(version=1,modules=[dict(id='relay')]),dict(version=1,modules=[dict(id=CALL,strength=True)]),
                      dict(version=1,modules=[dict(id=CALL,player_x=12)])):
            with self.assertRaises(ValueError):effective_profile(dict(raw,enemy_responses=value))
        for faction,hostile in [('player',['player']),('hollow',[]),('Hollow',['player']),('hollow',None)]:
            bad=copy.deepcopy(raw);bad['perception'].update(faction=faction,hostile_to=hostile)
            with self.assertRaises(ValueError):effective_profile(bad)

    def test_malformed_saved_receipts_foreign_scene_identity_and_inconsistent_state(self):
        a,b=self.pair();self.decision(a);self.phase(a);row=_serialize_entity(b)
        for mode in ('foreign','source','target','bool','deadline','unknown','ledger','owner','faction','budget'):
            bad=copy.deepcopy(row);s=bad['composite']['responses']['state'];i=s['interest']
            if mode=='foreign':i['incident']['owner']='1,1/foreign'
            if mode=='source':i['incident']['source']=row['individual_id']
            if mode=='target':bad['composite']['state']['target']=copy.deepcopy(a.ai.target)
            if mode=='bool':i['left']=True
            if mode=='deadline':i['deadline']+=1
            if mode=='unknown':i['incident']['player_x']=12
            if mode=='ledger':s['recent']*=2
            if mode=='owner':s['owner']='1,1/foreign'
            if mode=='faction':i['incident']['faction']='player'
            if mode=='budget':i['left']=0
            with self.assertRaises(ValueError,msg=mode):validate_saved(bad,self.e.local_map)
        with self.assertRaises(ValueError):_validate_escort_scene([row],'foreign',{'chunks':{}})

    def test_real_scheduler_speed_two_and_both_actor_orders_preserve_phase_barrier(self):
        for reverse in (False,True):
            self.e.entities=[self.e.player];a,b=self.pair()
            for actor in (a,b):self.e.data.entities[actor._creature_id]['speed']=2
            if reverse:self.e.entities=[self.e.player,b,a]
            origin=(a.x,a.y,b.x,b.y)
            with patch('engine.combat.resolve_attack') as attacks:
                self.tick();self.assertEqual(origin,(a.x,a.y,b.x,b.y));attacks.assert_not_called()
                self.assertEqual(2,a.ai.opportunities);self.assertIsNone(b.ai.responses['interest'])
                self.e.world_time.turn+=1;self.tick();self.assertEqual((origin[2],origin[3]),(b.x,b.y))
                self.assertIsNotNone(b.ai.responses['interest'])
                self.assertEqual(4,b.ai.opportunities)
                self.e.world_time.turn+=1;self.tick();self.assertNotEqual((origin[2],origin[3]),(b.x,b.y))

    def test_real_venom_paralysis_cancels_preparation_and_no_recovery_burst(self):
        from components.ai import _monster_attack_result
        from engine.venom import fully_paralysed
        from engine.effect_lifecycle import finish_turn
        a,b=self.pair();source=self.e.creature_factory.spawn('patient_amber_hunter',17,12);self.e.entities.append(source)
        source.perception.hostile_to=['hollow']
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True,damage_dealt=1)):
            result=_monster_attack_result(source,a,self.e,defensive=True)
        self.assertTrue(result.application.accepted)
        for _ in range(3):
            self.e.world_time.turn+=1;self.e._effect_aged_ids=set();finish_turn(self.e,[a,source])
        self.assertTrue(fully_paralysed(a));self.e.entities.remove(source)
        # A preparation accepted before incapacitation cannot survive the next
        # charged evidence pass. Setup keeps ordinary paralysis/scheduler rules.
        a.ai._remember(self.e,self.e.player);a.ai.phase='approach';a.ai.approach_left=32
        a.ai.responses.update(owner='0,0/',prepared=self.e.world_time.turn-1)
        allocate(self.e,[a]);origin=(a.x,a.y)
        for _ in range(3):
            self.tick();self.assertIsNone(a.ai.responses['prepared']);self.assertEqual(origin,(a.x,a.y))
            self.e.world_time.turn+=1;self.e._effect_aged_ids=set();finish_turn(self.e,[a])
        self.assertFalse(fully_paralysed(a));before=a.ai.opportunities;self.tick()
        self.assertEqual(before+1,a.ai.opportunities);self.assertIsNone(b.ai.responses['interest'])

    def test_heard_signal_survives_caller_death_but_foreign_recipient_cancels(self):
        a,b=self.pair();self.decision(a);self.phase(a);deadline=b.ai.responses['interest']['deadline']
        a.is_alive=False;self.e.entities.remove(a);self.e.player.x=40
        self.phase(b);self.assertIsNotNone(b.ai.responses['interest']);self.assertEqual(deadline,b.ai.responses['interest']['deadline'])
        b.ai.responses['owner']='1,1/foreign';b.ai.refresh_evidence(self.e,b,1)
        self.assertIsNone(b.ai.responses['interest'])

    def test_decoration_occupancy_sealed_diagonal_and_terrain_recheck_response_step(self):
        a,b=self.pair();self.decision(a);self.phase(a);self.e.player.x=40
        with patch.object(self.e,'_decor_blocks_movement',return_value=True):self.phase(b)
        self.assertEqual((24,12),(b.x,b.y))
        blocker=self.e.creature_factory.spawn('hollow_revenant',23,12);self.e.entities.append(blocker)
        self.assertFalse(b.ai._move(self.e,b,(23,12)))
        for point in ((23,12),(24,11)):self.e.local_map.set_tile(*point,'wall',False,False)
        self.assertFalse(b.ai._move(self.e,b,(23,11)))
        self.assertFalse(b.ai._move(self.e,b,(-1,-1)))

    def test_saved_preparation_requires_player_target_and_unknown_executable_state_rejects(self):
        a,b=self.pair();self.decision(a);row=_serialize_entity(a)
        for mode in ('no_target','called','unknown','missing','duplicate'):
            bad=copy.deepcopy(row);s=bad['composite']['responses']['state']
            if mode=='no_target':bad['composite']['state']['target']=None
            if mode=='called':s['called']=True
            if mode=='unknown':s['target_x']=12
            if mode=='missing':bad['composite']['responses']['config']['modules'][0].pop('strength')
            if mode=='duplicate':bad['composite']['responses']['config']['modules']*=2
            with self.assertRaises(ValueError,msg=mode):validate_saved(bad,self.e.local_map)


if __name__=='__main__':unittest.main()
