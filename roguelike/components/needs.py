# components/needs.py
from __future__ import annotations


# Fallback thresholds (float 0–1, ascending = worse) — used when not configured
HUNGER_THRESHOLDS = [
    (0.15, "Sated"),
    (0.35, "Hungry"),
    (0.60, "Famished"),
    (0.85, "Starving"),
    (1.00, "Wasting"),
]

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
    Modifies FOV, stats, and triggers effects at high values.
    """

    # Fallback rates per turn (used before configure() is called)
    HUNGER_RATE = 0.001
    THIRST_RATE = 0.00125

    def __init__(self) -> None:
        self.hunger: float = 0.0
        self.thirst: float = 0.0

        # Runtime config from survival.json — set by configure()
        self._configured:        bool  = False
        self._h_max:             float = 1000.0
        self._t_max:             float = 800.0
        self._h_tick:            float = self.HUNGER_RATE
        self._t_tick:            float = self.THIRST_RATE
        self._hp_drain_interval: int   = 10
        self._h_stages:          list  = []
        self._t_stages:          list  = []

    def configure(self, survival_cfg: dict) -> None:
        """
        Initialise from survival.json data.
        Normalises integer thresholds to the 0.0–1.0 float model:
          float_threshold = 1.0 - (json_threshold / max)
        e.g. json threshold 700 with max 1000 → float 0.30
        (the stage activates when hunger >= 0.30)
        """
        h = survival_cfg.get("hunger", {})
        t = survival_cfg.get("thirst", {})
        self._h_max = float(h.get("max", 1000))
        self._t_max = float(t.get("max", 800))
        self._h_tick = h.get("tick_rate", 1) / self._h_max
        self._t_tick = t.get("tick_rate", 1) / self._t_max
        self._hp_drain_interval = survival_cfg.get("hp_drain_interval", 10)

        self._h_stages = sorted(
            [
                {
                    "id":           s["id"],
                    "message":      s["message"],
                    "move_penalty": s.get("move_penalty", 0.0),
                    "hp_drain":     s.get("hp_drain", 0.0),
                    "float_thresh": 1.0 - s["threshold"] / self._h_max,
                }
                for s in h.get("stages", [])
            ],
            key=lambda x: x["float_thresh"],
        )
        self._t_stages = sorted(
            [
                {
                    "id":           s["id"],
                    "message":      s["message"],
                    "move_penalty": s.get("move_penalty", 0.0),
                    "hp_drain":     s.get("hp_drain", 0.0),
                    "float_thresh": 1.0 - s["threshold"] / self._t_max,
                }
                for s in t.get("stages", [])
            ],
            key=lambda x: x["float_thresh"],
        )
        self._configured = True

    # ------------------------------------------------------------------ #

    def _active_stage(self, value: float, stages: list) -> dict | None:
        """Return the most severe currently-active stage for the given value."""
        active = None
        for stage in stages:
            if value >= stage["float_thresh"]:
                active = stage
        return active

    @property
    def hunger_state(self) -> str:
        if self._configured and self._h_stages:
            stage = self._active_stage(self.hunger, self._h_stages)
            return stage["id"].capitalize() if stage else "Sated"
        return _state_from_value(self.hunger, HUNGER_THRESHOLDS)

    @property
    def thirst_state(self) -> str:
        if self._configured and self._t_stages:
            stage = self._active_stage(self.thirst, self._t_stages)
            return stage["id"].capitalize() if stage else "Slaked"
        return _state_from_value(self.thirst, THIRST_THRESHOLDS)

    @property
    def hunger_move_penalty(self) -> float:
        if not self._configured:
            return 0.0
        stage = self._active_stage(self.hunger, self._h_stages)
        return stage["move_penalty"] if stage else 0.0

    @property
    def thirst_move_penalty(self) -> float:
        if not self._configured:
            return 0.0
        stage = self._active_stage(self.thirst, self._t_stages)
        return stage["move_penalty"] if stage else 0.0

    @property
    def hunger_hp_drain(self) -> float:
        if not self._configured:
            return 0.0
        stage = self._active_stage(self.hunger, self._h_stages)
        return stage["hp_drain"] if stage else 0.0

    @property
    def thirst_hp_drain(self) -> float:
        if not self._configured:
            return 0.0
        stage = self._active_stage(self.thirst, self._t_stages)
        return stage["hp_drain"] if stage else 0.0

    @property
    def fov_penalty(self) -> int:
        """FOV radius reduction from hunger and thirst. Penalties stack."""
        penalty = 0
        if self.hunger >= 0.60: penalty += 1
        if self.hunger >= 0.85: penalty += 2
        if self.thirst >= 0.60: penalty += 1
        if self.thirst >= 0.85: penalty += 2
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
        h = hunger_rate if hunger_rate is not None else (
            self._h_tick if self._configured else self.HUNGER_RATE
        )
        t = thirst_rate if thirst_rate is not None else (
            self._t_tick if self._configured else self.THIRST_RATE
        )
        self.hunger = min(1.0, self.hunger + h)
        self.thirst = min(1.0, self.thirst + t)

    def eat(self, fraction: float) -> None:
        """Restore hunger. fraction is 0.0–1.0 of the full range."""
        self.hunger = max(0.0, self.hunger - fraction)

    def drink(self, fraction: float) -> None:
        """Restore thirst. fraction is 0.0–1.0 of the full range."""
        self.thirst = max(0.0, self.thirst - fraction)

    def drain_messages(
        self,
        log: "MessageLog",
        prev_hunger: float,
        prev_thirst: float,
    ) -> None:
        """
        Emit messages when needs cross stage boundaries (worsening only).
        Call after advance() with the pre-advance values.
        """
        from engine.message_log import MSG_DANGER, MSG_DEFAULT

        if self._configured:
            _DANGER_STAGES = {"starving", "collapsing", "parched", "desiccating"}

            def _check(prev: float, current: float, stages: list) -> None:
                prev_stage = self._active_stage(prev, stages)
                curr_stage = self._active_stage(current, stages)
                prev_thresh = prev_stage["float_thresh"] if prev_stage else -1.0
                curr_thresh = curr_stage["float_thresh"] if curr_stage else -1.0
                # Only fire on worsening transitions
                if curr_stage is not None and curr_thresh > prev_thresh:
                    color = (MSG_DANGER if curr_stage["id"] in _DANGER_STAGES
                             else MSG_DEFAULT)
                    log.add(curr_stage["message"], color)

            _check(prev_hunger, self.hunger, self._h_stages)
            _check(prev_thirst, self.thirst, self._t_stages)

        else:
            # Fallback: original hardcoded messages
            from engine.message_log import MSG_WORLD

            prev_hs = _state_from_value(prev_hunger, HUNGER_THRESHOLDS)
            curr_hs = self.hunger_state
            if prev_hs != curr_hs:
                _h_messages = {
                    "Hungry":   ("Your stomach contracts. You need food.",      MSG_WORLD),
                    "Famished": ("Hunger gnaws at the edges of your sight.",    MSG_WORLD),
                    "Starving": ("You are starving. Your hands shake.",         MSG_DANGER),
                    "Wasting":  ("Your body is consuming itself.",              MSG_DANGER),
                }
                if curr_hs in _h_messages:
                    text, color = _h_messages[curr_hs]
                    log.add(text, color)

            prev_ts = _state_from_value(prev_thirst, THIRST_THRESHOLDS)
            curr_ts = self.thirst_state
            if prev_ts != curr_ts:
                _t_messages = {
                    "Thirsty":     ("Your throat is dry.",                     MSG_WORLD),
                    "Parched":     ("Thirst makes the shadows swim.",           MSG_WORLD),
                    "Desiccating": ("You are dying of thirst.",                 MSG_DANGER),
                    "Drained":     ("Your lips crack. Your vision narrows.",    MSG_DANGER),
                }
                if curr_ts in _t_messages:
                    text, color = _t_messages[curr_ts]
                    log.add(text, color)
