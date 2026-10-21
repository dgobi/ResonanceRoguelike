# engine/weather.py
from __future__ import annotations
import random as _random
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    pass


# ------------------------------------------------------------------ #
#  Transition tables
#  Each entry: (next_state, relative_weight)
# ------------------------------------------------------------------ #

_TRANSITIONS: dict[str, list[tuple[str, int]]] = {
    "clear":           [("clear", 50), ("overcast", 30), ("wind", 12), ("light_rain", 8)],
    "overcast":        [("clear", 25), ("overcast", 30), ("light_rain", 25), ("fog", 12), ("heavy_rain", 8)],
    "light_rain":      [("overcast", 40), ("light_rain", 30), ("heavy_rain", 20), ("clear", 10)],
    "heavy_rain":      [("light_rain", 50), ("overcast", 30), ("fog", 12), ("heavy_rain", 8)],
    "fog":             [("overcast", 40), ("fog", 28), ("clear", 20), ("forgetting_fog", 12)],
    "wind":            [("clear", 40), ("overcast", 30), ("wind", 20), ("dead_calm", 10)],
    "dead_calm":       [("overcast", 50), ("clear", 30), ("dead_calm", 20)],
    "resonance_storm": [("overcast", 50), ("heavy_rain", 30), ("resonance_storm", 20)],
    "forgetting_fog":  [("fog", 50), ("overcast", 30), ("forgetting_fog", 20)],
    "bone_snow":       [("overcast", 60), ("bone_snow", 40)],
}

_DURATIONS: dict[str, tuple[int, int]] = {
    "clear":           (80,  200),
    "overcast":        (40,  120),
    "light_rain":      (20,  80),
    "heavy_rain":      (15,  50),
    "fog":             (30,  100),
    "wind":            (20,  60),
    "dead_calm":       (30,  80),
    "resonance_storm": (10,  30),
    "forgetting_fog":  (20,  50),
    "bone_snow":       (15,  40),
}

# (display_label, RGB)  — None means silent (no display)
_DISPLAY: dict[str, tuple[str, tuple[int, int, int]] | None] = {
    "clear":           None,
    "overcast":        ("overcast",          STONE_BLUE),
    "light_rain":      ("light rain",        STEEL_WATER),
    "heavy_rain":      ("heavy rain",        SLATE_MID),
    "fog":             ("fog",               STONE_BLUE),
    "wind":            ("wind",              AGED_WOOD),
    "dead_calm":       ("dead calm",         SLATE_DARK),
    "resonance_storm": ("RESONANCE STORM",   BLOOD_STONE),
    "forgetting_fog":  ("forgetting fog",    DEEP_PURPLE),
    "bone_snow":       ("bone snow",         VOID_PURPLE),
}


class WeatherSystem:
    """
    Lightweight weather state machine.

    tick(rng)             — call once per game turn
    discharge_push(rng, bell_type)  — called by discharge.py on bell fire
    display_string        — label for status bar, or None if clear
    display_color         — RGB tuple for the label
    force_state(state)    — for debug commands
    """

    VALID_STATES = tuple(_TRANSITIONS.keys())

    def __init__(self, rng: _random.Random) -> None:
        self.state:           str   = "clear"
        self.intensity:       float = 0.0
        self.turns_remaining: int   = rng.randint(*_DURATIONS["clear"])
        self._pending_msg:    tuple | None = None   # (text, color)
        self._weather_defs:   dict        = {}      # injected from data loader

    def load_mechanics(self, weather_defs: dict) -> None:
        """Inject weather_defs from DataLoader so get_mechanic() can read tunable values."""
        self._weather_defs = weather_defs

    def get_mechanic(self, key: str, default):
        """Return the mechanic value for the current state, or default if not defined."""
        state_data = self._weather_defs.get(self.state, {})
        return state_data.get("mechanics", {}).get(key, default)

    # ------------------------------------------------------------------ #

    def tick(self, rng: _random.Random) -> tuple | None:
        """
        Advance one turn. Returns (message, color) if a notable transition
        occurred, otherwise None.
        """
        self._pending_msg = None

        if self.turns_remaining > 0:
            self.turns_remaining -= 1
            return None

        # Time to transition
        old_state = self.state
        self._transition(rng)

        # Announce only notable new states
        msg = _TRANSITION_MESSAGES.get(self.state)
        if msg and self.state != old_state:
            col = _DISPLAY.get(self.state)
            color = col[1] if col else AGED_WOOD
            return (msg, color)
        return None

    def discharge_push(self, rng: _random.Random, bell_type: str) -> tuple | None:
        """
        A bell discharged — push weather toward something dramatic.
        Returns (message, color) if the weather changes notably.
        """
        if bell_type == "intact":
            # 25% chance: jump to resonance_storm
            if rng.random() < 0.25:
                old = self.state
                self._force_to("resonance_storm", rng)
                if old != "resonance_storm":
                    return (
                        "The sky breaks open. A resonance storm.",
                        BLOOD_STONE,
                    )
            elif self.state in ("clear", "wind"):
                # Push toward overcast
                self._force_to("overcast", rng)
        else:   # cracked
            # 15% chance: jump to dead_calm
            if rng.random() < 0.15:
                old = self.state
                self._force_to("dead_calm", rng)
                if old != "dead_calm":
                    return (
                        "The air goes still. The bells will carry.",
                        SLATE_DARK,
                    )
        return None

    def force_state(self, state: str) -> None:
        """Debug command — set state immediately."""
        self._force_to(state, _random.Random())

    # ------------------------------------------------------------------ #
    #  Display helpers
    # ------------------------------------------------------------------ #

    @property
    def display_string(self) -> str | None:
        entry = _DISPLAY.get(self.state)
        if entry is None:
            return None
        return entry[0]

    @property
    def display_color(self) -> tuple[int, int, int]:
        entry = _DISPLAY.get(self.state)
        if entry is None:
            return STONE_BLUE
        return entry[1]

    # ------------------------------------------------------------------ #
    #  Save / load
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "state":           self.state,
            "intensity":       self.intensity,
            "turns_remaining": self.turns_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict, rng: _random.Random) -> "WeatherSystem":
        w = cls(rng)
        w.state           = data.get("state",           "clear")
        w.intensity       = data.get("intensity",       0.0)
        w.turns_remaining = data.get("turns_remaining", 40)
        return w

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _transition(self, rng: _random.Random) -> None:
        options = _TRANSITIONS.get(self.state, _TRANSITIONS["clear"])
        states, weights = zip(*options)
        self.state = rng.choices(list(states), weights=list(weights), k=1)[0]
        lo, hi = _DURATIONS[self.state]
        self.turns_remaining = rng.randint(lo, hi)
        self.intensity = rng.uniform(0.3, 1.0)
        if self.state == "forgetting_fog":
            self.intensity = max(0.85, self.intensity)

    def _force_to(self, state: str, rng: _random.Random) -> None:
        self.state = state
        lo, hi = _DURATIONS.get(state, (20, 60))
        self.turns_remaining = rng.randint(lo, hi)
        self.intensity = rng.uniform(0.5, 1.0)
        if state == "forgetting_fog":
            self.intensity = max(0.85, self.intensity)


# ------------------------------------------------------------------ #
#  Transition messages — shown when entering these states
# ------------------------------------------------------------------ #

_TRANSITION_MESSAGES: dict[str, str] = {
    "resonance_storm": "A resonance storm breaks overhead.",
    "forgetting_fog":  "A forgetting fog comes in.",
    "dead_calm":       "The wind stops. The silence is complete.",
    "bone_snow":       "Something falls that is not quite snow.",
    "heavy_rain":      "The rain comes down hard.",
    "fog":             "Fog settles across the land.",
}
