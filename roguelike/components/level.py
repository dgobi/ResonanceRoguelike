# components/level.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class LevelComponent:
    """
    Tracks player level, experience, and perk points.
    """
    level:              int = 1
    exp:                int = 0
    exp_to_next:        int = 100
    perk_points:        int = 1
    total_levels_gained: int = 0

    def exp_threshold(self, level: int) -> int:
        """EXP required to reach `level` from 0."""
        return int(100 * (level ** 1.4))

    def add_exp(self, amount: int) -> bool:
        """
        Add experience. Returns True if the player levelled up.
        Does NOT handle the level-up state changes — caller does that.
        """
        self.exp += amount
        return self.exp >= self.exp_to_next
