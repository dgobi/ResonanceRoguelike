# world/world_myth.py
"""
WorldMyth — the seeded mythological backdrop of a generated world.

Generated once at world creation from the world seed. Provides the
archetypal framing that underlies dungeon names, faction identities,
and narrative fragments found in texts.

Fields read by other systems:
  age_name          — "The Age of Silence" etc.
  sundering_epithet — what the locals called the catastrophe
  myth_shape        — the archetypal narrative frame
  prominent_god     — the deity most associated with this world's events
  locus_name        — name of the most significant dungeon chunk
  locus_wx/wy       — world coordinates of the locus chunk
  faction_a/b       — the two primary competing factions
"""
from __future__ import annotations
import random
from dataclasses import dataclass


# ------------------------------------------------------------------ #
#  Constants
# ------------------------------------------------------------------ #

SUNDERING_ARCHETYPES: list[str] = [
    "The Final Tuning",
    "The Completion of the Array",
    "The Last Ringing",
    "The Great Convergence",
    "The Discharge",
    "The Resonant Silence",
    "The Bell-Song's End",
    "The Sounding",
    "The Unmaking of the Chord",
    "The Long Tone",
    "The Culmination",
    "The Accord",
]

MYTH_SHAPES: list[str] = [
    "The Punishment",    # the world was punished for transgression
    "The Abandonment",   # the gods left the mechanism running
    "The Completion",    # something finished what it was built to do
    "The Error",         # something went wrong; nobody intended it
    "The Sacrifice",     # deliberate, for a purpose not yet known
    "The Release",       # something long-contained was freed
    "The Inversion",     # what was meant to protect became the harm
    "The Answer",        # a question was asked and answered terribly
    "The Inheritance",   # the current age received what the prior age built
]

GOD_NAMES: list[str] = [
    "The Void-That-Precedes",
    "The Burning Throne",
    "The Dreaming",
    "The Measuring",
    "The Prior Claimant",
    "The Consistent Omission",
    "The Broken Ones",
]

FACTION_PAIRS: list[tuple[str, str]] = [
    ("The Keepers of the Array",  "The Silenced Guild"),
    ("The Resonant Order",        "The Unbound Wanderers"),
    ("The Bell-Wardens",          "The Stone-Breakers"),
    ("The Tuned Ones",            "The Deaf"),
    ("The Architects' Heirs",     "The Survivors"),
    ("The Sealed",                "The Released"),
    ("The Inheritors",            "The Undone"),
    ("The Warden-Scholars",       "The Unrecorded"),
]

_AGE_WORDS: list[str] = [
    "Stone", "Silence", "Ringing", "Ash", "Turning",
    "Ending", "Long Dark", "Quiet", "Accumulation",
    "Resonance", "Forgetting", "Hollow Days",
]


# ------------------------------------------------------------------ #
#  WorldMyth dataclass
# ------------------------------------------------------------------ #

@dataclass
class WorldMyth:
    age_name:          str
    sundering_epithet: str
    myth_shape:        str
    prominent_god:     str
    locus_name:        str
    locus_wx:          int
    locus_wy:          int
    faction_a:         str
    faction_b:         str

    def to_dict(self) -> dict:
        return {
            "age_name":          self.age_name,
            "sundering_epithet": self.sundering_epithet,
            "myth_shape":        self.myth_shape,
            "prominent_god":     self.prominent_god,
            "locus_name":        self.locus_name,
            "locus_wx":          self.locus_wx,
            "locus_wy":          self.locus_wy,
            "faction_a":         self.faction_a,
            "faction_b":         self.faction_b,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldMyth":
        return cls(
            age_name          = data["age_name"],
            sundering_epithet = data["sundering_epithet"],
            myth_shape        = data["myth_shape"],
            prominent_god     = data["prominent_god"],
            locus_name        = data["locus_name"],
            locus_wx          = data["locus_wx"],
            locus_wy          = data["locus_wy"],
            faction_a         = data["faction_a"],
            faction_b         = data["faction_b"],
        )


# ------------------------------------------------------------------ #
#  Generation
# ------------------------------------------------------------------ #

def generate_world_myth(
    seed:          int,
    submap_chunks: list[tuple[int, int]],
    name_gen,
) -> WorldMyth:
    """
    Generate a deterministic WorldMyth from the world seed.
    Uses a distinct RNG offset so myth selection is independent
    from terrain generation at the same seed.

    submap_chunks: list of (wx, wy) for chunks with submaps, sorted by
                   distance from world centre.
    name_gen:      the world.name_gen module (passed to avoid circular import).
    """
    rng = random.Random(seed ^ 0xDEADBEEF)

    age_name          = f"The Age of {rng.choice(_AGE_WORDS)}"
    sundering_epithet = rng.choice(SUNDERING_ARCHETYPES)
    myth_shape        = rng.choice(MYTH_SHAPES)
    prominent_god     = rng.choice(GOD_NAMES)
    faction_a, faction_b = rng.choice(FACTION_PAIRS)

    # Locus: pick from the closest quarter of submap chunks to world centre.
    # If no submaps exist fall back to (0,0).
    if submap_chunks:
        pool      = submap_chunks[:max(1, len(submap_chunks) // 4)]
        locus_wx, locus_wy = rng.choice(pool)
    else:
        locus_wx, locus_wy = 0, 0

    # Give the locus a name using a seed that is distinct from its terrain seed.
    locus_seed = seed ^ (locus_wx * 7919 + locus_wy * 6271) ^ 0xC0FFEE
    locus_name, _ = name_gen.assign_chunk_name("dungeon", locus_seed)

    return WorldMyth(
        age_name          = age_name,
        sundering_epithet = sundering_epithet,
        myth_shape        = myth_shape,
        prominent_god     = prominent_god,
        locus_name        = locus_name,
        locus_wx          = locus_wx,
        locus_wy          = locus_wy,
        faction_a         = faction_a,
        faction_b         = faction_b,
    )
