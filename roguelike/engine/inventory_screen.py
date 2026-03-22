# engine/inventory_screen.py
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
from config import UI_PANEL_INSET

if TYPE_CHECKING:
    from engine.engine import Engine
    from entities.item import Item
    from engine.display_config import DisplayConfig


# ------------------------------------------------------------------ #
#  Module-level helpers
# ------------------------------------------------------------------ #

def _render_stat(
    surf: pygame.Surface,
    font: pygame.font.Font,
    label: str,
    value: str,
    x: int,
    y: int,
    label_col: tuple,
    val_col: tuple,
    label_w: int = 100,
) -> None:
    lbl = font.render(f"{label}:", True, label_col)
    val = font.render(str(value),  True, val_col)
    surf.blit(lbl, (x, y))
    surf.blit(val, (x + label_w, y))


def _draw_pips(
    surf: pygame.Surface,
    x: int, y: int,
    filled: int, total: int,
    col_filled: tuple, col_empty: tuple,
) -> None:
    r, gap = max(1, 4), 11
    for i in range(total):
        cx, cy = x + i * gap + r, y + r
        if i < filled:
            pygame.draw.circle(surf, col_filled, (cx, cy), r)
        else:
            pygame.draw.circle(surf, col_empty,  (cx, cy), r)
            pygame.draw.circle(surf, col_filled, (cx, cy), r, 1)


class InventoryScreen:
    """
    Inventory overlay. Press I to open.
    Shows carried items with weight.
    Use / Drop / Examine from here.
    """

    BG       = (12, 10, 18)
    BORDER   = (100, 80, 140)
    TITLE    = (200, 180, 255)
    TEXT     = (180, 165, 145)
    DIM      = (110, 100, 90)
    SELECTED = (255, 220, 100)
    STAT     = (140, 200, 140)
    LABEL_C  = (68,  99, 116)
    VALUE_C  = (227, 245, 241)

    def __init__(self) -> None:
        self.open:           bool         = False
        self.selected:       int          = 0
        self._examining:     "Item | None" = None
        self._font_title:    pygame.font.Font | None = None
        self._font_normal:   pygame.font.Font | None = None
        self._font_small:    pygame.font.Font | None = None
        self._font_large:    pygame.font.Font | None = None
        self._font_bold:     pygame.font.Font | None = None
        self._row_height:    int          = 20

    def init(self, display: "DisplayConfig") -> None:
        self._font_title  = getattr(display, "font_ui_bold",       None) or display.font_ui_normal
        self._font_normal = display.font_ui_normal
        self._font_small  = display.font_ui_small
        self._font_large  = display.font_ui_large
        self._font_bold   = getattr(display, "font_ui_bold_large", None) or display.font_ui_large
        self._row_height  = self._font_normal.get_linesize() + 4

    def toggle(self) -> None:
        self.open      = not self.open
        self.selected  = 0
        self._examining = None

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> bool:
        """Returns True if key was consumed."""
        if not self.open:
            return False

        # If examining an item, ESC or X closes just the examine popup
        if self._examining is not None:
            if key in (pygame.K_ESCAPE, pygame.K_x):
                self._examining = None
            return True

        inv = getattr(engine.player, "inventory", None)
        if not inv:
            return False

        items = inv.items

        if key in (pygame.K_ESCAPE, pygame.K_i):
            self.open = False
            return True

        if key in (pygame.K_UP, pygame.K_k, pygame.K_KP8):
            self.selected = max(0, self.selected - 1)
            return True

        if key in (pygame.K_DOWN, pygame.K_j, pygame.K_KP2):
            self.selected = min(len(items) - 1, self.selected + 1)
            return True

        if key == pygame.K_x:
            if 0 <= self.selected < len(items):
                self._examining = items[self.selected]
            return True

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_u):
            if 0 <= self.selected < len(items):
                item     = items[self.selected]
                consumed = engine.item_system.use(item, engine)
                if consumed:
                    inv.remove(item)
                    self.selected = min(
                        self.selected,
                        max(0, len(inv.items) - 1)
                    )
                engine._advance_turn()
            return True

        if key == pygame.K_d:
            if 0 <= self.selected < len(items):
                item = items[self.selected]
                inv.remove(item)
                item.x = engine.player.x
                item.y = engine.player.y
                engine.entities.append(item)
                engine.log.add(
                    f"You drop the {item.name}.",
                    (160, 150, 130),
                )
                self.selected = min(
                    self.selected,
                    max(0, len(inv.items) - 1)
                )
                engine._advance_turn()
            return True

        return True

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #

    def render(
        self,
        surface: pygame.Surface,
        engine:  "Engine",
    ) -> None:
        if not self.open or not self._font_normal:
            return
        try:
            self._render_inner(surface, engine)
        except Exception:
            import traceback
            traceback.print_exc()
            self.open = False

    def _render_inner(
        self,
        surface: pygame.Surface,
        engine:  "Engine",
    ) -> None:
        inv = getattr(engine.player, "inventory", None)
        if not inv:
            return

        sw = surface.get_width()
        sh = surface.get_height()
        pw = min(500, sw - 80)
        ph = min(400, sh - 80)
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        engine.ui_registry.draw_panel(
            popup, pygame.Rect(0, 0, pw, ph), "weathered_temple",
            tint_color=self.BORDER, fill_color=self.BG, fill_alpha=245,
        )

        y = UI_PANEL_INSET

        # Title
        title = self._font_title.render("INVENTORY", True, self.TITLE)
        popup.blit(title, (UI_PANEL_INSET, y))

        # Weight
        weight_str = f"{inv.current_weight:.1f} / {inv.capacity:.1f} kg"
        ws = self._font_small.render(weight_str, True, self.DIM)
        popup.blit(ws, (pw - ws.get_width() - UI_PANEL_INSET, y + 2))
        y += 22

        pygame.draw.line(popup, self.BORDER,
                         (UI_PANEL_INSET, y), (pw - UI_PANEL_INSET, y), 1)
        y += 8

        if not inv.items:
            empty = self._font_normal.render(
                "You carry nothing.", True, self.DIM
            )
            popup.blit(empty, (UI_PANEL_INSET, y))
        else:
            for i, item in enumerate(inv.items):
                try:
                    self._render_item_row(popup, item, engine, i, y, pw)
                except Exception as e:
                    print(f"[INV] Failed to render item "
                          f"{getattr(item, 'item_id', '?')}: {e}")
                y += self._row_height
                if y > ph - self._row_height * 3:
                    break

        # Footer
        footer = self._font_small.render(
            "^ v select   Enter/U use   X examine   D drop   ESC/I close",
            True, self.DIM
        )
        footer_y = ph - UI_PANEL_INSET - footer.get_height()
        pygame.draw.line(popup, self.BORDER,
                         (UI_PANEL_INSET, footer_y - 6),
                         (pw - UI_PANEL_INSET, footer_y - 6), 1)
        popup.blit(footer, (UI_PANEL_INSET, footer_y))

        surface.blit(popup, (px, py))

        # Examine popup drawn on top if active
        if self._examining is not None:
            self._render_item_examine(surface, engine)

    def _render_item_row(
        self,
        popup: pygame.Surface,
        item:  "Item",
        engine: "Engine",
        idx:   int,
        y:     int,
        pw:    int,
    ) -> None:
        is_sel  = (idx == self.selected)
        equip   = getattr(engine.player, "equipment", None)
        equipped = equip.is_equipped(item) if equip else False

        name_color = (226, 181, 112) if equipped else self.TEXT
        color      = self.SELECTED if is_sel else name_color
        bg_col     = (40, 30, 60) if is_sel else None

        if bg_col:
            pygame.draw.rect(
                popup, bg_col,
                (UI_PANEL_INSET - 4, y - 2,
                 pw - UI_PANEL_INSET * 2 + 8, self._row_height)
            )

        # Tile glyph
        tile = getattr(item, "tile", "")
        if tile and tile in engine.registry._data:
            ch = chr(engine.registry.char(tile))
            fg = engine.registry.fg(tile)
            g  = self._font_normal.render(ch, True, fg)
            popup.blit(g, (UI_PANEL_INSET, y))

        # Name + count
        prefix   = "[E] " if equipped else "    "
        name_str = prefix + getattr(item, "name", "?")
        if getattr(item, "stackable", False) and getattr(item, "count", 1) > 1:
            name_str += f" x{item.count}"
        n = self._font_normal.render(name_str, True, color)
        popup.blit(n, (UI_PANEL_INSET + 20, y))

        # Weight
        w_str = f"{getattr(item, 'weight', 0.0):.1f}kg"
        ws2   = self._font_small.render(w_str, True, self.DIM)
        popup.blit(ws2, (pw - ws2.get_width() - UI_PANEL_INSET, y + 2))

    def _render_item_examine(
        self,
        surface: pygame.Surface,
        engine:  "Engine",
    ) -> None:
        item = self._examining
        if not item or not self._font_normal:
            return

        sw = surface.get_width()
        sh = surface.get_height()
        pw = min(520, sw - 60)
        ph = min(360, sh - 60)
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        engine.ui_registry.draw_panel(
            popup, pygame.Rect(0, 0, pw, ph), "weathered_temple",
            tint_color=self.BORDER, fill_color=self.BG, fill_alpha=250,
        )

        y = UI_PANEL_INSET

        # Title — bold large
        title_font = self._font_bold or self._font_large
        title = title_font.render(
            getattr(item, "name", "Unknown"), True, self.TITLE
        )
        popup.blit(title, (UI_PANEL_INSET, y))
        y += title.get_height() + 6

        pygame.draw.line(popup, self.BORDER,
                         (UI_PANEL_INSET, y), (pw - UI_PANEL_INSET, y), 1)
        y += 8

        # Description — word-wrapped
        desc  = getattr(item, "description", "") or "No description available."
        words = desc.split()
        lines = []
        line  = ""
        max_w = pw - UI_PANEL_INSET * 2 - 14

        for word in words:
            test = line + (" " if line else "") + word
            if self._font_normal.size(test)[0] <= max_w or not line:
                line = test
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)

        for ln in lines:
            t = self._font_normal.render(ln, True, self.TEXT)
            popup.blit(t, (UI_PANEL_INSET + 14, y))
            y += self._font_normal.get_linesize()
            if y > ph - 130:
                break

        y += 6
        pygame.draw.line(popup, (40, 50, 65),
                         (UI_PANEL_INSET, y), (pw - UI_PANEL_INSET, y), 1)
        y += 8

        # Item stats block
        item_id  = getattr(item, "item_id", "") or ""
        item_def = engine.data.items.get(item_id, {}) if item_id else {}
        category = item_def.get("category", "")
        slot     = item_def.get("slot", "")
        lh       = self._font_small.get_linesize() + 2
        x        = UI_PANEL_INSET

        if category == "weapon":
            dice    = item_def.get("damage_dice", "\u2014")
            bonus   = item_def.get("damage_bonus", 0)
            dmg_str = f"{dice}+{bonus}" if bonus else dice
            _render_stat(popup, self._font_small, "Damage", dmg_str,
                         x, y, self.LABEL_C, self.VALUE_C)
            y += lh

            slot_disp = slot.replace("_", " ").title()
            _render_stat(popup, self._font_small, "Slot", slot_disp,
                         x, y, self.LABEL_C, self.VALUE_C)
            y += lh

        elif category == "armor":
            slot_disp = slot.replace("_", " ").replace("armor ", "").title()
            _render_stat(popup, self._font_small, "Protects", slot_disp,
                         x, y, self.LABEL_C, self.VALUE_C)
            y += lh

            for layer in item_def.get("armor_layers", []):
                av   = layer.get("armor_value", 0)
                cov  = layer.get("coverage", 1.0)
                mat  = layer.get("material", "").title()
                name = layer.get("name", "layer")
                # Line 1: layer name + AV + material
                _render_stat(popup, self._font_small,
                             name, f"AV {av}  {mat}",
                             x, y, self.LABEL_C, self.VALUE_C)
                y += lh
                # Line 2: coverage bar indented under value column
                bar_x    = x + 100
                bar_w    = max(1, 80)
                bar_h    = 5
                filled   = max(0, min(int(cov * bar_w), bar_w))
                cov_pct  = int(cov * 100)
                pygame.draw.rect(popup, (30, 40, 50),    (bar_x, y, bar_w, bar_h))
                pygame.draw.rect(popup, (129, 175, 181), (bar_x, y, filled, bar_h))
                cov_s = self._font_small.render(
                    f"{cov_pct}% coverage", True, (68, 99, 116)
                )
                popup.blit(cov_s, (bar_x + bar_w + 8, y - 1))
                y += bar_h + 6

        elif category in ("tool", "consumable"):
            on_use = item_def.get("on_use", "")
            if on_use and on_use not in ("equip_toggle",):
                _render_stat(popup, self._font_small,
                             "Use", on_use.replace("_", " ").title(),
                             x, y, self.LABEL_C, self.VALUE_C)
                y += lh

        # Belt / light slot label
        if slot.startswith("belt") or slot == "light":
            slot_disp = "Belt" if slot.startswith("belt") else "Light"
            _render_stat(popup, self._font_small, "Slot", slot_disp,
                         x, y, self.LABEL_C, self.VALUE_C)
            y += lh

        # Essence — every item has one
        essence  = item_def.get("essence") or ""
        strength = float(item_def.get("essence_strength", 0.0))
        pips     = round(strength * 5)
        lbl_s    = self._font_small.render("Essence:", True, self.LABEL_C)
        popup.blit(lbl_s, (x, y))
        ess_s = self._font_small.render(essence or "\u2014", True, self.VALUE_C)
        popup.blit(ess_s, (x + 100, y))
        if pips > 0:
            _draw_pips(popup, x + 100 + ess_s.get_width() + 10, y + 2,
                       pips, 5, (129, 175, 181), (30, 35, 50))
        y += lh

        # Weight
        _render_stat(popup, self._font_small,
                     "Weight", f"{item_def.get('weight', getattr(item, 'weight', 0)):.1f} kg",
                     x, y, self.LABEL_C, self.VALUE_C)
        y += lh

        # Equipped indicator
        equip = getattr(engine.player, "equipment", None)
        if equip and equip.is_equipped(item):
            eq_s = self._font_small.render("[Equipped]", True, (226, 181, 112))
            popup.blit(eq_s, (x, y))
            y += lh

        # Footer
        pygame.draw.line(popup, (40, 50, 65),
                         (UI_PANEL_INSET, ph - 22),
                         (pw - UI_PANEL_INSET, ph - 22), 1)
        footer = self._font_small.render(
            "ESC / X to close", True, self.DIM
        )
        popup.blit(footer, (UI_PANEL_INSET, ph - 16))

        surface.blit(popup, (px, py))
