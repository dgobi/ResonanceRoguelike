# components/perception.py
from __future__ import annotations


class Perception:
    """
    Sensory capabilities of an actor.
    Drives AI state transitions.
    """

    def __init__(
        self,
        sight_radius:    int   = 8,
        hearing_radius:  int   = 6,
        sees_in_dark:    bool  = False,
        faction:         str   = "hostile",
        hostile_to:      list[str] | None = None,
    ) -> None:
        self.sight_radius   = sight_radius
        self.hearing_radius = hearing_radius
        self.sees_in_dark   = sees_in_dark
        self.faction        = faction
        self.hostile_to     = hostile_to or ["player"]

    def is_hostile_to(self, other_faction: str) -> bool:
        return other_faction in self.hostile_to

    def can_see(
        self,
        viewer_x: int,
        viewer_y: int,
        target_x: int,
        target_y: int,
        target_visible_to_player: bool,
        ambient_light: float,
    ) -> bool:
        """
        Returns True if this perceiver can see the target.
        Uses Euclidean distance + light level awareness.
        """
        import math
        dist = math.sqrt(
            (viewer_x - target_x) ** 2 +
            (viewer_y - target_y) ** 2
        )
        if dist > self.sight_radius:
            return False

        # In darkness, creatures without darkvision
        # have reduced effective sight radius
        if not self.sees_in_dark and ambient_light < 0.1:
            return dist <= max(1, self.sight_radius // 4)

        return True