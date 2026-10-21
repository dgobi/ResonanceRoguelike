# rendering/coords.py
"""
Canonical world-to-screen coordinate conversion.

All world-positioned draw calls must use world_to_screen() or an equivalent
that uses the same formula. No exceptions.

Formula: screen_x = viewport_x + (world_x - cam_x) * tile_w
         screen_y = viewport_y + (world_y - cam_y) * tile_h

cam_x, cam_y:           camera tile offset (tile units, not pixels).
viewport_x, viewport_y: screen pixel position of viewport top-left.
                         Include shake_offset when the call should track shake.
tile_w, tile_h:         tile size in pixels, including zoom factor.
"""
from __future__ import annotations


def world_to_screen(
    world_x: float,
    world_y: float,
    cam_x:   int,
    cam_y:   int,
    viewport_x: int,
    viewport_y: int,
    tile_w:  int,
    tile_h:  int | None = None,
) -> tuple[int, int]:
    """Convert world tile coordinates to absolute screen pixel position.

    Returns integer (screen_x, screen_y).
    Pass viewport_x/y including shake_offset when the call should track shake.
    Pass tile centre by adding 0.5 to world_x / world_y before calling.
    """
    if tile_h is None:
        tile_h = tile_w
    return (
        int(viewport_x + (world_x - cam_x) * tile_w),
        int(viewport_y + (world_y - cam_y) * tile_h),
    )
