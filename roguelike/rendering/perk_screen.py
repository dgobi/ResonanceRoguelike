# rendering/perk_screen.py
from __future__ import annotations
import pygame
from config import UI_PANEL_INSET
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine
    from engine.display_config import DisplayConfig


_CATEGORIES = ["Viscera", "Perception", "Resonance", "Creation", "Ontology"]


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


class PerkScreen:
    """
    Two-panel perk screen. K opens/closes.
    LEFT: category list + perks  RIGHT: detail + confirmation overlay
    """

    BG       = DEEP_NOTHING
    BORDER   = VOID_PURPLE
    TITLE    = SPIRIT_BLUE
    TEXT     = WORN_STONE
    DIM      = DEEP_EARTH
    SELECTED = RESONANCE_GOLD
    ACQUIRED = LIFE_GREEN
    LOCKED   = SLATE_DARK     # slate_dark
    LABEL_C  = STONE_BLUE
    VALUE_C  = FROST_WHITE
    HDR_C    = VOID_PURPLE
    CONFIRM_BG = DEEP_NOTHING

    def __init__(self) -> None:
        self.open:            bool = False
        self._font_title:     pygame.font.Font | None = None
        self._font_normal:    pygame.font.Font | None = None
        self._font_small:     pygame.font.Font | None = None
        self._font_bold:      pygame.font.Font | None = None
        self._row_height:     int  = 20
        # Navigation state
        self._flat:           list = []   # (perk_id, is_hdr, label)
        self.selected:        int  = 0
        # Confirmation overlay
        self._confirming:     bool = False

    def init(self, display: "DisplayConfig") -> None:
        self._font_title  = getattr(display, "font_ui_bold",      None) or display.font_ui_normal
        self._font_normal = display.font_ui_normal
        self._font_small  = display.font_ui_small
        self._font_bold   = getattr(display, "font_ui_bold_large", None) or display.font_ui_large
        self._row_height  = self._font_normal.get_linesize() + 4

    def toggle(self) -> None:
        self.open        = not self.open
        self._confirming = False
        self._flat       = []
        self.selected    = 0

    # ------------------------------------------------------------------ #
    #  Flat list of perks by category
    # ------------------------------------------------------------------ #

    def _build_flat(self, engine: "Engine") -> list:
        flat = []
        perks_data = engine.data.perks   # dict perk_id → def
        by_cat: dict[str, list] = {c: [] for c in _CATEGORIES}
        for perk_id, pdef in perks_data.items():
            cat = pdef.get("category", "Misc")
            if cat not in by_cat:
                by_cat.setdefault(cat, [])
            by_cat[cat].append(perk_id)

        for cat in _CATEGORIES:
            ids = by_cat.get(cat, [])
            if not ids:
                continue
            flat.append((None, True, cat))
            for pid in sorted(ids):
                flat.append((pid, False, ""))

        return flat

    def _selectable(self, flat: list) -> list[int]:
        return [i for i, (_, hdr, _) in enumerate(flat) if not hdr]

    def _selected_perk_id(self) -> str | None:
        if not self._flat or self.selected >= len(self._flat):
            return None
        pid, is_hdr, _ = self._flat[self.selected]
        return None if is_hdr else pid

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> bool:
        if not self.open:
            return False

        if self._confirming:
            return self._handle_confirm_key(key, engine)

        if key in (pygame.K_ESCAPE, pygame.K_k):
            self.open = False
            return True

        if not self._flat:
            self._flat = self._build_flat(engine)

        sel = self._selectable(self._flat)

        if key in (pygame.K_UP, pygame.K_KP8):
            self._move(-1, sel)
            return True

        if key in (pygame.K_DOWN, pygame.K_KP2):
            self._move(1, sel)
            return True

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            perk_id = self._selected_perk_id()
            if perk_id and self._can_afford(perk_id, engine):
                self._confirming = True
            return True

        return True

    def _handle_confirm_key(self, key: int, engine: "Engine") -> bool:
        if key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._commit(engine)
            self._confirming = False
        elif key in (pygame.K_n, pygame.K_ESCAPE):
            self._confirming = False
        return True

    def _move(self, delta: int, sel: list[int]) -> None:
        if not sel:
            return
        if self.selected not in sel:
            self.selected = sel[0]
            return
        idx = sel.index(self.selected)
        self.selected = sel[max(0, min(len(sel) - 1, idx + delta))]

    def _can_afford(self, perk_id: str, engine: "Engine") -> bool:
        perks      = getattr(engine.player, "perks", None)
        level_comp = getattr(engine.player, "level", None)
        if perks is None or level_comp is None:
            return False
        if perks.has(perk_id):
            return False
        pdef = engine.data.perks.get(perk_id, {})
        cost = pdef.get("cost", 1)
        return level_comp.perk_points >= cost

    def _commit(self, engine: "Engine") -> None:
        perk_id = self._selected_perk_id()
        if not perk_id:
            return
        perks      = getattr(engine.player, "perks", None)
        level_comp = getattr(engine.player, "level", None)
        if perks is None or level_comp is None:
            return
        pdef = engine.data.perks.get(perk_id, {})
        cost = pdef.get("cost", 1)
        if perks.has(perk_id) or level_comp.perk_points < cost:
            return
        level_comp.perk_points -= cost
        perks.add_perk(perk_id)
        engine._register_player_perks()
        engine.log.add("It settles into you.", OLD_GOLD)

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
        pw = min(860, sw - 40)
        ph = min(520, sh - 40)
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        engine.ui_registry.draw_panel(
            popup, pygame.Rect(0, 0, pw, ph), "weathered_temple",
            tint_color=self.BORDER, fill_color=self.BG, fill_alpha=252,
        )

        PAD = UI_PANEL_INSET
        lw  = int(pw * 0.30)
        rw  = pw - lw

        pygame.draw.line(popup, self.BORDER, (lw, PAD), (lw, ph - PAD), 1)

        if not self._flat:
            self._flat = self._build_flat(engine)
            sel = self._selectable(self._flat)
            if sel and self.selected not in sel:
                self.selected = sel[0]

        self._draw_left(popup, engine, 0, 0, lw, ph, PAD)
        self._draw_right(popup, engine, lw, 0, rw, ph, PAD)

        # Footer
        footer = self._font_small.render(
            "^ v navigate   Enter confirm   K/ESC close",
            True, self.DIM,
        )
        fy = ph - PAD - footer.get_height()
        pygame.draw.line(popup, self.BORDER,
                         (PAD, fy - 4), (pw - PAD, fy - 4), 1)
        popup.blit(footer, (PAD, fy))

        surface.blit(popup, (px, py))

        if self._confirming:
            self._render_confirm(surface, engine, px, py, pw, ph)

    def _draw_left(
        self, surf: pygame.Surface, engine: "Engine",
        ox: int, oy: int, w: int, h: int, pad: int,
    ) -> None:
        x = ox + pad
        y = oy + pad

        title = self._font_title.render("PERKS", True, self.TITLE)
        surf.blit(title, (x, y))
        y += title.get_height() + 4
        pygame.draw.line(surf, self.BORDER, (ox + pad, y), (ox + w - pad, y), 1)
        y += 6

        perks      = getattr(engine.player, "perks", None)
        level_comp = getattr(engine.player, "level", None)
        lh         = self._row_height
        max_y      = oy + h - pad - lh * 2

        # Points display
        if level_comp:
            pts_s = self._font_small.render(
                f"{level_comp.perk_points} point{'s' if level_comp.perk_points != 1 else ''} available",
                True, OLD_GOLD if level_comp.perk_points > 0 else self.DIM,
            )
            surf.blit(pts_s, (x, y))
            y += lh + 2

        # Scroll so selected is visible
        sel = self._selectable(self._flat)
        if sel and self.selected in sel:
            sel_rank  = sel.index(self.selected)
            vis_rows  = (max_y - y) // lh
            scroll_st = max(0, sel_rank - vis_rows + 1)
        else:
            scroll_st = 0

        row = 0
        for idx, (perk_id, is_hdr, label) in enumerate(self._flat):
            if y >= max_y:
                break

            if is_hdr:
                if row < scroll_st:
                    row += 1
                    y += lh
                    continue
                hs = self._font_small.render(label.upper(), True, self.HDR_C)
                surf.blit(hs, (x, y))
                y += lh
                continue

            if row < scroll_st:
                row += 1
                y += lh
                continue
            row += 1

            pdef     = engine.data.perks.get(perk_id, {})
            acquired = perks.has(perk_id) if perks else False
            cost     = pdef.get("cost", 1)
            pts      = level_comp.perk_points if level_comp else 0
            can_buy  = (not acquired) and pts >= cost

            if acquired:
                col = self.ACQUIRED
            elif can_buy:
                col = self.TEXT
            else:
                col = self.LOCKED

            is_sel = (idx == self.selected)
            if is_sel:
                # Build highlight from known interior rect (BORDER_PX=15 × scale=2 = 30px)
                _BORDER = 30
                _inner  = pygame.Rect(ox, oy, w, h).inflate(-2 * _BORDER, -2 * _BORDER)
                _hl_y   = max(y - 2, _inner.top)
                _hl_b   = min(y - 2 + lh, max_y - 2)
                if _hl_b > _hl_y:
                    pygame.draw.rect(surf, MIDNIGHT_DEEP,
                                     pygame.Rect(_inner.x, _hl_y, _inner.width, _hl_b - _hl_y))

            mark = "\u2713 " if acquired else "  "
            nm   = self._font_normal.render(
                mark + pdef.get("name", perk_id), True,
                self.SELECTED if is_sel else col,
            )
            surf.blit(nm, (x, y))
            y += lh

    def _draw_right(
        self, surf: pygame.Surface, engine: "Engine",
        ox: int, oy: int, w: int, h: int, pad: int,
    ) -> None:
        x = ox + pad
        y = oy + pad

        perk_id = self._selected_perk_id()
        pdef    = engine.data.perks.get(perk_id, {}) if perk_id else {}
        perks   = getattr(engine.player, "perks", None)
        lc      = getattr(engine.player, "level", None)
        lh      = self._font_small.get_linesize() + 2
        max_w   = w - pad * 2

        if not perk_id or not pdef:
            none_s = self._font_normal.render("Nothing has taken root yet.", True, self.DIM)
            surf.blit(none_s, (x, y + 20))
            return

        # Name
        nm = self._font_bold.render(pdef.get("name", perk_id), True, self.TITLE)
        if nm.get_width() > max_w:
            nm = self._font_normal.render(pdef.get("name", perk_id), True, self.TITLE)
        surf.blit(nm, (x, y))
        y += nm.get_height() + 4

        # Category + cost
        cat  = pdef.get("category", "")
        cost = pdef.get("cost", 1)
        sub  = f"{cat}  ·  cost {cost}"
        ss   = self._font_small.render(sub, True, self.LABEL_C)
        surf.blit(ss, (x, y))
        y += lh

        # Acquired / affordable state
        acquired = perks.has(perk_id) if perks else False
        if acquired:
            st = self._font_small.render("Acquired", True, self.ACQUIRED)
            surf.blit(st, (x, y))
            y += lh
        else:
            pts = lc.perk_points if lc else 0
            if pts >= cost:
                st = self._font_small.render(
                    "Press Enter to commit.", True, OLD_GOLD
                )
            else:
                st = self._font_small.render(
                    f"Requires {cost} point{'s' if cost != 1 else ''}.", True, self.DIM
                )
            surf.blit(st, (x, y))
            y += lh

        y += 4
        pygame.draw.line(surf, SLATE_DARK, (ox + pad, y), (ox + w - pad, y), 1)
        y += 6

        # Description
        desc = pdef.get("description", "")
        if desc:
            for ln in _wrap_text(self._font_small, desc, max_w - 8):
                ls = self._font_small.render(ln, True, self.TEXT)
                surf.blit(ls, (x, y))
                y += lh
            y += 4

        # Requires
        reqs = pdef.get("requires", [])
        if reqs:
            pygame.draw.line(surf, SLATE_DARK, (ox + pad, y), (ox + w - pad, y), 1)
            y += 6
            rq_h = self._font_small.render("Requires:", True, self.LABEL_C)
            surf.blit(rq_h, (x, y))
            y += lh
            for req in reqs:
                req_def  = engine.data.perks.get(req, {})
                req_name = req_def.get("name", req)
                met      = perks.has(req) if perks else False
                col      = self.ACQUIRED if met else self.LOCKED
                rs = self._font_small.render(f"  {req_name}", True, col)
                surf.blit(rs, (x, y))
                y += lh

        # Conflicts
        conflicts = pdef.get("conflicts", [])
        if conflicts:
            y += 2
            cf_h = self._font_small.render("Conflicts:", True, self.LABEL_C)
            surf.blit(cf_h, (x, y))
            y += lh
            for cf in conflicts:
                cf_def  = engine.data.perks.get(cf, {})
                cf_name = cf_def.get("name", cf)
                cs = self._font_small.render(f"  {cf_name}", True, self.DIM)
                surf.blit(cs, (x, y))
                y += lh

        # ── Mechanical effects ────────────────────────────────────────
        effects_list = pdef.get("effects", [])
        y += 4
        pygame.draw.line(surf, SLATE_DARK, (ox + pad, y), (ox + w - pad, y), 1)
        y += 6

        eff_hdr = self._font_small.render("EFFECT", True, self.LABEL_C)
        surf.blit(eff_hdr, (x, y))
        y += lh

        if effects_list:
            for eff_line in effects_list:
                if y > oy + h - pad * 2:
                    break
                # Bullet prefix in slate_dark, text in pale_yellow
                bullet = self._font_small.render("\u00b7 ", True, SLATE_DARK)
                surf.blit(bullet, (x, y))
                bw = bullet.get_width()
                for wrapped in _wrap_text(self._font_small, eff_line, max_w - bw - 4):
                    if y > oy + h - pad * 2:
                        break
                    eff_s = self._font_small.render(wrapped, True, BONE_PALE)
                    surf.blit(eff_s, (x + bw, y))
                    y += lh
                    # subsequent wrapped lines indent past bullet
        else:
            nd = self._font_small.render("No mechanical data recorded.", True, SLATE_DARK)
            surf.blit(nd, (x, y))
            y += lh

        # ── Perk state (for perks with tracked state) ─────────────────
        if perks and perk_id in perks.perk_state:
            state = perks.perk_state[perk_id]
            if state:
                y += 4
                pygame.draw.line(surf, SLATE_DARK, (ox + pad, y), (ox + w - pad, y), 1)
                y += 6
                for k, v in state.items():
                    ks = self._font_small.render(f"{k}: {v}", True, self.LABEL_C)
                    surf.blit(ks, (x, y))
                    y += lh

    def _render_confirm(
        self,
        surface: pygame.Surface,
        engine: "Engine",
        px: int, py: int, pw: int, ph: int,
    ) -> None:
        ow, oh = 320, 120
        ox = px + (pw - ow) // 2
        oy = py + (ph - oh) // 2

        overlay = pygame.Surface((ow, oh), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*self.CONFIRM_BG, 240), (0, 0, ow, oh))
        pygame.draw.rect(overlay, self.BORDER, (0, 0, ow, oh), 1)

        pad = UI_PANEL_INSET

        q  = self._font_normal.render("Commit to this?", True, self.TITLE)
        overlay.blit(q, ((ow - q.get_width()) // 2, pad))

        perk_id = self._selected_perk_id()
        pdef    = engine.data.perks.get(perk_id, {}) if perk_id else {}
        nm_s = self._font_small.render(
            pdef.get("name", perk_id or ""), True, OLD_GOLD
        )
        overlay.blit(nm_s, ((ow - nm_s.get_width()) // 2, pad + 22))

        y_s = self._font_normal.render("Y  confirm", True, self.ACQUIRED)
        n_s = self._font_normal.render("N  cancel",  True, self.DIM)
        overlay.blit(y_s, (ow // 2 - y_s.get_width() - 10, oh - pad - y_s.get_height()))
        overlay.blit(n_s, (ow // 2 + 10, oh - pad - n_s.get_height()))

        surface.blit(overlay, (ox, oy))
