# engine/ui.py
# UI RULES: read docs/UI_RULES.md before modifying this file.
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
from config import UI_PANEL_INSET, MSG_PANEL_W
from engine.palette import *

if TYPE_CHECKING:
    from engine.message_log import MessageLog
    from engine.world_time import WorldTime
    from entities.actor import Actor
    from engine.display_config import DisplayConfig
    from rendering.tile_registry import TileRegistry


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels. Returns list of lines."""
    words = text.split(' ')
    lines: list[str] = []
    current = ''
    for word in words:
        test = current + (' ' if current else '') + word
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines if lines else ['']


class UI:
    """
    Renders the UI into two regions:
      render_status()   — bottom status bar (HP, needs, corruption, time, items)
      render_messages() — right panel (message log)
    """

    # Color palette
    C_BG         = VOID_BLACK
    C_BORDER     = DEEP_EARTH
    C_TEXT       = WORN_STONE
    C_TEXT_DIM   = EARTH_BROWN
    C_HP_FULL    = FRESH_WOUND
    C_HP_LOW     = RESONANCE_GOLD
    C_BAR_BG     = BLOOD_CELLAR
    C_CORRUPT    = RESONANCE_BLOOM
    C_HUNGER     = EARTH_TONE
    C_THIRST     = STEEL_WATER

    def __init__(self, display: "DisplayConfig") -> None:
        self.display = display
        self._font_small: pygame.font.Font | None = None
        self._font_tiny:  pygame.font.Font | None = None
        self._damage_flash: int = 0
        self._context_prompt: str   = ""
        self._context_color:  tuple = STONE_BLUE

    def init(self) -> None:
        """Call after pygame.init() and display.init()."""
        self._font_small = self.display.font_ui_small
        self._font_tiny  = self.display.font_ui_tiny

    def set_context_prompt(self, text: str, color: tuple) -> None:
        self._context_prompt = text
        self._context_color  = color

    def clear_context_prompt(self) -> None:
        self._context_prompt = ""
        self._context_color  = STONE_BLUE

    def draw_context_strip(
        self,
        surface: "pygame.Surface",
        message: str,
        color:   tuple = WORN_STONE,
        sw:      int   = 0,
        sh:      int   = 0,
        strip_h: int   = 0,
        status_h: int  = 0,
    ) -> None:
        """
        Draw a single-line hint in the dedicated strip above the status bar.
        This is the canonical location for look-mode instructions, stair
        prompts, door prompts, and any transient single-line UI hint.
        """
        if not message or not self._font_small:
            return
        strip_w  = sw - (MSG_PANEL_W if sw > 0 else 0)
        strip_y  = sh - status_h - strip_h
        strip_rect = pygame.Rect(0, strip_y, strip_w, strip_h)

        bg = pygame.Surface((strip_rect.width, strip_rect.height), pygame.SRCALPHA)
        bg.fill(VOID_BLACK + (210,))
        surface.blit(bg, strip_rect.topleft)

        text = self._font_small.render(message, True, color)
        surface.blit(text, (strip_rect.x + UI_PANEL_INSET,
                            strip_rect.y + (strip_h - text.get_height()) // 2))

    # ------------------------------------------------------------------ #
    #  Status bar (bottom strip)
    # ------------------------------------------------------------------ #

    def render_status(
        self,
        screen:             pygame.Surface,
        status_rect:        pygame.Rect,
        player:             "Actor",
        world_time:         "WorldTime",
        nearby_items:       list | None = None,
        registry:           "TileRegistry | None" = None,
        resonance_exposure: float = 0.0,
        weather:            str | None = None,
        weather_color:      tuple = STONE_BLUE,
        debug_info:         str | None = None,
    ) -> None:
        """Render HP, needs, corruption, time, and nearby items into status_rect."""
        surf = pygame.Surface((status_rect.width, status_rect.height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # Top border line (fallback separator when no panel frame active)
        pygame.draw.line(surf, self.C_BORDER,
                         (0, 0), (status_rect.width, 0), 1)

        content_w = status_rect.width - UI_PANEL_INSET * 2
        col1_x = UI_PANEL_INSET
        col2_x = UI_PANEL_INSET + content_w // 3
        col3_x = UI_PANEL_INSET + content_w * 2 // 3
        line_h = self._font_tiny.get_linesize() if self._font_tiny else 16
        y      = UI_PANEL_INSET

        # --- Row 1: HP bar + EXP bar + time ---
        _HP_BAR_W  = 200
        _EXP_BAR_W = 110
        _BAR_H     = 14
        self._draw_hp_bar(surf, player, col1_x, y, _HP_BAR_W, _BAR_H)
        self._draw_exp_bar(surf, player,
                           col1_x + _HP_BAR_W + 12, y, _EXP_BAR_W, _BAR_H)
        time_str = world_time.status_string
        self._text(surf, time_str, col3_x, y, self.C_TEXT_DIM, self._font_tiny)
        y += line_h

        # --- Row 2: Needs bars + AV + moon phase ---
        needs = getattr(player, "needs", None)
        if needs:
            _BAR_W = 60
            _BAR_H = 8
            _bar_y = y + (line_h - _BAR_H) // 2

            # Hunger bar — colour shifts with severity
            if needs.hunger >= 0.80:
                h_color = FRESH_WOUND
            elif needs.hunger >= 0.30:
                h_color = OLD_GOLD
            else:
                h_color = EARTH_TONE
            h_label = needs.hunger_state
            self._text(surf, h_label, col1_x, y, h_color, self._font_tiny)
            h_label_w = self._font_tiny.size(h_label)[0] + 4 if self._font_tiny else 50
            h_frac = 1.0 - needs.hunger  # full bar = not hungry
            self._draw_need_bar(surf, col1_x + h_label_w, _bar_y, _BAR_W, _BAR_H,
                                h_frac, h_color)

            # Thirst bar — colour shifts with severity
            if needs.thirst >= 0.81:
                t_color = FRESH_WOUND
            elif needs.thirst >= 0.25:
                t_color = OLD_GOLD
            else:
                t_color = STEEL_WATER
            t_label = needs.thirst_state
            self._text(surf, t_label, col2_x, y, t_color, self._font_tiny)
            t_label_w = self._font_tiny.size(t_label)[0] + 4 if self._font_tiny else 50
            t_frac = 1.0 - needs.thirst
            self._draw_need_bar(surf, col2_x + t_label_w, _bar_y, _BAR_W, _BAR_H,
                                t_frac, t_color)
        fighter = getattr(player, "fighter", None)
        if fighter:
            av = getattr(fighter, "effective_av", 0)
            av_str = f"AV:{av}"
            av_x = col3_x - (self._font_tiny.size(av_str)[0] + 6) if self._font_tiny else col3_x
            self._text(surf, av_str, av_x, y, self.C_TEXT_DIM, self._font_tiny)
        moon_str = world_time.moon_string
        self._text(surf, moon_str, col3_x, y, self.C_TEXT_DIM, self._font_tiny)
        y += line_h

        # --- Row 3: Corruption (always) + chilled + weather ---
        corrupt = getattr(player, "corruption", None)
        c_str = f"Corruption: {corrupt.state}" if corrupt else "Corruption: none"
        self._text(surf, c_str, col1_x, y, self.C_CORRUPT, self._font_tiny)

        chilled = getattr(player, "chilled_turns", 0)
        if chilled > 0:
            self._text(surf, "Chilled", col2_x, y, SLATE_MID, self._font_tiny)

        if weather:
            self._text(surf, weather, col3_x, y, weather_color, self._font_tiny)

        y += line_h

        # --- Row 4: Resonance bar (bottom-left) + nearby items (after) ---
        res_end_x = col1_x   # track where resonance bar ends for item placement
        if self._font_tiny:
            # Color transitions: slate_mid → mist_blue → dusty_rose → blood_rose
            if resonance_exposure >= 0.85:
                bar_color = BLOOD_STONE    # blood_rose
            elif resonance_exposure >= 0.65:
                bar_color = DRIED_BLOOD     # blood_mid
            elif resonance_exposure >= 0.45:
                bar_color = DUSTY_ROSE    # dusty_rose
            elif resonance_exposure >= 0.25:
                bar_color = SLATE_MID  # mist_blue
            else:
                bar_color = STONE_BLUE    # slate_mid

            if resonance_exposure > 0.05:
                label_s = self._font_tiny.render("resonance", True, SLATE_DARK)
                surf.blit(label_s, (col1_x, y))
                bar_x   = col1_x + label_s.get_width() + 6
                bar_w   = 80
                bar_h   = 4
                bar_y   = y + (line_h - bar_h) // 2
                filled  = max(1, min(bar_w, int(resonance_exposure * bar_w)))
                pygame.draw.rect(surf, MIDNIGHT_DEEP, (bar_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(surf, bar_color,    (bar_x, bar_y, filled, bar_h))
                res_end_x = bar_x + bar_w + 14

        if nearby_items and self._font_tiny:
            glyph_w = self._font_tiny.size("@")[0] + 4   # approximate glyph cell
            gap     = 14                                   # px between items
            item_x  = max(res_end_x, col2_x)
            limit_x = status_rect.width - UI_PANEL_INSET
            for item in nearby_items:
                name_surf = self._font_tiny.render(item.name, True, VERDANT_MID)
                total_w   = glyph_w + name_surf.get_width() + gap
                if item_x + total_w > limit_x:
                    break   # no room — omit silently, no ellipsis
                if registry and item.tile in registry._data:
                    ch = chr(registry.char(item.tile))
                    fg = registry.fg(item.tile)
                    g  = self._font_tiny.render(ch, True, fg)
                    surf.blit(g, (item_x, y))
                surf.blit(name_surf, (item_x + glyph_w, y))
                item_x += total_w

        # --- Moveset HUD (bottom-left, above resonance if present) ---
        _movesets = getattr(self, "_engine_movesets", [])
        _ms_cds = getattr(self, "_engine_moveset_cooldowns", {})
        if _movesets and self._font_tiny:
            _ms_y = status_rect.height - 4 - self._font_tiny.get_linesize() * 2
            _essence_colors = {
                "Dissolution": CORRUPTION_COLOUR, "Binding": SPIRIT_BLUE,
                "Severance": OLD_GOLD, "Revelation": RESONANCE_HIGH,
            }
            _ess = getattr(self, "_engine_weapon_essence", "")
            _active_c = _essence_colors.get(_ess, VERDANT_MID)
            for ms in _movesets:
                key_label = ms.get("key", "?")
                name = ms.get("name", "?")
                cd = _ms_cds.get(ms.get("id", ""), 0)
                if cd > 0:
                    txt = f"[{key_label}] {name} ({cd})"
                    col = UI_TEXT_DIM
                else:
                    txt = f"[{key_label}] {name}"
                    col = _active_c
                _ms_s = self._font_tiny.render(txt, True, col)
                surf.blit(_ms_s, (col1_x, _ms_y))
                _ms_y += self._font_tiny.get_linesize()

        # --- Sprint slot (bottom-right): badge when active, hint when available ---
        import math as _ui_math
        _sprint_r = getattr(self, "_engine_sprint_turns", 0)
        _sprint_max = getattr(self, "_engine_sprint_max", 8)
        _sprint_cd = getattr(self, "_engine_sprint_cooldown", 0)
        _sprint_key_id = getattr(self, "_engine_sprint_key", None)

        if _sprint_r > 0 and self._font_tiny:
            # Active: pulsing pip badge
            _ticks_ms = pygame.time.get_ticks()
            _pulse = 0.85 + 0.15 * _ui_math.sin(_ticks_ms / 1000.0 * _ui_math.pi * 2)
            _pr, _pg, _pb = RESONANCE_LOW
            _pc = (min(255, int(_pr * _pulse)),
                   min(255, int(_pg * _pulse)),
                   min(255, int(_pb * _pulse)))

            _label_s = self._font_tiny.render("SPRINT", True, _pc)
            _pip_str = "●" * _sprint_r + "○" * (_sprint_max - _sprint_r)
            _pip_s = self._font_tiny.render(_pip_str, True, _pc)

            _badge_w = max(_label_s.get_width(), _pip_s.get_width()) + 12
            _badge_h = _label_s.get_height() + _pip_s.get_height() + 8
            _badge_x = status_rect.width - _badge_w - UI_PANEL_INSET
            _badge_y = status_rect.height - _badge_h - 4

            _badge_rect = pygame.Rect(_badge_x, _badge_y, _badge_w, _badge_h)
            pygame.draw.rect(surf, UI_PANEL_DARK, _badge_rect)
            pygame.draw.rect(surf, _pc, _badge_rect, 1)

            surf.blit(_label_s, (_badge_x + (_badge_w - _label_s.get_width()) // 2,
                                 _badge_y + 3))
            surf.blit(_pip_s, (_badge_x + (_badge_w - _pip_s.get_width()) // 2,
                               _badge_y + 3 + _label_s.get_height() + 2))

        elif _sprint_cd == 0 and _sprint_r == 0 and self._font_tiny and _sprint_key_id is not None:
            # Available: show keybind hint, right-aligned
            _key_name = pygame.key.name(_sprint_key_id)
            _hint_str = f"shift-{_key_name}: sprint"
            _hint_s = self._font_tiny.render(_hint_str, True, UI_TEXT_DIM)
            _hint_x = status_rect.width - _hint_s.get_width() - UI_PANEL_INSET
            _hint_y = status_rect.height - _hint_s.get_height() - 4
            surf.blit(_hint_s, (_hint_x, _hint_y))
        # On cooldown (cd > 0, not active): nothing shown — cooldown is silent

        # --- Debug info line (bottom-right, only when DEBUG_MODE) ---
        if debug_info and self._font_tiny:
            di = self._font_tiny.render(debug_info, True, OLD_GROWTH)
            surf.blit(di, (status_rect.width - di.get_width() - UI_PANEL_INSET,
                           status_rect.height - di.get_height() - 4))

        screen.blit(surf, (status_rect.x, status_rect.y))

    # ------------------------------------------------------------------ #
    #  Message panel (right column)
    # ------------------------------------------------------------------ #

    def render_messages(
        self,
        screen:        pygame.Surface,
        panel_rect:    pygame.Rect,
        log:           "MessageLog",
        scroll_offset: int = 0,
    ) -> None:
        """Render the message log into the right-side panel."""
        surf = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # Left border line (fallback separator when no panel frame active)
        pygame.draw.line(surf, self.C_BORDER,
                         (0, 0), (0, panel_rect.height), 1)

        line_h    = self._font_tiny.get_linesize() if self._font_tiny else 14
        max_width = panel_rect.width - UI_PANEL_INSET * 2
        messages  = log.recent(60)   # generous upper bound; clip rect handles overflow

        # Wrap each message into lines; collect newest-first for bottom-to-top layout
        groups: list[tuple[list[str], tuple[int, int, int]]] = []
        for msg in reversed(messages):
            lines = _wrap_text(f"\u203a {msg.with_count()}", self._font_tiny, max_width)
            groups.append((lines, msg.color))

        # Apply scroll offset — skip newest N groups (offset from bottom)
        actual_offset = min(scroll_offset, max(0, len(groups) - 1))
        displayed = groups[actual_offset:]

        surf.set_clip(pygame.Rect(
            UI_PANEL_INSET, UI_PANEL_INSET,
            panel_rect.width  - UI_PANEL_INSET * 2,
            panel_rect.height - UI_PANEL_INSET * 2,
        ))

        # Render bottom-to-top: newest visible message anchored at bottom
        y = panel_rect.height - UI_PANEL_INSET
        for lines, color in displayed:
            y -= len(lines) * line_h
            for i, line in enumerate(lines):
                self._text(surf, line, UI_PANEL_INSET, y + i * line_h,
                           color, self._font_tiny)
            if y < UI_PANEL_INSET:
                break   # remaining messages are off the top; clip handles partial

        # "↑ N more" indicator when scrolled
        if actual_offset > 0 and self._font_tiny:
            indicator = f"\u2191 {actual_offset} more"
            ind_surf = self._font_tiny.render(indicator, True, STONE_BLUE)
            surf.blit(ind_surf, (UI_PANEL_INSET, UI_PANEL_INSET))

        surf.set_clip(None)
        screen.blit(surf, (panel_rect.x, panel_rect.y))

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _text(
        self,
        surf:  pygame.Surface,
        text:  str,
        x:     int,
        y:     int,
        color: tuple[int, int, int],
        font:  pygame.font.Font | None = None,
    ) -> None:
        f = font or self._font_small
        if f is None:
            return
        rendered = f.render(text, True, color)
        surf.blit(rendered, (x, y))

    # HP bands shown in non-debug mode (fraction threshold → label, colour)
    _HP_BANDS = [
        (0.90, "Unharmed",    WORN_STONE),
        (0.60, "Bloodied",    OLD_GOLD),
        (0.35, "Wounded",     DUSTY_ROSE),
        (0.15, "Grievous",    DRIED_BLOOD),
        (0.00, "Death's door", FRESH_WOUND),
    ]

    def _draw_bar(
        self, surf: pygame.Surface,
        x: int, y: int, width: int, height: int,
        frac: float,
        fill_color: tuple,
        label: str,
    ) -> None:
        """Draw a generic progress bar with a text label overlaid."""
        pygame.draw.rect(surf, self.C_BAR_BG, (x, y, width, height))
        fill_w = max(1, int(width * max(0.0, min(1.0, frac))))
        pygame.draw.rect(surf, fill_color, (x, y, fill_w, height))
        pygame.draw.rect(surf, self.C_BORDER, (x, y, width, height), 1)
        if label and self._font_tiny:
            self._text(surf, label, x + 4, y + 1, self.C_TEXT, self._font_tiny)

    def _draw_need_bar(
        self, surf: pygame.Surface,
        x: int, y: int, width: int, height: int,
        frac: float,
        fill_color: tuple,
    ) -> None:
        """Draw a small needs bar (no label). frac=1.0 is full/safe."""
        pygame.draw.rect(surf, self.C_BAR_BG, (x, y, width, height))
        fill_w = max(1, int(width * max(0.0, min(1.0, frac))))
        pygame.draw.rect(surf, fill_color, (x, y, fill_w, height))
        pygame.draw.rect(surf, self.C_BORDER, (x, y, width, height), 1)

    def _draw_hp_bar(self, surf, player, x, y, width, height):
        fighter = getattr(player, "fighter", None)
        if not fighter:
            return
        from config import DEBUG_MODE as _DM

        frac = fighter.hp_fraction
        if self._damage_flash > 0:
            color = TRUE_WHITE
            self._damage_flash -= 1
        elif frac > 0.3:
            color = self.C_HP_FULL
        else:
            color = self.C_HP_LOW

        if _DM:
            label = f"HP {fighter.hp}/{fighter.max_hp}"
        else:
            label = next(
                (lbl for thr, lbl, _ in self._HP_BANDS if frac >= thr),
                "Death's door",
            )

        self._draw_bar(surf, x, y, width, height, frac, color, label)

    def _draw_exp_bar(self, surf, player, x, y, width, height):
        lv = getattr(player, "level", None)
        if not lv:
            return
        frac = lv.exp / lv.exp_to_next if lv.exp_to_next > 0 else 0.0
        label = f"Lv{lv.level}"
        self._draw_bar(surf, x, y, width, height, frac, RESONANCE_GOLD, label)

    def notify_damage(self) -> None:
        """Call when player takes damage to trigger HP bar flash."""
        self._damage_flash = 8
