"""Headless action-route regressions against supplied game source, using fresh saves.

Example: PYTHONPATH=critical_fixes/deps python critical_fixes/tests/test_action_routes.py
Set RESONANCE_GAME_ROOT to test another game directory. This is an archive-source
regression test; it does not assert Git branch/ancestry or touch existing saves.
RESONANCE_TEST_TOOLS locates the historical B1 loop helpers, and
RESONANCE_TEST_EVIDENCE_DIR controls where the stair-loop evidence is written.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import warnings

TASK_ROOT = Path(__file__).resolve().parents[2]
GAME_ROOT = Path(os.environ.get("RESONANCE_GAME_ROOT", TASK_ROOT / "fullgame_review/roguelike")).resolve()
TEST_TOOLS = Path(os.environ.get("RESONANCE_TEST_TOOLS", TASK_ROOT / "analysis/reconstructed/tools")).resolve()
EVIDENCE_DIR = Path(os.environ.get("RESONANCE_TEST_EVIDENCE_DIR", TASK_ROOT / "critical_fixes/evidence")).resolve()
DEPS = TASK_ROOT / "critical_fixes/deps"
if DEPS.is_dir():
    sys.path.insert(0, str(DEPS))
sys.path.insert(0, str(GAME_ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import config
import engine.save_manager as save_module
from engine.engine import Engine, GameMode
from generation.decor_utils import place_decor
from generation.floor_object_utils import place_container, place_floor_object, remove_floor_object
import main


class ActionRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_cwd = Path.cwd()
        os.chdir(GAME_ROOT)
        config.DEBUG_MODE = False
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        os.chdir(cls.original_cwd)

    def setUp(self):
        pygame.init()
        self.temp = tempfile.TemporaryDirectory(prefix="resonance-action-routes-")
        self.old_save_dir = save_module.SAVE_DIR
        save_module.SAVE_DIR = Path(self.temp.name) / "saves"
        slot = save_module.SAVE_DIR / "slot_0"
        slot.mkdir(parents=True)
        (slot / "world.json").write_text(json.dumps({"seed": 20261020}), encoding="utf-8")
        captured = []
        original_run = Engine.run
        Engine.run = lambda engine: captured.append(engine)
        try:
            with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                main.main()
        finally:
            Engine.run = original_run
        self.engine = e = captured[0]
        e.entities = [e.player]
        e.player.x = e.player.y = 20
        e.player_invincible = True
        e.player.inventory.capacity = 100
        e._move_debt = 0
        m = e.local_map
        m.tiles["terrain"][:] = "flagstone"
        m.walkable[:] = True
        m.transparent[:] = True
        m.visible[:] = True
        m.explored[:] = True
        m.decor.clear()
        m.floor_objects.clear()
        m.container_state.clear()
        m.processing_layer.clear()
        m.vine_networks.clear()
        m.examined_steles.clear()
        m.examined_bells.clear()
        m.interacted_waystones.clear()
        e.look_mode.enter(20, 20)

    def tearDown(self):
        save_module.SAVE_DIR = self.old_save_dir
        self.temp.cleanup()

    def look_at(self, x, y):
        e = self.engine
        e.mode = GameMode.LOOK
        e.look_mode.enter(e.player.x, e.player.y)
        e.look_mode.cursor_x, e.look_mode.cursor_y = x, y
        e.look_mode.handle_key(pygame.K_RETURN, e)

    def floor_item(self, x=21, y=20, item_id="crude_blade"):
        e = self.engine
        item = e.item_factory.create(item_id, x, y)
        self.assertIsNotNone(item)
        self.assertTrue(place_floor_object(e.local_map, x, y, item))
        return item

    def select_floor(self, items, selected=0, x=21, y=20):
        e = self.engine
        e.mode = GameMode.INTERACTION_CURSOR
        e.interaction_cursor.enter([(x, y)], e.player.x, e.player.y)
        e.interaction_cursor._selection_prompt = {
            "items": list(items), "selected": selected, "lx": x, "ly": y,
        }
        e.interaction_cursor.handle_key(pygame.K_RETURN, e)

    def test_navigation_clamps_all_edges_and_corners(self):
        e = self.engine
        m = e.local_map
        for x, y in [(0, 0), (m.width - 1, 0), (0, m.height - 1),
                     (m.width - 1, m.height - 1), (0, 20), (m.width - 1, 20)]:
            e.player.x, e.player.y = x, y
            c = e.interaction_cursor
            c.enter([], x, y)
            for key in [pygame.K_LEFT, pygame.K_UP, pygame.K_RIGHT, pygame.K_RIGHT,
                        pygame.K_DOWN, pygame.K_DOWN, pygame.K_LEFT]:
                c.handle_key(key, e)
                self.assertTrue(m.in_bounds(c.cursor_x, c.cursor_y))
                self.assertLessEqual(max(abs(c.cursor_x - x), abs(c.cursor_y - y)), 1)

    def test_stale_off_map_cursor_cannot_crash_confirm_or_render(self):
        e = self.engine
        c, m = e.interaction_cursor, e.local_map
        turn = e.world_time.turn
        screen = pygame.Surface((1280, 720))
        for pos in [(-1, 20), (m.width, 20), (20, -1), (20, m.height)]:
            c.enter([], e.player.x, e.player.y)
            c._cursor_x, c._cursor_y = pos
            c.handle_key(pygame.K_RETURN, e)
            c.render(screen, e, 0, 0, screen.get_rect())
        self.assertEqual(turn, e.world_time.turn)

    def test_remote_fire_examine_is_read_only(self):
        e = self.engine
        place_decor(e.local_map, 28, 28, "campfire_unlit")
        turn = e.world_time.turn
        self.look_at(28, 28)
        self.assertEqual("campfire_unlit", e.local_map.decor[(28, 28)])
        self.assertEqual(turn, e.world_time.turn)
        self.assertTrue(e.look_mode.examining)

    def test_remembered_adjacent_fire_examine_is_read_only(self):
        e = self.engine
        place_decor(e.local_map, 21, 20, "campfire_unlit")
        e.local_map.visible[21, 20] = False
        turn = e.world_time.turn
        self.look_at(21, 20)
        self.assertEqual("campfire_unlit", e.local_map.decor[(21, 20)])
        self.assertEqual(turn, e.world_time.turn)

    def test_adjacent_fire_uses_one_action(self):
        e = self.engine
        place_decor(e.local_map, 21, 20, "campfire_unlit")
        turn = e.world_time.turn
        self.look_at(21, 20)
        self.assertEqual("campfire_lit", e.local_map.decor[(21, 20)])
        self.assertEqual(turn + 1, e.world_time.turn)
        self.assertEqual(GameMode.LOOK, e.mode)

    def test_closed_diagonal_corner_blocks_physical_action(self):
        e = self.engine
        place_decor(e.local_map, 21, 21, "campfire_unlit")
        e.local_map.walkable[21, 20] = False
        e.local_map.walkable[20, 21] = False
        turn = e.world_time.turn
        self.look_at(21, 21)
        self.assertEqual("campfire_unlit", e.local_map.decor[(21, 21)])
        self.assertEqual(turn, e.world_time.turn)

    def test_remote_container_stays_closed(self):
        e = self.engine
        item = e.item_factory.create("tallow_torch")
        place_container(e.local_map, 28, 28, "crate", [item])
        turn = e.world_time.turn
        self.look_at(28, 28)
        self.assertEqual("closed", e.local_map.container_state[(28, 28)]["state"])
        self.assertIsNone(e.interaction_cursor._selection_prompt)
        self.assertEqual(turn, e.world_time.turn)

    def test_adjacent_container_prompt_owns_input_and_transfer_cost(self):
        e = self.engine
        item = e.item_factory.create("tallow_torch")
        place_container(e.local_map, 21, 20, "crate", [item])
        turn = e.world_time.turn
        self.look_at(21, 20)
        self.assertEqual(GameMode.INTERACTION_CURSOR, e.mode)
        self.assertIsNotNone(e.interaction_cursor._selection_prompt)
        self.assertEqual(turn, e.world_time.turn)
        e._handle_key(pygame.K_RETURN)
        self.assertTrue(e.player.inventory.contains(item))
        self.assertEqual(turn + 1, e.world_time.turn)
        self.assertIsNone(e.interaction_cursor._selection_prompt)

    def test_inscription_learning_costs_once_and_reread_stays_free(self):
        e = self.engine
        place_decor(e.local_map, 21, 20, "stele")
        e.local_map.stele_text_ids[(21, 20)] = "lab_label_sarcophagus"
        turn = e.world_time.turn
        self.look_at(21, 20)
        self.assertTrue(e.text_reader.open)
        self.assertIn((21, 20), e.local_map.examined_steles)
        self.assertEqual(turn + 1, e.world_time.turn)
        e.text_reader.close()
        self.look_at(21, 20)
        self.assertTrue(e.text_reader.open)
        self.assertEqual(turn + 1, e.world_time.turn)

    def test_repeated_live_bell_pulses_each_cost_a_turn(self):
        e = self.engine
        place_decor(e.local_map, 21, 20, "intact_bell")
        turn = e.world_time.turn
        self.look_at(21, 20)
        e.text_reader.close()
        exposure = e.resonance_exposure
        self.look_at(21, 20)
        self.assertGreater(e.resonance_exposure, exposure)
        self.assertEqual(turn + 2, e.world_time.turn)

    def test_full_bag_single_pickup_keeps_item_and_time(self):
        e = self.engine
        item = self.floor_item()
        e.player.inventory.capacity = 0
        e.interaction_cursor.enter([(21, 20)], 20, 20)
        turn = e.world_time.turn
        e.interaction_cursor.handle_key(pygame.K_RETURN, e)
        self.assertIn(item, e.local_map.floor_objects[(21, 20)])
        self.assertFalse(e.player.inventory.contains(item))
        self.assertEqual(turn, e.world_time.turn)

    def test_full_bag_selected_pickup_and_take_all_keep_time(self):
        e = self.engine
        items = [self.floor_item(), self.floor_item(item_id="tallow_torch")]
        e.player.inventory.capacity = 0
        turn = e.world_time.turn
        self.select_floor(items, 0)
        self.assertEqual(turn, e.world_time.turn)
        self.select_floor(items, len(items))
        self.assertEqual(turn, e.world_time.turn)
        self.assertEqual(items, e.local_map.floor_objects[(21, 20)])

    def test_partial_take_all_spends_one_turn_and_keeps_rejected_item(self):
        e = self.engine
        items = [self.floor_item(item_id="tallow_torch"), self.floor_item()]
        e.player.inventory.capacity = e.player.inventory.current_weight + items[0].weight
        turn = e.world_time.turn
        self.select_floor(items, len(items))
        self.assertTrue(e.player.inventory.contains(items[0]))
        self.assertFalse(e.player.inventory.contains(items[1]))
        self.assertEqual([items[1]], e.local_map.floor_objects[(21, 20)])
        self.assertEqual(turn + 1, e.world_time.turn)

    def test_full_bag_container_selection_keeps_item_and_time(self):
        e = self.engine
        item = e.item_factory.create("tallow_torch")
        place_container(e.local_map, 21, 20, "crate", [item])
        e.player.inventory.capacity = 0
        self.look_at(21, 20)
        turn = e.world_time.turn
        e._handle_key(pygame.K_RETURN)
        self.assertEqual([item], e.local_map.container_state[(21, 20)]["items"])
        self.assertFalse(e.player.inventory.contains(item))
        self.assertEqual(turn, e.world_time.turn)

    def test_stale_floor_prompt_cannot_take_item_moved_to_other_tile(self):
        e = self.engine
        item = self.floor_item()
        remove_floor_object(e.local_map, 21, 20, item)
        place_floor_object(e.local_map, 28, 28, item)
        turn = e.world_time.turn
        self.select_floor([item])
        self.assertFalse(e.player.inventory.contains(item))
        self.assertEqual([item], e.local_map.floor_objects[(28, 28)])
        self.assertEqual(turn, e.world_time.turn)

    def test_direct_comma_and_g_pickups_each_cost_one_turn(self):
        e = self.engine
        for key in (pygame.K_COMMA, pygame.K_g):
            item = self.floor_item(20, 20)
            turn = e.world_time.turn
            e._handle_key_local(key)
            self.assertTrue(e.player.inventory.contains(item))
            self.assertEqual(turn + 1, e.world_time.turn)

    def test_g_rejected_pickup_keeps_time(self):
        e = self.engine
        item = self.floor_item(20, 20)
        e.player.inventory.capacity = 0
        turn = e.world_time.turn
        e._handle_key_local(pygame.K_g)
        self.assertFalse(e.player.inventory.contains(item))
        self.assertEqual(turn, e.world_time.turn)

    def test_opening_direct_pickup_choice_spends_no_turn(self):
        e = self.engine
        self.floor_item(20, 20)
        self.floor_item(20, 20, "tallow_torch")
        turn = e.world_time.turn
        e._handle_key_local(pygame.K_COMMA)
        self.assertEqual(GameMode.INTERACTION_CURSOR, e.mode)
        self.assertIsNotNone(e.interaction_cursor._selection_prompt)
        self.assertEqual(turn, e.world_time.turn)

    def test_directional_pickup_spends_time_only_after_success(self):
        e = self.engine
        item = self.floor_item()
        turn = e.world_time.turn
        e._handle_key_local(pygame.K_COMMA)
        self.assertTrue(e._pickup_mode)
        self.assertEqual(turn, e.world_time.turn)
        e._handle_key_local(pygame.K_RIGHT)
        self.assertTrue(e.player.inventory.contains(item))
        self.assertEqual((20, 20), (e.player.x, e.player.y))
        self.assertEqual(turn + 1, e.world_time.turn)
        rejected = self.floor_item()
        e.player.inventory.capacity = 0
        turn = e.world_time.turn
        e._handle_key_local(pygame.K_COMMA)
        e._handle_key_local(pygame.K_RIGHT)
        self.assertFalse(e.player.inventory.contains(rejected))
        self.assertEqual(turn, e.world_time.turn)

    def test_empty_pickup_spends_no_turn(self):
        e = self.engine
        turn = e.world_time.turn
        e._handle_key_local(pygame.K_COMMA)
        self.assertFalse(e._pickup_mode)
        self.assertEqual(turn, e.world_time.turn)

    def test_directional_pickup_rejects_unseen_and_sealed_diagonal_items(self):
        e = self.engine
        for blocked_by in ("unseen", "sealed_corner"):
            with self.subTest(blocked_by=blocked_by):
                e.local_map.floor_objects.clear()
                e.local_map.visible[:] = True
                e.local_map.walkable[:] = True
                item = self.floor_item(21, 21)
                if blocked_by == "unseen":
                    e.local_map.visible[21, 21] = False
                else:
                    e.local_map.walkable[21, 20] = False
                    e.local_map.walkable[20, 21] = False
                turn = e.world_time.turn
                # An unreachable item alone must not open a pickup prompt.
                e._handle_key_local(pygame.K_COMMA)
                self.assertFalse(e._pickup_mode)
                # Another reachable item opens the prompt, but selecting the
                # blocked target must still be rejected by the transfer route.
                self.floor_item(19, 20, "tallow_torch")
                e._handle_key_local(pygame.K_COMMA)
                self.assertTrue(e._pickup_mode)
                e._handle_key_local(pygame.K_KP3)
                self.assertFalse(e._pickup_mode)
                self.assertFalse(e.player.inventory.contains(item))
                self.assertEqual([item], e.local_map.floor_objects[(21, 21)])
                self.assertEqual(turn, e.world_time.turn)

    def test_real_keydown_stairs_respect_modals_look_and_death(self):
        # Reuse the original loop driver without spoofing production Git state.
        sys.path.insert(0, str(TEST_TOOLS))
        from b1_support import Evidence
        from b1_journey import run_journey
        job = dict(run_id="archive-action-route-stairs", scenario="journey",
                   variant="stair-modal-guards", phase="loop", flavor="candidate",
                   game=str(GAME_ROOT), result=str(Path(self.temp.name) / "stairs.json"))
        ev = Evidence(job)

        def actions(e, key, capture, choose):
            e.entities = [e.player]
            e.player_invincible = True
            sid = e.current_submap_id
            self.assertIsNotNone(sid)
            self.assertEqual("stairs_up", str(e.local_map.tiles[e.player.x, e.player.y]["terrain"]))
            turn = e.world_time.turn
            # Actual KEYDOWN/KEYUP pairs exercise the previously bypassed Unicode path.
            for open_key, close_key, screen_name in (
                (pygame.K_i, pygame.K_i, "inventory_screen"),
                (pygame.K_c, pygame.K_ESCAPE, "craft_screen"),
            ):
                yield key(open_key, pygame.key.name(open_key))
                self.assertTrue(getattr(e, screen_name).open)
                yield key(pygame.K_COMMA, "<", pygame.KMOD_SHIFT)
                self.assertEqual(sid, e.current_submap_id)
                self.assertTrue(getattr(e, screen_name).open)
                self.assertEqual(turn, e.world_time.turn)
                yield key(close_key, pygame.key.name(close_key))
            e.text_reader.open_text(e.data.texts["lab_label_sarcophagus"])
            yield key(pygame.K_COMMA, "<", pygame.KMOD_SHIFT)
            self.assertEqual(sid, e.current_submap_id)
            self.assertTrue(e.text_reader.open)
            yield key(pygame.K_ESCAPE)
            item = e.item_factory.create("wight_concentrate")
            self.assertTrue(e.player.inventory.add(item))
            e.item_system.use(item, e)
            yield key(pygame.K_COMMA, "<", pygame.KMOD_SHIFT)
            self.assertEqual(sid, e.current_submap_id)
            self.assertIsNotNone(e._pending_consume)
            yield key(pygame.K_n, "n")
            yield key(pygame.K_x, "x")
            self.assertEqual(GameMode.LOOK, e.mode)
            yield key(pygame.K_COMMA, "<", pygame.KMOD_SHIFT)
            self.assertEqual(sid, e.current_submap_id)
            yield key(pygame.K_ESCAPE)
            # Local stairs still work in both directions.
            yield key(pygame.K_COMMA, "<", pygame.KMOD_SHIFT)
            self.assertIsNone(e.current_submap_id)
            yield key(pygame.K_PERIOD, ">", pygame.KMOD_SHIFT)
            self.assertEqual(sid, e.current_submap_id)
            e._player_is_dead = True
            yield key(pygame.K_COMMA, "<", pygame.KMOD_SHIFT)
            self.assertEqual(sid, e.current_submap_id)
            self.assertEqual(turn, e.world_time.turn)

        with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            run_journey(ev, actions)
        self.assertGreater(ev.record["actions"], 15)
        self.assertTrue(all(check["passed"] for check in ev.record["checks"]))
        ev.bind_sources(GAME_ROOT)
        ev.record["verification_scope"] = "Archive-source stair-route regression; no Git branch or production gate asserted"
        ev.record["completed"] = True
        evidence = EVIDENCE_DIR / "action_routes_stairs.json"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(ev.record, indent=2), encoding="utf-8")

    def test_held_stair_keys_never_repeat_as_wait_turns(self):
        # Unlike the historical paired-event driver, intentionally keep a real
        # KEYDOWN pressed beyond the game's repeat delay before posting KEYUP.
        # The original loop clock and get_ticks both advance normally.
        from engine.engine import KEY_REPEAT_DELAY, KEY_REPEAT_INTERVAL
        original_run, original_get = Engine.run, pygame.event.get
        runtime, trace = {}, []
        started = time.monotonic()
        frame, done = 0, False
        hold_seconds = (KEY_REPEAT_DELAY + 2 * KEY_REPEAT_INTERVAL + 40) / 1000

        def hold(key, text, modifiers):
            pygame.key.set_mods(modifiers)
            yield pygame.event.Event(pygame.KEYDOWN, key=key, unicode=text, mod=modifiers)
            pressed = time.monotonic()
            while time.monotonic() - pressed < hold_seconds:
                yield None
            yield pygame.event.Event(pygame.KEYUP, key=key, unicode=text, mod=modifiers)
            pygame.key.set_mods(0)

        def actions(e):
            e.entities = [e.player]
            e.player_invincible = True
            submap_id = e.current_submap_id
            self.assertIsNotNone(submap_id)
            for label, key, text, expected_scene in (
                ("ascent", pygame.K_COMMA, "<", None),
                ("descent", pygame.K_PERIOD, ">", submap_id),
                ("invalid descent on stairs up", pygame.K_PERIOD, ">", submap_id),
            ):
                turn = e.world_time.turn
                yield from hold(key, text, pygame.KMOD_SHIFT)
                trace.append(dict(phase=label, turn_before=turn, turn_after=e.world_time.turn,
                                  submap_id=e.current_submap_id, held_key=e._held_key))
                with self.subTest(phase=label):
                    self.assertEqual(expected_scene, e.current_submap_id)
                    self.assertEqual(turn, e.world_time.turn)
                    self.assertIsNone(e._held_key)
            # Preserve the intended hold-to-wait behavior for an ordinary period.
            turn = e.world_time.turn
            yield from hold(pygame.K_PERIOD, ".", 0)
            trace.append(dict(phase="ordinary wait", turn_before=turn, turn_after=e.world_time.turn,
                              submap_id=e.current_submap_id, held_key=e._held_key))
            self.assertGreater(e.world_time.turn, turn + 1)
            self.assertIsNone(e._held_key)

        def run(e):
            runtime["engine"] = e
            runtime["actions"] = actions(e)
            return original_run(e)

        def events(*args, **kwargs):
            nonlocal frame, done
            if frame >= 300 or time.monotonic() - started > 10:
                raise AssertionError("Held-key loop exceeded its frame/time budget")
            self.assertEqual("dummy", pygame.display.get_driver())
            try:
                event = next(runtime["actions"])
            except StopIteration:
                done = True
                event = pygame.event.Event(pygame.QUIT)
            if event is not None:
                self.assertTrue(pygame.event.post(event))
            frame += 1
            return original_get(*args, **kwargs)

        Engine.run, pygame.event.get = run, events
        try:
            with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                try:
                    main.main()
                except SystemExit as error:
                    if not done or error.code not in (None, 0):
                        raise
        finally:
            Engine.run, pygame.event.get = original_run, original_get
            if pygame.get_init():
                pygame.key.set_mods(0)
                pygame.event.clear()
            pygame.quit()
        self.assertTrue(done)
        self.assertEqual(4, len(trace))
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "held_stairs.json").write_text(json.dumps({
            "verification_scope": "Archive-source held-key regression; original Engine.run and wall clock",
            "hold_seconds": hold_seconds, "frames": frame, "trace": trace,
        }, indent=2), encoding="utf-8")

    def test_full_bag_direct_pickup_keeps_time(self):
        e = self.engine
        item = self.floor_item(20, 20)
        e.player.inventory.capacity = 0
        turn = e.world_time.turn
        e._handle_key_local(pygame.K_COMMA)
        self.assertFalse(e.player.inventory.contains(item))
        self.assertEqual(turn, e.world_time.turn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
