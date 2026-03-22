# components/language.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Language:
    """
    Tracks the player's knowledge of the deep tongue.

    known_deep_words: set of word strings the player has learned.
    translation_events: maps word → turn it was learned, for
                        the translation visual effect in text_reader.
    recovered_spans: set of (text_id, page_idx, span_idx) tuples
                     for damaged text spans the player has recovered
                     via The Witnessing perk line.
    recovered_text: maps (text_id, page_idx, span_idx) → recovered string.
    """
    known_deep_words:   set[str]          = field(default_factory=set)
    translation_events: dict[str, int]    = field(default_factory=dict)
    recovered_spans:    set[tuple]        = field(default_factory=set)
    recovered_text:     dict[tuple, str]  = field(default_factory=dict)

    def knows(self, word: str) -> bool:
        return word.lower() in self.known_deep_words

    def learn(self, word: str, turn: int) -> bool:
        """Learn a deep tongue word. Returns True if this is new knowledge."""
        word = word.lower()
        if word in self.known_deep_words:
            return False
        self.known_deep_words.add(word)
        self.translation_events[word] = turn
        return True

    def recover_span(
        self,
        text_id:   str,
        page_idx:  int,
        span_idx:  int,
        recovered: str,
    ) -> None:
        """Mark a damaged text span as recovered. Called by Witnessing perks."""
        key = (text_id, page_idx, span_idx)
        self.recovered_spans.add(key)
        self.recovered_text[key] = recovered

    def is_recovered(self, text_id: str, page_idx: int, span_idx: int) -> bool:
        return (text_id, page_idx, span_idx) in self.recovered_spans

    def get_recovered(self, text_id: str, page_idx: int, span_idx: int) -> str | None:
        return self.recovered_text.get((text_id, page_idx, span_idx))
