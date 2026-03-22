# components/fighter.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.data_loader import DataLoader


@dataclass
class Fighter:
    max_hp:   int
    power:    int   # kept for fallback, overridden by weapon damage_dice
    defense:  int   # kept for fallback, overridden by armor layers

    body_id:      str        = "body_human"
    location_hp:  dict       = field(default_factory=dict)  # location_id → current_hp
    location_max: dict       = field(default_factory=dict)  # location_id → max_hp
    impairments:  set        = field(default_factory=set)
    # armor_layers populated from body def at spawn, equipment adds on top
    # format: {location_id: [{"name":..., "coverage":..., "armor_value":..., "material":...}]}
    armor_layers: dict       = field(default_factory=dict)

    # Legacy HP for backward compat (used by UI bar and old code)
    _dead: bool = field(default=False, repr=False)

    def initialize_from_body(self, body_def: dict) -> None:
        """
        Set up location HP pools and natural armor from body definition.
        Call at spawn time after max_hp is set.
        """
        self.location_hp  = {}
        self.location_max = {}
        self.armor_layers = {}

        for loc in body_def.get("locations", []):
            loc_id = loc["id"]
            hp_mult = loc.get("hp_mult", 0.1)
            loc_max = max(1, int(self.max_hp * hp_mult))
            self.location_hp[loc_id]  = loc_max
            self.location_max[loc_id] = loc_max
            self.armor_layers[loc_id] = list(loc.get("natural_armor", []))

    @property
    def hp(self) -> int:
        """Sum of all location HP — used by UI bar."""
        if self.location_hp:
            return sum(self.location_hp.values())
        return self.max_hp

    @property
    def hp_fraction(self) -> float:
        if self.max_hp <= 0:
            return 0.0
        return self.hp / self.max_hp

    @property
    def is_dead(self) -> bool:
        return self._dead

    def take_damage(self, amount: int) -> int:
        """
        Legacy take_damage — distributes to torso or first vital location.
        Used as fallback when full combat system not available.
        """
        if self.location_hp:
            target = "torso" if "torso" in self.location_hp else \
                     next(iter(self.location_hp))
            actual = min(amount, self.location_hp[target])
            self.location_hp[target] -= actual
            if self.location_hp[target] <= 0:
                self._dead = True
            return actual
        return 0

    def take_location_damage(
        self,
        location_id: str,
        damage: int,
        body_def: dict,
    ) -> list[str]:
        """
        Apply damage to a specific location.
        Returns list of impairment ids triggered this hit.
        """
        if location_id not in self.location_hp:
            return []

        triggered = []
        prev_hp = self.location_hp[location_id]
        max_hp  = self.location_max[location_id]

        self.location_hp[location_id] = max(0, prev_hp - damage)
        curr_hp = self.location_hp[location_id]

        # Find this location's definition
        loc_def = next(
            (l for l in body_def.get("locations", []) if l["id"] == location_id),
            {}
        )

        # Check damage threshold
        threshold = loc_def.get("damage_threshold")
        if threshold is not None:
            threshold_imp = loc_def.get("threshold_impairment")
            if threshold_imp and threshold_imp not in self.impairments:
                if max_hp > 0 and curr_hp / max_hp <= threshold:
                    self.impairments.add(threshold_imp)
                    triggered.append(threshold_imp)

        # Check destroyed
        if curr_hp <= 0:
            destroyed_imp = loc_def.get("destroyed_impairment")
            if destroyed_imp:
                self.impairments.add(destroyed_imp)
                triggered.append(destroyed_imp)
            if destroyed_imp == "death" or loc_def.get("vital", False):
                self._dead = True

        return triggered

    def heal(self, amount: int) -> int:
        """Heal torso HP. Simple restoration."""
        if "torso" in self.location_hp:
            prev = self.location_hp["torso"]
            self.location_hp["torso"] = min(
                self.location_max["torso"],
                prev + amount
            )
            return self.location_hp["torso"] - prev
        return 0

    def has_impairment(self, imp: str) -> bool:
        return imp in self.impairments

    def can_attack(self) -> bool:
        return (
            "dominant_hand_lost" not in self.impairments and
            not self._dead
        )

    def can_move(self) -> bool:
        return (
            not ("leg_lost" in self.impairments and
                 sum(1 for i in self.impairments if "leg_lost" in i) >= 2) and
            not self._dead
        )
