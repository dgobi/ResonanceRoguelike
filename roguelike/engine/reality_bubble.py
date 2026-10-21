# engine/reality_bubble.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.world_map import WorldMap


class RealityBubble:
    """
    Tracks which world chunks are currently active (simulated).

    Step A: always includes the player's current chunk, plus any town-group
    chunks that chunk belongs to.

    Step B: will expand to include chunks within a radius and load their
    entities into memory for co-simulation.
    """

    def __init__(self) -> None:
        self.active_chunks: set[tuple[int, int]] = set()

    def update(self, player_wx: int, player_wy: int, world_map: "WorldMap") -> None:
        self.active_chunks = {(player_wx, player_wy)}
        group = world_map.get_town_group(player_wx, player_wy)
        if group:
            self.active_chunks.update(group)
        # Chebyshev-1: all 8 adjacent chunks also active for cross-chunk entity ticking
        for _dx in (-1, 0, 1):
            for _dy in (-1, 0, 1):
                if _dx == 0 and _dy == 0:
                    continue
                self.active_chunks.add((player_wx + _dx, player_wy + _dy))

    def is_active(self, wx: int, wy: int) -> bool:
        return (wx, wy) in self.active_chunks
