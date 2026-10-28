# engine/look_mode.py
# UI RULES: read docs/UI_RULES.md before modifying this file.
from __future__ import annotations
from engine.effect_lifecycle import creature_id
import pygame
from typing import TYPE_CHECKING
from config import UI_PANEL_INSET
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine
    from world.local_map import LocalMap
    from entities.entity import Entity
    from engine.display_config import DisplayConfig


def _fits(text: str, font: pygame.font.Font, max_px: int) -> bool:
    """Return True if text renders within max_px pixels."""
    return font.size(text)[0] <= max_px


def _can_see_exact_hp(engine, target) -> bool:
    """
    True if the player can see exact per-location HP for a target.
    Checked in order: DEBUG_MODE, true_sight, perk the_opened_page.
    target is reserved for future per-creature sight rules.
    """
    from config import DEBUG_MODE
    if DEBUG_MODE:
        return True
    if getattr(engine.player, "true_sight", False):
        return True
    perks = getattr(engine.player, "perks", None)
    if perks and perks.has("the_opened_page"):
        return True
    return False


class LookMode:
    """
    Free-cursor look mode.
    The player can move a cursor around the visible/explored map
    and examine what is on each tile.
    """

    CURSOR_COLOR    = DISCHARGE_FLASH
    CURSOR_CHAR     = "X"
    EXAMINE_BG      = DEEP_NOTHING
    EXAMINE_BORDER  = VOID_PURPLE
    EXAMINE_TITLE   = SPIRIT_BLUE
    EXAMINE_TEXT    = WORN_STONE
    EXAMINE_DIM     = EARTH_BROWN
    EXAMINE_STAT    = LIFE_GREEN

    def __init__(self) -> None:
        self.cursor_x:      int  = 0
        self.cursor_y:      int  = 0
        self.examining:     bool = False   # True = detail popup open
        self.examine_index: int  = 0       # which thing on tile is selected
        self._font_normal: pygame.font.Font | None = None
        self._font_small:  pygame.font.Font | None = None
        self._font_title:  pygame.font.Font | None = None
        self._font_large:  pygame.font.Font | None = None

    def init(self, display: "DisplayConfig") -> None:
        self._font_normal = display.font_ui_normal
        self._font_small  = display.font_ui_small
        self._font_title  = (getattr(display, "font_ui_bold_large", None)
                           or display.font_ui_bold
                           or display.font_ui_normal)  # large bold for popup title
        self._font_large  = display.font_ui_large

    def enter(self, player_x: int, player_y: int) -> None:
        """Enter look mode. Cursor starts at player position."""
        self.cursor_x      = player_x
        self.cursor_y      = player_y
        self.examining     = False
        self.examine_index = 0

    # ------------------------------------------------------------------ #
    #  Input
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> bool:
        """
        Handle keypress in look mode.
        Returns True if consumed.
        """
        from engine.engine import MOVE_KEYS, GameMode

        if self.examining:
            things = self._get_things_at(engine, self.cursor_x, self.cursor_y)
            n = len(things)
            if key in (pygame.K_TAB, pygame.K_n):
                self.examine_index = (self.examine_index + 1) % n if n else 0
            elif key == pygame.K_p:
                self.examine_index = (self.examine_index - 1) % n if n else 0
            elif key in (pygame.K_ESCAPE, pygame.K_x,
                         pygame.K_RETURN, pygame.K_KP_ENTER):
                self.examining = False
            return True

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            nx = self.cursor_x + dx
            ny = self.cursor_y + dy
            if engine.local_map.in_bounds(nx, ny):
                if engine.local_map.tiles[nx, ny]["explored"]:
                    self.cursor_x = nx
                    self.cursor_y = ny
            return True

        if key in (pygame.K_x, pygame.K_RETURN, pygame.K_KP_ENTER):
            # Remote and remembered tiles are read-only. A visible nearby
            # interactable uses the normal interaction route, including its
            # selection prompt and turn cost (e.g. first reading of a stele).
            cx, cy = self.cursor_x, self.cursor_y
            if not engine.local_map.in_bounds(cx, cy):
                return True
            terrain_id = engine._resolve_terrain_id(cx, cy)
            terrain_entry = engine.data.terrain.get(terrain_id, {})
            decor_id = engine.local_map.decor.get((cx, cy))
            decor_entry = engine.data.decoratives.get(decor_id, {}) if decor_id else {}
            handler_name = decor_entry.get("interactable") or terrain_entry.get("interactable")
            cursor = engine.interaction_cursor
            if handler_name and cursor.can_reach(engine, cx, cy):
                handler = getattr(engine, f"_interactable_{handler_name}", None)
                if handler:
                    cursor.enter([(cx, cy)], engine.player.x, engine.player.y)
                    engine.mode = GameMode.INTERACTION_CURSOR
                    cursor._interact(engine, interactable_only=True)
                    # Container choices must own input until resolved. Other
                    # interactions return to look after any inscription closes.
                    if cursor._selection_prompt is None:
                        engine.mode = GameMode.LOOK
                    return True

            # Open detailed examine if there is something to examine
            things = self._get_things_at(
                engine, self.cursor_x, self.cursor_y
            )
            if things:
                self.examining     = True
                self.examine_index = len(things) - 1   # start on most interesting
            return True

        if key in (pygame.K_ESCAPE, pygame.K_l):
            engine.mode = GameMode.LOCAL
            return True

        return True   # consume all keys in look mode

    # ------------------------------------------------------------------ #
    #  What is here
    # ------------------------------------------------------------------ #

    def _get_things_at(
        self,
        engine: "Engine",
        x: int,
        y: int,
    ) -> list[dict]:
        """
        Return a list of descriptors for everything at (x, y).
        Ordered: terrain, items, creatures.
        """
        things = []

        if not engine.local_map.in_bounds(x, y):
            return things

        tile    = engine.local_map.tiles[x, y]
        terrain = str(tile["terrain"])

        # Terrain
        terrain_def = dict(engine.data.terrain.get(terrain, {}))
        # Look for 'display_name' in data, fallback to title-cased ID
        raw_name = terrain_def.get("display_name")
        if not raw_name:
            raw_name = terrain.replace("_", " ").title()
            
        if terrain == "stairs_down":
            terrain_def["description"] = "Stone steps descend into darkness. Press > to descend."
        elif terrain == "stairs_up":
            terrain_def["description"] = "Stone steps ascend toward the surface. Press < to ascend."
            
        things.append({
            "type":        "terrain",
            "id":          terrain,
            "name":        raw_name, # Use the resolved display name
            "description": terrain_def.get(
                "description", "Unremarkable ground."
            ),
            "tile":        terrain_def.get("tile", terrain),
        })

        # Decorative on this tile
        decor_id = getattr(engine.local_map, "decor", {}).get((x, y))
        if decor_id:
            decor_def = engine.data.decoratives.get(decor_id, {})
            raw_dname = decor_def.get("display_name") or decor_id.replace("_", " ").replace("decor ", "").title()
            things.append({
                "type":        "decor",
                "id":          decor_id,
                "name":        raw_dname,
                "description": decor_def.get("description", ""),
            })

        # Processing layer
        _proc_layer = getattr(engine.local_map, "processing_layer", {})
        _proc_entry = _proc_layer.get((x, y))
        if _proc_entry:
            _psource = _proc_entry.get("source", "processing")
            things.append({
                "type":        "processing",
                "name":        f"Something {_psource}.",
                "description": f"Something {_psource}.",
            })

        # Floor objects
        from generation.floor_object_utils import get_floor_objects as _gfo_look
        _floor_items = _gfo_look(engine.local_map, x, y)
        for _fi in _floor_items:
            _fname = getattr(_fi, "name", "something")
            if getattr(_fi, "source_creature", None):
                _fname = f"Remains of {_fname.replace('remains of ', '')}"
            _fw = getattr(_fi, "weight", 0.0)
            things.append({
                "type":        "floor_object",
                "name":        _fname,
                "description": f"{_fname[0].upper()}{_fname[1:]}. {_fw:.1f}kg." if _fw > 0 else f"{_fname[0].upper()}{_fname[1:]}.",
                "entity":      _fi,
                "tile":        getattr(_fi, "tile", "generic_item"),
            })

        # Player at this tile
        if engine.player.x == x and engine.player.y == y:
            fighter = getattr(engine.player, "fighter", None)
            entry = {
                "type":        "player",
                "name":        engine.player.name,
                "tile":        engine.player.tile,
                "entity":      engine.player,
                "description": "You.",
                "fighter":     fighter,
            }
            things.append(entry)

        tile_visible = bool(tile["visible"])

        # Other entities at this tile (live visible position)
        for entity in engine.entities:
            if entity is engine.player:
                continue
            if entity.x == x and entity.y == y and tile_visible:
                has_ai    = getattr(entity, "ai",      None) is not None
                kind = "creature" if has_ai else "item"
                entry = {
                    "type":  kind,
                    "name":  entity.name,
                    "tile":  entity.tile,
                    "entity": entity,
                }

                # Get description from data
                if kind == "creature":
                    creature_def = engine.data.entities.get(
                        creature_id(entity), {}
                    )
                    entry["description"] = creature_def.get(
                        "description",
                        "Something that should not be here."
                    )
                    fighter = getattr(entity, "fighter", None)
                    ai      = getattr(entity, "ai",      None)
                    entry["fighter"] = fighter
                    entry["ai_state"] = ai.state.value if ai else "unknown"
                    perception = getattr(entity, "perception", None)
                    entry["faction"] = (perception.faction
                                        if perception else "unknown")
                else:
                    entry["description"] = f"The {entity.name}."

                things.append(entry)

            # Ghost entry — last known position when tile not currently visible
            elif not tile_visible and tile["explored"]:
                lkx = getattr(entity, "last_known_x", None)
                lky = getattr(entity, "last_known_y", None)
                if lkx == x and lky == y:
                    has_ai = getattr(entity, "ai", None) is not None
                    if has_ai:
                        creature_def = engine.data.entities.get(creature_id(entity), {})
                        things.append({
                            "type":        "creature",
                            "name":        f"{entity.name} (last seen)",
                            "tile":        entity.tile,
                            "entity":      entity,
                            "description": creature_def.get(
                                "description",
                                "Something that should not be here."
                            ) + " (Last known position.)",
                            "fighter":     None,
                            "ai_state":    "unknown",
                            "faction":     "unknown",
                        })

        return things

    def _get_look_summary(
        self,
        engine: "Engine",
        x: int,
        y: int,
    ) -> str:
        """
        One-line summary for the UI panel look bar.
        Shows everything at the tile in layer order.
        """
        if not engine.local_map.in_bounds(x, y):
            return "Out of bounds."

        tile = engine.local_map.tiles[x, y]
        if not tile["explored"]:
            return "You have not been here."

        things = self._get_things_at(engine, x, y)
        if not things:
            return "Nothing."

        parts = []
        for t in things:
            if t["type"] == "terrain":
                parts.append(t["name"])
            else:
                parts.append(t["name"])

        visible = bool(engine.local_map.tiles[x, y]["visible"])
        prefix  = "" if visible else "[remembered] "
        return prefix + ",  ".join(parts)

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #

    def render_cursor(
        self,
        surface:    pygame.Surface,
        engine:     "Engine",
        cam_x:      int,
        cam_y:      int,
        x:          int | None = None,
        y:          int | None = None,
        color:      tuple | None = None,
    ) -> None:
        """
        Draw the look cursor onto the game surface.
        x, y override the cursor position — used by InteractionCursor and the
        placement cursor to reuse this draw logic without duplicating it.
        color overrides the border colour — used by the placement cursor to
        signal valid vs invalid placement positions.
        """
        tw, th = engine.display.effective_tile_size(
            getattr(engine, "sprite_registry", None)
        )

        vp = getattr(engine, "_viewport", None)
        vp_x = vp.x if vp else 0
        vp_y = vp.y if vp else 0

        cx = x if x is not None else self.cursor_x
        cy = y if y is not None else self.cursor_y
        screen_x = (cx - cam_x) * tw + vp_x
        screen_y = (cy - cam_y) * th + vp_y

        border_color = color if color is not None else self.CURSOR_COLOR

        # Highlight using a transparent surface blit
        highlight = pygame.Surface((tw, th), pygame.SRCALPHA)
        highlight.fill(border_color + (40,))
        surface.blit(highlight, (screen_x, screen_y))

        # Border
        pygame.draw.rect(
            surface,
            border_color,
            (screen_x, screen_y, tw, th),
            1,
        )

    def render_hint_overlay(
        self,
        screen:   pygame.Surface,
        viewport: pygame.Rect,
        display:  "DisplayConfig",
    ) -> None:
        """
        Draw look-mode hint text in the top-left of the viewport,
        overlaid on the map with a dark background behind each line.
        """
        if not self._font_small:
            return

        hint_lines = [
            "[ LOOK ]",
            "Move cursor to examine",
            "X / Enter for details",
            "ESC / L to exit",
        ]

        x      = viewport.left + 8
        y      = viewport.top  + 8
        line_h = display.line_height("small")

        for line in hint_lines:
            text_surf = self._font_small.render(line, True, UI_TEXT_MID)
            bg_rect   = pygame.Rect(x - 2, y - 1,
                                    text_surf.get_width() + 4,
                                    text_surf.get_height() + 2)
            bg_surf   = pygame.Surface((bg_rect.w, bg_rect.h), pygame.SRCALPHA)
            bg_surf.fill(VOID_BLACK + (180,))
            screen.blit(bg_surf,   bg_rect)
            screen.blit(text_surf, (x, y))
            y += line_h


    def render_look_bar(
        self,
        surface:    pygame.Surface,
        panel_rect: pygame.Rect,
        engine:     "Engine",
    ) -> None:
        """
        Render the look-mode UI panel -- replaces the normal
        UI panel while look mode is active.
        All content within content_rect per UI_RULES.md.
        """
        if not self._font_normal:
            return

        # Content rect = panel_rect.inflate(-18, -18) per UI_RULES.md
        _CPAD = 18
        _cx = _CPAD
        _cy_top = _CPAD
        _cr = panel_rect.width - _CPAD
        _cb = panel_rect.height - _CPAD
        _lh = self._font_normal.get_linesize() + 2

        surf = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        pygame.draw.line(surf, self.EXAMINE_BORDER,
                         (0, 0), (panel_rect.width, 0), 1)

        y = _cy_top

        # Cursor coords on first line
        coord_str  = f"({self.cursor_x}, {self.cursor_y})"
        coord_surf = self._font_small.render(coord_str, True, EARTH_BROWN)
        surf.blit(coord_surf, (_cx, y))
        y += coord_surf.get_height() + 2

        things = self._get_things_at(engine, self.cursor_x, self.cursor_y)

        if not things:
            if y + _lh <= _cb:
                t = self._font_normal.render(
                    "Nothing here.", True, self.EXAMINE_DIM
                )
                surf.blit(t, (_cx, y))
        else:
            for thing in things:
                if y + _lh > _cb:
                    break

                color = {
                    "terrain":      self.EXAMINE_DIM,
                    "decor":        WORN_STONE,
                    "processing":   WORN_STONE,
                    "floor_object": PALE_LIFE,
                    "creature":     PALE_FLESH,
                    "item":         PALE_LIFE,
                    "player":       FROST_WHITE,
                }.get(thing["type"], self.EXAMINE_TEXT)

                name_surf = self._font_normal.render(
                    thing["name"], True, color
                )
                surf.blit(name_surf, (_cx, y))

                # Brief description beside name if it fits
                desc = thing.get("description", "")
                if desc and self._font_small:
                    name_end = _cx + name_surf.get_width() + 12
                    avail_px = _cr - name_end
                    if avail_px > 40 and _fits(desc, self._font_small, avail_px):
                        d = self._font_small.render(desc, True, self.EXAMINE_DIM)
                        surf.blit(d, (name_end, y + 2))

                y += _lh

        surface.blit(surf, (panel_rect.x, panel_rect.y))

    def render_examine_popup(
        self,
        surface: pygame.Surface,
        engine:  "Engine",
    ) -> None:
        """
        Full detail popup for the top-most thing at cursor position.
        Drawn over the game view.
        """
        if not self._font_normal:
            return

        things = self._get_things_at(engine, self.cursor_x, self.cursor_y)
        if not things:
            return

        idx     = min(self.examine_index, len(things) - 1)
        subject = things[idx]

        sw = surface.get_width()
        sh = surface.get_height()
        pw = min(600, sw - 80)
        ph = min(320, sh - 80)
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        engine.ui_registry.draw_panel(
            popup, pygame.Rect(0, 0, pw, ph), "weathered_temple",
            tint_color=self.EXAMINE_BORDER, fill_color=self.EXAMINE_BG,
            fill_alpha=255,
        )

        y = UI_PANEL_INSET

        # Title
        title = self._font_title.render(
            subject["name"], True, self.EXAMINE_TITLE
        )
        popup.blit(title, (UI_PANEL_INSET, y))
        y += 24

        # Divider
        pygame.draw.line(popup, self.EXAMINE_BORDER,
                         (UI_PANEL_INSET, y), (pw - UI_PANEL_INSET, y), 1)
        y += 8

        # Description — word wrapped
        desc  = subject.get("description", "No description available.")
        words = desc.split()
        lines = []
        line  = ""
        max_w = pw - UI_PANEL_INSET * 2 - 40

        for word in words:
            test = line + (" " if line else "") + word
            if self._font_normal.size(test)[0] > max_w:
                if line:
                    lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)

        text_y = y
        for l in lines:
            t = self._font_normal.render(l, True, self.EXAMINE_TEXT)
            popup.blit(t, (UI_PANEL_INSET + 18, text_y))
            text_y += 16
            if text_y > ph - 60:
                break

        y = max(text_y + 8, y + 52)

        # Stats for terrain — resonance_emit shown at threshold_resonance_sight
        if subject["type"] == "terrain":
            thresholds = getattr(engine, "_corruption_thresholds", set())
            if "threshold_resonance_sight" in thresholds:
                terrain_id  = subject.get("id", "")
                terrain_def = engine.data.terrain.get(terrain_id, {})
                emit = terrain_def.get("resonance_emit", 0.0)
                # Also check decor layer for resonance_emit
                _lk_x = subject.get("x", 0)
                _lk_y = subject.get("y", 0)
                _lk_did = engine.local_map.decor.get((_lk_x, _lk_y))
                if _lk_did:
                    _lk_demit = engine.data.decoratives.get(_lk_did, {}).get("resonance_emit", 0.0)
                    if _lk_demit > emit:
                        emit = _lk_demit
                if emit > 0.0:
                    lbl_s = self._font_small.render(
                        "resonance_emit", True, STONE_BLUE)
                    val_s = self._font_small.render(
                        f"{emit:.2f}", True, SLATE_MID)
                    popup.blit(lbl_s, (UI_PANEL_INSET, y))
                    popup.blit(val_s, (UI_PANEL_INSET + lbl_s.get_width() + 8, y))
                    y += 14

        # Stats for items
        if subject["type"] == "item":
            entity  = subject.get("entity")
            item_id = getattr(entity, "item_id", None)
            item_def = engine.data.items.get(item_id, {}) if item_id else {}
            category = item_def.get("category", "")
            slot     = item_def.get("slot", "")

            # Local stat-line renderer
            label_col_w = 80   # px reserved for label
            value_col_x = UI_PANEL_INSET + label_col_w

            def render_stat_line(label: str, value: str) -> None:
                nonlocal y
                lbl_s = self._font_small.render(label, True, STONE_BLUE)
                val_s = self._font_small.render(value, True, FROST_WHITE)
                popup.blit(lbl_s, (UI_PANEL_INSET, y))
                popup.blit(val_s, (value_col_x, y))
                y += 14

            if category == "weapon":
                dice    = item_def.get("damage_dice", "\u2014")
                bonus   = item_def.get("damage_bonus", 0)
                dmg_str = f"{dice}+{bonus}" if bonus else dice
                render_stat_line("Damage", dmg_str)
                essence  = item_def.get("essence")
                strength = item_def.get("essence_strength", 0.0)
                if essence:
                    pips  = round(strength * 5)
                    lbl_s = self._font_small.render("Essence", True, STONE_BLUE)
                    popup.blit(lbl_s, (UI_PANEL_INSET, y))
                    ess_s = self._font_small.render(essence + "  ", True, FROST_WHITE)
                    popup.blit(ess_s, (value_col_x, y))
                    pip_x   = value_col_x + ess_s.get_width()
                    pip_r   = max(1, 4)
                    pip_gap = 11
                    cy      = y + 7
                    for i in range(5):
                        cx = pip_x + i * pip_gap + pip_r
                        if i < pips:
                            pygame.draw.circle(popup, SLATE_MID, (cx, cy), pip_r)
                        else:
                            pygame.draw.circle(popup, MIDNIGHT_DEEP, (cx, cy), pip_r)
                            pygame.draw.circle(popup, SLATE_MID, (cx, cy), pip_r, 1)
                    y += 14
                render_stat_line("Slot",   item_def.get("slot", "\u2014").replace("_", " ").title())
                render_stat_line("Weight", f"{item_def.get('weight', 0)}kg")

            elif category == "armor":
                slot_label = slot.replace("_", " ").replace("armor ", "").title()
                render_stat_line("Slot", slot_label)
                layers = item_def.get("armor_layers", [])
                for layer in layers:
                    av   = layer.get("armor_value", 0)
                    cov  = layer.get("coverage", 1.0)
                    mat  = layer.get("material", "").title()
                    # Draw coverage bar as rects
                    bar_total = max(1, 64)
                    bar_h_px  = 5
                    filled    = max(0, min(int(cov * bar_total), bar_total))
                    lbl_s = self._font_small.render(layer["name"], True, STONE_BLUE)
                    popup.blit(lbl_s, (UI_PANEL_INSET, y))
                    bar_y_px = y + 3
                    pygame.draw.rect(popup, SLATE_DARK,
                                     (value_col_x, bar_y_px, bar_total, bar_h_px))
                    pygame.draw.rect(popup, SLATE_MID,
                                     (value_col_x, bar_y_px, filled, bar_h_px))
                    av_s = self._font_small.render(f"  AV {av}  {mat}", True, FROST_WHITE)
                    popup.blit(av_s, (value_col_x + bar_total + 4, y))
                    y += 14
                render_stat_line("Weight", f"{item_def.get('weight', 0)}kg")

            elif category in ("tool", "consumable"):
                render_stat_line("Weight", f"{item_def.get('weight', 0)}kg")
                on_use = item_def.get("on_use", "")
                if on_use and on_use not in ("equip_toggle",):
                    render_stat_line("Use", on_use.replace("_", " ").title())

            elif slot.startswith("belt"):
                render_stat_line("Slot",   "Belt")
                render_stat_line("Weight", f"{item_def.get('weight', 0)}kg")

            # Equipped tag
            equip = getattr(engine.player, "equipment", None)
            if equip and entity and equip.is_equipped(entity):
                eq_s = self._font_small.render("[Equipped]", True, OLD_GOLD)
                popup.blit(eq_s, (UI_PANEL_INSET, y))
                y += 14

        # Stats for the player — always shown
        elif subject["type"] == "player":
            fighter = subject.get("fighter")
            if fighter:
                stat_str = (f"HP: {fighter.hp}/{fighter.max_hp}   "
                            f"Power: {fighter.power}   "
                            f"Defense: {fighter.defense}")
                s = self._font_small.render(stat_str, True, self.EXAMINE_STAT)
                popup.blit(s, (UI_PANEL_INSET, y))
                y += 16

        # Stats for creatures
        elif subject["type"] == "creature":
            fighter  = subject.get("fighter")
            faction  = subject.get("faction",  "unknown")
            ai_state = subject.get("ai_state", "unknown")
            entity   = subject.get("entity")

            from config import DEBUG_MODE

            if fighter and _can_see_exact_hp(engine, entity):
                # Single HP bar
                bar_total_w = 80
                bar_h       = 6
                frac        = fighter.hp_fraction
                color       = LIFE_GREEN if frac > 0.5 else \
                              OLD_GOLD   if frac > 0.25 else \
                              DUSTY_ROSE
                filled_w    = int(frac * bar_total_w)

                label = self._font_small.render("HP", True, self.EXAMINE_DIM)
                popup.blit(label, (UI_PANEL_INSET, y))

                bar_x = UI_PANEL_INSET + 80
                bar_y = y + 2
                pygame.draw.rect(popup, SLATE_DARK, (bar_x, bar_y, bar_total_w, bar_h))
                pygame.draw.rect(popup, color,      (bar_x, bar_y, filled_w,    bar_h))

                hp_text = self._font_small.render(
                    f"{fighter.hp}/{fighter.max_hp}", True, color
                )
                popup.blit(hp_text, (bar_x + bar_total_w + 6, y))
                y += 14

                # Speed comparison — directly after HP
                creature_def   = engine.data.entities.get(creature_id(entity), {})
                _spd = creature_def.get("speed", 1.0)
                if _spd < 0.5:
                    _spd_text = "It moves as though mired. You could walk away."
                elif _spd < 0.75:
                    _spd_text = "Its pace is laboured. You are swifter."
                elif _spd < 0.95:
                    _spd_text = "Slower than you, but not by much."
                elif _spd <= 1.05:
                    _spd_text = "It matches your pace."
                elif _spd <= 1.25:
                    _spd_text = "It is faster than you."
                else:
                    _spd_text = "It is much faster. Do not let it close."
                _show_num = DEBUG_MODE
                if not _show_num:
                    _perks = getattr(engine.player, "perks", None)
                    if _perks and _perks.has("carrion_eye"):
                        _show_num = True
                if _show_num:
                    _spd_text += f" ({_spd})"
                popup.blit(
                    self._font_small.render(_spd_text, True, UI_TEXT_MID),
                    (UI_PANEL_INSET, y),
                )
                y += 14

                # Revealed knowledge (from revelation_lens or creature_knowledge)
                _ck = getattr(engine, "creature_knowledge", {}).get(
                    creature_id(entity), {})
                _show_ck = DEBUG_MODE or _ck
                if not _show_ck:
                    _perks_ck = getattr(engine.player, "perks", None)
                    _show_ck = (_perks_ck and _perks_ck.has("carrion_eye"))
                if not _show_ck:
                    _thresholds_ck = getattr(engine, "_corruption_thresholds", set())
                    _show_ck = "threshold_resonance_sight" in _thresholds_ck
                if _show_ck and _ck:
                    for _rw in _ck.get("revealed_weaknesses", []):
                        popup.blit(
                            self._font_small.render(f"Weak to: {_rw}", True, LIFE_GREEN),
                            (UI_PANEL_INSET, y),
                        )
                        y += 13
                    for _rs in _ck.get("revealed_strengths", []):
                        popup.blit(
                            self._font_small.render(f"Resists: {_rs}", True, DUSTY_ROSE),
                            (UI_PANEL_INSET, y),
                        )
                        y += 13

                # Essence profile — visible with true_sight or DEBUG_MODE
                essence_mods   = creature_def.get("essence_modifiers", {})
                if essence_mods:
                    y += 4
                    popup.blit(
                        self._font_small.render("Essence:", True, STONE_BLUE),
                        (UI_PANEL_INSET, y),
                    )
                    y += 14
                    _ESSENCES = [
                        "Dissolution", "Quickening", "Binding",
                        "Severance",   "Consumption", "Revelation",
                    ]
                    for ess in _ESSENCES:
                        mod = essence_mods.get(ess, 1.0)
                        if mod >= 1.8:
                            indicator = "++"
                            col = LIFE_GREEN
                        elif mod >= 1.3:
                            indicator = "+"
                            col = OLD_GOLD
                        elif mod <= 0.3:
                            indicator = "--"
                            col = BLOOD_STONE
                        elif mod <= 0.6:
                            indicator = "-"
                            col = DUSTY_ROSE
                        else:
                            indicator = "="
                            col = STONE_BLUE
                        line = self._font_small.render(
                            f"  {ess:<12} {indicator}", True, col
                        )
                        popup.blit(line, (UI_PANEL_INSET, y))
                        y += 13
                    y += 4

                if DEBUG_MODE:
                    info_str = f"Faction: {faction}   State: {ai_state}"
                    popup.blit(
                        self._font_small.render(info_str, True, self.EXAMINE_DIM),
                        (UI_PANEL_INSET, y),
                    )
                    y += 16

            elif fighter:
                # Single status word derived from total HP percentage
                frac = fighter.hp / fighter.max_hp if fighter.max_hp > 0 else 0.0
                if frac > 0.75:
                    status_word  = "Unmarked"
                    status_color = LIFE_GREEN
                elif frac > 0.5:
                    status_word  = "Bloodied"
                    status_color = OLD_GOLD
                elif frac > 0.25:
                    status_word  = "Grievous"
                    status_color = OLD_GOLD
                elif frac > 0.0:
                    status_word  = "Failing"
                    status_color = DUSTY_ROSE
                else:
                    status_word  = "Undone"
                    status_color = BLOOD_STONE

                label_surf  = self._font_small.render("Bearing: ", True, STONE_BLUE)
                status_surf = self._font_small.render(status_word, True, status_color)
                popup.blit(label_surf,  (UI_PANEL_INSET, y))
                popup.blit(status_surf, (UI_PANEL_INSET + label_surf.get_width(), y))
                y += 16

        # Footer — positioned inside the panel border (UI_PANEL_INSET from bottom)
        _footer_text_h = 14   # small font nominal height
        _footer_y = ph - UI_PANEL_INSET - _footer_text_h
        _divider_y = _footer_y - 5
        pygame.draw.line(popup, self.EXAMINE_BORDER,
                         (UI_PANEL_INSET, _divider_y),
                         (pw - UI_PANEL_INSET, _divider_y), 1)
        n = len(things)
        if n > 1:
            footer_text = (f"Tab / N \u00b7 P to cycle  ({idx + 1}/{n})   "
                           f"ESC / X to close")
        else:
            footer_text = "ESC / X to close"
        footer = self._font_small.render(footer_text, True, self.EXAMINE_DIM)
        popup.blit(footer, (UI_PANEL_INSET, _footer_y))

        surface.blit(popup, (px, py))
