# components/corruption.py
from __future__ import annotations
import random


CORRUPTION_STATES = [
    (0.15, "Unmarked"),
    (0.30, "Touched"),
    (0.50, "Stained"),
    (0.70, "Marked"),
    (0.90, "Consumed"),
    (1.00, "Vessel"),
]

# Whispers that appear in the message log at higher corruption
# Drawn from the Kirkbride/KSBD/Vermis aesthetic
CORRUPTION_WHISPERS = [
    "Something counts your heartbeats.",
    "The walls remember being something else.",
    "You have been measured and found present.",
    "A door that was not there before.",
    "It knows your name in a language older than names.",
    "The shadows here have the wrong number of edges.",
    "You are being described to something.",
    "There is a second set of footsteps. They are yours.",
    "The dark does not merely lack light. It waits.",
    "Something has written your name in a place you cannot see.",
]


def _state_from_value(value: float) -> str:
    for threshold, label in CORRUPTION_STATES:
        if value <= threshold:
            return label
    return CORRUPTION_STATES[-1][1]


class Corruption:
    """
    Tracks corruption as 0.0 (clean) → 1.0 (vessel).
    Corruption is not simply a penalty — it opens doors
    and unlocks abilities unavailable to the clean.
    Reducing it is possible but difficult.
    """

    # Passive accumulation rates per turn in corrupting zones
    PASSIVE_RATE_BARROW       = 0.00005
    PASSIVE_RATE_WARPED_PLACE = 0.0002

    def __init__(self) -> None:
        self.value:              float = 0.0
        self._whisper_cooldown:  int   = 0

    @property
    def state(self) -> str:
        return _state_from_value(self.value)

    @property
    def fov_penalty(self) -> int:
        if self.value < 0.30:  return 0
        if self.value < 0.50:  return 2
        if self.value < 0.70:  return 3
        if self.value < 0.90:  return 4
        return 4   # Vessel gets partial darkvision instead (later)

    @property
    def void_magic_bonus(self) -> float:
        """Multiplier for VOID school magic. Scales with corruption."""
        if self.value < 0.30:  return 1.0
        if self.value < 0.50:  return 1.3
        if self.value < 0.70:  return 1.6
        if self.value < 0.90:  return 2.0
        return 2.5

    @property
    def hallucinating(self) -> bool:
        """True if corruption is high enough for hallucinations."""
        return self.value >= 0.30

    @property
    def is_vessel(self) -> bool:
        return self.value >= 0.90

    def accumulate(self, amount: float) -> None:
        self.value = min(1.0, self.value + amount)

    def cleanse(self, amount: float) -> None:
        """
        Reduce corruption. Difficult — full cleansing
        requires ritual, not just time.
        """
        self.value = max(0.0, self.value - amount)

    def tick(
        self,
        log:       "MessageLog",
        zone_tags: list[str],
        turn:      int,
    ) -> None:
        """
        Called each turn. Applies passive accumulation
        based on current zone, emits whispers when appropriate.
        """
        prev_state = self.state

        # Passive accumulation by zone
        if "warped_place" in zone_tags:
            self.accumulate(self.PASSIVE_RATE_WARPED_PLACE)
        elif "barrow" in zone_tags or "dead" in zone_tags:
            self.accumulate(self.PASSIVE_RATE_BARROW)

        # State transition messages
        curr_state = self.state
        if prev_state != curr_state:
            _emit_state_message(curr_state, log)

        # Whispers at Stained and above
        if self.value >= 0.30 and self._whisper_cooldown <= 0:
            if random.random() < 0.03 * (self.value / 0.3):
                log.add_whisper(random.choice(CORRUPTION_WHISPERS))
                self._whisper_cooldown = random.randint(20, 60)

        if self._whisper_cooldown > 0:
            self._whisper_cooldown -= 1


def _emit_state_message(state: str, log: "MessageLog") -> None:
    from engine.message_log import MSG_CORRUPT, MSG_IMPORTANT
    messages = {
        "Touched":  "Something has noticed you.",
        "Stained":  "The corruption has taken hold. Your sight is dimming at the edges.",
        "Marked":   "You are marked. Some doors will open. Others will close.",
        "Consumed": "The boundary between you and what watches is thinning.",
        "Vessel":   "You are no longer entirely yourself.",
    }
    if state in messages:
        log.add(messages[state], MSG_CORRUPT)