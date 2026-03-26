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
from rendering.perk_screen import PerkScreen

from typing import TYPE_CHECKING
from engine.palette import *
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
from engine.reality_bubble import RealityBubble


def _apply_effects(effects: dict, engine: "Engine") -> None:
    """
    Apply a merged effects dict returned by hooks.fire().
    Handles all defined effect keys.
    Called after every hook.fire() at a dispatch site.
    """
    if not effects:
        return

    player = engine.player

    # Messages — add_message is collected as a list of {text, color} dicts
    for msg in effects.get("add_message", []):
        engine.log.add(msg["text"], color=msg["color"])

    # Healing — heal the least damaged body part
    if "heal" in effects:
        _heal_least_damaged(player, int(effects["heal"]))

    # Status application / removal (stubs — expand with status system)
    if "add_status" in effects:
        pass   # wired when status system is implemented
    if "remove_status" in effects:
        pass

    # Ephemeral terrain placement
    if "place_terrain" in effects:
        pt = effects["place_terrain"]
        engine.place_ephemeral_tile(pt["x"], pt["y"], pt["terrain_id"])

    # Level up
    if effects.get("level_up"):
        _do_level_up(player, engine)

    # Corruption / resonance exposure
    if "add_corruption" in effects:
        corr = getattr(player, "corruption", None)
        if corr:
            corr.value = min(1.0, getattr(corr, "value", 0.0) + effects["add_corruption"])
    if "add_resonance" in effects:
        engine.resonance_exposure = (
            getattr(engine, "resonance_exposure", 0.0) + effects["add_resonance"]
        )


def _do_level_up(player: "Actor", engine: "Engine") -> None:
    """Handle a level-up: increment level, carry-over exp, scale body HP, award perk point."""
    lc = getattr(player, "level", None)
    if lc is None:
        return
    lc.level               += 1
    lc.total_levels_gained += 1
    lc.exp                 -= lc.exp_to_next
    if lc.exp < 0:
        lc.exp = 0
    lc.exp_to_next  = lc.exp_threshold(lc.level)
    lc.perk_points += 1

    # Scale body part HP by 1.08
    fighter = getattr(player, "fighter", None)
    if fighter:
        loc_hp  = getattr(fighter, "location_hp",  {})
        loc_max = getattr(fighter, "location_max", {})
        for loc in list(loc_max.keys()):
            old_max          = loc_max[loc]
            new_max          = max(1, int(old_max * 1.08))
            gain             = new_max - old_max
            loc_max[loc]     = new_max
            loc_hp[loc]      = loc_hp.get(loc, old_max) + gain

    engine.log.add("Something shifts in you.", OLD_GOLD)   # old_gold
    engine.log.add("A perk point awaits. Press K to spend it.", STONE_BLUE)   # slate_mid


def _heal_least_damaged(player: "Actor", amount: int) -> None:
    """Heal `amount` HP to the body part with the most room to heal."""
    fighter = getattr(player, "fighter", None)
    if not fighter:
        return
    loc_hp  = getattr(fighter, "location_hp",  None)
    loc_max = getattr(fighter, "location_max", None)
    if not loc_hp or not loc_max:
        return
    # Find the location with the most healing room (max_hp - current_hp)
    best_loc  = None
    best_room = -1
    for loc, cur in loc_hp.items():
        room = loc_max.get(loc, cur) - cur
        if room > best_room:
            best_room = room
            best_loc  = loc
    if best_loc is None or best_room <= 0:
        return   # all parts at max — nothing to heal
    fighter.location_hp[best_loc] = min(
        loc_hp[best_loc] + amount, loc_max.get(best_loc, loc_hp[best_loc] + amount)
    )


# Unarmed combat profile — used when no weapon is equipped.
# Perks that enhance unarmed should modify a copy of this dict.
_UNARMED_PROFILE: dict = {
    "damage_dice":      "1d4",
    "damage_bonus":     0,
    "essence":          None,
    "essence_strength": 0.0,
    "name":             "bare hands",
    "reach":            1,
}

# Module-level resonance message register
_RESONANCE_MESSAGES: dict[str, list[tuple[str, tuple]]] = {
    "very_low": [
        ("The air here sits still. Old quiet.",                STONE_BLUE),
        ("Nothing hums. The stones here are different stone.", STONE_BLUE),
        ("Thy bones are easy in this place.",                  STONE_BLUE),
    ],
    "low": [
        ("A faint weight in the air. Nothing more.",           STONE_BLUE),
        ("The ground holds something old but spent.",          STONE_BLUE),
        ("Familiar. Not comfortable, but familiar.",           STONE_BLUE),
    ],
    "moderate": [
        ("Something accumulates in the silence here.",         STONE_BLUE),
        ("Thy teeth know this place before thy eyes do.",      STONE_BLUE),
        ("The grey stone is close. Not close enough to matter. Yet.",
                                                               STONE_BLUE),
    ],
    "high": [
        ("The resonance is in the walls here. Old, deep, patient.",
                                                               BLOOD_STONE),
        ("Thy bones remember something they were not present for.",
                                                               BLOOD_STONE),
        ("This place has been sung to for a very long time.",  BLOOD_STONE),
    ],
    "very_high": [
        ("The tone is almost audible. Almost.",                BLOOD_STONE),
        ("Every grey stone here is a held breath.",            BLOOD_STONE),
        ("Thou shouldst not linger. Something in thee agrees.",BLOOD_STONE),
    ],
    "intact_bell": [
        ("The bell is close. Do not touch it.",                DRIED_BLOOD),
        ("Something in thee goes quiet. The rest of thee does not know why.",
                                                               DRIED_BLOOD),
        ("The tone is present. Beneath hearing. In the bone.", DRIED_BLOOD),
    ],
}


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
        self.perk_screen      = PerkScreen()
        self.text_reader      = TextReader()
        self._pickup_mode:    bool = False
        self._player_is_dead:   bool = False
        self._death_killer:     str  = "unknown"
        self._death_messages:   list = []
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
        self.debug_move_log:    bool = False
        self._quit_pending:     bool = False
        # Resonance zone tracking
        self._resonance_tier: str  = "very_low"
        self._bell_warned:    bool = False
        # Set of town_ids the player has already been announced for this session
        self._entered_town_ids: set[int] = set()
        # Reality bubble — tracks which chunks are active this turn
        self.reality_bubble = RealityBubble()
        # Terrain movement debt and concealment
        self._move_debt:             float = 0.0
        self._player_in_concealment: bool  = False

        # Resonance / corruption state
        self.resonance_exposure:     float = 0.0
        self.corruption:             float = 0.0
        self.wind_turn:              int   = 0
        self._last_exposure_tier:    int   = 0
        self._corruption_thresholds: set   = set()
        self._discharge_flash:       tuple | None = None
        self._discharge_flash_turns: int   = 0
        self._log_scroll:            int   = 0

        # Seeded RNG for in-game systems (discharge, weather, wind)
        self.rng = random.Random(getattr(world_map, "seed", None))

        # Weather
        from engine.weather import WeatherSystem
        self.weather = WeatherSystem(self.rng)

        # Particle system (visual only — no game state)
        from rendering.particles import ParticleSystem
        self.particle_system = ParticleSystem()
        self._waystone_pulse_timers: dict = {}   # (tx,ty) → next_pulse_time
        self._last_weather_state: str = "clear"
        self._particle_map_id: int = 0           # detect map changes
        self._last_frame_time: float = 0.0       # for dt calculation
        # Fog vignette cache — rebuilt when intensity / type / size / fov / centre changes
        self._fog_surface:           "pygame.Surface | None" = None
        self._fog_surface_intensity: float                   = -1.0
        self._fog_surface_type:      str                     = ""
        self._fog_surface_size:      tuple                   = (0, 0)
        self._fog_surface_fov:       int                     = -1
        self._fog_surface_cx:        int                     = -1
        self._fog_surface_cy:        int                     = -1
        self._effective_fov_radius:  int                     = 8
        # Deferred blood emissions — resolved to screen coords in the render loop
        self._pending_blood: list = []
        # Callout system — floating text above entities (damage, sounds, status)
        from rendering.callouts import CalloutSystem
        self.callouts = CalloutSystem()
        # Deferred creature sound callouts — resolved from AI turns
        self._pending_callouts: list = []

        # Hook registry — perk/system event dispatch
        from engine.hooks import HookRegistry, HookEvent
        from engine.perk_handlers import system_exp_on_kill
        from engine.resonance_system import (
            system_resonance_on_turn,
            system_resonance_on_tile_entered,
            system_resonance_chunk_entered,
        )
        self.hooks = HookRegistry()
        self.hooks.register(HookEvent.ON_ENTITY_KILLED,  system_exp_on_kill)
        self.hooks.register(HookEvent.ON_TURN,           system_resonance_on_turn)
        self.hooks.register(HookEvent.ON_TILE_ENTERED,   system_resonance_on_tile_entered)
        self.hooks.register(HookEvent.ON_CHUNK_ENTERED,  system_resonance_chunk_entered)
        self._register_player_perks()

    @property
    def map_width(self) -> int:
        return self.local_map.width

    @property
    def map_height(self) -> int:
        return self.local_map.height

    def get_terrain(self, x: int, y: int) -> str:
        """Public wrapper — returns terrain id at local tile (x, y)."""
        return self._resolve_terrain_id(x, y)

    def _scan_waystone_timers(self) -> None:
        """
        Scan the current local map for waystone_plinth tiles and initialise
        pulse timers for any not already tracked.  Called when map changes.
        """
        import random as _rand
        import time as _time
        now = _time.monotonic()
        for x in range(self.local_map.width):
            for y in range(self.local_map.height):
                if not self.local_map.in_bounds(x, y):
                    continue
                t = self.local_map.tiles[x, y]["terrain"]
                if isinstance(t, bytes):
                    t = t.decode()
                if str(t) == "waystone_plinth":
                    key = (x, y)
                    if key not in self._waystone_pulse_timers:
                        offset = _rand.uniform(0, 60)
                        self._waystone_pulse_timers[key] = (
                            now + 60 + offset)

    def place_ephemeral_tile(self, x: int, y: int, terrain_id: str) -> None:
        """Place a transient terrain tile that is cleared on chunk re-entry."""
        if not self.local_map.in_bounds(x, y):
            return
        t = self.data.terrain.get(terrain_id, {})
        orig_terrain = self._resolve_terrain_id(x, y)
        self.local_map.set_tile(x, y, terrain_id,
                                t.get("walkable", True),
                                t.get("transparent", True))
        chunk = self.world_map.get(self.world_x, self.world_y)
        if chunk is not None:
            chunk.ephemeral_tiles.append((x, y, orig_terrain))

    def _register_player_perks(self) -> None:
        """
        Register hook handlers for all perks the player currently has.
        Called on game start and after any perk is gained or lost.
        """
        from engine.hooks import HookEvent
        from engine.perk_handlers import HANDLER_MAP

        # Clear any previously registered perk handlers
        for event in HookEvent:
            self.hooks._handlers[event] = [
                h for h in self.hooks._handlers[event]
                if not getattr(h, "_is_perk_handler", False)
            ]

        perks = getattr(self.player, "perks", None)
        if not perks:
            return
        for perk_id in perks.active_perks:
            perk_data = self.data.perks.get(perk_id)
            if not perk_data:
                continue
            for hook_def in perk_data.get("hooks", []):
                event_name   = hook_def.get("event", "")
                handler_name = hook_def.get("handler", "")
                try:
                    event = HookEvent[event_name]
                except KeyError:
                    print(f"[perks] unknown event '{event_name}' in perk '{perk_id}'")
                    continue
                handler = HANDLER_MAP.get(handler_name)
                if handler:
                    self.hooks.register(event, handler)
                else:
                    print(f"[perks] unknown handler '{handler_name}' in perk '{perk_id}'")

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
        self.perk_screen.init(self.display)
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
            SLATE_MID,
        )
        self.log.add(
            "Thou art beneath the ground. "
            "Something is wrong with the world above.",
            DRIED_BLOOD,
        )

        level_comp = getattr(self.player, "level", None)
        if (self.world_time.turn == 0
                and level_comp is not None
                and level_comp.perk_points > 0):
            self.log.add(
                "A point waits to be spent. Press K.",
                OLD_GOLD,
            )

        while True:
            sw  = screen.get_width()
            sh  = screen.get_height()

            game_panel_rect = pygame.Rect(0, 0, sw - MSG_PANEL_W, sh - STATUS_BAR_H)
            msg_panel       = pygame.Rect(sw - MSG_PANEL_W, 0, MSG_PANEL_W, sh - STATUS_BAR_H)
            status_bar      = pygame.Rect(0, sh - STATUS_BAR_H, sw, STATUS_BAR_H)

            # Inset tile viewport by UI_PANEL_INSET (border) + MAP_INSET (gap) on
            # all four sides so the map sits 2px inside the decorative border line.
            # No context strip — viewport extends to UI_PANEL_INSET above status bar.
            _MAP_INSET = 2
            viewport = pygame.Rect(
                UI_PANEL_INSET + _MAP_INSET,
                UI_PANEL_INSET + _MAP_INSET,
                sw - MSG_PANEL_W - 2 * (UI_PANEL_INSET + _MAP_INSET),
                sh - STATUS_BAR_H - 2 * (UI_PANEL_INSET + _MAP_INSET),
            )
            if not getattr(self, "_layout_printed", False):
                self._layout_printed = True
                print(f"[layout] sh={sh} sw={sw}")
                print(f"[layout] STATUS_BAR_H={STATUS_BAR_H}")
                print(f"[layout] strip_h=0")
                print(f"[layout] UI_PANEL_INSET={UI_PANEL_INSET}")
                print(f"[layout] MAP_INSET={_MAP_INSET}")
                print(f"[layout] viewport={viewport}")
                print(f"[layout] viewport.bottom={viewport.bottom}")

            self._viewport   = viewport
            self._msg_panel  = msg_panel
            self._status_bar = status_bar

            current_ticks = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit()

                if event.type in (pygame.VIDEORESIZE, pygame.WINDOWRESIZED):
                    screen.fill(VOID_BLACK)
                    continue

                if event.type == pygame.KEYDOWN:
                    # Clear pending quit on any non-ESC key
                    if event.key != pygame.K_ESCAPE:
                        self._quit_pending = False

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
            screen.fill(VOID_BLACK)

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
                screen.fill(VOID_BLACK, game_panel_rect)
                cam_x, cam_y = self._get_camera(viewport)
                shake_offset = self._update_screenshake()
                self.visual_events.tick()
                renderer.render(
                    screen, self.local_map, self.entities,
                    cam_x, cam_y, viewport,
                    shake_offset=shake_offset,
                    visual_events=self.visual_events.get_active(),
                    void_rect=game_panel_rect,
                    player_x=self.player.x,
                    player_y=self.player.y,
                )
                if self.mode == GameMode.LOOK:
                    self.look_mode.render_cursor(screen, self, cam_x, cam_y)
                    self.look_mode.render_hint_overlay(screen, viewport, self.display)
                    if self.look_mode.examining:
                        self.look_mode.render_examine_popup(screen, self)

                # --- Particle system (steps 4-9) ---
                # Skip when any screen overlay is open
                _overlay_open = (
                    self.inventory_screen.open or
                    self.perk_screen.open or
                    self.text_reader.open
                )
                if not _overlay_open:
                    import time as _time
                    _now = _time.monotonic()
                    _dt  = _now - self._last_frame_time if self._last_frame_time > 0 else 1/60
                    _dt  = min(_dt, 0.1)   # cap at 100ms to avoid spiral on freeze
                    self._last_frame_time = _now

                    # Scan local map for waystones when map changes
                    if self._particle_map_id != id(self.local_map):
                        self._particle_map_id = id(self.local_map)
                        self._scan_waystone_timers()

                    # Step 4: sync weather emitters
                    from rendering.particles import update_weather_emitters
                    update_weather_emitters(self)

                    # Step 5: update particle system
                    _zoom   = self.display.zoom_level
                    _tw, _th = renderer._tile_wh()
                    _tile_w  = _tw * _zoom
                    _tile_h  = _th * _zoom
                    self.particle_system.update(
                        _dt, viewport.width, viewport.height, _zoom)

                    # Waystone pulse check
                    import random as _rand
                    from rendering.particles import make_waystone_ring as _mwr
                    for (_wtx, _wty), _next_t in list(
                            self._waystone_pulse_timers.items()):
                        if _now >= _next_t:
                            if self.local_map.in_bounds(_wtx, _wty):
                                _terrain = self._resolve_terrain_id(_wtx, _wty)
                                if _terrain == "waystone_plinth":
                                    self.particle_system.emit(
                                        _mwr(_wtx, _wty, _rand.Random()))
                            self._waystone_pulse_timers[(_wtx, _wty)] = (
                                _now + _rand.uniform(60, 90))

                    # Sparkle emitter pass — scan visible tiles with visual_fx="sparkle"
                    # Probability ~1/second per tile (seed-driven, stable per frame).
                    _SPARKLE_COLORS = {
                        "waystone_plinth": RESONANCE_BLOOM,
                        "coldbell_flower": SPIRIT_BLUE,
                        "ectoplasm_pool":  COLDBELL_LIGHT,
                        "ichor_seep":      VOID_PURPLE,
                    }
                    _SPARKLE_PROB = 66   # 1/66 chance per frame ≈ 1/second at 60fps
                    _frame_tick = int(_now * 60)
                    _tiles_x = int(viewport.width  / _tile_w) + 2
                    _tiles_y = int(viewport.height / _tile_h) + 2
                    from rendering.particles import make_sparkle as _ms
                    import random as _spk_rng
                    for _my in range(cam_y, cam_y + _tiles_y):
                        for _mx in range(cam_x, cam_x + _tiles_x):
                            if not self.local_map.in_bounds(_mx, _my):
                                continue
                            if not self.local_map.visible[_mx, _my]:
                                continue
                            _t = self._resolve_terrain_id(_mx, _my)
                            if _t not in _SPARKLE_COLORS:
                                continue
                            _seed = (_frame_tick + _mx * 7919 + _my * 104729) & 0xFFFF
                            if _seed % _SPARKLE_PROB != 0:
                                continue
                            self.particle_system.emit(
                                _ms(_mx, _my, _SPARKLE_COLORS[_t],
                                    _spk_rng.Random(_seed)))

                    # Resolve deferred blood emissions: convert tile coords to
                    # screen coords here where cam/tile size are all available.
                    if self._pending_blood:
                        from rendering.particles import (
                            make_blood_particles as _mbp,
                            make_crit_impact_sparkles as _mcis,
                        )
                        import random as _brng
                        _mo_x = viewport.x + shake_offset[0]
                        _mo_y = viewport.y + shake_offset[1]
                        for _evt in self._pending_blood:
                            _dx, _dy = _evt["defender_tile"]
                            _ax, _ay = _evt["attacker_tile"]
                            _dsx = int(_mo_x + (_dx - cam_x) * _tile_w + _tile_w // 2)
                            _dsy = int(_mo_y + (_dy - cam_y) * _tile_h + _tile_h // 2)
                            _asx = int(_mo_x + (_ax - cam_x) * _tile_w + _tile_w // 2)
                            _asy = int(_mo_y + (_ay - cam_y) * _tile_h + _tile_h // 2)
                            if _evt.get("is_crit", False):
                                # Enhanced crit blood burst + impact sparkles
                                self.particle_system.emit_burst(
                                    _mbp(_dsx, _dsy, _evt["color"], _asx, _asy,
                                         count=_brng.randint(16, 20),
                                         speed_range=(120.0, 340.0),
                                         size_range=(3.0, 6.0),
                                         lifetime_range=(0.5, 1.0)))
                                self.particle_system.emit_burst(
                                    _mcis(_dsx, _dsy, _evt["color"],
                                          count=_brng.randint(4, 6)))
                            else:
                                self.particle_system.emit_burst(
                                    _mbp(_dsx, _dsy, _evt["color"], _asx, _asy))
                        self._pending_blood.clear()

                    # Steps 6-7: draw particles (clipped to viewport)
                    # map_origin = viewport top-left + shake (NO cam offset).
                    # cam_x/cam_y passed separately so draw() applies them
                    # correctly per particle space (world vs screen).
                    screen.set_clip(viewport)
                    self.particle_system.draw(
                        screen, _tile_w, _tile_h,
                        viewport.x + shake_offset[0],
                        viewport.y + shake_offset[1],
                        cam_x=cam_x,
                        cam_y=cam_y,
                        viewport_w=viewport.width,
                        viewport_h=viewport.height,
                    )
                    screen.set_clip(None)

                    # Player screen pos relative to viewport top-left
                    # Used by both precipitation vignette and fog vignette.
                    _player_sx = int(shake_offset[0]
                                     + (self.player.x - cam_x) * _tile_w
                                     + _tile_w // 2)
                    _player_sy = int(shake_offset[1]
                                     + (self.player.y - cam_y) * _tile_h
                                     + _tile_h // 2)

                    # Step 8a: rain / snow tile-layer overlay (data-driven)
                    _wstate = self.weather.state
                    if _wstate in ("light_rain", "heavy_rain",
                                   "resonance_storm", "bone_snow"):
                        screen.set_clip(viewport)
                        renderer.draw_weather_overlay(
                            screen, viewport,
                            _wstate, self.weather.intensity,
                            self,
                            player_screen_x=viewport.x + _player_sx,
                            player_screen_y=viewport.y + _player_sy,
                            tile_w=_tile_w, tile_h=_tile_h,
                        )
                        screen.set_clip(None)

                    # Step 8b: fog vignette (cached on self, centred on player)
                    _wstate = self.weather.state
                    if _wstate in ("fog", "forgetting_fog"):
                        from rendering.particles import draw_fog_vignette
                        draw_fog_vignette(
                            screen, self.weather.intensity, _wstate,
                            rect=viewport, engine=self,
                            effective_fov=self._effective_fov_radius,
                            tile_w=_tile_w, tile_h=_tile_h,
                            centre_x=_player_sx, centre_y=_player_sy)

                    # Step 9: floating callouts
                    # Resolve deferred pending_callouts (from AI turns)
                    for _co in self._pending_callouts:
                        self.callouts.add(
                            _co["text"],
                            _co["world_x"], _co["world_y"],
                            _co["color"],
                            _co.get("lifetime", 1.5),
                            font_size=_co.get("font_size", "creature"),
                        )
                    self._pending_callouts.clear()
                    self.callouts.update(_dt)
                    _co_ox = viewport.x + shake_offset[0]
                    _co_oy = viewport.y + shake_offset[1]
                    self.callouts.draw(
                        screen,
                        self.display.CALLOUT_FONTS,
                        int(_tile_w), int(_tile_h),
                        int(_co_ox), int(_co_oy),
                        cam_x, cam_y,
                        viewport=viewport,
                    )

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
                        tint_color=STEEL_WATER,
                        fill_color=VOID_BLACK,
                        fill_alpha=0,
                        border_scale=2,
                    )
                    self.ui_registry.draw_panel(
                        screen, msg_panel, "weathered_temple",
                        tint_color=SLATE_DARK,
                        fill_color=VOID_BLACK,
                        fill_alpha=245,
                        border_scale=2,
                    )
                    self.ui_registry.draw_panel(
                        screen, status_bar, "weathered_temple",
                        tint_color=MIDNIGHT_DEEP,
                        fill_color=VOID_BLACK,
                        fill_alpha=245,
                        border_scale=2,
                    )
                else:
                    screen.fill(VOID_BLACK, msg_panel)
                    screen.fill(VOID_BLACK, status_bar)

                if self.mode == GameMode.LOOK:
                    self.look_mode.render_look_bar(screen, status_bar, self)
                else:
                    nearby = (
                        self._items_at(self.player.x, self.player.y) +
                        self._adjacent_items()
                    )
                    from config import DEBUG_MODE as _DM
                    _dbg = (
                        f"({self.player.x},{self.player.y})"
                        f" chunk({self.world_x},{self.world_y})"
                        f" t={self.world_time.turn}"
                    ) if _DM else None
                    self.ui.render_status(
                        screen, status_bar, self.player,
                        self.world_time,
                        nearby_items=nearby,
                        registry=self.registry,
                        resonance_exposure=self.resonance_exposure,
                        weather=self.weather.display_string,
                        weather_color=self.weather.display_color,
                        debug_info=_dbg,
                    )
                self.ui.render_messages(screen, msg_panel, self.log,
                                        scroll_offset=self._log_scroll)


            if self.debug:
                self.debug.render(screen, self)

            self.inventory_screen.render(screen, self)
            self.perk_screen.render(screen, self)

            if self.text_reader.open:
                self.text_reader.render(screen, self)

            # Discharge flash overlay (fades per rendered frame)
            if self._discharge_flash is not None:
                r, g, b, a = self._discharge_flash
                flash_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
                flash_surf.fill((r, g, b, a))
                screen.blit(flash_surf, (0, 0))
                a = max(0, a - 3)
                if a == 0:
                    self._discharge_flash = None
                else:
                    self._discharge_flash = (r, g, b, a)

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

    def _confirm_quit(self) -> bool:
        """Show 'Press ESC again to quit' on first ESC; quit on second."""
        if self._quit_pending:
            return True
        self._quit_pending = True
        self.log.add("Press ESC again to quit.", DUSTY_ROSE)
        return False

    # ------------------------------------------------------------------ #
    #  Turn advancement
    # ------------------------------------------------------------------ #

    def get_active_entities(self) -> list:
        # Step B: merge entities from all active_chunks when multi-chunk loading exists
        return self.entities

    def _advance_turn(self) -> None:
        from engine.hooks import HookEvent
        effects = self.hooks.fire(HookEvent.ON_TURN, {
            "turn":   self.world_time.turn,
            "player": self.player,
            "engine": self,
        })
        _apply_effects(effects, self)

        self.reality_bubble.update(self.world_x, self.world_y, self.world_map)
        self.world_time.advance()
        self.log.advance_turn()

        needs = getattr(self.player, "needs", None)
        if needs and not self.player_invincible:
            prev_h = needs.hunger
            prev_t = needs.thirst
            needs.advance()
            needs.drain_messages(self.log, prev_h, prev_t)

        # Plague crow sickness — accelerated needs drain (also suppressed by invincibility)
        sickness = getattr(self.player, "_sickness_turns", 0)
        if sickness > 0:
            self.player._sickness_turns = sickness - 1
            if needs and not self.player_invincible:
                needs.hunger = min(1.0, needs.hunger + 0.003)
                needs.thirst = min(1.0, needs.thirst + 0.005)

        # Chilled status countdown
        chilled = getattr(self.player, "chilled_turns", 0)
        if chilled > 0:
            self.player.chilled_turns = chilled - 1
            if self.player.chilled_turns == 0:
                self.log.add("The chill passes.", STONE_BLUE)

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
                    # Unequip from off-hand slot
                    equip = getattr(self.player, "equipment", None)
                    if equip and equip.slots.get("offhand") is item_ref:
                        equip.unequip("offhand")
                    # Remove burned-out torch from inventory
                    inv = getattr(self.player, "inventory", None)
                    if inv and item_ref in inv.items:
                        inv.remove(item_ref)
                    self._update_fov()
                    self.log.add_danger(
                        f"Your {item_ref.name} gutters and dies. "
                        f"You are in darkness."
                    )
                elif remaining == 60:
                    self.log.add(
                        f"Your {item_ref.name} is burning low.",
                        BELL_BRASS,
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
        # Death screen — R to restart (exit for re-launch), N to quit
        if self._player_is_dead:
            if key == pygame.K_r:
                pygame.quit()
                import sys
                sys.exit(0)
            elif key == pygame.K_n:
                import sys, shutil
                from pathlib import Path
                try:
                    shutil.rmtree(Path("saves"))
                except Exception:
                    pass
                pygame.quit()
                print("The world endures.")
                raise SystemExit(2)
            return   # ignore all other keys
        
        if self.debug and self.debug.handle_key(key, self):
            return

        if self.text_reader.open:
            self.text_reader.handle_key(key)
            return

        if self.inventory_screen.open:
            self.inventory_screen.handle_key(key, self)
            return

        if self.perk_screen.open:
            self.perk_screen.handle_key(key, self)
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
                self.log.add("Cancelled.", EARTH_BROWN)
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
                            WORN_STONE,
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

        if key == pygame.K_PAGEUP:
            page_size = 5
            msgs = self.log.recent(60)
            max_scroll = max(0, len(msgs) - page_size)
            self._log_scroll = min(self._log_scroll + page_size, max_scroll)
            return
        if key == pygame.K_PAGEDOWN:
            self._log_scroll = max(0, self._log_scroll - 5)
            return

        self.player._in_concealment = False
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
                self.log.add("The door yields.", OLD_GOLD)
                acted = True
            elif self.local_map.walkable[dest_x, dest_y]:
                blocker = self._get_blocking_entity(dest_x, dest_y)
                if blocker:
                    self._player_attack(blocker)
                    acted = True
                else:
                    self.player.move(dx, dy)
                    self._update_fov()
                    self._on_player_step(dest_x, dest_y)
                    acted = True

        elif key in WAIT_KEYS:
            acted = True

        elif key == pygame.K_ESCAPE:
            if self._confirm_quit():
                pygame.quit()
                raise SystemExit()

        elif key == pygame.K_F5 and not self.debug:
            self.save_manager.save(self)

        elif key == pygame.K_F9 and not self.debug:
            self.save_manager.load(self)

        elif key == pygame.K_i:
            self.inventory_screen.toggle()
            return

        elif key == pygame.K_k:
            self.perk_screen.toggle()
            return

        elif key in (pygame.K_g, pygame.K_COMMA):
            self._pick_up_item()
            acted = True

        if acted:
            self._log_scroll = 0
            self._advance_turn()
            while self._move_debt >= 1.0:
                self._move_debt -= 1.0
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
                    STONE_BLUE,
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
        self.log.add(f"Arrived at {label}.", LIFE_GREEN)

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
    #  Resonance zone messages
    # ------------------------------------------------------------------ #

    def _check_resonance_message(self) -> None:
        """Fire a zone entry message when resonance tier changes."""
        chunk = self.world_map.get(self.world_x, self.world_y)
        if not chunk:
            return

        resonance = getattr(chunk, "resonance", 0.1)

        if resonance < 0.15:
            tier = "very_low"
        elif resonance < 0.30:
            tier = "low"
        elif resonance < 0.50:
            tier = "moderate"
        elif resonance < 0.70:
            tier = "high"
        else:
            tier = "very_high"

        # Bell proximity overrides tier message
        bell_state = getattr(getattr(chunk, "town_data", None), "bell_state", None)
        if bell_state in ("intact", "cracked") and not self._bell_warned:
            self._bell_warned = True
            msgs = _RESONANCE_MESSAGES["intact_bell"]
            msg, color = msgs[self.world_time.turn % len(msgs)]
            self.log.add(msg, color)
            return

        if tier != self._resonance_tier:
            self._resonance_tier = tier
            self._bell_warned    = False
            msgs = _RESONANCE_MESSAGES.get(tier, [])
            if msgs:
                msg, color = random.choice(msgs)
                self.log.add(msg, color)

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

        # Clear ephemeral tiles (blood, etc.) from the departing chunk's local_map
        # before caching so they don't persist across visits.
        current_chunk = self.world_map.get(self.world_x, self.world_y)
        if current_chunk and current_chunk.ephemeral_tiles:
            for ex, ey, orig_terrain in current_chunk.ephemeral_tiles:
                if self.local_map.in_bounds(ex, ey):
                    t = self.data.terrain.get(orig_terrain, {})
                    self.local_map.set_tile(ex, ey, orig_terrain,
                                            t.get("walkable", True),
                                            t.get("transparent", True))
            current_chunk.ephemeral_tiles.clear()

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

        # ── Determine old/new town membership ────────────────────────
        old_chunk  = self.world_map.get(self.world_x - dx, self.world_y - dy)
        old_town   = getattr(old_chunk, "town_id", -1) if old_chunk else -1
        new_town   = getattr(chunk,     "town_id", -1)
        same_town  = (old_town >= 0 and old_town == new_town)

        if same_town:
            # Silent seam crossing inside the same town group
            pass
        else:
            # Leaving a town: allow re-announcement on re-entry
            if old_town >= 0:
                self._entered_town_ids.discard(old_town)

            # Entering a new town for the first time this visit
            if new_town >= 0 and new_town not in self._entered_town_ids:
                self._entered_town_ids.add(new_town)
                town_name = self.world_map.chunk_names.get(
                    (self.world_x, self.world_y), chunk.name
                )
                if town_name:
                    self.log.add_world(f"Thou enterest {town_name}.")
            elif new_town < 0:
                # Wilderness chunk — show normal movement message
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
                        chunk.region_type.value, chunk.region_type.value
                    )
                    self.log.add_world(f"You move into {region_name}.")

            if not same_town:
                self._check_resonance_message()

        # Fire ON_CHUNK_ENTERED hook
        from engine.hooks import HookEvent
        effects = self.hooks.fire(HookEvent.ON_CHUNK_ENTERED, {
            "wx":         self.world_x,
            "wy":         self.world_y,
            "biome_id":   chunk.biome_id,
            "resonance":  chunk.resonance,
            "difficulty": chunk.difficulty,
            "player":     self.player,
            "engine":     self,
        })
        _apply_effects(effects, self)

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
                STONE_BLUE,
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
                STONE_BLUE,
            )

    def _try_ascend(self) -> None:
        """Player attempts to ascend. Must be standing on stairs_up."""
        terrain = str(self.local_map.tiles["terrain"][self.player.x, self.player.y])
        if terrain == "stairs_up" and self.current_submap_id:
            self._ascend_from_submap()
        elif terrain == "stairs_up":
            self.log.add(
                "Thou art already at the surface.",
                STONE_BLUE,
            )
        else:
            self.log.add(
                "There is nothing to ascend here.",
                STONE_BLUE,
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
        self._check_resonance_message()
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
    #  Terrain step helpers
    # ------------------------------------------------------------------ #

    def _resolve_terrain_id(self, x: int, y: int) -> str:
        """Get the terrain id at (x,y), decoded if bytes."""
        t = self.local_map.tiles[x, y]["terrain"]
        if isinstance(t, bytes):
            t = t.decode()
        return str(t)

    def _on_player_step(self, x: int, y: int) -> None:
        """Called after player moves to (x, y). Applies move_cost debt and effects."""
        from engine.hooks import HookEvent
        terrain_id    = self._resolve_terrain_id(x, y)
        terrain_entry = self.data.terrain.get(terrain_id, {})
        move_cost     = terrain_entry.get("move_cost", 1.0)
        effect        = terrain_entry.get("secondary_effect", None)
        if effect:
            self._apply_terrain_effect(effect, terrain_id)

        # Fire tile-entered hook — allows perks to modify move debt
        effects = self.hooks.fire(HookEvent.ON_TILE_ENTERED, {
            "terrain_id": terrain_id,
            "x": x, "y": y,
            "wx": self.world_x, "wy": self.world_y,
            "move_cost": move_cost,
            "player": self.player,
            "engine": self,
        })
        _apply_effects(effects, self)
        if "move_debt_modifier" in effects:
            move_cost = 1.0 + (move_cost - 1.0) * effects["move_debt_modifier"]

        self._move_debt += max(0.0, move_cost - 1.0)

        if self.debug_move_log:
            self.log.add(
                f"[D] step ({x},{y}) terrain={terrain_id}"
                f" cost={move_cost:.2f} debt={self._move_debt:.2f}",
                OLD_GROWTH,
            )

    def _apply_terrain_effect(self, effect: str, terrain_id: str) -> None:
        """Apply a terrain secondary effect when the player steps onto a tile."""
        if effect == "concealment":
            self.player._in_concealment = True

        elif effect == "thorns":
            fighter = getattr(self.player, "fighter", None)
            if fighter and getattr(fighter, "location_hp", None):
                exposed = [
                    loc for loc, layers in fighter.armor_layers.items()
                    if sum(layer.get("armor_value", 0) for layer in layers) < 3
                ]
                target_loc = random.choice(exposed) if exposed else None
                if target_loc:
                    fighter.location_hp[target_loc] = max(
                        0, fighter.location_hp.get(target_loc, 1) - 1
                    )
                    self.log.add("The briars catch at you.", DUSTY_ROSE)
                    if self.display.CALLOUT_STATUS_EFFECTS:
                        self.callouts.add("thorns",
                                          self.player.x, self.player.y,
                                          DUSTY_ROSE, font_size="status")
                    self.player.took_damage_this_turn = True
                    if fighter.location_hp[target_loc] <= 0:
                        fighter._dead = True
                else:
                    self.log.add("The briars scrape harmlessly.", STONE_BLUE)

        elif effect in ("chill", "chill_heavy"):
            turns = 60 if effect == "chill_heavy" else 30
            current = getattr(self.player, "chilled_turns", 0)
            if current == 0:
                msg = ("The deep cold enters your bones." if effect == "chill_heavy"
                       else "The cold seeps in.")
                self.log.add(msg, SLATE_MID)
                if self.display.CALLOUT_STATUS_EFFECTS:
                    self.callouts.add("chilled",
                                      self.player.x, self.player.y,
                                      SLATE_MID, font_size="status")
            self.player.chilled_turns = turns  # always refresh

        elif effect == "resonance_trace":
            pass  # stub — resonance system Tier 3

        elif effect == "poison_tile":
            pass  # stub — poison system Tier 3

    # ------------------------------------------------------------------ #
    #  _update_context_prompt
    # ------------------------------------------------------------------ #

    def _update_context_prompt(self) -> None:
        """Refresh the status-bar context prompt based on tile under player."""
        if not hasattr(self, "ui"):
            return
        terrain = str(self.local_map.tiles["terrain"][self.player.x, self.player.y])
        if terrain == "stairs_down":
            self.ui.set_context_prompt("[ > ] Descend", OLD_GOLD)
        elif terrain == "stairs_up":
            self.ui.set_context_prompt("[ < ] Ascend", SLATE_MID)
        elif terrain == "door_closed":
            self.ui.set_context_prompt("Walk into door to open", WORN_STONE)
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

        # Forgetting fog — mechanical FOV shrink (only fog weather effect)
        _weather = getattr(self, "weather", None)
        if _weather and _weather.state == "forgetting_fog":
            _fog_reduction = int(_weather.intensity * 3)
            active_radius = max(3, active_radius - _fog_reduction)

        # Store for fog vignette clear-radius calculation
        self._effective_fov_radius = active_radius

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

        # Terrain light sources (street lamps)
        lamp_tiles = {"street_lamp_working", "street_lamp_sputtering"}
        for mx in range(self.local_map.width):
            for my in range(self.local_map.height):
                if not bool(fov[mx, my]):
                    continue
                terrain = str(self.local_map.tiles[mx, my]["terrain"])
                if terrain not in lamp_tiles:
                    continue
                td = self.registry._data.get(terrain, {})
                light_radius    = td.get("light_radius",    0)
                light_intensity = td.get("light_intensity", 1.0)
                light_color_raw = td.get("light_color",     [255, 255, 255])
                if light_radius <= 0:
                    continue
                # Sputtering: time-based flicker suppression
                if terrain == "street_lamp_sputtering":
                    flicker_seed = ((mx * 7 + my * 13) % 60) or 1
                    frame_off    = (mx * 3 + my * 5) % flicker_seed
                    tick = (pygame.time.get_ticks() // 200 + frame_off) % flicker_seed
                    if tick == 0:
                        continue
                lc_r = light_color_raw[0] / 255.0
                lc_g = light_color_raw[1] / 255.0
                lc_b = light_color_raw[2] / 255.0
                for dx2 in range(-light_radius, light_radius + 1):
                    for dy2 in range(-light_radius, light_radius + 1):
                        nx, ny = mx + dx2, my + dy2
                        if not self.local_map.in_bounds(nx, ny):
                            continue
                        if not bool(fov[nx, ny]):
                            continue
                        dist = (dx2 * dx2 + dy2 * dy2) ** 0.5
                        if dist > light_radius:
                            continue
                        strength = light_intensity * max(0.0, 1.0 - dist / light_radius)
                        lm[nx, ny, 0] = min(1.0, lm[nx, ny, 0] + lc_r * strength)
                        lm[nx, ny, 1] = min(1.0, lm[nx, ny, 1] + lc_g * strength)
                        lm[nx, ny, 2] = min(1.0, lm[nx, ny, 2] + lc_b * strength)

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
            self.log.add("Thou canst not strike.", AGED_WOOD)
            return

        # Check line of sight (wall blocking)
        if not self._has_line_of_sight_adjacent(
            self.local_map, self.player.x, self.player.y, target.x, target.y
        ):
            self.log.add("Something stands between thee and thy mark.", AGED_WOOD)
            return

        weapon = self._get_equipped_weapon() or _UNARMED_PROFILE

        # Get body def for target
        body_id  = target_fighter.body_id
        body_def = self.data.bodies.get(body_id, {})

        # Fallback: if no body def, use legacy combat
        if not body_def:
            actual = target_fighter.take_damage(player_fighter.power)
            if actual == 0:
                self.log.add(
                    f"You strike the {target.name} but do no damage.",
                    AGED_WOOD,
                )
            else:
                self.log.add(
                    f"You strike the {target.name} for {actual} damage.",
                    DUSTY_ROSE,
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
        from config import DEBUG_MODE as _DEBUG_MODE
        _dbg_appended = False
        for msg, mtype in zip(result.messages, result.message_types):
            if mtype == "deflect":
                color = STONE_BLUE       # slate_mid — dim, neither triumph nor threat
            elif mtype == "impair":
                color = BLOOD_STONE        # blood_rose — creature impaired
            else:                            # hit / death
                color = SLATE_MID      # mist_blue
            if _DEBUG_MODE and not _dbg_appended and result.debug_formula:
                msg = msg + "  " + result.debug_formula
                _dbg_appended = True
            self.log.add(f"› {msg}", color)
        if result.damage_number > 0:
            self.log.add(f"  {result.damage_number} damage.", FROST_WHITE)  # bright mist_blue
            if self.display.CALLOUT_DAMAGE_NUMBERS:
                _num_y = target.y - 0.3 if result.is_crit else float(target.y)
                self.callouts.add(str(result.damage_number),
                                  target.x, _num_y, SLATE_MID,
                                  font_size="damage")
        elif result.damage_dealt == 0 and any(
                mt == "deflect" for mt in result.message_types):
            if self.display.CALLOUT_DAMAGE_NUMBERS:
                self.callouts.add("—", target.x, float(target.y),
                                  STONE_BLUE, font_size="creature")

        # Critical hit — "CRITICAL" callout, screenshake, extra particles, hook
        if result.is_crit and result.damage_dealt > 0:
            if self.display.CALLOUT_DAMAGE_NUMBERS:
                self.callouts.add("CRITICAL", target.x, target.y - 0.8,
                                  OLD_GOLD, lifetime=1.4,
                                  font_size="crit")
            self.trigger_screenshake(4)
            # Mark pending blood as crit so render loop emits enhanced burst
            if self._pending_blood:
                self._pending_blood[-1]["is_crit"] = True
            # ON_CRITICAL_HIT hook
            from engine.hooks import HookEvent as _HookEvent
            _wcrit = self._get_equipped_weapon()
            effects = self.hooks.fire(_HookEvent.ON_CRITICAL_HIT, {
                "damage":     result.damage_dealt,
                "raw_damage": result.damage_raw_post_essence,
                "target":     target,
                "weapon_id":  _wcrit.get("id", "") if _wcrit else "",
                "player":     self.player,
                "engine":     self,
            })
            _apply_effects(effects, self)

        if result.damage_dealt > 0:
            blood_type = self.data.entities.get(target.tile, {}).get("blood_type", "red")
            self._place_blood_tile(target.x, target.y, blood_type)
            from rendering.particles import BLOOD_COLORS
            _bcolor = BLOOD_COLORS.get(blood_type)
            if _bcolor is not None:
                self._pending_blood.append({
                    "defender_tile": (target.x, target.y),
                    "attacker_tile": (self.player.x, self.player.y),
                    "color": _bcolor,
                })

        # Fire ON_DAMAGE_DEALT hook
        if result.damage_dealt > 0:
            from engine.hooks import HookEvent
            weapon_item = self._get_equipped_weapon()
            effects = self.hooks.fire(HookEvent.ON_DAMAGE_DEALT, {
                "damage":       result.damage_dealt,
                "essence":      result.essence_applied,
                "hit_location": result.location_id,
                "target":       target,
                "weapon_id":    weapon_item.get("id", "") if weapon_item else "",
                "player":       self.player,
                "engine":       self,
            })
            _apply_effects(effects, self)

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
                    FOREST_DEEP,
                )
                self.log.add(f"  {thorn} damage.", LIFE_GREEN)
                self.player.took_damage_this_turn = True
                if player_fighter.location_hp.get("torso", 1) <= 0:
                    self._death_killer = target.name
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

    # blood_type → terrain id
    _BLOOD_TERRAIN: dict[str, str] = {
        "red":      "blood_pool",
        "bone_dust":"bone_dust",
        "ectoplasm":"ectoplasm_pool",
        "ichor":    "ichor_seep",
        "verdigris":"verdigris_fluid",
    }

    def _place_blood_tile(self, x: int, y: int, blood_type: str) -> None:
        """Write a blood/fluid tile onto the local map at (x, y).
        Skips non-walkable tiles and tiles already marked blood.
        Tracks placement in the current chunk's ephemeral_tiles for later cleanup."""
        terrain_id = self._BLOOD_TERRAIN.get(blood_type)
        if not terrain_id:
            return  # blood_type "none" → no tile
        if not self.local_map.in_bounds(x, y):
            return
        if not self.local_map.walkable[x, y]:
            return
        orig_terrain = str(self.local_map.tiles[x, y]["terrain"])
        # Don't overwrite stairs or other blood tiles
        if orig_terrain in ("stairs_down", "stairs_up") or orig_terrain in self._BLOOD_TERRAIN.values():
            return
        t = self.data.terrain.get(terrain_id, {})
        self.local_map.set_tile(x, y, terrain_id,
                                t.get("walkable", True), t.get("transparent", True))
        chunk = self.world_map.get(self.world_x, self.world_y)
        if chunk is not None:
            chunk.ephemeral_tiles.append((x, y, orig_terrain))

    def _on_entity_death(self, entity: "Actor") -> None:
        from engine.message_log import MSG_DANGER
        from engine.hooks import HookEvent
        from entities.item import Item

        self.log.add(f"The {entity.name} is destroyed.", MSG_DANGER)
        entity.is_alive = False

        # on_death creature sound callout
        if self.display.CALLOUT_CREATURE_SOUNDS:
            _cdef = self.data.entities.get(entity.tile, {})
            _csnd = _cdef.get("callout_sounds", {}).get("on_death")
            if _csnd:
                self.callouts.add(
                    _csnd["text"],
                    entity.x, entity.y,
                    tuple(_csnd.get("color", [200, 180, 150])),
                    lifetime=2.0,
                    font_size="creature",
                )

        # Fire ON_ENTITY_KILLED — perks that trigger on kills
        creature_def = self.data.entities.get(entity.tile, {})
        effects = self.hooks.fire(HookEvent.ON_ENTITY_KILLED, {
            "entity":     entity,
            "entity_id":  getattr(entity, "tile", ""),
            "blood_type": creature_def.get("blood_type", "red"),
            "x": entity.x, "y": entity.y,
            "player": self.player,
            "engine": self,
        })
        _apply_effects(effects, self)

        corpse = Item(
            x    = entity.x,
            y    = entity.y,
            tile = "corpse",
            name = f"remains of {entity.name}",
        )
        creature_def = self.data.entities.get(entity.tile, {})
        cs = creature_def.get("corpse_sprite")
        if cs:
            corpse.sprite_col = cs.get("col", 2055)
            corpse.sprite_row = cs.get("row", 0)
        self.entities.append(corpse)

        # Bog wraith death — lift FOV drain, brief overcorrection
        if entity.tile == "bog_wraith":
            self.player._wraith_fov_penalty  = 0
            self.player._wraith_overcorrect  = 3
            self.log.add(
                "The forgetting lifts. "
                "The world rushes back — too much of it, briefly.",
                COLDBELL_LIGHT,
            )
            self._update_fov()

    def _on_player_death(self) -> None:
        self.trigger_screenshake(6.0)

        # Capture the last 5 messages before adding death messages
        recent = self.log.recent(5)
        self._death_messages = [m.with_count() for m in recent]

        # Delete save so next run starts fresh
        import shutil
        from pathlib import Path
        save_path = Path("saves")
        if save_path.exists():
            shutil.rmtree(save_path)

        self._player_is_dead = True

    def _render_death_screen(self, screen: pygame.Surface) -> None:
        sw = screen.get_width()
        sh = screen.get_height()

        screen.fill(VOID_BLACK)

        font_title  = self.display.font_ui_large if self.display else \
                      pygame.font.SysFont("monospace", 28)
        font_body   = self.display.font_ui_small if self.display else \
                      pygame.font.SysFont("monospace", 14)
        font_tiny   = self.display.font_ui_tiny  if self.display else \
                      pygame.font.SysFont("monospace", 12)

        cy = sh // 4

        # --- "YOU ARE UNDONE." ---
        title = font_title.render("YOU ARE UNDONE.", True, BLOOD_STONE)
        screen.blit(title, (sw // 2 - title.get_width() // 2, cy))
        cy += title.get_height() + 24

        # --- Killer line ---
        killer_str = f"Slain by: {self._death_killer}"
        k_surf = font_body.render(killer_str, True, DUSTY_ROSE)
        screen.blit(k_surf, (sw // 2 - k_surf.get_width() // 2, cy))
        cy += k_surf.get_height() + 28

        # --- Divider ---
        pygame.draw.line(screen, ASH_DARK,
                         (sw // 4, cy), (sw * 3 // 4, cy), 1)
        cy += 14

        # --- Last 5 messages ---
        label = font_tiny.render("Last witnessed:", True, STONE_BLUE)
        screen.blit(label, (sw // 2 - label.get_width() // 2, cy))
        cy += label.get_height() + 6

        for line in self._death_messages:
            s = font_tiny.render(f"  \u203a {line}", True, EARTH_BROWN)
            screen.blit(s, (sw // 2 - s.get_width() // 2, cy))
            cy += s.get_height() + 2
        cy += 20

        # --- Divider ---
        pygame.draw.line(screen, ASH_DARK,
                         (sw // 4, cy), (sw * 3 // 4, cy), 1)
        cy += 18

        # --- R / N options ---
        r_surf = font_body.render("R \u2014 remain undone", True, STONE_BLUE)
        n_surf = font_body.render("N \u2014 begin again", True, SLATE_MID)
        gap = 40
        total_w = r_surf.get_width() + gap + n_surf.get_width()
        rx = sw // 2 - total_w // 2
        screen.blit(r_surf, (rx, cy))
        screen.blit(n_surf, (rx + r_surf.get_width() + gap, cy))

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
                    WORN_STONE,
                )
                return
            self._pickup_mode = True
            self.log.add(
                "Pick up from where? (movement key, ESC to cancel)",
                WORN_STONE,
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
                OLD_GOLD,
            )
            return
        if inv.add(item):
            self.entities.remove(item)
            self.log.add(f"You take the {item.name}.", WORN_STONE)

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

