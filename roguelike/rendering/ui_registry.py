# rendering/ui_registry.py
from __future__ import annotations
from pathlib import Path
import pygame
import numpy as np


BORDER_PX = 15   # border region width in the 96×96 source


class UIRegistry:
    """
    Loads 96×96 panel PNGs from assets/ui/ and draws them via 9-slice
    rendering with a flat tint mask.

    Source format (confirmed via pixel analysis):
      - 96×96, all pixels alpha=255
      - Center pixels: pure black (0,0,0)
      - Border pixels: brightness (r+g+b) > 15, outer ~15px
      - 883 bright (>200) pixels = flourishes, 306 medium (15-200) = fill

    _make_tinted_source converts to RGBA: border → tint color opaque,
    interior → fully transparent. 9-slice then assembles the frame.

    numpy surfarray note: array3d shape is (width, height, 3) — column-major,
    so border_mask is (w, h) and out_arr is (w, h, 4).
    """

    def __init__(self) -> None:
        self._panels: dict[str, pygame.Surface] = {}
        self._cache:  dict[tuple, pygame.Surface] = {}

    @property
    def _loaded(self) -> bool:
        return bool(self._panels)

    # ------------------------------------------------------------------ #
    #  Load
    # ------------------------------------------------------------------ #

    def load(self, path: str = "assets/ui") -> None:
        """Load all PNG files from path keyed by filename stem."""
        ui_path = Path(path)
        if not ui_path.exists():
            return
        for png in sorted(ui_path.glob("*.png")):
            panel_id = png.stem
            try:
                surf = pygame.image.load(str(png)).convert_alpha()
                self._panels[panel_id] = surf
            except pygame.error:
                print(f"UIRegistry: failed to load {png}")

    def has(self, panel_id: str) -> bool:
        return panel_id in self._panels

    # ------------------------------------------------------------------ #
    #  Tinted source
    # ------------------------------------------------------------------ #

    def _make_tinted_source(
        self,
        panel_id:   str,
        tint_color: tuple[int, int, int],
    ) -> pygame.Surface:
        """
        Convert a panel PNG to a tinted RGBA surface.
        Border pixels (brightness > 15) → tint color, fully opaque.
        Interior pixels → fully transparent.
        Result is cached by (panel_id, tint_color).
        """
        cache_key = ("tinted_src", panel_id, tint_color)
        if cache_key in self._cache:
            return self._cache[cache_key]

        src      = self._panels[panel_id]
        w, h     = src.get_size()
        arr      = pygame.surfarray.array3d(src)   # (w, h, 3)

        brightness = (arr[:, :, 0].astype(np.int32)
                      + arr[:, :, 1].astype(np.int32)
                      + arr[:, :, 2].astype(np.int32))   # (w, h), range 0–765
        border_mask = brightness > 15                     # (w, h)

        tr, tg, tb = tint_color
        out_arr          = np.zeros((w, h, 4), dtype=np.uint8)
        out_arr[:, :, 0] = np.where(border_mask, tr,  0)
        out_arr[:, :, 1] = np.where(border_mask, tg,  0)
        out_arr[:, :, 2] = np.where(border_mask, tb,  0)
        out_arr[:, :, 3] = np.where(border_mask, 255, 0)

        result = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.surfarray.blit_array(result, out_arr[:, :, :3])
        alpha_surf          = pygame.surfarray.pixels_alpha(result)
        alpha_surf[:, :]    = out_arr[:, :, 3]
        del alpha_surf   # release lock

        self._cache[cache_key] = result
        return result

    # ------------------------------------------------------------------ #
    #  Draw
    # ------------------------------------------------------------------ #

    def draw_panel(
        self,
        surface:      pygame.Surface,
        rect:         pygame.Rect,
        panel_id:     str,
        tint_color:   tuple[int, int, int],
        fill_color:   tuple[int, int, int] = (7, 12, 29),
        fill_alpha:   int  = 245,
        border_scale: int  = 2,
    ) -> None:
        """
        Draw a 9-sliced panel frame onto surface at rect.

        fill_alpha=0  → transparent fill (viewport overlay: border only).
        border_scale  → corner/edge thickness = BORDER_PX * border_scale px.
        """
        if not self._loaded or panel_id not in self._panels:
            pygame.draw.rect(surface, tint_color, rect, 3)
            return

        cache_key = ("panel", panel_id, tint_color, fill_color, fill_alpha,
                     border_scale, rect.width, rect.height)

        if cache_key not in self._cache:
            src_tinted       = self._make_tinted_source(panel_id, tint_color)
            src_w, src_h     = src_tinted.get_size()   # 96, 96
            cs               = BORDER_PX * border_scale  # corner size in output px
            bp               = BORDER_PX

            def crop(x0: int, y0: int, x1: int, y1: int) -> pygame.Surface:
                s = pygame.Surface((x1 - x0, y1 - y0), pygame.SRCALPHA)
                s.blit(src_tinted, (0, 0), pygame.Rect(x0, y0, x1 - x0, y1 - y0))
                return s

            tl     = crop(0,          0,          bp,       bp)
            tr     = crop(src_w - bp, 0,          src_w,    bp)
            bl     = crop(0,          src_h - bp, bp,       src_h)
            br     = crop(src_w - bp, src_h - bp, src_w,    src_h)
            top    = crop(bp,         0,          src_w - bp, bp)
            bottom = crop(bp,         src_h - bp, src_w - bp, src_h)
            left   = crop(0,          bp,         bp,       src_h - bp)
            right  = crop(src_w - bp, bp,         src_w,    src_h - bp)

            edge_w = max(1, rect.width  - cs * 2)
            edge_h = max(1, rect.height - cs * 2)

            def scale(s: pygame.Surface, w: int, h: int) -> pygame.Surface:
                return pygame.transform.scale(s, (max(1, w), max(1, h)))

            def tile_surface(
                strip: pygame.Surface, target_w: int, target_h: int,
            ) -> pygame.Surface:
                """Tile strip to fill target_w × target_h by repeating it."""
                out    = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
                sw, sh = strip.get_size()
                if sw <= 0 or sh <= 0:
                    return out
                x = 0
                while x < target_w:
                    y = 0
                    while y < target_h:
                        out.blit(strip, (x, y))
                        y += sh
                    x += sw
                return out

            tl_s = scale(tl, cs, cs)
            tr_s = scale(tr, cs, cs)
            bl_s = scale(bl, cs, cs)
            br_s = scale(br, cs, cs)

            # Scale strip to correct thickness, preserve pattern, then tile
            top_unit    = scale(top,    top.get_width()    * border_scale, cs)
            bottom_unit = scale(bottom, bottom.get_width() * border_scale, cs)
            left_unit   = scale(left,   cs, left.get_height()  * border_scale)
            right_unit  = scale(right,  cs, right.get_height() * border_scale)

            top_s    = tile_surface(top_unit,    edge_w, cs)
            bottom_s = tile_surface(bottom_unit, edge_w, cs)
            left_s   = tile_surface(left_unit,   cs,     edge_h)
            right_s  = tile_surface(right_unit,  cs,     edge_h)

            final = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

            if fill_alpha > 0:
                final.fill((*fill_color, fill_alpha))

            final.blit(tl_s,     (0,                0))
            final.blit(tr_s,     (rect.width - cs,   0))
            final.blit(bl_s,     (0,                rect.height - cs))
            final.blit(br_s,     (rect.width - cs,  rect.height - cs))
            final.blit(top_s,    (cs,               0))
            final.blit(bottom_s, (cs,               rect.height - cs))
            final.blit(left_s,   (0,                cs))
            final.blit(right_s,  (rect.width - cs,  cs))

            self._cache[cache_key] = final

        surface.blit(self._cache[cache_key], rect.topleft)
