"""Destination ownership regressions using real actors and disposable checkpoints."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_effect_persistence import load_data, make_engine
from engine.save_manager import (
    _serialize_player, _deserialize_player, _pending_destination, SaveFormatError,
)
from world.local_map import LocalMap, make_tile
from world.world_map import Chunk, RegionType


class PendingArrivalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="resonance-arrival-test-")
        self.addCleanup(temp.cleanup)
        save_patch = patch("engine.save_manager.SAVE_DIR", Path(temp.name) / "saves")
        save_patch.start()
        self.addCleanup(save_patch.stop)
        self.engine = e = make_engine(self.data)
        e.world_map.width = 2
        e.world_map.set(Chunk(1, 0, RegionType.PLAINS, 29418, visited=True))
        other = LocalMap()
        other.tiles[:] = make_tile("grass", True, True)
        e.save_manager.cache.store(1, 0, other, [])

    def queue(self, delay=1):
        e = self.engine
        actor = e.creature_factory.spawn("hollow_revenant", 0, 12)
        self.assertIsNotNone(actor)
        e._pending_pursuer_arrivals.append({
            "entity": actor, "entry_x": 0, "entry_y": 12, "delay": delay,
            "destination_wx": 0, "destination_wy": 0,
            "destination_submap_id": None,
        })
        return actor

    def test_expired_arrival_waits_for_its_original_chunk_then_arrives_once(self):
        e = self.engine
        actor = self.queue()
        e.world_x = 1
        e._tick_pending_pursuer_arrivals()
        self.assertNotIn(actor, e.entities)
        self.assertEqual(e._pending_pursuer_arrivals[0]["delay"], 0)
        for _ in range(4):
            e._tick_pending_pursuer_arrivals()
        self.assertNotIn(actor, e.entities)
        self.assertEqual(len(e._pending_pursuer_arrivals), 1)
        e.world_x = 0
        e._tick_pending_pursuer_arrivals()
        self.assertEqual(sum(a is actor for a in e.entities), 1)
        self.assertEqual(e._pending_pursuer_arrivals, [])
        self.assertTrue(e.local_map.in_bounds(actor.x, actor.y))
        self.assertTrue(e.local_map.walkable[actor.x, actor.y])
        e._tick_pending_pursuer_arrivals()
        self.assertEqual(sum(a is actor for a in e.entities), 1)

    def test_surface_arrival_does_not_materialize_in_submap_at_same_world_address(self):
        e = self.engine
        actor = self.queue()
        e.current_submap_id = "fixture_below"
        e._tick_pending_pursuer_arrivals()
        self.assertNotIn(actor, e.entities)
        self.assertEqual(len(e._pending_pursuer_arrivals), 1)
        e.current_submap_id = None
        e._tick_pending_pursuer_arrivals()
        self.assertIn(actor, e.entities)

    def test_real_save_load_preserves_destination_while_player_is_elsewhere(self):
        e = self.engine
        original_actor = self.queue(delay=2)
        e.save_manager.cache.store(0, 0, e.local_map, e.entities)
        e.world_x = 1
        e.local_map = e.save_manager.cache.load(1, 0).local_map
        self.assertTrue(e.save_manager.save(e), e.save_manager.last_error)
        self.assertTrue(e.save_manager.load(e), e.save_manager.last_error)
        pa = e._pending_pursuer_arrivals[0]
        self.assertIsNot(pa["entity"], original_actor)
        self.assertEqual((pa["destination_wx"], pa["destination_wy"],
                          pa["destination_submap_id"], pa["delay"]), (0, 0, None, 2))
        e._tick_pending_pursuer_arrivals()
        e._tick_pending_pursuer_arrivals()
        self.assertNotIn(pa["entity"], e.entities)
        self.assertEqual(pa["delay"], 0)
        self.assertTrue(e.save_manager.save(e))
        self.assertTrue(e.save_manager.load(e))
        pa = e._pending_pursuer_arrivals[0]
        e.world_x = 0
        e.local_map = e.save_manager.cache.load(0, 0).local_map
        e._tick_pending_pursuer_arrivals()
        self.assertIn(pa["entity"], e.entities)
        self.assertEqual(e._pending_pursuer_arrivals, [])

    def test_older_v2_queue_defaults_to_saved_scene_not_previous_runtime_scene(self):
        e = self.engine
        self.queue()
        saved = _serialize_player(e)
        for key in ("destination_wx", "destination_wy", "destination_submap_id"):
            saved["pending_pursuer_arrivals"][0].pop(key)
        e.world_x = 1
        _deserialize_player(saved, e)
        row = e._pending_pursuer_arrivals[0]
        self.assertEqual((row["destination_wx"], row["destination_wy"],
                          row["destination_submap_id"]), (0, 0, None))

    def test_partial_or_invalid_destination_cannot_replace_a_good_checkpoint(self):
        e = self.engine
        self.assertTrue(e.save_manager.save(e))
        head = (e.save_manager.save_path / "HEAD.json").read_bytes()
        self.queue()
        original = copy.copy(e._pending_pursuer_arrivals[0])
        for field, value in [("destination_wx", 99), ("destination_wy", True),
                             ("destination_submap_id", "missing"), ("delay", -1),
                             ("delay", 1.5), ("entry_x", "0")]:
            with self.subTest(field=field, value=value):
                e._pending_pursuer_arrivals[0] = dict(original, **{field: value})
                self.assertFalse(e.save_manager.save(e))
                self.assertEqual((e.save_manager.save_path / "HEAD.json").read_bytes(), head)
        row = dict(original)
        row.pop("destination_wy")
        with self.assertRaisesRegex(SaveFormatError, "Incomplete"):
            _pending_destination(row, _serialize_player(make_engine(self.data)))

    def test_dead_pending_actor_is_removed_without_materializing(self):
        actor = self.queue()
        actor.fighter.take_damage(actor.fighter.hp)
        self.engine._tick_pending_pursuer_arrivals()
        self.assertEqual(self.engine._pending_pursuer_arrivals, [])
        self.assertNotIn(actor, self.engine.entities)


if __name__ == "__main__":
    unittest.main()
