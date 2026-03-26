# engine/ui.py
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

        # --- Row 1: HP bar + time ---
        self._draw_hp_bar(surf, player, col1_x, y, 200, 14)
        time_str = world_time.status_string
        self._text(surf, time_str, col3_x, y, self.C_TEXT_DIM, self._font_tiny)
        y += line_h

        # --- Row 2: Needs + moon phase ---
        needs = getattr(player, "needs", None)
        if needs:
            hunger_str = f"Hunger: {needs.hunger_state}"
            thirst_str = f"Thirst: {needs.thirst_state}"
            self._text(surf, hunger_str, col1_x, y, self.C_HUNGER, self._font_tiny)
            self._text(surf, thirst_str, col2_x, y, self.C_THIRST, self._font_tiny)
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

    def _draw_hp_bar(self, surf, player, x, y, width, height):
        fighter = getattr(player, "fighter", None)
        if not fighter:
            return

        pygame.draw.rect(surf, self.C_BAR_BG, (x, y, width, height))

        frac = fighter.hp_fraction
        if self._damage_flash > 0:
            color = TRUE_WHITE
            self._damage_flash -= 1
        elif frac > 0.3:
            color = self.C_HP_FULL
        else:
            color = self.C_HP_LOW

        fill_w = max(1, int(width * frac))
        pygame.draw.rect(surf, color, (x, y, fill_w, height))
        pygame.draw.rect(surf, self.C_BORDER, (x, y, width, height), 1)

        hp_text = f"HP {fighter.hp}/{fighter.max_hp}"
        self._text(surf, hp_text, x + 4, y + 1, self.C_TEXT, self._font_tiny)

    def notify_damage(self) -> None:
        """Call when player takes damage to trigger HP bar flash."""
        self._damage_flash = 8
