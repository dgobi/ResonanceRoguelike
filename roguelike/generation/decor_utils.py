# generation/decor_utils.py
"""
Placement API for the decorative tile layer.

All writes to local_map.decor must go through these two functions.
Generation code and layout stamping both use these — never write to
local_map.decor directly outside this module.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.local_map import LocalMap


def place_decor(local_map: "LocalMap", lx: int, ly: int, decor_id: str) -> None:
    """Write a decorative tile at (lx, ly). No-op if out of bounds."""
    if local_map.in_bounds(lx, ly):
        local_map.decor[(lx, ly)] = decor_id


def clear_decor(local_map: "LocalMap", lx: int, ly: int) -> None:
    """Remove any decorative tile at (lx, ly). No-op if nothing there."""
    local_map.decor.pop((lx, ly), None)
