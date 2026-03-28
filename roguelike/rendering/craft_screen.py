# rendering/craft_screen.py
"""
Crafting screen. C key opens/closes.
Single-panel: list of known recipes, greyed out when ingredients missing.
ENTER attempts the craft.
"""
from __future__ import annotations

import pygame
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine
    from engine.display_config import DisplayConfig


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
    """Return True if any ambient source satisfies this tag/tier requirement."""
    for src in (ambient_sources or []):
        if src.get("tag") == tag and src.get("tier", 0) >= min_tier:
            return True
    return False


def _count_qualifying(inv, tag: str, min_tier: int) -> int:
    """Count inventory items bearing tag at or above min_tier."""
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

    def __init__(self) -> None:
        self.open:         bool = False
        self.selected:     int  = 0
        self._font_title:  pygame.font.Font | None = None
        self._font_normal: pygame.font.Font | None = None
        self._font_small:  pygame.font.Font | None = None
        self._row_height:  int  = 22

    def init(self, display: "DisplayConfig") -> None:
        self._font_title  = getattr(display, "font_ui_bold", None) or display.font_ui_normal
        self._font_normal = display.font_ui_normal
        self._font_small  = display.font_ui_small
        self._row_height  = self._font_normal.get_linesize() + 4

    def toggle(self) -> None:
        self.open     = not self.open
        self.selected = 0

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> bool:
        if not self.open:
            return False

        recipes = self._get_recipes(engine)

        if key in (pygame.K_ESCAPE, pygame.K_c):
            self.open = False
            return True

        if key in (pygame.K_UP, pygame.K_KP8):
            if recipes:
                self.selected = max(0, self.selected - 1)
            return True

        if key in (pygame.K_DOWN, pygame.K_KP2):
            if recipes:
                self.selected = min(len(recipes) - 1, self.selected + 1)
            return True

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if recipes:
                idx = min(self.selected, len(recipes) - 1)
                self._attempt_craft(engine, recipes[idx])
            return True

        return True

    def _get_recipes(self, engine: "Engine") -> list[dict]:
        return list(engine.data.recipes.values())

    @staticmethod
    def _build_ambient_sources(engine: "Engine") -> list:
        """
        Collect ambient sources from:
        - Equipped lit torch/lantern (provides burning tag)
        - Nearby campfire_lit decor within 3 tiles (provides burning tier 2)
        - Inventory items — their keywords provide ambient tags without being consumed.
          Used for reusable tools (e.g. clay_pot provides vessel tier 1).

        Returns list of {"tag": str, "tier": int} dicts.
        """
        sources: list[dict] = []

        # Equipped light source
        equip = getattr(engine.player, "equipment", None)
        if equip:
            light_item = equip.slots.get("light")
            if light_item is not None:
                item_def = engine.data.items.get(getattr(light_item, "item_id", ""), {})
                pb = item_def.get("provides_burning", False)
                if pb:
                    tier = int(pb) if isinstance(pb, (int, float)) else 1
                    sources.append({"tag": "burning", "tier": tier})

        # Nearby campfire_lit decor (within 3 tiles)
        decor = getattr(getattr(engine, "local_map", None), "decor", {})
        px, py = engine.player.x, engine.player.y
        for (dx, dy), did in decor.items():
            if did == "campfire_lit" and max(abs(dx - px), abs(dy - py)) <= 3:
                sources.append({"tag": "burning", "tier": 2})
                break

        # Inventory items provide ambient tags for their keywords (reusable tools)
        inv = getattr(engine.player, "inventory", None)
        seen_tags: set[tuple[str, int]] = set()
        for item in (inv.items if inv else []):
            for kw in getattr(item, "keywords", []):
                tag  = kw.get("tag", "")
                tier = kw.get("tier", 0)
                key  = (tag, tier)
                if tag and key not in seen_tags:
                    sources.append({"tag": tag, "tier": tier})
                    seen_tags.add(key)

        return sources

    def _attempt_craft(self, engine: "Engine", recipe: dict) -> None:
        from engine.crafting import can_craft, attempt_craft
        inv = getattr(engine.player, "inventory", None)
        if inv is None:
            return

        if not recipe.get("known", True):
            engine.log.add("The method is not known to you.", MSG_DEFAULT)
            self.open = False
            return

        ambient = self._build_ambient_sources(engine)
        kw_data = getattr(engine.data, "keywords", {})
        craftable, _ = can_craft(recipe, inv, kw_data, ambient)
        if not craftable:
            engine.log.add("The materials are not here.", MSG_DEFAULT)
            self.open = False
            return

        attempt_craft(recipe, inv, kw_data, ambient)

        if recipe.get("places_in_world"):
            tile_id   = recipe.get("result_tile", "")
            self.open = False
            engine._start_placement_cursor(tile_id, recipe)
        elif recipe.get("passive_processing"):
            result_id = recipe.get("result_item", "")
            turns     = recipe.get("processing_turns", 20)
            source    = recipe.get("processing_source", "drying")
            proc_msgs = getattr(engine.data, "processing_messages", {})
            start_tmpl = proc_msgs.get(source, {}).get("start", "The work begins.")
            # Look up result item name for the message
            result_def  = engine.data.items.get(result_id, {})
            result_name = result_def.get("name", result_id)
            engine.local_map.processing_queue.append({
                "item_id":         result_id,
                "turns_remaining": turns,
                "x": engine.player.x,
                "y": engine.player.y,
                "source":          source,
            })
            engine.log.add(start_tmpl.format(item_name=result_name), MSG_LORE)
            self.open = False
        else:
            result_id = recipe.get("result_item") or recipe.get("result_tile", "")
            if result_id:
                item = engine.item_factory.create(result_id, engine.player.x, engine.player.y)
                if item:
                    if not inv.add(item):
                        engine.log.add("No room. The work scatters.", MSG_DEFAULT)
                    else:
                        engine.log.add(f"{item.name} fashioned.", MSG_DEFAULT)
            self.open = False

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #

    def render(self, screen: pygame.Surface, engine: "Engine") -> None:
        if not self.open:
            return
        if not self._font_normal:
            return

        sw, sh = screen.get_size()
        pw = min(sw - 80, 520)
        ph = min(sh - 80, 500)
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((*self.BG, 240))
        pygame.draw.rect(panel, self.BORDER, (0, 0, pw, ph), 1)

        y = 12
        title_surf = self._font_title.render("CRAFT", True, self.TITLE)
        panel.blit(title_surf, (pw // 2 - title_surf.get_width() // 2, y))
        y += title_surf.get_height() + 8
        pygame.draw.line(panel, self.BORDER, (12, y), (pw - 12, y))
        y += 6

        from engine.crafting import can_craft
        inv      = getattr(engine.player, "inventory", None)
        kw_data  = getattr(engine.data, "keywords", {})
        ambient  = self._build_ambient_sources(engine)
        recipes  = self._get_recipes(engine)

        if not recipes:
            none_surf = self._font_small.render(
                "Nothing to make. Nothing to use.", True, self.DIM
            )
            panel.blit(none_surf, (pw // 2 - none_surf.get_width() // 2, y + 20))
        else:
            for i, recipe in enumerate(recipes):
                known   = recipe.get("known", True)
                is_sel  = (i == self.selected)

                if inv is not None and known:
                    craftable, _ = can_craft(recipe, inv, kw_data, ambient)
                else:
                    craftable = False

                name = recipe.get("name", recipe.get("id", "?"))
                if is_sel:
                    pygame.draw.rect(panel, (*self.SELECTED, 30), (8, y, pw - 16, self._row_height))

                if not known:
                    col = self.LOCKED
                elif is_sel:
                    col = self.SELECTED
                elif craftable:
                    col = self.OK
                else:
                    col = self.LOCKED

                name_surf = self._font_normal.render(name, True, col)
                panel.blit(name_surf, (16, y + 2))
                y += self._row_height

            # Detail panel for selected recipe
            if recipes and 0 <= self.selected < len(recipes):
                sel_recipe = recipes[self.selected]
                known      = sel_recipe.get("known", True)

                if inv is not None and known:
                    craftable, _ = can_craft(recipe=sel_recipe, inv=inv, keyword_data=kw_data, ambient_sources=ambient)
                else:
                    craftable = False

                y += 8
                pygame.draw.line(panel, self.BORDER, (12, y), (pw - 12, y))
                y += 6

                desc = sel_recipe.get("description", "")
                if desc and self._font_small:
                    for line in _wrap_text(self._font_small, desc, pw - 40):
                        ls = self._font_small.render(line, True, self.TEXT)
                        panel.blit(ls, (20, y))
                        y += self._font_small.get_linesize() + 2
                    y += 4

                if not known:
                    # Locked recipe — show hint, hide components
                    hint = sel_recipe.get("locked_hint", "The method is not known to you.")
                    if self._font_small:
                        hs = self._font_small.render(hint, True, MSG_LORE)
                        panel.blit(hs, (20, y))
                        y += self._font_small.get_linesize() + 2
                elif self._font_small:
                    # Ambient requirements (environmental, never consumed)
                    lh = self._font_small.get_linesize() + 2
                    for req in sel_recipe.get("requires_ambient", []):
                        tag      = req["tag"]
                        min_tier = req.get("min_tier", 1)
                        satisfied = _ambient_satisfies_screen(ambient, tag, min_tier)
                        kw_def       = kw_data.get(tag, {})
                        display_name = kw_def.get("display", tag)
                        req_text = f"  [{display_name} \u2265 {min_tier}] (nearby)"
                        req_s    = self._font_small.render(req_text, True, self.TEXT)
                        panel.blit(req_s, (20, y))
                        y += lh
                        have_col  = UI_TEXT_BRIGHT if satisfied else MSG_DANGER
                        have_text = "    (present)" if satisfied else "    (not present)"
                        have_s    = self._font_small.render(have_text, True, have_col)
                        panel.blit(have_s, (20, y))
                        y += lh

                    # Keyword component requirements
                    for comp in sel_recipe.get("components", []):
                        tag      = comp["tag"]
                        min_tier = comp.get("min_tier", 1)
                        quantity = comp.get("quantity", 1)
                        have     = _count_qualifying(inv, tag, min_tier)

                        kw_def       = kw_data.get(tag, {})
                        display_name = kw_def.get("display", tag)

                        req_text = f"  [{display_name} \u2265 {min_tier}] \u00d7 {quantity}"
                        req_s    = self._font_small.render(req_text, True, self.TEXT)
                        panel.blit(req_s, (20, y))
                        y += lh

                        have_col  = UI_TEXT_BRIGHT if have >= quantity else MSG_DANGER
                        have_text = f"    (have: {have})"
                        have_s    = self._font_small.render(have_text, True, have_col)
                        panel.blit(have_s, (20, y))
                        y += lh

                    y += 4

                # Action hint
                if self._font_small:
                    if craftable:
                        hint     = "[ ENTER ] craft     [ ESC / C ] close"
                        hint_col = self.OK
                    else:
                        hint     = "[ ESC / C ] close"
                        hint_col = self.DIM
                    hs = self._font_small.render(hint, True, hint_col)
                    panel.blit(hs, (pw // 2 - hs.get_width() // 2, ph - 28))

        screen.blit(panel, (px, py))
