"""Bounded real-world ports, all 36 town chunks, stairs, and WFC diagnostics."""
from __future__ import annotations
from collections import deque
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from test_effect_persistence import load_data, GAME_ROOT
from test_generation_g1 import reachable, edge_cells
from generation.context import GenerationError
from generation.world_gen import generate_world
from generation.region_gen import generate_region, _place_submap_entrance
from generation.ports import OFFSETS, OPPOSITE, mouth
from generation.wfc import WFCSolver
from engine.scene_generation import create_surface
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from world.world_map import WorldMap, Chunk, RegionType, ConnectorType, SubMap
from world.local_map import LocalMap, make_tile


class GenerationGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.worlds, cls.scenes = {}, {}
        with contextlib.redirect_stdout(io.StringIO()):
            for seed in (20261020, 20261023):
                world = WorldMap(128, 128)
                world.seed = seed
                generate_world(world, cls.data, random.Random(seed))
                cls.worlds[seed] = world
            world = cls.worlds[20261020]
            for xy in sorted(world.town_chunks):
                cls.scenes[xy] = create_surface(world, world.get(*xy), cls.data, ItemFactory(cls.data),
                                                CreatureFactory(cls.data), 80, 43)

    def test_new_world_connectors_are_reciprocal_without_changing_scale(self):
        for world in self.worlds.values():
            self.assertEqual((world.width, world.height, len(world.chunks)), (128, 128, 16384))
            self.assertTrue(all(0 <= c.seed <= 999999 for c in world.chunks.values()))
            counts = {ConnectorType.ROAD: 0, ConnectorType.RIVER: 0}
            for (wx, wy), chunk in world.chunks.items():
                for edge, (dx, dy) in OFFSETS.items():
                    other = world.get(wx + dx, wy + dy)
                    for port in chunk.edges[edge]:
                        if port.connector_type not in counts: continue
                        self.assertIsNotNone(other)
                        self.assertTrue(any(p.connector_type == port.connector_type and
                                            p.position == port.position and p.width == port.width
                                            for p in other.edges[OPPOSITE[edge]]),
                                        (world.seed, wx, wy, edge, port))
                        counts[port.connector_type] += 1
            self.assertTrue(all(counts.values()))

    def test_exact_nonriver_mountain_seam_and_inward_road_corridor(self):
        world = self.worlds[20261020]
        maps = [generate_region(copy.deepcopy(world.get(*xy)), 80, 43, self.data.terrain, self.data)[0]
                for xy in [(65, 73), (65, 74)]]
        a, b = edge_cells(maps[0], 'south'), edge_cells(maps[1], 'north')
        self.assertTrue(a)
        self.assertEqual(a, b)
        for m in maps:
            self.assertTrue(m.road_cells)
            seen = connected(m.road_cells, min(m.road_cells))
            self.assertEqual(seen, m.road_cells)
            self.assertTrue(all(str(m.tiles[p]['terrain']).startswith('road_') for p in m.road_cells))

    def test_constructed_ports_consume_width_position_and_axis(self):
        for kind, width in [(ConnectorType.ROAD, 3), (ConnectorType.RIVER, 9)]:
            for edge in ('east', 'south'):
                for position in (0.1, 0.9):
                    maps = []
                    for seed, side in [(47, edge), (991, OPPOSITE[edge])]:
                        c = Chunk(4, 5, RegionType.PLAINS, seed)
                        c.add_connector(side, kind, position, width=width)
                        m, _ = generate_region(c, 80, 43, self.data.terrain, self.data)
                        maps.append((m, side))
                    masks = [edge_cells(m, side, kind.value) for m, side in maps]
                    self.assertEqual(len(masks[0]), width)
                    self.assertEqual(masks[0], masks[1])
                    for m, side in maps:
                        for depth in range(3):
                            self.assertTrue(all(p in getattr(m, kind.value + '_cells')
                                                for p in mouth(side, position, width, 80, 43, depth)))

    def test_river_ford_retains_player_and_creature_semantics(self):
        c = Chunk(4, 5, RegionType.PLAINS, 47)
        for edge in ('west', 'east'): c.add_connector(edge, ConnectorType.RIVER, 0.5, width=9)
        for edge in ('north', 'south'): c.add_connector(edge, ConnectorType.ROAD, 0.5, width=3)
        m, _ = generate_region(c, 80, 43, self.data.terrain, self.data)
        crossing = m.road_cells & m.river_cells
        self.assertTrue(crossing)
        water = [p for p in crossing if str(m.tiles[p]['terrain']) == 'river_water']
        self.assertTrue(water)
        self.assertTrue(all(m.walkable[p] for p in crossing))
        self.assertFalse(self.data.terrain['river_water']['creature_passable'])

    def test_every_town_through_band_has_reciprocal_inward_street(self):
        world = self.worlds[20261020]
        self.assertEqual(len(self.scenes), 36)
        for xy, scene in self.scenes.items():
            m = scene.local_map
            actual = {p for p in m.street_cells if str(m.tiles[p]['terrain']) in
                      ('cobblestone', 'flagstone', 'dirt_path', 'road_0', 'town_plaza', 'worn_stone', 'door_closed',
                       'cobblestone_cracked', 'cobblestone_mossy')}
            # Plaza objects may replace individual street cells, but every mouth
            # must still connect inward to the same real street network.
            components = []
            remaining = set(actual)
            while remaining:
                component = connected(remaining, min(remaining))
                components.append(component)
                remaining -= component
            main = max(components, key=len)
            for edge, (dx, dy) in OFFSETS.items():
                border = border_positions(m.street_cells, edge, m.width, m.height)
                self.assertTrue(all(p in main for p in border_points(border, edge, m.width, m.height)), (xy, edge))
                neighbour_xy = xy[0] + dx, xy[1] + dy
                if neighbour_xy in self.scenes:
                    other = self.scenes[neighbour_xy].local_map
                    reverse = border_positions(other.street_cells, OPPOSITE[edge], other.width, other.height)
                    self.assertEqual(border, reverse, (xy, edge, neighbour_xy))
                elif border:
                    other, _ = generate_region(copy.deepcopy(world.get(*neighbour_xy)), 80, 43, self.data.terrain, self.data)
                    reverse = border_positions(other.road_cells, OPPOSITE[edge], 80, 43)
                    self.assertEqual(border, reverse, (xy, edge, neighbour_xy))

    def test_repaired_assets_remain_selected_accessible_without_overlaps(self):
        counts = {'hovel': 0, 'hunter_cabin': 0}
        for scene in self.scenes.values():
            m, td = scene.local_map, scene.metadata.town_data
            access = reachable(m, self.data)
            occupied = set()
            for b in td.buildings:
                footprint = {(x, y) for x in range(b['x'], b['x'] + b['w']) for y in range(b['y'], b['y'] + b['h'])}
                self.assertFalse(occupied & footprint)
                occupied |= footprint
                if b['id'] in counts:
                    counts[b['id']] += 1
                    for spec in b['item_specs']:
                        if spec.get('text_id'):
                            xy = spec['x'], spec['y']
                            self.assertIn(xy, access)
                            self.assertTrue(any(i.text_id == spec['text_id'] for i in m.floor_objects[xy]))
        self.assertTrue(all(counts.values()), counts)

    def test_centre_bell_state_matches_physical_bell_before_population(self):
        for xy, scene in self.scenes.items():
            td = scene.metadata.town_data
            if scene.metadata.town_role == 'C':
                self.assertEqual(td.bell_state, 'cracked')
                self.assertEqual(scene.local_map.decor[td.bell_tower_pos], 'cracked_bell')
            else:
                self.assertEqual(td.bell_state, 'spent')
                self.assertFalse(any(a._creature_id == 'hollow_knight' for a in scene.actors))

    def test_no_plaza_has_no_fabricated_bell_or_guardian(self):
        world = self.worlds[20261020]
        chunk = next(c for c in world.chunks.values() if c.town_role == 'C')
        with patch('generation.town_gen.BuildingLoader.pick_plaza', return_value=None):
            result = create_surface(world, chunk, self.data, ItemFactory(self.data), CreatureFactory(self.data), 80, 43)
        self.assertEqual(result.metadata.town_data.bell_state, 'missing')
        self.assertFalse(any('bell' in d for d in result.local_map.decor.values()))
        self.assertFalse(any(a._creature_id == 'hollow_knight' for a in result.actors))

    def test_actual_placed_notes_have_legal_actions(self):
        from test_generation_ownership import action_path
        from test_effect_persistence import make_engine
        from engine.engine import MOVE_KEYS
        from engine.interaction_cursor import InteractionCursor
        import pygame
        import tempfile
        visited = set()
        with tempfile.TemporaryDirectory(prefix='resonance-g1-access-') as root, patch('engine.save_manager.SAVE_DIR', Path(root)):
            for scene in self.scenes.values():
                for b in scene.metadata.town_data.buildings:
                    if b['id'] not in ('hovel', 'hunter_cabin') or b['id'] in visited:
                        continue
                    e = make_engine(self.data)
                    e.local_map = copy.deepcopy(scene.local_map)
                    e.player.x, e.player.y = 0, 0
                    note = next(s for s in b['item_specs'] if s.get('text_id'))
                    path = action_path(e, (0, 0), (note['x'], note['y']))
                    self.assertIsNotNone(path)
                    for xy in path[1:]:
                        delta = xy[0] - e.player.x, xy[1] - e.player.y
                        key = next(k for k, d in MOVE_KEYS.items() if d == delta)
                        if str(e.local_map.tiles[xy]['terrain']) == 'door_closed': e._handle_key_local(key)
                        e._handle_key_local(key)
                        self.assertEqual((e.player.x, e.player.y), xy)
                    e._handle_key_local(pygame.K_COMMA)
                    item = next(i for i in e.player.inventory.items if i.text_id == note['text_id'])
                    e.item_system.use(item, e)
                    self.assertTrue(e.text_reader.open)
                    visited.add(b['id'])
        self.assertEqual(visited, {'hovel', 'hunter_cabin'})

    def test_generated_market_crate_has_legal_approach_and_transfer(self):
        from test_generation_ownership import action_path
        from test_effect_persistence import make_engine
        from engine.engine import MOVE_KEYS, GameMode
        from engine.interaction_cursor import InteractionCursor
        import pygame
        import tempfile
        matches = [(scene, b) for scene in self.scenes.values()
                   for b in scene.metadata.town_data.buildings if b['id'] == 'market_stall_a']
        self.assertTrue(matches, 'real generated market fixture must exist')
        scene, building = matches[0]
        with tempfile.TemporaryDirectory(prefix='resonance-g1-crate-') as root, patch('engine.save_manager.SAVE_DIR', Path(root)):
            e = make_engine(self.data)
            e.local_map = copy.deepcopy(scene.local_map)
            spec = next(s for s in building['item_specs'] if s['kind'] == 'container')
            target = spec['x'], spec['y']
            container = e.local_map.container_state[target]
            self.assertTrue(self.data.decoratives[container['decor_id']]['blocks_movement'])
            self.assertTrue(container['items'])
            self.assertIsNone(action_path(e, (0, 0), target))
            routes = [action_path(e, (0, 0), (target[0] + dx, target[1] + dy))
                      for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0))]
            routes = [route for route in routes if route]
            self.assertTrue(routes, 'blocking crate needs a legal interaction approach')
            e.player.x, e.player.y = 0, 0
            for xy in min(routes, key=len)[1:]:
                delta = xy[0] - e.player.x, xy[1] - e.player.y
                key = next(k for k, d in MOVE_KEYS.items() if d == delta)
                if str(e.local_map.tiles[xy]['terrain']) == 'door_closed': e._handle_key_local(key)
                e._handle_key_local(key)
                self.assertEqual((e.player.x, e.player.y), xy)
            self.assertTrue(InteractionCursor.can_reach(e, *target))
            e.mode = GameMode.INTERACTION_CURSOR
            e.interaction_cursor._cursor_x, e.interaction_cursor._cursor_y = target
            e.interaction_cursor.candidates = [target]
            e._handle_key(pygame.K_RETURN)
            self.assertIsNotNone(e.interaction_cursor._selection_prompt)
            item = container['items'][0]
            e._handle_key(pygame.K_RETURN)
            self.assertIn(item, e.player.inventory.items)
            self.assertNotIn(item, container['items'])

    def test_impossible_entrance_cannot_mutate_map_or_metadata(self):
        m = LocalMap(20, 14)
        m.tiles[:] = make_tile('floor', True, True)
        m.protected_cells = {(x, y) for x in range(20) for y in range(14)}
        before = m.tiles.tobytes()
        sm = SubMap('impossible', 'cave', 'Cave', 3)
        with self.assertRaisesRegex(GenerationError, 'no valid entrance'):
            _place_submap_entrance(m, sm, self.data.terrain, data=self.data)
        self.assertEqual(before, m.tiles.tobytes())
        self.assertFalse(m.submap_links)
        self.assertEqual((sm.surface_x, sm.surface_y, sm.generated), (0, 0, False))

    def test_entrance_respects_objects_and_uses_valid_fallback(self):
        m = LocalMap(24, 18)
        m.tiles[:] = make_tile('floor', True, True)
        item = ItemFactory(self.data).create('flint_shard')
        from generation.floor_object_utils import place_floor_object, place_container
        place_floor_object(m, 11, 8, item)
        place_container(m, 12, 8, 'crate', [])
        m.decor[13, 8] = 'waystone_plinth'
        m.submap_links[10, 8] = 'existing'
        m.set_tile(10, 8, 'stairs_down', True, True)
        sm = SubMap('second', 'cave', 'Cave', 3)
        huge = dict(id='impossible-sized', layers=['#' * 80] * 43, legend={'#': 'wall'})
        with patch('generation.entrance_gen._pick_layout', return_value=huge):
            _place_submap_entrance(m, sm, self.data.terrain, data=self.data)
        self.assertIs(m.floor_objects[11, 8][0], item)
        self.assertEqual(m.decor[13, 8], 'waystone_plinth')
        self.assertEqual(m.submap_links[10, 8], 'existing')
        self.assertEqual(m.submap_links[sm.surface_x, sm.surface_y], 'second')
        self.assertEqual(str(m.tiles[sm.surface_x, sm.surface_y]['terrain']), 'stairs_down')
        self.assertEqual(m.generation_diagnostics[-1]['status'], 'bare-stair-fallback')

    def test_outskirts_seeds_zero_to_nine_are_bounded_and_reported_separately(self):
        rows = []
        for seed in range(10):
            solver = WFCSolver.from_json(str(GAME_ROOT / 'data/wfc/town_outskirts.json'), random.Random(seed))
            grid = solver.solve(74, 37)
            if grid is not None: self.assertTrue(solver.valid(grid, 74, 37))
            rows.append(dict(seed=seed, status='solved' if grid is not None else 'fallback', attempts_bound=solver.MAX_ATTEMPTS))
        target = os.getenv('RESONANCE_TEST_EVIDENCE_DIR')
        if target:
            Path(target, 'wfc-outskirts.json').write_text(json.dumps(rows, indent=2))

    def test_full_authored_entrance_preserves_objects_and_their_approaches(self):
        m = LocalMap(30, 24)
        m.tiles[:] = make_tile('floor', True, True)
        item = ItemFactory(self.data).create('flint_shard')
        from generation.floor_object_utils import place_floor_object, place_container
        place_floor_object(m, 8, 8, item)
        place_container(m, 9, 8, 'crate', [])
        preserved = {(x, y): str(m.tiles[x, y]['terrain']) for x in range(7, 11) for y in range(7, 10)}
        layout = dict(id='g1-full-footprint', layers=['#####', '#...#', '#.>.#', '#...#', '##+##'],
                      legend={'#':'wall', '.':'floor', '>':'stairs_down', '+':'door_closed'})
        sm = SubMap('full', 'cave', 'Cave', 3)
        with patch('generation.entrance_gen._pick_layout', return_value=layout):
            _place_submap_entrance(m, sm, self.data.terrain, data=self.data)
        self.assertFalse(getattr(m, 'generation_diagnostics', []))
        self.assertIs(m.floor_objects[8, 8][0], item)
        self.assertEqual(preserved, {p: str(m.tiles[p]['terrain']) for p in preserved})
        self.assertEqual(m.submap_links[sm.surface_x, sm.surface_y], 'full')
        self.assertIn((sm.surface_x, sm.surface_y), reachable(m, self.data))


def connected(cells, start):
    seen, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = x + dx, y + dy
            if p in cells and p not in seen:
                seen.add(p)
                queue.append(p)
    return seen


def border_positions(cells, edge, w, h):
    if edge == 'north': return {x for x, y in cells if y == 0}
    if edge == 'south': return {x for x, y in cells if y == h - 1}
    if edge == 'west': return {y for x, y in cells if x == 0}
    return {y for x, y in cells if x == w - 1}


def border_points(values, edge, w, h):
    for a in values:
        yield {'north': (a, 0), 'south': (a, h - 1), 'west': (0, a), 'east': (w - 1, a)}[edge]
