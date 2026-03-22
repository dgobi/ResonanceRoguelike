# engine/turn_queue.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.actor import Actor


class TurnQueue:
    """
    Tracks which actors act and in what order.
    Currently round-robin; will become a time/speed-based
    priority queue when we build the time system.
    """

    def __init__(self) -> None:
        self._actors: list[Actor] = []
        self._index: int = 0

    def add(self, actor: Actor) -> None:
        self._actors.append(actor)

    def remove(self, actor: Actor) -> None:
        if actor in self._actors:
            self._actors.remove(actor)

    def next(self) -> Actor:
        if not self._actors:
            raise IndexError("Turn queue is empty.")
        actor = self._actors[self._index % len(self._actors)]
        self._index += 1
        return actor

    def __len__(self) -> int:
        return len(self._actors)