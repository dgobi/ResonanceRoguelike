# components/needs.py
from __future__ import annotations


# Hunger thresholds
HUNGER_THRESHOLDS = [
    (0.15, "Sated"),
    (0.35, "Hungry"),
    (0.60, "Famished"),
    (0.85, "Starving"),
    (1.00, "Wasting"),
]

# Thirst thresholds
THIRST_THRESHOLDS = [
    (0.15, "Slaked"),
    (0.35, "Thirsty"),
    (0.60, "Parched"),
    (0.85, "Desiccating"),
    (1.00, "Drained"),
]


def _state_from_value(value: float, thresholds: list) -> str:
    for threshold, label in thresholds:
        if value <= threshold:
            return label
    return thresholds[-1][1]


class Needs:
    """
    Tracks hunger and thirst as 0.0 (full) → 1.0 (critical).
    Advances each turn at configurable rates.
    Modifies FOV, stats, and triggers hallucinations at high values.
    """

    # Base rates per turn — tuned so starvation takes ~500 turns
    # thirst progresses ~2x faster than hunger
    HUNGER_RATE = 0.0008
    THIRST_RATE = 0.0016

    def __init__(self) -> None:
        self.hunger: float = 0.0
        self.thirst: float = 0.0

    @property
    def hunger_state(self) -> str:
        return _state_from_value(self.hunger, HUNGER_THRESHOLDS)

    @property
    def thirst_state(self) -> str:
        return _state_from_value(self.thirst, THIRST_THRESHOLDS)

    @property
    def fov_penalty(self) -> int:
        """
        FOV radius reduction from hunger and thirst.
        Penalties stack — both starving and desiccating is very bad.
        """
        penalty = 0
        if self.hunger >= 0.60:   penalty += 1
        if self.hunger >= 0.85:   penalty += 2
        if self.thirst >= 0.60:   penalty += 1
        if self.thirst >= 0.85:   penalty += 2
        return penalty

    @property
    def is_critical(self) -> bool:
        return self.hunger >= 0.85 or self.thirst >= 0.85

    def advance(
        self,
        hunger_rate: float | None = None,
        thirst_rate: float | None = None,
    ) -> None:
        """Advance needs by one turn."""
        self.hunger = min(1.0,
            self.hunger + (hunger_rate or self.HUNGER_RATE))
        self.thirst = min(1.0,
            self.thirst + (thirst_rate or self.THIRST_RATE))

    def eat(self, nutrition: float) -> None:
        """Consume food. nutrition 0.0-1.0."""
        self.hunger = max(0.0, self.hunger - nutrition)

    def drink(self, hydration: float) -> None:
        """Consume water. hydration 0.0-1.0."""
        self.thirst = max(0.0, self.thirst - hydration)

    def drain_messages(
        self,
        log: "MessageLog",
        prev_hunger: float,
        prev_thirst: float,
    ) -> None:
        """
        Emit messages when needs cross state boundaries.
        Call after advance() with the pre-advance values.
        """
        from engine.message_log import MSG_DANGER, MSG_WORLD

        prev_hs = _state_from_value(prev_hunger, HUNGER_THRESHOLDS)
        curr_hs = self.hunger_state
        if prev_hs != curr_hs:
            messages = {
                "Hungry":   ("Your stomach contracts. You need food.",
                             MSG_WORLD),
                "Famished": ("Hunger gnaws at the edges of your sight.",
                             MSG_WORLD),
                "Starving": ("You are starving. Your hands shake.",
                             MSG_DANGER),
                "Wasting":  ("Your body is consuming itself.",
                             MSG_DANGER),
            }
            if curr_hs in messages:
                text, color = messages[curr_hs]
                log.add(text, color)

        prev_ts = _state_from_value(prev_thirst, THIRST_THRESHOLDS)
        curr_ts = self.thirst_state
        if prev_ts != curr_ts:
            messages = {
                "Thirsty":     ("Your throat is dry.",
                                MSG_WORLD),
                "Parched":     ("Thirst makes the shadows swim.",
                                MSG_WORLD),
                "Desiccating": ("You are dying of thirst.",
                                MSG_DANGER),
                "Drained":     ("Your lips crack. Your vision narrows.",
                                MSG_DANGER),
            }
            if curr_ts in messages:
                text, color = messages[curr_ts]
                log.add(text, color)