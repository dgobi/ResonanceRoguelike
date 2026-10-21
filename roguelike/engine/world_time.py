# engine/world_time.py
from __future__ import annotations
import math


MOON_PHASES = [
    ("The Dark Seal",      0.00),
    ("The Thin Knife",     0.04),
    ("The Half Truth",     0.09),
    ("The Swelling Eye",   0.14),
    ("The Full Witness",   0.25),
    ("The Dimming Eye",    0.14),
    ("The Half Lie",       0.09),
    ("The Waning Knife",   0.04),
]

TURNS_PER_HOUR  = 60
TURNS_PER_DAY   = TURNS_PER_HOUR * 24
TURNS_PER_PHASE = TURNS_PER_DAY * 3    # each phase lasts 3 days
TURNS_PER_CYCLE = TURNS_PER_PHASE * len(MOON_PHASES)


class WorldTime:
    """
    Tracks in-game time. Advances one tick per player turn.

    Drives:
      - Day/night cycle (sun angle → ambient light outdoors)
      - Moon phase (affects outdoor night light + alchemy + magic)
      - Eventually: seasons, tidal events, ritual windows
    """

    def __init__(self, start_turn: int = 0) -> None:
        # Start at 8am — enough light to see, not mid-day flat
        self.turn = start_turn + (TURNS_PER_HOUR * 8)

    # ------------------------------------------------------------------ #
    #  Time of day
    # ------------------------------------------------------------------ #

    @property
    def hour(self) -> float:
        """Current hour as float 0.0-24.0."""
        return (self.turn % TURNS_PER_DAY) / TURNS_PER_HOUR

    @property
    def hour_int(self) -> int:
        return int(self.hour)

    @property
    def is_day(self) -> bool:
        return 6.0 <= self.hour < 20.0

    @property
    def is_night(self) -> bool:
        return not self.is_day

    @property
    def time_string(self) -> str:
        h   = int(self.hour)
        m   = int((self.hour - h) * 60)
        return f"{h:02d}:{m:02d}"

    # ------------------------------------------------------------------ #
    #  Sun contribution
    # ------------------------------------------------------------------ #

    @property
    def sun_intensity(self) -> float:
        """
        0.0 at midnight, 1.0 at noon.
        Smooth sine curve with dawn at hour 6, dusk at hour 20.
        """
        h = self.hour
        if h < 6.0 or h >= 20.0:
            return 0.0
        # Map 6-20 to 0-π for a smooth arc
        t = (h - 6.0) / 14.0
        return math.sin(t * math.pi)

    @property
    def sun_color(self) -> tuple[float, float, float]:
        """
        Sun color shifts from warm orange at dawn/dusk
        to cool white at noon.
        """
        i = self.sun_intensity
        h = self.hour
        # Dawn/dusk warmth
        if h < 8.0 or h > 18.0:
            return (1.0, 0.75 * i, 0.5 * i)
        # Midday coolness
        return (1.0 * i, 0.95 * i, 0.85 * i)

    # ------------------------------------------------------------------ #
    #  Moon phase
    # ------------------------------------------------------------------ #

    @property
    def moon_phase_index(self) -> int:
        return (self.turn // TURNS_PER_PHASE) % len(MOON_PHASES)

    @property
    def moon_phase(self) -> tuple[str, float]:
        """Returns (phase_name, light_intensity)."""
        return MOON_PHASES[self.moon_phase_index]

    @property
    def moon_phase_name(self) -> str:
        return self.moon_phase[0]

    @property
    def moon_intensity(self) -> float:
        """Moon only contributes at night."""
        if self.is_day:
            return 0.0
        return self.moon_phase[1]

    @property
    def moon_color(self) -> tuple[float, float, float]:
        """Cold silver-blue moonlight."""
        i = self.moon_intensity
        return (0.7 * i, 0.75 * i, 1.0 * i)

    # ------------------------------------------------------------------ #
    #  Ambient light for a chunk
    # ------------------------------------------------------------------ #

    def get_ambient_light(
        self,
        zone_ambient: float,
        is_outdoor:   bool,
    ) -> tuple[float, tuple[float, float, float]]:
        """
        Return (intensity, color) for a tile given its zone's
        base ambient light level and whether it's outdoors.

        Indoor tiles use zone ambient only.
        Outdoor tiles add sun + moon on top.
        """
        if not is_outdoor:
            return zone_ambient, (1.0, 1.0, 1.0)

        # Outdoor: sun + moon + zone base combined
        sun  = self.sun_intensity
        moon = self.moon_intensity

        # Sun dominates during the day, moon at night
        if sun > 0.0:
            intensity = zone_ambient * (0.2 + 0.8 * sun)
            color     = self.sun_color
        elif moon > 0.0:
            intensity = zone_ambient * (0.05 + 0.95 * moon)
            color     = self.moon_color
        else:
            # True darkness — only zone base remains
            # (could be 0.0 for a fully dark night)
            intensity = zone_ambient * 0.02
            color     = (0.1, 0.1, 0.15)   # faint cold nothing

        return intensity, color

    # ------------------------------------------------------------------ #
    #  Advance
    # ------------------------------------------------------------------ #

    def advance(self, turns: int = 1) -> None:
        self.turn += turns

    # ------------------------------------------------------------------ #
    #  Display strings
    # ------------------------------------------------------------------ #

    @property
    def day_number(self) -> int:
        return self.turn // TURNS_PER_DAY + 1

    @property
    def status_string(self) -> str:
        """Short string for UI panel."""
        return f"Day {self.day_number}  {self.time_string}"

    @property
    def moon_string(self) -> str:
        return self.moon_phase_name