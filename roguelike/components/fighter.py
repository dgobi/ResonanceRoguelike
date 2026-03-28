# components/fighter.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Fighter:
    max_hp:       int
    power:        int   # kept for fallback, overridden by weapon damage_dice
    defense:      int   # kept for fallback

    body_id:               str  = "body_human"
    effective_av:          int  = 0   # sum of all equipped + natural armour AV; recomputed on equip
    corruption_damage_bonus: int = 0  # flat bonus per threshold crossed (The Indifference perk)
    body_limbs:            list = field(default_factory=list)
    _dead:                 bool = field(default=False, repr=False)
    hp:                    int  = field(default=0,     repr=True)  # current HP; set in __post_init__

    def __post_init__(self) -> None:
        # Only initialise hp from max_hp when the caller hasn't supplied it explicitly.
        # default=0 is the sentinel; caller may override after construction.
        if self.hp == 0:
            self.hp = self.max_hp

    @property
    def hp_fraction(self) -> float:
        if self.max_hp <= 0:
            return 0.0
        return self.hp / self.max_hp

    @property
    def is_dead(self) -> bool:
        return self._dead

    def take_damage(self, amount: int) -> int:
        """Apply damage to the single HP pool. Returns actual damage taken."""
        actual = min(amount, self.hp)
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self._dead = True
        return actual

    def heal(self, amount: int) -> int:
        """Restore HP up to max_hp. Returns actual amount healed."""
        prev = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - prev

    def can_attack(self) -> bool:
        return not self._dead

    def can_move(self) -> bool:
        return not self._dead
