"""G1 complete native content, deterministic generation, and staged failures."""
from __future__ import annotations
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_effect_persistence import load_data, make_engine, GAME_ROOT
from g1_support import fingerprint
from generation.context import GenerationContext, GenerationError
from generation.region_gen import _generate_town_base
from generation.town_gen import _stamp_building_at, _apply_wfc_fill
from generation.local_gen import generate_submap
from generation.layout_stamper import stamp_layout, stamp_layout_interior
from generation.wfc import WFCSolver
from engine.scene_generation import populate
from world.world_map import Chunk, RegionType
from world.local_map import LocalMap, make_tile
from components.ai import AIState


class GenerationContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='resonance-g1-content-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        saver = patch('engine.save_manager.SAVE_DIR', self.root)
        saver.start()
        self.addCleanup(saver.stop)
        capture = contextlib.redirect_stdout(io.StringIO())
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)
        self.e = make_engine(self.data)

    def destination(self, kind=RegionType.TOWN):
        e = self.e
        e.world_map.width = 3
        c = Chunk(1, 0, kind, 29417, town_id=1 if kind == RegionType.TOWN else -1,
                  town_role='N' if kind == RegionType.TOWN else '', zones=[('deepwood', 1)])
        e.world_map.set(c)
        return c

    def test_all_four_scenes_use_actual_adapter(self):
        for index, (scene_id, scene) in enumerate(self.data.scenes.items()):
            x, y = 3 + index, 4
            self.e._spawn_layout_entities([dict(kind='scene', scene_id=scene_id, x=x, y=y)])
            self.assertEqual([r['item_id'] for r in scene['floor_objects']],
                             [i.item_id for i in self.e.local_map.floor_objects[x, y]])
        self.assertEqual(len(self.data.scenes), 4)

    def test_weighted_choices_and_transforms_are_exactly_once(self):
        e = self.e
        choices = [dict(type='item', item_id='flint_shard'),
                   dict(type='container', decor_id='crate', loot_pools=['storage_tools']),
                   dict(type='scene', scene_id='interrupted_meal'), dict(type='empty')]
        for choice in choices:
            for flip in (False, True):
                m = _generate_town_base(20, 20, self.data.terrain)
                b = dict(id='weighted_fixture', layers=['.....'] * 5, legend={'.': 'floor'},
                         special_tiles=[dict(type='weighted', x=1, y=1, spawn_table=[choice])])
                original = copy.deepcopy(b)
                specs = _stamp_building_at(m, b, 4, 5, self.data.terrain, flip_v=flip)
                e._spawn_layout_entities(specs, local_map=m)
                self.assertEqual(b, original)
                xy = (5, 8 if flip else 6)
                self.assertEqual(set(m.floor_objects) | set(m.container_state),
                                 set() if choice['type'] == 'empty' else {xy})
                if choice['type'] == 'scene':
                    self.assertEqual([i.item_id for i in m.floor_objects[xy]], ['dried_provisions', 'water_skin'])

    def test_malformed_content_has_diagnostics_and_no_partial_objects(self):
        bad = [dict(kind='weighted', spawn_table=[]),
               dict(kind='weighted', spawn_table=[dict(type='empty', weight=0)]),
               dict(kind='weighted', spawn_table=[dict(type='empty', weight=float('nan'))]),
               dict(kind='weighted', spawn_table=[dict(type='body')]),
               dict(kind='weighted', spawn_table=[dict(type='weighted')]),
               dict(kind='item', item_id='missing_g1'), dict(kind='scene', scene_id='missing_g1'),
               dict(kind='container', loot_pools=['missing_g1']), dict(kind='surprise')]
        for spec in bad:
            with self.subTest(spec=spec):
                m = self.e.local_map
                before = fingerprint(m, [])
                with self.assertRaisesRegex(GenerationError, 'fixture.*'):
                    self.e._spawn_layout_entities([dict(kind='item', item_id='flint_shard', x=2, y=2),
                                                  dict(spec, x=3, y=3, source='fixture special[1]')])
                self.assertEqual(before, fingerprint(m, []))
        m.set_tile(4, 4, 'wall', False, False)
        with self.assertRaisesRegex(GenerationError, 'anchor'):
            self.e._spawn_layout_entities([dict(kind='scene', scene_id='interrupted_meal', x=4, y=4)])

    def test_actual_lab_weighted_table_and_deferred_records(self):
        sm = self.e.world_map.get(0, 0).add_submap('laboratory', 'Lab', 29417, 'starting_lab')
        m, specs = generate_submap(sm, 80, 43, self.data.terrain)
        weighted = [s for s in specs if s['source'] == 'starting_lab special[16]']
        # Locate the actual authored weighted index, without relying on a statistical roll.
        layout = json.loads((GAME_ROOT / 'data/layouts/starting_lab.json').read_text())
        index = next(i for i, s in enumerate(layout['special_tiles']) if s['type'] == 'weighted')
        spec = next(s for s in specs if s['source'] == f'starting_lab special[{index}]')
        self.e._spawn_layout_entities(specs, local_map=m)
        values = m.floor_objects.get((spec['x'], spec['y']), [])
        self.assertEqual(len(values), 0 if spec['kind'] == 'empty' else 1)
        if values:
            self.assertEqual(values[0].item_id, spec['item_id'])
        self.assertTrue(any(r['kind'] == 'body' for r in m.deferred_generation_records))
        self.assertTrue(m.stele_text_ids)

    def test_population_failure_preserves_metadata_player_and_migrant_then_retry(self):
        e = self.e
        c = self.destination()
        actor = e.creature_factory.spawn('hollow_revenant', 79, 12)
        actor.ai.state = AIState.HUNTING
        actor._last_known_px, actor._last_known_py = 79, 12
        e.entities.append(actor)
        e.player.x, e.player.y = 79, 12
        original = e.local_map
        with patch('engine.scene_generation.populate', side_effect=GenerationError('injected population failure')):
            e._check_entity_chunk_crossings()
            e._transition_chunk(1, 0)
        self.assertIs(e.local_map, original)
        self.assertIn(actor, e.entities)
        self.assertEqual((actor.x, actor.y), (79, 12))
        self.assertIsNone(c.town_data)
        self.assertFalse(e.save_manager.cache.has(1, 0))
        e._check_entity_chunk_crossings()
        self.assertNotIn(actor, e.entities)
        e._transition_chunk(1, 0)
        self.assertTrue(e.local_map.generation_complete)
        self.assertGreater(len(e.local_map.container_state), 0)

    def test_active_map_precedes_stale_cache(self):
        e = self.e
        stale = copy.deepcopy(e.local_map)
        stale.set_tile(4, 4, 'mud', True, True)
        e.save_manager.cache.store(0, 0, stale, [])
        actor = e.creature_factory.spawn('hollow_revenant', 5, 5)
        e.entities.append(actor)
        m, actors = e._ensure_surface_scene(0, 0)
        self.assertIs(m, e.local_map)
        self.assertEqual(actors, [actor])

    def test_loot_stream_ignores_gameplay_and_other_decoration(self):
        maps = []
        for draws in (0, 1000):
            e = make_engine(self.data)
            for _ in range(draws): e.rng.random()
            m = _generate_town_base(20, 20, self.data.terrain, context=GenerationContext(5, 9, (1, 2, None)))
            specs = [dict(kind='container', x=6, y=6, decor_id='crate', loot_pools=['storage_tools'])]
            if draws:
                specs.insert(0, dict(kind='item', x=7, y=7, item_id='flint_shard'))
            e._spawn_layout_entities(specs, local_map=m)
            from engine.save_components import serialize_item
            maps.append([serialize_item(i) for i in m.container_state[6, 6]['items']])
        self.assertEqual(maps[0], maps[1])

    def test_weighted_entrance_both_consumers_repeat(self):
        layout = dict(id='weighted_entrance', layers=['xxx', 'x>x', 'xxx'], legend={'>': 'stairs_down'},
                      legend_weights={'x': [dict(tile='floor', weight=2), dict(tile='gravel', weight=1)]},
                      connection_point=dict(x=1, y=0), spawn_offset=dict(x=1, y=1))
        for interior in (False, True):
            rows = []
            for _ in range(2):
                m = LocalMap(20, 20, GenerationContext(5, 8, (1, 2, None)))
                if interior:
                    start = stamp_layout_interior(m, layout, 10, 10, self.data.terrain, rng=random.Random(45))
                else:
                    start = stamp_layout(m, layout, 'north', 0.5, self.data.terrain, rng=random.Random(45))
                rows.append((start, fingerprint(m, [])))
            self.assertEqual(rows[0], rows[1])

    def test_wfc_failure_and_exception_fallback_preserve_protected_cells(self):
        path = str(GAME_ROOT / 'data/wfc/town_block.json')
        for result in (None, RuntimeError('forced solver failure')):
            m = _generate_town_base(12, 12, self.data.terrain)
            m.set_tile(3, 3, 'stairs_down', True, True)
            m.submap_links[3, 3] = 'protected'
            m.protected_cells = {(4, 4)}
            before = str(m.tiles[4, 4]['terrain'])
            kwargs = dict(side_effect=result) if isinstance(result, Exception) else dict(return_value=None)
            with patch.object(WFCSolver, 'solve', **kwargs):
                _apply_wfc_fill(m, self.data.terrain, random.Random(0), path, (0, 0, 12, 12), {}, 'packed_earth')
            self.assertEqual(str(m.tiles[3, 3]['terrain']), 'stairs_down')
            self.assertEqual(str(m.tiles[4, 4]['terrain']), before)
            self.assertEqual(str(m.tiles[5, 5]['terrain']), 'packed_earth')
            self.assertEqual(m.generation_diagnostics[-1]['status'], 'fallback')
            self.assertTrue(m.generation_diagnostics[-1]['reason'])

    def test_successful_wfc_obeys_adjacency(self):
        solver = WFCSolver.from_json(str(GAME_ROOT / 'data/wfc/town_block.json'), random.Random(4))
        grid = solver.solve(8, 8)
        self.assertIsNotNone(grid)
        self.assertTrue(solver.valid(grid, 8, 8))

    def test_fresh_hashseed_order_and_gameplay_matrix(self):
        results = []
        for seed in ('1', '2'):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(GAME_ROOT))
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--fingerprint'],
                                    env=env, cwd=GAME_ROOT, capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stderr)
            results.append(json.loads(result.stdout))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0], results[0][1])


def process_fingerprints():
    rows = []
    with contextlib.redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory(prefix='resonance-g1-hash-') as root:
        data = load_data()
        for order in ((1, 2), (2, 1)):
            with patch('engine.save_manager.SAVE_DIR', Path(root) / str(order[0])):
                e = make_engine(data)
                e.world_map.width = 3
                e.world_map.set(Chunk(1, 0, RegionType.TOWN, 29417, town_id=1, town_role='N'))
                e.world_map.set(Chunk(2, 0, RegionType.FOREST, 77123,
                                     zones=[('deepwood', .6), ('briarwood', .3), ('mere', .1)]))
                row = {}
                for x in order:
                    for _ in range(order[0] * 127): e.rng.random()
                    m, actors = e._ensure_surface_scene(x, 0)
                    assert actors, 'native population fixture must be nonempty'
                    row[str(x)] = fingerprint(m, actors, e.world_map.get(x, 0).town_data)
                for layout in ('starting_lab', ''):
                    sm = e.world_map.get(2, 0).add_submap('barrow', 'Fixture', 29417, layout)
                    m, actors = e._ensure_submap_scene(2, 0, sm.submap_id)
                    row['submap-' + layout] = fingerprint(m, actors)
                rows.append(row)
    print(json.dumps(rows, sort_keys=True))


if __name__ == '__main__':
    if '--fingerprint' in sys.argv:
        process_fingerprints()
    else:
        unittest.main()
