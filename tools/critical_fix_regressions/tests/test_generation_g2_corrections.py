"""G2 corrective contracts, real runtime adapters and disposable saves only."""
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
from generation.context import GenerationContext, GenerationError, GENERATION_REVISION
from generation.ports import mouth, town_ports, resolve_mouth, OPPOSITE
from generation.feature_carving import carve_feature, reserve_town_routes
from generation.region_gen import _place_submap_entrance
from engine.scene_generation import validate_scene
from world.local_map import LocalMap, make_tile
from world.world_map import Chunk, RegionType, SubMap, EdgeConnector, ConnectorType


class G2Corrections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def test_debug_departure_failed_same_address_and_saved_encounter(self):
        with tempfile.TemporaryDirectory() as root, patch('engine.save_manager.SAVE_DIR', Path(root)), contextlib.redirect_stdout(io.StringIO()):
            e = make_engine(self.data)
            e.world_map.width = 2
            e.world_map.set(Chunk(1, 0, RegionType.PLAINS, 77123))
            center = e.local_map.width // 2, e.local_map.height // 2
            e.player.x, e.player.y = center
            a = e.creature_factory.spawn('bog_wraith', center[0]+1, center[1])
            e.entities.append(a)
            for _ in range(4): e._update_wraith_aura()
            e._wraith_overcorrect_turns = 2
            e.local_map.set_tile(2, 3, 'flagstone', True, True)
            self.assertTrue(e.save_manager.save(e))
            head = e.save_manager.save_path / 'HEAD.json'
            saved_head, turn = head.read_bytes(), e.world_time.turn
            e.overmap_cursor_x = e.overmap_cursor_y = 0
            e._teleport_to_overmap_cursor()
            self.assertEqual(a._wraith_exposure_turns, 4)
            self.assertEqual(e._wraith_overcorrect_turns, 2)
            e.overmap_cursor_x = 1
            with patch.object(e, '_ensure_surface_scene', side_effect=GenerationError('bad candidate')):
                e._teleport_to_overmap_cursor()
            self.assertEqual((e.world_x, a._wraith_exposure_turns), (0, 4))
            self.assertEqual(e._wraith_overcorrect_turns, 2)
            e._teleport_to_overmap_cursor()
            self.assertEqual(a._wraith_exposure_turns, 0)
            self.assertEqual(e._wraith_overcorrect_turns, 0)
            cached = e.save_manager.cache.load(0, 0)
            row = next(a for a in cached.entities if a.get('tile') == 'bog_wraith')
            self.assertEqual(row['component_state']['actor']['_wraith_exposure_turns'], 0)
            e.overmap_cursor_x = 0
            e._teleport_to_overmap_cursor()
            actors = [a for a in e.entities if getattr(a, '_creature_id', '') == 'bog_wraith']
            self.assertEqual(len(actors), 1)
            self.assertEqual(actors[0]._wraith_exposure_turns, 0)
            self.assertEqual(str(e.local_map.tiles[2, 3]['terrain']), 'flagstone')
            self.assertEqual(e.world_time.turn, turn)
            self.assertEqual(head.read_bytes(), saved_head)
            self.assertTrue(e.save_manager.load(e))
            restored = [a for a in e.entities if getattr(a, '_creature_id', '') == 'bog_wraith']
            self.assertEqual([a._wraith_exposure_turns for a in restored], [4])
            self.assertEqual(e._wraith_overcorrect_turns, 2)

    def test_checker_shared_container_defaults(self):
        example = GAME_ROOT / 'docs/examples/author_cottage_a.json'
        with tempfile.TemporaryDirectory() as root:
            for fields in ((), ('decor_id',), ('loot_pools',), ('decor_id', 'loot_pools')):
                doc = json.loads(example.read_text())
                container = next(s for s in doc['special_tiles'] if s['type'] == 'container')
                for key in fields: container.pop(key, None)
                if not fields: container['loot_pools'] = []
                candidate = Path(root) / 'cottage.json'
                candidate.write_text(json.dumps(doc))
                run = subprocess.run([sys.executable, '-X', 'utf8', str(example.with_name('validate_building.py')),
                                      '--game', str(GAME_ROOT), '--building', str(candidate)],
                                     capture_output=True, text=True, timeout=20, env=dict(os.environ))
                self.assertEqual(run.returncode, 0, (fields, run.stdout, run.stderr))

    def test_whole_mouth_axes_extremes_defaults_and_reciprocals(self):
        for kind, width in [('road', 3), ('river', 13), ('river', 9)]:
            for axis in ['east', 'south']:
                for position in [0, 0.5, 0.9, 1]:
                    masks = []
                    for edge in [axis, OPPOSITE[axis]]:
                        m = LocalMap(80, 43)
                        m.tiles[:] = make_tile('grass', True, True)
                        port = EdgeConnector(ConnectorType(kind), position, width=width)
                        cells = carve_feature(m, self.data.terrain, [(edge, port)], kind, random.Random(47))
                        border = set(mouth(edge, position, width, 80, 43))
                        actual = {p for p in cells if p[0] in (0,79) or p[1] in (0,42)}
                        self.assertEqual(actual, border)
                        self.assertEqual(len(border), width)
                        masks.append(sorted(p[1] if axis == 'east' else p[0] for p in border))
                        for d in range(4): self.assertTrue(set(mouth(edge, position, width, 80, 43, d)) <= cells)
                    self.assertEqual(*masks)
        for kind, default in [('road',3), ('river',9)]:
            for width in (None, 0):
                self.assertEqual(len(list(mouth('east', 0, width, 80, 43, kind=kind))), default)
        for width in (-1, 42, 200, 2.5, True):
            with self.assertRaises(GenerationError): resolve_mouth('east', .5, width, 80,43)
        for pos in (-.1, 1.1, float('nan'), float('inf'), True, '0.5'):
            with self.assertRaises(GenerationError): resolve_mouth('east', pos, 3, 80,43)

    def test_full_town_wilderness_port_lists_match(self):
        context = GenerationContext(47,47,(4,5,None))
        for position in (0,1):
            town = LocalMap(80,43)
            town.tiles[:] = make_tile('grass',True,True)
            c = Chunk(4,5,RegionType.TOWN,47,town_id=1,town_role='N')
            c.add_connector('west',ConnectorType.ROAD,position,width=3)
            reserve_town_routes(town,c,self.data.terrain,{(40,21)},context)
            bands=town_ports(context.world_seed,1,'N',80,43)['west']+[(position,3)]
            wild=LocalMap(80,43)
            wild.tiles[:]=make_tile('grass',True,True)
            carve_feature(wild,self.data.terrain,[('east',EdgeConnector(ConnectorType.ROAD,p,width=w)) for p,w in bands],'road',random.Random(91))
            self.assertEqual(sorted(y for x,y in town.road_cells if x==0),sorted(y for x,y in wild.road_cells if x==79))

    def test_pocket_and_final_content_block_fail_and_fallback_reaches_entry(self):
        m=LocalMap(24,18)
        m.tiles[:]=make_tile('wall',False,False)
        for p in [(0,0),(1,0),(10,6),(11,6)]: m.set_tile(*p,'floor',True,True)
        m.required_access_anchors=[(0,0)]
        s=SubMap('pocket','cave','Cave',3)
        with patch('generation.entrance_gen._pick_layout',return_value=None), self.assertRaises(GenerationError):
            _place_submap_entrance(m,s,self.data.terrain,self.data)
        m.set_tile(11,6,'stairs_down',True,True)
        m.submap_links[11,6]=s.submap_id
        s.surface_x,s.surface_y=11,6
        with self.assertRaises(GenerationError): validate_scene(m,[s],self.data)
        m.tiles[:]=make_tile('floor',True,True)
        m.submap_links.clear()
        with patch('generation.entrance_gen._pick_layout',return_value=None):
            _place_submap_entrance(m,s,self.data.terrain,self.data)
        validate_scene(m,[s],self.data)
        x,y=s.surface_x,s.surface_y
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx or dy: m.decor[x+dx,y+dy]='crate'
        with self.assertRaises(GenerationError): validate_scene(m,[s],self.data)
