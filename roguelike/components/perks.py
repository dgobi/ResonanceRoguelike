# components/perks.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Perks:
    """
    Tracks which perks the player has acquired and their state.

    acquired: set of perk IDs the player currently has.
    perk_state: maps perk_id → arbitrary state dict for perks
                that need to track usage, cooldowns, or charges.
    affinity_scores: maps affinity name → float 0.0-1.0 tracking
                     how deeply the player has moved into each affinity.
                     Drives unlock conditions for deeper perks.
    """
    acquired:        set[str]         = field(default_factory=set)
    perk_state:      dict[str, dict]  = field(default_factory=dict)
    affinity_scores: dict[str, float] = field(default_factory=dict)

    # Canonical affinity names
    AFFINITIES = [
        "the_hollow_road",
        "the_witnessing",
        "the_green_patience",
        "the_bound_name",
        "the_unmarked_way",
        "the_consuming",
        "the_sutured_work",
        "the_red_accounting",
    ]

    def has(self, perk_id: str) -> bool:
        return perk_id in self.acquired

    def acquire(self, perk_id: str, affinity: str | None = None) -> bool:
        """Acquire a perk. Returns True if newly acquired. Optionally increments affinity score."""
        if perk_id in self.acquired:
            return False
        self.acquired.add(perk_id)
        if affinity:
            current = self.affinity_scores.get(affinity, 0.0)
            self.affinity_scores[affinity] = min(1.0, current + 0.2)
        return True

    def get_state(self, perk_id: str) -> dict:
        """Return mutable state dict for a perk. Creates if absent."""
        if perk_id not in self.perk_state:
            self.perk_state[perk_id] = {}
        return self.perk_state[perk_id]

    def affinity_score(self, affinity: str) -> float:
        return self.affinity_scores.get(affinity, 0.0)

    # ── Hook system aliases ──────────────────────────────────────────
    # Used by the hook registry and debug console.

    @property
    def active_perks(self) -> list[str]:
        """Ordered list of acquired perk ids (for hook registration)."""
        return list(self.acquired)

    def has_perk(self, perk_id: str) -> bool:
        return perk_id in self.acquired

    def add_perk(self, perk_id: str) -> None:
        self.acquired.add(perk_id)

    def remove_perk(self, perk_id: str) -> None:
        self.acquired.discard(perk_id)
