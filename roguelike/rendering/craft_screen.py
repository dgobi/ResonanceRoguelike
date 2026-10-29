# rendering/craft_screen.py
# UI RULES: read docs/UI_RULES.md before modifying this file.
"""
Crafting screen. C key opens/closes.
Recipes grouped by category with collapsible headers.
UP/DOWN/PgUp/PgDn scrolls the list. ENTER on header collapses/expands.
ENTER on a craftable recipe attempts the craft.
"""
from __future__ import annotations

import pygame
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine
    from engine.display_config import DisplayConfig


# Canonical display order for categories
_CATEGORY_ORDER = ["campfire", "cooking", "wildcrafting", "alchemy"]
_CATEGORY_LABELS = {
    "campfire":    "Campfire",
    "cooking":     "Cooking",
    "wildcrafting": "Wildcrafting",
    "alchemy":     "Alchemy",
}


def _wrap_text(font: pygame.font.Font, text: str, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
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


def _ambient_satisfies_screen(ambient_sources: list, tag: str, min_tier: int) -> bool:
    for src in (ambient_sources or []):
        if src.get("tag") == tag and src.get("tier", 0) >= min_tier:
            return True
    return False


def _count_qualifying(inv, tag: str, min_tier: int) -> int:
    count = 0
    for item in (inv.items if inv else []):
        for kw in getattr(item, "keywords", []):
            if kw.get("tag") == tag and kw.get("tier", 0) >= min_tier:
                count += 1
                break
    return count


class CraftScreen:
    """Single-panel crafting screen opened with C."""

    BG       = DEEP_NOTHING
    BORDER   = VOID_PURPLE
    TITLE    = SPIRIT_BLUE
    TEXT     = WORN_STONE
    DIM      = DEEP_EARTH
    SELECTED = RESONANCE_GOLD
    LOCKED   = SLATE_DARK
    OK       = LIFE_GREEN
    HDR_COL  = STONE_BLUE

    def __init__(self) -> None:
        self.open:         bool       = False
        self.selected:     int        = 0   # index into _flat_items list
        self.scroll:       int        = 0
        self._collapsed:   set[str]   = set()
        self._font_title:  pygame.font.Font | None = None
        self._font_normal: pygame.font.Font | None = None
        self._font_small:  pygame.font.Font | None = None
        self._row_height:  int  = 22
        self._vis_rows:    int  = 8   # updated by render() each frame
        # Ingredient selection prompt state
        self._choosing:        bool       = False
        self._choice_prompts:  list       = []   # per-component prompt data
        self._choice_index:    int        = 0
        self._choice_selected: int        = 0
        self._chosen_items:    dict       = {}   # comp_index -> item_id
        self._pending_recipe:  dict | None = None

    def init(self, display: "DisplayConfig") -> None:
        self._font_title  = getattr(display, "font_ui_bold", None) or display.font_ui_normal
        self._font_normal = display.font_ui_normal
        self._font_small  = display.font_ui_small
        self._row_height  = self._font_normal.get_linesize() + 4

    def toggle(self) -> None:
        self.open     = not self.open
        self.selected = 0
        self.scroll   = 0
        self._choosing       = False
        self._pending_recipe = None
        self._chosen_items   = {}

    # ------------------------------------------------------------------ #
    #  Data helpers
    # ------------------------------------------------------------------ #

    def _get_recipes(self, engine: "Engine") -> list[dict]:
        return [r for r in engine.data.recipes.values()
                if not r.get("_deprecated")]

    def _build_flat_items(self, recipes: list[dict]) -> list[dict]:
        """
        Returns a flat list of items to render, interleaving category headers
        with recipe rows. Headers have type="header", rows have type="recipe".
        """
        # Group recipes by category
        groups: dict[str, list[dict]] = {cat: [] for cat in _CATEGORY_ORDER}
        other: list[dict] = []
        for r in recipes:
            cat = r.get("category", "")
            if cat in groups:
                groups[cat].append(r)
            else:
                other.append(r)

        flat: list[dict] = []
        for cat in _CATEGORY_ORDER:
            rlist = groups[cat]
            if not rlist:
                continue
            flat.append({"type": "header", "category": cat})
            if cat not in self._collapsed:
                for r in rlist:
                    flat.append({"type": "recipe", "recipe": r})
        # Uncategorised at the end
        if other:
            flat.append({"type": "header", "category": "_other"})
            if "_other" not in self._collapsed:
                for r in other:
                    flat.append({"type": "recipe", "recipe": r})
        return flat

    @staticmethod
    def _build_ambient_sources(engine: "Engine") -> list:
        sources: list[dict] = []

        equip = getattr(engine.player, "equipment", None)
        if equip:
            light_item = equip.slots.get("offhand")
            light = getattr(engine.player, "light_source", None)
            if (light_item is not None and light and light.active
                    and getattr(light, "_item_ref", None) is light_item
                    and engine.player.inventory.contains(light_item)
                    and (not light_item.burn_turns or light_item.turns_lit < light_item.burn_turns)):
                item_def = engine.data.items.get(getattr(light_item, "item_id", ""), {})
                pb = item_def.get("provides_burning", False)
                if pb:
                    tier = int(pb) if isinstance(pb, (int, float)) else 1
                    sources.append({"tag": "burning", "tier": tier})

        decor = getattr(getattr(engine, "local_map", None), "decor", {})
        px, py = engine.player.x, engine.player.y
        for (dx, dy), did in decor.items():
            radius = engine.data.decoratives.get(did, {}).get("warmth_radius", 3)
            if did == "campfire_lit" and max(abs(dx - px), abs(dy - py)) <= radius:
                sources.append({"tag": "burning", "tier": 2})
                sources.append({"tag": "stationary_fire", "tier": 1})
                break

        return sources

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> bool:
        if not self.open:
            return False

        # Ingredient selection sub-panel intercepts all input
        if self._choosing:
            return self._handle_choice_key(key, engine)

        recipes   = self._get_recipes(engine)
        flat      = self._build_flat_items(recipes)
        n         = len(flat)

        if key in (pygame.K_ESCAPE, pygame.K_c):
            self.open = False
            return True

        if key in (pygame.K_UP, pygame.K_KP8):
            self.selected = max(0, self.selected - 1)
            self._clamp_scroll(flat, self._vis_rows)
            return True

        if key in (pygame.K_DOWN, pygame.K_KP2):
            self.selected = min(n - 1, self.selected + 1)
            self._clamp_scroll(flat, self._vis_rows)
            return True

        if key in (pygame.K_PAGEUP,):
            self.selected = max(0, self.selected - 6)
            self._clamp_scroll(flat, self._vis_rows)
            return True

        if key in (pygame.K_PAGEDOWN,):
            self.selected = min(n - 1, self.selected + 6)
            self._clamp_scroll(flat, self._vis_rows)
            return True

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if 0 <= self.selected < n:
                item = flat[self.selected]
                if item["type"] == "header":
                    cat = item["category"]
                    if cat in self._collapsed:
                        self._collapsed.discard(cat)
                    else:
                        self._collapsed.add(cat)
                    # Rebuild flat and clamp selection
                    new_flat = self._build_flat_items(recipes)
                    self.selected = min(self.selected, len(new_flat) - 1)
                    self._clamp_scroll(new_flat, self._vis_rows)
                elif item["type"] == "recipe":
                    self._attempt_craft(engine, item["recipe"])
            return True

        return True

    def _clamp_scroll(self, flat: list[dict], visible: int = 8) -> None:
        """Keep selected item visible in the visible window."""
        n = len(flat)
        if n == 0:
            self.selected = 0
            self.scroll = 0
            return
        # Clamp selection
        self.selected = max(0, min(n - 1, self.selected))
        # Clamp scroll: max offset so last item is visible
        max_scroll = max(0, n - visible)
        # Ensure selected is within visible window
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + visible:
            self.scroll = self.selected - visible + 1
        self.scroll = max(0, min(self.scroll, max_scroll))

    def _attempt_craft(self, engine: "Engine", recipe: dict,
                       chosen_items: dict | None = None) -> None:
        from engine.crafting import can_craft, plan_craft, commit_craft
        inv = getattr(engine.player, "inventory", None)
        if inv is None:
            return

        if not recipe.get("known", True):
            engine.log.add("The method is not known to you.", MSG_DEFAULT)
            self.open = False
            return

        ambient = self._build_ambient_sources(engine)
        kw_data = getattr(engine.data, "keywords", {})
        # An automatic plan may exclude protected materials. Reach the existing
        # affirmative picker first, then revalidate the complete selected plan.
        if chosen_items is None:
            prompts = self._find_ambiguous_components(recipe, inv, kw_data)
            if prompts:
                self._choosing        = True
                self._choice_prompts  = prompts
                self._choice_index    = 0
                self._choice_selected = 0
                self._chosen_items    = {}
                self._pending_recipe  = recipe
                return

        selected, missing = plan_craft(recipe, inv, kw_data, ambient, chosen_items)
        if missing:
            engine.log.add("Materials, tools or conditions are missing. Passive work needs a stationary fire.", MSG_DEFAULT)
            self.open = False
            return
        if recipe.get("places_in_world"):
            tile_id   = recipe.get("result_tile", "")
            self.open = False
            engine._start_placement_cursor(tile_id, recipe, selected)
        elif recipe.get("passive_processing"):
            # Do NOT consume items yet -- placement cursor will craft on ENTER
            self.open = False
            engine._start_processing_placement(recipe, selected)
        else:
            result_id = recipe.get("result_item") or recipe.get("result_tile", "")
            item = engine.item_factory.create(result_id, engine.player.x, engine.player.y) if result_id else None
            if item is None or not commit_craft(engine, recipe, selected, ambient, [item]):
                engine.log.add("The work cannot be completed. The materials remain.", MSG_DEFAULT)
            else:
                engine.log.add(f"{item.name} fashioned.", MSG_DEFAULT)
            self.open = False

    @staticmethod
    def _find_ambiguous_components(recipe: dict, inv, kw_data: dict) -> list:
        """
        For each component, check if more than one distinct item_id qualifies.
        Returns list of prompt dicts for ambiguous components, or empty list.
        """
        from engine.crafting import _item_has_tag
        prompts = []
        for ci, comp in enumerate(recipe.get("components", [])):
            tag      = comp["tag"]
            min_tier = comp.get("min_tier", 1)
            # Collect all qualifying items grouped by item_id
            by_id: dict[str, list] = {}
            for item in (inv.items if inv else []):
                if _item_has_tag(item, tag, min_tier):
                    iid = getattr(item, "item_id", "")
                    if iid not in by_id:
                        by_id[iid] = []
                    by_id[iid].append(item)
            if len(by_id) > 1 or any(not getattr(item, "consumed_on_use", True)
                                     for items in by_id.values() for item in items):
                # Build option list
                options = []
                for iid, items in by_id.items():
                    name = getattr(items[0], "name", iid) + " (spent)"
                    # Find the relevant keyword display
                    kw_display = ""
                    kw_color   = UI_TEXT_MID
                    for kw in getattr(items[0], "keywords", []):
                        if kw.get("tag") == tag:
                            tier_val = kw.get("tier", 0)
                            kw_def   = kw_data.get(tag, {})
                            disp     = kw_def.get("display", tag)
                            kw_display = f"[{disp}: {tier_val}]"
                            color_alias = kw_def.get("color", "")
                            if color_alias:
                                import engine.palette as _pal
                                kw_color = getattr(_pal, color_alias, UI_TEXT_MID)
                            break
                    options.append({
                        "item_id":    iid,
                        "name":       name,
                        "count":      len(items),
                        "kw_display": kw_display,
                        "kw_color":   kw_color,
                    })
                kw_def    = kw_data.get(tag, {})
                disp_name = kw_def.get("display", tag)
                prompts.append({
                    "comp_index": ci,
                    "header":     f"Choose: [{disp_name} >= {min_tier}]",
                    "options":    options,
                })
        return prompts

    def _handle_choice_key(self, key: int, engine: "Engine") -> bool:
        """Handle input while ingredient selection prompt is active."""
        prompt = self._choice_prompts[self._choice_index]
        n_opts = len(prompt["options"])

        if key in (pygame.K_ESCAPE,):
            # Cancel entire craft attempt
            self._choosing       = False
            self._pending_recipe = None
            self._chosen_items   = {}
            return True

        if key in (pygame.K_UP, pygame.K_KP8):
            self._choice_selected = max(0, self._choice_selected - 1)
            return True

        if key in (pygame.K_DOWN, pygame.K_KP2):
            self._choice_selected = min(n_opts - 1, self._choice_selected + 1)
            return True

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            # Store choice
            chosen = prompt["options"][self._choice_selected]
            self._chosen_items[prompt["comp_index"]] = chosen["item_id"]
            # Advance to next prompt or finalize
            if self._choice_index + 1 < len(self._choice_prompts):
                self._choice_index    += 1
                self._choice_selected  = 0
            else:
                # All prompts resolved -- proceed with craft
                recipe = self._pending_recipe
                self._choosing       = False
                self._pending_recipe = None
                chosen_map = dict(self._chosen_items)
                self._chosen_items   = {}
                if recipe:
                    self._attempt_craft(engine, recipe, chosen_items=chosen_map)
            return True

        return True

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #

    def render(self, screen: pygame.Surface, engine: "Engine") -> None:
        if not self.open:
            return
        if not self._font_normal:
            return

        from engine.crafting import can_craft
        inv     = getattr(engine.player, "inventory", None)
        kw_data = getattr(engine.data, "keywords", {})
        ambient = self._build_ambient_sources(engine)
        recipes = self._get_recipes(engine)
        flat    = self._build_flat_items(recipes)

        sw, sh = screen.get_size()
        pw = min(sw - 80, 520)
        ph = min(sh - 80, 560)
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        # Panel construction: 9-slice border via draw_panel (UI_RULES.md)
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        _ui_reg = getattr(engine, "ui_registry", None)
        if _ui_reg:
            _ui_reg.draw_panel(
                panel, pygame.Rect(0, 0, pw, ph), "thorny_growth",
                tint_color=self.BORDER, fill_color=self.BG, fill_alpha=255,
            )
        else:
            panel.fill((*self.BG, 255))
            pygame.draw.rect(panel, self.BORDER, (0, 0, pw, ph), 1)

        # Content rect = panel_rect.inflate(-18, -18) per UI_RULES.md
        _CPAD = 18  # 12 border + 6 inner gap
        _cx = _CPAD
        _cy_top = _CPAD
        _cw = pw - _CPAD * 2
        _cr = _cx + _cw

        y = _cy_top
        title_surf = self._font_title.render("CRAFT", True, self.TITLE)
        panel.blit(title_surf, (pw // 2 - title_surf.get_width() // 2, y))
        y += title_surf.get_height() + 8
        pygame.draw.line(panel, self.BORDER, (_cx, y), (_cr, y))
        y += 6

        # Reserve hint row at bottom of content rect
        _fh = self._font_small.get_linesize() if self._font_small else 14
        _HINT_ROW_H = _fh + 8
        _hint_y = _CPAD + (ph - _CPAD * 2) - _HINT_ROW_H

        # Leave room for material/tool counts above the reserved hint row.
        _content_bottom = _CPAD + (ph - _CPAD * 2)
        list_bottom = _cy_top + int((_content_bottom - _cy_top) * 0.4)
        detail_top  = list_bottom + 6

        # ---- Recipe list (scrollable) ----
        rh   = self._row_height
        visible_rows = max(1, (list_bottom - y) // rh)
        self._vis_rows = visible_rows  # store for key handler

        # Clamp scroll
        self._clamp_scroll(flat, visible_rows)

        sel_recipe: dict | None = None

        _has_above = self.scroll > 0
        _has_below = (self.scroll + visible_rows) < len(flat)

        for vi in range(visible_rows):
            fi = vi + self.scroll
            if fi >= len(flat):
                break
            item    = flat[fi]
            is_sel  = (fi == self.selected)
            iy      = y + vi * rh

            if item["type"] == "header":
                cat   = item["category"]
                label = _CATEGORY_LABELS.get(cat, cat.title())
                arrow = "v" if cat not in self._collapsed else ">"
                hdr_text = f"  {arrow} {label}"
                if is_sel:
                    pygame.draw.rect(panel, UI_PANEL_DARK, (_cx, iy, _cw, rh))
                hs = self._font_normal.render(hdr_text, True,
                                              self.SELECTED if is_sel else self.HDR_COL)
                panel.blit(hs, (_cx + 4, iy + 2))

            elif item["type"] == "recipe":
                recipe  = item["recipe"]
                known   = recipe.get("known", True)
                craftable = False
                if inv is not None and known:
                    craftable, _ = can_craft(recipe, inv, kw_data, ambient)

                name = recipe.get("name", recipe.get("id", "?"))
                if is_sel:
                    pygame.draw.rect(panel, UI_PANEL_DARK, (_cx, iy, _cw, rh))
                    sel_recipe = recipe

                if not known:
                    col = self.LOCKED
                elif is_sel:
                    col = self.SELECTED
                elif craftable:
                    col = self.OK
                else:
                    col = self.LOCKED

                ns = self._font_normal.render(f"    {name}", True, col)
                panel.blit(ns, (_cx + 8, iy + 2))

        # Scroll indicators at right edge of list area
        if _has_above and self._font_small:
            _ind = self._font_small.render("^", True, UI_TEXT_DIM)
            panel.blit(_ind, (_cr - _ind.get_width(), y + 2))
        if _has_below and self._font_small:
            _iy = y + (visible_rows - 1) * rh
            _ind = self._font_small.render("v", True, UI_TEXT_DIM)
            panel.blit(_ind, (_cr - _ind.get_width(), _iy + 2))

        pygame.draw.line(panel, self.BORDER, (_cx, detail_top), (_cr, detail_top))

        # ---- Detail panel (3 sections: Name+Desc, Requires, Produces) ----
        _detail_overflow = False
        if sel_recipe and self._font_small:
            dy  = detail_top + 6
            lh  = self._font_small.get_linesize() + 2
            max_dy = _hint_y - 2  # never draw below hint row
            detail_clip = panel.get_clip()
            panel.set_clip(pygame.Rect(_cx, dy, _cw, max(0, max_dy-dy)))

            known = sel_recipe.get("known", True)
            if inv is not None and known:
                craftable, _ = can_craft(recipe=sel_recipe, inv=inv,
                                         keyword_data=kw_data, ambient_sources=ambient)
            else:
                craftable = False

            # -- Section 1: Name + Description --
            _dx = _cx + 2  # detail content left
            _rname_display = sel_recipe.get("name", sel_recipe.get("id", "?"))
            _name_s = self._font_title.render(_rname_display, True, UI_TEXT_BRIGHT)
            panel.blit(_name_s, (_dx, dy))
            dy += _name_s.get_height() + 2

            desc = sel_recipe.get("description", "")
            if desc:
                for line in _wrap_text(self._font_small, desc, _cw - 4):
                    if dy >= max_dy:
                        _detail_overflow = True
                        break
                    panel.blit(self._font_small.render(line, True, UI_TEXT_MID), (_dx, dy))
                    dy += lh
            dy += 2
            pygame.draw.line(panel, self.BORDER, (_cx, dy), (_cr, dy))
            dy += 4

            if not known:
                hint = sel_recipe.get("locked_hint", "The method is not known to you.")
                if dy < max_dy:
                    panel.blit(self._font_small.render(hint, True, MSG_LORE), (_dx, dy))
            else:
                # -- Section 2: Requires --
                _req_hdr = self._font_title.render("Requires:", True, UI_TEXT_BRIGHT)
                panel.blit(_req_hdr, (_dx, dy))
                dy += _req_hdr.get_height() + 2
                for line in _wrap_text(self._font_small, "Counts are potential matches; each slot needs a distinct item.", _cw - 4):
                    if dy + lh > max_dy:
                        _detail_overflow = True
                        break
                    panel.blit(self._font_small.render(line, True, UI_TEXT_DIM), (_dx, dy))
                    dy += lh

                # requires_single_item
                _rsi = sel_recipe.get("requires_single_item")
                if _rsi and dy < max_dy:
                    if isinstance(_rsi, list):
                        _rsi_tags = _rsi
                        _rsi_qty = 1
                    else:
                        _rsi_tags = _rsi.get("tags", [])
                        _rsi_qty = _rsi.get("max_quantity", 1)
                    _rsi_x = _dx + 4
                    for _ri, _rt in enumerate(_rsi_tags):
                        _rkdef = kw_data.get(_rt["tag"], {})
                        _rdisp = _rkdef.get("display", _rt["tag"])
                        _rc_alias = _rkdef.get("color", "")
                        _rc = self.TEXT
                        if _rc_alias:
                            import engine.palette as _pal
                            _rc = getattr(_pal, _rc_alias, self.TEXT)
                        _rt_s = self._font_small.render(
                            f"[{_rdisp} >= {_rt.get('min_tier', 1)}]", True, _rc)
                        panel.blit(_rt_s, (_rsi_x, dy))
                        _rsi_x += _rt_s.get_width() + 4
                        if _ri < len(_rsi_tags) - 1:
                            _plus = self._font_small.render(" + ", True, self.DIM)
                            panel.blit(_plus, (_rsi_x, dy))
                            _rsi_x += _plus.get_width()
                    _on_s = self._font_small.render(f" on one item x {_rsi_qty}", True, self.DIM)
                    panel.blit(_on_s, (_rsi_x, dy))
                    dy += lh
                    from engine.crafting import _item_has_all_tags, material_candidate
                    _rsi_have = sum(1 for it in (inv.items if inv else [])
                                    if _item_has_all_tags(it, _rsi_tags) and material_candidate(it))
                    _rsi_col = UI_TEXT_BRIGHT if _rsi_have >= _rsi_qty else MSG_DANGER
                    panel.blit(self._font_small.render(
                        f"    (automatic: {_rsi_have})", True, _rsi_col), (_dx, dy))
                    dy += lh

                # requires_ambient
                from engine.crafting import conditions_for
                for req in conditions_for(sel_recipe):
                    if dy >= max_dy:
                        _detail_overflow = True
                        break
                    tag       = req["tag"]
                    min_tier  = req.get("min_tier", 1)
                    satisfied = _ambient_satisfies_screen(ambient, tag, min_tier)
                    kw_def    = kw_data.get(tag, {})
                    disp_name = "stationary fire" if tag == "stationary_fire" else kw_def.get("display", tag)
                    _kw_color_alias = kw_def.get("color", "")
                    _kw_col = self.TEXT
                    if _kw_color_alias:
                        import engine.palette as _pal
                        _kw_col = getattr(_pal, _kw_color_alias, self.TEXT)
                    _tag_s = self._font_small.render(
                        f"  [{disp_name} >= {min_tier}]", True, _kw_col)
                    _nearby_s = self._font_small.render(" (nearby: present)" if satisfied else " (nearby: not present)", True, UI_TEXT_BRIGHT if satisfied else MSG_DANGER)
                    panel.blit(_tag_s, (_dx, dy))
                    panel.blit(_nearby_s, (_dx + _tag_s.get_width(), dy))
                    dy += lh

                # Standard components
                for comp in sel_recipe.get("components", []) + [dict(t, role="tool") for t in sel_recipe.get("tools", [])]:
                    if dy + 2 * lh > max_dy:
                        _detail_overflow = True
                        break
                    tag       = comp["tag"]
                    min_tier  = comp.get("min_tier", 1)
                    quantity  = comp.get("quantity", 1)
                    from engine.crafting import material_candidate, _item_has_tag
                    tool = comp.get("role") == "tool"
                    have = sum(_item_has_tag(i, tag, min_tier) and (tool or material_candidate(i))
                               for i in (inv.items if inv else []))
                    choice_only = sum(_item_has_tag(i, tag, min_tier) and not material_candidate(i)
                                      for i in (inv.items if inv else [])) if not tool else 0
                    kw_def    = kw_data.get(tag, {})
                    disp_name = kw_def.get("display", tag)
                    _kw_color_alias = kw_def.get("color", "")
                    _kw_col = self.TEXT
                    if _kw_color_alias:
                        import engine.palette as _pal
                        _kw_col = getattr(_pal, _kw_color_alias, self.TEXT)
                    panel.blit(self._font_small.render(
                        f"  {'Tool (kept)' if tool else 'Material (spent)'}: [{disp_name} >= {min_tier}] x {quantity}", True, _kw_col), (_dx, dy))
                    dy += lh
                    have_col  = UI_TEXT_BRIGHT if have >= quantity else MSG_DANGER
                    panel.blit(self._font_small.render(
                        (f"    (retained matches: {have})" if tool else
                         f"    (automatic: {have}; choose: {choice_only})"), True, have_col), (_dx, dy))
                    dy += lh

                dy += 2
                pygame.draw.line(panel, self.BORDER, (_cx, dy), (_cr, dy))
                dy += 4

                # -- Section 3: Produces --
                _result_id = sel_recipe.get("result_item", "")
                if _result_id and dy < max_dy:
                    _prod_hdr = self._font_title.render("Produces:", True, UI_TEXT_BRIGHT)
                    panel.blit(_prod_hdr, (_dx, dy))
                    dy += _prod_hdr.get_height() + 2
                    _rdef = engine.data.items.get(_result_id, {})
                    _rpname = _rdef.get("name", _result_id)
                    panel.blit(self._font_small.render(_rpname, True, UI_TEXT_MID), (_dx + 4, dy))
                    dy += lh
                    _rkws = _rdef.get("keywords", [])
                    if _rkws and dy < max_dy:
                        _kw_x = _dx + 4
                        for _rkw in _rkws:
                            _rtag = _rkw.get("tag", "")
                            _rtier = _rkw.get("tier", 0)
                            _rkdef = kw_data.get(_rtag, {})
                            _rdisp = _rkdef.get("display", _rtag)
                            _rcolor_alias = _rkdef.get("color", "")
                            _rkw_col = self.TEXT
                            if _rcolor_alias:
                                import engine.palette as _pal
                                _rkw_col = getattr(_pal, _rcolor_alias, self.TEXT)
                            _rkw_s = self._font_small.render(
                                f"[{_rdisp}: {_rtier}]", True, _rkw_col)
                            if _kw_x + _rkw_s.get_width() + 4 > _cr:
                                dy += lh
                                _kw_x = _dx + 4
                            panel.blit(_rkw_s, (_kw_x, dy))
                            _kw_x += _rkw_s.get_width() + 6
                        dy += lh

            panel.set_clip(detail_clip)

        if _detail_overflow and self._font_small:
            _dind = self._font_small.render("v", True, UI_TEXT_DIM)
            panel.blit(_dind, (_cr - _dind.get_width(), max_dy - 2))

        # ---- Ingredient selection overlay (covers detail area) ----
        if self._choosing and self._choice_prompts and self._font_small:
            prompt = self._choice_prompts[self._choice_index]
            _cy = detail_top + 6
            _clh = self._font_small.get_linesize() + 4
            # Clear detail area
            pygame.draw.rect(panel, self.BG, (_cx, detail_top + 1, _cw, _hint_y - detail_top - 2))
            # Header
            _hdr = self._font_normal.render(prompt["header"], True, UI_TEXT_BRIGHT)
            panel.blit(_hdr, (_dx, _cy))
            _cy += _hdr.get_height() + 6
            # Options
            for _oi, opt in enumerate(prompt["options"]):
                _is_sel = (_oi == self._choice_selected)
                if _is_sel:
                    pygame.draw.rect(panel, UI_PANEL_DARK, (_cx, _cy - 1, _cw, _clh))
                _name_s = self._font_small.render(
                    opt["name"], True,
                    self.SELECTED if _is_sel else self.TEXT,
                )
                panel.blit(_name_s, (_dx + 4, _cy))
                if opt["kw_display"]:
                    _kw_s = self._font_small.render(opt["kw_display"], True, opt["kw_color"])
                    panel.blit(_kw_s, (_cr - _kw_s.get_width() - 4, _cy))
                _cy += _clh
            # Prompt hint
            _cy += 4
            _ph_s = self._font_small.render(
                "[ ENTER ] use this   [ ESC ] cancel", True, UI_TEXT_DIM,
            )
            panel.blit(_ph_s, (pw // 2 - _ph_s.get_width() // 2, _cy))

        # Hint row — separator + vertically centred text (UI_RULES.md)
        if self._font_small:
            pygame.draw.line(panel, self.BORDER, (_cx, _hint_y - 1), (_cr, _hint_y - 1))
            sel_item = flat[self.selected] if 0 <= self.selected < len(flat) else None
            if sel_item and sel_item["type"] == "header":
                cat = sel_item["category"]
                verb = "collapse" if cat not in self._collapsed else "expand"
                hint     = f"[ ENTER ] {verb}     [ ESC / C ] close"
                hint_col = self.HDR_COL
            elif sel_recipe and sel_recipe.get('known', True) and self._find_ambiguous_components(sel_recipe, inv, kw_data):
                hint = "[ ENTER ] Choose materials   [ ESC / C ] close"
                hint_col = self.SELECTED
            elif sel_recipe and craftable:
                hint     = "[ ENTER ] craft     [ ESC / C ] close"
                hint_col = self.OK
            else:
                hint     = "[ ESC / C ] close"
                hint_col = self.DIM
            hs = self._font_small.render(hint, True, hint_col)
            _hint_text_y = _hint_y + (_HINT_ROW_H - hs.get_height()) // 2
            panel.blit(hs, (pw // 2 - hs.get_width() // 2, _hint_text_y))

        screen.blit(panel, (px, py))
