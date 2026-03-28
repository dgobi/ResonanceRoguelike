# engine/interaction_cursor.py
"""
Adjacent-tile selection cursor for Shift+G interact.

When multiple adjacent tiles contain harvestable terrain or floor items,
this cursor lets the player choose which tile to interact with.

Navigation uses a fixed 3×3 grid centred on the player. All 8 adjacent tiles
are always reachable regardless of their contents. The candidates list only
determines what happens on ENTER — it does not constrain movement.

Reuses LookMode.render_cursor for the tile highlight — no duplicated draw logic.
"""
from __future__ import annotations

import pygame
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine
    from engine.display_config import DisplayConfig


class InteractionCursor:
    """
    Adjacent-tile selection cursor activated by Shift+G when 2+ candidates exist.

    Cursor position is stored as absolute world coords (_cursor_x, _cursor_y).
    Navigation wraps within the 3×3 grid around the player — every adjacent tile
    is always reachable. The player's own tile (offset 0,0) is skipped.

    candidates  — (x, y) positions with harvestable terrain or floor items
    player_x/y  — player position at time of entering cursor mode
    """

    def __init__(self) -> None:
        self.candidates:  list[tuple[int, int]] = []
        self._cursor_x:   int = 0
        self._cursor_y:   int = 0
        self.player_x:    int = 0
        self.player_y:    int = 0
        self._font_small: pygame.font.Font | None = None

    def init(self, display: "DisplayConfig") -> None:
        self._font_small = display.font_ui_small

    # ------------------------------------------------------------------ #
    #  Enter / state
    # ------------------------------------------------------------------ #

    def enter(
        self,
        candidates: list[tuple[int, int]],
        player_x: int,
        player_y: int,
    ) -> None:
        """
        Open cursor. Starts on the nearest candidate (manhattan, ties by scan order).
        If no candidates, starts on the player's own tile.
        """
        self.candidates = list(candidates)
        self.player_x   = player_x
        self.player_y   = player_y

        # Place cursor on nearest candidate by manhattan distance, scan-order tie-break
        def mdist(pos: tuple[int, int]) -> int:
            return abs(pos[0] - player_x) + abs(pos[1] - player_y)

        if self.candidates:
            best = min(self.candidates, key=mdist)
            self._cursor_x, self._cursor_y = best
        else:
            self._cursor_x, self._cursor_y = player_x, player_y  # player's own tile

    @property
    def cursor_x(self) -> int:
        return self._cursor_x

    @property
    def cursor_y(self) -> int:
        return self._cursor_y

    # ------------------------------------------------------------------ #
    #  Navigation
    # ------------------------------------------------------------------ #

    def _move(self, dx: int, dy: int) -> None:
        """
        Move cursor one step within the 3×3 grid centred on the player.
        Offsets are clamped to [-1, +1] — pressing into a boundary does nothing.
        The player's own tile (0, 0) is reachable and selectable.
        """
        ox = self._cursor_x - self.player_x
        oy = self._cursor_y - self.player_y
        self._cursor_x = self.player_x + max(-1, min(1, ox + dx))
        self._cursor_y = self.player_y + max(-1, min(1, oy + dy))

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> None:
        """
        Handle a keypress while interaction cursor is active.
        All keys consumed here — no fall-through to normal dispatch.
        """
        from engine.engine import MOVE_KEYS, GameMode

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            self._move(dx, dy)
            return

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_g):
            cx, cy = self._cursor_x, self._cursor_y
            if (cx, cy) in self.candidates:
                self._interact(engine)
                engine.mode = GameMode.LOCAL
                return
            # Not a candidate — check if it's an interactable tile (e.g. campfire)
            terrain_id    = engine._resolve_terrain_id(cx, cy)
            terrain_entry = engine.data.terrain.get(terrain_id, {})
            if terrain_entry.get("interactable"):
                self._interact(engine)
                engine.mode = GameMode.LOCAL
                return
            # Neither candidate nor interactable — contextual message, cursor stays
            self._emit_empty_message(engine, cx, cy)
            return

        if key == pygame.K_ESCAPE:
            engine.mode = GameMode.LOCAL
            return

        # All other keys silently consumed — cursor stays active.

    def _interact(self, engine: "Engine") -> None:
        """Harvest, gather, interact with, or pick up at cursor position. Spends one turn."""
        cx, cy = self._cursor_x, self._cursor_y
        acted = engine._try_harvest(cx, cy)
        if not acted:
            acted = engine._try_gather(cx, cy)
        if not acted:
            acted = engine._dispatch_interactable(cx, cy)
        if not acted:
            items = engine._items_at(cx, cy)
            if items:
                inv = getattr(engine.player, "inventory", None)
                if inv:
                    engine._take_item(items[-1], inv)
                    acted = True
        if acted:
            engine._log_scroll = 0
            engine._advance_turn()
            while engine._move_debt >= 1.0:
                engine._move_debt -= 1.0
                engine._advance_turn()

    def _emit_empty_message(self, engine: "Engine", x: int, y: int) -> None:
        """
        Log a contextual message for an empty tile. No turn spent.
        Uses the terrain description if present; falls back to walkability.
        """
        terrain_id    = engine._resolve_terrain_id(x, y)
        terrain_entry = engine.data.terrain.get(terrain_id, {})
        desc          = terrain_entry.get("description", "")
        if desc:
            engine.log.add(desc, MSG_DEFAULT)
        elif terrain_entry.get("walkable", True):
            engine.log.add("Nothing to take here.", MSG_DEFAULT)
        else:
            engine.log.add("You cannot reach that.", MSG_DEFAULT)

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #

    def render(
        self,
        screen:   pygame.Surface,
        engine:   "Engine",
        cam_x:    int,
        cam_y:    int,
        viewport: pygame.Rect,
    ) -> None:
        """Draw cursor highlight (via look_mode) and one-line interaction hint."""
        engine.look_mode.render_cursor(
            screen, engine, cam_x, cam_y,
            x=self._cursor_x, y=self._cursor_y,
        )
        cx, cy = self._cursor_x, self._cursor_y
        on_candidate = (cx, cy) in self.candidates
        if not on_candidate:
            terrain_id    = engine._resolve_terrain_id(cx, cy)
            terrain_entry = engine.data.terrain.get(terrain_id, {})
            on_candidate  = bool(terrain_entry.get("interactable"))
        self._render_hint(screen, viewport, on_candidate)

    def _render_hint(
        self,
        screen:       pygame.Surface,
        viewport:     pygame.Rect,
        on_candidate: bool,
    ) -> None:
        if not self._font_small:
            return
        hint = "[ ENTER ] interact     [ ESC ] cancel" if on_candidate else "[ ESC ] cancel"
        text_surf = self._font_small.render(hint, True, UI_TEXT_MID)
        x = viewport.left + (viewport.width - text_surf.get_width()) // 2
        y = viewport.bottom - text_surf.get_height() - 10
        bg_w = text_surf.get_width() + 10
        bg_h = text_surf.get_height() + 6
        bg_x = x - 5
        bg_y = y - 3
        bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        bg_surf.fill((*VOID_BLACK, 210))
        screen.blit(bg_surf,   (bg_x, bg_y))
        screen.blit(text_surf, (x, y))
