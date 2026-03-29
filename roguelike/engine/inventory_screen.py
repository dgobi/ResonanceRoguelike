# engine/inventory_screen.py
# UI RULES: read docs/UI_RULES.md before modifying this file.
from __future__ import annotations
import pygame
from config import UI_PANEL_INSET, DEBUG_MODE
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine
    from entities.item import Item
    from engine.display_config import DisplayConfig


# ------------------------------------------------------------------ #
#  Palette constants (Punolite Plus)
# ------------------------------------------------------------------ #
_NEAR_WHITE   = FROST_WHITE
_PALE_YELLOW  = BONE_PALE
_OLD_GOLD     = OLD_GOLD
_DUSTY_ROSE   = DUSTY_ROSE
_BLOOD_MID    = DRIED_BLOOD
_BLOOD_ROSE   = BLOOD_STONE
_MIST_BLUE    = SLATE_MID
_SLATE_MID    = STONE_BLUE
_SLATE_DARK   = SLATE_DARK


# ------------------------------------------------------------------ #
#  Health bearing — per palette spec
# ------------------------------------------------------------------ #

_BEARINGS: list[tuple[float, str, tuple]] = [
    (0.99, "Unmarked",      _NEAR_WHITE),
    (0.75, "Lightly Worn",  _PALE_YELLOW),
    (0.50, "Worn",          _OLD_GOLD),
    (0.30, "Heavily Worn",  _DUSTY_ROSE),
    (0.15, "Damaged",       _BLOOD_MID),
    (0.05, "Badly Damaged", _BLOOD_ROSE),
    (0.00, "Undone",        FRESH_WOUND),
]


def _bearing(frac: float) -> tuple[str, tuple]:
    for thresh, label, col in _BEARINGS:
        if frac >= thresh:
            return label, col
    return "Undone", FRESH_WOUND


# ------------------------------------------------------------------ #
#  Equipment slot display order
# ------------------------------------------------------------------ #

_EQUIP_SLOT_DISPLAY: list[tuple[str, str | None]] = [
    ("Head",         "armor_head"),
    ("Torso",        "armor_torso"),
    ("Arms",         "armor_arms"),
    ("Legs",         "armor_legs"),
    ("Main Hand",    "weapon"),
    ("Off Hand",     "offhand"),
    ("Belt",         "belt_1"),
    ("Belt",         "belt_2"),
    ("Belt",         "belt_3"),
    ("Light",        "light"),
    # Section header — slot_id = None means draw as label, not a slot row
    ("TALISMANS",    None),
    ("Talisman I",   "talisman_1"),
    ("Talisman II",  "talisman_2"),
    ("Talisman III", "talisman_3"),
]


# ------------------------------------------------------------------ #
#  Item category helpers
# ------------------------------------------------------------------ #

_CATEGORIES = [
    "Weapons", "Armour & Shields", "Light Sources", "Consumables",
    "Preparations", "Components", "Tools", "Miscellaneous",
]

_CAT_MAP: dict[str, str] = {
    "weapon":      "Weapons",
    "shield":      "Armour & Shields",
    "armor":       "Armour & Shields",
    "consumable":  "Consumables",
    "preparation": "Preparations",
    "component":   "Components",
    "butchery":    "Components",
    "tool":        "Tools",
    "talisman":    "Miscellaneous",
    "document":    "Miscellaneous",
    "text":        "Miscellaneous",
}


def _item_category(item: "Item", engine: "Engine") -> str:
    item_id  = getattr(item, "item_id", "") or ""
    item_def = engine.data.items.get(item_id, {}) if item_id else {}
    raw = item_def.get("category", "")
    if getattr(item, "on_use", "") == "read" or raw in ("document", "text"):
        return "Miscellaneous"
    if item_def.get("slot") == "light":
        return "Light Sources"
    return _CAT_MAP.get(raw, "Miscellaneous")


def _group_items(items: list, engine: "Engine") -> dict[str, list]:
    groups: dict[str, list] = {c: [] for c in _CATEGORIES}
    for item in items:
        groups[_item_category(item, engine)].append(item)
    return groups


def _flat_list(groups: dict[str, list], collapsed: "set[str] | None" = None) -> list:
    """
    Build flat display list with collapsible category headers.
    Tuple format: (item, is_header, label)
      - item: None for headers; first item in group for item rows
      - is_header: True for category headers
      - label: category name for headers; "" for single items; "×N" for stacks
    """
    if collapsed is None:
        collapsed = set()
    flat = []
    for cat in _CATEGORIES:
        items = groups[cat]
        if not items:
            continue
        flat.append((None, True, cat))
        if cat in collapsed:
            continue
        # Group by item_id — only stackable items merge; non-stackable always separate
        seen: dict[str, list] = {}
        for item in items:
            if getattr(item, "stackable", False):
                iid = getattr(item, "item_id", "") or str(id(item))
                seen.setdefault(iid, []).append(item)
            else:
                # Non-stackable: each item is its own entry
                flat.append((item, False, ""))
        for group in seen.values():
            first = group[0]
            count = len(group)
            label = f"x{count}" if count > 1 else ""
            flat.append((first, False, label))
    return flat


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def _render_stat(
    surf: pygame.Surface,
    font: pygame.font.Font,
    label: str,
    value: str,
    x: int, y: int,
    label_col: tuple,
    val_col: tuple,
    label_w: int = 90,
) -> None:
    lbl = font.render(f"{label}:", True, label_col)
    val = font.render(str(value),  True, val_col)
    surf.blit(lbl, (x, y))
    surf.blit(val, (x + label_w, y))


def _wrap_text(font: pygame.font.Font, text: str, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line  = ""
    for word in words:
        test = line + (" " if line else "") + word
        if font.size(test)[0] <= max_w or not line:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines



# ------------------------------------------------------------------ #
#  Main class
# ------------------------------------------------------------------ #

class InventoryScreen:
    """
    Three-panel inventory overlay.
    LEFT (28%): Equipped / Bearing  MIDDLE (28%): item list
    RIGHT (44%): item detail
    """

    BG       = DEEP_NOTHING
    BORDER   = VOID_PURPLE
    TITLE    = SPIRIT_BLUE
    TEXT     = WORN_STONE
    DIM      = _SLATE_DARK
    SELECTED = RESONANCE_GOLD
    LABEL_C  = _SLATE_MID
    VALUE_C  = _NEAR_WHITE
    HDR_C    = _NEAR_WHITE      # section header colour
    SEP_C    = _SLATE_DARK      # horizontal rules

    def __init__(self) -> None:
        self.open:           bool      = False
        self.selected:       int       = 0
        self.scroll:         int       = 0
        self._collapsed:     set[str]  = {"Miscellaneous"}
        self._font_title:    pygame.font.Font | None = None
        self._font_normal:   pygame.font.Font | None = None
        self._font_small:    pygame.font.Font | None = None
        self._font_large:    pygame.font.Font | None = None
        self._font_bold:     pygame.font.Font | None = None
        self._row_height:    int  = 20
        self._flat:          list = []

    def init(self, display: "DisplayConfig") -> None:
        self._font_title  = getattr(display, "font_ui_bold",       None) or display.font_ui_normal
        self._font_normal = display.font_ui_normal
        self._font_small  = display.font_ui_small
        self._font_large  = display.font_ui_large
        self._font_bold   = getattr(display, "font_ui_bold_large", None) or display.font_ui_large
        self._row_height  = self._font_normal.get_linesize() + 4

    def toggle(self) -> None:
        self.open     = not self.open
        self.selected = 0
        self.scroll   = 0
        self._flat    = []

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> bool:
        if not self.open:
            return False

        if key in (pygame.K_ESCAPE, pygame.K_i):
            self.open = False
            ui = getattr(engine, "ui", None)
            if ui:
                ui.clear_context_prompt()
            return True

        inv = getattr(engine.player, "inventory", None)
        if not inv:
            return False

        n = len(self._flat)

        if key in (pygame.K_UP, pygame.K_KP8):
            self.selected = max(0, self.selected - 1)
            self._clamp_scroll()
            return True

        if key in (pygame.K_DOWN, pygame.K_KP2):
            self.selected = min(max(0, n - 1), self.selected + 1)
            self._clamp_scroll()
            return True

        if key == pygame.K_PAGEUP:
            self.selected = max(0, self.selected - 6)
            self._clamp_scroll()
            return True

        if key == pygame.K_PAGEDOWN:
            self.selected = min(max(0, n - 1), self.selected + 6)
            self._clamp_scroll()
            return True

        if 0 <= self.selected < n:
            row_item, is_hdr, row_label = self._flat[self.selected]

            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
                if is_hdr:
                    cat = row_label
                    if cat in self._collapsed:
                        self._collapsed.discard(cat)
                    else:
                        self._collapsed.add(cat)
                    groups = _group_items(inv.items, engine)
                    self._flat = _flat_list(groups, self._collapsed)
                    self.selected = min(self.selected, max(0, len(self._flat) - 1))
                    self._clamp_scroll()
                else:
                    consumed = engine.item_system.use(row_item, engine)
                    if consumed:
                        inv.remove(row_item)
                        self._flat = []
                        self.selected = max(0, self.selected - 1)
                    engine._advance_turn()
                return True

            if key == pygame.K_d and not is_hdr:
                self._drop_item(row_item, inv, engine)
                return True

        return True

    def _clamp_scroll(self) -> None:
        vis = 10
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + vis:
            self.scroll = self.selected - vis + 1
        self.scroll = max(0, self.scroll)

    def _drop_item(self, item: "Item", inv, engine: "Engine") -> None:
        from generation.floor_object_utils import place_floor_object
        px, py = engine.player.x, engine.player.y
        inv.remove(item)
        item.x = px
        item.y = py
        place_floor_object(engine.local_map, px, py, item)
        self._flat = []
        self.selected = max(0, self.selected - 1)
        _dname = getattr(item, "name", "") or "something"
        engine.log.add(f"Thou settest down the {_dname}.", _SLATE_MID)
        engine._advance_turn()

    def _selected_item(self) -> "Item | None":
        if not self._flat or self.selected >= len(self._flat):
            return None
        item, is_hdr, _ = self._flat[self.selected]
        return None if is_hdr else item

    # ------------------------------------------------------------------ #
    #  Rendering — outer
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
        # Set context strip hint
        ui = getattr(engine, "ui", None)
        if ui:
            ui.set_context_prompt(
                "^/v navigate   E use/equip   D drop   I/ESC close",
                _SLATE_MID,
            )

        sw, sh = surface.get_width(), surface.get_height()
        pw = min(920, sw - 40)
        ph = min(560, sh - 40)
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        engine.ui_registry.draw_panel(
            popup, pygame.Rect(0, 0, pw, ph), "weathered_temple",
            tint_color=self.BORDER, fill_color=self.BG, fill_alpha=255,
        )

        PAD = UI_PANEL_INSET
        lw  = int(pw * 0.28)   # left panel   28%
        mw  = int(pw * 0.28)   # middle panel 28%
        rw  = pw - lw - mw     # right panel  44%

        lx = 0
        mx = lw
        rx = lw + mw

        pygame.draw.line(popup, self.BORDER, (mx, PAD), (mx, ph - PAD), 1)
        pygame.draw.line(popup, self.BORDER, (rx, PAD), (rx, ph - PAD), 1)

        self._draw_left_panel(  popup, engine, lx, 0, lw, ph, PAD)
        self._draw_carried_panel(popup, engine, mx, 0, mw, ph, PAD)
        self._draw_detail_panel(popup, engine, rx, 0, rw, ph, PAD)

        surface.blit(popup, (px, py))

    # ------------------------------------------------------------------ #
    #  Left panel — EQUIPPED / BODY / CONDITION + EXP bar
    # ------------------------------------------------------------------ #

    def _draw_left_panel(
        self, surf: pygame.Surface, engine: "Engine",
        ox: int, oy: int, w: int, h: int, pad: int,
    ) -> None:
        x       = ox + pad
        lh      = self._font_small.get_linesize() + 2
        col_mid = x + (w - pad * 2) // 2   # second-column x within panel

        player  = engine.player
        fighter = getattr(player, "fighter", None)
        equip   = getattr(player, "equipment", None)
        show_hp = getattr(player, "true_sight", False) or DEBUG_MODE

        # ── Reserve bottom area for EXP section ──────────────────────
        # From bottom: pad + 3px bar + 2px gap + lh (text) + 4px gap + 1px sep + 5px gap
        exp_reserved = pad + 3 + 2 + lh + 4 + 1 + 5
        content_bottom = oy + h - exp_reserved

        y = oy + pad

        # ── Section 1: EQUIPPED ───────────────────────────────────────
        hdr = self._font_normal.render("EQUIPPED", True, self.HDR_C)
        surf.blit(hdr, (x, y))
        y += hdr.get_height() + 3

        for disp_name, slot_id in _EQUIP_SLOT_DISPLAY:
            if y >= content_bottom - lh:
                break
            # Section header sentinel (slot_id is None)
            if slot_id is None:
                if y < content_bottom - 4:
                    y += 2
                    pygame.draw.line(surf, self.SEP_C, (ox + pad, y), (ox + w - pad, y), 1)
                    y += 4
                hdr_s = self._font_small.render(disp_name, True, self.HDR_C)
                surf.blit(hdr_s, (x, y))
                y += lh
                continue
            item = equip.slots.get(slot_id) if equip else None

            slot_s = self._font_small.render(disp_name, True, _SLATE_MID)
            surf.blit(slot_s, (x, y))

            if item:
                item_s = self._font_small.render(item.name, True, _NEAR_WHITE)
            else:
                item_s = self._font_small.render("\u2014", True, _SLATE_DARK)
            surf.blit(item_s, (col_mid, y))
            y += lh

        # ── Divider ───────────────────────────────────────────────────
        if y < content_bottom - 4:
            y += 3
            pygame.draw.line(surf, self.SEP_C, (ox + pad, y), (ox + w - pad, y), 1)
            y += 5

        # ── Section 2: BEARING (single HP pool) ───────────────────────
        if fighter and y < content_bottom - lh:
            frac = fighter.hp_fraction
            label, col = _bearing(frac)
            nm_s = self._font_small.render("Bearing", True, _SLATE_MID)
            surf.blit(nm_s, (x, y))
            brng_s = self._font_small.render(label, True, col)
            surf.blit(brng_s, (col_mid, y))
            if show_hp:
                hp_s = self._font_small.render(
                    f"  {fighter.hp}/{fighter.max_hp}", True, _SLATE_MID
                )
                surf.blit(hp_s, (col_mid + brng_s.get_width(), y))
            y += lh

        # AV display
        if fighter and y < content_bottom - lh:
            av = getattr(fighter, "effective_av", 0)
            av_label = self._font_small.render("Ward", True, _SLATE_MID)
            surf.blit(av_label, (x, y))
            av_val = self._font_small.render(str(av) if av > 0 else "\u2014", True, _NEAR_WHITE)
            surf.blit(av_val, (col_mid, y))
            y += lh

        # ── Level / EXP bar at bottom ─────────────────────────────────
        level_comp = getattr(player, "level", None)
        if level_comp:
            sep_y    = oy + h - exp_reserved + 5
            bar_y    = oy + h - pad - 3
            text_y   = bar_y - lh - 2

            pygame.draw.line(surf, self.SEP_C,
                             (ox + pad, sep_y), (ox + w - pad, sep_y), 1)

            exp_label = f"Level {level_comp.level}   EXP  {level_comp.exp} / {level_comp.exp_to_next}"
            exp_s = self._font_small.render(exp_label, True, _SLATE_MID)
            surf.blit(exp_s, (x, text_y))

            if level_comp.perk_points > 0:
                pp_s = self._font_small.render(
                    f"  · {level_comp.perk_points}pt", True, _OLD_GOLD
                )
                surf.blit(pp_s, (x + exp_s.get_width(), text_y))

            bar_w  = w - pad * 2
            frac   = min(1.0, level_comp.exp / max(1, level_comp.exp_to_next))
            filled = max(0, int(frac * bar_w))
            pygame.draw.rect(surf, MIDNIGHT_DEEP,  (x, bar_y, bar_w, 3))
            pygame.draw.rect(surf, _OLD_GOLD,     (x, bar_y, filled, 3))

    # ------------------------------------------------------------------ #
    #  Middle panel — Carried items
    # ------------------------------------------------------------------ #

    def _draw_carried_panel(
        self, surf: pygame.Surface, engine: "Engine",
        ox: int, oy: int, w: int, h: int, pad: int,
    ) -> None:
        x = ox + pad
        y = oy + pad

        inv = getattr(engine.player, "inventory", None)

        title = self._font_title.render("CARRIED", True, self.TITLE)
        surf.blit(title, (x, y))

        if inv:
            wt_s = self._font_small.render(
                f"{inv.current_weight:.1f}/{inv.capacity:.1f}kg", True, self.DIM
            )
            surf.blit(wt_s, (ox + w - wt_s.get_width() - pad, y + 2))
        y += title.get_height() + 4
        pygame.draw.line(surf, self.BORDER, (ox + pad, y), (ox + w - pad, y), 1)
        y += 6

        if not inv or not inv.items:
            none_s = self._font_normal.render("Nothing has taken root yet.", True, self.DIM)
            surf.blit(none_s, (x, y))
            return

        equip  = getattr(engine.player, "equipment", None)
        groups = _group_items(inv.items, engine)
        flat   = _flat_list(groups, self._collapsed)

        if not self._flat:
            self._flat = flat
            if self.selected >= len(self._flat):
                self.selected = 0
        else:
            flat = self._flat

        lh    = self._row_height
        max_y = oy + h - pad - lh

        # Clamp scroll to actual content
        vis_rows = max(1, (max_y - y) // lh)
        self.scroll = max(0, min(self.scroll, max(0, len(flat) - vis_rows)))

        # Column constants — all row content positions derived from these.
        # Sprite is 32px wide at zoom=2 (16px base * 2). Columns must not overlap.
        _content_left  = x             # = ox + pad
        _content_right = ox + w - pad
        COL_SPRITE  = _content_left + 2    # sprite: pixels 2..33 (32px wide)
        COL_BADGE   = _content_left + 36   # [E] badge starts after sprite + 2px gap
        COL_NAME    = _content_left + 58   # name starts after badge column
        COL_WEIGHT  = _content_right - 50  # weight right-aligned
        _max_name_w = COL_WEIGHT - COL_NAME - 4

        sprite_reg  = getattr(engine, "sprite_registry", None)
        render_mode = getattr(getattr(engine, "display", None), "render_mode", "ascii")

        clip     = pygame.Rect(ox, oy + pad, w, h - pad * 2)
        old_clip = surf.get_clip()
        surf.set_clip(clip)

        for idx, (item, is_hdr, label) in enumerate(flat):
            if y >= max_y:
                break
            if idx < self.scroll:
                continue

            is_sel = (idx == self.selected)

            if is_hdr:
                cat    = label
                arrow  = "v" if cat not in self._collapsed else ">"
                hdr_text = f" {arrow} {label.upper()}"
                if is_sel:
                    pygame.draw.rect(surf, MIDNIGHT_DEEP, (ox + 2, y - 2, w - 4, lh))
                hdr_col = self.SELECTED if is_sel else VOID_PURPLE
                hdr_s = self._font_small.render(hdr_text, True, hdr_col)
                surf.blit(hdr_s, (_content_left, y + (lh - hdr_s.get_height()) // 2))
                y += lh
                continue

            _row_cy = y + lh // 2

            equipped = equip.is_equipped(item) if equip else False
            name_col = _OLD_GOLD if equipped else self.TEXT
            row_col  = self.SELECTED if is_sel else name_col

            if is_sel:
                pygame.draw.rect(surf, MIDNIGHT_DEEP, (ox + 2, y - 2, w - 4, lh))

            # Sprite at COL_SPRITE
            tile = getattr(item, "tile", "")
            icon_drawn = False
            if tile and render_mode == "sprite" and sprite_reg:
                fg   = engine.registry.fg(tile) if tile in engine.registry._data else TRUE_WHITE
                icon = sprite_reg.get_tinted(tile, fg, zoom=2)
                if icon:
                    surf.blit(icon, (COL_SPRITE, _row_cy - icon.get_height() // 2))
                    icon_drawn = True
            if not icon_drawn and tile and tile in engine.registry._data:
                ch = chr(engine.registry.char(tile))
                fg = engine.registry.fg(tile)
                g  = self._font_normal.render(ch, True, fg)
                surf.blit(g, (COL_SPRITE, _row_cy - g.get_height() // 2))

            # [E] badge at COL_BADGE — separate from name, never concatenated
            if equipped:
                e_s = self._font_small.render("[E]", True, _OLD_GOLD)
                surf.blit(e_s, (COL_BADGE, _row_cy - e_s.get_height() // 2))

            # Item name at COL_NAME — truncated before COL_WEIGHT
            name_str = getattr(item, "name", "?")
            if label:
                name_str += f" ({label})"
            elif getattr(item, "stackable", False) and getattr(item, "count", 1) > 1:
                name_str += f" x{item.count}"
            if self._font_normal.size(name_str)[0] > _max_name_w:
                while len(name_str) > 1 and self._font_normal.size(name_str + "...")[0] > _max_name_w:
                    name_str = name_str[:-1]
                name_str += "..."
            ns = self._font_normal.render(name_str, True, row_col)
            surf.blit(ns, (COL_NAME, _row_cy - ns.get_height() // 2))

            # Weight at COL_WEIGHT — right-aligned
            wt_s2 = self._font_small.render(
                f"{getattr(item, 'weight', 0.0):.1f}kg", True, self.DIM
            )
            surf.blit(wt_s2, (COL_WEIGHT + 50 - wt_s2.get_width(), _row_cy - wt_s2.get_height() // 2))
            y += lh

        surf.set_clip(old_clip)

    # ------------------------------------------------------------------ #
    #  Right panel — Detail
    # ------------------------------------------------------------------ #

    def _draw_detail_panel(
        self, surf: pygame.Surface, engine: "Engine",
        ox: int, oy: int, w: int, h: int, pad: int,
    ) -> None:
        x = ox + pad
        y = oy + pad

        title = self._font_title.render("DETAIL", True, self.TITLE)
        surf.blit(title, (x, y))
        y += title.get_height() + 4
        pygame.draw.line(surf, self.BORDER, (ox + pad, y), (ox + w - pad, y), 1)
        y += 6

        item = self._selected_item()
        if item is None:
            none_s = self._font_small.render("Select an item.", True, self.DIM)
            surf.blit(none_s, (x, y))
            return

        lh       = self._font_small.get_linesize() + 2
        item_id  = getattr(item, "item_id", "") or ""
        item_def = engine.data.items.get(item_id, {}) if item_id else {}
        equip    = getattr(engine.player, "equipment", None)
        max_w    = w - pad * 2

        # Name
        nm = self._font_bold.render(getattr(item, "name", "?"), True, self.TITLE)
        if nm.get_width() > max_w:
            nm = self._font_normal.render(getattr(item, "name", "?"), True, self.TITLE)
        surf.blit(nm, (x, y))
        y += nm.get_height() + 4

        # Category + slot
        cat  = item_def.get("category", "")
        slot = item_def.get("slot", "")
        sub  = cat.title()
        if slot:
            sub += f" \u00b7 {slot.replace('_', ' ').title()}"
        if sub:
            sub_s = self._font_small.render(sub, True, _SLATE_MID)
            surf.blit(sub_s, (x, y))
            y += lh

        if equip and equip.is_equipped(item):
            eq_s = self._font_small.render("[Equipped]", True, _OLD_GOLD)
            surf.blit(eq_s, (x, y))
            y += lh

        y += 4
        pygame.draw.line(surf, SLATE_DARK, (ox + pad, y), (ox + w - pad, y), 1)
        y += 6

        # Description
        desc = getattr(item, "description", "") or item_def.get("description", "")
        if desc:
            for ln in _wrap_text(self._font_small, desc, max_w - 8):
                if y > oy + h - pad * 3:
                    break
                ls = self._font_small.render(ln, True, self.TEXT)
                surf.blit(ls, (x, y))
                y += lh
            y += 4

        pygame.draw.line(surf, SLATE_DARK, (ox + pad, y), (ox + w - pad, y), 1)
        y += 6

        # Keyword tags
        keywords = getattr(item, "keywords", [])
        kw_data  = getattr(engine.data, "keywords", {})
        if keywords:
            import engine.palette as _pal
            for kw_entry in keywords:
                tag          = kw_entry.get("tag", "")
                tier         = kw_entry.get("tier", 1)
                kw_def       = kw_data.get(tag, {})
                display_name = kw_def.get("display", tag)
                color_alias  = kw_def.get("color", "UI_TEXT_MID")
                try:
                    kw_color = getattr(_pal, color_alias)
                except AttributeError:
                    kw_color = UI_TEXT_MID
                kw_line  = f"[{display_name}: {tier}]"
                kw_s     = self._font_small.render(kw_line, True, kw_color)
                surf.blit(kw_s, (x, y))
                y += lh
            y += 4

        # Stats block
        if cat == "weapon":
            dice  = item_def.get("damage_dice", "\u2014")
            bonus = item_def.get("damage_bonus", 0)
            dmg   = f"{dice}+{bonus}" if bonus else str(dice)
            _render_stat(surf, self._font_small, "Damage", dmg,
                         x, y, _SLATE_MID, self.VALUE_C)
            y += lh

        elif cat == "armor":
            for layer in item_def.get("armor_layers", []):
                av  = layer.get("armor_value", 0)
                mat = layer.get("material", "").title()
                nm2 = layer.get("name", "layer")
                _render_stat(surf, self._font_small,
                             nm2, f"AV {av}  {mat}",
                             x, y, _SLATE_MID, self.VALUE_C)
                y += lh
                cov        = layer.get("coverage", 1.0)
                cov_label  = f"{int(cov * 100)}%"
                label_w    = self._font_small.size("100%")[0]  # worst-case width
                bar_x      = x + 6
                panel_right = ox + w - pad
                bar_w      = max(1, panel_right - bar_x - label_w - 6)
                filled     = max(0, min(int(cov * bar_w), bar_w))
                pygame.draw.rect(surf, MIDNIGHT_DEEP,   (bar_x, y, bar_w, 4))
                pygame.draw.rect(surf, _MIST_BLUE,     (bar_x, y, filled, 4))
                cov_s = self._font_small.render(cov_label, True, _SLATE_MID)
                surf.blit(cov_s, (bar_x + bar_w + 6, y - 1))
                y += 8

        # Essence — supports both "essences" list and single "essence"
        essences_list = item_def.get("essences", [])
        if essences_list:
            for idx, ess_entry in enumerate(essences_list):
                ename   = ess_entry.get("name", "")
                estr    = float(ess_entry.get("strength", 0.0))
                pips    = min(5, round(estr * 5))
                ess_str = ename + "  " + "\u2022" * pips + "\u00b7" * max(0, 5 - pips)
                label   = "Essences" if idx == 0 else ""
                _render_stat(surf, self._font_small, label, ess_str,
                             x, y, _SLATE_MID, self.VALUE_C)
                y += lh
        else:
            essence  = item_def.get("essence") or ""
            strength = float(item_def.get("essence_strength", 0.0))
            if essence:
                ess_str = essence
                if strength > 0:
                    pips    = round(strength * 5)
                    ess_str += "  " + "\u2022" * pips + "\u00b7" * max(0, 5 - pips)
                _render_stat(surf, self._font_small, "Essence", ess_str,
                             x, y, _SLATE_MID, self.VALUE_C)
                y += lh

        # Weight
        wt = item_def.get("weight", getattr(item, "weight", 0))
        _render_stat(surf, self._font_small, "Weight", f"{wt:.1f} kg",
                     x, y, _SLATE_MID, self.VALUE_C)
