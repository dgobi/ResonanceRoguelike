# engine/health_screen.py
from __future__ import annotations
import pygame
from config import UI_PANEL_INSET, DEBUG_MODE
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine
    from engine.display_config import DisplayConfig


# ------------------------------------------------------------------ #
#  Bearing table — matches inventory_screen._BEARINGS
# ------------------------------------------------------------------ #
_BEARINGS: list[tuple[float, str, tuple]] = [
    (0.99, "Unmarked",      FROST_WHITE),
    (0.75, "Lightly Worn",  BONE_PALE),
    (0.50, "Worn",          OLD_GOLD),
    (0.30, "Heavily Worn",  DUSTY_ROSE),
    (0.15, "Damaged",       DRIED_BLOOD),
    (0.05, "Badly Damaged", BLOOD_STONE),
    (0.00, "Undone",        FRESH_WOUND),
]


def _bearing(frac: float) -> tuple[str, tuple]:
    for thresh, label, col in _BEARINGS:
        if frac >= thresh:
            return label, col
    return "Undone", FRESH_WOUND


# ------------------------------------------------------------------ #
#  Condition descriptions (in-world voice)
# ------------------------------------------------------------------ #
_CONDITION_DESCS: dict[str, str] = {
    "Hunger":     "The body consumes itself. What remains of you is less than what began the day.",
    "Hunger.Critical": "A hollow pressure behind the sternum. Each movement costs something that does not return.",
    "Thirst":     "The throat closes. Thought becomes imprecise. Water is the first thing the world took from you.",
    "Thirst.Critical": "The veins run slow. The eyes cannot focus. You are becoming still.",
    "Chilled":    "Cold has entered the joints. Movement is slower than it was. The chill is patient.",
    "Sickened":   "Something from the crow's touch persists in the blood. Hunger and thirst advance faster than they should.",
    "Corruption": "The discharge has left a mark. The body is remembering something it was never meant to know.",
}


class HealthScreen:
    """
    Full-screen health overlay. H opens/closes.
    Section 1: Status — bearing, HP bar, player condition summary.
    Section 2: Active Conditions — each active effect with description.
    """

    BG      = DEEP_NOTHING
    BORDER  = VOID_PURPLE
    TITLE   = SPIRIT_BLUE
    TEXT    = WORN_STONE
    DIM     = SLATE_DARK
    LABEL_C = STONE_BLUE
    SEP_C   = SLATE_DARK

    def __init__(self) -> None:
        self.open:          bool = False
        self._font_title:   pygame.font.Font | None = None
        self._font_normal:  pygame.font.Font | None = None
        self._font_small:   pygame.font.Font | None = None
        self._font_bold:    pygame.font.Font | None = None

    def init(self, display: "DisplayConfig") -> None:
        self._font_title  = getattr(display, "font_ui_bold",      None) or display.font_ui_normal
        self._font_normal = display.font_ui_normal
        self._font_small  = display.font_ui_small
        self._font_bold   = getattr(display, "font_ui_bold_large", None) or display.font_ui_large

    def toggle(self) -> None:
        self.open = not self.open

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> bool:
        if not self.open:
            return False
        if key in (pygame.K_h, pygame.K_ESCAPE, pygame.K_k):
            self.open = False
            return True
        return True

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #

    def render(self, surface: pygame.Surface, engine: "Engine") -> None:
        if not self.open or not self._font_normal:
            return
        try:
            self._render_inner(surface, engine)
        except Exception:
            import traceback
            traceback.print_exc()
            self.open = False

    def _render_inner(self, surface: pygame.Surface, engine: "Engine") -> None:
        sw, sh = surface.get_width(), surface.get_height()
        pw = min(680, sw - 40)
        ph = min(520, sh - 40)
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        engine.ui_registry.draw_panel(
            popup, pygame.Rect(0, 0, pw, ph), "weathered_temple",
            tint_color=self.BORDER, fill_color=self.BG, fill_alpha=252,
        )

        PAD = UI_PANEL_INSET
        lh  = self._font_small.get_linesize() + 2

        # Collect active conditions
        conditions = self._collect_conditions(engine)

        # Split at roughly 40% / 60%
        split_y = int(ph * 0.40)
        pygame.draw.line(popup, self.BORDER, (PAD, split_y), (pw - PAD, split_y), 1)

        self._draw_status(popup, engine, PAD, PAD, pw - PAD * 2, split_y - PAD, lh)
        self._draw_conditions(popup, engine, PAD, split_y + 6, pw - PAD * 2, ph - split_y - PAD, lh, conditions)

        # Footer
        footer = self._font_small.render("H / ESC  close", True, self.DIM)
        fy = ph - PAD - footer.get_height()
        pygame.draw.line(popup, self.BORDER, (PAD, fy - 4), (pw - PAD, fy - 4), 1)
        popup.blit(footer, ((pw - footer.get_width()) // 2, fy))

        surface.blit(popup, (px, py))

    # ------------------------------------------------------------------ #
    #  Section 1: Status
    # ------------------------------------------------------------------ #

    def _draw_status(
        self,
        surf: pygame.Surface,
        engine: "Engine",
        x: int, y: int, w: int, h: int,
        lh: int,
    ) -> None:
        player  = engine.player
        fighter = getattr(player, "fighter", None)
        show_hp = getattr(player, "true_sight", False) or DEBUG_MODE

        title = self._font_title.render("STATUS", True, self.TITLE)
        surf.blit(title, (x, y))
        y += title.get_height() + 6

        if not fighter:
            surf.blit(self._font_small.render("No body.", True, self.DIM), (x, y))
            return

        frac = fighter.hp_fraction
        label, col = _bearing(frac)

        # Bearing label + optional true HP
        brng_s = self._font_normal.render(label, True, col)
        surf.blit(brng_s, (x, y))
        if show_hp:
            hp_s = self._font_small.render(
                f"  {fighter.hp} / {fighter.max_hp}", True, self.LABEL_C
            )
            surf.blit(hp_s, (x + brng_s.get_width(), y + (brng_s.get_height() - hp_s.get_height()) // 2))
        y += brng_s.get_height() + 6

        # HP bar — full width
        bar_h = 6
        bar_w = w
        filled = max(0, int(frac * bar_w))
        # Bar colour transitions: green → yellow → red
        if frac > 0.5:
            bar_col = LIFE_GREEN
        elif frac > 0.25:
            bar_col = OLD_GOLD
        else:
            bar_col = FRESH_WOUND
        pygame.draw.rect(surf, MIDNIGHT_DEEP, (x, y, bar_w, bar_h))
        pygame.draw.rect(surf, bar_col,       (x, y, filled, bar_h))
        y += bar_h + 8

        # AV display
        av = getattr(fighter, "effective_av", 0)
        if av > 0:
            av_s = self._font_small.render(f"Ward  {av}", True, self.LABEL_C)
            surf.blit(av_s, (x, y))
            y += lh

    # ------------------------------------------------------------------ #
    #  Section 2: Conditions
    # ------------------------------------------------------------------ #

    def _collect_conditions(self, engine: "Engine") -> list[tuple[str, str, tuple]]:
        """Returns list of (name, description, colour) for each active condition."""
        player = engine.player
        out: list[tuple[str, str, tuple]] = []

        needs = getattr(player, "needs", None)
        if needs:
            h = needs.hunger
            if h >= 0.85:
                out.append(("Hunger", _CONDITION_DESCS["Hunger.Critical"], FRESH_WOUND))
            elif h >= 0.5:
                out.append(("Hunger", _CONDITION_DESCS["Hunger"], DUSTY_ROSE))

            t = needs.thirst
            if t >= 0.85:
                out.append(("Thirst", _CONDITION_DESCS["Thirst.Critical"], FRESH_WOUND))
            elif t >= 0.5:
                out.append(("Thirst", _CONDITION_DESCS["Thirst"], STONE_BLUE))

        chilled = getattr(player, "chilled_turns", 0)
        if chilled > 0:
            out.append(("Chilled", _CONDITION_DESCS["Chilled"], SLATE_MID))

        sickness = getattr(player, "_sickness_turns", 0)
        if sickness > 0:
            out.append(("Sickened", _CONDITION_DESCS["Sickened"], DUSTY_ROSE))

        corruption = getattr(engine, "corruption", 0.0)
        if corruption >= 0.15:
            out.append(("Corruption", _CONDITION_DESCS["Corruption"], DEEP_PURPLE))

        return out

    def _draw_conditions(
        self,
        surf: pygame.Surface,
        engine: "Engine",
        x: int, y: int, w: int, h: int,
        lh: int,
        conditions: list[tuple[str, str, tuple]],
    ) -> None:
        max_y = y + h - lh * 2

        title = self._font_title.render("ACTIVE CONDITIONS", True, self.TITLE)
        surf.blit(title, (x, y))
        y += title.get_height() + 6

        if not conditions:
            none_s = self._font_small.render("Unmarked.", True, self.DIM)
            surf.blit(none_s, (x, y))
            return

        for name, desc, col in conditions:
            if y >= max_y:
                break

            nm_s = self._font_normal.render(name, True, col)
            surf.blit(nm_s, (x, y))
            y += nm_s.get_height() + 2

            # Wrap description
            words = desc.split()
            line  = ""
            max_w = w - 8
            for word in words:
                test = line + (" " if line else "") + word
                if self._font_small.size(test)[0] <= max_w or not line:
                    line = test
                else:
                    if y < max_y:
                        ds = self._font_small.render(line, True, self.TEXT)
                        surf.blit(ds, (x + 4, y))
                        y += lh
                    line = word
            if line and y < max_y:
                ds = self._font_small.render(line, True, self.TEXT)
                surf.blit(ds, (x + 4, y))
                y += lh

            y += 6
