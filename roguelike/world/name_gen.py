# world/name_gen.py
from __future__ import annotations
import random
import json
from pathlib import Path

_TABLES: dict = {}

_REGISTER_WEIGHTS: dict[str, list[tuple[str, float]]] = {
    "dungeon":  [("old", 0.6),   ("deep", 0.3),   ("common", 0.1)],
    "heath":    [("common", 0.5),("old", 0.4),     ("deep", 0.1)],
    "forest":   [("old", 0.5),   ("common", 0.4),  ("deep", 0.1)],
    "swamp":    [("old", 0.4),   ("deep", 0.4),    ("common", 0.2)],
    "mountain": [("old", 0.5),   ("deep", 0.3),    ("common", 0.2)],
    "town":     [("common", 0.7),("old", 0.3),     ("deep", 0.0)],
    "plains":   [("common", 0.6),("old", 0.3),     ("deep", 0.1)],
}

_REGION_TYPE_WORDS: dict[str, list[str]] = {
    "heath":    ["Heath", "Moor", "Fell"],
    "forest":   ["Wood", "Forest", "Holt"],
    "swamp":    ["Mere", "Fen", "Marsh"],
    "mountain": ["Heights", "Ridge", "Pass"],
    "plains":   ["Plain", "Reach", "Flats"],
    "dungeon":  ["Barrow", "Vault", "Depths"],
    "town":     [],
}


def _load() -> None:
    global _TABLES
    if not _TABLES:
        path = Path(__file__).parent.parent / "data" / "names.json"
        with open(path, encoding="utf-8") as f:
            _TABLES = json.load(f)


def pick_register(region_type: str, rng: random.Random) -> str:
    options = _REGISTER_WEIGHTS.get(region_type, [("common", 1.0)])
    roll = rng.random()
    cumulative = 0.0
    for reg, prob in options:
        cumulative += prob
        if roll <= cumulative:
            return reg
    return options[-1][0]


def _common_region(rng: random.Random) -> str:
    t      = _TABLES["common"]
    prefix = rng.choice(t["region_prefixes"])
    suffix = rng.choice(t["region_suffixes"])
    # Avoid doubled syllable (e.g. "Fenfen")
    if suffix.lower().startswith(prefix.lower()[:2].lower()):
        suffix = rng.choice(t["region_suffixes"])
    return prefix + suffix.lower()


def _old_name(rng: random.Random) -> str:
    t    = _TABLES["old"]
    root = rng.choice(t["roots"])
    conn = rng.choice(t["connectors"])
    suf  = rng.choice(t["suffixes"])
    return root + conn + suf


def _deep_name(rng: random.Random) -> str:
    t = _TABLES["deep"]
    return rng.choice(t["openings"]) + rng.choice(t["closings"])


def generate_region_name(
    region_type: str,
    register:    str,
    rng:         random.Random,
) -> str:
    _load()
    type_words = _REGION_TYPE_WORDS.get(region_type, [""])
    type_word  = rng.choice(type_words) if type_words else ""

    if register == "common":
        base = _common_region(rng)
    elif register == "old":
        base = _old_name(rng)
    else:
        base = _deep_name(rng)

    return f"{base} {type_word}" if type_word else base


def generate_settlement_name(
    register: str,
    rng:      random.Random,
) -> str:
    _load()
    if register == "common":
        t    = _TABLES["common"]
        root = rng.choice(t["settlement_roots"])
        suf  = rng.choice(t["settlement_suffixes"])
        return root + suf.lower()
    elif register == "old":
        return _old_name(rng)
    else:
        return _deep_name(rng)


def assign_chunk_name(
    region_type: str,
    chunk_seed:  int,
) -> tuple[str, str]:
    """
    Return (name, register) for a chunk, deterministically from its seed.
    Uses a fixed offset so name RNG is independent from terrain RNG.
    """
    rng      = random.Random(chunk_seed ^ 0xA7F3C1)
    register = pick_register(region_type, rng)
    if region_type == "town":
        name = generate_settlement_name(register, rng)
    else:
        name = generate_region_name(region_type, register, rng)
    return name, register
