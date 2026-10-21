# engine/hooks.py
from __future__ import annotations
from enum import Enum, auto
from typing import Callable
from engine.palette import *


class HookEvent(Enum):
    ON_TURN           = auto()  # start of each player turn
    ON_DAMAGE_TAKEN   = auto()  # player receives damage
    ON_DAMAGE_DEALT   = auto()  # player deals damage
    ON_TILE_ENTERED   = auto()  # player steps onto a tile
    ON_ENTITY_KILLED  = auto()  # player kills an entity
    ON_ITEM_EQUIPPED    = auto()  # player equips an item
    ON_STATUS_APPLIED   = auto()  # a status is applied to player
    ON_CHUNK_ENTERED    = auto()  # player enters a new chunk
    ON_CRITICAL_HIT     = auto()  # player lands a critical hit


class HookRegistry:
    """
    Central registry for perk hook handlers.
    Handlers registered per event type.
    Multiple handlers per event, called in registration order.
    Effects from all handlers are merged and returned together.
    """

    def __init__(self) -> None:
        self._handlers: dict[HookEvent, list[Callable]] = {
            e: [] for e in HookEvent
        }

    def register(self, event: HookEvent, handler: Callable) -> None:
        """
        Register a handler for an event.
        handler signature: (payload: dict) -> dict | None
        """
        self._handlers[event].append(handler)

    def unregister(self, event: HookEvent, handler: Callable) -> None:
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    def fire(self, event: HookEvent, payload: dict) -> dict:
        """
        Fire all handlers for an event.
        Merges returned effects. damage_modifier effects multiply.
        Returns merged effect dict (may be empty).
        """
        merged: dict = {}
        for handler in self._handlers[event]:
            try:
                result = handler(payload)
            except Exception as e:
                print(f"[hooks] handler error in {handler.__name__}: {e}")
                continue
            if not result:
                continue
            _merge_effects(merged, result)
        return merged


def _merge_effects(base: dict, new: dict) -> None:
    """Merge new effects into base in-place."""
    for key, val in new.items():
        if key == "damage_modifier":
            base[key] = base.get(key, 1.0) * val
        elif key == "add_message":
            if key not in base:
                base[key] = []
            base[key].append({
                "text":  val,
                "color": new.get("message_color", FROST_WHITE),
            })
        elif key not in base:
            base[key] = val
        # For other keys: first handler wins
