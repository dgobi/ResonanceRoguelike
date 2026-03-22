# rendering/renderer.py
from __future__ import annotations
import pygame
import random
from typing import TYPE_CHECKING
from config import UI_PANEL_INSET
from rendering.decor import get_procedural_key

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
          fg = (255,255,255) → full brightness (lit tile).
          fg = (38,38,38)    → memory darkness (~15%).
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
            tint_color = fg if fg is not None else (255, 255, 255)
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
    ) -> None:
        if viewport_rect is None:
            viewport_rect = display_surface.get_rect()
        if void_rect is None:
            void_rect = viewport_rect
        _ = visual_events  # reserved — Tier 3

        display_surface.fill((4, 6, 14), void_rect)

        zoom   = self.display.zoom_level
        tw, th = self._tile_wh()
        vw     = viewport_rect.width
        vh     = viewport_rect.height

        tiles_x = (vw  + zoom - 1) // (tw * zoom) + 1
        tiles_y = (vh  + zoom - 1) // (th * zoom) + 1
        disp_w  = tiles_x * tw * zoom
        disp_h  = tiles_y * th * zoom

        terrain_surf = pygame.Surface((disp_w, disp_h))
        terrain_surf.fill((7, 12, 29))
        # Pass active light colour for tinting in full-colour mode
        light_color = (255, 255, 255)  # default: white/neutral
        for e in entities:
            if e.name == "Player":
                ls = getattr(e, "light_source", None)
                if ls and ls.active and hasattr(ls, "color"):
                    light_color = ls.color
                break

        self._draw_map_to(terrain_surf, local_map,
                          cam_x, cam_y, tiles_x, tiles_y, zoom,
                          light_color=light_color)

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
                pygame.draw.circle(surface, (28, 55, 72), (dx, dy), 2)

            radius_inner = 4 * tw * zoom
            for i in range(48):
                if i % 2 == 1:
                    continue
                angle = (i / 48) * 2 * math.pi
                dx = int(cx + radius_inner * math.cos(angle))
                dy = int(cy + radius_inner * math.sin(angle))
                pygame.draw.circle(surface, (18, 35, 50), (dx, dy), 1)

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
        light_color: tuple[int,int,int] = (255, 255, 255),
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
                        fg_base = (40, 96, 128)
                        bg_base = (7, 12, 29)

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
                                fg = (12, 12, 15)
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
                            fg = (255, 255, 255)
                            bg = None
                        else:
                            # Memory tile — dark, cool blue cast
                            fg = (30, 32, 38)
                            bg = None

                    # 1. Resolve procedural name (intercepts "grass" or "tree" here)
                    decorated_name = get_procedural_key(mx, my, terrain)

                    # 2. Skip rendering if the result is None (Void)
                    if decorated_name is None:
                        continue

                    # 3. Determine the specific sprite variant (Autotiling)
                    if any(key in decorated_name for key in ["wall", "water"]):
                        variant_name = self._get_autotile_name(local_map, mx, my, decorated_name)
                        sprite_name = variant_name if self.sprite_registry.has(variant_name) else decorated_name
                    else:
                        sprite_name = decorated_name

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
        GHOST_COLOR = (20, 20, 35)
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
        for entity in sorted(entities, key=priority):
            if not local_map.in_bounds(entity.x, entity.y):
                continue
            if not bool(local_map.tiles[entity.x, entity.y]["visible"]):
                continue

            tx = entity.x - cam_x
            ty = entity.y - cam_y

            if self._sprite_mode:
                if use_tint:
                    # 1-bit: apply fg colour tint from tiles.json
                    fg = self.registry.fg(entity.tile) \
                        if entity.tile in self.registry._data \
                        else (255, 255, 255)
                else:
                    # Full-colour: full brightness, no colour tint
                    fg = (255, 255, 255)

                self._draw_sprite(surface, entity.tile,
                                  fg, None, tx, ty, zoom=zoom)
            else:
                char = chr(self.registry.char(entity.tile))
                fg   = self.registry.fg(entity.tile)
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

        display_surface.fill((4, 6, 14), viewport)

        zoom   = self.display.zoom_level
        tw, th = self._tile_wh()
        vw     = viewport.width
        vh     = viewport.height

        tiles_x  = vw  // (tw * zoom) + 2
        tiles_y  = vh  // (th * zoom) + 2
        native_w = tiles_x * tw
        native_h = tiles_y * th

        surf = pygame.Surface((native_w, native_h))
        surf.fill((0, 0, 0))
        pygame.draw.rect(surf, (100, 80, 140), (0, 0, native_w, native_h), 1)

        offset_x = cam_x - tiles_x // 2
        offset_y = cam_y - tiles_y // 2

        for sx in range(tiles_x):
            for sy in range(tiles_y):
                wx = sx + offset_x
                wy = sy + offset_y

                if wx == player_wx and wy == player_wy:
                    key = "overmap_player"
                    fg  = (255, 255, 255)
                    bg  = (40, 30, 60)
                else:
                    if not world_map.in_bounds(wx, wy):
                        continue
                    chunk = world_map.get(wx, wy)
                    if not chunk or not chunk.explored:
                        continue
                    key = chunk.region_type.overmap_tile()
                    fg  = self.registry.fg(key) \
                        if key in self.registry._data \
                        else (120, 110, 140)
                    bg  = self.registry.bg(key) \
                        if key in self.registry._data \
                        else (0, 0, 0)

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
                    surf, (226, 181, 112),
                    (csx * tw + 1, csy * th + 1, tw - 2, th - 2), 1,
                )

        if highlight_passages:
            _SUBMAP_COLOR = (63, 160, 164)
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

        _LOCUS_COLOR = (145, 58, 82)
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

        scaled = pygame.transform.scale(surf, (native_w * zoom, native_h * zoom))
        display_surface.blit(scaled, viewport.topleft)

        label      = self.display.font_ui_small.render(
            "WORLD MAP  \xb7  M or ESC to close", True, (180, 165, 140)
        )
        label_rect = label.get_rect(
            topleft=(viewport.x + UI_PANEL_INSET, viewport.y + UI_PANEL_INSET)
        )
        bg_rect  = label_rect.inflate(8, 4)
        bg_surf  = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill((7, 12, 29, 200))
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
                tint_color=(68, 99, 116),
                fill_color=(7, 12, 29),
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
            name_surf = fb.render(chunk.name, True, (200, 185, 150))
        elif chunk:
            name_surf = fb.render(chunk.region_type.value.title(), True, (200, 185, 150))
        else:
            name_surf = fb.render("Unknown", True, (100, 90, 80))
        surface.blit(name_surf, (sx, y))
        y += name_surf.get_height() + 4

        if chunk:
            explored_tag = " [explored]" if chunk.explored else " [unexplored]"
            rt_surf = fs.render(
                chunk.region_type.value + explored_tag, True, (93, 140, 110)
            )
            surface.blit(rt_surf, (sx, y))
        y += slh + 2

        if chunk and getattr(chunk, "is_locus", False):
            locus_surf = fs.render("[LOCUS]", True, (145, 58, 82))
            surface.blit(locus_surf, (sx, y))
            y += slh + 2

        pygame.draw.line(surface, (40, 60, 80), (sx, y), (sx + sw, y), 1)
        y += 8

        if chunk and chunk.explored:
            region_str = chunk.region_type.value
            icon = get_biome_icon(region_str, seed=chunk.seed % 10000)
            icon_scaled = pygame.transform.scale(icon, (48, 48))
            surface.blit(icon_scaled, (sx, y))

            tx = sx + 56
            biome_surf = fn.render(region_str.title(), True, (180, 165, 130))
            surface.blit(biome_surf, (tx, y + 4))

            zone_str = ""
            if chunk.zones:
                zone_str = chunk.zones[0][0].replace("_", " ")
            if zone_str:
                zone_surf = fs.render(zone_str, True, (80, 100, 90))
                surface.blit(zone_surf, (tx, y + 4 + lh))

            y += 56
        else:
            unknown = fn.render("— not yet explored —", True, (60, 60, 70))
            surface.blit(unknown, (sx, y))
            y += lh + 4

        pygame.draw.line(surface, (40, 60, 80), (sx, y), (sx + sw, y), 1)
        y += 8

        myth = getattr(world_map, "myth", None)
        if myth:
            age_surf = fs.render(myth.age_name, True, (120, 50, 70))
            surface.blit(age_surf, (sx, y))
            y += slh

            shape_surf = fs.render(myth.myth_shape, True, (80, 30, 50))
            surface.blit(shape_surf, (sx, y))
            y += slh

            sunder_surf = fs.render(myth.sundering_epithet, True, (50, 70, 90))
            surface.blit(sunder_surf, (sx, y))
            y += slh + 4

            pygame.draw.line(surface, (40, 60, 80), (sx, y), (sx + sw, y), 1)
            y += 8

        td = getattr(chunk, "town_data", None) if chunk else None
        if td:
            bell_colors = {
                "intact":    (188, 89,  96),
                "cracked":   (226, 181, 112),
                "spent":     (68,  99,  116),
                "missing":   (50,  73,  95),
                "destroyed": (50,  73,  95),
            }
            bell_color = bell_colors.get(td.bell_state, (68, 99, 116))
            bell_surf = fs.render(f"Bell: {td.bell_state}", True, bell_color)
            surface.blit(bell_surf, (sx, y))
            y += slh

            if td.is_festival:
                fest_surf = fs.render(
                    "Festival — was ongoing", True, (145, 58, 82)
                )
                surface.blit(fest_surf, (sx, y))
                y += slh

            districts_str = ", ".join(td.districts)
            dist_surf = fs.render(districts_str, True, (50, 73, 95))
            surface.blit(dist_surf, (sx, y))
            y += slh + 4

            pygame.draw.line(surface, (40, 60, 80), (sx, y), (sx + sw, y), 1)
            y += 8

        if chunk and chunk.explored and chunk.submaps:
            for sub in chunk.submaps:
                ent_surf = fn.render(
                    f"> {sub.submap_type} entrance", True, (226, 181, 112)
                )
                surface.blit(ent_surf, (sx, y))
                y += lh
                if DEBUG_MODE:
                    name_surf = fs.render(
                        f"  {sub.name or sub.submap_type}", True, (145, 58, 82)
                    )
                    surface.blit(name_surf, (sx, y))
                    y += slh
                    id_surf = fs.render(
                        f"  [{sub.submap_id}]", True, (68, 99, 116)
                    )
                    surface.blit(id_surf, (sx, y))
                    y += slh
                    layout_surf = fs.render(
                        f"  layout: {sub.layout_id or 'bsp'}", True, (68, 99, 116)
                    )
                    surface.blit(layout_surf, (sx, y))
                    y += slh
            y += 4
            pygame.draw.line(surface, (40, 60, 80), (sx, y), (sx + sw, y), 1)
            y += 8

        cur_surf = fs.render(
            f"Cursor  ({cursor_wx}, {cursor_wy})", True, (50, 73, 95)
        )
        surface.blit(cur_surf, (sx, y))
        y += slh

        pl_surf = fs.render(
            f"Player  ({player_wx}, {player_wy})", True, (50, 73, 95)
        )
        surface.blit(pl_surf, (sx, y))
        y += slh + 4

        pygame.draw.line(surface, (40, 60, 80), (sx, y), (sx + sw, y), 1)
        y += 8

        from world.world_map import RegionType
        _LEGEND_COLORS = {
            "heath":    (57,  117,  92),
            "forest":   (40,   84,  50),
            "plains":   (93,  167,  93),
            "swamp":    (63,  160, 164),
            "mountain": (68,   99, 116),
            "town":     (226, 181, 112),
        }
        legend_items = [(rt.value, _LEGEND_COLORS.get(rt.value, (100, 100, 100)))
                        for rt in RegionType]
        col_w = sw // 2
        for i, (name, color) in enumerate(legend_items):
            col  = i % 2
            row  = i // 2
            lx   = sx + col * col_w
            ly   = y + row * (slh + 2)
            pygame.draw.rect(surface, color, (lx, ly + 2, 10, 10))
            lbl  = fs.render(name, True, (120, 110, 100))
            surface.blit(lbl, (lx + 14, ly))
        legend_rows = (len(legend_items) + 1) // 2
        y += legend_rows * (slh + 2) + 6

        pygame.draw.line(surface, (40, 60, 80), (sx, y), (sx + sw, y), 1)
        y += 8

        footer_y = sidebar_rect.bottom - UI_PANEL_INSET - fs.get_height()
        if DEBUG_MODE:
            dbg_surf = fs.render("[DEBUG] Enter — teleport", True, (140, 140, 80))
            surface.blit(dbg_surf, (sx, footer_y - slh - 2))
        enter_surf = fs.render("Enter — travel here", True, (140, 160, 130))
        surface.blit(enter_surf,
                     (sx, footer_y - slh - 2 - (slh + 2 if DEBUG_MODE else 0)))
        close_surf = fs.render("M / ESC — close", True, (80, 90, 80))
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