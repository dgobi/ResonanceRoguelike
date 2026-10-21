# engine/message_log.py
from __future__ import annotations
from dataclasses import dataclass, field
from engine.palette import *


# Message colors — thematic palette
MSG_NORMAL    = BONE_PALE   # default parchment
MSG_IMPORTANT = RESONANCE_GOLD   # gold — significant events
MSG_DANGER    = EMBER_GLOW    # blood red — injury, threat
MSG_WORLD     = LIFE_GREEN   # muted green — world/environment
MSG_CORRUPT   = RESONANCE_BLOOM    # void purple — corruption events
MSG_SYSTEM    = SLATE_DARK   # grey — system messages
MSG_WHISPER   = STONE_BLUE   # dim blue — things half-heard


@dataclass
class Message:
    text:  str
    color: tuple[int, int, int] = MSG_NORMAL
    turn:  int                  = 0
    count: int                  = 1   # for stacking identical messages

    def with_count(self) -> str:
        if self.count > 1:
            return f"{self.text} (x{self.count})"
        return self.text


class MessageLog:
    """
    Global message log. Any system can write to it.
    The UI panel reads from it.
    Messages stack if identical and consecutive.
    """

    def __init__(self, max_messages: int = 100) -> None:
        self.messages:     list[Message] = []
        self.max_messages: int           = max_messages
        self.current_turn: int           = 0

    def add(
        self,
        text:  str,
        color: tuple[int, int, int] = MSG_NORMAL,
    ) -> None:
        # Stack identical consecutive messages
        if (self.messages and
                self.messages[-1].text == text and
                self.messages[-1].turn == self.current_turn):
            self.messages[-1].count += 1
            return

        self.messages.append(Message(text, color, self.current_turn))

        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def add_important(self, text: str) -> None:
        self.add(text, MSG_IMPORTANT)

    def add_danger(self, text: str) -> None:
        self.add(text, MSG_DANGER)

    def add_world(self, text: str) -> None:
        self.add(text, MSG_WORLD)

    def add_corrupt(self, text: str) -> None:
        self.add(text, MSG_CORRUPT)

    def add_whisper(self, text: str) -> None:
        self.add(text, MSG_WHISPER)

    def recent(self, n: int = 5) -> list[Message]:
        """Return the n most recent messages."""
        return self.messages[-n:]

    def advance_turn(self) -> None:
        self.current_turn += 1