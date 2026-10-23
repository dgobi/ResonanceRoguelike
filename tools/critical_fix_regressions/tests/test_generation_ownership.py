"""Actual startup/travel/pursuit/checkpoint routes, using only disposable saves."""
from __future__ import annotations
from collections import deque
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pygame
from test_effect_persistence import load_data, make_engine, GAME_ROOT
from g1_support import fingerprint
from components.ai import AIState
from engine.engine import Engine, MOVE_KEYS
from engine.save_manager import _serialize_world, _deserialize_world
from generation.context import GenerationError, GENERATION_REVISION
from generation.region_gen import _generate_town_base
from generation.town_gen import _stamp_building_at
from world.world_map import Chunk, RegionType


class GenerationOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='resonance-g1-ownership-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        saver = patch('engine.save_manager.SAVE_DIR', self.root)
        saver.start()
        self.addCleanup(saver.stop)
        capture = contextlib.redirect_stdout(io.StringIO())
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)

    def engine(self):
        e = make_engine(self.data)
        e.world_map.width = 3
        e.world_map.set(Chunk(1, 0, RegionType.TOWN, 29417, town_id=1, town_role='N'))
        e.world_map.set(Chunk(2, 0, RegionType.FOREST, 77123, biome_id='forest',
                              zones=[('deepwood', .6), ('briarwood', .3), ('mere', .1)]))
        return e

    def test_real_wilderness_first_creator_has_equivalent_positive_native_population(self):
        rows = []
        for migrant_first in (False, True):
            e = self.engine()
            # Move the authored starting fixture next to the wilderness destination.
            e.world_x = 1
            e.player.x, e.player.y = 79, 12
            if migrant_first:
                a = e.creature_factory.spawn('hollow_revenant', 79, 12)
                a.name = 'G1 migrant'
                a.ai.state = AIState.HUNTING
                a._last_known_px, a._last_known_py = 79, 12
                e.entities.append(a)
                e._check_entity_chunk_crossings()
                self.assertNotIn(a, e.entities)
            e._transition_chunk(1, 0)
            natives = [a for a in e.entities if a is not e.player and a.name != 'G1 migrant']
            self.assertGreater(len(natives), 0)
            self.assertEqual(sum(a.name == 'G1 migrant' for a in e.entities), int(migrant_first))
            rows.append(fingerprint(e.local_map, natives))
        self.assertEqual(rows[0], rows[1])

    def test_town_first_creator_semantics_and_abandoned_pursuer_active_owner(self):
        rows = []
        for migrant_first in (False, True):
            e = self.engine()
            e.player.x, e.player.y = 79, 12
            if migrant_first:
                a = e.creature_factory.spawn('hollow_revenant', 79, 12)
                a.name = 'G1 migrant'
                a.ai.state = AIState.HUNTING
                a._last_known_px, a._last_known_py = 79, 12
                e.entities.append(a)
                e._check_entity_chunk_crossings()
            e._transition_chunk(1, 0)
            natives = [a for a in e.entities if a is not e.player and a.name != 'G1 migrant']
            self.assertGreater(len(natives), 0)
            self.assertEqual(sum(a.name == 'G1 migrant' for a in e.entities), int(migrant_first))
            rows.append(fingerprint(e.local_map, natives, e.world_map.get(1, 0).town_data))
            a = e.creature_factory.spawn('hollow_revenant', 12, 12)
            a.ai.state = AIState.WANDERING
            e._live_pursuers = [(a, 1, 0, None)]
            e.save_manager.cache.store(1, 0, copy.deepcopy(e.local_map), [])
            e._tick_live_pursuers()
            self.assertEqual(sum(actor is a for actor in e.entities), 1)
            self.assertFalse(e._live_pursuers)
        self.assertEqual(rows[0], rows[1])

    def test_abandoned_pursuer_failure_keeps_owner_and_surface_return_creates_natives(self):
        e = self.engine()
        a = e.creature_factory.spawn('hollow_revenant', 12, 12)
        a.ai.state = AIState.WANDERING
        e._live_pursuers = [(a, 1, 0, None)]
        with patch('engine.scene_generation.populate', side_effect=GenerationError('injected')):
            e._tick_live_pursuers()
        self.assertEqual(e._live_pursuers, [(a, 1, 0, None)])
        self.assertIsNone(e.save_manager.cache.load(1, 0))
        a._surface_exit_wx, a._surface_exit_wy = 1, 0
        a._surface_exit_x, a._surface_exit_y = 12, 12
        self.assertTrue(e._transfer_submap_pursuer_to_surface(a, 1, 0, 'fixture'))
        # Caller removes the live tuple after successful transfer.
        e._live_pursuers.clear()
        cache = e.save_manager.cache.load(1, 0)
        self.assertTrue(cache.local_map.generation_complete)
        self.assertGreater(len(cache.entities), 1)

    def test_authored_and_bsp_pursuer_first_match_player_first_and_return_links(self):
        for layout in ('starting_lab', ''):
            rows = []
            for migrant_first in (False, True):
                e = self.engine()
                c = e.world_map.get(0, 0)
                sm = c.add_submap('laboratory' if layout else 'barrow', 'Fixture', 29417, layout)
                sm.surface_x, sm.surface_y = 12, 12
                e.local_map.set_tile(12, 12, 'stairs_down', True, True)
                e.local_map.submap_links[12, 12] = sm.submap_id
                if migrant_first:
                    a = e.creature_factory.spawn('hollow_revenant', 12, 12)
                    a.name = 'G1 migrant'
                    a.ai.state = AIState.HUNTING
                    a.ai.target_x = a.ai.target_y = 12
                    a._last_known_px = a._last_known_py = 12
                    e._live_pursuers = [(a, 0, 0, None)]
                    e._tick_live_pursuers()
                    self.assertFalse(e._live_pursuers)
                    self.assertEqual((e.world_x, e.world_y, e.current_submap_id), (0, 0, None))
                e._descend_to_submap(sm.submap_id)
                self.assertEqual(e.current_submap_id, sm.submap_id)
                natives = [a for a in e.entities if a is not e.player and a.name != 'G1 migrant']
                rows.append((fingerprint(e.local_map, natives), sm.entry_x, sm.entry_y))
                self.assertGreater(sum(map(len, e.local_map.floor_objects.values())), 0)
                self.assertEqual(sum(a.name == 'G1 migrant' for a in e.entities), int(migrant_first))
                e._ascend_from_submap()
                self.assertEqual(e.local_map.submap_links[12, 12], sm.submap_id)
                self.assertEqual((e.player.x, e.player.y), (12, 12))
            self.assertEqual(rows[0], rows[1])

    def test_submap_failure_does_not_transfer_or_mark_generated(self):
        e = self.engine()
        sm = e.world_map.get(0, 0).add_submap('barrow', 'Fixture', 29417)
        a = e.creature_factory.spawn('hollow_revenant', 12, 13)
        a.ai.state = AIState.HUNTING
        e.entities.append(a)
        before = e.local_map
        e.player._hollow_knight_disruption = True
        with patch('engine.scene_generation.populate', side_effect=GenerationError('injected native failure')):
            e._descend_to_submap(sm.submap_id)
        self.assertIs(e.local_map, before)
        self.assertTrue(e.player._hollow_knight_disruption)
        self.assertIsNone(e.current_submap_id)
        self.assertFalse(sm.generated)
        self.assertIn(a, e.entities)
        self.assertFalse(e._pending_transfer)
        self.assertIsNone(e.save_manager.cache.load_submap(sm.submap_id))
        e._descend_to_submap(sm.submap_id)
        self.assertTrue(sm.generated)
        self.assertEqual(sum(a is actor for actor in e.entities), 1)

    def test_startup_uses_complete_surface_and_retains_its_actors_below(self):
        import main
        captured = []
        # Seed-only bootstrap is the existing supported new-game seed fixture.
        slot = self.root / 'slot_0'
        slot.mkdir()
        (slot / 'world.json').write_text(json.dumps(dict(seed=20261020)))
        previous = Path.cwd()
        try:
            os.chdir(GAME_ROOT)
            with patch.object(Engine, 'run', lambda e: captured.append(e)):
                main.main()
        finally:
            os.chdir(previous)
        e = captured[0]
        self.assertIsNotNone(e.current_submap_id)
        surface = e.save_manager.cache.load(e.world_x, e.world_y)
        self.assertTrue(surface.local_map.generation_complete)
        self.assertGreater(len(surface.entities), 0)
        self.assertGreater(int((surface.local_map.tiles['terrain'] == 'flint_rock').sum()), 0)
        self.assertTrue(e.local_map.generation_complete)
        self.assertGreater(len(e.local_map.floor_objects), 0)

    def test_mutated_scene_survives_hot_cold_and_fresh_process_return(self):
        e = self.engine()
        e.overmap_cursor_x, e.overmap_cursor_y = 1, 0
        e._teleport_to_overmap_cursor()
        victim = next(a for a in e.entities if a is not e.player)
        victim.fighter.take_damage(victim.fighter.hp)
        e._on_entity_death(victim)
        e.entities.remove(victim)  # same finalized-death cleanup as the turn loop
        e.local_map.floor_objects.clear()
        for c in e.local_map.container_state.values():
            c['items'].clear()
            c['state'] = 'looted'
        e.local_map.set_tile(3, 3, 'mud', True, True)
        expected = fingerprint(e.local_map, e.entities[1:])
        for cold in (False, True):
            e.overmap_cursor_x = 0
            e._teleport_to_overmap_cursor()
            if cold:
                e.save_manager.cache.evict_distant(100, 100)
                self.assertNotIn((1, 0), e.save_manager.cache.hot)
            e.overmap_cursor_x = 1
            e._teleport_to_overmap_cursor()
            self.assertEqual(expected, fingerprint(e.local_map, e.entities[1:]))
        self.assertTrue(e.save_manager.save(e), e.save_manager.last_error)
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--read', str(self.root)],
                                capture_output=True, text=True, cwd=GAME_ROOT, timeout=30,
                                env=dict(os.environ, PYTHONPATH=str(GAME_ROOT)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(expected, json.loads(result.stdout)['fingerprint'])

    def test_f5_exploration_migration_f9_does_not_advance_checkpoint(self):
        e = self.engine()
        e.debug = False
        e._handle_key_local(pygame.K_F5)
        path = e.save_manager.save_path / 'HEAD.json'
        head = path.read_bytes()
        e.player.x, e.player.y = 79, 12
        a = e.creature_factory.spawn('hollow_revenant', 79, 12)
        a.name = 'G1 migrant'
        a.ai.state = AIState.HUNTING
        a._last_known_px, a._last_known_py = 79, 12
        e.entities.append(a)
        e._check_entity_chunk_crossings()
        e._transition_chunk(1, 0)
        self.assertEqual(path.read_bytes(), head)
        self.assertTrue(e.save_manager.cache.has(1, 0))
        e._handle_key_local(pygame.K_F9)
        self.assertEqual((e.world_x, e.world_y), (0, 0))
        self.assertFalse(e.save_manager.cache.has(1, 0))
        self.assertFalse(any(a.name == 'G1 migrant' for a in e.entities))

    def test_legacy_empty_scene_is_authoritative_and_new_scene_does_not_relabel_world(self):
        e = self.engine()
        record = _serialize_world(e.world_map)
        record.pop('generation_revision')
        _deserialize_world(record, e.world_map)
        for name in ('generation_context', 'generation_revision', 'generation_complete'):
            e.local_map.__dict__.pop(name, None)
        original = fingerprint(e.local_map, [])
        e.save_manager.cache.store(0, 0, e.local_map, [])
        e.overmap_cursor_x, e.overmap_cursor_y = 1, 0
        e._teleport_to_overmap_cursor()
        self.assertEqual(e.local_map.generation_revision, GENERATION_REVISION)
        self.assertEqual(_serialize_world(e.world_map)['generation_revision'], 'legacy-unversioned')
        e.overmap_cursor_x = 0
        e._teleport_to_overmap_cursor()
        self.assertEqual(original, fingerprint(e.local_map, e.entities[1:]))
        self.assertTrue(e.save_manager.save(e), e.save_manager.last_error)
        self.assertTrue(e.save_manager.load(e), e.save_manager.last_error)
        self.assertEqual(original, fingerprint(e.local_map, e.entities[1:]))
        self.assertEqual(e.world_map.generation_revision, 'legacy-unversioned')

    def test_missing_owned_scene_is_not_regenerated(self):
        e = self.engine()
        c = e.world_map.get(1, 0)
        c.visited = True
        with patch('engine.scene_generation.create_surface') as create:
            self.assertIsNone(e._prepare_destination(1, 0))
            create.assert_not_called()
        self.assertEqual((e.world_x, e.world_y), (0, 0))

    def test_missing_or_corrupt_checkpoint_never_invokes_generation(self):
        for mode in ('missing', 'corrupt'):
            with patch('engine.save_manager.SAVE_DIR', self.root / mode):
                e = self.engine()
                self.assertTrue(e.save_manager.save(e), e.save_manager.last_error)
                scene_file = next((e.save_manager.checkpoint_path() / 'chunks').glob('*.pkl'))
                if mode == 'missing': scene_file.unlink()  # owned temporary fixture only
                else: scene_file.write_bytes(b'injected corrupt test record')
                original = e.local_map
                with patch('engine.scene_generation.create_surface') as surface, patch('engine.scene_generation.create_submap') as submap:
                    self.assertFalse(e.save_manager.load(e))
                    surface.assert_not_called()
                    submap.assert_not_called()
                self.assertIs(e.local_map, original)
                self.assertTrue(e.save_manager.last_error)

    def test_validation_failure_cannot_publish_metadata(self):
        e = self.engine()
        c = e.world_map.get(1, 0)
        sm = c.add_submap('barrow', 'Fixture', 29417)
        before = (sm.surface_x, sm.surface_y, sm.generated)
        with patch('engine.scene_generation.validate_scene', side_effect=GenerationError('injected validation failure')):
            self.assertIsNone(e._prepare_destination(1, 0))
        self.assertIsNone(c.town_data)
        self.assertEqual(before, (sm.surface_x, sm.surface_y, sm.generated))
        self.assertFalse(getattr(c, 'generation_revision', None))
        self.assertIsNone(e.save_manager.cache.load(1, 0))
        m, actors = e._ensure_surface_scene(1, 0)
        self.assertTrue(m.generation_complete)
        self.assertGreater(len(actors), 0)

    def test_repaired_notes_can_be_walked_to_picked_up_and_read(self):
        for category, bid in [('residential', 'hovel'), ('wilderness', 'hunter_cabin')]:
            building = next(b for b in self.data.buildings[category] if b['id'] == bid)
            for flip in (False, True):
                e = self.engine()
                m = _generate_town_base(30, 25, self.data.terrain)
                specs = _stamp_building_at(m, building, 8, 8, self.data.terrain, flip_v=flip)
                e._spawn_layout_entities(specs, local_map=m)
                e.local_map = m
                note = next(s for s in specs if s.get('text_id'))
                target = note['x'], note['y']
                e.player.x, e.player.y = 1, 1
                path = action_path(e, (1, 1), target)
                self.assertIsNotNone(path)
                for xy in path[1:]:
                    delta = xy[0] - e.player.x, xy[1] - e.player.y
                    key = next(k for k, direction in MOVE_KEYS.items() if direction == delta)
                    if str(m.tiles[xy]['terrain']) == 'door_closed':
                        e._handle_key_local(key)
                        self.assertEqual(str(m.tiles[xy]['terrain']), 'door_open')
                    e._handle_key_local(key)
                    self.assertEqual((e.player.x, e.player.y), xy)
                e._handle_key_local(pygame.K_COMMA)
                item = next(i for i in e.player.inventory.items if i.text_id == note['text_id'])
                self.assertFalse(m.floor_objects.get(target))
                e.item_system.use(item, e)
                self.assertTrue(e.text_reader.open)
                self.assertEqual(e.text_reader._text_id, note['text_id'])


def action_path(e, start, target):
    parents, queue = {start: None}, deque([start])
    m = e.local_map
    while queue:
        p = queue.popleft()
        if p == target:
            path = []
            while p is not None:
                path.append(p)
                p = parents[p]
            return path[::-1]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = p[0] + dx, p[1] + dy
                if (m.in_bounds(*q) and q not in parents and
                    (m.walkable[q] or str(m.tiles[q]['terrain']) == 'door_closed') and
                        not e._decor_blocks_movement(*q)):
                    parents[q] = p
                    queue.append(q)


if __name__ == '__main__':
    if '--read' in sys.argv:
        with contextlib.redirect_stdout(io.StringIO()), patch('engine.save_manager.SAVE_DIR', Path(sys.argv[-1])):
            e = make_engine(load_data())
            if not e.save_manager.load(e): raise RuntimeError(e.save_manager.last_error)
            result = dict(fingerprint=fingerprint(e.local_map, e.entities[1:]))
        print(json.dumps(result))
    else:
        unittest.main()
