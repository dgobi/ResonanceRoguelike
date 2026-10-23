"""G1 contracts on production generation and actual engine entry routes."""
from __future__ import annotations

from collections import deque
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_effect_persistence import load_data, make_engine, GAME_ROOT
from components.ai import AIState
from generation.local_gen import generate_dungeon
from generation.region_gen import generate_region, _generate_town_base
from generation.town_gen import _stamp_building_at
from world.world_map import Chunk, RegionType, ConnectorType


def reachable(local_map, data, starts=None):
    """Current player: eight directions, openable doors, blocking decor."""
    def enterable(x, y):
        terrain = str(local_map.tiles[x, y]['terrain'])
        return (bool(local_map.walkable[x, y]) or terrain == 'door_closed') and not (
            data.decoratives.get(local_map.decor.get((x, y)), {}).get('blocks_movement', False))
    seen = set(starts or ((x, y) for x in range(local_map.width)
                         for y in range(local_map.height)
                         if x in (0, local_map.width - 1) or y in (0, local_map.height - 1)))
    seen = {p for p in seen if enterable(*p)}
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = x + dx, y + dy
                if local_map.in_bounds(*p) and p not in seen and enterable(*p):
                    seen.add(p)
                    queue.append(p)
    return seen


def edge_cells(m, edge, kind='road'):
    values = {'north': m.tiles['terrain'][:, 0], 'south': m.tiles['terrain'][:, -1],
              'west': m.tiles['terrain'][0, :], 'east': m.tiles['terrain'][-1, :]}[edge]
    return {i for i, t in enumerate(values)
            if (str(t).startswith('road_') if kind == 'road' else str(t) == 'river_water')}


class GenerationG1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='resonance-g1-')
        self.addCleanup(temp.cleanup)
        self.save_root = Path(temp.name)
        save_patch = patch('engine.save_manager.SAVE_DIR', self.save_root)
        save_patch.start()
        self.addCleanup(save_patch.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def town_engine(self):
        e = make_engine(self.data)
        e.world_map.width = 2
        e.world_map.set(Chunk(1, 0, RegionType.TOWN, 29417, town_id=1, town_role='N'))
        e.player.x, e.player.y = 79, 12
        return e

    def test_first_creator_preserves_native_town_contents(self):
        rows = []
        for creature_first in (False, True):
            e = self.town_engine()
            if creature_first:
                actor = e.creature_factory.spawn('hollow_revenant', 79, 12)
                actor.ai.state = AIState.HUNTING
                actor._last_known_px, actor._last_known_py = 79, 12
                e.entities.append(actor)
                e._check_entity_chunk_crossings()
                self.assertNotIn(actor, e.entities)
            e._transition_chunk(1, 0)
            self.assertEqual((e.world_x, e.world_y), (1, 0))
            rows.append((len(e.entities) - 1 - int(creature_first),
                         len(e.local_map.container_state),
                         sum(map(len, e.local_map.floor_objects.values()))))
        self.assertGreater(min(rows[0]), 0)
        self.assertEqual(rows[0], rows[1])

    def test_bsp_repeats_same_seed(self):
        maps = [generate_dungeon(80, 43, self.data.terrain, seed=29417) for _ in range(3)]
        for m, start in maps[1:]:
            self.assertEqual(maps[0][1], start)
            self.assertTrue((maps[0][0].tiles['terrain'] == m.tiles['terrain']).all(),
                            'same-seed BSP terrain differs')

    def test_normal_town_travel_materializes_scene(self):
        e = self.town_engine()
        building = {'id': 'g1_meal', 'layers': ['.....'] * 5,
                    'legend': {'.': 'floor'}, 'special_tiles': [
                        {'type': 'scene', 'scene_id': 'interrupted_meal', 'x': 2, 'y': 2}]}
        with patch.object(self.data, 'buildings', {'residential': [building]}):
            e._transition_chunk(1, 0)
        specs = [s for s in e.world_map.get(1, 0).town_data.item_spawns if s['kind'] == 'scene']
        self.assertTrue(specs)
        expected = sorted(s['item_id'] for s in self.data.scenes['interrupted_meal']['floor_objects'])
        for s in specs:
            self.assertEqual(expected, sorted(i.item_id for i in e.local_map.floor_objects.get((s['x'], s['y']), [])))

    def test_repaired_house_notes_reachable_in_both_transforms(self):
        for category, bid in [('residential', 'hovel'), ('wilderness', 'hunter_cabin')]:
            b = next(b for b in self.data.buildings[category] if b['id'] == bid)
            for flip in (False, True):
                with self.subTest(building=bid, flip=flip):
                    m = _generate_town_base(30, 25, self.data.terrain)
                    specs = _stamp_building_at(m, b, 5, 5, self.data.terrain, flip_v=flip)
                    notes = [s for s in specs if s.get('text_id')]
                    self.assertTrue(notes)
                    access = reachable(m, self.data)
                    self.assertTrue(all((s['x'], s['y']) in access for s in notes))

    def test_road_port_position_is_consumed(self):
        mouths = []
        for position in (0.1, 0.9):
            c = Chunk(0, 0, RegionType.PLAINS, 77123)
            for edge in ('west', 'east'):
                c.add_connector(edge, ConnectorType.ROAD, position)
            m, _ = generate_region(c, 80, 43, self.data.terrain, data=self.data)
            mouths.append(edge_cells(m, 'west'))
        self.assertTrue(all(mouths))
        self.assertLess(max(mouths[0]), min(mouths[1]))

    def test_debug_travel_reuses_modified_active_scene(self):
        e = self.town_engine()
        e._transition_chunk(1, 0)
        m = e.local_map
        m.set_tile(3, 3, 'mud', True, True)
        m.floor_objects.clear()
        m.container_state.clear()
        e.overmap_cursor_x, e.overmap_cursor_y = 1, 0
        e._teleport_to_overmap_cursor()
        self.assertIs(e.local_map, m)
        self.assertFalse(e.local_map.floor_objects)
        self.assertFalse(e.local_map.container_state)


if __name__ == '__main__':
    unittest.main()
