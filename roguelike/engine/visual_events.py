# engine/visual_events.py
from __future__ import annotations
from dataclasses import dataclass, field
from engine.palette import *


@dataclass
class VisualEvent:
    """
    A transient visual effect queued by abilities and gameplay systems.
    Processed and cleared by the renderer each frame.

    type values:
      "aura"      — radius ring around a position
      "pulse"     — brief flash at a position
      "particles" — particle emission (Tier 3 particle system)
      "overlay"   — screen-space tint or overlay
    """
    type:      str
    x:         int           # world tile x (for world-space effects)
    y:         int           # world tile y
    radius:    float = 0.0
    color:     tuple = TRUE_WHITE
    duration:  int   = 1     # frames to display (1 = single frame flash)
    intensity: float = 1.0
    data:      dict  = field(default_factory=dict)


class VisualEventQueue:
    """
    Engine holds one instance. Abilities append to it.
    Renderer reads active events each frame; tick() decrements duration.
    Events with duration <= 0 are removed automatically.
    """

    def __init__(self) -> None:
        self._events: list[VisualEvent] = []

    def add(self, event: VisualEvent) -> None:
        self._events.append(event)

    def get_active(self) -> list[VisualEvent]:
        return [e for e in self._events if e.duration > 0]

    def tick(self) -> None:
        """Decrement duration on all events. Call once per frame."""
        for e in self._events:
            e.duration -= 1
        self._events = [e for e in self._events if e.duration > 0]

    def clear(self) -> None:
        self._events.clear()
