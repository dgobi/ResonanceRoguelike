"""One empty crate: explicit intent, exact source, physical ownership and persistence."""
import copy
import random
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pygame
from test_effect_persistence import load_data, make_engine
from engine.engine import GameMode
from generation.floor_object_utils import place_container, place_floor_object


class EmptyCrateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        pygame.init()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='resonance-g14-test-')
        self.addCleanup(temp.cleanup)
        save = patch('engine.save_manager.SAVE_DIR', Path(temp.name))
        save.start(); self.addCleanup(save.stop)
        self.fresh()

    def fresh(self):
        self.e = e = make_engine(self.data)
        e.debug = None
        e.rng = random.Random(29417)
        self.xy = (13, 12)
        place_container(e.local_map, *self.xy, 'crate', [])
        self.owner = e.local_map.container_state[self.xy]
        self.blade = e.item_factory.create('crude_blade')
        self.assertTrue(e.player.inventory.add(self.blade))
        e.player.equipment.equip(self.blade, 'weapon')
        self.started = e.world_time.turn
        e._update_fov()
        self.cursor()

    def cursor(self):
        e = self.e
        e.mode = GameMode.INTERACTION_CURSOR
        e.interaction_cursor.enter([self.xy], e.player.x, e.player.y)

    def key(self, key):
        self.e._handle_key(key)

    def prompt(self):
        self.key(pygame.K_x)
        self.assertIsNotNone(self.e.interaction_cursor._dismantle_prompt)

    def intact(self, turn=0):
        self.assertIs(self.e.local_map.container_state[self.xy], self.owner)
        self.assertEqual('crate', self.e.local_map.decor[self.xy])
        self.assertEqual(self.started + turn, self.e.world_time.turn)
        self.assertFalse(self.e.local_map.floor_objects.get(self.xy))

    def test_eligibility_uses_matching_owners_and_actual_contents_including_serialized_rows(self):
        for case in ('live-item', 'serialized-item', 'orphan-decor', 'orphan-owner',
                     'decor-mismatch', 'owner-mismatch', 'barrel', 'missing-list', 'bad-state'):
            with self.subTest(case=case):
                self.fresh()
                e = self.e; m = e.local_map
                if case == 'live-item': self.owner['items'] = [e.item_factory.create('wood_bundle')]
                if case == 'serialized-item': self.owner.update(state='looted', items=[{'item_id':'wood_bundle'}])
                if case == 'orphan-decor': del m.container_state[self.xy]
                if case == 'orphan-owner': del m.decor[self.xy]
                if case == 'decor-mismatch': m.decor[self.xy] = 'barrel'
                if case == 'owner-mismatch': self.owner['decor_id'] = 'barrel'
                if case == 'barrel': m.decor[self.xy] = self.owner['decor_id'] = 'barrel'
                if case == 'missing-list': del self.owner['items']
                if case == 'bad-state': self.owner['state'] = 'invalid'
                before = repr((m.container_state, m.decor))
                self.key(pygame.K_x)
                self.assertIsNone(e.interaction_cursor._dismantle_prompt)
                self.assertEqual(before, repr((m.container_state, m.decor)))
                self.assertEqual(self.started, e.world_time.turn)
                self.assertFalse(m.floor_objects)
        for state in ('closed', 'open', 'looted'):
            with self.subTest(empty_state=state):
                self.fresh(); self.owner['state'] = state
                self.prompt(); self.key(pygame.K_ESCAPE)
                self.intact()

    def test_enter_search_and_last_pickup_preserve_crate_and_cancel_is_free(self):
        e = self.e
        item = e.item_factory.create('leather_satchel')
        self.owner['items'].append(item)
        self.key(pygame.K_RETURN)
        self.assertEqual('container', e.interaction_cursor._selection_prompt['source'])
        self.key(pygame.K_RETURN)
        self.assertTrue(e.player.inventory.contains(item))
        self.intact(1)
        self.cursor(); self.key(pygame.K_RETURN)
        self.assertIsNone(e.interaction_cursor._selection_prompt)
        self.intact(1)
        self.prompt()
        self.key(pygame.K_LEFT)  # Modal prompt consumes movement without action.
        self.key(pygame.K_ESCAPE)
        self.intact(1)

    def test_owned_equipped_cutting_tool_required_on_offer_and_confirmation(self):
        for moment in ('offer', 'confirm'):
            for case in ('unequipped', 'not-owned', 'flag-only', 'no-flag', 'tier-zero', 'wrong-slot'):
                with self.subTest(moment=moment, tool=case):
                    self.fresh(); e = self.e
                    if moment == 'confirm': self.prompt()
                    if case == 'unequipped': e.player.equipment.unequip('weapon')
                    if case == 'not-owned': e.player.inventory.remove(self.blade)
                    if case == 'flag-only': e.player.equipment.slots['weapon'] = None
                    if case == 'no-flag': self.blade.equipped = False
                    if case == 'tier-zero': self.blade.keywords = [{'tag':'cutting','tier':0}]
                    if case == 'wrong-slot': e.player.equipment.equip(self.blade, 'belt_1')
                    self.key(pygame.K_x if moment == 'offer' else pygame.K_RETURN)
                    self.assertIsNone(e.interaction_cursor._dismantle_prompt)
                    self.intact()
        self.fresh()
        self.e.player.equipment.equip(self.blade, 'offhand')
        self.prompt(); self.key(pygame.K_RETURN)
        self.assertEqual(self.started + 1, self.e.world_time.turn)
        self.assertIs(self.blade, self.e.player.equipment.equipped_in('offhand'))

    def test_confirmation_rejects_replaced_changed_unreachable_or_hidden_source(self):
        for case in ('owner-removed', 'owner-replaced', 'decor-removed', 'decor-changed',
                     'contents-added', 'serialized-added', 'state-changed', 'scene-replaced',
                     'address-changed', 'range', 'invisible', 'sealed-diagonal'):
            with self.subTest(stale=case):
                self.fresh(); e = self.e; m = e.local_map
                self.prompt()
                if case == 'owner-removed': del m.container_state[self.xy]
                if case == 'owner-replaced': m.container_state[self.xy] = copy.deepcopy(self.owner)
                if case == 'decor-removed': del m.decor[self.xy]
                if case == 'decor-changed': m.decor[self.xy] = 'barrel'
                if case == 'contents-added': self.owner['items'].append(e.item_factory.create('wood_bundle'))
                if case == 'serialized-added': self.owner['items'].append({'item_id':'wood_bundle'})
                if case == 'state-changed': self.owner['state'] = 'open'
                if case == 'scene-replaced': e.local_map = copy.copy(m)
                if case == 'address-changed': e.current_submap_id = 'another-scene'
                if case == 'range': e.player.x = 10
                if case == 'invisible': m.visible[self.xy] = False
                if case == 'sealed-diagonal':
                    e.player.y = 11
                    m.walkable[13,11] = m.walkable[12,12] = False
                self.key(pygame.K_RETURN)
                self.assertEqual(self.started, e.world_time.turn)
                self.assertFalse(m.floor_objects)
                self.assertFalse(e.player.inventory.has('wood_bundle'))
                if case not in ('decor-removed', 'decor-changed'):
                    self.assertEqual('crate', m.decor[self.xy])
                if case != 'owner-removed': self.assertIn(self.xy, m.container_state)
        # The same visibility/range/corner rules also prevent opening the prompt.
        for case in ('range', 'hidden', 'corner'):
            self.fresh(); e = self.e
            if case == 'range': e.player.x = 10
            if case == 'hidden': e.local_map.visible[self.xy] = False
            if case == 'corner':
                e.player.y = 11
                e.local_map.walkable[13,11] = e.local_map.walkable[12,12] = False
            self.key(pygame.K_x)
            self.assertIsNone(e.interaction_cursor._dismantle_prompt)
            self.intact()

    def test_factory_and_placement_failures_are_atomic_even_after_partial_write(self):
        for case in ('factory-none', 'factory-raise', 'wrong-output', 'place-false',
                     'place-raise', 'partial-false', 'partial-raise'):
            with self.subTest(failure=case):
                self.fresh(); e = self.e; m = e.local_map
                other = e.item_factory.create('tallow_torch')
                place_floor_object(m, *self.xy, other)
                self.prompt()
                def fail_placement(local_map, x, y, output):
                    if case.startswith('partial'): place_floor_object(local_map, x, y, output)
                    if case.endswith('raise'): raise OSError('injected placement failure')
                    return False
                if case.startswith('factory'):
                    kwargs = {'side_effect':ValueError('injected factory failure')} if case.endswith('raise') else {'return_value':None}
                    failure = patch.object(e.item_factory, 'create', **kwargs)
                elif case == 'wrong-output':
                    failure = patch.object(e.item_factory, 'create', return_value=e.item_factory.create('tallow_torch'))
                else:
                    failure = patch('generation.floor_object_utils.place_floor_object', side_effect=fail_placement)
                with failure: self.key(pygame.K_RETURN)
                self.assertIs(self.owner, m.container_state[self.xy])
                self.assertEqual('crate', m.decor[self.xy])
                self.assertEqual([other], m.floor_objects[self.xy])
                self.assertEqual(self.started, e.world_time.turn)

    def test_success_preserves_other_owners_terrain_tool_and_costs_one_turn(self):
        e = self.e; m = e.local_map
        other = e.item_factory.create('tallow_torch')
        place_floor_object(m, *self.xy, other)
        terrain = m.tiles.copy(); entities = list(e.entities)
        self.prompt(); self.key(pygame.K_RETURN)
        self.assertEqual(self.started + 1, e.world_time.turn)
        self.assertEqual(0, e._move_debt)
        self.assertNotIn(self.xy, m.decor)
        self.assertNotIn(self.xy, m.container_state)
        wood, = [i for i in m.floor_objects[self.xy] if i is not other]
        self.assertEqual('wood_bundle', wood.item_id)
        self.assertEqual(1, wood.count)
        self.assertEqual(self.xy, (wood.x, wood.y))
        self.assertIn('empty crate', wood.description)
        self.assertEqual(terrain.tobytes(), m.tiles.tobytes())
        self.assertEqual(entities, e.entities)
        self.assertTrue(e.player.inventory.contains(self.blade))
        self.assertIs(self.blade, e.player.equipment.equipped_in('weapon'))
        self.cursor(); self.key(pygame.K_x)
        self.assertIsNone(e.interaction_cursor._dismantle_prompt)
        self.assertEqual([other, wood], m.floor_objects[self.xy])
        self.assertEqual(self.started + 1, e.world_time.turn)

    def test_full_pack_leaves_output_and_rejected_pickup_then_takes_once(self):
        e = self.e; inv = e.player.inventory
        inv.capacity = inv.current_weight
        self.prompt(); self.key(pygame.K_RETURN)
        wood, = e.local_map.floor_objects[self.xy]
        self.cursor(); self.key(pygame.K_RETURN)
        self.assertEqual(self.started + 1, e.world_time.turn)
        self.assertEqual([wood], e.local_map.floor_objects[self.xy])
        self.assertFalse(inv.contains(wood))
        inv.capacity = 20
        self.key(pygame.K_RETURN)
        self.assertEqual(self.started + 2, e.world_time.turn)
        self.assertTrue(inv.contains(wood))
        self.assertNotIn(self.xy, e.local_map.floor_objects)
        self.assertEqual(1, sum(i is wood for i in inv.items))

    def test_success_uses_existing_action_debt_and_cache_eviction_revisit(self):
        e = self.e
        e._move_debt = 2.25
        self.prompt(); self.key(pygame.K_RETURN)
        self.assertEqual(self.started + 3, e.world_time.turn)
        self.assertEqual(.25, e._move_debt)
        from g1_support import fingerprint
        expected = fingerprint(e.local_map, [])
        e.save_manager.cache.store(0, 0, e.local_map, e.entities)
        e.save_manager.cache.evict_distant(10, 10)
        self.assertNotIn((0,0), e.save_manager.cache.hot)
        e.world_x = e.world_y = 10  # Leave the scene before preparing its revisit.
        # Destination preparation reads the disk cache before any generation.
        with patch('engine.scene_generation.create_surface', side_effect=AssertionError('must not regenerate')):
            local_map, actors = e._prepare_destination(0, 0)
        self.assertIsNot(local_map, e.local_map)
        self.assertEqual(expected, fingerprint(local_map, actors))
        self.assertNotIn(self.xy, local_map.decor)
        self.assertNotIn(self.xy, local_map.container_state)
        self.assertEqual(['wood_bundle'], [i.item_id for i in local_map.floor_objects[self.xy]])


if __name__ == '__main__': unittest.main()
