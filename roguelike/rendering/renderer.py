# rendering/renderer.py
from __future__ import annotations
import pygame
import random
import math
from typing import TYPE_CHECKING
from config import UI_PANEL_INSET
from rendering.decor import get_procedural_key
from engine.palette import *

if TYPE_CHECKING:
    from world.local_map import LocalMap
    from world.world_map import WorldMap
    from entities.entity import Entity
    from rendering.tile_registry import TileRegistry
    from rendering.sprite_registry import SpriteRegistry
    from engine.display_config import DisplayConfig

class Renderer:
    """
    Dual-mode renderer: ASCII or sprite.
    Controlled by display.render_mode ("ascii" or "sprite").

    Sprite colouring modes (controlled by display.use_sprite_tint):

      use_sprite_tint = True  (1-bit / white-on-transparent sheets):
        White pixels × fg_color → tinted sprite.
        fg_color from tiles.json drives the creature/terrain colour.
        Lighting modulates fg_color before the multiply.
        Memory tiles: fg darkened to ~15% brightness.

      use_sprite_tint = False  (full-colour / pre-coloured sheets):
        Sprite pixels rendered as-is (true colour preserved).
        A light overlay is multiplied on top for lighting.
        Memory tiles: sprite darkened to ~15% brightness via overlay.
        fg_color from tiles.json is NOT applied — colour is in the art.

    Adding sprite support for a new tile:
      1. Find tile coordinates on sheet using sprite_ref.py
      2. Add entry to data/sprites/sprite_map.json
      3. Done — no code changes needed

    Layer order (both modes):
      Layer 0: terrain (floor, walls, water)
      Layer 1: entities (items → creatures → player)
    """

    def __init__(
        self,
        registry:        "TileRegistry",
        display:         "DisplayConfig",
        sprite_registry: "SpriteRegistry | None" = None,
    ) -> None:
        self.registry        = registry
        self.display         = display
        self.sprite_registry = sprite_registry
        # Weather tile-layer overlay — single surface, absolute-time grid scroll
        self._weather_surf:      "pygame.Surface | None" = None
        self._weather_surf_size: tuple[int, int]         = (0, 0)
        # Resonance storm glyph overlay
        self._storm_glyphs:      list                    = []
        self._storm_last_state:  str                     = ""
        # Resonance storm edge vignette cache
        self._storm_vignette:           "pygame.Surface | None" = None
        self._storm_vignette_intensity: float                   = -1.0
        self._storm_vignette_size:      tuple[int, int]         = (0, 0)

    @property
    def _sprite_mode(self) -> bool:
        return (
            self.display.render_mode == "sprite" and
            self.sprite_registry is not None and
            self.sprite_registry._loaded
        )

    # ------------------------------------------------------------------ #
    #  Tile size helpers
    # ------------------------------------------------------------------ #

    def _tile_wh(self) -> tuple[int, int]:
        """Native tile size (before zoom)."""
        if self._sprite_mode:
            return self.sprite_registry.tile_size()
        return (
            self.display.font_sheet.tile_width,
            self.display.font_sheet.tile_height,
        )



    # ------------------------------------------------------------------ #
    #  ASCII glyph drawing
    # ------------------------------------------------------------------ #

    def _draw_glyph(
        self,
        surface: pygame.Surface,
        char:    str,
        fg:      tuple[int, int, int],
        bg:      tuple[int, int, int] | None,
        tx:      int,
        ty:      int,
    ) -> None:
        fs  = self.display.font_sheet
        tw  = fs.tile_width
        th  = fs.tile_height
        px  = tx * tw
        py  = ty * th
        if bg is not None:
            pygame.draw.rect(surface, bg, (px, py, tw, th))
        glyph = fs.get_glyph_char(char).copy()
        tint  = pygame.Surface((tw, th), pygame.SRCALPHA)
        tint.fill((*fg, 255))
        glyph.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(glyph, (px, py))

    # ------------------------------------------------------------------ #
    #  Sprite drawing
    # ------------------------------------------------------------------ #

    def _draw_sprite(
        self,
        surface:  pygame.Surface,
        tile_id:  str,
        fg:       tuple[int, int, int] | None,
        bg:       tuple[int, int, int] | None,
        tx:       int,
        ty:       int,
        zoom:     int = 1,
        alpha:    int = 255,
    ) -> None:
        """
        Draw a sprite at tile grid position (tx, ty).

        use_sprite_tint = True (1-bit white sheets):
          fg is applied as a multiply tint. Drives tile colour entirely.

        use_sprite_tint = False (full-colour sheets):
          fg is used only as a brightness multiplier (greyscale value).
          fg = TRUE_WHITE → full brightness (lit tile).
          fg = CHAR_BLACK    → memory darkness (~15%).
          fg = None          → no brightness adjustment.

        bg: solid background rect drawn beneath sprite, or None.
        alpha: overall surface opacity.
        """
        sr       = self.sprite_registry
        tw, th   = sr.tile_size(tile_id)
        px       = tx * tw * zoom
        py       = ty * th * zoom
        use_tint = getattr(self.display, "use_sprite_tint", True)

        # Background rect
        if bg is not None:
            pygame.draw.rect(surface, bg, (px, py, tw * zoom, th * zoom))

        if use_tint:
            # 1-bit mode: fg colour is applied as multiply tint
            tint_color = fg if fg is not None else TRUE_WHITE
            sprite = sr.get_tinted(tile_id, tint_color, zoom=zoom)
        else:
            # Full-colour mode: get raw sprite, apply brightness separately
            sprite = sr.get(tile_id, zoom=zoom)

        if sprite is None:
            # Fallback to ASCII
            if tile_id in self.registry._data:
                ch  = chr(self.registry.char(tile_id))
                afg = self.registry.fg(tile_id)
                abg = self.registry.bg(tile_id)
                self._draw_glyph(surface, ch, afg, abg, tx, ty)
            return

        # Full-colour mode: apply brightness overlay if fg provided
        if not use_tint and fg is not None:
            brightness = fg[0]  # fg is greyscale (r==g==b expected)
            if brightness < 255:
                sprite = sprite.copy()
                overlay = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                overlay.fill((brightness, brightness, brightness, 255))
                sprite.blit(overlay, (0, 0),
                            special_flags=pygame.BLEND_RGBA_MULT)

        if alpha < 255:
            sprite = sprite.copy()
            sprite.set_alpha(alpha)

        surface.blit(sprite, (px, py))

    # ------------------------------------------------------------------ #
    #  Light colour helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _apply_light(
        base_color: tuple[int, int, int],
        light:      tuple[float, float, float],
        dark:       bool,
    ) -> tuple[int, int, int]:
        """
        Modulate a colour by light map values.
        dark=True: explored-but-unlit dimming.
        """
        if dark:
            return (
                int(base_color[0] * 0.8),
                int(base_color[1] * 0.8),
                int(base_color[2] * 0.8),
            )
        lr, lg, lb = light
        intensity  = max(lr, lg, lb)
        if intensity < 0.05:
            return (
                int(base_color[0] * 0.05),
                int(base_color[1] * 0.05),
                int(base_color[2] * 0.05),
            )
        return (
            min(255, int(base_color[0] * (0.3 + 0.7 * lr))),
            min(255, int(base_color[1] * (0.3 + 0.7 * lg))),
            min(255, int(base_color[2] * (0.3 + 0.7 * lb))),
        )

    @staticmethod
    def _light_to_brightness(
        light: tuple[float, float, float],
    ) -> int:
        """
        Convert a light map value to a greyscale brightness (0-255).
        Used in full-colour mode to produce a greyscale overlay.
        """
        intensity = max(light[0], light[1], light[2])
        if intensity < 0.05:
            return int(255 * 0.05)
        # 30% ambient + 70% light-driven
        val = 0.3 + 0.7 * intensity
        return min(255, int(255 * val))

    # ------------------------------------------------------------------ #
    #  Local map render
    # ------------------------------------------------------------------ #

    def render(
        self,
        display_surface: pygame.Surface,
        local_map:       "LocalMap",
        entities:        list["Entity"],
        cam_x:           int,
        cam_y:           int,
        viewport_rect:   pygame.Rect | None = None,
        shake_offset:    tuple[int, int]    = (0, 0),
        visual_events:   list | None        = None,
        void_rect:       pygame.Rect | None = None,
        player_x:        int                = -999,
        player_y:        int                = -999,
    ) -> None:
        if viewport_rect is None:
            viewport_rect = display_surface.get_rect()
        if void_rect is None:
            void_rect = viewport_rect
        _ = visual_events  # reserved — Tier 3

        display_surface.fill(VOID_BLACK, void_rect)

        zoom   = self.display.zoom_level
        tw, th = self._tile_wh()
        vw     = viewport_rect.width
        vh     = viewport_rect.height

        tiles_x = (vw  + zoom - 1) // (tw * zoom) + 1
        tiles_y = (vh  + zoom - 1) // (th * zoom) + 1
        disp_w  = tiles_x * tw * zoom
        disp_h  = tiles_y * th * zoom

        terrain_surf = pygame.Surface((disp_w, disp_h))
        terrain_surf.fill(VOID_BLACK)
        # Pass active light colour for tinting in full-colour mode
        light_color = TRUE_WHITE  # default: white/neutral
        for e in entities:
            if e.name == "Player":
                ls = getattr(e, "light_source", None)
                if ls and ls.active and hasattr(ls, "color"):
                    light_color = ls.color
                break

        self._draw_map_to(terrain_surf, local_map,
                          cam_x, cam_y, tiles_x, tiles_y, zoom,
                          light_color=light_color,
                          player_x=player_x, player_y=player_y)

        entity_surf = pygame.Surface((disp_w, disp_h), pygame.SRCALPHA)
        self._draw_entities_to(entity_surf, local_map, entities,
                               cam_x, cam_y, zoom)

        display_surface.set_clip(viewport_rect)
        blit_x = viewport_rect.x + shake_offset[0]
        blit_y = viewport_rect.y + shake_offset[1]
        display_surface.blit(terrain_surf, (blit_x, blit_y))
        display_surface.blit(entity_surf,  (blit_x, blit_y))

        self._draw_wraith_aura(display_surface, entities, local_map,
                               cam_x, cam_y, zoom, blit_x, blit_y)

        display_surface.set_clip(None)

        self._draw_void_pattern(display_surface, local_map,
                                cam_x, cam_y, zoom,
                                draw_rect=void_rect,
                                tile_origin=viewport_rect)

    # ------------------------------------------------------------------ #
    #  Wraith aura overlay
    # ------------------------------------------------------------------ #

    def _draw_wraith_aura(
        self,
        surface:   pygame.Surface,
        entities:  list,
        local_map: "LocalMap",
        cam_x:     int,
        cam_y:     int,
        zoom:      int,
        blit_x:    int,
        blit_y:    int,
    ) -> None:
        """Concentric dotted rings around any visible bog_wraith."""
        import math
        tw, th = self._tile_wh()
        for entity in entities:
            if entity.tile != "bog_wraith":
                continue
            if not local_map.in_bounds(entity.x, entity.y):
                continue
            if not bool(local_map.tiles[entity.x, entity.y]["visible"]):
                continue
            cx = blit_x + (entity.x - cam_x) * tw * zoom + (tw * zoom) // 2
            cy = blit_y + (entity.y - cam_y) * th * zoom + (th * zoom) // 2

            radius_outer = 8 * tw * zoom
            for i in range(80):
                if i % 3 == 2:
                    continue
                angle = (i / 80) * 2 * math.pi
                dx = int(cx + radius_outer * math.cos(angle))
                dy = int(cy + radius_outer * math.sin(angle))
                pygame.draw.circle(surface, DEEP_STONE_BLUE, (dx, dy), 2)

            radius_inner = 4 * tw * zoom
            for i in range(48):
                if i % 2 == 1:
                    continue
                angle = (i / 48) * 2 * math.pi
                dx = int(cx + radius_inner * math.cos(angle))
                dy = int(cy + radius_inner * math.sin(angle))
                pygame.draw.circle(surface, DEEP_STONE_BLUE, (dx, dy), 1)

    # ------------------------------------------------------------------ #
    #  Void dot pattern
    # ------------------------------------------------------------------ #

    def _draw_void_pattern(
        self,
        surface:     pygame.Surface,
        local_map:   "LocalMap",
        cam_x:       int,
        cam_y:       int,
        zoom:        int,
        draw_rect:   pygame.Rect,
        tile_origin: pygame.Rect,
    ) -> None:
        """Sparse organic scatter of faint dots outside the map boundary."""
        import random
        tw, th = self._tile_wh()
        rng = random.Random(cam_x * 7919 + cam_y * 6271)

        dot_count = (draw_rect.width * draw_rect.height) // 400
        dot_count = max(80, min(dot_count, 600))

        for _ in range(dot_count):
            px = rng.randint(draw_rect.x, draw_rect.right - 1)
            py = rng.randint(draw_rect.y, draw_rect.bottom - 1)

            tile_x = (px - tile_origin.x) / (tw * zoom) + cam_x
            tile_y = (py - tile_origin.y) / (th * zoom) + cam_y
            if 0 <= tile_x < local_map.width and 0 <= tile_y < local_map.height:
                continue

            brightness = rng.randint(35, 65)
            color  = (brightness // 4, brightness // 3, brightness)
            radius = 1 if rng.random() < 0.8 else 2
            pygame.draw.circle(surface, color, (px, py), radius)

            if rng.random() < 0.12:
                ox = px + rng.randint(-5, 5)
                oy = py + rng.randint(-5, 5)
                if draw_rect.collidepoint(ox, oy):
                    dim = brightness // 2
                    pygame.draw.circle(surface,
                                       (dim // 4, dim // 3, dim),
                                       (ox, oy), 1)

    # ------------------------------------------------------------------ #
    #  Weather tile-layer overlay  (data-driven — reads data/weather.json)
    # ------------------------------------------------------------------ #

    def draw_weather_overlay(
        self,
        surf:             pygame.Surface,
        viewport_rect:    pygame.Rect,
        weather_state:    str,
        intensity:        float,
        engine,
        player_screen_x:  "int | None" = None,
        player_screen_y:  "int | None" = None,
        tile_w:           int = 24,
        tile_h:           int = 24,
    ) -> None:
        """
        Grid-based scrolling precipitation overlay. All visual properties
        come from engine.data.weather_defs (data/weather.json).
        Adding a new weather type: add an entry to weather.json — no code change.
        player_screen_x/y: player pos relative to viewport top-left (for vignette centre).
        """
        # Clear storm glyphs when weather state changes away from resonance_storm
        if weather_state != self._storm_last_state:
            if self._storm_last_state == "resonance_storm":
                self._storm_glyphs.clear()
            self._storm_last_state = weather_state

        wdef = getattr(engine, "data", None)
        if wdef is None:
            return
        wdef = engine.data.weather_defs.get(weather_state)
        if wdef is None:
            return

        vx, vy = viewport_rect.x, viewport_rect.y
        vw, vh = viewport_rect.width, viewport_rect.height
        now_ms = pygame.time.get_ticks()
        self._draw_precipitation(surf, now_ms, wdef, intensity, vx, vy, vw, vh)

        if weather_state == "resonance_storm":
            # Smooth dark violet radial vignette centred on the player — cached
            _psx = player_screen_x if player_screen_x is not None else vx + vw // 2
            _psy = player_screen_y if player_screen_y is not None else vy + vh // 2
            _vcx = _psx - vx   # player pos relative to viewport
            _vcy = _psy - vy

            _centre_moved = (
                abs(_vcx - getattr(self, "_storm_vignette_cx", -9999)) > tile_w // 2
                or abs(_vcy - getattr(self, "_storm_vignette_cy", -9999)) > tile_h // 2
            )

            if (self._storm_vignette is None
                    or self._storm_vignette_size != (vw, vh)
                    or abs(intensity - self._storm_vignette_intensity) > 0.05
                    or _centre_moved):
                SCALE = 4
                sw2 = vw // SCALE + 1
                sh2 = vh // SCALE + 1
                small = pygame.Surface((sw2, sh2), pygame.SRCALPHA)
                small.fill((0, 0, 0, 0))
                # Centre on player in small-surface space
                scx = _vcx / SCALE
                scy = _vcy / SCALE
                # max_dist: farthest corner from player centre
                corners = [
                    (0 - scx, 0 - scy),
                    (sw2 - scx, 0 - scy),
                    (0 - scx, sh2 - scy),
                    (sw2 - scx, sh2 - scy),
                ]
                s_max_r   = max(math.sqrt(dx*dx + dy*dy) for dx, dy in corners) * 1.05
                s_clear_r = min(vw / SCALE, vh / SCALE) * 0.55
                s_denom   = max(0.001, s_max_r - s_clear_r)
                for sy_px in range(sh2):
                    for sx_px in range(sw2):
                        ddx = sx_px - scx
                        ddy = sy_px - scy
                        dist = math.sqrt(ddx * ddx + ddy * ddy)
                        if dist <= s_clear_r:
                            a = 0
                        elif dist >= s_max_r:
                            a = int(130 * intensity)
                        else:
                            t = (dist - s_clear_r) / s_denom
                            a = int((t ** 2.5) * 130 * intensity)
                        if a > 0:
                            small.set_at((sx_px, sy_px), (60, 20, 100, a))
                self._storm_vignette           = pygame.transform.smoothscale(
                    small, (vw, vh))
                self._storm_vignette_intensity = intensity
                self._storm_vignette_size      = (vw, vh)
                self._storm_vignette_cx        = _vcx
                self._storm_vignette_cy        = _vcy

            pulse  = abs(math.sin(now_ms / 800.0))
            pulsed = self._storm_vignette.copy()
            pulsed.set_alpha(int(200 + pulse * 55))
            surf.blit(pulsed, (vx, vy))
            # Flickering dark glyphs
            self._draw_storm_glyph_overlay(
                surf, now_ms, intensity, vx, vy, vw, vh)

    def _draw_precipitation(
        self,
        surf:     pygame.Surface,
        now_ms:   int,
        wdef:     dict,
        intensity: float,
        vx: int, vy: int, vw: int, vh: int,
    ) -> None:
        """Render one frame of precipitation from a weather definition dict."""
        ptype      = wdef["type"]
        base_sp    = wdef["spacing"]
        color      = tuple(wdef["color"])
        alpha      = wdef["alpha"]

        if wdef.get("intensity_scale", False):
            spacing = max(base_sp // 3,
                          min(base_sp * 3,
                              int(base_sp / max(0.1, intensity))))
        else:
            spacing = base_sp

        if (self._weather_surf is None
                or self._weather_surf_size != (vw, vh)):
            self._weather_surf = pygame.Surface((vw, vh), pygame.SRCALPHA)
            self._weather_surf_size = (vw, vh)
        self._weather_surf.fill((0, 0, 0, 0))

        if ptype == "streak":
            self._draw_streak_grid(
                self._weather_surf, now_ms, wdef,
                spacing, color, alpha, vw, vh)
        elif ptype == "dot":
            self._draw_dot_grid(
                self._weather_surf, now_ms, wdef,
                spacing, color, alpha, vw, vh)

        surf.blit(self._weather_surf, (vx, vy))

    def _draw_streak_grid(
        self,
        surf:    pygame.Surface,
        now_ms:  int,
        wdef:    dict,
        spacing: int,
        color:   tuple,
        alpha:   int,
        vw: int, vh: int,
    ) -> None:
        speed_y    = wdef["speed_y"]
        speed_x    = wdef.get("speed_x", 0)
        streak_len = wdef.get("streak_len", 8)
        width      = wdef.get("width", 1)

        sp = max(1, spacing)

        # Absolute scroll — not modded, needed for stable cell identity
        total_scroll_y = int(now_ms / 1000.0 * speed_y)
        total_scroll_x = int(now_ms / 1000.0 * speed_x)

        # Grid row at the top of the viewport right now
        first_row        = total_scroll_y // sp
        row_pixel_offset = total_scroll_y % sp

        full_color = (*color, alpha)

        for row in range(first_row, first_row + vh // sp + 3):
            for col in range(-1, vw // sp + 2):
                # Fixed cell identity — key is stable for this (row, col) pair
                key = ((col * 2654435761) ^ (row * 2246822519)) & 0xFFFF

                # Sub-cell jitter: fixed per cell, not per frame
                jx = key % sp
                jy = (key >> 8) % sp

                # Screen position this frame — +offset scrolls downward/rightward
                screen_x = col * sp + jx + (total_scroll_x % sp)
                screen_y = (row - first_row) * sp + jy + row_pixel_offset

                if screen_x < -sp or screen_x > vw + sp:
                    continue
                if screen_y < -sp or screen_y > vh + sp:
                    continue

                end_x = screen_x + int(streak_len * speed_x / max(1, speed_y))
                end_y = screen_y + streak_len

                pygame.draw.line(
                    surf, full_color,
                    (max(0, min(vw - 1, screen_x)),
                     max(0, min(vh - 1, screen_y))),
                    (max(0, min(vw - 1, end_x)),
                     max(0, min(vh - 1, end_y))),
                    width,
                )

    def _draw_dot_grid(
        self,
        surf:    pygame.Surface,
        now_ms:  int,
        wdef:    dict,
        spacing: int,
        color:   tuple,
        alpha:   int,
        vw: int, vh: int,
    ) -> None:
        speed_y    = wdef["speed_y"]
        osc_amp    = wdef.get("speed_x_oscillate", 0)
        osc_period = wdef.get("oscillate_period", 2000)
        dot_size   = wdef.get("dot_size", 2)
        full_color = (*color, alpha)

        sp = max(1, spacing)

        total_scroll_y   = int(now_ms / 1000.0 * speed_y)
        first_row        = total_scroll_y // sp
        row_pixel_offset = total_scroll_y % sp

        for row in range(first_row, first_row + vh // sp + 3):
            for col in range(-1, vw // sp + 2):
                # Fixed cell identity
                key = ((col * 1234567) ^ (row * 7654321)) & 0xFFFF

                jx = key % sp
                jy = (key >> 8) % sp

                # Oscillation on screen position only (not cell identity)
                phase = row * 1.3 + col * 0.7
                drift_x = int(math.sin(
                    now_ms / osc_period * math.pi * 2 + phase
                ) * osc_amp)

                screen_x = col * sp + jx + drift_x
                screen_y = (row - first_row) * sp + jy + row_pixel_offset

                if 0 <= screen_x < vw and 0 <= screen_y < vh:
                    pygame.draw.circle(surf, full_color,
                                       (screen_x, screen_y), dot_size)

    def _draw_storm_glyph_overlay(
        self,
        surf:      pygame.Surface,
        now_ms:    float,
        intensity: float,
        vx: int, vy: int, vw: int, vh: int,
    ) -> None:
        """
        Flickering dark archaic glyphs across the screen during resonance_storm.
        Glyphs fade in, hold briefly, then fade out and die.
        Uses a fixed ~60fps dt assumption for simplicity.
        """
        GLYPH_CHARS = [
            "\u2234", "\u2237", "\u25c6", "\u25c7", "\u25aa", "\u25ab",
            "\u2591", "\u2592",
            "\u2502", "\u2500", "\u253c", "\u256b", "\u256c", "\u256a",
            "\u2524", "\u251c",
            "|", "/", "\\", "#", "~", "*",
        ]
        GLYPH_COLORS = [
            DEEP_PURPLE,
            DEEP_PURPLE,
            VOID_PURPLE,
            DEEP_PURPLE,
            VOID_PURPLE,
        ]

        dt = 0.016  # assume ~60fps for glyph system

        # Spawn new glyphs up to target count
        target_count = int(12 * intensity)
        if len(self._storm_glyphs) < target_count:
            rng = random.Random()
            glyph: dict = {
                "char":         rng.choice(GLYPH_CHARS),
                "x":            rng.randint(vx, vx + vw - 20),
                "y":            rng.randint(vy, vy + vh - 20),
                "color":        rng.choice(GLYPH_COLORS),
                "alpha":        rng.randint(60, 140),
                "lifetime":     rng.uniform(0.3, 1.4),
                "max_lifetime": 0.0,
            }
            glyph["max_lifetime"] = glyph["lifetime"]
            self._storm_glyphs.append(glyph)

        font = self.display.font_ui_tiny
        if font is None:
            return

        alive = []
        for g in self._storm_glyphs:
            g["lifetime"] -= dt
            if g["lifetime"] <= 0:
                continue

            frac = 1.0 - g["lifetime"] / g["max_lifetime"]
            if frac < 0.20:
                alpha = int(g["alpha"] * (frac / 0.20))
            elif frac > 0.70:
                alpha = int(g["alpha"] * (1.0 - frac) / 0.30)
            else:
                alpha = g["alpha"]

            r, gr, b = g["color"]
            try:
                glyph_surf = font.render(g["char"], True, (r, gr, b))
                glyph_surf.set_alpha(alpha)
                surf.blit(glyph_surf, (g["x"], g["y"]))
            except Exception:
                pass  # never crash on glyph render

            alive.append(g)

        self._storm_glyphs = alive

    # ------------------------------------------------------------------ #
    #  Visual FX helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_fx_brightness(fx: str, ticks: int, mx: int, my: int) -> float:
        """
        Return a brightness multiplier for the given visual_fx type.
        Values >1.0 brighten; <1.0 dim.  Returns 1.0 for non-brightness FX.
        """
        if fx == "pulse_glow":
            # Slow sine pulse — same logic as the old bell pulse
            phase = (ticks // 400 + mx * 3 + my * 7) % 20
            intensity = phase if phase < 10 else 20 - phase
            return 1.0 + intensity * 0.015
        if fx == "pulse_dim":
            phase = (ticks // 500 + mx * 5 + my * 11) % 20
            intensity = phase if phase < 10 else 20 - phase
            return 1.0 - intensity * 0.012
        if fx == "flicker":
            rng = random.Random(ticks // 2 + mx * 7 + my * 3)
            return 1.0 + rng.uniform(-0.15, 0.08)
        return 1.0  # sparkle, gas_overlay, unknown

    # ------------------------------------------------------------------ #
    #  Map tile rendering
    # ------------------------------------------------------------------ #

    def _draw_map_to(
        self,
        surface:     pygame.Surface,
        local_map:   "LocalMap",
        cam_x:       int,
        cam_y:       int,
        tiles_x:     int,
        tiles_y:     int,
        zoom:        int = 1,
        light_color: tuple[int,int,int] = TRUE_WHITE,
        player_x:    int = -999,
        player_y:    int = -999,
    ) -> None:
        has_lm    = hasattr(local_map, "light_map")
        use_tint  = getattr(self.display, "use_sprite_tint", True)
        # Normalise light colour to 0.0-1.0 for blending
        lc_r = light_color[0] / 255.0
        lc_g = light_color[1] / 255.0
        lc_b = light_color[2] / 255.0

        for tx in range(tiles_x):
            for ty in range(tiles_y):
                mx = tx + cam_x
                my = ty + cam_y
                if not local_map.in_bounds(mx, my):
                    continue

                tile    = local_map.tiles[mx, my]
                vis     = bool(tile["visible"])
                exp     = bool(tile["explored"])
                terrain = str(tile["terrain"])

                if not vis and not exp:
                    continue

                name = terrain

                if self._sprite_mode:
                    # Resolve colours from tiles.json (used for bg and tint mode)
                    if name in self.registry._data:
                        fg_base = self.registry.fg(name, dark=False)
                        bg_base = self.registry.bg(name, dark=False)
                    else:
                        fg_base = STEEL_WATER
                        bg_base = VOID_BLACK

                    if use_tint:
                        # ── 1-bit tint mode ───────────────────────────────
                        # fg drives tile colour; lighting modulates fg
                        if vis and has_lm:
                            lm    = local_map.light_map[mx, my]
                            light = (float(lm[0]), float(lm[1]), float(lm[2]))
                            fg    = self._apply_light(fg_base, light, dark=False)
                            bg    = self._apply_light(bg_base, light, dark=False)
                        elif vis:
                            fg = fg_base
                            bg = bg_base
                        else:
                            # Memory tile — darken fg
                            fg = (
                                min(45, int(fg_base[0] * 0.25)),
                                min(45, int(fg_base[1] * 0.25)),
                                min(45, int(fg_base[2] * 0.25)),
                            )
                            bg = (
                                min(45, int(bg_base[0] * 0.25)),
                                min(45, int(bg_base[1] * 0.25)),
                                min(45, int(bg_base[2] * 0.25)),
                            )
                    else:
                        # ── Full-colour mode ──────────────────────────────
                        # Light map drives brightness. Light source colour
                        # (lc_r/g/b) drives tint — passed from the active
                        # light source directly, not from the light map RGB.
                        if vis and has_lm:
                            lm        = local_map.light_map[mx, my]
                            intensity = max(float(lm[0]), float(lm[1]),
                                           float(lm[2]))
                            if intensity < 0.05:
                                # Barely lit — very dim, cool
                                fg = VOID_BLACK
                            else:
                                # Brightness: 30% ambient + 70% light-driven
                                brightness = 0.3 + 0.7 * intensity
                                # Tint: blend neutral brightness with light colour
                                # 65% neutral preserves sprite colour, 35% tint
                                # adds torch warmth / other light character
                                fg = (
                                    min(255, int(255 * (brightness * 0.65
                                                        + lc_r * brightness * 0.35))),
                                    min(255, int(255 * (brightness * 0.65
                                                        + lc_g * brightness * 0.35))),
                                    min(255, int(255 * (brightness * 0.65
                                                        + lc_b * brightness * 0.35))),
                                )
                            bg = None
                        elif vis:
                            # Visible but no light map — full neutral brightness
                            fg = TRUE_WHITE
                            bg = None
                        else:
                            # Memory tile — dark, cool blue cast
                            fg = DUNGEON_SHADOW
                            bg = None

                    # 1. Resolve procedural name (intercepts "grass" or "tree" here)
                    decorated_name = get_procedural_key(mx, my, terrain)

                    # 2. Skip rendering if the result is None (Void)
                    if decorated_name is None:
                        continue

                    # 3. Determine the specific sprite variant (Autotiling)
                    if any(key in decorated_name for key in ["wall", "water", "rock"]):
                        variant_name = self._get_autotile_name(local_map, mx, my, decorated_name)
                        sprite_name = variant_name if self.sprite_registry.has(variant_name) else decorated_name
                    elif decorated_name.startswith("road"):
                        variant_name = self._get_road_autotile_name(local_map, mx, my)
                        sprite_name = variant_name if self.sprite_registry.has(variant_name) else decorated_name
                    else:
                        sprite_name = decorated_name

                    # Visual FX — brightness mod applied before sprite draw
                    _fx = self.registry._data.get(terrain, {}).get("visual_fx")
                    if _fx and vis:
                        _ticks = pygame.time.get_ticks()
                        _bmod  = self._get_fx_brightness(_fx, _ticks, mx, my)
                        if _bmod != 1.0 and fg is not None:
                            fg = (
                                min(255, int(fg[0] * _bmod)),
                                min(255, int(fg[1] * _bmod)),
                                min(255, int(fg[2] * _bmod)),
                            )

                    # 4. Draw the resolved sprite
                    self._draw_sprite(surface, sprite_name,
                                      fg, None, tx, ty, zoom=zoom)

                else:
                    # ASCII mode — unchanged
                    dark = not vis
                    if name not in self.registry._data:
                        name = terrain
                    if name not in self.registry._data:
                        continue
                    fg   = self.registry.fg(name, dark=dark)
                    bg   = self.registry.bg(name, dark=dark)
                    char = chr(self.registry.char(name))

                    # Visual FX in ASCII mode
                    _fx = self.registry._data.get(terrain, {}).get("visual_fx")
                    if _fx and vis:
                        _ticks = pygame.time.get_ticks()
                        _bmod  = self._get_fx_brightness(_fx, _ticks, mx, my)
                        if _bmod != 1.0:
                            fg = (
                                min(255, int(fg[0] * _bmod)),
                                min(255, int(fg[1] * _bmod)),
                                min(255, int(fg[2] * _bmod)),
                            )

                    self._draw_glyph(surface, char, fg, bg, tx, ty)

    # ------------------------------------------------------------------ #
    #  Entity rendering
    # ------------------------------------------------------------------ #

    def _draw_entities_to(
        self,
        surface:   pygame.Surface,
        local_map: "LocalMap",
        entities:  list,
        cam_x:     int,
        cam_y:     int,
        zoom:      int,
    ) -> None:
        GHOST_COLOR = MIDNIGHT_DEEP
        use_tint    = getattr(self.display, "use_sprite_tint", True)

        def priority(e) -> int:
            if e.name == "Player": return 2
            if getattr(e, "ai", None): return 1
            return 0

        # Pass 1 — last known position ghosts
        for entity in entities:
            if entity.name == "Player":
                continue
            if getattr(entity, "ai", None) is None:
                continue

            lkx = getattr(entity, "last_known_x", None)
            lky = getattr(entity, "last_known_y", None)
            if lkx is None or lky is None:
                continue

            if local_map.in_bounds(entity.x, entity.y):
                if bool(local_map.tiles[entity.x, entity.y]["visible"]):
                    continue

            if not local_map.in_bounds(lkx, lky):
                continue
            if not bool(local_map.tiles[lkx, lky]["explored"]):
                continue
            if bool(local_map.tiles[lkx, lky]["visible"]):
                continue

            tx = lkx - cam_x
            ty = lky - cam_y
            if self._sprite_mode:
                self._draw_sprite(surface, entity.tile,
                                  GHOST_COLOR, None, tx, ty, zoom=zoom)
            else:
                char = chr(self.registry.char(entity.tile))
                self._draw_glyph(surface, char, GHOST_COLOR, None, tx, ty)

        # Pass 2 — live visible entities
        ticks = pygame.time.get_ticks()
        for entity in sorted(entities, key=priority):
            if not local_map.in_bounds(entity.x, entity.y):
                continue
            if not bool(local_map.tiles[entity.x, entity.y]["visible"]):
                continue

            tx = entity.x - cam_x
            ty = entity.y - cam_y

            _efx   = self.registry._data.get(entity.tile, {}).get("visual_fx")
            _ebmod = self._get_fx_brightness(_efx, ticks, tx, ty) if _efx else 1.0

            if self._sprite_mode:
                if use_tint:
                    # 1-bit: apply fg colour tint from tiles.json
                    fg = self.registry.fg(entity.tile) \
                        if entity.tile in self.registry._data \
                        else TRUE_WHITE
                else:
                    # Full-colour: full brightness, no colour tint
                    fg = TRUE_WHITE

                if _ebmod != 1.0 and fg is not None:
                    fg = (
                        min(255, int(fg[0] * _ebmod)),
                        min(255, int(fg[1] * _ebmod)),
                        min(255, int(fg[2] * _ebmod)),
                    )

                self._draw_sprite(surface, entity.tile,
                                  fg, None, tx, ty, zoom=zoom)
            else:
                char = chr(self.registry.char(entity.tile))
                fg   = self.registry.fg(entity.tile)
                if _ebmod != 1.0:
                    fg = (
                        min(255, int(fg[0] * _ebmod)),
                        min(255, int(fg[1] * _ebmod)),
                        min(255, int(fg[2] * _ebmod)),
                    )
                self._draw_glyph(surface, char, fg, None, tx, ty)

    # ------------------------------------------------------------------ #
    #  Overmap
    # ------------------------------------------------------------------ #

    def render_overmap(
        self,
        display_surface: pygame.Surface,
        world_map:       "WorldMap",
        player_wx: int, player_wy: int,
        cam_x: int,     cam_y: int,
        cursor_wx: int | None = None,
        cursor_wy: int | None = None,
        highlight_passages: bool = False,
        viewport: pygame.Rect | None = None,
    ) -> None:
        if viewport is None:
            viewport = display_surface.get_rect()

        display_surface.fill(VOID_BLACK, viewport)

        zoom   = self.display.zoom_level
        tw, th = self._tile_wh()
        vw     = viewport.width
        vh     = viewport.height

        tiles_x  = vw  // (tw * zoom) + 2
        tiles_y  = vh  // (th * zoom) + 2
        native_w = tiles_x * tw
        native_h = tiles_y * th

        surf = pygame.Surface((native_w, native_h))
        surf.fill(VOID_BLACK)
        pygame.draw.rect(surf, VOID_PURPLE, (0, 0, native_w, native_h), 1)

        offset_x = cam_x - tiles_x // 2
        offset_y = cam_y - tiles_y // 2

        for sx in range(tiles_x):
            for sy in range(tiles_y):
                wx = sx + offset_x
                wy = sy + offset_y

                if not world_map.in_bounds(wx, wy):
                    continue
                chunk = world_map.get(wx, wy)
                if not chunk or not chunk.explored:
                    continue
                if wx == player_wx and wy == player_wy:
                    continue  # drawn after overlays
                key = chunk.region_type.overmap_tile()

                if not getattr(self.display, "use_sprite_tint", True):
                    fg = TRUE_WHITE
                else:
                    fg = self.registry.fg(key) if key in self.registry._data else STONE_BLUE

                bg = self.registry.bg(key) if key in self.registry._data else VOID_BLACK
                # Capital ring: override background to blood_rose
                if getattr(chunk, "is_capital", False):
                    bg = BLOOD_STONE

                if self._sprite_mode:
                    self._draw_sprite(surf, key, fg, bg, sx, sy, zoom=1)
                else:
                    if key not in self.registry._data:
                        continue
                    ch = chr(self.registry.char(key))
                    self._draw_glyph(surf, ch, fg, bg, sx, sy)

        if cursor_wx is not None and cursor_wy is not None:
            csx = cursor_wx - offset_x
            csy = cursor_wy - offset_y
            if 0 <= csx < tiles_x and 0 <= csy < tiles_y:
                pygame.draw.rect(
                    surf, OLD_GOLD,
                    (csx * tw + 1, csy * th + 1, tw - 2, th - 2), 1,
                )

        if highlight_passages:
            _SUBMAP_COLOR = COLDBELL_LIGHT
            for sx in range(tiles_x):
                for sy in range(tiles_y):
                    wx = sx + offset_x
                    wy = sy + offset_y
                    chunk = world_map.get(wx, wy)
                    if not chunk or not chunk.submaps:
                        continue
                    dot_x = sx * tw + tw - 3
                    dot_y = sy * th + th - 3
                    pygame.draw.rect(surf, _SUBMAP_COLOR, (dot_x, dot_y, 2, 2))

        # River lines — use stored river_connections for clean branching lines
        road_tiles = getattr(world_map, "road_tiles", {})
        _CYAN = COLDBELL_LIGHT
        for sx in range(tiles_x):
            for sy in range(tiles_y):
                wx = sx + offset_x
                wy = sy + offset_y
                if not world_map.in_bounds(wx, wy):
                    continue
                chunk = world_map.get(wx, wy)
                if not chunk or not chunk.explored or not getattr(chunk, "is_river", False):
                    continue
                cx_ = sx * tw + tw // 2
                cy_ = sy * th + th // 2
                for d in getattr(chunk, "river_connections", []):
                    if   d == "N": em = (sx * tw + tw // 2, sy * th)
                    elif d == "S": em = (sx * tw + tw // 2, sy * th + th)
                    elif d == "E": em = (sx * tw + tw,      sy * th + th // 2)
                    else:          em = (sx * tw,            sy * th + th // 2)
                    pygame.draw.line(surf, _CYAN, (cx_, cy_), em, 3)
                pygame.draw.circle(surf, _CYAN, (cx_, cy_), 2)

        # Road lines — use stored connections for clean path lines
        for sx in range(tiles_x):
            for sy in range(tiles_y):
                wx = sx + offset_x
                wy = sy + offset_y
                if (wx, wy) not in road_tiles:
                    continue
                chunk = world_map.get(wx, wy)
                if not chunk or not chunk.explored:
                    continue
                road_data  = road_tiles[(wx, wy)]
                road_type  = road_data["type"]        if isinstance(road_data, dict) else road_data
                road_conns = road_data["connections"]  if isinstance(road_data, dict) else []
                road_color = EARTH_TONE if road_type == "primary" else EARTH_BROWN
                road_w     = 2             if road_type == "primary" else 1
                cx_ = sx * tw + tw // 2
                cy_ = sy * th + th // 2
                for d in road_conns:
                    if   d == "N": em = (sx * tw + tw // 2, sy * th)
                    elif d == "S": em = (sx * tw + tw // 2, sy * th + th)
                    elif d == "E": em = (sx * tw + tw,      sy * th + th // 2)
                    else:          em = (sx * tw,            sy * th + th // 2)
                    pygame.draw.line(surf, road_color, (cx_, cy_), em, road_w)
                pygame.draw.circle(surf, road_color, (cx_, cy_), 1)

        _LOCUS_COLOR = BLOOD_STONE
        for sx in range(tiles_x):
            for sy in range(tiles_y):
                wx = sx + offset_x
                wy = sy + offset_y
                chunk = world_map.get(wx, wy)
                if chunk and chunk.explored and getattr(chunk, "is_locus", False):
                    cx_ = sx * tw + tw // 2
                    cy_ = sy * th + th // 2
                    for dx_, dy_ in ((0,0),(1,0),(-1,0),(0,1),(0,-1)):
                        px_ = cx_ + dx_
                        py_ = cy_ + dy_
                        if 0 <= px_ < native_w and 0 <= py_ < native_h:
                            surf.set_at((px_, py_), _LOCUS_COLOR)

        # VUKH 2×2 block — old_gold border outline
        _vukh_wx = getattr(world_map, "vukh_x", -1)
        _vukh_wy = getattr(world_map, "vukh_y", -1)
        if _vukh_wx >= 0:
            _vc = world_map.get(_vukh_wx, _vukh_wy)
            if _vc and _vc.explored:
                _vsx = _vukh_wx - offset_x
                _vsy = _vukh_wy - offset_y
                pygame.draw.rect(
                    surf, OLD_GOLD,
                    (_vsx * tw, _vsy * th, tw * 2, th * 2), 1,
                )

        # Player tile — drawn over all overlays
        psx = player_wx - offset_x
        psy = player_wy - offset_y
        if 0 <= psx < tiles_x and 0 <= psy < tiles_y:
            if self._sprite_mode:
                self._draw_sprite(surf, "overmap_player",
                                  TRUE_WHITE, MIDNIGHT_DEEP, psx, psy, zoom=1)
            else:
                if "overmap_player" in self.registry._data:
                    ch = chr(self.registry.char("overmap_player"))
                    self._draw_glyph(surf, ch, TRUE_WHITE, MIDNIGHT_DEEP, psx, psy)

        scaled = pygame.transform.scale(surf, (native_w * zoom, native_h * zoom))
        display_surface.blit(scaled, viewport.topleft)

        # ── Named location labels: towns and VUKH ────────────────────
        _LABEL_COLOR = OLD_GOLD  # old_gold

        if self.display.font_ui_small is not None:
            # Town group labels — one per group, drawn at NW chunk position
            town_groups  = getattr(world_map, "town_groups",  {})
            chunk_names  = getattr(world_map, "chunk_names",  {})
            drawn_groups: set[int] = set()

            for town_id, group in town_groups.items():
                if not group or town_id in drawn_groups:
                    continue
                nw_wx, nw_wy = group[0]
                nw_chunk = world_map.get(nw_wx, nw_wy)
                if not nw_chunk or not nw_chunk.explored:
                    continue
                town_name = chunk_names.get((nw_wx, nw_wy), "")
                if not town_name:
                    continue
                drawn_groups.add(town_id)

                nsx = nw_wx - offset_x
                nsy = nw_wy - offset_y
                if not (0 <= nsx < tiles_x and 0 <= nsy < tiles_y):
                    continue
                lbl = self.display.font_ui_small.render(town_name, True, _LABEL_COLOR)
                lx_ = viewport.x + nsx * tw * zoom + (tw * zoom) - lbl.get_width() // 2
                ly_ = viewport.y + nsy * th * zoom - lbl.get_height()
                if ly_ >= viewport.y:
                    display_surface.blit(lbl, (lx_, ly_))

            # VUKH label — drawn once at NW VUKH chunk
            vukh_wx  = getattr(world_map, "vukh_x", -1)
            vukh_wy  = getattr(world_map, "vukh_y", -1)
            if vukh_wx >= 0:
                vc = world_map.get(vukh_wx, vukh_wy)
                if vc and vc.explored:
                    vsx = vukh_wx - offset_x
                    vsy = vukh_wy - offset_y
                    if 0 <= vsx < tiles_x and 0 <= vsy < tiles_y:
                        vlbl = self.display.font_ui_small.render(
                            "Vukh", True, _LABEL_COLOR
                        )
                        # Centre label over the 2×2 block (offset by 1 tile width)
                        vlx = viewport.x + vsx * tw * zoom + tw * zoom - vlbl.get_width() // 2
                        vly = viewport.y + vsy * th * zoom - vlbl.get_height()
                        if vly >= viewport.y:
                            display_surface.blit(vlbl, (vlx, vly))

        label      = self.display.font_ui_small.render(
            "WORLD MAP  \xb7  M or ESC to close", True, WORN_STONE
        )
        label_rect = label.get_rect(
            topleft=(viewport.x + UI_PANEL_INSET, viewport.y + UI_PANEL_INSET)
        )
        bg_rect  = label_rect.inflate(8, 4)
        bg_surf  = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill(VOID_BLACK + (200,))
        display_surface.blit(bg_surf,  bg_rect.topleft)
        display_surface.blit(label,    label_rect.topleft)

    # ------------------------------------------------------------------ #
    #  Overmap sidebar
    # ------------------------------------------------------------------ #

    def render_overmap_sidebar(
        self,
        surface:      pygame.Surface,
        sidebar_rect: pygame.Rect,
        world_map,
        cursor_wx:    int,
        cursor_wy:    int,
        player_wx:    int,
        player_wy:    int,
        engine,
    ) -> None:
        from rendering.biome_icons import get_biome_icon
        from config import DEBUG_MODE

        if hasattr(engine, "ui_registry") and engine.ui_registry._loaded:
            engine.ui_registry.draw_panel(
                surface, sidebar_rect, "weathered_temple",
                tint_color=STONE_BLUE,
                fill_color=VOID_BLACK,
                fill_alpha=245,
            )

        sx  = sidebar_rect.x + UI_PANEL_INSET
        sw  = sidebar_rect.width - UI_PANEL_INSET * 2
        y   = sidebar_rect.y + UI_PANEL_INSET

        fn  = self.display.font_ui_normal
        fs  = self.display.font_ui_small
        fl  = self.display.font_ui_large
        fb  = getattr(self.display, "font_ui_bold_large", fl)
        lh  = fn.get_linesize()
        slh = fs.get_linesize()

        chunk = world_map.get(cursor_wx, cursor_wy)

        if chunk and chunk.name:
            name_surf = fb.render(chunk.name, True, WORN_STONE)
        elif chunk:
            name_surf = fb.render(chunk.region_type.value.title(), True, WORN_STONE)
        else:
            name_surf = fb.render("Unknown", True, EARTH_BROWN)
        surface.blit(name_surf, (sx, y))
        y += name_surf.get_height() + 4

        if chunk:
            explored_tag = " [explored]" if chunk.explored else " [unexplored]"
            rt_surf = fs.render(
                chunk.region_type.value + explored_tag, True, VERDANT_MID
            )
            surface.blit(rt_surf, (sx, y))
        y += slh + 2

        if chunk and getattr(chunk, "is_locus", False):
            locus_surf = fs.render("[LOCUS]", True, BLOOD_STONE)
            surface.blit(locus_surf, (sx, y))
            y += slh + 2

        pygame.draw.line(surface, DEEP_STONE_BLUE, (sx, y), (sx + sw, y), 1)
        y += 8

        if chunk and chunk.explored:
            region_str = chunk.region_type.value
            icon = get_biome_icon(region_str, seed=chunk.seed % 10000)
            icon_scaled = pygame.transform.scale(icon, (48, 48))
            surface.blit(icon_scaled, (sx, y))

            tx = sx + 56
            biome_surf = fn.render(region_str.title(), True, WORN_STONE)
            surface.blit(biome_surf, (tx, y + 4))

            zone_str = ""
            if chunk.zones:
                zone_str = chunk.zones[0][0].replace("_", " ")
            if zone_str:
                zone_surf = fs.render(zone_str, True, VERDANT_MID)
                surface.blit(zone_surf, (tx, y + 4 + lh))

            if chunk.difficulty > 0 or chunk.resonance > 0:
                diff_surf = fs.render(
                    f"Difficulty: {chunk.difficulty:.2f}  "
                    f"Resonance: {chunk.resonance:.2f}",
                    True, VERDANT_MID,
                )
                surface.blit(diff_surf, (sx, y + 52))

            if getattr(chunk, "is_river", False):
                river_surf = fs.render("~ River", True, COLDBELL_LIGHT)
                surface.blit(river_surf, (tx, y + 4 + lh + lh))

            y += 56
        else:
            unknown = fn.render("— not yet explored —", True, DUNGEON_SHADOW)
            surface.blit(unknown, (sx, y))
            y += lh + 4

        pygame.draw.line(surface, DEEP_STONE_BLUE, (sx, y), (sx + sw, y), 1)
        y += 8

        myth = getattr(world_map, "myth", None)
        if myth:
            age_surf = fs.render(myth.age_name, True, BLOOD_STONE)
            surface.blit(age_surf, (sx, y))
            y += slh

            shape_surf = fs.render(myth.myth_shape, True, BLOOD_DARK)
            surface.blit(shape_surf, (sx, y))
            y += slh

            sunder_surf = fs.render(myth.sundering_epithet, True, SLATE_DARK)
            surface.blit(sunder_surf, (sx, y))
            y += slh + 4

            pygame.draw.line(surface, DEEP_STONE_BLUE, (sx, y), (sx + sw, y), 1)
            y += 8

        td = getattr(chunk, "town_data", None) if chunk else None
        if td:
            bell_colors = {
                "intact":    DUSTY_ROSE,
                "cracked":   OLD_GOLD,
                "spent":     STONE_BLUE,
                "missing":   SLATE_DARK,
                "destroyed": SLATE_DARK,
            }
            bell_color = bell_colors.get(td.bell_state, STONE_BLUE)
            bell_surf = fs.render(f"Bell: {td.bell_state}", True, bell_color)
            surface.blit(bell_surf, (sx, y))
            y += slh

            if td.is_festival:
                fest_surf = fs.render(
                    "Festival — was ongoing", True, BLOOD_STONE
                )
                surface.blit(fest_surf, (sx, y))
                y += slh

            districts_str = ", ".join(td.districts)
            dist_surf = fs.render(districts_str, True, SLATE_DARK)
            surface.blit(dist_surf, (sx, y))
            y += slh + 4

            pygame.draw.line(surface, DEEP_STONE_BLUE, (sx, y), (sx + sw, y), 1)
            y += 8

        if chunk and chunk.explored and chunk.submaps:
            for sub in chunk.submaps:
                ent_surf = fn.render(
                    f"> {sub.submap_type} entrance", True, OLD_GOLD
                )
                surface.blit(ent_surf, (sx, y))
                y += lh
                if DEBUG_MODE:
                    name_surf = fs.render(
                        f"  {sub.name or sub.submap_type}", True, BLOOD_STONE
                    )
                    surface.blit(name_surf, (sx, y))
                    y += slh
                    id_surf = fs.render(
                        f"  [{sub.submap_id}]", True, STONE_BLUE
                    )
                    surface.blit(id_surf, (sx, y))
                    y += slh
                    layout_surf = fs.render(
                        f"  layout: {sub.layout_id or 'bsp'}", True, STONE_BLUE
                    )
                    surface.blit(layout_surf, (sx, y))
                    y += slh
            y += 4
            pygame.draw.line(surface, DEEP_STONE_BLUE, (sx, y), (sx + sw, y), 1)
            y += 8

        # Overlay legend — river / road / capital / vukh
        _overlay_legend = [
            ("River",   COLDBELL_LIGHT),
            ("Road",    EARTH_TONE),
            ("Capital", BLOOD_STONE),
            ("Vukh",    OLD_GOLD),
        ]
        for _name, _color in _overlay_legend:
            pygame.draw.rect(surface, _color, (sx, y + 2, 10, 10))
            _lbl = fs.render(_name, True, EARTH_BROWN)
            surface.blit(_lbl, (sx + 14, y))
            y += slh + 1
        y += 4
        pygame.draw.line(surface, DEEP_STONE_BLUE, (sx, y), (sx + sw, y), 1)
        y += 8

        cur_surf = fs.render(
            f"Cursor  ({cursor_wx}, {cursor_wy})", True, SLATE_DARK
        )
        surface.blit(cur_surf, (sx, y))
        y += slh

        pl_surf = fs.render(
            f"Player  ({player_wx}, {player_wy})", True, SLATE_DARK
        )
        surface.blit(pl_surf, (sx, y))
        y += slh + 4

        pygame.draw.line(surface, DEEP_STONE_BLUE, (sx, y), (sx + sw, y), 1)
        y += 8

        from world.world_map import RegionType
        _LEGEND_COLORS = {
            "heath":          FOREST_DEEP,
            "forest":         FOREST_DEEP,
            "plains":         LIFE_GREEN,
            "swamp":          COLDBELL_LIGHT,
            "mountain":       STONE_BLUE,
            "town":           OLD_GOLD,
            "deep_mountain":  SLATE_DARK,
            "capital":        BLOOD_STONE,
            "drowned_wood":   TEAL_DEEP,
            "ash_wastes":     EARTH_BROWN,
            "unknown":        DUNGEON_SHADOW,
        }
        legend_items = [(rt.value, _LEGEND_COLORS.get(rt.value, SLATE_DARK))
                        for rt in RegionType]
        col_w = sw // 2
        for i, (name, color) in enumerate(legend_items):
            col  = i % 2
            row  = i // 2
            lx   = sx + col * col_w
            ly   = y + row * (slh + 2)
            pygame.draw.rect(surface, color, (lx, ly + 2, 10, 10))
            lbl  = fs.render(name, True, EARTH_BROWN)
            surface.blit(lbl, (lx + 14, ly))
        legend_rows = (len(legend_items) + 1) // 2
        y += legend_rows * (slh + 2) + 6

        pygame.draw.line(surface, DEEP_STONE_BLUE, (sx, y), (sx + sw, y), 1)
        y += 8

        footer_y = sidebar_rect.bottom - UI_PANEL_INSET - fs.get_height()
        if DEBUG_MODE:
            dbg_surf = fs.render("[DEBUG] Enter — teleport", True, OLD_GOLD)
            surface.blit(dbg_surf, (sx, footer_y - slh - 2))
        enter_surf = fs.render("Enter — travel here", True, VERDANT_MID)
        surface.blit(enter_surf,
                     (sx, footer_y - slh - 2 - (slh + 2 if DEBUG_MODE else 0)))
        close_surf = fs.render("M / ESC — close", True, MOSS_DARK)
        surface.blit(close_surf, (sx, footer_y))

    def _is_wall_connection(self, local_map: "LocalMap", x: int, y: int, base_terrain: str) -> bool:
        """Checks if a neighbor should connect to the current wall."""
        if not local_map.in_bounds(x, y):
            # Treat out-of-bounds as a connection to prevent 'open' edges at map borders
            return True
        neighbor_terrain = str(local_map.tiles[x, y]["terrain"])
        # Connect if it's the exact same wall type (e.g., 'stone_wall' connects to 'stone_wall')
        return neighbor_terrain == base_terrain

    def _get_autotile_name(self, local_map: "LocalMap", mx: int, my: int, terrain: str) -> str:
        """Generates a bitmasked name like 'wall_10' based on N, E, S, W neighbors."""
        # Standard bitmask: N=1, E=2, S=4, W=8
        mask = 0
        if self._is_wall_connection(local_map, mx, my - 1, terrain): mask |= 1
        if self._is_wall_connection(local_map, mx + 1, my,     terrain): mask |= 2
        if self._is_wall_connection(local_map, mx, my + 1, terrain): mask |= 4
        if self._is_wall_connection(local_map, mx - 1, my,     terrain): mask |= 8
        
        return f"{terrain}_{mask}"

    def _is_road_tile(self, local_map: "LocalMap", x: int, y: int) -> bool:
        """Check if neighbour is a road tile (for road autotile connection)."""
        if not local_map.in_bounds(x, y):
            return True  # out-of-bounds counts as connecting
        t = str(local_map.tiles[x, y]["terrain"])
        return t.startswith("road")

    def _get_road_autotile_name(self, local_map: "LocalMap", mx: int, my: int) -> str:
        """Compute bitmask for road tile and return 'road_N'."""
        mask = 0
        if self._is_road_tile(local_map, mx, my - 1): mask |= 1
        if self._is_road_tile(local_map, mx + 1, my): mask |= 2
        if self._is_road_tile(local_map, mx, my + 1): mask |= 4
        if self._is_road_tile(local_map, mx - 1, my): mask |= 8
        return f"road_{mask}"