# engine/language_system.py
"""
Deep tongue learning system — pure functions, no engine state imports.

Words are learned from waystones, found texts, and corruption thresholds.
Each word belongs to a category and tier. Learning never duplicates.

Restrictions:
  - Tier 3+ words are never returned by automatic learning functions.
    They require explicit learn_word() calls (future unlock conditions).
  - Ominous words are excluded from waystone learning (text/corruption only).
  - Legacy words are learnable from all sources — no restriction.
"""
from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from components.language import Language


def get_learnable_words(
    all_words: dict,
    source: str,
    exclude_ids: set | None = None,
) -> list[str]:
    """Return list of word ids learnable from this source."""
    result = []
    for wid, wdef in all_words.items():
        if wdef.get("tier", 1) >= 3:
            continue
        if source not in wdef.get("learn_sources", []):
            continue
        if source == "waystone" and wdef.get("category") == "ominous":
            continue
        if exclude_ids and wid in exclude_ids:
            continue
        result.append(wid)
    return result


def learn_word(
    word_id: str,
    source: str,
    language: "Language",
    all_words: dict,
    rng: random.Random,
) -> tuple[bool, str]:
    """
    Attempt to learn word_id from source.
    Returns (learned: bool, word_id_actually_learned: str).
    If word_id already known, draws next unknown word from same category and tier.
    Never duplicates. Never fails if unknown words of that category/tier exist.
    Falls back to any unknown learnable word if category exhausted.
    """
    w = all_words.get(word_id)
    if w is None:
        return False, ""

    if not language.knows(word_id):
        # Check source is valid for this word
        sources = w.get("learn_sources", [])
        if sources and source not in sources:
            return False, ""
        language.learn(word_id, 0)  # turn filled by caller if needed
        return True, word_id

    # Already known — draw from same category/tier
    cat = w.get("category", "")
    tier = w.get("tier", 1)
    return learn_from_category(cat, tier, source, language, all_words, rng)


def learn_from_category(
    category: str,
    tier: int,
    source: str,
    language: "Language",
    all_words: dict,
    rng: random.Random,
) -> tuple[bool, str]:
    """Learn a random unknown word from category/tier pool."""
    known = language.known_deep_words
    learnable = get_learnable_words(all_words, source, exclude_ids=known)

    # Primary pool: matching category and tier
    pool = [
        wid for wid in learnable
        if all_words[wid].get("category") == category
        and all_words[wid].get("tier", 1) == tier
    ]
    if not pool:
        # Fallback: any unknown learnable word (already filtered by source/tier/ominous)
        pool = learnable
    if not pool:
        return False, ""

    chosen = rng.choice(pool)
    language.learn(chosen, 0)
    return True, chosen


def learn_from_text(
    text_def: dict,
    language: "Language",
    all_words: dict,
    rng: random.Random,
) -> list[str]:
    """
    Learn words from a text with a teach_words block.
    Returns list of word_ids actually learned.
    """
    tw = text_def.get("teach_words")
    if not tw:
        return []

    categories = tw.get("categories", [])
    tier = tw.get("tier", 1)
    source = "text"

    # Every text teaches exactly one word on first read — no exceptions.
    cat = categories[0] if categories else ""
    if cat:
        ok, wid = learn_from_category(cat, tier, source, language, all_words, rng)
    else:
        ok, wid = learn_from_category("", tier, source, language, all_words, rng)

    return [wid] if ok else []


def get_unknown_words_in_text(
    text_body: str,
    language: "Language",
    all_words: dict,
) -> list[str]:
    """Return list of deep tongue word ids present in text_body that are not yet learned."""
    unknown = []
    for token in text_body.split():
        clean = token.strip(".,;:!?\"'()[]").lower()
        if clean in all_words and not language.knows(clean):
            if clean not in unknown:
                unknown.append(clean)
    return unknown
