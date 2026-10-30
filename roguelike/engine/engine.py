# engine/engine.py
from __future__ import annotations
from engine.effect_lifecycle import creature_id
import enum
import json
import pygame
import tcod.map
import numpy as np
import random

from pathlib import Path
from config import MAP_WIDTH, MAP_HEIGHT, MSG_PANEL_W, STATUS_BAR_H, OVERMAP_SIDEBAR_W, UI_PANEL_INSET
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
from engine.interaction_cursor import InteractionCursor
from engine.save_manager import SaveManager
from engine.item_factory import ItemFactory
from engine.item_system import ItemSystem
from engine.inventory_screen import InventoryScreen
from engine.health_screen import HealthScreen
from engine.text_reader import TextReader
from rendering.perk_screen import PerkScreen
from rendering.craft_screen import CraftScreen
from rendering.lexicon_screen import LexiconScreen

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

    # Scale max HP by 1.08 and restore the gain
    fighter = getattr(player, "fighter", None)
    if fighter:
        old_max      = fighter.max_hp
        new_max      = max(1, int(old_max * 1.08))
        gain         = new_max - old_max
        fighter.max_hp = new_max
        fighter.hp     = fighter.hp + gain

    engine.log.add("Something shifts in you.", OLD_GOLD)   # old_gold
    engine.log.add("A perk point awaits. Press K to spend it.", STONE_BLUE)   # slate_mid

    # Prolonged level-up callout — slow upward drift, 2.0–2.5s
    import random as _lrng
    _levelup_texts = ["ASCENSION", "SOMETHING SHIFTS", "A THRESHOLD CROSSED"]
    _ltext = _lrng.choice(_levelup_texts)
    engine.callouts.add(
        _ltext,
        float(player.x), float(player.y) - 1.0,
        OLD_GOLD,
        lifetime=_lrng.uniform(2.0, 2.5),
        font_size="levelup",
        vy=-12.0,    # slow upward drift
    )


def _heal_least_damaged(player: "Actor", amount: int) -> None:
    """Heal `amount` HP from the single pool."""
    fighter = getattr(player, "fighter", None)
    if not fighter:
        return
    fighter.heal(amount)


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
    LOCAL               = "local"
    OVERMAP             = "overmap"
    LOOK                = "look"
    INTERACTION_CURSOR  = "interaction_cursor"
    PLACEMENT_CURSOR    = "placement_cursor"


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
        *,
        save_manager: SaveManager | None = None,
        debug_mode: bool | None = None,
        session_label: str = "Roguelike",
        bounded_room_test: bool = False,
    ) -> None:
        self.player    = player
        self.local_map = local_map
        self.entities  = entities
        self.registry  = registry
        self.world_map = world_map
        self.world_x   = world_x
        self.world_y   = world_y
        self.data      = data
        if player.inventory is not None:
            player.inventory.bind_carrying(player.equipment, data.items)
        self.display   = display
        self.mode      = GameMode.LOCAL
        self.overmap_cam_x    = world_x
        self.overmap_cam_y    = world_y
        self.overmap_cursor_x = world_x
        self.overmap_cursor_y = world_y
        self.debug            = DebugOverlay() if (DEBUG_MODE if debug_mode is None else debug_mode) else None
        self.session_label = session_label
        self.bounded_room_test = bounded_room_test
        self.ai_system        = AISystem()
        self.creature_factory = CreatureFactory(data)
        self._held_key:        int | None = None
        self._held_key_timer:  int        = 0
        self.log              = MessageLog()
        self.world_time       = WorldTime()
        self.look_mode          = LookMode()
        self.interaction_cursor = InteractionCursor()
        self.save_manager     = SaveManager(slot=0) if save_manager is None else save_manager
        self.item_factory     = ItemFactory(data)
        self.item_system      = ItemSystem()
        self.inventory_screen = InventoryScreen()
        self.health_screen    = HealthScreen()
        self.perk_screen      = PerkScreen()
        self.craft_screen     = CraftScreen()
        self.lexicon_screen   = LexiconScreen()
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
        self._weapon_time_balance:  int = 0  # signed millionths of a phase
        self._free_move_pending:    bool = False
        self._player_in_concealment: bool  = False
        # Warmth system
        self.player_near_fire:       bool  = False
        self._warm_tile_ids:         set   = set()
        # Placement cursor
        self._pending_placement_tile:   str | None  = None
        self._pending_placement_recipe: dict | None = None
        self._pending_craft_items: list | None = None
        self._placement_cursor_x:       int         = 0
        self._placement_cursor_y:       int         = 0
        self._placement_mode:           str         = "campfire"   # "campfire"|"drying"|"cooking"
        self._pending_processing:       dict | None = None

        # Resonance / corruption state
        self.resonance_exposure:     float = 0.0
        self.corruption:             float = 0.0
        self.wind_turn:              int   = 0
        self._last_exposure_tier:    int   = 0
        self._corruption_thresholds: set   = set()
        self._resonance_sight_active: bool  = False
        self._discharge_flash:       tuple | None = None
        self._discharge_flash_turns: int   = 0
        self._log_scroll:            int   = 0

        # Seeded RNG for in-game systems (discharge, weather, wind)
        self.rng = random.Random(getattr(world_map, "seed", None))

        # Weather
        from engine.weather import WeatherSystem
        self.weather = WeatherSystem(self.rng)
        self.weather.load_mechanics(data.weather_defs)

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
        # Wraith aura state: entity id → consecutive turns in radius
        self._wraith_aura_state:     dict                    = {}
        # Overcorrect turns remaining after wraith death (adds +3 to FOV for 3 turns)
        self._wraith_overcorrect_turns: int                  = 0
        # Deferred blood emissions — resolved to screen coords in the render loop
        self._pending_blood: list = []
        # Entities pursuing the player across chunk boundaries — populated in
        # _transition_chunk before cache.store, merged into new chunk after load
        self._pending_transfer: list = []
        # Live pursuers: entities extracted from their chunk/submap, ticked every turn.
        # tuple: (Actor, wx, wy, submap_id_or_None)
        # submap_id_or_None=None  → entity is in surface chunk (wx,wy)
        # submap_id_or_None=str   → entity is in a submap; (wx,wy) is the surface chunk
        self._live_pursuers: list = []
        # Deferred pursuer arrivals — entities waiting to materialise in player's chunk.
        # Each entry: {entity, entry_x, entry_y, delay: int}
        self._pending_pursuer_arrivals: list[dict] = []
        # Last chunk entry position — used to place arriving pursuers at the
        # same edge the player entered from.
        self._last_chunk_entry: tuple[int, int] = (0, 0)
        # Sprint state
        self.sprint_turns_remaining:    int   = 0
        self.sprint_cooldown_remaining: int   = 0
        self.player_move_accumulator:   float = 0.0
        # Speed bonus (stalker unguent)
        self.player_speed_bonus:       float = 0.0
        self.player_speed_bonus_turns: int   = 0
        # True sight (wight concentrate)
        self.true_sight_turns:         int   = 0
        # Pending consume confirmation (wight concentrate warning prompt)
        self._pending_consume:         dict | None = None
        # Pending throw (musk pellet target selection)
        self._pending_throw:           dict | None = None
        # Rain collection accumulator (refilling empty_water_skin)
        self.rain_collection_progress: int = 0
        # Moveset cooldowns — action_id → turns remaining
        self.moveset_cooldowns: dict[str, int] = {}
        # Creature knowledge — creature_id → {revealed_weaknesses, revealed_strengths}
        self.creature_knowledge: dict[str, dict] = {}
        # Callout system — floating text above entities (damage, sounds, status)
        from rendering.callouts import CalloutSystem
        self.callouts = CalloutSystem()
        # Deferred creature sound callouts — resolved from AI turns
        self._pending_callouts: list = []
        # Projectile tween animations (generic, data-driven per creature JSON)
        self._projectile_tweens: list = []

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
        self._configure_player_needs()
        self._build_warm_tile_ids()

    def _configure_player_needs(self) -> None:
        """Configure player needs from survival.json. Called at startup and after load."""
        needs = getattr(self.player, "needs", None)
        if needs and self.data.survival:
            needs.configure(self.data.survival)

    def _restore_loaded_state(self) -> None:
        """Rebind derived owners once, after the full saved graph is installed.

        This does not fire gameplay events, advance time, heal, consume fuel or
        replay perk acquisition. Unfinished UI commands belong to the old graph.
        """
        self._configure_player_needs()
        self._register_player_perks()
        self._update_warmth()
        from engine.effect_lifecycle import knight_disruption, refresh_wraith_aura
        knight_disruption(self)
        refresh_wraith_aura(self)
        self.player.took_damage_this_turn = False
        self._player_is_dead = not self.player.is_alive
        self._held_key = None
        self._quit_pending = False
        self._pickup_mode = False
        self.mode = GameMode.LOCAL
        for screen in (self.inventory_screen, self.health_screen, self.perk_screen,
                       self.craft_screen, self.lexicon_screen, self.text_reader):
            screen.open = False
        self.inventory_screen._flat = []
        self.inventory_screen.selected = 0
        self._pending_consume = self._pending_throw = None
        self._pending_processing = self._pending_placement_recipe = None
        self._pending_craft_items = None
        self._pending_placement_tile = None
        self._pending_blood = []
        self._pending_callouts = []
        self._projectile_tweens = []
        self.callouts.clear()
        self.particle_system.clear()
        self.visual_events.clear()
        self._fog_surface = None
        self._particle_map_id = 0
        self._discharge_flash = None
        self._discharge_flash_turns = 0
        self._update_context_prompt()

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
                _is_ws = str(t) == "waystone_plinth"
                if not _is_ws:
                    _is_ws = self.local_map.decor.get((x, y)) == "waystone_plinth"
                if _is_ws:
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
        from engine.perk_handlers import HANDLER_MAP, cleanup_perk_state, restore_perk_bonuses

        # Clean up stateful perk side-effects before clearing handlers
        cleanup_perk_state(self)

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
        restore_perk_bonuses(self)

    @property
    def world_myth(self):
        return self.world_map.myth

    # ------------------------------------------------------------------ #
    #  Main loop
    # ------------------------------------------------------------------ #

    def run(self, *, on_frame=None) -> None:
        pygame.init()

        screen = pygame.display.set_mode(
            (1280, 720),
            pygame.RESIZABLE,
        )
        pygame.display.set_caption(self.session_label)

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
        self.interaction_cursor.init(self.display)
        self.inventory_screen.init(self.display)
        self.health_screen.init(self.display)
        self.perk_screen.init(self.display)
        self.craft_screen.init(self.display)
        self.lexicon_screen.init(self.display)
        self.text_reader.init(self.display)

        if self.debug:
            self.debug.init()

        clock    = pygame.time.Clock()

        renderer = Renderer(
            self.registry,
            self.display,
            sprite_registry=self.sprite_registry,
        )
        renderer._terrain_data = self.data.terrain
        renderer._decor_defs   = self.data.decoratives

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

                    # Every key follows the same death/modal guards. Unicode is
                    # retained for Shift+. / Shift+, without bypassing those guards.
                    self._handle_key(event.key, getattr(event, "unicode", ""))

                    if getattr(event, "unicode", "") in ("<", ">"):
                        # A held Shift+. must never repeat as unshifted wait.
                        self._held_key = None
                    elif event.key in MOVE_KEYS or event.key in WAIT_KEYS:
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
                if on_frame is not None:
                    on_frame(self, screen)
                clock.tick(60)
                continue

            _panels = (
                hasattr(self, "ui_registry") and self.ui_registry._loaded
            )

            # --- Game world ---
            if self.mode in (GameMode.LOCAL, GameMode.LOOK,
                             GameMode.INTERACTION_CURSOR, GameMode.PLACEMENT_CURSOR):
                # Fill full game panel area with void color first — covers the
                # border inset zone on all sides before panel/tiles are drawn.
                screen.fill(VOID_BLACK, game_panel_rect)
                cam_x, cam_y = self._get_camera(viewport)
                shake_offset = self._update_screenshake()
                self.visual_events.tick()
                # Entities with active tweens are drawn at their tween position;
                # suppress their normal tile render to avoid doubling.
                _suppressed_ids = {
                    t["entity_id"] for t in self._projectile_tweens
                    if t["elapsed"] < t["duration"]
                }
                # Set river connections for autotile OOB checks
                _rc_chunk = self.world_map.get(self.world_x, self.world_y) if hasattr(self, "world_map") else None
                renderer._river_connections = getattr(_rc_chunk, "river_connections", []) if _rc_chunk else []
                renderer.render(
                    screen, self.local_map, self.entities,
                    cam_x, cam_y, viewport,
                    shake_offset=shake_offset,
                    visual_events=self.visual_events.get_active(),
                    void_rect=game_panel_rect,
                    player_x=self.player.x,
                    player_y=self.player.y,
                    suppressed_entity_ids=_suppressed_ids,
                )
                if self.mode == GameMode.LOOK:
                    self.look_mode.render_cursor(screen, self, cam_x, cam_y)
                    self.look_mode.render_hint_overlay(screen, viewport, self.display)
                    if self.look_mode.examining:
                        self.look_mode.render_examine_popup(screen, self)
                elif self.mode == GameMode.INTERACTION_CURSOR:
                    self.interaction_cursor.render(screen, self, cam_x, cam_y, viewport)
                elif self.mode == GameMode.PLACEMENT_CURSOR:
                    self._render_placement_cursor(screen, cam_x, cam_y, viewport)

                # --- Particle system (steps 4-9) ---
                # Skip when any screen overlay is open
                _overlay_open = (
                    self.inventory_screen.open or
                    self.health_screen.open or
                    self.perk_screen.open or
                    self.craft_screen.open or
                    self.lexicon_screen.open or
                    self.text_reader.open or
                    self.look_mode.examining
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

                    # Waystone pulse check + resonance ripple
                    import random as _rand
                    from rendering.particles import make_waystone_ring as _mwr
                    from rendering.particles import make_resonance_ripple as _mrr2
                    for (_wtx, _wty), _next_t in list(
                            self._waystone_pulse_timers.items()):
                        if _now >= _next_t:
                            if self.local_map.in_bounds(_wtx, _wty):
                                _terrain = self._resolve_terrain_id(_wtx, _wty)
                                _is_ws2 = (_terrain == "waystone_plinth" or
                                           self.local_map.decor.get((_wtx, _wty)) == "waystone_plinth")
                                if _is_ws2:
                                    self.particle_system.emit(
                                        _mwr(_wtx, _wty, _rand.Random()))
                                    # Resonance ripple — expanding dot ring
                                    self.particle_system.emit_burst(
                                        _mrr2(_wtx, _wty))
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
                                # Check decor layer for sparkle-eligible tiles
                                _sdid = self.local_map.decor.get((_mx, _my))
                                if _sdid in _SPARKLE_COLORS:
                                    _t = _sdid
                                else:
                                    continue
                            _seed = (_frame_tick + _mx * 7919 + _my * 104729) & 0xFFFF
                            if _seed % _SPARKLE_PROB != 0:
                                continue
                            self.particle_system.emit(
                                _ms(_mx, _my, _SPARKLE_COLORS[_t],
                                    _spk_rng.Random(_seed)))

                    # Flame / ember emitter pass — visible tiles with fire visual_fx.
                    # Checks both terrain and decor layers. Each flame tier fires
                    # at a different frame cadence:
                    #   flame_low / smoke_incense : every 4-5 frames (slow flicker)
                    #   flame_med / embers        : every 3 frames (campfire)
                    #   flame_high                : every 2 frames (roaring fire)
                    _flame_fx_any = (
                        _frame_tick % 2 == 0 or
                        _frame_tick % 3 == 0 or
                        _frame_tick % 4 == 0 or
                        _frame_tick % 5 == 0
                    )
                    if _flame_fx_any:
                        from rendering.particles import (
                            make_ember_particles       as _mep,
                            make_flame_low_particles   as _mfl,
                            make_flame_med_particles   as _mfm,
                            make_flame_high_particles  as _mfh,
                            make_smoke_incense_particles as _msi,
                        )
                        _emb_mo_x = viewport.x + shake_offset[0]
                        _emb_mo_y = viewport.y + shake_offset[1]
                        _FLAME_FUNCS = {
                            "embers":        (_mep, 3),
                            "flame_low":     (_mfl, 4),
                            "flame_med":     (_mfm, 3),
                            "flame_high":    (_mfh, 2),
                            "smoke_incense": (_msi, 5),
                        }
                        for _ey in range(cam_y, cam_y + _tiles_y):
                            for _ex in range(cam_x, cam_x + _tiles_x):
                                if not self.local_map.in_bounds(_ex, _ey):
                                    continue
                                if not self.local_map.visible[_ex, _ey]:
                                    continue
                                _et = self._resolve_terrain_id(_ex, _ey)
                                _etd = self.data.terrain.get(_et, {})
                                _edid = self.local_map.decor.get((_ex, _ey))
                                _edd  = self.data.decoratives.get(_edid, {}) if _edid else {}
                                _efx = _etd.get("visual_fx") or _edd.get("visual_fx")
                                if _efx not in _FLAME_FUNCS:
                                    continue
                                _efunc, _ecadence = _FLAME_FUNCS[_efx]
                                if _frame_tick % _ecadence != 0:
                                    continue
                                _eseed = (_frame_tick + _ex * 6113 + _ey * 9311) & 0xFFFF
                                _esx = int(_emb_mo_x + (_ex - cam_x) * _tile_w + _tile_w // 2)
                                _esy = int(_emb_mo_y + (_ey - cam_y) * _tile_h + _tile_h // 2)
                                self.particle_system.emit_burst(
                                    _efunc(_esx, _esy, _spk_rng.Random(_eseed)))

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

                    # Step 5c: atmospheric particle emitters
                    # (Resonance ripple is wired into the waystone pulse block above.)

                    # Ground mist — swamp / drowned_wood biomes
                    _biome_chunk = self.world_map.get(self.world_x, self.world_y)
                    _biome_id_atm = getattr(_biome_chunk, "biome_id", "") if _biome_chunk else ""
                    if _biome_id_atm in ("swamp", "drowned_wood") and self.current_submap_id is None:
                        if _frame_tick % 20 == 0:
                            from rendering.particles import make_ground_mist as _mgm
                            _mist_count = _spk_rng.randint(2, 3)
                            for _ in range(_mist_count):
                                _mx2 = cam_x + _spk_rng.randint(0, _tiles_x - 1)
                                _my2 = cam_y + _spk_rng.randint(0, _tiles_y - 1)
                                if (self.local_map.in_bounds(_mx2, _my2)
                                        and self.local_map.visible[_mx2, _my2]
                                        and self.local_map.walkable[_mx2, _my2]):
                                    self.particle_system.emit(
                                        _mgm(_mx2, _my2, _spk_rng.Random(_frame_tick + _mx2)))

                    # Dust motes — building interiors (non-town walkable tiles
                    # with wall neighbours, as a heuristic for enclosed spaces)
                    if _frame_tick % 30 == 0 and self.current_submap_id is not None:
                        from rendering.particles import make_dust_mote as _mdu
                        _dx2 = cam_x + _spk_rng.randint(0, _tiles_x - 1)
                        _dy2 = cam_y + _spk_rng.randint(0, _tiles_y - 1)
                        if (self.local_map.in_bounds(_dx2, _dy2)
                                and self.local_map.visible[_dx2, _dy2]
                                and self.local_map.walkable[_dx2, _dy2]):
                            self.particle_system.emit(
                                _mdu(_dx2, _dy2, _spk_rng.Random(_frame_tick + _dx2)))

                    # Corruption wisps — orbit player when exposure > 0.5
                    if self.resonance_exposure > 0.5 and _frame_tick % 4 == 0:
                        from rendering.particles import make_corruption_wisp as _mcw
                        self.particle_system.emit(
                            _mcw(self.player.x, self.player.y,
                                 self.resonance_exposure,
                                 _spk_rng.Random(_frame_tick)))

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

                    # Step 7b: projectile tween animations (generic, data-driven)
                    if self._projectile_tweens:
                        screen.set_clip(viewport)
                        _living = []
                        _sreg     = self.sprite_registry
                        _use_tint = getattr(self.display, "use_sprite_tint", False)
                        for _tween in self._projectile_tweens:
                            _tween["elapsed"] += _dt
                            _frac = _tween["elapsed"] / _tween["duration"]
                            if _frac >= 1.0:
                                continue   # expired
                            _living.append(_tween)

                            # 3-phase position
                            if _frac < 0.60:
                                _pt = _frac / 0.60
                                _wx = _tween["sx"] + (_tween["apex_x"] - _tween["sx"]) * _pt
                                _wy = _tween["sy"] + (_tween["apex_y"] - _tween["sy"]) * _pt
                            elif _frac < 0.70:
                                _wx = _tween["apex_x"]
                                _wy = _tween["apex_y"]
                                # Fire impact FX once when entering phase 2
                                if not _tween["_impact_fired"]:
                                    _tween["_impact_fired"] = True
                                    if _tween["on_hit"]:
                                        from rendering.particles import (
                                            make_blood_particles, BLOOD_COLORS)
                                        _bc = BLOOD_COLORS.get(
                                            _tween.get("blood_type", "red"))
                                        if _bc:
                                            # Convert tile coords → absolute screen
                                            # coords before passing to make_blood_particles.
                                            # apex = impact point; sx/sy = attacker origin.
                                            _b_sx = int(viewport.x + shake_offset[0]
                                                        + (_tween["apex_x"] - cam_x + 0.5) * _tile_w)
                                            _b_sy = int(viewport.y + shake_offset[1]
                                                        + (_tween["apex_y"] - cam_y + 0.5) * _tile_h)
                                            _a_sx = int(viewport.x + shake_offset[0]
                                                        + (_tween["sx"] - cam_x + 0.5) * _tile_w)
                                            _a_sy = int(viewport.y + shake_offset[1]
                                                        + (_tween["sy"] - cam_y + 0.5) * _tile_h)
                                            self.particle_system.emit_burst(
                                                make_blood_particles(
                                                    _b_sx, _b_sy,
                                                    _bc,
                                                    _a_sx, _a_sy,
                                                    count=5))
                                    else:
                                        if getattr(self.display,
                                                   "CALLOUT_DAMAGE_NUMBERS", True):
                                            self.callouts.add(
                                                "—",
                                                _tween["apex_x"], _tween["apex_y"],
                                                COMBAT_INCOMING,
                                                lifetime=0.3, font_size="tiny")
                            else:
                                _pt = (_frac - 0.70) / 0.30
                                _wx = _tween["apex_x"] + (_tween["sx"] - _tween["apex_x"]) * _pt
                                _wy = _tween["apex_y"] + (_tween["sy"] - _tween["apex_y"]) * _pt

                            # Screen position (centred on tile)
                            _psx = int(viewport.x + shake_offset[0]
                                       + (_wx - cam_x + 0.5) * _tile_w)
                            _psy = int(viewport.y + shake_offset[1]
                                       + (_wy - cam_y + 0.5) * _tile_h)

                            if viewport.collidepoint(_psx, _psy) and _sreg and getattr(_sreg, "_loaded", False):
                                if _use_tint:
                                    _psurf = _sreg.get_tinted(
                                        _tween["tile_id"], TRUE_WHITE, zoom=_zoom)
                                else:
                                    _psurf = _sreg.get(_tween["tile_id"], zoom=_zoom)
                                if _psurf is not None:
                                    screen.blit(
                                        _psurf,
                                        (_psx - _psurf.get_width() // 2,
                                         _psy - _psurf.get_height() // 2))

                        self._projectile_tweens = _living
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
                    # No weather effects underground — submaps are enclosed.
                    if self.current_submap_id is None:
                        _wstate = self.weather.state
                        if _wstate in ("light_rain", "heavy_rain",
                                       "resonance_storm", "bone_snow", "wind"):
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
                            # Wisp particle layer — drifting soft blobs over the gradient
                            if "fog_wisps" in self.data.weather_defs:
                                screen.set_clip(viewport)
                                renderer.draw_weather_overlay(
                                    screen, viewport,
                                    "fog_wisps", self.weather.intensity,
                                    self,
                                    player_screen_x=viewport.x + _player_sx,
                                    player_screen_y=viewport.y + _player_sy,
                                    tile_w=_tile_w, tile_h=_tile_h,
                                )
                                screen.set_clip(None)

                    # Step 8c: resonance emit overlay (gated on _resonance_sight_active)
                    if getattr(self, "_resonance_sight_active", False):
                        import math as _rmath
                        _ticks = pygame.time.get_ticks()
                        _re_surf = pygame.Surface((_tile_w, _tile_h), pygame.SRCALPHA)
                        _res_tiles_x = viewport.width // _tile_w + 2
                        _res_tiles_y = viewport.height // _tile_h + 2
                        screen.set_clip(viewport)
                        for _rx in range(cam_x, cam_x + _res_tiles_x):
                            for _ry in range(cam_y, cam_y + _res_tiles_y):
                                if not self.local_map.in_bounds(_rx, _ry):
                                    continue
                                if not self.local_map.visible[_rx, _ry]:
                                    continue
                                _rterrain = self.local_map.tiles["terrain"][_rx, _ry]
                                if isinstance(_rterrain, bytes):
                                    _rterrain = _rterrain.decode()
                                _rtd = self.data.terrain.get(str(_rterrain), {})
                                _remit = _rtd.get("resonance_emit", 0.0)
                                # Also check decor layer for resonance_emit
                                _rdid = self.local_map.decor.get((_rx, _ry))
                                if _rdid:
                                    _rdd = self.data.decoratives.get(_rdid, {})
                                    _remit = max(_remit, _rdd.get("resonance_emit", 0.0))
                                if _remit <= 0.0:
                                    continue
                                _phase = (_ticks + _rx * 1300 + _ry * 1700) % 4000
                                _pulse = (_rmath.sin(_phase / 4000.0 * _rmath.pi * 2) + 1.0) * 0.5
                                _alpha = int(25 + _pulse * 40)
                                _re_surf.fill((80, 0, 120, _alpha))
                                _rsx = int(viewport.x + shake_offset[0] + (_rx - cam_x) * _tile_w)
                                _rsy = int(viewport.y + shake_offset[1] + (_ry - cam_y) * _tile_h)
                                screen.blit(_re_surf, (_rsx, _rsy))
                        screen.set_clip(None)

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

            # --- UI panel frames + content (LOCAL / LOOK / INTERACTION_CURSOR / PLACEMENT_CURSOR) ---
            if self.mode in (GameMode.LOCAL, GameMode.LOOK,
                             GameMode.INTERACTION_CURSOR, GameMode.PLACEMENT_CURSOR):
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
                    self.ui._engine_sprint_turns    = self.sprint_turns_remaining
                    self.ui._engine_sprint_max      = self.display.SPRINT_DURATION
                    self.ui._engine_sprint_cooldown = self.sprint_cooldown_remaining
                    self.ui._engine_sprint_key      = self.display.SPRINT_KEY
                    # Moveset HUD data
                    _ms_weapon = self._get_equipped_weapon()
                    self.ui._engine_movesets = _ms_weapon.get("movesets", []) if _ms_weapon else []
                    self.ui._engine_moveset_cooldowns = self.moveset_cooldowns
                    self.ui._engine_weapon_essence = _ms_weapon.get("essence", "") if _ms_weapon else ""
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
            self.health_screen.render(screen, self)
            self.perk_screen.render(screen, self)
            self.craft_screen.render(screen, self)
            self.lexicon_screen.render(screen, self)

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
            if on_frame is not None:
                on_frame(self, screen)
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

    def spawn_projectile(
        self,
        sx: float, sy: float,
        tx: float, ty: float,
        tile_id: str,
        entity_id: int,
        duration:   float = 0.45,
        on_hit:     bool  = False,
        blood_type: str   = "red",
    ) -> None:
        """
        Spawn a 3-phase swoop tween from world tile (sx,sy) to halfway toward (tx,ty)
        and back. Damage is resolved before this call; on_hit drives impact FX.
        entity_id: id(entity) — suppresses the entity's normal render during the tween.
        tile_id: sprite tile key from sprite_map.json.
        Phases: 0-60% approach apex, 60-70% hold (impact FX), 70-100% retreat.
        """
        apex_x = sx + (tx - sx) * 0.5
        apex_y = sy + (ty - sy) * 0.5
        self._projectile_tweens.append({
            "sx": sx, "sy": sy,
            "tx": tx, "ty": ty,
            "apex_x": apex_x,
            "apex_y": apex_y,
            "tile_id": tile_id,
            "entity_id": entity_id,
            "elapsed": 0.0,
            "duration": max(0.05, duration),
            "on_hit": on_hit,
            "blood_type": blood_type,
            "_impact_fired": False,
        })

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
        # Paid modal actions also resolve Press. A killing moveset grants its
        # new opportunity only after all of its phases have finished.
        self._free_move_pending = False
        from engine.effect_lifecycle import live_actors, finish_turn
        effect_actors = live_actors(self)
        self._effect_aged_ids = set()
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

        # Speed bonus tick (stalker unguent)
        if self.player_speed_bonus_turns > 0:
            self.player_speed_bonus_turns -= 1
            if self.player_speed_bonus_turns == 0:
                self.player_speed_bonus = 0.0
                self.log.add("The quickening fades.", UI_TEXT_DIM)

        # True sight tick (wight concentrate)
        if self.true_sight_turns > 0:
            self.true_sight_turns -= 1
            if self.true_sight_turns == 0:
                self.player.true_sight = False
                self.log.add("The sight closes. The cost remains.", UI_TEXT_DIM)

        # Sprint cooldown tick
        if self.sprint_cooldown_remaining > 0:
            self.sprint_cooldown_remaining -= 1

        # Moveset cooldown tick
        if self.moveset_cooldowns:
            expired = [k for k, v in self.moveset_cooldowns.items() if v <= 1]
            for k in expired:
                del self.moveset_cooldowns[k]
            for k in self.moveset_cooldowns:
                self.moveset_cooldowns[k] -= 1

        # Vine network tick
        if self.local_map.vine_networks:
            from engine.vine_system import tick_vine_networks
            tick_vine_networks(self)

        needs = getattr(self.player, "needs", None)
        if needs and not self.player_invincible:
            prev_h = needs.hunger
            prev_t = needs.thirst

            # Compute biome-modified tick rates from survival.json
            h_rate = None
            t_rate = None
            if needs._configured and self.data.survival:
                chunk = self.world_map.get(self.world_x, self.world_y)
                if chunk:
                    mods = self.data.survival.get("biome_modifiers", {}).get(
                        chunk.biome_id, {}
                    )
                    h_rate = needs._h_tick * mods.get("hunger", 1.0)
                    t_rate = needs._t_tick * mods.get("thirst", 1.0)

            needs.advance(hunger_rate=h_rate, thirst_rate=t_rate)
            needs.drain_messages(self.log, prev_h, prev_t)

            # HP drain at critical stages — every hp_drain_interval turns
            if needs._configured:
                turn     = self.world_time.turn
                interval = needs._hp_drain_interval
                if turn > 0 and interval > 0 and turn % interval == 0:
                    total_drain = int(needs.hunger_hp_drain + needs.thirst_hp_drain)
                    if total_drain > 0:
                        fighter = getattr(self.player, "fighter", None)
                        if fighter:
                            fighter.take_damage(total_drain)
                            self.player.took_damage_this_turn = True
                            # Post crisis message based on dominant drain source
                            h_d = needs.hunger_hp_drain
                            t_d = needs.thirst_hp_drain
                            if h_d >= t_d:
                                self.log.add("Starvation takes from you.", MSG_DANGER)
                            else:
                                self.log.add("The thirst takes from you.", MSG_DANGER)
                            if fighter.is_dead:
                                h_d = needs.hunger_hp_drain
                                t_d = needs.thirst_hp_drain
                                self._death_killer = (
                                    "starvation" if h_d >= t_d else "thirst"
                                )
                                self._on_player_death()

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

        self._update_warmth()

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
                    from engine.item_transfers import consume
                    consume(self, item_ref)
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

        self._update_wraith_aura()

        # Snapshot positions before AI processes for concealment free-hit detection
        _pre_ai_pos = {id(e): (e.x, e.y) for e in self.entities}

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

        # Concealment free-hit: player gets one free attack when a hostile
        # creature steps into a concealment tile while adjacent.
        for _ce in self.entities:
            if _ce is self.player or not getattr(_ce, "is_alive", True):
                continue
            _old_pos = _pre_ai_pos.get(id(_ce))
            if _old_pos is None or (_ce.x, _ce.y) == _old_pos:
                continue  # didn't move
            _ct = self._resolve_terrain_id(_ce.x, _ce.y)
            _ctd = self.data.terrain.get(_ct, {})
            if _ctd.get("secondary_effect") != "concealment":
                continue
            if max(abs(_ce.x - self.player.x), abs(_ce.y - self.player.y)) > 1:
                continue
            equip = getattr(self.player, "equipment", None)
            if equip and equip.slots.get("weapon") is None:
                continue  # bare-handed — no free strike in grass
            self.log.add("It steps into your reach through the grass.", MSG_DEFAULT)
            self._player_attack(_ce)

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

        # Clear _just_arrived flags from previous turn and decrement arrival cooldowns.
        for _e_flag in self.entities:
            if getattr(_e_flag, "_just_arrived", False):
                _e_flag._just_arrived = False
            _acd = getattr(_e_flag, "_arrival_cooldown", 0)
            if _acd > 0:
                _e_flag._arrival_cooldown = _acd - 1

        self._process_creature_stair_transfers()
        self._check_entity_chunk_crossings()
        self._tick_live_pursuers()
        self._tick_pending_pursuer_arrivals()

        # Floor object decay — tick decay_timer on all floor objects in current chunk
        if self.local_map.floor_objects:
            from generation.floor_object_utils import remove_floor_object as _rfo_decay
            _decay_removals: list[tuple[tuple[int,int], object]] = []
            for _dpos, _ditems in self.local_map.floor_objects.items():
                for _ditem in _ditems:
                    _dt = getattr(_ditem, "decay_timer", None)
                    if _dt is not None:
                        if _dt <= 1:
                            _decay_removals.append((_dpos, _ditem))
                        else:
                            _ditem.decay_timer = _dt - 1
            for _dpos, _ditem in _decay_removals:
                _rfo_decay(self.local_map, _dpos[0], _dpos[1], _ditem)

        # The actual cache owner contains both surface and underground maps.
        # Identity de-duplication prevents the active map (or another alias) from
        # consuming two turns. Cold maps remain outside this bounded simulation.
        self._tick_processing_map(self.local_map, active=True)
        seen = {id(self.local_map)}
        cache = self.save_manager.cache
        for cached in list(cache.hot.values()) + list(cache.submap_hot.values()):
            local_map = cached.local_map
            if id(local_map) not in seen:
                seen.add(id(local_map))
                self._tick_processing_map(local_map, active=False)

        finish_turn(self, effect_actors)

        # Recompute FOV after every turn so wraith penalty (and all other
        # per-turn modifiers) are reflected immediately, not one turn late.
        self._update_fov()


    def _tick_processing_map(self, local_map, *, active: bool) -> None:
        """Complete processing in its owning map, once per simulated turn."""
        from generation.floor_object_utils import place_floor_object
        from generation.decor_utils import clear_decor
        from engine.processing_text import completion_text
        from engine.save_components import ITEM_STATE, snapshot, validate_fields
        failures = getattr(self, "_processing_completion_failures", None)
        if failures is None:
            failures = self._processing_completion_failures = {}
        for (x, y), record in list(local_map.processing_layer.items()):
            record["turns_remaining"] = max(0, record["turns_remaining"] - 1)
            if record["turns_remaining"] > 0:
                continue
            item_id = record.get("item_id", "")
            failure_key = (id(local_map), x, y)
            try:
                # Avoid ItemFactory's repeated missing-definition stdout warning.
                item = self.item_factory.create(item_id, x, y) if item_id in self.data.items else None
                if item is None:
                    raise ValueError("output definition is unavailable")
                validate_fields(snapshot(item, ITEM_STATE), ITEM_STATE, "processing output")
            except (ValueError, TypeError, KeyError, OverflowError) as error:
                problem = (id(record), item_id, str(error))
                if active and failures.get(failure_key) != problem:
                    self.log.add(f"Preparation of {item_id!r} cannot finish: {error}. The unfinished work remains.", MSG_DEFAULT)
                    failures[failure_key] = problem
                continue
            messages = getattr(self.data, "processing_messages", {})
            template = record.get("completion_message") or messages.get(
                record.get("source", ""), {}).get("complete", "{item_name} is ready.")
            message = completion_text(template, item.name)
            place_floor_object(local_map, x, y, item)
            del local_map.processing_layer[(x, y)]
            failures.pop(failure_key, None)
            decor_id = record.get("decor_id", "")
            if decor_id and local_map.decor.get((x, y)) == decor_id:
                clear_decor(local_map, x, y)
            if active:
                self.log.add(message, MSG_LORE)
                self.callouts.add("ready", self.world_x * MAP_WIDTH + x,
                                  self.world_y * MAP_HEIGHT + y, LIFE_GREEN, font_size="status")

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def _handle_key(self, key: int, text: str = "") -> None:
        # Death screen — R to restart (exit for re-launch), N to quit
        if self._player_is_dead:
            if key == pygame.K_r:
                pygame.quit()
                import sys
                sys.exit(0)
            elif key == pygame.K_n:
                import sys
                pygame.quit()
                print("The world endures.")
                raise SystemExit(2)
            return   # ignore all other keys
        
        if self._pending_consume is not None:
            from engine.effect_lifecycle import confirm_consume
            confirm_consume(self, key)
            return

        if self.debug and self.debug.handle_key(key, self):
            return

        if self.text_reader.open:
            self.text_reader.handle_key(key)
            return

        if self.inventory_screen.open:
            self.inventory_screen.handle_key(key, self)
            return

        if self.health_screen.open:
            self.health_screen.handle_key(key, self)
            return

        if self.perk_screen.open:
            self.perk_screen.handle_key(key, self)
            return

        if self.craft_screen.open:
            self.craft_screen.handle_key(key, self)
            return

        if self.lexicon_screen.open:
            self.lexicon_screen.handle_key(key, self)
            return

        if self.mode == GameMode.INTERACTION_CURSOR:
            self.interaction_cursor.handle_key(key, self)
            return

        if self.mode == GameMode.PLACEMENT_CURSOR:
            self._handle_key_placement(key)
            return

        # E key — open interaction cursor from LOCAL and LOOK modes.
        # Works without modifier. Closes look mode first if open.
        if key == pygame.K_e and self.mode not in (
            GameMode.PLACEMENT_CURSOR, GameMode.INTERACTION_CURSOR,
        ) and not getattr(self.inventory_screen, "open", False) \
          and not getattr(self.craft_screen, "open", False) \
          and not getattr(self.perk_screen, "open", False) \
          and not getattr(self.lexicon_screen, "open", False):
            if self.mode == GameMode.LOOK:
                self.mode = GameMode.LOCAL
            self._try_open_interaction_cursor()
            return

        if self.mode == GameMode.LOOK:
            self.look_mode.handle_key(key, self)
            return

        if self.mode == GameMode.LOCAL:
            if text == ">" and not self._pickup_mode:
                self._try_descend()
            elif text == "<" and not self._pickup_mode:
                self._try_ascend()
            else:
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
                if not self.interaction_cursor.can_reach(self, tx, ty):
                    self.log.add("You cannot reach that.", MSG_DEFAULT)
                    self._pickup_mode = False
                    return
                inv = getattr(self.player, "inventory", None)
                if inv is not None:
                    items = self._items_at(tx, ty)
                    if items:
                        if self._take_item(items[-1], inv):
                            self._advance_turn()
                    else:
                        self.log.add(
                            "Nothing there to take.",
                            WORN_STONE,
                        )
                self._pickup_mode = False
            return

        if key == pygame.K_m:
            if self.current_submap_id is None:
                self.overmap_cursor_x = self.world_x
                self.overmap_cursor_y = self.world_y
                self.overmap_cam_x    = self.world_x
                self.overmap_cam_y    = self.world_y
                self.mode = GameMode.OVERMAP
            else:
                self.log.add("No sky. No bearings.", MSG_DEFAULT)
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

        if key == pygame.K_h:
            self.health_screen.toggle()
            return

        if key == pygame.K_l:
            self.lexicon_screen.toggle()
            return

        self.player._in_concealment = False
        acted = False
        _was_move = False
        _press_step = False
        _moveset_result = None
        # Capture speed before consuming the final sprint move or salve turn.
        _move_speed = self.display.SPRINT_SPEED_MULT if self.sprint_turns_remaining > 0 else 1.0
        if self.player_speed_bonus_turns > 0:
            _move_speed += max(0.0, self.player_speed_bonus)
        _move_speed = max(1.0, _move_speed)

        # Sprint activation: Shift+SPRINT_KEY only (default W)
        _sprint_key = self.display.SPRINT_KEY
        if (key == _sprint_key
                and pygame.key.get_mods() & pygame.KMOD_SHIFT
                and self.sprint_turns_remaining == 0
                and self.sprint_cooldown_remaining == 0):
            self.sprint_turns_remaining = self.display.SPRINT_DURATION
            self.sprint_cooldown_remaining = self.display.SPRINT_COOLDOWN
            self.player_move_accumulator = 0.0
            self._free_move_pending = False
            self.callouts.add("SPRINT", float(self.player.x),
                              float(self.player.y) - 0.3,
                              RESONANCE_LOW, lifetime=1.2,
                              font_size="status")
            # Sprint activation itself doesn't count as a move or advance turn

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]

            dest_x = self.player.x + dx
            dest_y = self.player.y + dy

            if not self.local_map.in_bounds(dest_x, dest_y):
                acted = bool(self._transition_chunk(dx, dy))
                _was_move = acted
            elif self.local_map.tiles['terrain'][dest_x, dest_y] == 'door_closed':
                self.local_map.set_tile(dest_x, dest_y, 'door_open', True, True)
                self._update_fov()
                self.log.add("The door yields.", OLD_GOLD)
                acted = True
            elif self.local_map.walkable[dest_x, dest_y]:
                blocker = self._get_blocking_entity(dest_x, dest_y)
                if blocker:
                    acted = self._player_attack(blocker)
                elif self._decor_blocks_movement(dest_x, dest_y):
                    pass  # blocked by decor object (campfire, barrel, etc.)
                else:
                    _press_step = self._free_move_pending
                    _prev_x, _prev_y = self.player.x, self.player.y
                    self.player.move(dx, dy)
                    self._update_fov()
                    self._on_player_step(dest_x, dest_y)
                    acted = True
                    _was_move = True
                    _is_sprint_move = self.sprint_turns_remaining > 0
                    # Sprint turn decrement — counts player moves, not AI ticks
                    if _is_sprint_move:
                        self.sprint_turns_remaining -= 1
                        # Streak particles on every sprint move
                        import random as _sprint_rng
                        from rendering.particles import make_sprint_streaks
                        self.particle_system.emit_burst(
                            make_sprint_streaks(
                                float(_prev_x), float(_prev_y),
                                dx, dy, RESONANCE_LOW,
                                _sprint_rng.Random()))
                        if self.sprint_turns_remaining == 0:
                            self.callouts.add("\u2014", float(self.player.x),
                                              float(self.player.y) - 0.3,
                                              UI_TEXT_DIM, lifetime=0.8,
                                              font_size="status")

        elif key in (self.display.MOVESET_KEY_1, self.display.MOVESET_KEY_2):
            _moveset_result = self._try_moveset_action(key)
            acted = bool(_moveset_result)

        elif key in WAIT_KEYS:
            acted = True
            # Rain collection: accumulate toward filling empty_water_skin
            self._tick_rain_collection()

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

        elif key == pygame.K_c:
            self.craft_screen.toggle()
            return

        elif key == pygame.K_COMMA:
            acted = self._pick_up_item()

        elif key == pygame.K_g:
            acted = self._try_harvest()
            if not acted:
                acted = self._try_gather(self.player.x, self.player.y)
            if not acted:
                acted = self._pick_up_item()

        elif key == pygame.K_w and not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
            acted = self._try_drink_terrain()

        if acted:
            self._log_scroll = 0
            self._free_move_pending = False
            # Fractional credit earns skipped enemy phases, never extra ones.
            # Non-movement actions always advance time and never spend this credit.
            skip_turn = _press_step
            if _was_move and not _press_step:
                self.player_move_accumulator += 1.0 - 1.0 / _move_speed
                if self.player_move_accumulator >= 1.0 - 1e-9:
                    self.player_move_accumulator = max(0.0, self.player_move_accumulator - 1.0)
                    skip_turn = True
            phases = 0 if skip_turn else 1
            if _moveset_result:
                phases = self._weapon_action_phases(_moveset_result.turn_cost)
            for _ in range(phases):
                if self._player_is_dead or not self.player.is_alive:
                    break
                self._advance_turn()
            while (self._move_debt >= 1.0
                   and not self._player_is_dead and self.player.is_alive):
                self._move_debt -= 1.0
                self._advance_turn()
            if (_moveset_result and _moveset_result.free_move
                    and not self._player_is_dead and self.player.is_alive):
                self._free_move_pending = True
                self.log.add("Momentum: one free local step. Terrain still slows you; another action gives it up.", MSG_COMBAT_OUT)
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
            if self.debug:
                self._teleport_to_overmap_cursor()
            else:
                self.log.add(
                    "Travel planning is not yet implemented.",
                    STONE_BLUE,
                )
                self.mode = GameMode.LOCAL
        elif key in {pygame.K_m, pygame.K_ESCAPE}:
            self.mode = GameMode.LOCAL

    def _ensure_surface_scene(self, wx, wy):
        """Active owner, existing cache, or one complete staged creation; never backfill."""
        from engine.scene_generation import create_surface, publish_metadata
        from generation.context import GenerationError
        if (wx, wy, None) == (self.world_x, self.world_y, self.current_submap_id):
            return self.local_map, [e for e in self.entities if e is not self.player]
        cached = self.save_manager.cache.load(wx, wy)
        if cached is not None:
            return cached.local_map, _deserialize_entities_inline(cached.entities, self)
        chunk = self.world_map.get(wx, wy)
        if chunk is None:
            raise GenerationError(f'surface ({wx},{wy}): unknown destination')
        if chunk.visited or getattr(chunk, 'generation_revision', None):
            raise GenerationError(f'surface ({wx},{wy}): missing previously owned scene; generation refused')
        result = create_surface(self.world_map, chunk, self.data, self.item_factory,
                                self.creature_factory, MAP_WIDTH, MAP_HEIGHT)
        self.save_manager.cache.store(wx, wy, result.local_map, result.actors)
        publish_metadata(chunk, result.metadata)
        chunk.generation_revision = result.local_map.generation_revision
        return result.local_map, result.actors

    def _ensure_submap_scene(self, wx, wy, submap_id):
        from engine.scene_generation import create_submap, publish_metadata
        from generation.context import GenerationError
        if (wx, wy, submap_id) == (self.world_x, self.world_y, self.current_submap_id):
            return self.local_map, [e for e in self.entities if e is not self.player]
        cached = self.save_manager.cache.load_submap(submap_id)
        if cached is not None:
            return cached.local_map, _deserialize_entities_inline(cached.entities, self)
        chunk = self.world_map.get(wx, wy)
        submap = next((s for s in chunk.submaps if s.submap_id == submap_id), None) if chunk else None
        if submap is None:
            raise GenerationError(f'{submap_id}: unknown submap destination ({wx},{wy})')
        if submap.generated:
            raise GenerationError(f'{submap_id}: missing previously owned scene; generation refused')
        result = create_submap(self.world_map, wx, wy, submap, self.data, self.item_factory,
                               self.creature_factory, MAP_WIDTH, MAP_HEIGHT)
        self.save_manager.cache.store_submap(submap_id, result.local_map, result.actors)
        publish_metadata(submap, result.metadata)
        return result.local_map, result.actors

    def _prepare_destination(self, wx, wy, submap_id=None):
        """Expected creation/read failures leave the departing owners untouched."""
        try:
            if submap_id is None:
                return self._ensure_surface_scene(wx, wy)
            return self._ensure_submap_scene(wx, wy, submap_id)
        except (ValueError, OSError) as error:
            self.log.add(f'Scene entry failed: {error}', STONE_BLUE)
            return None

    def _teleport_to_overmap_cursor(self) -> None:
        """Debug travel shares normal scene ownership and complete creation."""
        wx, wy = self.overmap_cursor_x, self.overmap_cursor_y
        chunk = self.world_map.get(wx, wy)
        if chunk is None:
            return
        prepared = self._prepare_destination(wx, wy)
        if prepared is None:
            return
        if (wx, wy, None) != (self.world_x, self.world_y, self.current_submap_id):
            from engine.effect_lifecycle import reset_wraith_aura
            reset_wraith_aura(self)
            self._wraith_overcorrect_turns = 0
        from engine.save_manager import SceneAddress
        SceneAddress(self.world_x, self.world_y, self.current_submap_id).store(
            self.save_manager.cache, self.local_map, self.entities)
        self.local_map, natives = prepared
        self.world_x, self.world_y, self.current_submap_id = wx, wy, None
        self.player.x, self.player.y = self._find_walkable_near(
            self.local_map, self.local_map.width // 2, self.local_map.height // 2)
        self.entities = [self.player] + natives
        # Live pursuers at this exact scene change owner once.
        for actor, px, py, sid in list(self._live_pursuers):
            if (px, py, sid) == (wx, wy, None):
                self._live_arrive(actor, actor.x, actor.y)
        chunk.visited = True
        self.world_map.mark_explored_radius(wx, wy, radius=2)
        self._update_fov()
        self.mode = GameMode.LOCAL
        self.log.add(f'Arrived at {chunk.name or chunk.region_type.value}.', LIFE_GREEN)

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
        elif self.mode == GameMode.INTERACTION_CURSOR:
            cx = self.interaction_cursor.cursor_x
            cy = self.interaction_cursor.cursor_y
        elif self.mode == GameMode.PLACEMENT_CURSOR:
            cx = self._placement_cursor_x
            cy = self._placement_cursor_y
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

    def _transition_chunk(self, dx: int, dy: int) -> bool:
        if self.bounded_room_test:
            self.log.add("Disposable room test: travel is limited to the room and its foyer.", STONE_BLUE)
            return False
        # Clear screen-space particles — their absolute pixel coords become
        # invalid when the camera shifts to a new chunk.
        self.particle_system.particles.clear()

        # Stale transfers from interrupted transitions must never accumulate.
        self._pending_transfer = []

        # Determine which chunk to enter based on which boundary was crossed,
        # not the movement direction. Diagonal only when both x AND y are
        # simultaneously out of bounds (true corner exit).
        dest_x = self.player.x + dx
        dest_y = self.player.y + dy

        x_under = dest_x < 0
        x_over  = dest_x >= MAP_WIDTH
        y_under = dest_y < 0
        y_over  = dest_y >= MAP_HEIGHT

        wx_off = -1 if x_under else (1 if x_over else 0)
        wy_off = -1 if y_under else (1 if y_over else 0)

        new_wx = self.world_x + wx_off
        new_wy = self.world_y + wy_off

        if not self.world_map.in_bounds(new_wx, new_wy):
            return False

        chunk = self.world_map.get(new_wx, new_wy)
        if not chunk:
            return False

        prepared = self._prepare_destination(new_wx, new_wy)
        if prepared is None:
            return False
        new_map, new_entities = prepared

        from engine.effect_lifecycle import reset_wraith_aura
        reset_wraith_aura(self)
        self._wraith_overcorrect_turns = 0

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

        # Extract pursuing entities into _live_pursuers before caching the old chunk.
        # They will be ticked every turn and promoted back to self.entities when they
        # cross into the player's current chunk.
        from components.ai import AIState as _AIState_tp
        from config import DEBUG_MODE as _DM_tp
        _pursuing_tp = (_AIState_tp.HUNTING, _AIState_tp.ALERTED, _AIState_tp.ATTACKING)
        _threshold_tp = self.data.ai_config.get("pursuit_boundary_threshold", 3)
        _extract_ids_tp: set[int] = set()
        for _ep in self.entities:
            if _ep is self.player:
                continue
            if not getattr(_ep, "is_alive", True):
                continue
            _eai_tp = getattr(_ep, "ai", None)
            if _eai_tp is None or _eai_tp.state not in _pursuing_tp:
                continue
            _can_cross_tp = self.data.entities.get(creature_id(_ep), {}).get("can_cross_chunks", False)
            if not _can_cross_tp:
                continue
            # Allow re-extraction even with arrival cooldown — prevents losing
            # pursuit on back-and-forth transitions. Cooldown only gates
            # _check_entity_chunk_crossings (same-turn re-crossing), not re-extraction.
            _acd_tp = getattr(_ep, "_arrival_cooldown", 0)
            _dist_tp = max(abs(_ep.x - self.player.x), abs(_ep.y - self.player.y))
            # State-gated: any HUNTING/ALERTED creature with can_cross_chunks
            # is always extracted. pursuit_timeout handles true abandonment.
            _extracted_tp = True
            if _DM_tp:
                print(f"[LP-CHECK] {_ep.name} state={_eai_tp.state.name} "
                      f"dist={_dist_tp} can_cross={_can_cross_tp} "
                      f"acd={_acd_tp} -> EXTRACTED")
            if _extracted_tp:
                _extract_ids_tp.add(id(_ep))
                # Avoid duplicate entries in _live_pursuers
                _already_tracked = any(id(_lp[0]) == id(_ep) for _lp in self._live_pursuers)
                if _already_tracked:
                    if _DM_tp:
                        print(f"[LP-RE-EXTRACT] {_ep.name} already tracked, updating position")
                    self._live_pursuers = [
                        _lp for _lp in self._live_pursuers if id(_lp[0]) != id(_ep)
                    ]
                elif _acd_tp > 0 and _DM_tp:
                    print(f"[LP-RE-EXTRACT] {_ep.name} re-extracted from departing chunk (had cooldown {_acd_tp})")
                _ep._arrival_cooldown = 0
                self._live_pursuers.append((_ep, self.world_x, self.world_y, None))
                # Point entity toward the boundary edge it needs to cross to follow player.
                if _eai_tp is not None:
                    from config import MAP_WIDTH as _MWtp, MAP_HEIGHT as _MHtp
                    if wx_off == -1:
                        _ep._last_known_px = 0;          _ep._last_known_py = _ep.y
                        _eai_tp.target_x   = 0;          _eai_tp.target_y   = _ep.y
                    elif wx_off == 1:
                        _ep._last_known_px = _MWtp - 1;  _ep._last_known_py = _ep.y
                        _eai_tp.target_x   = _MWtp - 1;  _eai_tp.target_y   = _ep.y
                    elif wy_off == -1:
                        _ep._last_known_px = _ep.x;      _ep._last_known_py = 0
                        _eai_tp.target_x   = _ep.x;      _eai_tp.target_y   = 0
                    elif wy_off == 1:
                        _ep._last_known_px = _ep.x;      _ep._last_known_py = _MHtp - 1
                        _eai_tp.target_x   = _ep.x;      _eai_tp.target_y   = _MHtp - 1
                if _DM_tp:
                    print(f"[LIVE-EXTRACT] {_ep.name} from ({self.world_x},{self.world_y}) "
                          f"lk=({getattr(_ep,'_last_known_px',None)},{getattr(_ep,'_last_known_py',None)})")
        if _extract_ids_tp:
            self.entities = [_e for _e in self.entities if id(_e) not in _extract_ids_tp]

        self.save_manager.cache.store(
            self.world_x,
            self.world_y,
            self.local_map,
            self.entities,
        )
        if _DM_tp:
            print(f"[LP-STORED] {len(self._live_pursuers)} live pursuers: "
                  f"{[e.name for e, wx, wy, si in self._live_pursuers]}")

        # ── Mirror entry position from boundary violations ─────────────
        # Cardinal crossing: preserve the perpendicular axis.
        # True diagonal (both x and y out of bounds): land at the corner.
        if wx_off != 0 and wy_off != 0:
            # True diagonal — both x and y simultaneously out of bounds
            entry_x = MAP_WIDTH  - 1 if wx_off == -1 else 0
            entry_y = MAP_HEIGHT - 1 if wy_off == -1 else 0
        elif wx_off != 0:
            # East or west crossing — preserve y
            entry_x = MAP_WIDTH - 1 if wx_off == -1 else 0
            entry_y = max(0, min(MAP_HEIGHT - 1, dest_y))
        else:
            # North or south crossing — preserve x
            entry_x = max(0, min(MAP_WIDTH  - 1, dest_x))
            entry_y = MAP_HEIGHT - 1 if wy_off == -1 else 0

        # Store entry position for arriving pursuers — they must enter at
        # the same edge the player used, not the opposite edge.
        self._last_chunk_entry = (entry_x, entry_y)

        # Diagnostic (DEBUG_MODE): log boundary violations and entry
        from config import DEBUG_MODE as _DM
        if _DM:
            _dir_map = {
                (-1,-1):"NW", (0,-1):"N", (1,-1):"NE",
                (-1, 0):"W",              (1, 0):"E",
                (-1, 1):"SW", (0, 1):"S", (1, 1):"SE",
            }
            dir_name = _dir_map.get((wx_off, wy_off), f"({wx_off},{wy_off})")
            print(
                f"[CHUNK] {dir_name} player=({self.player.x},{self.player.y}) "
                f"dest=({dest_x},{dest_y}) "
                f"-> entry=({entry_x},{entry_y}) "
                f"world ({self.world_x},{self.world_y})->({new_wx},{new_wy})"
            )

        # Find the nearest walkable tile to the mirror entry point.
        # max_radius=3 searches a 7×7 area; falls back to map centre if blocked.
        spawn_x, spawn_y = self._find_walkable_near(new_map, entry_x, entry_y,
                                                    max_radius=3)
        _centre = (new_map.width // 2, new_map.height // 2)
        if (spawn_x, spawn_y) == _centre and (entry_x, entry_y) != _centre:
            print(
                f"[CHUNK] WARNING: no walkable tile near entry ({entry_x},{entry_y}) "
                f"in chunk ({new_wx},{new_wy}), falling back to centre"
            )

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

        # Promote any live pursuers that were already in the new chunk
        _promo_keep: list = []
        _promo_list: list = []
        for (_lpe, _lpwx, _lpwy, _lpsi) in self._live_pursuers:
            # Only promote surface-chunk pursuers that are now in the player's chunk.
            # Submap pursuers (lpsi != None) are never promoted via chunk crossing.
            if _lpsi is None and _lpwx == self.world_x and _lpwy == self.world_y:
                _promo_list.append(_lpe)
            else:
                _promo_keep.append((_lpe, _lpwx, _lpwy, _lpsi))
        if _promo_list:
            self._live_pursuers = _promo_keep
            _occ_promo: set[tuple[int, int]] = {(self.player.x, self.player.y)}
            for _ne_promo in self.entities:
                if getattr(_ne_promo, "blocks_movement", True):
                    _occ_promo.add((_ne_promo.x, _ne_promo.y))
            for _lpe in _promo_list:
                _placed_promo = False
                for _r_promo in range(0, 12):
                    for _rdx_promo in range(-_r_promo, _r_promo + 1):
                        for _rdy_promo in range(-_r_promo, _r_promo + 1):
                            if _r_promo > 0 and abs(_rdx_promo) != _r_promo and abs(_rdy_promo) != _r_promo:
                                continue
                            _nx_promo = _lpe.x + _rdx_promo
                            _ny_promo = _lpe.y + _rdy_promo
                            if (self.local_map.in_bounds(_nx_promo, _ny_promo)
                                    and self.local_map.walkable[_nx_promo, _ny_promo]
                                    and (_nx_promo, _ny_promo) not in _occ_promo):
                                _lpe.x, _lpe.y = _nx_promo, _ny_promo
                                _occ_promo.add((_nx_promo, _ny_promo))
                                _placed_promo = True
                                break
                        if _placed_promo:
                            break
                    if _placed_promo:
                        break
                if not _placed_promo:
                    _lpe.x, _lpe.y = self._find_walkable_near(
                        self.local_map, _lpe.x, _lpe.y, max_radius=50
                    )
                # Nudge one step inward from boundary to prevent immediate re-crossing
                if _lpe.x <= 0:
                    _lpe.x = 1
                elif _lpe.x >= MAP_WIDTH - 1:
                    _lpe.x = MAP_WIDTH - 2
                if _lpe.y <= 0:
                    _lpe.y = 1
                elif _lpe.y >= MAP_HEIGHT - 1:
                    _lpe.y = MAP_HEIGHT - 2
                _lpe._just_arrived     = True
                _lpe._arrival_cooldown = 3
                _lpe._last_known_px = self.player.x
                _lpe._last_known_py = self.player.y
                _lpe.last_known_x   = None
                _lpe.last_known_y   = None
                if _lpe.ai is not None:
                    _lpe.ai.target_x = self.player.x
                    _lpe.ai.target_y = self.player.y
                self.entities.append(_lpe)
                if _DM_tp:
                    print(f"[LIVE-PROMOTE] {_lpe.name} -> new chunk ({self.world_x},{self.world_y}) "
                          f"at ({_lpe.x},{_lpe.y})")

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

        # Deliver any items that completed processing while player was away
        _ready = getattr(self.local_map, "ready_items", [])
        if _ready:
            from generation.floor_object_utils import place_floor_object as _pfo_ri
            for _ri in _ready:
                _ri_id   = _ri.get("item_id", "")
                _ri_lx   = _ri.get("lx", self.player.x)
                _ri_ly   = _ri.get("ly", self.player.y)
                _ri_item = self.item_factory.create(_ri_id, _ri_lx, _ri_ly)
                if _ri_item:
                    _ri_item.x = _ri_lx
                    _ri_item.y = _ri_ly
                    _pfo_ri(self.local_map, _ri_lx, _ri_ly, _ri_item)
                    self.log.add(f"{_ri_item.name} is ready.", MSG_LORE)
            self.local_map.ready_items = []

        # Travel writes the session cache; only an explicit save publishes a
        # checkpoint. F9 must still restore the last F5 state after crossing.
        self._update_context_prompt()
        self._free_move_pending = False
        return True

    # ------------------------------------------------------------------ #
    #  SubMap traversal (stairs)
    # ------------------------------------------------------------------ #

    def _can_use_stairs(self) -> bool:
        """Stairs are physical actions and share the normal input guards."""
        fighter = getattr(self.player, "fighter", None)
        return (not self._player_is_dead and self.player.is_alive
                and (fighter is None or not fighter.is_dead)
                and self.mode == GameMode.LOCAL and not self._pickup_mode
                and self._pending_consume is None
                and not any(screen.open for screen in (
                    self.text_reader, self.inventory_screen, self.health_screen,
                    self.perk_screen, self.craft_screen, self.lexicon_screen)))

    def _try_descend(self) -> None:
        """Player attempts to descend. Must be standing on stairs_down."""
        if not self._can_use_stairs():
            return
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
        if not self._can_use_stairs():
            return
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
        chunk = self.world_map.get(self.world_x, self.world_y)
        if not chunk:
            return
        submap = next((s for s in chunk.submaps if s.submap_id == submap_id), None)
        if not submap:
            return

        prepared = self._prepare_destination(self.world_x, self.world_y, submap_id)
        if prepared is None:
            return
        new_map, new_entities = prepared

        self._free_move_pending = False

        self.particle_system.particles.clear()
        from engine.effect_lifecycle import reset_wraith_aura
        reset_wraith_aura(self)
        self._wraith_overcorrect_turns = 0
        self.player._hollow_knight_disruption = False

        # Clear ephemeral tiles (blood, bone dust, etc.) from the surface
        # before caching — same as _transition_chunk does on chunk exit.
        surface_chunk = self.world_map.get(self.world_x, self.world_y)
        if surface_chunk and surface_chunk.ephemeral_tiles:
            for _ex, _ey, _orig in surface_chunk.ephemeral_tiles:
                if self.local_map.in_bounds(_ex, _ey):
                    _t = self.data.terrain.get(_orig, {})
                    self.local_map.set_tile(
                        _ex, _ey, _orig,
                        _t.get("walkable", True),
                        _t.get("transparent", True),
                    )
            surface_chunk.ephemeral_tiles.clear()

        # Identify hot entities to transfer into the submap with the player.
        # Criteria: HUNTING/ALERTED, alive, can_cross_chunks, within threshold of
        # the stair tile. can_use_stairs entities always transfer regardless of distance.
        from components.ai import AIState as _AIState
        _stair_x, _stair_y = self.player.x, self.player.y
        self._pending_transfer = []
        _hot_ids_stair: set[int] = set()
        for _e in self.entities:
            if _e is self.player:
                continue
            _eai = getattr(_e, "ai", None)
            if _eai is None or _eai.state not in (_AIState.HUNTING, _AIState.ALERTED, _AIState.ATTACKING):
                continue
            if not getattr(_e, "is_alive", True):
                continue
            _cdef = self.data.entities.get(creature_id(_e), {})
            if not _cdef.get("can_cross_chunks", False):
                continue
            _dist = max(abs(_e.x - _stair_x), abs(_e.y - _stair_y))
            if _dist <= 1:
                self._pending_transfer.append(_e)
                _hot_ids_stair.add(id(_e))
        self.entities = [_e for _e in self.entities if id(_e) not in _hot_ids_stair]

        # Non-adjacent live pursuer extraction: pursuing entities too far for the
        # 1-tile proactive transfer still follow the player through the stair.
        _lp_ids_sd: set[int] = set()
        for _lpe_sd in list(self.entities):
            if _lpe_sd is self.player:
                continue
            _lpeai_sd = getattr(_lpe_sd, "ai", None)
            if _lpeai_sd is None or _lpeai_sd.state not in (_AIState.HUNTING, _AIState.ALERTED, _AIState.ATTACKING):
                continue
            if not getattr(_lpe_sd, "is_alive", True):
                continue
            _lpcd_sd = self.data.entities.get(creature_id(_lpe_sd), {})
            if not _lpcd_sd.get("can_cross_chunks", False):
                continue
            _lpt_sd = getattr(_lpeai_sd, "pursuit_turns_without_contact", 0)
            _lpto_sd = _lpcd_sd.get("pursuit_timeout", 20)
            if _lpt_sd >= _lpto_sd:
                continue
            _lpe_sd._last_known_px = _stair_x
            _lpe_sd._last_known_py = _stair_y
            _lpeai_sd.target_x = _stair_x
            _lpeai_sd.target_y = _stair_y
            _lp_ids_sd.add(id(_lpe_sd))
            self._live_pursuers.append((_lpe_sd, self.world_x, self.world_y, None))
            if DEBUG_MODE:
                print(f"[LIVE-EXTRACT-STAIR-DOWN] {_lpe_sd.name} from ({self.world_x},{self.world_y}) lk=({_stair_x},{_stair_y})")
        if _lp_ids_sd:
            self.entities = [_e for _e in self.entities if id(_e) not in _lp_ids_sd]

        # Cache current surface state
        self.save_manager.cache.store(
            self.world_x, self.world_y,
            self.local_map, self.entities,
        )

        # Remember where to return on ascent
        self.surface_return_x  = self.player.x
        self.surface_return_y  = self.player.y
        self.current_submap_id = submap_id

        spawn_x, spawn_y = self._find_walkable_near(
            new_map, submap.entry_x, submap.entry_y
        )
        self.player.x  = spawn_x
        self.player.y  = spawn_y
        self.local_map = new_map
        self.entities  = [self.player] + new_entities

        # Merge transferred entities into the submap near the entry stair
        if self._pending_transfer:
            _occ_stair: set[tuple[int, int]] = {(self.player.x, self.player.y)}
            for _ne in new_entities:
                if getattr(_ne, "blocks_movement", True):
                    _occ_stair.add((_ne.x, _ne.y))
            _ex_s, _ey_s = submap.entry_x, submap.entry_y
            for _te in self._pending_transfer:
                _placed_s = False
                for _pr_s in range(0, 12):
                    for _pdx_s in range(-_pr_s, _pr_s + 1):
                        for _pdy_s in range(-_pr_s, _pr_s + 1):
                            if _pr_s > 0 and abs(_pdx_s) != _pr_s and abs(_pdy_s) != _pr_s:
                                continue
                            _nx_s = _ex_s + _pdx_s
                            _ny_s = _ey_s + _pdy_s
                            if (new_map.in_bounds(_nx_s, _ny_s)
                                    and new_map.walkable[_nx_s, _ny_s]
                                    and (_nx_s, _ny_s) not in _occ_stair):
                                _te.x, _te.y = _nx_s, _ny_s
                                _occ_stair.add((_nx_s, _ny_s))
                                _placed_s = True
                                break
                        if _placed_s:
                            break
                    if _placed_s:
                        break
                if not _placed_s:
                    _fx_s, _fy_s = self._find_walkable_near(new_map, _ex_s, _ey_s, max_radius=50)
                    _te.x, _te.y = _fx_s, _fy_s
                    _occ_stair.add((_fx_s, _fy_s))
                if hasattr(_te, "ai"):
                    _te.ai._last_known_px = self.player.x
                    _te.ai._last_known_py = self.player.y
                    _te.ai.target_x = self.player.x
                    _te.ai.target_y = self.player.y
                _te._last_known_px = self.player.x
                _te._last_known_py = self.player.y
                self.entities.append(_te)
                if DEBUG_MODE:
                    print(f"[TRANSFER-STAIR-DOWN] {_te.name} -> submap ({_te.x},{_te.y})")
            self._pending_transfer = []

        self._update_fov()
        label = submap.name or submap.submap_type
        self.log.add_world(f"You descend into {label}.")
        self._check_resonance_message()
        self._update_context_prompt()

    def _ascend_from_submap(self) -> None:
        """Cache submap, restore surface, place player at return coords."""
        prepared = self._prepare_destination(self.world_x, self.world_y)
        if prepared is None:
            return
        new_map, new_entities = prepared
        self._free_move_pending = False
        self.particle_system.particles.clear()
        from engine.effect_lifecycle import reset_wraith_aura
        reset_wraith_aura(self)
        self._wraith_overcorrect_turns = 0
        self.player._hollow_knight_disruption = False

        # Identify hot entities to transfer to the surface with the player.
        from components.ai import AIState as _AIState
        _stair_x2, _stair_y2 = self.player.x, self.player.y
        self._pending_transfer = []
        _hot_ids_asc: set[int] = set()
        for _e in self.entities:
            if _e is self.player:
                continue
            _eai2 = getattr(_e, "ai", None)
            if _eai2 is None or _eai2.state not in (_AIState.HUNTING, _AIState.ALERTED, _AIState.ATTACKING):
                continue
            if not getattr(_e, "is_alive", True):
                continue
            _cdef2 = self.data.entities.get(creature_id(_e), {})
            if not _cdef2.get("can_cross_chunks", False):
                continue
            _dist2 = max(abs(_e.x - _stair_x2), abs(_e.y - _stair_y2))
            if _dist2 <= 1:
                self._pending_transfer.append(_e)
                _hot_ids_asc.add(id(_e))
        self.entities = [_e for _e in self.entities if id(_e) not in _hot_ids_asc]

        # Non-adjacent live pursuer extraction (submap -> surface followers).
        # current_submap_id is still valid here (cleared below after surface reload).
        _lp_ids_su: set[int] = set()
        _submap_id_su = self.current_submap_id
        for _lpe_su in list(self.entities):
            if _lpe_su is self.player:
                continue
            _lpeai_su = getattr(_lpe_su, "ai", None)
            if _lpeai_su is None or _lpeai_su.state not in (_AIState.HUNTING, _AIState.ALERTED, _AIState.ATTACKING):
                continue
            if not getattr(_lpe_su, "is_alive", True):
                continue
            _lpcd_su = self.data.entities.get(creature_id(_lpe_su), {})
            if not _lpcd_su.get("can_cross_chunks", False):
                continue
            _lpt_su = getattr(_lpeai_su, "pursuit_turns_without_contact", 0)
            _lpto_su = _lpcd_su.get("pursuit_timeout", 20)
            if _lpt_su >= _lpto_su:
                continue
            # Stamp surface exit coords so _transfer_submap_pursuer_to_surface() knows placement
            _lpe_su._surface_exit_x  = self.surface_return_x
            _lpe_su._surface_exit_y  = self.surface_return_y
            _lpe_su._surface_exit_wx = self.world_x
            _lpe_su._surface_exit_wy = self.world_y
            _lpe_su._last_known_px   = _stair_x2
            _lpe_su._last_known_py   = _stair_y2
            _lpeai_su.target_x = _stair_x2
            _lpeai_su.target_y = _stair_y2
            _lp_ids_su.add(id(_lpe_su))
            self._live_pursuers.append((_lpe_su, self.world_x, self.world_y, _submap_id_su))
            if DEBUG_MODE:
                print(f"[LIVE-EXTRACT-STAIR-UP] {_lpe_su.name} from {_submap_id_su} lk=({_stair_x2},{_stair_y2})")
        if _lp_ids_su:
            self.entities = [_e for _e in self.entities if id(_e) not in _lp_ids_su]

        # Cache the current submap state (without transferred entities)
        self.save_manager.cache.store_submap(
            self.current_submap_id,
            self.local_map,
            self.entities,
        )

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

        # Merge transferred entities onto the surface near the stair exit
        if self._pending_transfer:
            _occ_asc: set[tuple[int, int]] = {(self.player.x, self.player.y)}
            for _ne2 in new_entities:
                if getattr(_ne2, "blocks_movement", True):
                    _occ_asc.add((_ne2.x, _ne2.y))
            _ex_a, _ey_a = self.surface_return_x, self.surface_return_y
            for _te2 in self._pending_transfer:
                _placed_a = False
                for _pr_a in range(0, 12):
                    for _pdx_a in range(-_pr_a, _pr_a + 1):
                        for _pdy_a in range(-_pr_a, _pr_a + 1):
                            if _pr_a > 0 and abs(_pdx_a) != _pr_a and abs(_pdy_a) != _pr_a:
                                continue
                            _nx_a = _ex_a + _pdx_a
                            _ny_a = _ey_a + _pdy_a
                            if (new_map.in_bounds(_nx_a, _ny_a)
                                    and new_map.walkable[_nx_a, _ny_a]
                                    and (_nx_a, _ny_a) not in _occ_asc):
                                _te2.x, _te2.y = _nx_a, _ny_a
                                _occ_asc.add((_nx_a, _ny_a))
                                _placed_a = True
                                break
                        if _placed_a:
                            break
                    if _placed_a:
                        break
                if not _placed_a:
                    _fx_a, _fy_a = self._find_walkable_near(new_map, _ex_a, _ey_a, max_radius=50)
                    _te2.x, _te2.y = _fx_a, _fy_a
                    _occ_asc.add((_fx_a, _fy_a))
                if hasattr(_te2, "ai"):
                    _te2.ai._last_known_px = self.player.x
                    _te2.ai._last_known_py = self.player.y
                    _te2.ai.target_x = self.player.x
                    _te2.ai.target_y = self.player.y
                _te2._last_known_px = self.player.x
                _te2._last_known_py = self.player.y
                self.entities.append(_te2)
                if DEBUG_MODE:
                    print(f"[TRANSFER-STAIR-UP] {_te2.name} -> surface ({_te2.x},{_te2.y})")
            self._pending_transfer = []

        self._update_fov()
        chunk = self.world_map.get(self.world_x, self.world_y)
        label = (chunk.name if chunk and chunk.name else "the surface")
        self.log.add_world(f"You emerge into {label}.")
        self._update_context_prompt()

    def _check_entity_chunk_crossings(self) -> None:
        """Detect entities that have reached a chunk boundary during their AI turn.

        Entities with can_cross_chunks whose last-known player position is at the
        same edge are transferred to the adjacent chunk.  If the adjacent chunk is
        the player's current chunk they are merged immediately; otherwise they are
        cached there (the player will load them on next entry).

        Entities without can_cross_chunks are clamped inside bounds.
        """
        from components.ai import AIState as _AIState
        from config import DEBUG_MODE as _DM_cc

        _pursuing = (_AIState.HUNTING, _AIState.ALERTED, _AIState.ATTACKING)
        _crossed: list = []
        _to_remove: set[int] = set()
        # IDs of entities under live pursuer management — skip them
        _managed_ids_cc = (
            {id(lp[0]) for lp in self._live_pursuers} |
            {id(p["entity"]) for p in self._pending_pursuer_arrivals}
        )

        for _e in self.entities:
            if _e is self.player:
                continue
            if not getattr(_e, "is_alive", True):
                continue
            # Skip entities managed by the live pursuer / pending arrival system
            if id(_e) in _managed_ids_cc:
                continue
            # Skip entities that just arrived this turn — prevent immediate re-crossing
            if getattr(_e, "_just_arrived", False):
                if _DM_cc:
                    print(f"[ENTITY-CROSS] SKIP {_e.name} — _just_arrived")
                continue
            from engine.effect_lifecycle import disrupted
            if disrupted(_e, self.local_map):
                continue
            _eai = getattr(_e, "ai", None)
            if _eai is None or _eai.state not in _pursuing:
                continue
            _lkx = getattr(_e, "_last_known_px", None)
            _lky = getattr(_e, "_last_known_py", None)
            if _lkx is None:
                continue
            _cdef = self.data.entities.get(creature_id(_e), {})
            if not _cdef.get("can_cross_chunks", False):
                # Non-mobile: clamp inside bounds
                _e.x = max(0, min(MAP_WIDTH  - 1, _e.x))
                _e.y = max(0, min(MAP_HEIGHT - 1, _e.y))
                continue

            # Determine crossing direction: entity at boundary edge, last-known
            # position confirms player exited that way.
            _wx_off = 0
            _wy_off = 0
            if _e.x <= 0 and _lkx <= 1:
                _wx_off = -1
            elif _e.x >= MAP_WIDTH - 1 and _lkx >= MAP_WIDTH - 2:
                _wx_off = 1
            if _e.y <= 0 and _lky <= 1:
                _wy_off = -1
            elif _e.y >= MAP_HEIGHT - 1 and _lky >= MAP_HEIGHT - 2:
                _wy_off = 1

            if _wx_off == 0 and _wy_off == 0:
                continue

            _new_wx = self.world_x + _wx_off
            _new_wy = self.world_y + _wy_off
            if not self.world_map.in_bounds(_new_wx, _new_wy):
                _e.x = max(0, min(MAP_WIDTH  - 1, _e.x))
                _e.y = max(0, min(MAP_HEIGHT - 1, _e.y))
                continue

            _crossed.append((_e, _wx_off, _wy_off, _new_wx, _new_wy))
            _to_remove.add(id(_e))

        if not _crossed:
            return


        for _te, _wx_off, _wy_off, _new_wx, _new_wy in _crossed:
            # Mirror entry position to the opposite edge of the target chunk
            if _wx_off != 0 and _wy_off != 0:
                _ex = MAP_WIDTH  - 1 if _wx_off == -1 else 0
                _ey = MAP_HEIGHT - 1 if _wy_off == -1 else 0
            elif _wx_off != 0:
                _ex = MAP_WIDTH - 1 if _wx_off == -1 else 0
                _ey = max(0, min(MAP_HEIGHT - 1, _te.y))
            else:
                _ex = max(0, min(MAP_WIDTH  - 1, _te.x))
                _ey = MAP_HEIGHT - 1 if _wy_off == -1 else 0

            # Shell-search helper (shared by both branches)
            def _shell_place(target_map, occ):
                for _r in range(0, 12):
                    for _rdx in range(-_r, _r + 1):
                        for _rdy in range(-_r, _r + 1):
                            if _r > 0 and abs(_rdx) != _r and abs(_rdy) != _r:
                                continue
                            _nx, _ny = _ex + _rdx, _ey + _rdy
                            if (target_map.in_bounds(_nx, _ny)
                                    and target_map.walkable[_nx, _ny]
                                    and (_nx, _ny) not in occ):
                                occ.add((_nx, _ny))
                                return _nx, _ny
                return self._find_walkable_near(target_map, _ex, _ey, max_radius=50)

            if _new_wx == self.world_x and _new_wy == self.world_y:
                # Arriving in player's current chunk — defer arrival
                _entry_x, _entry_y = self._last_chunk_entry
                _cdef_cc = self.data.entities.get(creature_id(_te), {})
                _delay_cc = _cdef_cc.get("chunk_cross_delay", 6)
                _already_pending_cc = any(
                    id(p["entity"]) == id(_te)
                    for p in self._pending_pursuer_arrivals
                )
                if not _already_pending_cc:
                    self._pending_pursuer_arrivals.append({
                        "entity":  _te,
                        "entry_x": _entry_x,
                        "entry_y": _entry_y,
                        "delay":   _delay_cc,
                        "destination_wx": self.world_x,
                        "destination_wy": self.world_y,
                        "destination_submap_id": None,
                    })
                    if _DM_cc:
                        print(f"[LIVE-PENDING] {_te.name} delay={_delay_cc} "
                              f"entry=({_entry_x},{_entry_y}) "
                              f"(via entity-cross)")
            else:
                # Third chunk — cache the entity there; player will load it on entry
                _tgt_chunk = self.world_map.get(_new_wx, _new_wy)
                if _tgt_chunk is None:
                    continue
                prepared = self._prepare_destination(_new_wx, _new_wy)
                if prepared is None:
                    continue
                _t_map, _t_ents = prepared
                _occ2: set[tuple[int, int]] = {
                    (e.x, e.y) for e in _t_ents
                    if getattr(e, "blocks_movement", True)
                }
                _te.x, _te.y = _shell_place(_t_map, _occ2)
                # Guard: if last-known already points at a stair tile in the
                # player's current map, preserve it — entity is stair-following.
                _lkx_g = getattr(_te, "_last_known_px", None)
                _lky_g = getattr(_te, "_last_known_py", None)
                _lk_is_stair_g = False
                if _lkx_g is not None and _lky_g is not None:
                    _lkx_gi, _lky_gi = int(_lkx_g), int(_lky_g)
                    if self.local_map.in_bounds(_lkx_gi, _lky_gi):
                        _lk_t_g = self.local_map.tiles[_lkx_gi, _lky_gi]["terrain"]
                        if isinstance(_lk_t_g, bytes):
                            _lk_t_g = _lk_t_g.decode()
                        _lk_is_stair_g = str(_lk_t_g) in ("stairs_down", "stairs_up")
                if not _lk_is_stair_g:
                    # Update last-known to the boundary edge facing back toward player,
                    # so entity waits there (boundary suppression) rather than wandering
                    # to the old player-chunk-space coordinates inside the third chunk.
                    _blkx = MAP_WIDTH  - 1 if _wx_off == -1 else (0 if _wx_off == 1 else _te.x)
                    _blky = MAP_HEIGHT - 1 if _wy_off == -1 else (0 if _wy_off == 1 else _te.y)
                    _te._last_known_px = _blkx
                    _te._last_known_py = _blky
                    if _te.ai is not None:
                        _te.ai.target_x = _blkx
                        _te.ai.target_y = _blky
                from engine.effect_lifecycle import age_actor
                age_actor(self, _te)
                _t_ents.append(_te)
                self.save_manager.cache.store(_new_wx, _new_wy, _t_map, _t_ents)
                if _DM_cc:
                    print(f"[ENTITY-CROSS] {_te.name} -> third chunk "
                          f"({_new_wx},{_new_wy}) at ({_te.x},{_te.y})")

            self.entities = [e for e in self.entities if e is not _te]

    def _get_chunk_local_map(self, wx: int, wy: int):
        """Return the LocalMap for chunk (wx, wy) from cache, or None."""
        if (wx, wy, None) == (self.world_x, self.world_y, self.current_submap_id):
            return self.local_map
        cached = self.save_manager.cache.load(wx, wy)
        return cached.local_map if cached else None

    def _tick_live_pursuers(self) -> None:
        """Tick entities in self._live_pursuers each turn.

        Tuple format: (Actor, wx, wy, submap_id_or_None).
          submap_id=None → entity is in surface chunk (wx,wy).
          submap_id=str  → entity is in a submap; (wx,wy) is its surface chunk.

        Surface entities: offset virtual player across boundary; detect chunk
        crossings and stair descents.
        Submap entities: virtual player at stairs_up (last_known); detect stair
        ascent to transfer back to surface.
        """
        if not self._live_pursuers:
            return

        from components.ai import AIState as _AIState_lp
        from config import DEBUG_MODE as _DM_lp, MAP_WIDTH, MAP_HEIGHT

        _pursuing = (_AIState_lp.HUNTING, _AIState_lp.ALERTED, _AIState_lp.ATTACKING)
        _remaining: list = []
        _to_promote: list = []

        for (_entity, _wx, _wy, _sub_id) in self._live_pursuers:
            # --- Dead ---
            if not getattr(_entity, "is_alive", True):
                if _DM_lp:
                    print(f"[LIVE-DEAD] {_entity.name} removed from live pursuers")
                continue

            _eai = getattr(_entity, "ai", None)

            from engine.effect_lifecycle import age_actor

            # --- Timed-out or abandoned — return to cache ---
            if _eai is None or _eai.state not in _pursuing:
                prepared = self._prepare_destination(_wx, _wy, _sub_id)
                if prepared is None:
                    _remaining.append((_entity, _wx, _wy, _sub_id))
                    continue
                age_actor(self, _entity)
                if _DM_lp:
                    print(f"[LIVE-TIMEOUT] {_entity.name} abandoned pursuit")
                if (_wx, _wy, _sub_id) == (self.world_x, self.world_y, self.current_submap_id):
                    if _entity not in self.entities:
                        self.entities.append(_entity)
                else:
                    from engine.save_manager import SceneAddress
                    _ret_map, _ret_e = prepared
                    _ret_e.append(_entity)
                    SceneAddress(_wx, _wy, _sub_id).store(self.save_manager.cache, _ret_map, _ret_e)
                continue

            # --- Load map ---
            if _sub_id is None:
                _map = self._get_chunk_local_map(_wx, _wy)
            else:
                _map = self._get_submap_local_map(_sub_id)
            if _map is None:
                if _DM_lp:
                    _loc = f"submap:{_sub_id}" if _sub_id else f"chunk({_wx},{_wy})"
                    print(f"[LP-TICK] {_entity.name} — map NOT FOUND for {_loc}, deferring")
                _remaining.append((_entity, _wx, _wy, _sub_id))
                continue

            from engine.effect_lifecycle import disrupted, creature_id
            if disrupted(_entity, _map):
                _remaining.append((_entity, _wx, _wy, _sub_id))
                continue

            # --- Virtual player ---
            # Always out-of-bounds: keeps can_see_player False so entity stays
            # HUNTING/ALERTED.  Navigation is driven entirely by last_known, which
            # is set at extraction time (boundary edge for chunk crossing, stair
            # tile for stair following).  Calculated offsets are not needed and
            # actively harmful for CirclingAI state transitions.
            _virt_px = -999
            _virt_py = -999

            if _DM_lp:
                _loc2 = f"submap:{_sub_id}" if _sub_id else f"chunk({_wx},{_wy})"
                print(f"[LP-TICK] {_entity.name} at ({_entity.x},{_entity.y}) in {_loc2} "
                      f"virtual_player=({_virt_px},{_virt_py}) "
                      f"state={_eai.state.name} lkx={getattr(_entity,'_last_known_px',None)}")

            # Speed accumulator — same logic as ai_system.process()
            _lp_speed = self.data.entities.get(creature_id(_entity), {}).get("speed", 1.0)
            _eai.move_accumulator += _lp_speed

            # Move directly toward target (boundary edge or stair tile).
            # Bypass process_single entirely — entity is not seeing the player,
            # it just needs to walk to a known point.  _update_state() and the
            # full state machine are skipped; only the movement and timeout
            # counter matter during live pursuer ticks.
            _lp_steps = 0
            while _eai.move_accumulator >= 1.0 and _lp_steps < 2:
                _eai.move_accumulator -= 1.0
                _lp_steps += 1
                _lp_tx = getattr(_eai, "target_x", None)
                _lp_ty = getattr(_eai, "target_y", None)
                if _lp_tx is None:
                    _lp_tx = getattr(_entity, "_last_known_px", None)
                if _lp_ty is None:
                    _lp_ty = getattr(_entity, "_last_known_py", None)
                if _lp_tx is not None and _lp_ty is not None:
                    _lp_tx_c = max(0, min(MAP_WIDTH  - 1, int(_lp_tx)))
                    _lp_ty_c = max(0, min(MAP_HEIGHT - 1, int(_lp_ty)))
                    _eai._move_toward(
                        actor     = _entity,
                        local_map = _map,
                        entities  = [],
                        tx        = _lp_tx_c,
                        ty        = _lp_ty_c,
                    )

            # Timeout accounting (replaces _update_state() incrementing the counter).
            _eai.pursuit_turns_without_contact += 1
            _lp_cdef = self.data.entities.get(creature_id(_entity), {})
            _lp_timeout = _lp_cdef.get("pursuit_timeout", 20)
            if _eai.pursuit_turns_without_contact >= _lp_timeout:
                _eai.state = _AIState_lp.WANDERING  # triggers timeout/return-to-cache next tick

            if _DM_lp:
                print(f"[LP-POST] {_entity.name} now at ({_entity.x},{_entity.y}) "
                      f"state={_eai.state.name} lkx={getattr(_entity,'_last_known_px',None)}")

            # --- Stair detection ---
            _t_raw = _map.tiles[_entity.x, _entity.y]["terrain"]
            if isinstance(_t_raw, bytes):
                _t_raw = _t_raw.decode()
            _t_id_lp = str(_t_raw)

            if _sub_id is None and _t_id_lp == "stairs_down":
                if self._transfer_live_pursuer_through_stair(_entity, _wx, _wy, _map):
                    if _DM_lp:
                        print(f"[LIVE-STAIR-DOWN] {_entity.name} entered submap")
                    continue
            elif _sub_id is not None and _t_id_lp == "stairs_up":
                if self._transfer_submap_pursuer_to_surface(_entity, _wx, _wy, _sub_id):
                    if _DM_lp:
                        print(f"[LIVE-STAIR-UP] {_entity.name} returned to surface")
                    continue

            # --- Submap entities stay in submap; no chunk crossings ---
            if _sub_id is not None:
                _remaining.append((_entity, _wx, _wy, _sub_id))
                continue

            # --- Boundary crossing detection (surface entities only) ---
            _lkx = getattr(_entity, "_last_known_px", None)
            _lky = getattr(_entity, "_last_known_py", None)

            _cox, _coy = 0, 0
            if _lkx is not None:
                if _entity.x <= 0 and _lkx <= 1:
                    _cox = -1
                elif _entity.x >= MAP_WIDTH - 1 and _lkx >= MAP_WIDTH - 2:
                    _cox = 1
                if _entity.y <= 0 and _lky <= 1:
                    _coy = -1
                elif _entity.y >= MAP_HEIGHT - 1 and _lky >= MAP_HEIGHT - 2:
                    _coy = 1

            if _DM_lp:
                print(f"[LP-CROSS-CHECK] {_entity.name} pos=({_entity.x},{_entity.y}) "
                      f"lkx={_lkx} lky={_lky} cox={_cox} coy={_coy} "
                      f"MAP_W={MAP_WIDTH} MAP_H={MAP_HEIGHT}")

            if _cox == 0 and _coy == 0:
                _remaining.append((_entity, _wx, _wy, None))
                continue

            _new_wx = _wx + _cox
            _new_wy = _wy + _coy

            if not self.world_map.in_bounds(_new_wx, _new_wy):
                if _DM_lp:
                    print(f"[LP-CROSSING] {_entity.name} -> ({_new_wx},{_new_wy}) — OUT OF WORLD BOUNDS, clamped")
                _entity.x = max(0, min(MAP_WIDTH  - 1, _entity.x))
                _entity.y = max(0, min(MAP_HEIGHT - 1, _entity.y))
                _remaining.append((_entity, _wx, _wy, None))
                continue

            # Mirror entry to facing edge of target chunk
            if _cox != 0 and _coy != 0:
                _entry_x = MAP_WIDTH  - 1 if _cox == -1 else 0
                _entry_y = MAP_HEIGHT - 1 if _coy == -1 else 0
            elif _cox != 0:
                _entry_x = MAP_WIDTH  - 1 if _cox == -1 else 0
                _entry_y = max(0, min(MAP_HEIGHT - 1, _entity.y))
            else:
                _entry_x = max(0, min(MAP_WIDTH  - 1, _entity.x))
                _entry_y = MAP_HEIGHT - 1 if _coy == -1 else 0

            if self._prepare_destination(_new_wx, _new_wy) is None:
                _remaining.append((_entity, _wx, _wy, None))
                continue
            _entity.x = _entry_x
            _entity.y = _entry_y

            if _DM_lp:
                print(f"[LP-CROSSING] {_entity.name} crossed to ({_new_wx},{_new_wy}) "
                      f"player_chunk=({self.world_x},{self.world_y}) entry=({_entry_x},{_entry_y})")

            if _new_wx == self.world_x and _new_wy == self.world_y:
                _to_promote.append(_entity)
                if _DM_lp:
                    print(f"[LIVE-CROSS] {_entity.name} ({_wx},{_wy}) -> player chunk "
                          f"({self.world_x},{self.world_y}) entry ({_entry_x},{_entry_y})")
            else:
                # Update target toward the player's chunk from the new position.
                # Without this, the entity walks back to the edge it just crossed.
                _pdx = self.world_x - _new_wx
                _pdy = self.world_y - _new_wy
                if _pdx < 0:
                    _ntx, _nty = 0, _entity.y
                elif _pdx > 0:
                    _ntx, _nty = MAP_WIDTH - 1, _entity.y
                elif _pdy < 0:
                    _ntx, _nty = _entity.x, 0
                elif _pdy > 0:
                    _ntx, _nty = _entity.x, MAP_HEIGHT - 1
                else:
                    _ntx, _nty = _entity.x, _entity.y
                _entity._last_known_px = _ntx
                _entity._last_known_py = _nty
                _eai.target_x = _ntx
                _eai.target_y = _nty

                _remaining.append((_entity, _new_wx, _new_wy, None))
                if _DM_lp:
                    print(f"[LIVE-MOVE] {_entity.name} ({_wx},{_wy}) -> ({_new_wx},{_new_wy}) "
                          f"new_target=({_ntx},{_nty})")

        self._live_pursuers = _remaining

        # Defer promoted pursuers — they arrive after a delay, not immediately.
        _arrive_x, _arrive_y = self._last_chunk_entry
        for _pe in _to_promote:
            _cdef_pe = self.data.entities.get(creature_id(_pe), {})
            _delay = _cdef_pe.get("chunk_cross_delay", 6)
            # Skip if already pending
            _already_pending = any(
                id(p["entity"]) == id(_pe)
                for p in self._pending_pursuer_arrivals
            )
            if _already_pending:
                continue
            self._pending_pursuer_arrivals.append({
                "entity":  _pe,
                "entry_x": _arrive_x,
                "entry_y": _arrive_y,
                "delay":   _delay,
                "destination_wx": self.world_x,
                "destination_wy": self.world_y,
                "destination_submap_id": None,
            })
            if _DM_lp:
                print(f"[LIVE-PENDING] {_pe.name} delay={_delay} "
                      f"entry=({_arrive_x},{_arrive_y})")

    def _tick_pending_pursuer_arrivals(self) -> None:
        """Age arrivals and deliver only into their recorded destination scene.

        An expired arrival waits for that scene to become active. Travelling to
        another chunk or underground cannot transplant the queued actor there.
        """
        from config import DEBUG_MODE as _DM_pa
        _still_pending: list[dict] = []
        active_scene = (self.world_x, self.world_y, self.current_submap_id)
        for _pa in self._pending_pursuer_arrivals:
            entity = _pa["entity"]
            fighter = getattr(entity, "fighter", None)
            if not entity.is_alive or (fighter is not None and fighter.is_dead):
                continue
            # Older in-memory callers receive the same migration as old saves.
            _pa.setdefault("destination_wx", self.world_x)
            _pa.setdefault("destination_wy", self.world_y)
            _pa.setdefault("destination_submap_id", self.current_submap_id)
            destination = (_pa["destination_wx"], _pa["destination_wy"],
                           _pa["destination_submap_id"])
            _pa["delay"] = max(0, _pa["delay"] - 1)
            if _pa["delay"] > 0 or destination != active_scene:
                _still_pending.append(_pa)
                continue
            # Delay expired in the intended scene — materialise once.
            self._live_arrive(entity, _pa["entry_x"], _pa["entry_y"])
            if _DM_pa:
                _pe = _pa["entity"]
                print(f"[LIVE-ARRIVE-DEFERRED] {_pe.name} at ({_pe.x},{_pe.y}) "
                      f"player=({self.player.x},{self.player.y})")
        self._pending_pursuer_arrivals = _still_pending

    def _live_arrive(self, entity, entry_x: int, entry_y: int) -> None:
        """Place a pursuing entity into the player's current chunk at entry edge.

        Uses a border-constrained strip search: tiles within 3 of the crossing
        edge are tried first (lateral expansion, then inward), so the creature
        materialises at the map boundary, not near the player.
        """
        # Clean up from tracking lists — entity becomes a normal entity
        self._live_pursuers = [
            lp for lp in self._live_pursuers if id(lp[0]) != id(entity)
        ]
        _occ: set[tuple[int, int]] = {(self.player.x, self.player.y)}
        for _ne in self.entities:
            if getattr(_ne, "blocks_movement", True):
                _occ.add((_ne.x, _ne.y))

        # Determine crossing axis and constrained strip (max 3 tiles inward)
        _max_depth = 3
        if entry_y <= 0:
            _y_lo, _y_hi = 0, min(MAP_HEIGHT - 1, _max_depth)
            _x_lo, _x_hi = 0, MAP_WIDTH - 1
        elif entry_y >= MAP_HEIGHT - 1:
            _y_lo, _y_hi = max(0, MAP_HEIGHT - 1 - _max_depth), MAP_HEIGHT - 1
            _x_lo, _x_hi = 0, MAP_WIDTH - 1
        elif entry_x <= 0:
            _x_lo, _x_hi = 0, min(MAP_WIDTH - 1, _max_depth)
            _y_lo, _y_hi = 0, MAP_HEIGHT - 1
        elif entry_x >= MAP_WIDTH - 1:
            _x_lo, _x_hi = max(0, MAP_WIDTH - 1 - _max_depth), MAP_WIDTH - 1
            _y_lo, _y_hi = 0, MAP_HEIGHT - 1
        else:
            # Interior entry (shouldn't happen) — use full map
            _x_lo, _x_hi = 0, MAP_WIDTH - 1
            _y_lo, _y_hi = 0, MAP_HEIGHT - 1

        # Search within constrained strip: expand laterally from entry, then inward
        _placed = False
        for _r in range(0, max(MAP_WIDTH, MAP_HEIGHT)):
            if _placed:
                break
            for _rdx in range(-_r, _r + 1):
                for _rdy in range(-_r, _r + 1):
                    if _r > 0 and abs(_rdx) != _r and abs(_rdy) != _r:
                        continue
                    _nx = entry_x + _rdx
                    _ny = entry_y + _rdy
                    if not (_x_lo <= _nx <= _x_hi and _y_lo <= _ny <= _y_hi):
                        continue
                    if (self.local_map.in_bounds(_nx, _ny)
                            and self.local_map.walkable[_nx, _ny]
                            and (_nx, _ny) not in _occ):
                        entity.x, entity.y = _nx, _ny
                        _occ.add((_nx, _ny))
                        _placed = True
                        break
                if _placed:
                    break
        if not _placed:
            entity.x, entity.y = self._find_walkable_near(
                self.local_map, entry_x, entry_y, max_radius=50
            )
        # Nudge one step inward from boundary to prevent immediate re-crossing
        if entity.x <= 0:
            entity.x = 1
        elif entity.x >= MAP_WIDTH - 1:
            entity.x = MAP_WIDTH - 2
        if entity.y <= 0:
            entity.y = 1
        elif entity.y >= MAP_HEIGHT - 1:
            entity.y = MAP_HEIGHT - 2
        entity._just_arrived     = True
        entity._arrival_cooldown = 3
        entity._last_known_px = self.player.x
        entity._last_known_py = self.player.y
        entity.last_known_x   = None
        entity.last_known_y   = None
        if entity.ai is not None:
            entity.ai.target_x = self.player.x
            entity.ai.target_y = self.player.y
        self.entities.append(entity)

    def _get_submap_local_map(self, submap_id: str):
        """Return the LocalMap for a cached submap, or None."""
        if self.current_submap_id == submap_id:
            return self.local_map
        cached = self.save_manager.cache.load_submap(submap_id)
        return cached.local_map if cached else None

    def _transfer_live_pursuer_through_stair(self, entity, wx: int, wy: int, surface_map) -> bool:
        """Transfer a surface live pursuer through stairs_down into its linked submap.

        Returns True if the transfer was handled (entity removed from live pursuers).
        """
        from config import DEBUG_MODE as _DM_st2
        _linked_id = surface_map.submap_links.get((entity.x, entity.y))
        if _linked_id is None:
            return False  # stair tile with no linked submap

        prepared = self._prepare_destination(wx, wy, _linked_id)
        if prepared is None:
            return False
        _sub_map, _sub_ents = prepared

        # Find entry point
        _chunk_wm2 = self.world_map.get(wx, wy)
        _smeta2 = None
        if _chunk_wm2:
            _smeta2 = next((s for s in _chunk_wm2.submaps if s.submap_id == _linked_id), None)
        _ex = _smeta2.entry_x if _smeta2 else _sub_map.width  // 2
        _ey = _smeta2.entry_y if _smeta2 else _sub_map.height // 2

        # Shell-search for placement
        _occ_st: set[tuple[int, int]] = set()
        for _se2 in _sub_ents:
            if getattr(_se2, "blocks_movement", True):
                _occ_st.add((_se2.x, _se2.y))
        _placed_st = False
        for _r_st in range(0, 12):
            for _dx_st in range(-_r_st, _r_st + 1):
                for _dy_st in range(-_r_st, _r_st + 1):
                    if _r_st > 0 and abs(_dx_st) != _r_st and abs(_dy_st) != _r_st:
                        continue
                    _nx_st, _ny_st = _ex + _dx_st, _ey + _dy_st
                    if (_sub_map.in_bounds(_nx_st, _ny_st)
                            and _sub_map.walkable[_nx_st, _ny_st]
                            and (_nx_st, _ny_st) not in _occ_st):
                        entity.x, entity.y = _nx_st, _ny_st
                        _placed_st = True
                        break
                if _placed_st:
                    break
            if _placed_st:
                break
        if not _placed_st:
            entity.x, entity.y = self._find_walkable_near(_sub_map, _ex, _ey, max_radius=50)

        if _linked_id == self.current_submap_id:
            # Player is in this submap — add entity to active scene
            entity._last_known_px = self.player.x
            entity._last_known_py = self.player.y
            if entity.ai is not None:
                entity.ai.target_x = self.player.x
                entity.ai.target_y = self.player.y
            self.entities.append(entity)
            if _DM_st2:
                print(f"[LIVE-STAIR-DOWN-ARRIVE] {entity.name} -> submap {_linked_id} "
                      f"at ({entity.x},{entity.y}) [player present]")
        else:
            # Player not in this submap — cache entity into it
            from engine.effect_lifecycle import age_actor
            age_actor(self, entity)
            _sub_ents.append(entity)
            self.save_manager.cache.store_submap(_linked_id, _sub_map, _sub_ents)
            if _DM_st2:
                print(f"[LIVE-STAIR-DOWN-CACHE] {entity.name} cached into submap {_linked_id} "
                      f"at ({entity.x},{entity.y})")
        return True

    def _transfer_submap_pursuer_to_surface(self, entity, wx: int, wy: int, submap_id: str) -> bool:
        """Transfer a submap live pursuer through stairs_up back to the surface.

        Returns True if the transfer was handled (entity removed from live pursuers).
        """
        from config import DEBUG_MODE as _DM_su
        # Surface exit coords were stamped on entity at extraction time
        _exit_x  = getattr(entity, "_surface_exit_x",  None)
        _exit_y  = getattr(entity, "_surface_exit_y",  None)
        _exit_wx = getattr(entity, "_surface_exit_wx", None)
        _exit_wy = getattr(entity, "_surface_exit_wy", None)
        if _exit_wx is None:
            _exit_wx, _exit_wy = wx, wy
        if _exit_x is None:
            _exit_x = self.surface_return_x if hasattr(self, "surface_return_x") else 0
            _exit_y = self.surface_return_y if hasattr(self, "surface_return_y") else 0

        if (self.current_submap_id is None
                and _exit_wx == self.world_x
                and _exit_wy == self.world_y):
            # Player is on this surface chunk — add directly to active scene
            _occ_su: set[tuple[int, int]] = {(self.player.x, self.player.y)}
            for _se_su in self.entities:
                if getattr(_se_su, "blocks_movement", True):
                    _occ_su.add((_se_su.x, _se_su.y))
            _placed_su = False
            for _r_su in range(0, 12):
                for _dx_su in range(-_r_su, _r_su + 1):
                    for _dy_su in range(-_r_su, _r_su + 1):
                        if _r_su > 0 and abs(_dx_su) != _r_su and abs(_dy_su) != _r_su:
                            continue
                        _nx_su, _ny_su = _exit_x + _dx_su, _exit_y + _dy_su
                        if (self.local_map.in_bounds(_nx_su, _ny_su)
                                and self.local_map.walkable[_nx_su, _ny_su]
                                and (_nx_su, _ny_su) not in _occ_su):
                            entity.x, entity.y = _nx_su, _ny_su
                            _placed_su = True
                            break
                    if _placed_su:
                        break
                if _placed_su:
                    break
            if not _placed_su:
                entity.x, entity.y = self._find_walkable_near(
                    self.local_map, _exit_x, _exit_y, max_radius=50
                )
            entity._last_known_px = self.player.x
            entity._last_known_py = self.player.y
            if entity.ai is not None:
                entity.ai.target_x = self.player.x
                entity.ai.target_y = self.player.y
            self.entities.append(entity)
            if _DM_su:
                print(f"[LIVE-STAIR-UP-ARRIVE] {entity.name} -> surface "
                      f"({_exit_wx},{_exit_wy}) at ({entity.x},{entity.y}) [player present]")
        else:
            # Player not on this surface chunk — cache entity there
            prepared = self._prepare_destination(_exit_wx, _exit_wy)
            if prepared is None:
                return False
            _surf_map, _surf_ents = prepared
            entity.x, entity.y = self._find_walkable_near(
                _surf_map, _exit_x, _exit_y, max_radius=50
            )
            from engine.effect_lifecycle import age_actor
            age_actor(self, entity)
            _surf_ents.append(entity)
            self.save_manager.cache.store(_exit_wx, _exit_wy, _surf_map, _surf_ents)
            if _DM_su:
                print(f"[LIVE-STAIR-UP-CACHE] {entity.name} cached onto surface "
                      f"({_exit_wx},{_exit_wy}) at ({entity.x},{entity.y})")
        return True

    def _process_creature_stair_transfers(self) -> None:
        """Process stair-use flags set by AI when a creature reached a stair tile.

        Handles two cases:
          stairs_down: creature on surface wants to descend; player must be
                       underground in the linked submap.
          stairs_up:   creature in submap wants to ascend; player must be on
                       the surface (no current_submap_id).
        """
        from config import DEBUG_MODE as _DM_st

        for _e in list(self.entities):
            if _e is self.player:
                continue
            _psu = getattr(_e, "_pending_stair_use", None)
            if not _psu:
                continue
            _e._pending_stair_use = None

            if _psu == "stairs_down":
                # Surface-to-submap creature stair use requires surface entities
                # to get AI ticks while the player is underground — deferred to
                # full reality bubble implementation.
                pass

            elif _psu == "stairs_up":
                # Creature is in submap (self.entities), player has ascended
                # (current_submap_id is None). Transfer creature to surface.
                if self.current_submap_id:
                    continue  # player still underground
                # Remove from current entities list
                self.entities = [_x for _x in self.entities if _x is not _e]
                # Load surface cache and place creature near surface return pos
                _cached_surf = self.save_manager.cache.load(self.world_x, self.world_y)
                if _cached_surf is None:
                    continue
                _surf_ents = _deserialize_entities_inline(_cached_surf.entities, self)
                _occ_s2: set[tuple[int, int]] = {(self.player.x, self.player.y)}
                for _se in _surf_ents:
                    if getattr(_se, "blocks_movement", True):
                        _occ_s2.add((_se.x, _se.y))
                _ex_s2, _ey_s2 = self.surface_return_x, self.surface_return_y
                _placed_s2 = False
                for _pr_s2 in range(0, 12):
                    for _pdx_s2 in range(-_pr_s2, _pr_s2 + 1):
                        for _pdy_s2 in range(-_pr_s2, _pr_s2 + 1):
                            if _pr_s2 > 0 and abs(_pdx_s2) != _pr_s2 and abs(_pdy_s2) != _pr_s2:
                                continue
                            _nx_s2 = _ex_s2 + _pdx_s2
                            _ny_s2 = _ey_s2 + _pdy_s2
                            if (_cached_surf.local_map.in_bounds(_nx_s2, _ny_s2)
                                    and _cached_surf.local_map.walkable[_nx_s2, _ny_s2]
                                    and (_nx_s2, _ny_s2) not in _occ_s2):
                                _e.x, _e.y = _nx_s2, _ny_s2
                                _placed_s2 = True
                                break
                        if _placed_s2:
                            break
                    if _placed_s2:
                        break
                if not _placed_s2:
                    _e.x, _e.y = self._find_walkable_near(
                        _cached_surf.local_map, _ex_s2, _ey_s2, max_radius=50
                    )
                if hasattr(_e, "ai"):
                    _e.ai._last_known_px = self.player.x
                    _e.ai._last_known_py = self.player.y
                    _e.ai.target_x = self.player.x
                    _e.ai.target_y = self.player.y
                _e._last_known_px = self.player.x
                _e._last_known_py = self.player.y
                _surf_ents.append(_e)
                self.save_manager.cache.store(
                    self.world_x, self.world_y,
                    _cached_surf.local_map, _surf_ents,
                )
                if _DM_st:
                    print(f"[TRANSFER-STAIR-UP-DELAYED] {_e.name} -> surface ({_e.x},{_e.y})")

    def _spawn_layout_entities(self, layout_entities: list, local_map=None) -> list:
        from engine.scene_generation import populate
        return populate(self.data, self.item_factory, self.creature_factory,
                        local_map if local_map is not None else self.local_map, layout_entities)

    # ------------------------------------------------------------------ #
    #  Terrain step helpers
    # ------------------------------------------------------------------ #

    def _resolve_terrain_id(self, x: int, y: int) -> str:
        """Get the terrain id at (x,y), decoded if bytes."""
        t = self.local_map.tiles[x, y]["terrain"]
        if isinstance(t, bytes):
            t = t.decode()
        return str(t)

    def _try_drink_terrain(self) -> bool:
        """Drink from drinkable terrain at player's position (W key). Drink only — flask fill uses E key."""
        terrain_id    = self._resolve_terrain_id(self.player.x, self.player.y)
        terrain_entry = self.data.terrain.get(terrain_id, {})

        if not terrain_entry.get("drinkable", False):
            return False

        if self.current_submap_id is not None:
            self.log.add(
                "The water here has a wrong quality. You do not drink.",
                STONE_BLUE,
            )
            return True

        needs = getattr(self.player, "needs", None)
        if not needs:
            return False

        raw      = terrain_entry.get("drink_hydration", 400)
        survival = self.data.survival or {}
        t_max    = survival.get("thirst", {}).get("max", 800)
        needs.drink(raw / t_max)
        self.log.add("The water is cold. Grit between the teeth.", CLEAR_WATER)
        return True

    def _tick_rain_collection(self) -> None:
        """Accumulate rain toward filling an empty_water_skin while waiting outdoors."""
        if self.current_submap_id is not None:
            self.rain_collection_progress = 0
            return
        weather = getattr(self, "weather", None)
        if not weather:
            self.rain_collection_progress = 0
            return
        state = weather.state
        if state == "heavy_rain":
            threshold = 4
        elif state == "light_rain":
            threshold = 8
        else:
            self.rain_collection_progress = 0
            return
        # Check for empty_water_skin
        inv = getattr(self.player, "inventory", None)
        if not inv:
            self.rain_collection_progress = 0
            return
        has_empty = any(getattr(it, "item_id", "") == "empty_water_skin" for it in inv.items)
        if not has_empty:
            self.rain_collection_progress = 0
            return
        self.rain_collection_progress += 1
        if self.rain_collection_progress >= threshold:
            # Fill the water skin
            for it in inv.items:
                if getattr(it, "item_id", "") == "empty_water_skin":
                    full = self.item_factory.create("water_skin")
                    from engine.item_transfers import exchange
                    if full is None or not exchange(self, [it], [full]):
                        self.rain_collection_progress = 0
                        return
                    _item_name = full.name if full else "water skin"
                    self.log.add(f"Rain fills the {_item_name}.", MSG_DEFAULT)
                    self.callouts.add("FILLED", float(self.player.x),
                                      float(self.player.y) - 0.3,
                                      RESONANCE_LOW, lifetime=1.0, font_size="status")
                    self.rain_collection_progress = 0
                    return

    def _try_harvest(self, x: int | None = None, y: int | None = None) -> bool:
        """Harvest a plant at (x, y), defaulting to player position. Returns True if a turn was spent."""
        from config import DEBUG_MODE as _DM
        hx = x if x is not None else self.player.x
        hy = y if y is not None else self.player.y

        terrain_id    = self._resolve_terrain_id(hx, hy)
        terrain_entry = self.data.terrain.get(terrain_id, {})

        # Check decor layer for harvestable plants
        _decor_id = self.local_map.decor.get((hx, hy))
        _decor_entry = self.data.decoratives.get(_decor_id, {}) if _decor_id else {}
        _harvest_from_decor = _decor_entry.get("harvestable", False)

        if _DM:
            print(f"[harvest] tile=({hx},{hy}) terrain={terrain_id} "
                  f"harvestable={terrain_entry.get('harvestable', False)} "
                  f"decor={_decor_id} decor_harvestable={_harvest_from_decor}")

        if _harvest_from_decor:
            harvest_item_id = _decor_entry.get("harvest_item", "")
            depleted_id     = _decor_entry.get("depleted_id", "")
            display_name    = _decor_entry.get("description", "plant").split(".")[0].lower()
        elif terrain_entry.get("harvestable", False):
            harvest_item_id = terrain_entry.get("harvest_item", "")
            depleted_id     = terrain_entry.get("depleted_tile", terrain_id)
            display_name    = terrain_entry.get("display_name", "plant").lower()
        else:
            return False

        if not harvest_item_id:
            return False

        item = self.item_factory.create(harvest_item_id, hx, hy)
        if item is None:
            return False

        inv = getattr(self.player, "inventory", None)
        if inv is None:
            return False

        if not inv.add(item):
            self.log.add("No room.", MSG_DEFAULT)
            return False
        self.log.add(f"You take a cutting of {display_name}.", MSG_DEFAULT)

        # deep_harvest perk: 30% chance to NOT deplete the tile
        _perks_dh = getattr(self.player, "perks", None)
        _skip_deplete = (_perks_dh and _perks_dh.has("deep_harvest")
                         and self.rng.random() < 0.30)
        if not _skip_deplete:
            if _harvest_from_decor:
                from generation.decor_utils import place_decor, clear_decor
                clear_decor(self.local_map, hx, hy)
                if depleted_id:
                    place_decor(self.local_map, hx, hy, depleted_id)
            else:
                dep_entry = self.data.terrain.get(depleted_id, {})
                self.local_map.set_tile(
                    hx, hy, depleted_id,
                    dep_entry.get("walkable", True),
                    dep_entry.get("transparent", True),
                )
        return True

    def _try_gather(self, x: int, y: int) -> bool:
        """
        Attempt to gather a material from terrain at (x, y).
        gather_chance roll decides success/fail.
        If gather_depletes is true, tile changes to depleted_tile on success.
        Returns True if a turn was spent.
        """
        terrain_id    = self._resolve_terrain_id(x, y)
        terrain_entry = self.data.terrain.get(terrain_id, {})
        if not terrain_entry.get("gatherable", False):
            return False

        gather_item_id = terrain_entry.get("gather_item", "")
        if not gather_item_id:
            return False

        inv = getattr(self.player, "inventory", None)
        if inv is None:
            return False

        chance = terrain_entry.get("gather_chance", 0.5)
        if self.rng.random() >= chance:
            dname = terrain_entry.get("display_name", "there")
            self.log.add(f"Nothing useful from the {dname.lower()}.", MSG_DEFAULT)
            return True  # turn spent on the attempt

        item = self.item_factory.create(gather_item_id, x, y)
        if item is None:
            return False

        if not inv.add(item):
            self.log.add("No room.", MSG_DEFAULT)
            return True

        dname = terrain_entry.get("display_name", "terrain")
        self.log.add(f"You take {item.name} from the {dname.lower()}.", MSG_DEFAULT)

        if terrain_entry.get("gather_depletes", False):
            dep_id    = terrain_entry.get("depleted_tile", terrain_id)
            dep_entry = self.data.terrain.get(dep_id, {})
            self.local_map.set_tile(
                x, y, dep_id,
                dep_entry.get("walkable", True),
                dep_entry.get("transparent", True),
            )

        return True

    def _get_interaction_candidates(self) -> list[tuple[int, int]]:
        """
        Return all tiles (including the player's own) with harvestable terrain,
        gatherable terrain, an interactable, or floor items.
        Scan order: self, then N/NE/E/SE/S/SW/W/NW.
        """
        _OFFSETS = [(0, 0),
                    (0, -1), (1, -1), (1, 0), (1, 1),
                    (0, 1), (-1, 1), (-1, 0), (-1, -1)]
        candidates: list[tuple[int, int]] = []
        for dx, dy in _OFFSETS:
            ax, ay = self.player.x + dx, self.player.y + dy
            if not self.local_map.in_bounds(ax, ay):
                continue
            terrain_id    = self._resolve_terrain_id(ax, ay)
            terrain_entry = self.data.terrain.get(terrain_id, {})
            decor_id      = self.local_map.decor.get((ax, ay))
            decor_entry   = self.data.decoratives.get(decor_id, {}) if decor_id else {}
            # Floor objects take priority as interaction candidates
            if self._items_at(ax, ay):
                candidates.append((ax, ay))
                continue
            # Processing layer tiles are candidates (shows "not ready" on interact)
            if (ax, ay) in self.local_map.processing_layer:
                candidates.append((ax, ay))
                continue
            if (terrain_entry.get("harvestable", False)
                    or terrain_entry.get("gatherable", False)
                    or terrain_entry.get("interactable")
                    or decor_entry.get("interactable")
                    or decor_entry.get("harvestable", False)):
                candidates.append((ax, ay))
                continue
        return candidates

    # ------------------------------------------------------------------ #
    #  Interactable tile handlers
    # ------------------------------------------------------------------ #

    def _dispatch_interactable(self, x: int, y: int) -> bool:
        """Call the named handler for the interactable at (x, y). Checks decor first, then terrain."""
        # Decor layer — campfires and other placed objects live here
        decor_id = self.local_map.decor.get((x, y))
        if decor_id:
            decor_entry  = self.data.decoratives.get(decor_id, {})
            handler_name = decor_entry.get("interactable", "")
            if handler_name:
                handler = getattr(self, f"_interactable_{handler_name}", None)
                if handler:
                    return handler(x, y)
        # Terrain layer
        terrain_id    = self._resolve_terrain_id(x, y)
        terrain_entry = self.data.terrain.get(terrain_id, {})
        handler_name  = terrain_entry.get("interactable", "")
        if not handler_name:
            return False
        handler = getattr(self, f"_interactable_{handler_name}", None)
        if handler is None:
            return False
        return handler(x, y)

    def _interactable_butcher(self, x: int, y: int, corpse=None, *, scene=None, address=None) -> bool:
        from engine.harvesting import butcher
        return butcher(self, x, y, corpse, scene=scene, address=address)

    def _interactable_light_campfire(self, x: int, y: int) -> bool:
        from generation.decor_utils import place_decor
        place_decor(self.local_map, x, y, "campfire_lit")
        self.log.add("The fire takes.", MSG_DEFAULT)
        return True

    def _interactable_extinguish_campfire(self, x: int, y: int) -> bool:
        from generation.decor_utils import place_decor
        place_decor(self.local_map, x, y, "campfire_unlit")
        self.log.add("The fire dies.", MSG_DEFAULT)
        return True

    # ── Container messages — one dict, one place ─────────────────
    _CONTAINER_OPEN_MSG: dict[str, str] = {
        "barrel": "The barrel opens with a dull report. The smell of old wood and whatever was sealed within.",
        "crate":  "The lid comes free. The crate yields its contents to examination.",
        "sack":   "The knot gives. The sack falls open.",
        "coffer": "The coffer opens. Someone closed this carefully, once.",
    }
    _CONTAINER_LOOTED_MSG: dict[str, str] = {
        "barrel": "The barrel is empty. It has been so for some time.",
        "crate":  "The crate holds nothing. The lid was already off.",
        "sack":   "The sack is empty. Already searched.",
        "coffer": "The coffer is bare. Whatever it kept is gone.",
    }

    def _interactable_container(self, x: int, y: int) -> bool:
        """Single-step container interaction: open + browse in one action."""
        from generation.floor_object_utils import open_container, get_container_items
        entry = self.local_map.container_state.get((x, y))
        if not entry:
            return False
        decor_id = entry.get("decor_id", "")
        state = entry["state"]

        if state == "looted" or not entry["items"]:
            msg = self._CONTAINER_LOOTED_MSG.get(decor_id, "Nothing within.")
            self.log.add(msg, MSG_DEFAULT)
            return False  # no turn

        if state == "closed":
            open_container(self.local_map, x, y)
            msg = self._CONTAINER_OPEN_MSG.get(decor_id, "It opens.")
            self.log.add(msg, MSG_DEFAULT)

        # Now open — show browse prompt
        items = get_container_items(self.local_map, x, y, self.item_factory)
        if not items:
            entry["state"] = "looted"
            msg = self._CONTAINER_LOOTED_MSG.get(decor_id, "Nothing within.")
            self.log.add(msg, MSG_DEFAULT)
            return False

        self.interaction_cursor._selection_prompt = {
            "items": items,
            "selected": 0,
            "lx": x, "ly": y,
            "source": "container",
        }
        return False  # prompt takes over — no turn yet

    # ------------------------------------------------------------------ #
    #  Deep tongue learning interactables
    # ------------------------------------------------------------------ #

    def _maybe_show_lexicon_hint(self) -> None:
        """Fire the lexicon hint exactly once on first word learned."""
        lang = getattr(self.player, "language", None)
        if lang is None:
            return
        if lang.shown_lexicon_hint:
            return
        if len(lang.known_deep_words) >= 1:
            lang.shown_lexicon_hint = True
            self.log.add("Press [L] to open the Lexicon.", UI_TEXT_DIM)

    # Biome-weighted category lists for waystone learning
    _WAYSTONE_CATEGORIES = {
        "forest":        ["place", "body", "action"],
        "heath":         ["time", "essence", "cosmic"],
        "swamp":         ["body", "time", "cosmic"],
        "mountain":      ["place", "cosmic", "number"],
        "plains":        ["action", "people", "time"],
        "drowned_wood":  ["body", "time", "cosmic"],
        "ash_wastes":    ["essence", "cosmic", "number"],
        "town":          ["people", "action", "place"],
        "capital":       ["people", "action", "cosmic"],
        "deep_mountain": ["cosmic", "essence", "number"],
    }
    _WAYSTONE_DEFAULT = ["action", "cosmic", "place"]

    _WAYSTONE_FALLBACK_IDS = ["waystone_fallback_a", "waystone_fallback_b"]

    def _interactable_drink_source(self, x: int, y: int) -> bool:
        """Fill empty_water_skin from drinkable terrain, or drink directly."""
        terrain_id = self._resolve_terrain_id(x, y)
        terrain_entry = self.data.terrain.get(terrain_id, {})
        if not terrain_entry.get("drinkable", False):
            return False

        inv = getattr(self.player, "inventory", None)
        if inv:
            for it in inv.items:
                if getattr(it, "item_id", "") == "empty_water_skin":
                    full = self.item_factory.create("water_skin")
                    from engine.item_transfers import exchange
                    if full is None or not exchange(self, [it], [full]):
                        self.log.add("No room for the filled skin.", MSG_DEFAULT)
                        return False
                    item_name = full.name if full else "water skin"
                    self.log.add(
                        f"Thou fillest the {item_name} at the shallows.",
                        MSG_DEFAULT,
                    )
                    return True

        # No flask — drink directly
        needs = getattr(self.player, "needs", None)
        if needs:
            raw = terrain_entry.get("drink_hydration", 400)
            survival = self.data.survival or {}
            t_max = survival.get("thirst", {}).get("max", 800)
            needs.drink(raw / t_max)
            self.log.add("The water is cold. Grit between the teeth.", CLEAR_WATER)
            return True
        return False

    def _interactable_vine(self, x: int, y: int) -> bool:
        """Cut a vine tile with an equipped cutting weapon."""
        decor_id = self.local_map.decor.get((x, y))
        if not decor_id or not decor_id.startswith("vine_"):
            return False

        # Check cutting weapon
        equip = getattr(self.player, "equipment", None)
        weapon = equip.slots.get("weapon") if equip else None
        cutting_tier = 0
        if weapon:
            for kw in getattr(weapon, "keywords", []):
                if isinstance(kw, dict) and kw.get("tag") == "cutting":
                    cutting_tier = kw.get("tier", 1)
                elif isinstance(kw, str) and kw == "cutting":
                    cutting_tier = 1

        # Eyestalk requires cutting tier >= 2
        min_tier = 2 if decor_id == "vine_eyestalk" else 1
        if cutting_tier < min_tier:
            if cutting_tier == 0:
                self.log.add("It resists. You need something sharp.", WORN_STONE)
            else:
                self.log.add("The growth is too thick. A sharper blade is needed.", WORN_STONE)
            return False

        from engine.vine_system import destroy_vine_tile
        destroy_vine_tile(self, x, y)
        self.log.add("The vine tears.", MSG_DEFAULT)
        return True  # turn spent

    def _interactable_examine_waystone(self, x: int, y: int) -> bool:
        """Examine a waystone — teach word on first visit, always open inscription."""
        if not hasattr(self.local_map, "interacted_waystones"):
            self.local_map.interacted_waystones = set()
        if not hasattr(self.local_map, "waystone_inscriptions"):
            self.local_map.waystone_inscriptions = {}

        first_time = (x, y) not in self.local_map.interacted_waystones

        # Teach one word on first examine only
        if first_time:
            lang = getattr(self.player, "language", None)
            if lang is not None:
                from engine.language_system import learn_from_category
                chunk = self.world_map.get(self.world_x, self.world_y) if self.world_map else None
                biome_id = getattr(chunk, "biome_id", "forest") if chunk else "forest"
                cat_list = self._WAYSTONE_CATEGORIES.get(biome_id, self._WAYSTONE_DEFAULT)
                cat = self.rng.choice(cat_list)
                ok, wid = learn_from_category(cat, 1, "waystone", lang,
                                               self.data.deep_tongue, self.rng)
                if ok:
                    wdef = self.data.deep_tongue.get(wid, {})
                    deep = wdef.get("deep", wid)
                    common = wdef.get("common", "")
                    lang.translation_events[wid] = self.world_time.turn
                    self.log.add(
                        f"Something stirs in the bone. A word surfaces — [{deep}]: {common}.",
                        DEEP_TONGUE_COLOUR,
                    )
                    self._maybe_show_lexicon_hint()
            self.local_map.interacted_waystones.add((x, y))

        # Select or retrieve inscription for this waystone
        if (x, y) not in self.local_map.waystone_inscriptions:
            chunk = self.world_map.get(self.world_x, self.world_y) if self.world_map else None
            biome_id = getattr(chunk, "biome_id", "forest") if chunk else "forest"
            biome_def = self.data.biomes.get(biome_id, {})
            ins_ids = biome_def.get("waystone_inscriptions", [])
            if not ins_ids:
                ins_ids = self._WAYSTONE_FALLBACK_IDS
            self.local_map.waystone_inscriptions[(x, y)] = self.rng.choice(ins_ids)

        ins_id = self.local_map.waystone_inscriptions[(x, y)]
        text_def = self.data.texts.get(ins_id)
        if text_def:
            self.text_reader.open_text(
                text_def,
                panel_style="ziggurat",
                text_align="center",
                line_spacing_bonus=6,
                panel_size="inscription",
            )

        return first_time

    def _interactable_examine_stele(self, x: int, y: int) -> bool:
        """Examine a stele — teach words on first examine, always open inscription."""
        if not hasattr(self.local_map, "examined_steles"):
            self.local_map.examined_steles = set()

        # Find and load the inscription text
        text_id = self._find_stele_text_id(x, y)
        if not text_id:
            self.log.add("The marks are too worn to read.", WORN_STONE)
            return False
        text_def = self.data.texts.get(text_id, {})
        if not text_def:
            self.log.add("The marks are too worn to read.", WORN_STONE)
            return False

        # Teach words on first examine only
        lang = getattr(self.player, "language", None)
        first_time = (x, y) not in self.local_map.examined_steles
        if first_time and lang is not None:
            if text_id not in lang.taught_texts:
                from engine.language_system import learn_from_text
                learned = learn_from_text(text_def, lang, self.data.deep_tongue, self.rng)
                lang.taught_texts.add(text_id)
                for wid in learned:
                    wdef = self.data.deep_tongue.get(wid, {})
                    deep = wdef.get("deep", wid)
                    common = wdef.get("common", "")
                    lang.translation_events[wid] = self.world_time.turn
                    self.log.add(
                        f"Something stirs in the bone. A word surfaces — [{deep}]: {common}.",
                        DEEP_TONGUE_COLOUR,
                    )
                    self._maybe_show_lexicon_hint()
            self.local_map.examined_steles.add((x, y))

        # Always open the inscription for reading
        self.text_reader.open_text(
            text_def,
            panel_style="ziggurat",
            text_align="center",
            line_spacing_bonus=6,
            panel_size="inscription",
        )
        return first_time

    def _find_stele_text_id(self, x: int, y: int) -> str:
        """Look up the text_id for a stele special_tile at (x, y)."""
        return self.local_map.stele_text_ids.get((x, y), "")

    # ------------------------------------------------------------------ #
    #  Bell interaction
    # ------------------------------------------------------------------ #

    _BELL_INSCRIPTION_IDS = [
        "bell_inscription_a", "bell_inscription_b", "bell_inscription_c",
        "bell_inscription_d", "bell_inscription_e", "bell_inscription_f",
    ]

    def _interactable_examine_bell(self, x: int, y: int) -> bool:
        """Examine a bell — resonance pulse, teach word, show inscription."""
        if not hasattr(self.local_map, "bell_inscriptions"):
            self.local_map.bell_inscriptions = {}
        if not hasattr(self.local_map, "examined_bells"):
            self.local_map.examined_bells = set()

        # Resonance pulse — every examination (reduced rate)
        self.resonance_exposure = min(1.0, self.resonance_exposure + 0.02)
        self.log.add("The metal hums against your hand.", RESONANCE_MID)

        # Select or retrieve inscription for this bell
        if (x, y) not in self.local_map.bell_inscriptions:
            self.local_map.bell_inscriptions[(x, y)] = self.rng.choice(
                self._BELL_INSCRIPTION_IDS)

        ins_id = self.local_map.bell_inscriptions[(x, y)]
        text_def = self.data.texts.get(ins_id)

        # Teach word on first examine only
        first_time = (x, y) not in self.local_map.examined_bells
        if first_time:
            if text_def and text_def.get("teach_words"):
                lang = getattr(self.player, "language", None)
                if lang and ins_id not in lang.taught_texts:
                    from engine.language_system import learn_from_text
                    learned = learn_from_text(
                        text_def, lang, self.data.deep_tongue, self.rng)
                    lang.taught_texts.add(ins_id)
                    for wid in learned:
                        wdef = self.data.deep_tongue.get(wid, {})
                        deep = wdef.get("deep", wid)
                        common = wdef.get("common", "")
                        lang.translation_events[wid] = self.world_time.turn
                        self.log.add(
                            f"Something stirs. A word surfaces — [{deep}]: {common}.",
                            DEEP_TONGUE_COLOUR,
                        )
                        self._maybe_show_lexicon_hint()
            self.local_map.examined_bells.add((x, y))

        # Open inscription
        if text_def:
            self.text_reader.open_text(
                text_def,
                panel_style="ziggurat",
                text_align="center",
                line_spacing_bonus=6,
                panel_size="inscription",
            )

        return True  # Every touch changes resonance, including rereads.

    def _interactable_examine_dead_bell(self, x: int, y: int) -> bool:
        """Examine a dead bell — inscription and word, but no resonance pulse."""
        if not hasattr(self.local_map, "bell_inscriptions"):
            self.local_map.bell_inscriptions = {}
        if not hasattr(self.local_map, "examined_bells"):
            self.local_map.examined_bells = set()

        # No resonance pulse — bell is dead
        self.log.add(
            "The bell is cracked through. The metal is cold. The marks remain.",
            UI_TEXT_MID,
        )

        # Select or retrieve inscription for this bell
        if (x, y) not in self.local_map.bell_inscriptions:
            self.local_map.bell_inscriptions[(x, y)] = self.rng.choice(
                self._BELL_INSCRIPTION_IDS)

        ins_id = self.local_map.bell_inscriptions[(x, y)]
        text_def = self.data.texts.get(ins_id)

        # Teach word on first examine only
        first_time = (x, y) not in self.local_map.examined_bells
        if first_time:
            if text_def and text_def.get("teach_words"):
                lang = getattr(self.player, "language", None)
                if lang and ins_id not in lang.taught_texts:
                    from engine.language_system import learn_from_text
                    learned = learn_from_text(
                        text_def, lang, self.data.deep_tongue, self.rng)
                    lang.taught_texts.add(ins_id)
                    for wid in learned:
                        wdef = self.data.deep_tongue.get(wid, {})
                        deep = wdef.get("deep", wid)
                        common = wdef.get("common", "")
                        lang.translation_events[wid] = self.world_time.turn
                        self.log.add(
                            f"Something stirs. A word surfaces — [{deep}]: {common}.",
                            DEEP_TONGUE_COLOUR,
                        )
                        self._maybe_show_lexicon_hint()
            self.local_map.examined_bells.add((x, y))

        # Open inscription
        if text_def:
            self.text_reader.open_text(
                text_def,
                panel_style="ziggurat",
                text_align="center",
                line_spacing_bonus=6,
                panel_size="inscription",
            )

        return first_time

    def _build_warm_tile_ids(self) -> None:
        """Rebuild the set of terrain IDs that emit warmth."""
        self._warm_tile_ids = {
            tid for tid, entry in self.data.terrain.items()
            if entry.get("warmth_radius", 0) > 0
        }

    def _update_warmth(self) -> None:
        """Check player proximity to warm tiles and warm decor. Fire transition messages on state change."""
        was_warm = self.player_near_fire
        near     = False
        px, py   = self.player.x, self.player.y
        for dx in range(-4, 5):
            if near:
                break
            for dy in range(-4, 5):
                wx, wy = px + dx, py + dy
                if not self.local_map.in_bounds(wx, wy):
                    continue
                # Terrain warmth
                if self._warm_tile_ids:
                    tid = self._resolve_terrain_id(wx, wy)
                    if tid in self._warm_tile_ids:
                        entry  = self.data.terrain.get(tid, {})
                        radius = entry.get("warmth_radius", 0)
                        if abs(dx) <= radius and abs(dy) <= radius:
                            near = True
                            break
                # Decor warmth (campfire_lit and any future warm decor)
                if not near:
                    _did = self.local_map.decor.get((wx, wy))
                    if _did:
                        _de = self.data.decoratives.get(_did, {})
                        _dr = _de.get("warmth_radius", 0)
                        if _dr > 0 and abs(dx) <= _dr and abs(dy) <= _dr:
                            near = True
                            break
        self.player_near_fire = near
        if near and not was_warm:
            self.log.add("The fire takes the edge off.", MSG_DEFAULT)
        elif was_warm and not near:
            self.log.add("The cold returns.", STONE_BLUE)

    # ------------------------------------------------------------------ #
    #  Placement cursor
    # ------------------------------------------------------------------ #

    def _start_placement_cursor(self, tile_id: str, recipe: dict, selected=None) -> None:
        """Enter PLACEMENT_CURSOR mode after a places_in_world craft succeeds."""
        self._pending_placement_tile   = tile_id
        self._pending_placement_recipe = recipe
        from engine.crafting import plan_craft
        from rendering.craft_screen import CraftScreen
        self._pending_craft_items = selected if selected is not None else plan_craft(
            recipe, self.player.inventory, ambient_sources=CraftScreen._build_ambient_sources(self))[0]
        self._placement_mode = "campfire"
        # Start on the tile adjacent to the player (north) as a sensible default
        self._placement_cursor_x = self.player.x
        self._placement_cursor_y = max(0, self.player.y - 1)
        self.mode = GameMode.PLACEMENT_CURSOR
        msg = recipe.get("placement_message", "Where will you set it?")
        self.log.add(msg, MSG_DEFAULT)

    def _is_valid_placement(self, x: int, y: int) -> bool:
        """True if (x, y) is a legal tile to place a world object on."""
        if not self.local_map.in_bounds(x, y):
            return False
        if not self.local_map.walkable[x, y]:
            return False
        if self._get_blocking_entity(x, y):
            return False
        if self._decor_blocks_movement(x, y):
            return False
        return True

    def _decor_blocks_movement(self, x: int, y: int) -> bool:
        """True if the decorative tile at (x, y) has blocks_movement: true."""
        decor_id = self.local_map.decor.get((x, y))
        if not decor_id:
            return False
        return self.data.decoratives.get(decor_id, {}).get("blocks_movement", False)

    def _is_valid_drying(self, x: int, y: int) -> bool:
        """Valid drying spot: walkable, no blocking decor, no active processing, within warmth_radius of campfire_lit."""
        if not self.local_map.in_bounds(x, y):
            return False
        if not self.local_map.walkable[x, y]:
            return False
        if self.local_map.decor.get((x, y)):
            return False   # any existing decor blocks drying
        if (x, y) in self.local_map.processing_layer:
            return False   # already processing here
        # Must be within warmth_radius of a nearby campfire_lit
        px, py = x, y
        for (dx, dy), did in self.local_map.decor.items():
            if did == "campfire_lit":
                decor_def = self.data.decoratives.get(did, {})
                radius    = decor_def.get("warmth_radius", 3)
                if max(abs(dx - px), abs(dy - py)) <= radius and (dx, dy) != (px, py):
                    return True
        return False

    def _is_valid_cooking(self, x: int, y: int) -> bool:
        """Valid cooking spot: campfire_lit decor, no existing processing at this tile."""
        if not self.local_map.in_bounds(x, y):
            return False
        decor_id = self.local_map.decor.get((x, y))
        if decor_id != "campfire_lit":
            return False
        # One item at a time on the fire -- O(1) lookup via processing_layer
        if (x, y) in self.local_map.processing_layer:
            return False
        return True

    def _start_processing_placement(self, recipe: dict, selected=None) -> None:
        """Enter PLACEMENT_CURSOR mode for a passive_processing recipe."""
        decor_id = recipe.get("processing_decor", "")
        self._pending_processing   = recipe
        self._pending_placement_recipe = recipe
        from engine.crafting import plan_craft
        from rendering.craft_screen import CraftScreen
        self._pending_craft_items = selected if selected is not None else plan_craft(
            recipe, self.player.inventory, ambient_sources=CraftScreen._build_ambient_sources(self))[0]
        self._pending_placement_tile   = decor_id
        source = recipe.get("processing_source", "drying")
        self._placement_mode = "cooking" if source == "cooking" else "drying"

        px, py = self.player.x, self.player.y
        if self._placement_mode == "drying":
            # Find nearest valid drying tile by Chebyshev distance
            # Scan order: N, NE, E, SE, S, SW, W, NW (ties broken by scan order)
            _best = None
            _best_dist = 999
            # Search outward by Chebyshev distance from player
            for _r in range(1, 8):
                for _dx in range(-_r, _r + 1):
                    for _dy in range(-_r, _r + 1):
                        _tx, _ty = px + _dx, py + _dy
                        if self._is_valid_drying(_tx, _ty):
                            _cd = max(abs(_dx), abs(_dy))
                            if _cd < _best_dist:
                                _best_dist = _cd
                                _best = (_tx, _ty)
                if _best is not None:
                    break
            if _best:
                self._placement_cursor_x, self._placement_cursor_y = _best
            else:
                self._placement_cursor_x = px
                self._placement_cursor_y = py
        else:
            self._placement_cursor_x = px
            self._placement_cursor_y = max(0, py - 1)

        self.mode = GameMode.PLACEMENT_CURSOR
        msg = recipe.get("placement_message", "Where will you set it to work?")
        self.log.add(msg, MSG_DEFAULT)

    def _handle_key_placement(self, key: int) -> None:
        """Input handler for PLACEMENT_CURSOR mode."""
        if self._pending_throw is not None:
            from engine.effect_lifecycle import throw_key
            throw_key(self, key)
            return
        from engine.engine import MOVE_KEYS

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            px, py = self.player.x, self.player.y
            ox = self._placement_cursor_x - px
            oy = self._placement_cursor_y - py
            self._placement_cursor_x = px + max(-1, min(1, ox + dx))
            self._placement_cursor_y = py + max(-1, min(1, oy + dy))
            return

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            cx, cy = self._placement_cursor_x, self._placement_cursor_y

            if self._placement_mode in ("drying", "cooking"):
                # Processing placement — items not yet consumed; validate then craft
                if not self._check_placement_valid(cx, cy):
                    if self._placement_mode == "drying":
                        self.log.add("Too far from the fire.", MSG_DEFAULT)
                    else:
                        self.log.add("Must be placed on the fire.", MSG_DEFAULT)
                    return
                recipe = self._pending_processing
                if recipe is None:
                    self.mode = GameMode.LOCAL
                    return
                from engine.crafting import commit_craft
                inv     = getattr(self.player, "inventory", None)
                kw_data = getattr(self.data, "keywords", {})
                # Build ambient for the campfire at (cx, cy)
                from rendering.craft_screen import CraftScreen
                ambient = CraftScreen._build_ambient_sources(self)
                result_id = recipe.get("result_item", "")
                if result_id not in self.data.items or not commit_craft(
                        self, recipe, self._pending_craft_items, ambient):
                    self.log.add("The materials are not here.", MSG_DEFAULT)
                    self._pending_processing       = None
                    self._pending_placement_tile   = None
                    self._pending_placement_recipe = None
                    self._pending_craft_items = None
                    self._placement_mode = "campfire"
                    self.mode = GameMode.LOCAL
                    return
                # Capture ingredient name before consumption
                _ingredient_name = ""
                _rsi = recipe.get("requires_single_item")
                if _rsi:
                    from engine.crafting import _item_has_all_tags
                    _rsi_tags = _rsi if isinstance(_rsi, list) else _rsi.get("tags", [])
                    for _inv_item in (self._pending_craft_items or []):
                        if _item_has_all_tags(_inv_item, _rsi_tags):
                            _ingredient_name = getattr(_inv_item, "name", "")
                            break
                if not _ingredient_name:
                    # Fall back to first component match
                    from engine.crafting import _item_has_tag
                    for _comp in recipe.get("components", []):
                        for _inv_item in (self._pending_craft_items or []):
                            if _item_has_tag(_inv_item, _comp["tag"], _comp.get("min_tier", 1)):
                                _ingredient_name = getattr(_inv_item, "name", "")
                                break
                        if _ingredient_name:
                            break
                # Place processing decor — skip for cooking (fire tile stays)
                decor_id = recipe.get("processing_decor", "")
                source   = recipe.get("processing_source", "drying")
                _on_fire = (source == "cooking")
                if not _on_fire and decor_id and decor_id in self.data.decoratives:
                    from generation.decor_utils import place_decor
                    place_decor(self.local_map, cx, cy, decor_id)
                # Push to processing queue (with world position)
                result_id  = recipe.get("result_item", "")
                turns      = recipe.get("processing_turns", 20)
                proc_msgs  = getattr(self.data, "processing_messages", {})
                start_tmpl = proc_msgs.get(source, {}).get("start", "The work begins.")
                result_def  = self.data.items.get(result_id, {})
                result_name = result_def.get("name", result_id)
                # Use ingredient name in start message, fall back to result name
                _msg_name = _ingredient_name or result_name
                _completion_msg = recipe.get("completion_message", "")
                self.local_map.processing_layer[(cx, cy)] = {
                    "item_id":         result_id,
                    "turns_remaining": turns,
                    "decor_id":        "" if _on_fire else decor_id,
                    "source":          source,
                    "completion_message": _completion_msg,
                    "on_fire":         _on_fire,
                }
                self.log.add(start_tmpl.format(item_name=_msg_name), MSG_LORE)
                self._emit_placement_burst(cx, cy)
                self._pending_processing       = None
                self._pending_placement_tile   = None
                self._pending_placement_recipe = None
                self._pending_craft_items = None
                self._placement_mode           = "campfire"
                self.mode = GameMode.LOCAL
                self._log_scroll = 0
                self._advance_turn()
                return

            # Standard campfire/world-object placement
            if cx == self.player.x and cy == self.player.y:
                self.log.add("You cannot place it at your own feet.", MSG_DEFAULT)
                return
            if not self._is_valid_placement(cx, cy):
                self.log.add("You cannot place it there.", MSG_DEFAULT)
                return
            # Place the tile — decor tiles go to the decor layer, terrain to terrain
            tile_id = self._pending_placement_tile
            from engine.crafting import commit_craft
            from rendering.craft_screen import CraftScreen
            if (tile_id not in self.data.decoratives and tile_id not in self.data.terrain
                    or not commit_craft(self, self._pending_placement_recipe or {},
                                        self._pending_craft_items, CraftScreen._build_ambient_sources(self))):
                self.log.add("The work cannot be completed. The materials remain.", MSG_DEFAULT)
                return
            _placed = False
            if tile_id and tile_id in self.data.decoratives:
                from generation.decor_utils import place_decor
                place_decor(self.local_map, cx, cy, tile_id)
                _placed = True
            elif tile_id and tile_id in self.data.terrain:
                t = self.data.terrain[tile_id]
                self.local_map.set_tile(cx, cy, tile_id,
                                        t.get("walkable", False),
                                        t.get("transparent", True))
                _placed = True
            if _placed:
                recipe = self._pending_placement_recipe or {}
                self.log.add(recipe.get("result_message",
                             f"{recipe.get('name', 'It')} placed."), MSG_DEFAULT)
                self._emit_placement_burst(cx, cy)
            self._pending_placement_tile   = None
            self._pending_placement_recipe = None
            self._pending_craft_items = None
            self._placement_mode           = "campfire"
            self.mode = GameMode.LOCAL
            self._log_scroll = 0
            self._advance_turn()
            return

        if key == pygame.K_ESCAPE:
            if self._placement_mode in ("drying", "cooking"):
                # Items not yet consumed — just cancel
                self.log.add("You decide against it.", MSG_DEFAULT)
                self._pending_processing       = None
                self._pending_placement_tile   = None
                self._pending_placement_recipe = None
                self._pending_craft_items = None
                self._placement_mode           = "campfire"
                self.mode = GameMode.LOCAL
                return
            # Nothing has been consumed; cancellation preserves exact instances.
            self.log.add("You decide against it.", MSG_DEFAULT)
            self._pending_placement_tile   = None
            self._pending_placement_recipe = None
            self._pending_craft_items = None
            self._placement_mode           = "campfire"
            self.mode = GameMode.LOCAL
            return

    def _emit_placement_burst(self, wx: int, wy: int) -> None:
        """World-space burst particles + ring on successful tile placement."""
        import math as _pm
        import random as _pr
        from rendering.particles import Particle as _Pp
        _rng = _pr.Random()
        _cx = float(wx) + 0.5
        _cy = float(wy) + 0.5
        # 8-12 outward circle particles
        for _ in range(_rng.randint(8, 12)):
            _angle = _rng.uniform(0, _pm.pi * 2)
            _speed = _rng.uniform(1.5, 3.5)
            _lt    = _rng.uniform(0.35, 0.55)
            self.particle_system.emit(_Pp(
                x=_cx, y=_cy,
                vx=_pm.cos(_angle) * _speed,
                vy=_pm.sin(_angle) * _speed,
                lifetime=_lt, max_lifetime=_lt,
                r=OLD_GOLD[0], g=OLD_GOLD[1], b=OLD_GOLD[2],
                alpha=220, size=2.5,
                space="world", shape="circle",
            ))
        # Expanding ring
        _rlt = 0.6
        self.particle_system.emit(_Pp(
            x=_cx, y=_cy,
            vx=0.0, vy=0.0,
            lifetime=_rlt, max_lifetime=_rlt,
            r=OLD_GOLD[0], g=OLD_GOLD[1], b=OLD_GOLD[2],
            alpha=180, size=1.0,
            space="world", shape="ring",
            ring_radius=0.0, ring_max_radius=0.75, ring_width=2,
        ))

    def _check_placement_valid(self, cx: int, cy: int) -> bool:
        """Dispatch to the appropriate validity checker based on _placement_mode."""
        if self._placement_mode == "throw":
            from engine.effect_lifecycle import valid_throw
            return valid_throw(self, cx, cy)
        if self._placement_mode == "drying":
            return self._is_valid_drying(cx, cy)
        elif self._placement_mode == "cooking":
            return self._is_valid_cooking(cx, cy)
        return self._is_valid_placement(cx, cy)

    def _render_placement_cursor(
        self,
        screen:   pygame.Surface,
        cam_x:    int,
        cam_y:    int,
        viewport: pygame.Rect,
    ) -> None:
        """Draw the placement cursor and a one-line hint."""
        cx, cy   = self._placement_cursor_x, self._placement_cursor_y
        valid    = self._check_placement_valid(cx, cy)
        color    = DISCHARGE_FLASH if valid else FRESH_WOUND
        self.look_mode.render_cursor(screen, self, cam_x, cam_y,
                                     x=cx, y=cy, color=color)
        self._render_placement_hint(screen, viewport, valid)

    def _render_placement_hint(
        self,
        screen:   pygame.Surface,
        viewport: pygame.Rect,
        valid:    bool,
    ) -> None:
        font = getattr(self.display, "font_ui_small", None)
        if not font:
            return
        if valid:
            if self._placement_mode == "drying":
                hint = "[ ENTER ] spread here to dry     [ ESC ] cancel"
            elif self._placement_mode == "cooking":
                hint = "[ ENTER ] set to cook     [ ESC ] cancel"
            elif self._placement_mode == "throw":
                hint = "[ ENTER ] throw     [ ESC ] cancel"
            else:
                hint = "[ ENTER ] place     [ ESC ] cancel"
            col  = DISCHARGE_FLASH
        else:
            if self._placement_mode == "drying":
                hint = "Too far from the fire.     [ ESC ] cancel"
            elif self._placement_mode == "cooking":
                hint = "Must be placed on the fire.     [ ESC ] cancel"
            elif self._placement_mode == "throw":
                hint = "Cannot throw here.     [ ESC ] cancel"
            else:
                hint = "Cannot place here.     [ ESC ] cancel"
            col  = FRESH_WOUND
        text_surf = font.render(hint, True, col)
        x = viewport.left + (viewport.width - text_surf.get_width()) // 2
        y = viewport.bottom - text_surf.get_height() - 10
        bg_w = text_surf.get_width() + 10
        bg_h = text_surf.get_height() + 6
        bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        bg_surf.fill((*VOID_BLACK, 210))
        screen.blit(bg_surf,   (x - 5, y - 3))
        screen.blit(text_surf, (x, y))

    def _try_open_interaction_cursor(self) -> None:
        """
        Shift+G: always open the interaction cursor over the 3×3 grid.
        candidates is passed through to the cursor for ENTER handling;
        zero or one candidate both work — the player navigates and confirms.
        """
        candidates = self._get_interaction_candidates()
        self.interaction_cursor.enter(candidates, self.player.x, self.player.y)
        self.mode = GameMode.INTERACTION_CURSOR

    def _on_player_step(self, x: int, y: int) -> None:
        """Called after player moves to (x, y). Applies move_cost debt and effects."""
        # Movement resets rain collection
        self.rain_collection_progress = 0
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

        # Needs move penalty — stacks with terrain cost
        needs = getattr(self.player, "needs", None)
        if needs:
            self._move_debt += needs.hunger_move_penalty + needs.thirst_move_penalty

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
            if fighter:
                thorn_dmg = max(1, 1 - fighter.effective_av // 3)
                fighter.take_damage(thorn_dmg)
                self.log.add("The briars catch at you.", DUSTY_ROSE)
                if self.display.CALLOUT_STATUS_EFFECTS:
                    self.callouts.add("thorns",
                                      self.player.x, self.player.y,
                                      DUSTY_ROSE, font_size="status")
                self.player.took_damage_this_turn = True
                if fighter.is_dead:
                    self._death_killer = "briars"
                    self._on_player_death()

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

    # Surface-night FOV radius by moon phase name
    _MOON_FOV: dict[str, int] = {
        "The Full Witness": 18,
        "The Swelling Eye": 14,
        "The Dimming Eye":  14,
        "The Half Truth":   10,
        "The Half Lie":     10,
        "The Thin Knife":    6,
        "The Waning Knife":  6,
        "The Dark Seal":     3,
    }

    # Dusk/dawn transition windows (hours, inclusive)
    _DUSK_START:  float = 19.0   # dusk ramp begins
    _DUSK_END:    float = 21.0   # full night
    _DAWN_START:  float =  5.0   # dawn ramp begins
    _DAWN_END:    float =  7.0   # full day

    # Surface day radius (full daylight)
    _DAY_FOV: int = 40

    def _compute_fov_base(self) -> int:
        """Underground=1, surface day=40, surface night=moon phase table.
        Dusk and dawn transition windows interpolate smoothly."""
        try:
            if self.current_submap_id is not None:
                return 1

            hour       = self.world_time.hour
            night_fov  = self._MOON_FOV.get(self.world_time.moon_phase_name, 6)
            day_fov    = self._DAY_FOV

            # Dawn ramp: _DAWN_START → _DAWN_END  (night → day)
            if self._DAWN_START <= hour < self._DAWN_END:
                t = (hour - self._DAWN_START) / (self._DAWN_END - self._DAWN_START)
                return int(night_fov + t * (day_fov - night_fov))

            # Dusk ramp: _DUSK_START → _DUSK_END  (day → night)
            if self._DUSK_START <= hour < self._DUSK_END:
                t = (hour - self._DUSK_START) / (self._DUSK_END - self._DUSK_START)
                return int(day_fov + t * (night_fov - day_fov))

            # Full day
            if self._DAWN_END <= hour < self._DUSK_START:
                return day_fov

            # Full night
            return night_fov

        except Exception as e:
            import traceback
            print(f"[CRITICAL] _compute_fov_base() crashed: {e}")
            traceback.print_exc()
            return 40  # safe surface default

    def _get_equipped_light_radius(self) -> int:
        """Return light_radius from equipped light item JSON. 0 if none or inactive."""
        light = getattr(self.player, "light_source", None)
        if not (light and light.active):
            return 0
        # item_system stores a reference to the lighting item on the LightSource component
        item_ref = getattr(light, "_item_ref", None)
        if item_ref is not None:
            item_def = self.data.items.get(getattr(item_ref, "item_id", ""), {})
            lr = item_def.get("light_radius", 0)
            if lr > 0:
                return lr
        # Fallback: scan all equipment slots for any item with light_data
        equip = getattr(self.player, "equipment", None)
        if not equip:
            return 0
        for slot_item in equip.slots.values():
            if slot_item and getattr(slot_item, "light_data", None):
                item_def = self.data.items.get(getattr(slot_item, "item_id", ""), {})
                lr = item_def.get("light_radius", 0)
                if lr > 0:
                    return lr
        return 0

    def _update_fov(self) -> None:
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
        # ── Unconditional surface guard ───────────────────────────────
        # If current_submap_id is set but no matching submap exists in the
        # current chunk, the ID is stale (e.g. from a debug teleport that
        # skipped _ascend_from_submap). Clear it and log so the root cause
        # can be traced. Generation functions must never write this field.
        if self.current_submap_id is not None:
            _guard_chunk = self.world_map.get(self.world_x, self.world_y) if hasattr(self, "world_map") else None
            _chunk_subs  = getattr(_guard_chunk, "submaps", []) or []
            if not any(getattr(s, "submap_id", None) == self.current_submap_id for s in _chunk_subs):
                print(
                    f"[FOV WARNING] current_submap_id={self.current_submap_id!r} has no matching "
                    f"submap in chunk ({self.world_x},{self.world_y}) "
                    f"biome={getattr(_guard_chunk, 'biome_id', '?')}. "
                    f"Forcing surface. Check generation/debug teleport code for stale writes."
                )
                self.current_submap_id = None

        # ── FOV formula (single definition) ──────────────────────────
        # base → with_light = max(base, light_radius)
        # with wraiths: snap to ability_range, then drain 1/turn/wraith, floor 2
        # on wraith death: +3 overcorrect for 3 turns
        base         = self._compute_fov_base()
        if self.current_submap_id is None and base < 3:
            print(f"[WARNING] FOV radius {base} on surface — clamping to 8. Check _compute_fov_base().")
            base = 8
        light_radius = self._get_equipped_light_radius()
        with_light   = max(base, light_radius)

        # Mark whether the torch is actually extending vision beyond ambient.
        # When ambient dominates, suppress torch colour/brightness overlay in renderer.
        _player_ls = getattr(self.player, "light_source", None)
        if _player_ls and _player_ls.active:
            _player_ls.is_dominant = (light_radius > base)

        from engine.effect_lifecycle import refresh_wraith_aura
        refresh_wraith_aura(self)
        if self._wraith_aura_state:
            _wraith_range  = self.data.entities.get("bog_wraith", {}).get("ability_range", 8)
            snap_penalty   = max(0, with_light - _wraith_range)
            drain_penalty  = sum(max(0, t - 1) for t in self._wraith_aura_state.values())
            wraith_penalty = snap_penalty + drain_penalty
            overcorrect    = 3 if self._wraith_overcorrect_turns > 0 else 0
            active_radius  = max(2, with_light - wraith_penalty + overcorrect)
        else:
            active_radius = with_light

        # Weather FOV cap (fog, forgetting_fog) — values from weather.json mechanics
        _weather = getattr(self, "weather", None)
        _fov_cap = None
        if _weather:
            _fov_cap_val = _weather.get_mechanic("fov_cap", None)
            if _fov_cap_val is not None:
                _fov_cap = int(_fov_cap_val)
                active_radius = min(active_radius, _fov_cap)

        # ── Zone ambient for lighting (still needed for light_map) ───
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

        # ── Light source FOV contribution ───────────────────────────
        # For each light source the player can see, compute a secondary
        # FOV from that source and union it with the visible mask.
        _light_sources: list[tuple[int, int, int, float]] = []  # (lx, ly, radius, dist_to_player)
        _max_light_radius = 0

        # Terrain light sources (street lamps etc.)
        _search_r = active_radius + 10  # generous search radius
        _px, _py = self.player.x, self.player.y
        _lm_w, _lm_h = self.local_map.width, self.local_map.height
        for _slx in range(max(0, _px - _search_r), min(_lm_w, _px + _search_r + 1)):
            for _sly in range(max(0, _py - _search_r), min(_lm_h, _py + _search_r + 1)):
                if not bool(visible[_slx, _sly]):
                    continue
                _sterrain = str(self.local_map.tiles[_slx, _sly]["terrain"])
                _std = self.data.terrain.get(_sterrain, {})
                _semit = _std.get("light_emit", 0)
                if _semit > 0:
                    _sdist = abs(_slx - _px) + abs(_sly - _py)
                    _light_sources.append((_slx, _sly, int(_semit), _sdist))
                    _max_light_radius = max(_max_light_radius, int(_semit))

        # Decor light sources (campfire_lit etc.)
        _decor = getattr(self.local_map, "decor", {})
        for (_dlx, _dly), _did in _decor.items():
            if not (0 <= _dlx < _lm_w and 0 <= _dly < _lm_h):
                continue
            if not bool(visible[_dlx, _dly]):
                continue
            _dentry = self.data.decoratives.get(_did, {})
            _demit = _dentry.get("light_emit", 0)
            if _demit > 0:
                _ddist = abs(_dlx - _px) + abs(_dly - _py)
                _light_sources.append((_dlx, _dly, int(_demit), _ddist))
                _max_light_radius = max(_max_light_radius, int(_demit))

        # Cap at 20 nearest, then compute secondary FOVs
        if _light_sources:
            _light_sources.sort(key=lambda t: t[3])
            for _llx, _lly, _lrad, _ in _light_sources[:20]:
                _lfov = tcod.map.compute_fov(
                    self.local_map.transparent,
                    (_llx, _lly),
                    radius=_lrad,
                    light_walls=True,
                    algorithm=tcod.FOV_SYMMETRIC_SHADOWCAST,
                )
                visible |= _lfov

        self.local_map.tiles["visible"][:] = visible

        # ── Passive memory — lit zones only ──────────────────────────
        # In well-lit areas, cast sightlines to map edge and commit
        # everything reachable to explored (memory) even beyond active FOV.
        # Tiles are remembered but not live — entities won't show there.
        if ambient_intensity > 0.4:
            # In fog/forgetting_fog, cap passive memory to active_radius so tiles
            # beyond the fog cap don't render as dim memory tiles (making fog appear broken).
            _passive_radius = active_radius if _fov_cap is not None else 0
            passive_fov = tcod.map.compute_fov(
                self.local_map.transparent,
                (self.player.x, self.player.y),
                radius=_passive_radius,  # 0 = unlimited in tcod
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
            if light and getattr(light, "is_dominant", True):
                light.apply_to_light_map(lm, entity.x, entity.y, fov)

        # Terrain light sources — any terrain tile with light_emit > 0 participates.
        # Data-driven: add light_emit + light_mode fields to terrain.json, no code changes needed.
        import math as _lm_math
        _now_s = pygame.time.get_ticks() / 1000.0
        for _lx in range(self.local_map.width):
            for _ly in range(self.local_map.height):
                if not bool(fov[_lx, _ly]):
                    continue
                _terrain = str(self.local_map.tiles[_lx, _ly]["terrain"])
                _td = self.data.terrain.get(_terrain, {})
                _emit = _td.get("light_emit", 0)
                if _emit <= 0:
                    continue
                _mode      = _td.get("light_mode", "steady")
                _lc_raw    = _td.get("light_color", [255, 220, 150])
                _lc_r = _lc_raw[0] / 255.0
                _lc_g = _lc_raw[1] / 255.0
                _lc_b = _lc_raw[2] / 255.0
                # Determine effective radius for this frame
                if _mode == "pulse":
                    _pmin  = float(_td.get("light_pulse_min", _emit // 2))
                    _pmax  = float(_td.get("light_pulse_max", _emit))
                    _prate = float(_td.get("light_pulse_rate", 0.5))
                    # Per-tile phase offset so lamps don't all pulse in sync
                    _phase = (_lx * 0.37 + _ly * 0.59) % 1.0
                    _sine  = _lm_math.sin(
                        2.0 * _lm_math.pi * (_prate * _now_s + _phase)
                    )
                    # sine in [-1, 1] → radius in [pmin, pmax]
                    _radius = int(round(_pmin + (_pmax - _pmin) * (_sine * 0.5 + 0.5)))
                else:  # "steady"
                    _radius = int(_emit)
                if _radius <= 0:
                    continue
                for _dx2 in range(-_radius, _radius + 1):
                    for _dy2 in range(-_radius, _radius + 1):
                        _nx, _ny = _lx + _dx2, _ly + _dy2
                        if not self.local_map.in_bounds(_nx, _ny):
                            continue
                        if not bool(fov[_nx, _ny]):
                            continue
                        _dist = (_dx2 * _dx2 + _dy2 * _dy2) ** 0.5
                        if _dist > _radius:
                            continue
                        # Same falloff as LightSource.apply_to_light_map (linear, falloff=1)
                        _strength = max(0.0, 1.0 - _dist / _radius)
                        lm[_nx, _ny, 0] = min(1.0, lm[_nx, _ny, 0] + _lc_r * _strength)
                        lm[_nx, _ny, 1] = min(1.0, lm[_nx, _ny, 1] + _lc_g * _strength)
                        lm[_nx, _ny, 2] = min(1.0, lm[_nx, _ny, 2] + _lc_b * _strength)

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

    def _player_attack(self, target: "Actor") -> bool:
        from engine.combat import resolve_attack
        from engine.effect_lifecycle import creature_id, coated_weapon, coating_contact, knight_disruption, ability_enabled

        player_fighter = getattr(self.player, "fighter", None)
        target_fighter = getattr(target,      "fighter", None)
        if (not player_fighter or not target_fighter
                or self._player_is_dead or not self.player.is_alive
                or player_fighter.is_dead or player_fighter.hp <= 0 or not target.is_alive
                or target_fighter.is_dead):
            return False

        # Check impairment
        if not player_fighter.can_attack():
            self.log.add("Thou canst not strike.", AGED_WOOD)
            return False

        # Check line of sight (wall blocking)
        if not self._has_line_of_sight_adjacent(
            self.local_map, self.player.x, self.player.y, target.x, target.y
        ):
            self.log.add("Something stands between thee and thy mark.", AGED_WOOD)
            return False

        self._free_move_pending = False

        weapon = self._get_equipped_weapon() or _UNARMED_PROFILE

        # Get body def for target
        from engine.combat import get_body_def
        body_def = get_body_def(target_fighter, self.data.bodies)

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
            return True

        creature_def          = self.data.entities.get(creature_id(target), {})
        creature_essence_mods = creature_def.get("essence_modifiers", {})
        target_dodge_chance   = float(creature_def.get("dodge_chance", 0.0))

        rng = self.rng
        disrupted = knight_disruption(self)

        _weapon_entity = self.player.equipment.slots.get("weapon")
        weapon = self._player_weapon_profile(weapon, _weapon_entity)

        result = resolve_attack(
            attacker_name          = "thou",
            defender_name          = target.name,
            defender_fighter       = target_fighter,
            body_def               = body_def,
            weapon                 = weapon,
            creature_essence_mods  = creature_essence_mods,
            rng                    = rng,
            attacker_disrupted     = disrupted,
            defender_dodge_chance  = target_dodge_chance,
            shield_def             = None,   # creatures have no shield equipment
            damage_scale           = max(0.0, 1.0 + self.display.SPRINT_HIT_PENALTY) if self.sprint_turns_remaining > 0 else 1.0,
        )

        coating_contact(self, _weapon_entity, result)

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

        self._apply_player_hit_effects(target, result)

        if result.defender_dead or target_fighter.is_dead:
            self._on_entity_death(target)

        self._apply_melee_retaliation(target, result)
        return True

    def _player_weapon_profile(self, weapon: dict, weapon_item) -> dict:
        """Use the same perk and coating modifiers for both melee routes."""
        from engine.effect_lifecycle import coated_weapon
        fighter = self.player.fighter
        bonus = (getattr(fighter, "corruption_damage_bonus", 0)
                 + getattr(fighter, "corruption_channel_bonus", 0))
        profile = dict(weapon)
        if bonus > 0:
            profile["damage_bonus"] = profile.get("damage_bonus", 0) + bonus
        return coated_weapon(profile, weapon_item)

    def _apply_player_hit_effects(self, target, result) -> None:
        """Shared damage/critical hooks and blood effects for melee contact."""
        from engine.effect_lifecycle import creature_id
        # Critical hit — "CRITICAL" callout, screenshake, extra particles, hook
        if result.is_crit and result.damage_dealt > 0:
            if self.display.CALLOUT_DAMAGE_NUMBERS:
                self.callouts.add("CRITICAL", target.x, target.y - 0.8,
                                  OLD_GOLD, lifetime=1.4,
                                  font_size="crit")
            self.trigger_screenshake(4)
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
            blood_type = self.data.entities.get(creature_id(target), {}).get("blood_type", "red")
            self._place_blood_tile(target.x, target.y, blood_type)
            from rendering.particles import BLOOD_COLORS
            _bcolor = BLOOD_COLORS.get(blood_type)
            if _bcolor is not None:
                self._pending_blood.append({
                    "defender_tile": (target.x, target.y),
                    "attacker_tile": (self.player.x, self.player.y),
                    "color": _bcolor,
                    "is_crit": bool(result.is_crit),
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

    def _apply_melee_retaliation(self, target, result) -> None:
        from engine.effect_lifecycle import creature_id, ability_enabled
        player_fighter = self.player.fighter
        rng = self.rng
        # Briar lurker retaliation — thorns on melee contact
        if (creature_id(target) == "briar_lurker" and result.damage_dealt > 0
                and ability_enabled(target, self.local_map)):
            thorn = rng.randint(1, 2)
            if player_fighter:
                player_fighter.take_damage(thorn)
                self.log.add(
                    "The briars find thee as thou strikest.",
                    FOREST_DEEP,
                )
                self.log.add(f"  {thorn} damage.", LIFE_GREEN)
                self.player.took_damage_this_turn = True
                if player_fighter.is_dead:
                    self._death_killer = target.name
                    self._on_player_death()

    def _weapon_action_phases(self, cost: float) -> int:
        """Settle decimal costs to millionths; keep a bounded signed residual.

        Whole adjustments truncate toward zero so the first fast action still
        pays its base phase. Integer boundaries avoid accumulating float drift.
        Ordinary actions never touch this weapon-only balance.
        """
        units = 1_000_000
        balance = self._weapon_time_balance + round((cost - 1.0) * units)
        whole = (abs(balance) // units) * (-1 if balance < 0 else 1)
        self._weapon_time_balance = balance - whole * units
        return 1 + whole

    def _try_moveset_action(self, key: int):
        """Return the committed moveset result, or False for a free rejection."""
        from engine.movesets import get_moveset_action, execute_moveset, apply_damage_mult
        from engine.combat import resolve_attack, get_body_def, roll_dice
        from engine.effect_lifecycle import creature_id, coated_weapon, coating_contact, knight_disruption

        player_fighter = getattr(self.player, "fighter", None)
        if (self._player_is_dead or not self.player.is_alive
                or not player_fighter or player_fighter.hp <= 0 or not player_fighter.can_attack()):
            self.log.add("Thou canst not strike.", AGED_WOOD)
            return False

        weapon_def = self._get_equipped_weapon()
        if not weapon_def or not weapon_def.get("movesets"):
            return False

        key_label = "Q" if key == self.display.MOVESET_KEY_1 else "R"
        action = get_moveset_action(weapon_def, key_label)
        if not action:
            return False

        # Cooldown check
        aid = action["id"]
        cd = self.moveset_cooldowns.get(aid, 0)
        if cd > 0:
            self.log.add(f"{action['name']}: {cd} turns remaining.", UI_TEXT_DIM)
            return False

        # Find adjacent target (closest hostile)
        target = None
        best_dist = 999.0
        action_range = action.get("range", 1)
        for e in self.entities:
            if e is self.player or not getattr(e, "is_alive", True):
                continue
            fighter = getattr(e, "fighter", None)
            if (not getattr(e, "blocks_movement", True)
                    or fighter is None or fighter.is_dead):
                continue
            import math
            d = math.sqrt((e.x - self.player.x) ** 2 + (e.y - self.player.y) ** 2)
            if (d <= action_range + 0.5 and d < best_dist
                    and self._has_line_of_sight_adjacent(self.local_map, self.player.x, self.player.y, e.x, e.y)):
                best_dist = d
                target = e

        if target is None:
            self.log.add("Nothing in range.", UI_TEXT_DIM)
            return False

        # Execute moveset — checks positioning, HP gates
        ms_result = execute_moveset(action, self, target, weapon_def)
        if ms_result is None:
            # Blocked by positioning or HP gate — messages already posted
            return False

        self._free_move_pending = False

        # Set cooldown
        cooldown = action.get("cooldown", 0)
        if cooldown > 0:
            self.moveset_cooldowns[aid] = cooldown

        # Resolve damage via normal combat pipeline with modifiers
        player_fighter = getattr(self.player, "fighter", None)
        target_fighter = getattr(target, "fighter", None)
        body_def = get_body_def(target_fighter, self.data.bodies)
        creature_def = self.data.entities.get(creature_id(target), {})
        creature_essence_mods = creature_def.get("essence_modifiers", {})
        target_dodge = float(creature_def.get("dodge_chance", 0.0))
        if ms_result.ignore_dodge:
            target_dodge = 0.0

        rng = self.rng

        # Build weapon dict with damage multiplier
        weapon_item = self.player.equipment.slots.get("weapon")
        mod_weapon = dict(self._player_weapon_profile(weapon_def, weapon_item))
        base_dice = mod_weapon.get("damage_dice", "1d4")
        base_dmg = roll_dice(base_dice, rng)
        if knight_disruption(self):
            base_dmg = min(base_dmg, roll_dice(base_dice, rng))
        modified_dmg = apply_damage_mult(base_dmg, action)
        mod_weapon["damage_dice"] = f"{modified_dmg}d1"  # pre-rolled damage
        mod_weapon["damage_bonus"] = mod_weapon.get("damage_bonus", 0)

        # Ignore armour: set target AV to 0 temporarily
        saved_av = target_fighter.effective_av
        if ms_result.ignore_armour:
            target_fighter.effective_av = 0

        try:
            result = resolve_attack(
                attacker_name="thou",
                defender_name=target.name,
                defender_fighter=target_fighter,
                body_def=body_def,
                weapon=mod_weapon,
                creature_essence_mods=creature_essence_mods,
                rng=rng,
                defender_dodge_chance=target_dodge,
                damage_scale=max(0.0, 1.0 + self.display.SPRINT_HIT_PENALTY) if self.sprint_turns_remaining > 0 else 1.0,
            )
        finally:
            if ms_result.ignore_armour:
                target_fighter.effective_av = saved_av

        coating_contact(self, weapon_item, result)

        # Log combat messages
        from config import DEBUG_MODE
        for msg, mtype in zip(result.messages, result.message_types):
            color = MSG_COMBAT_OUT if mtype == "hit" else STONE_BLUE
            self.log.add(f"> {msg}", color)
        if result.damage_number > 0:
            self.log.add(f"  {result.damage_number} damage.", MSG_COMBAT_OUT)

        # Callout
        if ms_result.callout:
            self.callouts.add(
                ms_result.callout,
                float(target.x), float(target.y) - 0.3,
                ms_result.callout_colour,
                lifetime=1.0, font_size="status",
            )

        # Screen shake
        if ms_result.screen_shake > 0:
            self.trigger_screenshake(ms_result.screen_shake)

        self._apply_player_hit_effects(target, result)

        # Post-hit effects
        target_dead = target_fighter.is_dead

        # Reduce AV
        if ms_result.reduce_av > 0 and result.hit:
            target_fighter.effective_av = max(0, target_fighter.effective_av - ms_result.reduce_av)
            self.log.add("The blade leaves something behind in the wound.", MSG_COMBAT_OUT)

        # Suppress ability
        if ms_result.suppress_ability > 0 and result.hit:
            target._ability_suppressed_turns = max(getattr(target, "_ability_suppressed_turns", 0), ms_result.suppress_ability)
            self.log.add("Something severs between it and its nature.", MSG_COMBAT_OUT)

        # Destroy armour layer
        if ms_result.destroy_armour and result.hit:
            if target_fighter.effective_av > 0:
                target_fighter.effective_av = max(0, target_fighter.effective_av - 2)
                self.log.add("The armour tears.", MSG_COMBAT_OUT)

        # AoE disrupt (disconnect)
        if ms_result.aoe_disrupt_range > 0 and result.hit:
            from components.ai import AIState
            for e in self.entities:
                if e is self.player or e is target or not getattr(e, "is_alive", True):
                    continue
                if creature_id(e) != creature_id(target):
                    continue
                d = math.sqrt((e.x - target.x) ** 2 + (e.y - target.y) ** 2)
                if d <= ms_result.aoe_disrupt_range:
                    ai = getattr(e, "ai", None)
                    if ai:
                        e._disrupted_turns = max(getattr(e, "_disrupted_turns", 0), ms_result.aoe_disrupt_turns)
            self.log.add("Something shared between them breaks.", MSG_COMBAT_OUT)

        # Reveal knowledge (revelation_lens)
        if ms_result.reveal_knowledge and result.hit:
            self._reveal_creature_knowledge(target)

        # On-kill effects
        if target_dead:
            # Place pool on kill
            if ms_result.place_pool:
                from generation.decor_utils import place_decor
                place_decor(self.local_map, target.x, target.y, ms_result.place_pool)

            self._on_entity_death(target)

        self._apply_melee_retaliation(target, result)

        ms_result.free_move = bool(ms_result.free_move and target_dead)
        return ms_result

    def _reveal_creature_knowledge(self, target: "Actor") -> None:
        """Reveal one unknown weakness or strength of a creature type."""
        from engine.effect_lifecycle import creature_id
        target_id = creature_id(target)
        creature_def = self.data.entities.get(target_id, {})
        essence_mods = creature_def.get("essence_modifiers", {})
        if not essence_mods:
            self.log.add("It holds no more secrets.", UI_TEXT_DIM)
            return

        knowledge = self.creature_knowledge.get(target_id, {
            "revealed_weaknesses": [],
            "revealed_strengths": [],
        })

        all_known = set(knowledge["revealed_weaknesses"] + knowledge["revealed_strengths"])
        if len(all_known) >= len(essence_mods):
            self.log.add("It holds no more secrets.", UI_TEXT_DIM)
            return

        # Find weakest unknown (highest modifier = most weak to)
        unknown_weak = [(ess, mod) for ess, mod in essence_mods.items()
                        if ess not in all_known and mod > 1.0]
        unknown_strong = [(ess, mod) for ess, mod in essence_mods.items()
                          if ess not in all_known and mod < 1.0]

        revealed_ess = None
        revealed_type = None
        if unknown_weak:
            unknown_weak.sort(key=lambda x: -x[1])  # highest modifier first
            revealed_ess = unknown_weak[0][0]
            revealed_type = "weakness"
            knowledge["revealed_weaknesses"].append(revealed_ess)
        elif unknown_strong:
            unknown_strong.sort(key=lambda x: x[1])  # lowest modifier first
            revealed_ess = unknown_strong[0][0]
            revealed_type = "strength"
            knowledge["revealed_strengths"].append(revealed_ess)

        self.creature_knowledge[target_id] = knowledge

        if revealed_ess:
            self.log.add("Its nature opens to you.", MSG_ANCIENT)
            if revealed_type == "weakness":
                self.log.add(f"  Weak to: {revealed_ess}", RESONANCE_HIGH)
            else:
                self.log.add(f"  Resists: {revealed_ess}", DUSTY_ROSE)
            # Screen flash + particles
            self.callouts.add("REVEALED", float(self.player.x),
                              float(self.player.y) - 0.5,
                              RESONANCE_HIGH, lifetime=1.5, font_size="crit")

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
        """Write a blood/fluid decor tile at (x, y).
        Skips non-walkable tiles, stairs, and tiles already marked blood.
        Blood persists with the chunk via the decor layer — no ephemeral cleanup needed."""
        from generation.decor_utils import place_decor
        decor_id = self._BLOOD_TERRAIN.get(blood_type)
        if not decor_id:
            return  # blood_type "none" → no tile
        if not self.local_map.in_bounds(x, y):
            return
        # Don't place blood at the player's own tile — the blood_pool tile's dark
        # background shows through the transparent player sprite, making it appear
        # black. Blood particles already convey the visual effect at this position.
        if x == self.player.x and y == self.player.y:
            return
        if not self.local_map.walkable[x, y]:
            return
        terrain_id = str(self.local_map.tiles[x, y]["terrain"])
        # Don't place over stairs
        if terrain_id in ("stairs_down", "stairs_up"):
            return
        # Don't overwrite existing blood decor
        if self.local_map.decor.get((x, y)) in self._BLOOD_TERRAIN.values():
            return
        place_decor(self.local_map, x, y, decor_id)

    def _on_entity_death(self, entity: "Actor") -> None:
        from engine.message_log import MSG_DANGER
        from engine.hooks import HookEvent
        from engine.effect_lifecycle import creature_id

        # Fighter death may already be set; this separate flag owns finalization.
        if getattr(entity, "_death_finalized", False):
            return
        entity._death_finalized = True
        target_id = creature_id(entity)

        self.log.add(f"The {entity.name} is destroyed.", MSG_DANGER)
        entity.is_alive = False

        # on_death creature sound callout
        if self.display.CALLOUT_CREATURE_SOUNDS:
            _cdef = self.data.entities.get(target_id, {})
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
        creature_def = self.data.entities.get(target_id, {})
        effects = self.hooks.fire(HookEvent.ON_ENTITY_KILLED, {
            "entity":     entity,
            "entity_id":  target_id,
            "blood_type": creature_def.get("blood_type", "red"),
            "x": entity.x, "y": entity.y,
            "player": self.player,
            "engine": self,
        })
        _apply_effects(effects, self)

        # Ephemeral creatures dissolve — no corpse
        _ephemeral = creature_def.get("ephemeral", False)
        if not _ephemeral:
            from generation.floor_object_utils import place_floor_object as _pfo_corpse
            from engine.harvesting import decay_turns
            _decay = decay_turns(creature_def)
            _corpse_item = self.item_factory.create("corpse", entity.x, entity.y)
            if _corpse_item:
                _corpse_item.name = f"remains of {entity.name}"
                _corpse_item.source_creature = target_id
                _corpse_item.decay_timer = _decay
                _pfo_corpse(self.local_map, entity.x, entity.y, _corpse_item)

        # Bog wraith death — remove from aura state immediately
        if target_id == "bog_wraith":
            entity._wraith_exposure_turns = 0
            eid = id(entity)
            if eid in self._wraith_aura_state:
                del self._wraith_aura_state[eid]
                self._wraith_overcorrect_turns = 3
            self.log.add("The forgetting lifts.", COLDBELL_LIGHT)
            self._update_fov()

    def _update_wraith_aura(self) -> None:
        """
        Called once per turn. Tracks consecutive turns each bog wraith spends
        within ability_range tiles of the player. Fires "Sight dims." on turn 2+.
        Penalty = sum of max(0, turns - 1) per wraith, read by _update_fov.
        """
        from engine.effect_lifecycle import refresh_wraith_aura
        refresh_wraith_aura(self, advance=True)
        if self._wraith_overcorrect_turns > 0:
            self._wraith_overcorrect_turns -= 1

    def _on_player_death(self) -> None:
        self._free_move_pending = False
        self.trigger_screenshake(6.0)

        # Capture the last 5 messages before adding death messages
        recent = self.log.recent(5)
        self._death_messages = [m.with_count() for m in recent]

        # Preserve other campaigns. Death retires only this manager's slot.
        try:
            self.save_manager.delete_slot()
        except Exception as error:
            self.log.add(f"Save retirement failed: {error}", FRESH_WOUND)

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

    def _pick_up_item(self) -> bool:
        inv = getattr(self.player, "inventory", None)
        if inv is None:
            return False

        px, py = self.player.x, self.player.y
        items_here = self._items_at(px, py)

        if items_here:
            if len(items_here) == 1:
                _top = items_here[0]
                if getattr(_top, "source_creature", None):
                    return self._interactable_butcher(px, py, _top)
                else:
                    return self._take_item(_top, inv)
            else:
                # Multiple items — open interaction cursor with selection prompt
                self.interaction_cursor.enter([(px, py)], px, py)
                self.interaction_cursor._selection_prompt = {
                    "scene": self.local_map,
                    "address": (self.world_x, self.world_y, self.current_submap_id),
                    "items": list(items_here),
                    "selected": 0,
                    "lx": px, "ly": py,
                }
                self.mode = GameMode.INTERACTION_CURSOR
        else:
            adjacent = self._adjacent_items()
            if not adjacent:
                self.log.add(
                    "Nothing here.",
                    WORN_STONE,
                )
                return False
            self._pickup_mode = True
            self.log.add(
                "Pick up from where? (movement key, ESC to cancel)",
                WORN_STONE,
            )
        return False

    def _items_at(self, x: int, y: int) -> list:
        """Return items at tile — checks floor_objects first, falls back to entities."""
        from generation.floor_object_utils import get_floor_objects as _gfo_at
        floor = _gfo_at(self.local_map, x, y)
        if floor:
            return list(floor)
        # Fallback: legacy entity items (during migration)
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
                x, y = self.player.x + dx, self.player.y + dy
                if self.interaction_cursor.can_reach(self, x, y):
                    results.extend(self._items_at(x, y))
        return results

    def _take_item(self, item: "Item", inv: "Inventory") -> bool:
        from engine.item_transfers import take_floor
        if take_floor(self, item):
            _iname = getattr(item, "name", "") or "something"
            self.log.add(f"Thou takest the {_iname}.", WORN_STONE)
            return True
        if inv.weight_for(inv.items + [item]) > inv.capacity:
            self.log.add(inv.capacity_feedback(item), OLD_GOLD)
            return False
        self.log.add("Thou canst not take that now.", OLD_GOLD)
        return False

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

