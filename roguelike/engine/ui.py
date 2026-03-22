# engine/ui.py
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
from config import UI_PANEL_INSET

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
    C_BG         = (15,  12,  10)
    C_BORDER     = (80,  70,  55)
    C_TEXT       = (200, 190, 165)
    C_TEXT_DIM   = (100, 90,  75)
    C_HP_FULL    = (180, 40,  40)
    C_HP_LOW     = (220, 180, 20)
    C_BAR_BG     = (40,  20,  20)
    C_CORRUPT    = (140, 60,  200)
    C_HUNGER     = (180, 130, 50)
    C_THIRST     = (60,  130, 180)

    def __init__(self, display: "DisplayConfig") -> None:
        self.display = display
        self._font_small: pygame.font.Font | None = None
        self._font_tiny:  pygame.font.Font | None = None
        self._damage_flash: int = 0
        self._context_prompt: str   = ""
        self._context_color:  tuple = (99, 120, 140)

    def init(self) -> None:
        """Call after pygame.init() and display.init()."""
        self._font_small = self.display.font_ui_small
        self._font_tiny  = self.display.font_ui_tiny

    def set_context_prompt(self, text: str, color: tuple) -> None:
        self._context_prompt = text
        self._context_color  = color

    def clear_context_prompt(self) -> None:
        self._context_prompt = ""
        self._context_color  = (99, 120, 140)

    # ------------------------------------------------------------------ #
    #  Status bar (bottom strip)
    # ------------------------------------------------------------------ #

    def render_status(
        self,
        screen:       pygame.Surface,
        status_rect:  pygame.Rect,
        player:       "Actor",
        world_time:   "WorldTime",
        nearby_items: list | None = None,
        registry:     "TileRegistry | None" = None,
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
        line_h = 16
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

        # --- Row 3: Corruption + nearby items ---
        corrupt = getattr(player, "corruption", None)
        if corrupt:
            c_str = f"Corruption: {corrupt.state}"
            self._text(surf, c_str, col1_x, y, self.C_CORRUPT, self._font_tiny)

        if nearby_items and self._font_tiny:
            glyph_w  = self._font_tiny.size("@")[0] + 4   # approximate glyph cell
            gap      = 14                                   # px between items
            item_x   = col2_x
            limit_x  = UI_PANEL_INSET + content_w          # right content edge
            for item in nearby_items:
                name_surf = self._font_tiny.render(item.name, True, (140, 160, 130))
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

        # --- Context prompt (fixed bottom strip) ---
        if self._context_prompt and self._font_tiny:
            line_h_cp  = self._font_tiny.get_linesize()
            prompt_y   = status_rect.height - UI_PANEL_INSET - line_h_cp
            self._text(surf, self._context_prompt, col1_x, prompt_y,
                       self._context_color, self._font_tiny)

        screen.blit(surf, (status_rect.x, status_rect.y))

    # ------------------------------------------------------------------ #
    #  Message panel (right column)
    # ------------------------------------------------------------------ #

    def render_messages(
        self,
        screen:     pygame.Surface,
        panel_rect: pygame.Rect,
        log:        "MessageLog",
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

        surf.set_clip(pygame.Rect(
            UI_PANEL_INSET, UI_PANEL_INSET,
            panel_rect.width  - UI_PANEL_INSET * 2,
            panel_rect.height - UI_PANEL_INSET * 2,
        ))

        # Render bottom-to-top: newest message anchored at bottom
        y = panel_rect.height - UI_PANEL_INSET
        for lines, color in groups:
            y -= len(lines) * line_h
            for i, line in enumerate(lines):
                self._text(surf, line, UI_PANEL_INSET, y + i * line_h,
                           color, self._font_tiny)
            if y < UI_PANEL_INSET:
                break   # remaining messages are off the top; clip handles partial

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
            color = (255, 255, 255)
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
