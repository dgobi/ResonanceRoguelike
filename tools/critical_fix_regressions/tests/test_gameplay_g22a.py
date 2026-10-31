"""Scenario premise and real carried-form regressions, not a duplicated route."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_effect_persistence import load_data, make_engine
from test_gameplay_g22 import world
from engine import location_reports
from engine.item_system import ItemSystem
from g22a_journey import Policy, validate_situation


class ConnectedScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        self.e = e = make_engine(self.data)
        e.world_map = world()
        e.world_map.seed = 20261023
        location_reports.bind(e.world_map, 'Test report')
        e.world_map.learned_reports = list(location_reports.ROLES)
        e.world_x, e.world_y, e.current_submap_id = 2, 0, 'ward'
        e.local_map.visible[:] = True
        for iid in ('research_note','letter','herbal_dressing','musk_pellet','faceted_ward'):
            item = e.item_factory.create(iid)
            if iid == 'research_note': item.text_id = 'lab_route_sheet_a'
            if iid == 'letter': item.text_id = 'barrow_ward_store_note_a'
            self.assertTrue(e.player.inventory.add(item))
        self.context = dict(owner=e.world_map.report_owner,home=[0,0],target=[2,0],submap='ward')
        self.guard = e.creature_factory.spawn('hollow_revenant',13,12)
        e.entities.append(self.guard)

    def test_semantic_premise_accepts_later_turn_but_requires_observed_contact(self):
        e = self.e
        e.world_time.turn = 2117
        self.assertTrue(validate_situation(e,self.context,keeper_delay=True))
        e.local_map.visible[self.guard.x,self.guard.y] = False
        with self.assertRaisesRegex(AssertionError,'No observed adjacent keeper'):
            validate_situation(e,self.context,keeper_delay=True)
        # No keeper can still be an honest no-injury pickup, never that setback.
        self.assertTrue(validate_situation(e,self.context))
        e.local_map.visible[:] = True
        self.guard.x = 16
        with self.assertRaisesRegex(AssertionError,'No observed adjacent keeper'):
            validate_situation(e,self.context,keeper_delay=True)

    def test_reject_wrong_world_destination_ownership_and_dead_character(self):
        e = self.e
        with self.assertRaisesRegex(AssertionError,'Wrong campaign'):
            validate_situation(e,dict(self.context,owner='0'*32))
        with self.assertRaisesRegex(AssertionError,'Wrong reported destination'):
            validate_situation(e,dict(self.context,target=[3,0]))
        for iid in ('herbal_dressing','musk_pellet','faceted_ward'):
            item=e.player.inventory.get_by_id(iid)
            e.player.inventory.remove(item)
            with self.assertRaises(AssertionError):
                validate_situation(e,self.context,keeper_delay=True)
            e.player.inventory.add(item)
        e.player.fighter.hp=0
        with self.assertRaisesRegex(AssertionError,'Living ordinary character'):
            validate_situation(e,self.context,keeper_delay=True)

    def test_filled_skin_and_flask_both_use_real_exchange_retaining_empty(self):
        e = self.e
        policy = Policy(None,SimpleNamespace(record={}))
        policy.record=lambda *a,**kw:None
        system = ItemSystem()
        def ordinary_use(engine,item,key,choose):
            system.use(item,engine)
            yield None
        for iid in ('water_skin','water_flask'):
            with self.subTest(form=iid):
                item=e.item_factory.create(iid)
                self.assertTrue(e.player.inventory.add(item))
                empties=sum(i.item_id=='empty_water_skin' for i in e.player.inventory.items)
                e.player.needs.thirst=.6
                with patch('g12_journey.inventory',ordinary_use):
                    list(policy.eat_drink(e,None))
                self.assertFalse(e.player.inventory.contains(item))
                self.assertAlmostEqual(.1,e.player.needs.thirst)
                self.assertEqual(empties+1,sum(i.item_id=='empty_water_skin' for i in e.player.inventory.items))

    def test_no_refill_detour_for_unseen_water_or_unowned_empty(self):
        e = self.e
        e.current_submap_id=None
        e.entities=[e.player]
        e.local_map.set_tile(14,12,'shallow_water',True,True)
        e.local_map.explored[:]=False
        e.player.inventory.add(e.item_factory.create('empty_water_skin'))
        policy=Policy(None,SimpleNamespace(record={}))
        with patch('g22_journey.approach',side_effect=AssertionError('Unseen water selected')):
            list(policy.water(e,None))
        e.local_map.explored[:]=True
        e.player.inventory.remove(e.player.inventory.get_by_id('empty_water_skin'))
        with patch('g22_journey.approach',side_effect=AssertionError('Unneeded detour')):
            list(policy.water(e,None))

    def test_musk_enters_real_cursor_before_validity_and_pays_exact_consumption(self):
        e=self.e
        policy=Policy(None,SimpleNamespace(record={}))
        policy.record=lambda *a,**kw:None
        pellet=e.player.inventory.get_by_id('musk_pellet')
        def open_item(engine,item,key,choose):
            self.assertIs(item,pellet)
            engine.item_system.use(item,engine)
            yield None
        def key(k,*args):
            e._handle_key(k)
        before=e.world_time.turn
        with patch('g12_journey.inventory',open_item):
            list(policy.musk(e,key))
        self.assertTrue(policy.pellet_used)
        self.assertFalse(e.player.inventory.contains(pellet))
        self.assertEqual(before+1,e.world_time.turn)
        self.assertEqual(5,e.local_map.disruption_zones[-1]['turns_remaining'])


if __name__ == '__main__':
    unittest.main()
