"""Actual-source regression tests for wraith exposure and save reconstruction.

Run with the game's directory on PYTHONPATH. All checkpoints are created in
TemporaryDirectory roots; the game's shipped saves are never opened.
"""
from __future__ import annotations

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

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from components.corruption import Corruption
from components.equipment import Equipment
from components.fighter import Fighter
from components.inventory import Inventory
from components.language import Language
from components.level import LevelComponent
from components.needs import Needs
from components.perks import Perks
from engine.data_loader import DataLoader
from engine.display_config import DisplayConfig
from engine.engine import Engine
from engine.save_components import ACTOR_OPTIONAL_STATE, validate_actor_runtime
from engine.save_manager import _deserialize_entities, _serialize_entity
from entities.actor import Actor
from rendering.tile_registry import TileRegistry
from world.local_map import LocalMap, make_tile
from world.world_map import Chunk, RegionType, WorldMap

GAME_ROOT = Path(sys.modules[Engine.__module__].__file__).resolve().parents[1]


def load_data():
    with contextlib.redirect_stdout(io.StringIO()):
        return DataLoader(str(GAME_ROOT / "data"))


def make_engine(data):
    """Small authored fixture around the real components, factories and engine."""
    world = WorldMap(1, 1)
    world.seed = 29417
    world.start_wx = world.start_wy = 0
    world.set(Chunk(0, 0, RegionType.PLAINS, world.seed, visited=True))
    local_map = LocalMap()
    local_map.tiles[:] = make_tile("grass", True, True)
    player = Actor(12, 12, "player", "Player")
    player.fighter = Fighter(60, 5, 1)
    player.fighter.body_id = "body_player"
    player.inventory = Inventory(20.0)
    player.equipment = Equipment()
    player.needs = Needs()
    player.corruption = Corruption()
    player.language = Language()
    player.perks = Perks()
    player.level = LevelComponent()
    return Engine(player, local_map, [player],
                  TileRegistry(str(GAME_ROOT / "data/tiles.json")),
                  world, 0, 0, data, DisplayConfig.from_config())


def aura_state(engine):
    sources = sorted((a.x, a.y, getattr(a, "_wraith_exposure_turns", 0))
                     for a in engine.entities if a is not engine.player)
    return {"sources": sources, "radius": engine._effective_fov_radius,
            "turn": engine.world_time.turn,
            "dim_messages": sum(m.count for m in engine.log.messages
                                if m.text == "Sight dims.")}


class WraithPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="resonance-wraith-test-")
        self.addCleanup(self.temp.cleanup)
        self.save_root = Path(self.temp.name) / "saves"
        self.save_patch = patch("engine.save_manager.SAVE_DIR", self.save_root)
        self.save_patch.start()
        self.addCleanup(self.save_patch.stop)
        self.engine = make_engine(self.data)

    def add_wraith(self, x=14, y=12):
        actor = self.engine.creature_factory.spawn("bog_wraith", x, y)
        self.assertIsNotNone(actor)
        self.engine.entities.append(actor)
        return actor

    def expose(self, turns):
        for _ in range(turns):
            self.engine._update_wraith_aura()
        self.engine._update_fov()

    def seed_two_sources(self):
        first = self.add_wraith()
        self.expose(2)
        second = self.add_wraith(12, 14)
        self.expose(2)
        self.assertEqual([first._wraith_exposure_turns,
                          second._wraith_exposure_turns], [4, 2])
        self.assertEqual(self.engine._effective_fov_radius, 4)
        return first, second

    def test_full_same_process_load_preserves_each_source_and_immediate_fov(self):
        first, second = self.seed_two_sources()
        engine = self.engine
        expected = aura_state(engine)
        self.assertTrue(engine.save_manager.save(engine), engine.save_manager.last_error)
        first._wraith_exposure_turns = second._wraith_exposure_turns = 50
        engine._update_fov()
        self.assertTrue(engine.save_manager.load(engine), engine.save_manager.last_error)
        self.assertEqual(aura_state(engine), expected)
        self.assertNotIn(first, engine.entities)
        self.assertNotIn(second, engine.entities)
        # A redraw/repeated load is not a simulated turn or new exposure event.
        engine._update_fov()
        self.assertTrue(engine.save_manager.load(engine), engine.save_manager.last_error)
        self.assertEqual(aura_state(engine), expected)
        engine._advance_turn()
        self.assertEqual(engine.world_time.turn, expected["turn"] + 1)
        self.assertEqual(sorted(a._wraith_exposure_turns for a in engine.entities
                                if a is not engine.player), [3, 5])
        self.assertEqual(engine._effective_fov_radius, 2)

    def test_fresh_process_reader_restores_fov_without_replaying_exposure(self):
        self.seed_two_sources()
        engine = self.engine
        expected = aura_state(engine)
        self.assertTrue(engine.save_manager.save(engine), engine.save_manager.last_error)
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                 "--inspect-checkpoint", str(self.save_root)],
                                capture_output=True, text=True, timeout=30,
                                env=dict(os.environ))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        observed = json.loads(result.stdout.strip().splitlines()[-1])
        expected["dim_messages"] = 0  # message history is deliberately not saved
        self.assertEqual(observed, json.loads(json.dumps(expected)))

    def test_suppression_and_disruption_clear_exposure_without_advancing_time(self):
        actor = self.add_wraith()
        self.expose(4)
        turn = self.engine.world_time.turn
        actor._ability_suppressed_turns = 2
        self.engine._update_fov()
        self.assertEqual((actor._wraith_exposure_turns,
                          self.engine._wraith_aura_state,
                          self.engine.world_time.turn), (0, {}, turn))
        self.assertEqual(self.engine._effective_fov_radius, 40)
        self.assertTrue(self.engine.save_manager.save(self.engine))
        self.assertTrue(self.engine.save_manager.load(self.engine))
        actor = next(a for a in self.engine.entities if a is not self.engine.player)
        self.assertEqual((actor._ability_suppressed_turns,
                          actor._wraith_exposure_turns), (2, 0))
        actor._ability_suppressed_turns = 0
        self.expose(1)
        self.assertEqual(actor._wraith_exposure_turns, 1)
        self.engine.local_map.disruption_zones.append(
            dict(x=actor.x, y=actor.y, radius=1, turns_remaining=3))
        self.engine._update_fov()
        self.assertEqual(actor._wraith_exposure_turns, 0)
        self.assertEqual(self.engine._wraith_aura_state, {})

    def test_dead_distant_and_offscreen_sources_cannot_reapply_old_exposure(self):
        actor = self.add_wraith()
        self.expose(4)
        actor.x = 40
        self.engine._update_fov()
        self.assertEqual(actor._wraith_exposure_turns, 0)
        actor.x = 14
        self.expose(1)
        self.assertEqual(actor._wraith_exposure_turns, 1)
        self.engine.entities.remove(actor)
        self.engine._live_pursuers.append((actor, 0, 0, None))
        self.engine._update_fov()
        self.assertEqual((actor._wraith_exposure_turns,
                          self.engine._wraith_aura_state), (0, {}))
        self.engine._live_pursuers.clear()
        self.engine.entities.append(actor)
        self.expose(2)
        actor.is_alive = False
        self.engine._update_fov()
        self.assertEqual((actor._wraith_exposure_turns,
                          self.engine._wraith_aura_state), (0, {}))

    def test_scene_reset_clears_durable_counts_before_the_source_is_serialized(self):
        from engine.effect_lifecycle import reset_wraith_aura
        actor = self.add_wraith()
        self.expose(4)
        reset_wraith_aura(self.engine)
        row = _serialize_entity(actor)
        self.assertEqual(row["component_state"]["actor"]["_wraith_exposure_turns"], 0)
        rebuilt = _deserialize_entities([row], self.engine)[0]
        self.engine.entities = [self.engine.player, rebuilt]
        self.engine._update_fov()
        self.assertEqual(self.engine._wraith_aura_state, {})
        self.expose(1)
        self.assertEqual(rebuilt._wraith_exposure_turns, 1)

    def test_older_v2_actor_without_optional_exposure_still_loads(self):
        actor = self.add_wraith()
        self.expose(4)
        row = _serialize_entity(actor)
        for key in ACTOR_OPTIONAL_STATE:
            row["component_state"]["actor"].pop(key)
        validate_actor_runtime(row)
        restored = _deserialize_entities([row], self.engine)[0]
        self.assertEqual(restored._wraith_exposure_turns, 0)
        self.assertIsNone(restored._surface_exit_x)
        self.assertIsNone(restored._surface_exit_wx)
        self.engine.entities = [self.engine.player, restored]
        self.expose(1)
        self.assertEqual(restored._wraith_exposure_turns, 1)

    def test_optional_exposure_rejects_invalid_values_without_relaxing_old_schema(self):
        row = _serialize_entity(self.add_wraith())
        for invalid in (-1, True, 1.5, "4", None):
            with self.subTest(invalid=invalid):
                changed = copy.deepcopy(row)
                changed["component_state"]["actor"]["_wraith_exposure_turns"] = invalid
                with self.assertRaisesRegex(ValueError, "_wraith_exposure_turns"):
                    validate_actor_runtime(changed)
        row["component_state"]["actor"].pop("_disrupted_turns")
        with self.assertRaisesRegex(ValueError, "_disrupted_turns"):
            validate_actor_runtime(row)

    def test_trailing_creature_retains_its_own_stair_exit_after_save_and_load(self):
        actor = self.add_wraith()
        actor._surface_exit_x, actor._surface_exit_y = 0, 8
        actor._surface_exit_wx, actor._surface_exit_wy = 0, 0
        submap = self.engine.world_map.get(0, 0).add_submap("lab", "Fixture lab", 41)
        submap.surface_x, submap.surface_y = 0, 8
        submap.entry_x, submap.entry_y = 12, 12
        source_map = LocalMap()
        source_map.tiles[:] = make_tile("flagstone", True, True)
        self.engine.save_manager.cache.store_submap(submap.submap_id, source_map, [])
        self.engine.entities.remove(actor)
        self.engine._live_pursuers.append((actor, 0, 0, submap.submap_id))
        # The player's current return location belongs to a different entrance.
        self.engine.surface_return_x, self.engine.surface_return_y = 25, 26
        self.assertTrue(self.engine.save_manager.save(self.engine))
        self.assertTrue(self.engine.save_manager.load(self.engine))
        rebuilt = self.engine._live_pursuers[0][0]
        self.assertIsNot(rebuilt, actor)
        self.assertEqual([rebuilt._surface_exit_x, rebuilt._surface_exit_y,
                          rebuilt._surface_exit_wx, rebuilt._surface_exit_wy],
                         [0, 8, 0, 0])
        self.assertTrue(self.engine._transfer_submap_pursuer_to_surface(
            rebuilt, 0, 0, submap.submap_id))
        self.assertEqual((rebuilt.x, rebuilt.y), (0, 8))
        self.assertIn(rebuilt, self.engine.entities)

    def test_incomplete_stair_exit_pair_is_rejected(self):
        row = _serialize_entity(self.add_wraith())
        row["component_state"]["actor"]["_surface_exit_x"] = 12
        with self.assertRaisesRegex(ValueError, "incomplete _surface_exit_x"):
            validate_actor_runtime(row)

    def test_surface_crossing_preserves_f5_and_resets_departing_wraith_before_cache(self):
        import pygame
        engine = self.engine
        engine.debug = None  # production F5/F9 bindings, not debug hotkeys
        engine.world_map.width = 2
        engine.world_map.set(Chunk(1, 0, RegionType.PLAINS, 29418, visited=True))
        destination = LocalMap()
        destination.tiles[:] = make_tile("grass", True, True)
        engine.save_manager.cache.store(1, 0, destination, [])
        engine.player.x, engine.player.y = engine.local_map.width - 1, 12
        actor = self.add_wraith(engine.player.x - 2, 12)
        self.expose(4)
        original = aura_state(engine)
        engine._handle_key(pygame.K_F5)
        self.assertIsNone(engine.save_manager.last_error)
        head = (engine.save_manager.save_path / "HEAD.json").read_bytes()
        engine._handle_key(pygame.K_RIGHT)
        self.assertEqual((engine.world_x, engine.world_y), (1, 0))
        self.assertEqual((engine.save_manager.save_path / "HEAD.json").read_bytes(), head)
        cached_source = engine.save_manager.cache.load(0, 0)
        self.assertEqual(len(cached_source.entities), 1)
        self.assertEqual(cached_source.entities[0]["component_state"]["actor"]
                         ["_wraith_exposure_turns"], 0)
        self.assertEqual(actor._wraith_exposure_turns, 0)
        engine._handle_key(pygame.K_F9)
        self.assertIsNone(engine.save_manager.last_error)
        self.assertEqual((engine.world_x, engine.world_y), (0, 0))
        self.assertEqual((engine.player.x, engine.player.y), (79, 12))
        self.assertEqual(aura_state(engine), original)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--inspect-checkpoint":
        # The parent supplies only its newly created temporary save root.
        save_root = Path(sys.argv[2]).resolve()
        if save_root.is_relative_to(GAME_ROOT):
            raise SystemExit("Refusing to use saves inside the source checkout")
        with patch("engine.save_manager.SAVE_DIR", save_root):
            engine = make_engine(load_data())
            if not engine.save_manager.load(engine):
                raise SystemExit(engine.save_manager.last_error)
            print(json.dumps(aura_state(engine)))
    else:
        unittest.main()
