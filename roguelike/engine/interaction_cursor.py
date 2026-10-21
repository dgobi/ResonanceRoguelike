# engine/interaction_cursor.py
# UI RULES: read docs/UI_RULES.md before modifying this file.
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
        self._font_normal: pygame.font.Font | None = None
        # Multi-item selection prompt state
        self._selection_prompt: dict | None = None  # {items, selected, lx, ly}

    def init(self, display: "DisplayConfig") -> None:
        self._font_small = display.font_ui_small
        self._font_normal = display.font_ui_normal

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

        # Multi-item selection prompt intercepts all input
        if self._selection_prompt is not None:
            self._handle_selection_key(key, engine)
            return

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            self._move(dx, dy)
            return

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_g):
            cx, cy = self._cursor_x, self._cursor_y
            if (cx, cy) in self.candidates:
                self._interact(engine)
                return
            terrain_id    = engine._resolve_terrain_id(cx, cy)
            terrain_entry = engine.data.terrain.get(terrain_id, {})
            if terrain_entry.get("interactable"):
                self._interact(engine)
                return
            self._emit_empty_message(engine, cx, cy)
            return

        if key == pygame.K_ESCAPE:
            engine.mode = GameMode.LOCAL
            return

    def _interact(self, engine: "Engine") -> None:
        """Harvest, gather, interact with, or pick up at cursor position."""
        from engine.engine import GameMode
        cx, cy = self._cursor_x, self._cursor_y

        acted = engine._try_harvest(cx, cy)
        if not acted:
            acted = engine._try_gather(cx, cy)
        if not acted:
            items = engine._items_at(cx, cy)
            if items:
                if len(items) == 1:
                    _top = items[0]
                    if getattr(_top, "source_creature", None):
                        acted = engine._interactable_butcher(cx, cy)
                    else:
                        inv = getattr(engine.player, "inventory", None)
                        if inv:
                            engine._take_item(_top, inv)
                            acted = True
                else:
                    # Multiple items — open selection prompt
                    self._selection_prompt = {
                        "items": list(items),
                        "selected": 0,
                        "lx": cx, "ly": cy,
                    }
                    return  # no turn spent yet, prompt takes over
        if not acted:
            acted = engine._dispatch_interactable(cx, cy)
        if self._selection_prompt is not None:
            return  # prompt opened by interactable handler (e.g. browse_container)
        if not acted:
            _proc_layer = getattr(engine.local_map, "processing_layer", {})
            if (cx, cy) in _proc_layer:
                engine.log.add("Not ready.", WORN_STONE)
                return
        if acted:
            engine._log_scroll = 0
            engine._advance_turn()
            while engine._move_debt >= 1.0:
                engine._move_debt -= 1.0
                engine._advance_turn()
            engine.mode = GameMode.LOCAL

    def _handle_selection_key(self, key: int, engine: "Engine") -> None:
        """Handle input for multi-item selection prompt."""
        from engine.engine import GameMode
        prompt = self._selection_prompt
        if prompt is None:
            return
        items = prompt["items"]
        # Options: each item + "Take all" at the end
        n_opts = len(items) + 1

        if key in (pygame.K_UP, pygame.K_KP8):
            prompt["selected"] = max(0, prompt["selected"] - 1)
            return
        if key in (pygame.K_DOWN, pygame.K_KP2):
            prompt["selected"] = min(n_opts - 1, prompt["selected"] + 1)
            return

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            sel = prompt["selected"]
            lx, ly = prompt["lx"], prompt["ly"]
            is_container = prompt.get("source") == "container"
            self._selection_prompt = None
            if is_container:
                self._handle_container_take(sel, items, lx, ly, engine)
            elif sel < len(items):
                # Single item selected
                item = items[sel]
                if getattr(item, "source_creature", None):
                    engine._interactable_butcher(lx, ly)
                else:
                    inv = getattr(engine.player, "inventory", None)
                    if inv:
                        engine._take_item(item, inv)
            else:
                # "Take all"
                from generation.floor_object_utils import clear_floor_objects as _cfo
                inv = getattr(engine.player, "inventory", None)
                if inv:
                    _taken_names = []
                    for it in items:
                        if not getattr(it, "source_creature", None):
                            if inv.add(it):
                                _taken_names.append(getattr(it, "name", "") or "something")
                    _cfo(engine.local_map, lx, ly)
                    if _taken_names:
                        _parts = [f"the {n}" for n in _taken_names]
                        if len(_parts) == 1:
                            _list = _parts[0]
                        elif len(_parts) == 2:
                            _list = f"{_parts[0]} and {_parts[1]}"
                        else:
                            _list = ", ".join(_parts[:-1]) + f", and {_parts[-1]}"
                        engine.log.add(f"Thou takest {_list}.", WORN_STONE)
            engine._log_scroll = 0
            engine._advance_turn()
            while engine._move_debt >= 1.0:
                engine._move_debt -= 1.0
                engine._advance_turn()
            engine.mode = GameMode.LOCAL
            return

        if key == pygame.K_ESCAPE:
            self._selection_prompt = None
            return

    def _handle_container_take(
        self, sel: int, items: list, lx: int, ly: int, engine: "Engine",
    ) -> None:
        """Handle taking items from a container selection prompt."""
        from generation.floor_object_utils import take_from_container
        inv = getattr(engine.player, "inventory", None)
        if not inv:
            return
        if sel < len(items):
            item = items[sel]
            if inv.add(item):
                take_from_container(engine.local_map, lx, ly, item)
                _dname = getattr(item, "name", "") or "something"
                engine.log.add(f"Thou takest the {_dname}.", WORN_STONE)
            else:
                engine.log.add("Thou canst not carry more.", EARTH_BROWN)
        else:
            # "Take all"
            _taken_names = []
            for it in items:
                if inv.add(it):
                    take_from_container(engine.local_map, lx, ly, it)
                    _taken_names.append(getattr(it, "name", "") or "something")
            if _taken_names:
                _parts = [f"the {n}" for n in _taken_names]
                if len(_parts) == 1:
                    _list = _parts[0]
                elif len(_parts) == 2:
                    _list = f"{_parts[0]} and {_parts[1]}"
                else:
                    _list = ", ".join(_parts[:-1]) + f", and {_parts[-1]}"
                engine.log.add(f"Thou takest {_list}.", WORN_STONE)

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
        """Draw cursor highlight, interaction hint, and selection prompt if active."""
        engine.look_mode.render_cursor(
            screen, engine, cam_x, cam_y,
            x=self._cursor_x, y=self._cursor_y,
        )

        if self._selection_prompt is not None:
            self._render_selection_prompt(screen, engine, cam_x, cam_y, viewport)
            return

        cx, cy = self._cursor_x, self._cursor_y
        on_candidate = (cx, cy) in self.candidates
        if not on_candidate:
            terrain_id    = engine._resolve_terrain_id(cx, cy)
            terrain_entry = engine.data.terrain.get(terrain_id, {})
            on_candidate  = bool(terrain_entry.get("interactable"))
        self._render_hint(screen, viewport, on_candidate)

    def _render_selection_prompt(
        self,
        screen:   pygame.Surface,
        engine:   "Engine",
        cam_x:    int,
        cam_y:    int,
        viewport: pygame.Rect,
    ) -> None:
        """Draw multi-item selection prompt. Follows docs/UI_RULES.md panel contract."""
        prompt = self._selection_prompt
        if prompt is None or not self._font_small:
            return
        items = prompt["items"]
        sel   = prompt["selected"]
        fn    = self._font_small
        fh    = fn.get_linesize()
        lh    = fh + 4  # row height
        BORDER_PAD = 18  # panel contract: 12 border + 6 inner gap

        # Build option labels
        labels: list[str] = []
        for it in items:
            if getattr(it, "source_creature", None):
                labels.append("Butcher")
            else:
                labels.append(getattr(it, "name", "?"))
        labels.append("Take all")

        # Hint row reservation (UI_RULES: font_height + 8)
        HINT_ROW_H = fh + 8
        _hint_text = "[ ENTER ] select   [ ESC ] cancel"

        # Calculate content dimensions needed
        _weight_col_w = fn.size("00.0kg")[0] + 8
        _max_label_w  = max(fn.size(lb)[0] for lb in labels)
        _content_w = max(200, _max_label_w + _weight_col_w + 16,
                         fn.size(_hint_text)[0] + 8)
        _content_h = 4 + len(labels) * lh + 4 + HINT_ROW_H

        # Panel = content + border padding on all sides
        pw = _content_w + BORDER_PAD * 2
        ph = _content_h + BORDER_PAD * 2

        # Position: centre on viewport, clamped to viewport bounds
        _px = viewport.left + (viewport.width - pw) // 2
        _py = viewport.top + (viewport.height - ph) // 2
        _px = max(viewport.left + 2, min(_px, viewport.right - pw - 2))
        _py = max(viewport.top + 2, min(_py, viewport.bottom - ph - 2))

        # Draw panel with 9-slice border
        _panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        _ui_reg = getattr(engine, "ui_registry", None)
        if _ui_reg:
            _ui_reg.draw_panel(
                _panel, pygame.Rect(0, 0, pw, ph), "weathered_temple",
                tint_color=UI_BORDER, fill_color=DEEP_NOTHING, fill_alpha=250,
            )
        else:
            _panel.fill((*DEEP_NOTHING, 250))
            pygame.draw.rect(_panel, UI_BORDER, (0, 0, pw, ph), 1)

        # Content rect = panel_rect.inflate(-18, -18)
        cx = BORDER_PAD
        cy = BORDER_PAD + 4  # 4px top breathing room
        cw = pw - BORDER_PAD * 2
        cr = cx + cw  # content right edge

        # Hint row at bottom of content rect
        _hint_row_top = BORDER_PAD + _content_h - HINT_ROW_H
        pygame.draw.line(_panel, UI_BORDER, (cx, _hint_row_top - 1), (cr, _hint_row_top - 1))
        _hint_s = fn.render(_hint_text, True, UI_TEXT_DIM)
        _hint_text_y = _hint_row_top + (HINT_ROW_H - _hint_s.get_height()) // 2
        _panel.blit(_hint_s, ((pw - _hint_s.get_width()) // 2, _hint_text_y))

        # Item rows + "Take all" — all within content rect, above hint row
        for i, lb in enumerate(labels):
            _is_sel = (i == sel)
            if _is_sel:
                pygame.draw.rect(_panel, UI_PANEL_DARK,
                                 (cx, cy - 1, cw, lh))
            _col = RESONANCE_GOLD if _is_sel else WORN_STONE
            if i == len(items) and not _is_sel:
                _col = UI_TEXT_DIM
            _ls = fn.render(lb, True, _col)
            _panel.blit(_ls, (cx + 4, cy))
            # Weight column for non-corpse items
            if i < len(items):
                it = items[i]
                if not getattr(it, "source_creature", None):
                    _ws = fn.render(f"{getattr(it, 'weight', 0.0):.1f}kg", True, DEEP_EARTH)
                    _panel.blit(_ws, (cr - _ws.get_width() - 4, cy))
            cy += lh

        screen.blit(_panel, (_px, _py))

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
