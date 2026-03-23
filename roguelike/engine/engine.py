# engine/engine.py
from __future__ import annotations
import enum
import json
import pygame
import tcod.map
import numpy as np
import random

from pathlib import Path
from config import FOV_RADIUS, MAP_WIDTH, MAP_HEIGHT, MSG_PANEL_W, STATUS_BAR_H, OVERMAP_SIDEBAR_W, UI_PANEL_INSET
from rendering.sprite_registry import SpriteRegistry
from rendering.tile_registry import TileRegistry
from rendering.ui_registry import UIRegistry
from rendering.renderer import Renderer
from engine.display_config import DisplayConfig
from engine.message_log import MessageLog
from engine.world_time import WorldTime
from engine.ui import UI
from components.light_source import LightSource
from components.fighter import Fighter
from components.needs import Needs
from components.corruption import Corruption
from components.inventory import Inventory
from engine.look_mode import LookMode
from engine.save_manager import SaveManager
from engine.item_factory import ItemFactory
from engine.item_system import ItemSystem
from engine.inventory_screen import InventoryScreen
from engine.text_reader import TextReader

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from world.local_map import LocalMap
    from world.world_map import WorldMap
    from entities.actor import Actor
    from entities.entity import Entity
    from entities.item import Item
    from engine.data_loader import DataLoader

from config import DEBUG_MODE
from engine.debug import DebugOverlay
from engine.ai_system import AISystem
from engine.creature_factory import CreatureFactory


class GameMode(enum.Enum):
    LOCAL   = "local"
    OVERMAP = "overmap"
    LOOK    = "look"


MOVE_KEYS: dict[int, tuple[int, int]] = {
    pygame.K_UP:    ( 0, -1),
    pygame.K_DOWN:  ( 0,  1),
    pygame.K_LEFT:  (-1,  0),
    pygame.K_RIGHT: ( 1,  0),
    pygame.K_KP8:   ( 0, -1),
    pygame.K_KP2:   ( 0,  1),
    pygame.K_KP4:   (-1,  0),
    pygame.K_KP6:   ( 1,  0),
    pygame.K_KP7:   (-1, -1),
    pygame.K_KP9:   ( 1, -1),
    pygame.K_KP1:   (-1,  1),
    pygame.K_KP3:   ( 1,  1),
    pygame.K_k:     ( 0, -1),
    pygame.K_j:     ( 0,  1),
    pygame.K_h:     (-1,  0),
    pygame.K_l:     ( 1,  0),
    pygame.K_y:     (-1, -1),
    pygame.K_u:     ( 1, -1),
    pygame.K_b:     (-1,  1),
    pygame.K_n:     ( 1,  1),
}

WAIT_KEYS = {pygame.K_PERIOD, pygame.K_KP5, pygame.K_z}

KEY_REPEAT_DELAY    = 180
KEY_REPEAT_INTERVAL = 60


class Engine:
    def __init__(
        self,
        player:    "Actor",
        local_map: "LocalMap",
        entities:  list["Entity"],
        registry:  TileRegistry,
        world_map: "WorldMap",
        world_x:   int,
        world_y:   int,
        data:      "DataLoader",
        display:   DisplayConfig,
    ) -> None:
        self.player    = player
        self.local_map = local_map
        self.entities  = entities
        self.registry  = registry
        self.world_map = world_map
        self.world_x   = world_x
        self.world_y   = world_y
        self.data      = data
        self.display   = display
        self.mode      = GameMode.LOCAL
        self.overmap_cam_x    = world_x
        self.overmap_cam_y    = world_y
        self.overmap_cursor_x = world_x
        self.overmap_cursor_y = world_y
        self.debug            = DebugOverlay() if DEBUG_MODE else None
        self.ai_system        = AISystem()
        self.creature_factory = CreatureFactory(data)
        self._held_key:        int | None = None
        self._held_key_timer:  int        = 0
        self.log              = MessageLog()
        self.world_time       = WorldTime()
        self.look_mode        = LookMode()
        self.save_manager     = SaveManager(slot=0)
        self.item_factory     = ItemFactory(data)
        self.item_system      = ItemSystem()
        self.inventory_screen = InventoryScreen()
        self.text_reader      = TextReader()
        self._pickup_mode:    bool = False
        self._player_is_dead: bool = False
        # SubMap traversal state
        self.current_submap_id:  str | None = None
        self.surface_return_x:   int        = 0
        self.surface_return_y:   int        = 0
        # Screenshake
        self._shake_x:     float = 0.0
        self._shake_y:     float = 0.0
        self._shake_decay: float = 0.75
        # Visual event queue (abilities → renderer)
        from engine.visual_events import VisualEventQueue
        self.visual_events = VisualEventQueue()
        # Debug flags
        self.player_invincible: bool = False

    @property
    def world_myth(self):
        return self.world_map.myth

    # ------------------------------------------------------------------ #
    #  Main loop
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        pygame.init()

        screen = pygame.display.set_mode(
            (1280, 720),
            pygame.RESIZABLE,
        )
        pygame.display.set_caption("Roguelike")

        self.display.init()

        # Load sprite registry
        self.sprite_registry: SpriteRegistry | None = None
        if self.display.render_mode == "sprite":
            self.sprite_registry = SpriteRegistry()
            self.sprite_registry.load()

        self.ui = UI(self.display)
        self.ui.init()
        self.ui_registry = UIRegistry()
        self.ui_registry.load()
        self.look_mode.init(self.display)
        self.inventory_screen.init(self.display)
        self.text_reader.init(self.display)

        if self.debug:
            self.debug.init()

        clock    = pygame.time.Clock()

        renderer = Renderer(
            self.registry,
            self.display,
            sprite_registry=self.sprite_registry,
        )

        self._update_fov()

        self.log.add(
            "Stone. Cold stone, and the smell of old air. "
            "Thy eyes open to darkness.",
            (129, 175, 181),
        )
        self.log.add(
            "Thou art beneath the ground. "
            "Something is wrong with the world above.",
            (99, 34, 64),
        )

        while True:
            sw  = screen.get_width()
            sh  = screen.get_height()

            game_panel_rect = pygame.Rect(0, 0, sw - MSG_PANEL_W, sh - STATUS_BAR_H)
            msg_panel       = pygame.Rect(sw - MSG_PANEL_W, 0, MSG_PANEL_W, sh - STATUS_BAR_H)
            status_bar      = pygame.Rect(0, sh - STATUS_BAR_H, sw, STATUS_BAR_H)

            # Inset tile viewport on the outer-frame sides only (left + top).
            # Right and bottom edges meet the adjacent panels — those panels
            # own their own left/top border, so no inset needed here.
            _border  = UI_PANEL_INSET // 2
            viewport = pygame.Rect(
                _border,
                _border,
                sw - MSG_PANEL_W - _border,   # full width minus left inset only
                sh - STATUS_BAR_H - _border,  # full height minus top inset only
            )

            self._viewport   = viewport
            self._msg_panel  = msg_panel
            self._status_bar = status_bar

            current_ticks = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit()

                if event.type in (pygame.VIDEORESIZE, pygame.WINDOWRESIZED):
                    screen.fill((4, 6, 14))
                    continue

                if event.type == pygame.KEYDOWN:
                    # Stair keys — checked via unicode so Shift+. and Shift+, work
                    if event.unicode == '>':
                        self._try_descend()
                        continue
                    elif event.unicode == '<':
                        self._try_ascend()
                        continue

                    if self.debug and self.debug.handle_key(event.key, self):
                        self._held_key = None
                        continue

                    self._handle_key(event.key)

                    if event.key in MOVE_KEYS or event.key in WAIT_KEYS:
                        self._held_key       = event.key
                        self._held_key_timer = current_ticks + KEY_REPEAT_DELAY

                if event.type == pygame.KEYUP:
                    if event.key == self._held_key:
                        self._held_key = None

            if self._held_key is not None:
                if current_ticks >= self._held_key_timer:
                    self._handle_key(self._held_key)
                    self._held_key_timer = current_ticks + KEY_REPEAT_INTERVAL

            # ---- Render ----
            screen.fill((4, 6, 14))

            # Death screen overlay
            if self._player_is_dead:
                self._render_death_screen(screen)
                pygame.display.flip()
                clock.tick(60)
                continue

            _panels = (
                hasattr(self, "ui_registry") and self.ui_registry._loaded
            )

            # --- Game world ---
            if self.mode in (GameMode.LOCAL, GameMode.LOOK):
                # Fill full game panel area with void color first — covers the
                # border inset zone on all sides before panel/tiles are drawn.
                screen.fill((4, 6, 14), game_panel_rect)
                cam_x, cam_y = self._get_camera(viewport)
                shake_offset = self._update_screenshake()
                self.visual_events.tick()
                renderer.render(
                    screen, self.local_map, self.entities,
                    cam_x, cam_y, viewport,
                    shake_offset=shake_offset,
                    visual_events=self.visual_events.get_active(),
                    void_rect=game_panel_rect,
                )
                if self.mode == GameMode.LOOK:
                    self.look_mode.render_cursor(screen, self, cam_x, cam_y)
                    if self.look_mode.examining:
                        self.look_mode.render_examine_popup(screen, self)

            elif self.mode == GameMode.OVERMAP:
                overmap_rect = pygame.Rect(0, 0, sw - OVERMAP_SIDEBAR_W, sh)
                sidebar_rect = pygame.Rect(sw - OVERMAP_SIDEBAR_W, 0,
                                           OVERMAP_SIDEBAR_W, sh)
                renderer.render_overmap(
                    screen,
                    self.world_map,
                    self.world_x,
                    self.world_y,
                    self.overmap_cam_x,
                    self.overmap_cam_y,
                    cursor_wx=self.overmap_cursor_x,
                    cursor_wy=self.overmap_cursor_y,
                    highlight_passages=(
                        self.debug.show_submap_highlights
                        if self.debug else False
                    ),
                    viewport=overmap_rect,
                )
                renderer.render_overmap_sidebar(
                    screen, sidebar_rect,
                    self.world_map,
                    self.overmap_cursor_x, self.overmap_cursor_y,
                    self.world_x, self.world_y,
                    self,
                )

            # --- UI panel frames + content (LOCAL / LOOK only) ---
            if self.mode in (GameMode.LOCAL, GameMode.LOOK):
                if _panels:
                    self.ui_registry.draw_panel(
                        screen, game_panel_rect, "weathered_temple",
                        tint_color=(40, 96, 128),
                        fill_color=(7, 12, 29),
                        fill_alpha=0,
                        border_scale=2,
                    )
                    self.ui_registry.draw_panel(
                        screen, msg_panel, "weathered_temple",
                        tint_color=(50, 73, 95),
                        fill_color=(7, 12, 29),
                        fill_alpha=245,
                        border_scale=2,
                    )
                    self.ui_registry.draw_panel(
                        screen, status_bar, "weathered_temple",
                        tint_color=(25, 27, 63),
                        fill_color=(7, 12, 29),
                        fill_alpha=245,
                        border_scale=2,
                    )
                else:
                    screen.fill((15, 12, 10), msg_panel)
                    screen.fill((15, 12, 10), status_bar)

                if self.mode == GameMode.LOOK:
                    self.look_mode.render_look_bar(screen, status_bar, self)
                else:
                    nearby = (
                        self._items_at(self.player.x, self.player.y) +
                        self._adjacent_items()
                    )
                    self.ui.render_status(
                        screen, status_bar, self.player,
                        self.world_time,
                        nearby_items=nearby,
                        registry=self.registry,
                    )
                self.ui.render_messages(screen, msg_panel, self.log)

            if self.debug:
                self.debug.render(screen, self)

            self.inventory_screen.render(screen, self)

            if self.text_reader.open:
                self.text_reader.render(screen, self)

            pygame.display.flip()
            clock.tick(60)

    # ------------------------------------------------------------------ #
    #  Screenshake
    # ------------------------------------------------------------------ #

    def _update_screenshake(self) -> tuple[int, int]:
        offset = (int(self._shake_x), int(self._shake_y))
        self._shake_x *= self._shake_decay
        self._shake_y *= self._shake_decay
        if abs(self._shake_x) < 0.1:
            self._shake_x = 0.0
        if abs(self._shake_y) < 0.1:
            self._shake_y = 0.0
        return offset

    def trigger_screenshake(
        self, magnitude: float, dx: int = 0, dy: int = 0
    ) -> None:
        """Trigger a screenshake. dx/dy is direction of impact (-1,0,1)."""
        self._shake_x = magnitude * (dx if dx != 0 else 1)
        self._shake_y = magnitude * (dy if dy != 0 else 0)

    # ------------------------------------------------------------------ #
    #  Turn advancement
    # ------------------------------------------------------------------ #

    def _advance_turn(self) -> None:
        self.world_time.advance()
        self.log.advance_turn()

        needs = getattr(self.player, "needs", None)
        if needs:
            prev_h = needs.hunger
            prev_t = needs.thirst
            needs.advance()
            needs.drain_messages(self.log, prev_h, prev_t)

        # Plague crow sickness — accelerated needs drain
        sickness = getattr(self.player, "_sickness_turns", 0)
        if sickness > 0:
            self.player._sickness_turns = sickness - 1
            if needs:
                needs.hunger = min(1.0, needs.hunger + 0.003)
                needs.thirst = min(1.0, needs.thirst + 0.005)

        corrupt = getattr(self.player, "corruption", None)
        if corrupt:
            chunk = self.world_map.get(self.world_x, self.world_y)
            zone_tags: list[str] = []
            if chunk:
                for zone_id, _ in chunk.zones:
                    zone = self.data.zones.get(zone_id)
                    if zone:
                        zone_tags.extend(zone.get("tags", []))
            corrupt.tick(self.log, zone_tags, self.world_time.turn)

        light = getattr(self.player, "light_source", None)
        if light and light.active:
            item_ref = getattr(light, "_item_ref", None)
            if item_ref is not None:
                item_ref.turns_lit += 1
                burn_turns = getattr(light, "_burn_turns", 600)
                remaining  = burn_turns - item_ref.turns_lit
                if remaining <= 0:
                    light.active = False
                    self._update_fov()
                    self.log.add_danger(
                        f"Your {item_ref.name} gutters and dies. "
                        f"You are in darkness."
                    )
                elif remaining == 60:
                    self.log.add(
                        f"Your {item_ref.name} is burning low.",
                        (200, 140, 60),
                    )

        self.ai_system.process(
            entities   = self.entities,
            player     = self.player,
            local_map  = self.local_map,
            world_map  = self.world_map,
            world_x    = self.world_x,
            world_y    = self.world_y,
            log        = self.log,
            world_time = self.world_time,
            data       = self.data,
            engine     = self,
        )

        if getattr(self.player, "took_damage_this_turn", False):
            if hasattr(self, "ui"):
                self.ui.notify_damage()
            self.trigger_screenshake(4.0)
            self.player.took_damage_this_turn = False

        if not self.player.is_alive:
            self._on_player_death()

        self.entities = [
            e for e in self.entities
            if getattr(e, "is_alive", True)
        ]


    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def _handle_key(self, key: int) -> None:
        # Any key on death screen exits
        if self._player_is_dead:
            pygame.quit()
            raise SystemExit()
        
        if self.debug and self.debug.handle_key(key, self):
            return

        if self.text_reader.open:
            self.text_reader.handle_key(key)
            return

        if self.inventory_screen.open:
            self.inventory_screen.handle_key(key, self)
            return

        if self.mode == GameMode.LOOK:
            self.look_mode.handle_key(key, self)
            return

        if self.mode == GameMode.LOCAL:
            self._handle_key_local(key)
        elif self.mode == GameMode.OVERMAP:
            self._handle_key_overmap(key)

    def _handle_key_local(self, key: int) -> None:
        # Directional pickup mode
        if self._pickup_mode:
            if key == pygame.K_ESCAPE:
                self._pickup_mode = False
                self.log.add("Cancelled.", (130, 120, 110))
                return
            if key in MOVE_KEYS:
                dx, dy = MOVE_KEYS[key]
                tx = self.player.x + dx
                ty = self.player.y + dy
                inv = getattr(self.player, "inventory", None)
                if inv:
                    items = self._items_at(tx, ty)
                    if items:
                        self._take_item(items[-1], inv)
                    else:
                        self.log.add(
                            "Nothing there to take.",
                            (160, 150, 130),
                        )
                self._pickup_mode = False
            return

        if key == pygame.K_m:
            self.overmap_cursor_x = self.world_x
            self.overmap_cursor_y = self.world_y
            self.overmap_cam_x    = self.world_x
            self.overmap_cam_y    = self.world_y
            self.mode = GameMode.OVERMAP
            return

        if key == pygame.K_EQUALS or key == pygame.K_PLUS:
            self.display.zoom_in()
            return
        elif key == pygame.K_MINUS:
            self.display.zoom_out()
            return

        if key in (pygame.K_SEMICOLON, pygame.K_x):
            self.look_mode.enter(self.player.x, self.player.y)
            self.mode = GameMode.LOOK
            return

        acted = False

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            dest_x = self.player.x + dx
            dest_y = self.player.y + dy

            if not self.local_map.in_bounds(dest_x, dest_y):
                self._transition_chunk(dx, dy)
                acted = True
            elif self.local_map.tiles['terrain'][dest_x, dest_y] == 'door_closed':
                self.local_map.set_tile(dest_x, dest_y, 'door_open', True, True)
                self._update_fov()
                self.log.add("The door yields.", (226, 181, 112))
                acted = True
            elif self.local_map.walkable[dest_x, dest_y]:
                blocker = self._get_blocking_entity(dest_x, dest_y)
                if blocker:
                    self._player_attack(blocker)
                    acted = True
                else:
                    self.player.move(dx, dy)
                    self._update_fov()
                    acted = True

        elif key in WAIT_KEYS:
            acted = True

        elif key == pygame.K_ESCAPE:
            pygame.quit()
            raise SystemExit()

        elif key == pygame.K_F5 and not self.debug:
            self.save_manager.save(self)

        elif key == pygame.K_F9 and not self.debug:
            self.save_manager.load(self)

        elif key == pygame.K_i:
            self.inventory_screen.toggle()
            return

        elif key in (pygame.K_g, pygame.K_COMMA):
            self._pick_up_item()
            acted = True

        if acted:
            self._advance_turn()
        if self.mode == GameMode.LOCAL:
            self._update_context_prompt()

    def _handle_key_overmap(self, key: int) -> None:
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            self.overmap_cursor_x = max(0, min(
                self.world_map.width  - 1,
                self.overmap_cursor_x + dx,
            ))
            self.overmap_cursor_y = max(0, min(
                self.world_map.height - 1,
                self.overmap_cursor_y + dy,
            ))
            # Camera follows cursor
            self.overmap_cam_x = self.overmap_cursor_x
            self.overmap_cam_y = self.overmap_cursor_y
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if DEBUG_MODE:
                self._teleport_to_overmap_cursor()
            else:
                self.log.add(
                    "Travel planning is not yet implemented.",
                    (99, 120, 140),
                )
                self.mode = GameMode.LOCAL
        elif key in {pygame.K_m, pygame.K_ESCAPE}:
            self.mode = GameMode.LOCAL

    def _teleport_to_overmap_cursor(self) -> None:
        """Generate and enter the chunk under the overmap cursor."""
        wx, wy = self.overmap_cursor_x, self.overmap_cursor_y
        chunk  = self.world_map.get(wx, wy)
        if not chunk:
            return
        from generation.region_gen import generate_region
        from config import MAP_WIDTH, MAP_HEIGHT
        new_map, (sx, sy) = generate_region(
            chunk, MAP_WIDTH, MAP_HEIGHT, self.data.terrain, data=self.data
        )
        sx, sy = self._find_walkable_near(new_map, sx, sy)
        self.player.x  = sx
        self.player.y  = sy
        self.local_map = new_map
        self.world_x   = wx
        self.world_y   = wy
        chunk.visited  = True
        # Spawn town creatures from town_data if available
        from world.world_map import RegionType
        town_entities = []
        if chunk.region_type == RegionType.TOWN and chunk.town_data:
            for sd in chunk.town_data.creature_spawns:
                actor = self.creature_factory.spawn(
                    sd["creature_id"], sd["x"], sd["y"]
                )
                if actor:
                    town_entities.append(actor)
        self.entities  = [self.player] + town_entities
        self.world_map.mark_explored_radius(wx, wy, radius=2)
        self._update_fov()
        self.mode = GameMode.LOCAL
        label = chunk.name if chunk.name else chunk.region_type.value
        self.log.add(f"Arrived at {label}.", (140, 180, 140))

    # ------------------------------------------------------------------ #
    #  Camera
    # ------------------------------------------------------------------ #

    def _get_camera(self, viewport: pygame.Rect) -> tuple[int, int]:
        tw, th = self.display.effective_tile_size(
            getattr(self, "sprite_registry", None)
        )
        tiles_x = viewport.width  // tw
        tiles_y = viewport.height // th

        if self.mode == GameMode.LOOK:
            cx = self.look_mode.cursor_x
            cy = self.look_mode.cursor_y
        else:
            cx = self.player.x
            cy = self.player.y

        cam_x = cx - tiles_x // 2
        cam_y = cy - tiles_y // 2
        cam_x = max(0, min(cam_x, max(0, self.local_map.width  - tiles_x)))
        cam_y = max(0, min(cam_y, max(0, self.local_map.height - tiles_y)))
        return cam_x, cam_y

    # ------------------------------------------------------------------ #
    #  Chunk transitions
    # ------------------------------------------------------------------ #

    def _transition_chunk(self, dx: int, dy: int) -> None:
        new_wx = self.world_x + dx
        new_wy = self.world_y + dy

        if not self.world_map.in_bounds(new_wx, new_wy):
            return

        chunk = self.world_map.get(new_wx, new_wy)
        if not chunk:
            return

        self.save_manager.cache.store(
            self.world_x,
            self.world_y,
            self.local_map,
            self.entities,
        )

        cached = self.save_manager.cache.load(new_wx, new_wy)

        if cached:
            new_map      = cached.local_map
            new_entities = _deserialize_entities_inline(
                cached.entities, self
            )
        else:
            from generation.region_gen import generate_region
            from world.world_map import RegionType as _RT
            new_map, _ = generate_region(
                chunk, MAP_WIDTH, MAP_HEIGHT, self.data.terrain, data=self.data
            )
            new_entities = []
            if chunk.region_type == _RT.TOWN and chunk.town_data:
                for sd in chunk.town_data.creature_spawns:
                    actor = self.creature_factory.spawn(
                        sd["creature_id"], sd["x"], sd["y"]
                    )
                    if actor:
                        new_entities.append(actor)
            else:
                chunk_rng = random.Random(chunk.seed + 1)
                for zone_id, _ in chunk.zones:
                    creatures = self.creature_factory.spawn_for_zone(
                        zone_id, new_map, chunk_rng, max_count=3
                    )
                    new_entities.extend(creatures)

        # Determine spawn from PASSAGE connector on the entry edge, else
        # fall back to a few tiles inside the edge we crossed.
        from world.world_map import ConnectorType
        entry_edge = {
            ( 1,  0): "west",
            (-1,  0): "east",
            ( 0,  1): "north",
            ( 0, -1): "south",
        }.get((dx, dy))

        spawn_x = MAP_WIDTH  // 2
        spawn_y = MAP_HEIGHT // 2

        passage = None
        if entry_edge:
            for conn in chunk.edges.get(entry_edge, []):
                if conn.connector_type == ConnectorType.PASSAGE:
                    passage = conn
                    break

        if passage and entry_edge:
            from generation.local_gen import _edge_to_tile
            ex, ey = _edge_to_tile(entry_edge, passage.position,
                                   MAP_WIDTH, MAP_HEIGHT)
            step = {"west": (3, 0), "east": (-3, 0),
                    "north": (0, 3), "south": (0, -3)}[entry_edge]
            spawn_x = ex + step[0]
            spawn_y = ey + step[1]
        else:
            if dx ==  1: spawn_x = 1
            if dx == -1: spawn_x = MAP_WIDTH  - 2
            if dy ==  1: spawn_y = 1
            if dy == -1: spawn_y = MAP_HEIGHT - 2

        spawn_x, spawn_y = self._find_walkable_near(new_map, spawn_x, spawn_y)

        self.player.x  = spawn_x
        self.player.y  = spawn_y
        self.local_map = new_map
        self.world_x   = new_wx
        self.world_y   = new_wy

        chunk.visited  = True
        self.world_map.mark_explored_radius(new_wx, new_wy, radius=1)
        self.entities  = [self.player] + new_entities
        for _e in new_entities:
            _e.last_known_x = None
            _e.last_known_y = None
        self._update_fov()

        self.save_manager.cache.evict_distant(new_wx, new_wy)

        if chunk.name:
            self.log.add_world(f"You move into {chunk.name}.")
        else:
            region_display = {
                "plains":   "open ground",
                "forest":   "the forest",
                "town":     "a settlement",
                "swamp":    "the mere",
                "mountain": "the high ground",
                "heath":    "the heath",
            }
            region_name = region_display.get(
                chunk.region_type.value,
                chunk.region_type.value
            )
            self.log.add_world(f"You move into {region_name}.")
        self.save_manager.save(self)
        self._update_context_prompt()

    # ------------------------------------------------------------------ #
    #  SubMap traversal (stairs)
    # ------------------------------------------------------------------ #

    def _try_descend(self) -> None:
        """Player attempts to descend. Must be standing on stairs_down."""
        terrain = str(self.local_map.tiles["terrain"][self.player.x, self.player.y])
        if terrain != "stairs_down":
            self.log.add(
                "There is nothing to descend here.",
                (99, 120, 140),
            )
            return
        submap_id = self.local_map.submap_links.get(
            (self.player.x, self.player.y)
        )
        if submap_id:
            self._descend_to_submap(submap_id)
        else:
            self.log.add(
                "The stairs descend into darkness but the way is blocked.",
                (99, 120, 140),
            )

    def _try_ascend(self) -> None:
        """Player attempts to ascend. Must be standing on stairs_up."""
        terrain = str(self.local_map.tiles["terrain"][self.player.x, self.player.y])
        if terrain == "stairs_up" and self.current_submap_id:
            self._ascend_from_submap()
        elif terrain == "stairs_up":
            self.log.add(
                "Thou art already at the surface.",
                (99, 120, 140),
            )
        else:
            self.log.add(
                "There is nothing to ascend here.",
                (99, 120, 140),
            )

    def _descend_to_submap(self, submap_id: str) -> None:
        """Cache surface, generate/load submap, place player at entry."""
        # Clear creature ability state that doesn't survive transitions
        self.player._wraith_fov_penalty = 0
        self.player._wraith_overcorrect = 0
        self.player._hollow_knight_disruption = False

        chunk = self.world_map.get(self.world_x, self.world_y)
        if not chunk:
            return
        submap = next((s for s in chunk.submaps if s.submap_id == submap_id), None)
        if not submap:
            return

        # Cache current surface state
        self.save_manager.cache.store(
            self.world_x, self.world_y,
            self.local_map, self.entities,
        )

        # Remember where to return on ascent
        self.surface_return_x  = self.player.x
        self.surface_return_y  = self.player.y
        self.current_submap_id = submap_id

        # Load or generate the submap
        cached = self.save_manager.cache.load_submap(submap_id)
        if cached:
            new_map      = cached.local_map
            new_entities = _deserialize_entities_inline(cached.entities, self)
        else:
            from generation.local_gen import generate_submap
            new_map, layout_entities = generate_submap(
                submap, MAP_WIDTH, MAP_HEIGHT, self.data.terrain, data=self.data
            )
            new_entities = self._spawn_layout_entities(layout_entities)

        spawn_x, spawn_y = self._find_walkable_near(
            new_map, submap.entry_x, submap.entry_y
        )
        self.player.x  = spawn_x
        self.player.y  = spawn_y
        self.local_map = new_map
        self.entities  = [self.player] + new_entities
        self._update_fov()
        label = submap.name or submap.submap_type
        self.log.add_world(f"You descend into {label}.")
        self._update_context_prompt()

    def _ascend_from_submap(self) -> None:
        """Cache submap, restore surface, place player at return coords."""
        self.player._wraith_fov_penalty = 0
        self.player._wraith_overcorrect = 0
        self.player._hollow_knight_disruption = False
        # Cache the current submap state
        self.save_manager.cache.store_submap(
            self.current_submap_id,
            self.local_map,
            self.entities,
        )

        # Reload the surface chunk
        cached = self.save_manager.cache.load(self.world_x, self.world_y)
        if cached:
            new_map      = cached.local_map
            new_entities = _deserialize_entities_inline(cached.entities, self)
        else:
            from generation.region_gen import generate_region
            chunk = self.world_map.get(self.world_x, self.world_y)
            if not chunk:
                return
            new_map, _ = generate_region(
                chunk, MAP_WIDTH, MAP_HEIGHT, self.data.terrain
            )
            new_entities = []

        self.player.x  = self.surface_return_x
        self.player.y  = self.surface_return_y
        spawn_x, spawn_y = self._find_walkable_near(
            new_map, self.player.x, self.player.y
        )
        self.player.x  = spawn_x
        self.player.y  = spawn_y
        self.local_map = new_map
        self.entities  = [self.player] + new_entities
        self.current_submap_id = None
        self._update_fov()
        chunk = self.world_map.get(self.world_x, self.world_y)
        label = (chunk.name if chunk and chunk.name else "the surface")
        self.log.add_world(f"You emerge into {label}.")
        self._update_context_prompt()

    def _spawn_layout_entities(self, layout_entities: list) -> list:
        """
        Convert layout entity dicts returned by generate_submap into real
        Item / Actor instances and return them as a list.
        """
        result = []
        for spec in layout_entities:
            kind = spec.get("kind")
            x, y = spec["x"], spec["y"]
            if kind == "item":
                item_id = spec.get("item_id", "")
                text_id = spec.get("text_id", "")
                item = self.item_factory.create(item_id, x, y)
                if item is not None:
                    if text_id:
                        item.text_id = text_id
                    result.append(item)
            # "body" type — skip for now (Tier 2 content)
        return result

    # ------------------------------------------------------------------ #
    #  _update_context_prompt
    # ------------------------------------------------------------------ #

    def _update_context_prompt(self) -> None:
        """Refresh the status-bar context prompt based on tile under player."""
        if not hasattr(self, "ui"):
            return
        terrain = str(self.local_map.tiles["terrain"][self.player.x, self.player.y])
        if terrain == "stairs_down":
            self.ui.set_context_prompt("[ > ] Descend", (226, 181, 112))
        elif terrain == "stairs_up":
            self.ui.set_context_prompt("[ < ] Ascend", (129, 175, 181))
        elif terrain == "door_closed":
            self.ui.set_context_prompt("Walk into door to open", (160, 150, 120))
        else:
            self.ui.clear_context_prompt()

    # ------------------------------------------------------------------ #
    #  FOV + lighting
    # ------------------------------------------------------------------ #

    def _update_fov(self) -> None:
        import math as _math
        from engine.engine import GameMode
        
        if getattr(self, "mode", None) == GameMode.OVERMAP:
            # Reveal the map grid
            self.local_map.tiles["visible"][:] = True
            self.local_map.tiles["explored"][:] = True
            
            # Set the lighting multiplier to 1.0 (True Color)
            if hasattr(self, "light_map"):
                self.light_map.fill(1.0)
            
            self._update_last_known_positions()
            return
        # Recalculate wraith penalty fresh from current entity positions.
        # This ensures every FOV call — post-move, turn-end, etc. — sees
        # the correct penalty without staleness from ability execution order.
        wraith_penalty = 0
        for _e in self.entities:
            if _e.tile == "bog_wraith":
                _dist = _math.sqrt(
                    (_e.x - self.player.x) ** 2 +
                    (_e.y - self.player.y) ** 2
                )
                if _dist <= 8:
                    wraith_penalty = max(wraith_penalty, max(0, int(8 - _dist)))
        self.player._wraith_fov_penalty = wraith_penalty

        needs   = getattr(self.player, "needs",        None)
        corrupt = getattr(self.player, "corruption",   None)
        light   = getattr(self.player, "light_source", None)

        from config import DARK_VISION_RADIUS

        # ── Zone ambient ─────────────────────────────────────────────
        chunk        = self.world_map.get(self.world_x, self.world_y)
        zone_ambient = 0.0
        is_outdoor   = True

        if chunk:
            for zone_id, _ in chunk.zones:
                zone = self.data.zones.get(zone_id)
                if zone:
                    zone_ambient = zone.get("ambient_light", 1.0)
                    if zone.get("category") == "dungeon":
                        is_outdoor = False
                    break

        ambient_intensity, _ = self.world_time.get_ambient_light(
            zone_ambient, is_outdoor
        )

        # ── Active FOV radius (live — entities visible here) ─────────
        # Step 1: gather all radius sources and take the largest
        ambient_sight = int(FOV_RADIUS * ambient_intensity * 3)
        torch_sight   = light.effective_radius() \
                        if (light and light.active) else 0
        active_radius = max(ambient_sight, torch_sight, DARK_VISION_RADIUS)

        # Step 2: apply all penalties AFTER combining sources so that
        # a large torch radius does not cancel out the wraith drain.
        if needs:
            active_radius -= needs.fov_penalty
        if corrupt:
            active_radius -= corrupt.fov_penalty
        active_radius -= wraith_penalty  # already computed above from entity scan

        overcorrect = getattr(self.player, "_wraith_overcorrect", 0)
        if overcorrect > 0:
            active_radius += 3
            self.player._wraith_overcorrect = overcorrect - 1

        active_radius = max(2, active_radius)

        # ── Active visible mask (circle) ─────────────────────────────
        raw_fov = tcod.map.compute_fov(
            self.local_map.transparent,
            (self.player.x, self.player.y),
            radius=active_radius,
        )

        w  = self.local_map.width
        h  = self.local_map.height
        xs = np.arange(w).reshape(w, 1)
        ys = np.arange(h).reshape(1, h)
        dist_sq     = (xs - self.player.x)**2 + (ys - self.player.y)**2
        circle_mask = dist_sq <= (active_radius ** 2)

        visible = raw_fov & circle_mask
        self.local_map.tiles["visible"][:] = visible

        # ── Passive memory — lit zones only ──────────────────────────
        # In well-lit areas, cast sightlines to map edge and commit
        # everything reachable to explored (memory) even beyond active FOV.
        # Tiles are remembered but not live — entities won't show there.
        if ambient_intensity > 0.4:
            # Full raycast to map edge — no radius cap
            passive_fov = tcod.map.compute_fov(
                self.local_map.transparent,
                (self.player.x, self.player.y),
                radius=0,   # 0 = unlimited in tcod
            )
            # Only commit to memory — do not mark as visible
            self.local_map.tiles["explored"] |= passive_fov
        else:
            # Dark zone — only remember what's in active FOV
            self.local_map.tiles["explored"] |= visible

        self._update_light_map()
        self._update_last_known_positions()

    def _update_last_known_positions(self) -> None:
        """After each FOV update, record current position for visible entities."""
        for entity in self.entities:
            if entity is self.player:
                continue
            if getattr(entity, "ai", None) is None:
                continue  # skip items and non-creatures
            if not self.local_map.in_bounds(entity.x, entity.y):
                continue
            if bool(self.local_map.tiles[entity.x, entity.y]["visible"]):
                entity.last_known_x = entity.x
                entity.last_known_y = entity.y

    def _update_light_map(self) -> None:
        lm    = self.local_map.light_map
        lm[:] = 0.0

        fov          = self.local_map.tiles["visible"]
        chunk        = self.world_map.get(self.world_x, self.world_y)
        is_outdoor   = True
        zone_ambient = 1.0

        if chunk:
            for zone_id, _ in chunk.zones:
                zone = self.data.zones.get(zone_id)
                if zone:
                    zone_ambient = zone.get("ambient_light", 1.0)
                    if zone.get("category") == "dungeon":
                        is_outdoor = False
                    break

        intensity, amb_color = self.world_time.get_ambient_light(
            zone_ambient, is_outdoor
        )

        lm[fov, 0] = amb_color[0] * intensity
        lm[fov, 1] = amb_color[1] * intensity
        lm[fov, 2] = amb_color[2] * intensity

        for entity in self.entities:
            light = getattr(entity, "light_source", None)
            if light:
                light.apply_to_light_map(lm, entity.x, entity.y, fov)

    # ------------------------------------------------------------------ #
    #  Combat
    # ------------------------------------------------------------------ #

    def _get_blocking_entity(self, x: int, y: int) -> "Actor | None":
        for entity in self.entities:
            if entity is self.player:
                continue
            if entity.x == x and entity.y == y:
                if getattr(entity, "blocks_movement", False):
                    return entity
        return None

    # ------------------------------------------------------------------ #
    #  Line-of-sight check for adjacent attacks
    # ------------------------------------------------------------------ #

    @staticmethod
    def _has_line_of_sight_adjacent(
        local_map, x1: int, y1: int, x2: int, y2: int
    ) -> bool:
        """
        Return True if (x1,y1) and (x2,y2) share an open face — i.e. the
        shared edge is not blocked by a wall on either side.

        For adjacent tiles (Chebyshev distance 1) this reduces to:
        - Both tiles are walkable (non-wall), OR
        - At least one of the two cells on the shared face is walkable.

        In practice: block the attack only when a solid wall (non-walkable,
        non-transparent tile) sits between attacker and target.
        We check walkability as the wall proxy (matches what the rest of the
        code uses for movement blocking).
        """
        import math as _math
        if _math.fabs(x2 - x1) > 1 or _math.fabs(y2 - y1) > 1:
            # Not adjacent — not handled here; allow by default
            return True
        # Both in-bounds check
        if not local_map.in_bounds(x1, y1) or not local_map.in_bounds(x2, y2):
            return False
        # If either tile is a solid wall, no LOS (one is the attacker's tile
        # so this would be unusual, but guard it)
        if not local_map.walkable[x1, y1] or not local_map.walkable[x2, y2]:
            return False
        # Diagonal attacks: also check that at least one of the two orthogonal
        # corner tiles is open (wall-corner blocking)
        dx = x2 - x1
        dy = y2 - y1
        if dx != 0 and dy != 0:
            corner_a = local_map.walkable[x1 + dx, y1]
            corner_b = local_map.walkable[x1, y1 + dy]
            if not corner_a and not corner_b:
                return False
        return True

    def _player_attack(self, target: "Actor") -> None:
        from engine.combat import resolve_attack
        import random as _random

        player_fighter = getattr(self.player, "fighter", None)
        target_fighter = getattr(target,      "fighter", None)
        if not player_fighter or not target_fighter:
            return

        # Check impairment
        if not player_fighter.can_attack():
            self.log.add("Thou canst not strike.", (160, 140, 100))
            return

        # Check line of sight (wall blocking)
        if not self._has_line_of_sight_adjacent(
            self.local_map, self.player.x, self.player.y, target.x, target.y
        ):
            self.log.add("Something stands between thee and thy mark.", (160, 140, 100))
            return

        # Get equipped weapon (or None for unarmed)
        weapon = self._get_equipped_weapon()

        # Get body def for target
        body_id  = target_fighter.body_id
        body_def = self.data.bodies.get(body_id, {})

        # Fallback: if no body def, use legacy combat
        if not body_def:
            actual = target_fighter.take_damage(player_fighter.power)
            if actual == 0:
                self.log.add(
                    f"You strike the {target.name} but do no damage.",
                    (160, 140, 100),
                )
            else:
                self.log.add(
                    f"You strike the {target.name} for {actual} damage.",
                    (188, 89, 96),
                )
            if target_fighter.is_dead:
                self._on_entity_death(target)
            return

        creature_essence_mods = self.data.entities.get(target.tile, {}).get(
            "essence_modifiers", {}
        )

        rng = _random.Random()
        disrupted = getattr(self.player, "_hollow_knight_disruption", False)

        result = resolve_attack(
            attacker_name         = "thou",
            defender_name         = target.name,
            defender_fighter      = target_fighter,
            body_def              = body_def,
            weapon                = weapon,
            creature_essence_mods = creature_essence_mods,
            rng                   = rng,
            attacker_disrupted    = disrupted,
        )

        # Log messages — outgoing damage (player→creature): mist_blue family
        for msg, mtype in zip(result.messages, result.message_types):
            if mtype == "deflect":
                color = (99, 120, 140)       # slate_mid — dim, neither triumph nor threat
            elif mtype == "impair":
                color = (145, 58, 82)        # blood_rose — creature impaired
            else:                            # hit / death
                color = (129, 175, 181)      # mist_blue
            self.log.add(f"› {msg}", color)
        if result.damage_number > 0:
            self.log.add(f"  {result.damage_number} damage.", (180, 220, 225))  # bright mist_blue

        if result.defender_dead:
            self._on_entity_death(target)

        # Briar lurker retaliation — thorns on melee contact
        if target.tile == "briar_lurker" and result.damage_dealt > 0:
            thorn = _random.randint(1, 2)
            if player_fighter:
                torso_hp = player_fighter.location_hp.get("torso", 0)
                player_fighter.location_hp["torso"] = max(0, torso_hp - thorn)
                self.log.add(
                    "The briars find thee as thou strikest.",
                    (57, 117, 92),
                )
                self.log.add(f"  {thorn} damage.", (93, 167, 93))
                self.player.took_damage_this_turn = True
                if player_fighter.location_hp.get("torso", 1) <= 0:
                    self._on_player_death()

    def _get_equipped_weapon(self) -> dict | None:
        """Return equipped weapon item dict, or None for unarmed."""
        equipment = getattr(self.player, "equipment", None)
        if not equipment:
            return None
        weapon_item = equipment.slots.get("weapon")
        if not weapon_item:
            return None
        return self.data.items.get(weapon_item.item_id)

    def _on_entity_death(self, entity: "Actor") -> None:
        from engine.message_log import MSG_DANGER
        from entities.item import Item

        self.log.add(f"The {entity.name} is destroyed.", MSG_DANGER)
        entity.is_alive = False

        corpse = Item(
            x    = entity.x,
            y    = entity.y,
            tile = "corpse",
            name = f"remains of {entity.name}",
        )
        self.entities.append(corpse)

        # Bog wraith death — lift FOV drain, brief overcorrection
        if entity.tile == "bog_wraith":
            self.player._wraith_fov_penalty  = 0
            self.player._wraith_overcorrect  = 3
            self.log.add(
                "The forgetting lifts. "
                "The world rushes back — too much of it, briefly.",
                (63, 160, 164),
            )
            self._update_fov()

    def _on_player_death(self) -> None:
        from engine.message_log import MSG_DANGER

        self.trigger_screenshake(6.0)
        self.log.add_danger("You are dead.")
        self.log.add(
            "The world continues without you. "
            "It does not notice.",
            (145, 58, 82),
        )

        # Delete save so next run starts fresh
        import shutil
        from pathlib import Path
        save_path = Path("saves")
        if save_path.exists():
            shutil.rmtree(save_path)

        # Show death screen — render a few frames so the player can read it
        # The run loop will handle the actual display
        self._player_is_dead = True

    def _render_death_screen(self, screen: pygame.Surface) -> None:
        sw = screen.get_width()
        sh = screen.get_height()

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((7, 12, 29, 220))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.SysFont("monospace", 32)
        font_small = pygame.font.SysFont("monospace", 16)

        title  = font_large.render("YOU ARE DEAD", True, (188, 89, 96))
        sub    = font_small.render(
            "The world continues without you. It does not notice.",
            True, (99, 34, 64)
        )
        prompt = font_small.render(
            "Press any key to exit.",
            True, (50, 73, 95)
        )

        screen.blit(title,  (sw//2 - title.get_width()//2,  sh//2 - 60))
        screen.blit(sub,    (sw//2 - sub.get_width()//2,    sh//2 - 10))
        screen.blit(prompt, (sw//2 - prompt.get_width()//2, sh//2 + 30))

    # ------------------------------------------------------------------ #
    #  Items
    # ------------------------------------------------------------------ #

    def _pick_up_item(self) -> None:
        inv = getattr(self.player, "inventory", None)
        if not inv:
            return

        items_here = self._items_at(self.player.x, self.player.y)

        if items_here:
            self._take_item(items_here[-1], inv)
        else:
            adjacent = self._adjacent_items()
            if not adjacent:
                self.log.add(
                    "There is nothing here or nearby to take.",
                    (160, 150, 130),
                )
                return
            self._pickup_mode = True
            self.log.add(
                "Pick up from where? (movement key, ESC to cancel)",
                (180, 170, 140),
            )

    def _items_at(self, x: int, y: int) -> list:
        return [
            e for e in self.entities
            if (e is not self.player and
                e.x == x and e.y == y and
                hasattr(e, "item_id"))
        ]

    def _adjacent_items(self) -> list:
        results = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue
                results.extend(
                    self._items_at(
                        self.player.x + dx,
                        self.player.y + dy,
                    )
                )
        return results

    def _take_item(self, item: "Item", inv: "Inventory") -> None:
        if inv.is_full:
            self.log.add(
                f"You cannot carry the {item.name}. "
                f"You are overburdened.",
                (200, 150, 80),
            )
            return
        if inv.add(item):
            self.entities.remove(item)
            self.log.add(f"You take the {item.name}.", (180, 165, 130))

    # ------------------------------------------------------------------ #
    #  Spawn safety
    # ------------------------------------------------------------------ #

    def _find_walkable_near(
        self,
        local_map: "LocalMap",
        x: int,
        y: int,
        max_radius: int = 10,
    ) -> tuple[int, int]:
        if local_map.in_bounds(x, y) and local_map.walkable[x, y]:
            return x, y
        for radius in range(1, max_radius + 1):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    nx, ny = x + dx, y + dy
                    if (local_map.in_bounds(nx, ny) and
                            local_map.walkable[nx, ny]):
                        return nx, ny
        return local_map.width // 2, local_map.height // 2


# ------------------------------------------------------------------ #
#  Module-level helpers
# ------------------------------------------------------------------ #

def _deserialize_entities_inline(
    entity_dicts: list[dict],
    engine: "Engine",
) -> list:
    from engine.save_manager import _deserialize_entities
    return _deserialize_entities(entity_dicts, engine)

def _render_death_screen(self, screen: pygame.Surface) -> None:
        """
        Full-screen death message. Press any key to exit.
        Clears on keypress — add to event handling.
        """
        sw = screen.get_width()
        sh = screen.get_height()

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((7, 12, 29, 220))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.SysFont("monospace", 32)
        font_small = pygame.font.SysFont("monospace", 16)

        title  = font_large.render("YOU ARE DEAD", True, (188, 89, 96))
        sub    = font_small.render(
            "The world continues without you. It does not notice.",
            True, (99, 34, 64)
        )
        prompt = font_small.render(
            "Press any key to exit.",
            True, (50, 73, 95)
        )

        screen.blit(title,  (sw//2 - title.get_width()//2,  sh//2 - 60))
        screen.blit(sub,    (sw//2 - sub.get_width()//2,    sh//2 - 10))
        screen.blit(prompt, (sw//2 - prompt.get_width()//2, sh//2 + 30))