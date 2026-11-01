"""AI-6 controlled engine risks; ordinary/native witnesses are separate."""
import copy
import unittest
from unittest.mock import patch
import test_ai_1 as ai1
from engine.ai_profiles import TERRITORY_DEFAULTS, effective_profile, validate_saved, depart
from engine.save_manager import _serialize_entity, _deserialize_entities
from engine.combat import CombatResult
from engine.sound import emit
from components.territorial import signature


class TerritorialTests(unittest.TestCase):
    setUpClass = classmethod(ai1.StrikeWithdrawTests.setUpClass.__func__)
    setUp = ai1.StrikeWithdrawTests.setUp
    decision = ai1.StrikeWithdrawTests.decision
    tick = ai1.StrikeWithdrawTests.tick

    def actor(self, x=16, y=12, **profile):
        return ai1.StrikeWithdrawTests.actor(self,x=x,y=y,**{**TERRITORY_DEFAULTS,**profile})

    def test_strict_profile_and_matched_engagement_authority(self):
        for change in ({'defended_radius':True},{'excursion_radius':4},{'excursion_radius':9},
                       {'defended_radius':2.5},{'engagement':'venom'}, {'trigger':'committed_attack'},
                       {'retreat_distance':3},{'scene_scope':'world'},{'pursuit_budget':0}):
            with self.assertRaises(ValueError): effective_profile(dict(ai_profile={**TERRITORY_DEFAULTS,**change}))
        p=effective_profile(dict(ai_profile={**TERRITORY_DEFAULTS,'engagement':'strike_and_withdraw','trigger':'committed_attack'}))
        self.assertEqual('committed_attack',p['trigger'])

    def test_ordinary_nonplayer_intrusion_neutral_dead_and_foreign_rejection(self):
        a=self.actor();self.e.player.x=40
        rival=self.e.creature_factory.spawn('highland_bandit',12,12);self.e.entities.append(rival)
        self.decision(a);self.assertIsNone(a.ai.target)
        a.perception.hostile_to=[rival.perception.faction]
        self.decision(a);self.assertEqual(rival._individual_id,a.ai.target['id'])
        rival.is_alive=False;self.decision(a);self.assertIsNone(a.ai.target)
        rival.is_alive=True;a.ai.territory['owner']='1,1/foreign'
        pos=(a.x,a.y);self.decision(a);self.assertEqual(pos,(a.x,a.y));self.assertIsNone(a.ai.target)

    def test_diagonal_decor_occupancy_and_terrain_commit_revalidation(self):
        a=self.actor();self.e.player.x=40;self.decision(a);m=self.e.local_map
        for xy in ((17,12),(16,13)):m.set_tile(*xy,'wall',False,False)
        self.assertFalse(a.ai._move(self.e,a,(17,13)))
        m.set_tile(17,12,'floor',True,True)
        with patch.object(self.e,'_decor_blocks_movement',side_effect=lambda x,y:(x,y)==(17,13)):
            self.assertFalse(a.ai._move(self.e,a,(17,13)))
        b=self.e.creature_factory.spawn('highland_bandit',17,13);self.e.entities.append(b)
        self.assertFalse(a.ai._move(self.e,a,(17,13)));self.e.entities.remove(b)
        raw=self.e.data.terrain[str(m.tiles[17,13]['terrain'])];old=raw.get('creature_passable',True)
        raw['creature_passable']=False
        self.assertFalse(a.ai._move(self.e,a,(17,13)))
        raw['creature_passable']=old

    def test_inner_acquisition_outer_cessation_real_return(self):
        a=self.actor();self.e.player.x=11;self.decision(a)
        self.assertIsNone(a.ai.target);self.assertEqual((16,12),(a.x,a.y))
        self.e.player.x=12;self.decision(a)
        self.assertEqual('engaged',a.ai.territory['phase']);self.assertEqual(31,a.ai.territory['pursuit_left'])
        self.e.player.x=9;self.decision(a)
        self.assertIsNone(a.ai.target);self.assertEqual('observed_beyond_excursion',a.ai.territory['reason'])
        for _ in range(12):self.decision(a)
        self.assertEqual('guard',a.ai.territory['phase']);self.assertEqual((16,12),(a.x,a.y))
        self.assertEqual([16,12],a.ai.territory['anchor'])

    def test_hidden_crossing_never_uses_live_position_or_debug_reveal(self):
        a=self.actor();self.decision(a);trail=copy.deepcopy(a.ai.target)
        self.e.player.x=35;self.e.debug_reveal=True
        with patch.object(a.ai,'sees',return_value=False):
            a.ai.refresh_evidence(self.e,a,1)
            self.assertEqual(trail,a.ai.target)
            self.decision(a)
            self.assertNotEqual('observed_beyond_excursion',a.ai.territory['reason'])
            self.e.world_time.turn=trail['deadline']+1
            a.ai.refresh_evidence(self.e,a,1)
        self.assertIsNone(a.ai.target);self.assertEqual('return',a.ai.territory['phase'])

    def test_shared_executor_direct_and_withdraw_and_tuning_change(self):
        for engagement,phase in [('direct_melee','approach'),('strike_and_withdraw','withdraw')]:
            self.e.entities=[self.e.player];a=self.actor(x=13,engagement=engagement)
            with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True)) as resolver:
                self.decision(a);self.assertEqual(phase,a.ai.phase);resolver.assert_called_once()
                before=(a.x,a.y);self.decision(a)
                if engagement=='strike_and_withdraw': self.assertNotEqual(before,(a.x,a.y));self.assertEqual('hold',a.ai.phase)
            self.assertEqual([13,12],a.ai.territory['anchor'])
        self.e.entities=[self.e.player];a=self.actor(defended_radius=3);self.decision(a)
        self.assertIsNone(a.ai.target)
        a.ai.profile['defended_radius']=4;self.decision(a);self.assertIsNotNone(a.ai.target)

    def test_no_progress_retired_at_home_until_material_route_or_position_change(self):
        a=self.actor();self.e.player.x=12
        # Transparent blocking decor: visible, but all approach routes fail.
        with patch.object(self.e,'_decor_blocks_movement',side_effect=lambda x,y: (x,y)!=(a.x,a.y)):
            for _ in range(10):self.decision(a)
            self.assertIsNone(a.ai.target);self.assertEqual('guard',a.ai.territory['phase'])
            for _ in range(60):self.decision(a)
            self.assertIsNone(a.ai.target);self.assertEqual(1,len(a.ai.territory['retired']))
            self.assertEqual('approach_exhausted',a.ai.territory['reason'])
        self.decision(a);self.assertIsNotNone(a.ai.target)

    def test_budget_spends_attacks_holds_and_return_ignores_boundary_spam(self):
        a=self.actor(x=13,pursuit_budget=2,engagement='strike_and_withdraw')
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True)):
            self.decision(a);self.decision(a)
            self.assertEqual(0,a.ai.territory['pursuit_left']);self.assertEqual('return',a.ai.territory['phase'])
            for x in (8,12,8):
                self.e.player.x=x;emit(self.e,13,12,'combat');self.assertIsNone(a.ai.sound_interest)
                self.decision(a);self.assertEqual(0,a.ai.territory['pursuit_left'])
                if a.ai.territory['phase']=='guard':break

    def test_domain_filters_entire_route_retreat_and_actual_commit(self):
        a=self.actor(x=16,engagement='strike_and_withdraw');self.decision(a)
        a.x,a.y=22,12
        self.assertFalse(a.ai._move(self.e,a,(23,12)))
        step,length=a.ai._route(self.e,a,lambda x,y: x==23)
        self.assertIsNone(step);self.assertIsNone(length)
        # Displacement recovery retains home; no outward pursuit even with prey.
        a.x=24;self.e.player.x=25;self.decision(a)
        self.assertEqual('return',a.ai.territory['phase']);self.assertIsNone(a.ai.target)
        for _ in range(20):self.decision(a)
        self.assertEqual([16,12],a.ai.territory['anchor']);self.assertLessEqual(a.x,22)

    def test_occupied_post_fallback_retains_anchor_and_restores_original(self):
        a=self.actor();self.e.player.x=40;self.decision(a)
        blocker=self.e.creature_factory.spawn('hollow_revenant',16,12);self.e.entities.append(blocker)
        a.x=19;a.ai.cancel(a,'fixture_displacement')
        for _ in range(12):self.decision(a)
        self.assertEqual('guard',a.ai.territory['phase']);self.assertNotEqual((16,12),(a.x,a.y))
        self.assertEqual([16,12],a.ai.territory['anchor'])
        self.e.entities.remove(blocker)
        for _ in range(8):self.decision(a)
        self.assertEqual((16,12),(a.x,a.y))

    def test_far_external_displacement_can_physically_recover_beyond_route_horizon(self):
        a=self.actor();self.e.player.x=60;self.decision(a);a.x=42
        for _ in range(40):self.decision(a)
        self.assertEqual((16,12),(a.x,a.y));self.assertEqual([16,12],a.ai.territory['anchor'])

    def test_impossible_return_replans_infrequently_then_on_change(self):
        a=self.actor();self.e.player.x=40;self.decision(a);a.x=20;a.ai.cancel(a,'fixture')
        with patch.object(self.e,'_decor_blocks_movement',return_value=True):
            for _ in range(8):self.decision(a)
            self.assertEqual('blocked',a.ai.territory['phase'])
            with patch.object(a.ai,'_route',wraps=a.ai._route) as route:
                for _ in range(11):self.decision(a)
                route.assert_not_called()
        self.decision(a);self.assertNotEqual('blocked',a.ai.territory['phase'])

    def test_anonymous_sound_inner_only_finite_and_no_return_queue(self):
        a=self.actor();self.e.player.x=40;self.decision(a)
        self.assertEqual(0,emit(self.e,21,12,'combat'))
        self.assertEqual(1,emit(self.e,18,12,'flint'))
        self.decision(a);self.assertNotEqual(16,a.x);self.assertIsNone(a.ai.target)
        for _ in range(20):
            if a.ai.territory['phase']=='return':
                emit(self.e,18,12,'combat');self.assertIsNone(a.ai.sound_interest)
            self.decision(a)
        self.assertEqual('guard',a.ai.territory['phase']);self.assertEqual((16,12),(a.x,a.y))

    def test_save_state_exact_validation_and_effective_profile(self):
        a=self.actor();self.decision(a);row=_serialize_entity(a);validate_saved(row,self.e.local_map)
        b=_deserialize_entities([row],self.e)[0]
        self.assertEqual(a.ai.snapshot(),b.ai.snapshot());self.assertEqual(a.ai.home_x,b.ai.home_x)
        for field,value in [('pursuit_left',True),('pursuit_left',99),('anchor',[15,12]),('owner','world'),('retry',13),('phase','wander')]:
            bad=copy.deepcopy(row);bad['composite']['state']['territory'][field]=value
            with self.assertRaises(ValueError):validate_saved(bad,self.e.local_map)
        self.e.data.entities['hollow_revenant']['ai_profile']['defended_radius']=1
        b=_deserialize_entities([row],self.e)[0];self.assertEqual(4,b.ai.profile['defended_radius'])

    def test_scene_departure_keeps_position_home_and_consequences(self):
        a=self.actor();self.decision(a);pos=(a.x,a.y);hp=a.fighter.hp
        depart(self.e)
        self.assertIsNone(a.ai.target);self.assertEqual('return',a.ai.territory['phase'])
        self.assertEqual(pos,(a.x,a.y));self.assertEqual(hp,a.fighter.hp);self.assertEqual(0,a.ai.move_accumulator)
        row=_serialize_entity(a);validate_saved(row,self.e.local_map)
        self.decision(a);self.assertEqual([16,12],a.ai.territory['anchor'])

    def test_paralysis_does_not_spend_route_or_pursuit_and_contact_defence_is_ordinary(self):
        a=self.actor();self.decision(a);budget=a.ai.territory['pursuit_left'];pos=(a.x,a.y)
        with patch('engine.venom.fully_paralysed',return_value=True):
            for _ in range(5):self.decision(a)
        self.assertEqual(budget,a.ai.territory['pursuit_left']);self.assertEqual(pos,(a.x,a.y))
        self.e.player.x=a.x-1;a.ai.cancel(a,'fixture')
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True)) as resolve:
            self.decision(a);self.assertEqual('return_contact_defence',a.ai.trace[-1]['reason']);resolve.assert_called_once()
            self.assertIsNone(a.ai.target);self.assertEqual(0,a.ai.territory['pursuit_left'])

    def test_guard_is_supported_real_venom_victim_scheduler_cannot_bank_a_burst(self):
        from components.ai import _monster_attack_result
        from engine.venom import dose, fully_paralysed
        from engine.effect_lifecycle import finish_turn
        a=self.actor(x=13);self.decision(a)
        source=self.e.creature_factory.spawn('patient_amber_hunter',14,12);source.perception.hostile_to=[a.perception.faction];self.e.entities.append(source)
        with patch('engine.combat.resolve_attack',return_value=CombatResult(hit=True,damage_dealt=1)):
            r=_monster_attack_result(source,a,self.e,defensive=True)
        self.assertTrue(r.application.accepted)
        def age():
            self.e.world_time.turn+=1;self.e._effect_aged_ids=set();finish_turn(self.e,[a,source])
        for _ in range(3):age()
        self.assertTrue(fully_paralysed(a));budget=a.ai.territory['pursuit_left'];pos=(a.x,a.y)
        self.e.entities.remove(source)
        for _ in range(3):
            self.tick();self.assertEqual(pos,(a.x,a.y));self.assertEqual(budget,a.ai.territory['pursuit_left'])
            self.assertLess(a.ai.move_accumulator,1);age()
        self.assertEqual('recovery',dose(a)['stage']);self.assertTrue(a.fighter.can_attack())
        opportunities=a.ai.opportunities;self.tick();self.assertEqual(opportunities+1,a.ai.opportunities)

    def test_failed_actual_departure_and_report_roles(self):
        a=self.actor();self.decision(a);before=a.ai.snapshot()
        self.e._try_ascend();self.assertEqual(before,a.ai.snapshot())
        from test_gameplay_g22 import world
        from engine import location_reports
        from engine.save_manager import _serialize_world,_deserialize_world
        from world.world_map import WorldMap
        w=world();location_reports.bind(w,'Original');old=copy.deepcopy(w.location_reports)
        w.get(2,0).submaps[0].layout_id='barrow_ward_store_b'
        self.assertEqual('barrow_ward_store_b',list(location_reports.candidates(w,'ward_store'))[0][3])
        # Loading old records never rebinds them to a new selected identity.
        w.get(2,0).submaps[0].layout_id='barrow_ward_store_a'
        restored=copy.deepcopy(w);location_reports.validate(restored)
        self.assertEqual(old,restored.location_reports)


if __name__=='__main__':unittest.main()

