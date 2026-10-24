# World names, mythology, and biome identity

Use this chapter to change the world's naming voice, its seeded mythological framing, and the environmental identity of generated regions. Structure placement and creature-zone content have their own chapters; the settings here explain what actually connects those systems to a biome.

## Change generated names

`roguelike/data/names.json` holds reusable fragments in three styles. These are naming styles, not the learned Deep Tongue vocabulary.

| Table | Lists you can edit | Combination |
|---|---|---|
| `common` | `region_prefixes`, `region_suffixes` | Region prefix + lowercased suffix, optionally followed by a region-type word. |
| `common` | `settlement_roots`, `settlement_suffixes` | Town root + lowercased suffix. |
| `old` | `roots`, `connectors`, `suffixes` | Root + connector + suffix. Empty connector strings are valid. |
| `deep` | `openings`, `closings` | Opening + closing. |

Keep every required list present and nonempty: generation calls `random.choice()` on them. Add fragments, restart the process, and inspect a range of generated names before adopting the change. The module caches these tables after its first load. There is no uniqueness guarantee, and the common-region doubled-syllable check rerolls only once.

The style mix and words such as “Wood,” “Fen” and “Barrow” are Python tables in `world/name_gen.py`, not JSON. For example, forest names choose old/common/deep with weights 0.5/0.4/0.1; town names choose common/old with 0.7/0.3. `_REGISTER_WEIGHTS` is accumulated directly against a 0–1 random roll, so preserve a total of 1.0 when editing a row. Unlisted region types use the common style and no additional region-type word.

For a small, reproducible text-only sample, run this from `roguelike/` using the configured Python interpreter:

```python
from world.name_gen import assign_chunk_name

for seed in range(8):
    name, register = assign_chunk_name("forest", seed)
    print(seed, register, name)
```

`assign_chunk_name()` derives a separate RNG from the supplied chunk seed, so naming does not consume the terrain generator's RNG stream. Shared settlement names derive from the world seed and settlement ID through `settlement_context.semantics()`. Editing list contents or order can change names generated for the same seed; record the source revision alongside the seed.

Sources: [name fragments](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/data/names.json), [name generation](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/world/name_gen.py), [shared settlement naming](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/settlement_context.py).

## Change the world's mythological framing

`world/world_myth.py` chooses an age, sundering epithet, myth shape, prominent god and faction pair from Python lists. Edit `_AGE_WORDS`, `SUNDERING_ARCHETYPES`, `MYTH_SHAPES`, `GOD_NAMES` and `FACTION_PAIRS` to change those choices. A faction entry remains a pair of strings. Keep all choice lists nonempty.

The active world-generation wrapper fixes the myth's locus to **VUKH**, at the generated VUKH coordinates. The helper's internal selection of a nearby dungeon is overwritten. To change the active locus policy, inspect `generation/world_gen.py::_generate_world_myth()` as well as the helper.

The overmap displays the age, myth shape and sundering epithet; with `DEBUG_MODE = True`, F9 prints the full myth, including god and factions. No active faction simulation or automatic text-template substitution consumer was found for the god/faction strings in this checkout. Their evocative names are stored narrative metadata, not a complete faction system. To make a text react to them, implement and test an explicit reader/template consumer.

Names and the selected myth are serialized. Existing saved worlds retain their generated strings after a source-list edit. Use a new disposable world to review the full result; renaming tables does not rename an established campaign.

Sources: [myth choices](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/world/world_myth.py), [active naming and VUKH-locus policy](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/world_gen.py), [overmap presentation](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/rendering/renderer.py), [world serialization](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/save_manager.py).

## Which biome fields are active?

Biome files live under `roguelike/data/biomes/`. Several retained fields describe design intent without controlling the current generator. Use the table to choose the real edit point.

| JSON field | Current role |
|---|---|
| `id` | Registry identity and the chunk's selected biome ID. Keep references stable. |
| `elevation_range`, `moisture_range` | Inclusive normalized matching ranges for ordinary biome assignment. |
| `river_adjacent` | Adds 0.3 to the biome's match score on river chunks; it is not a strict requirement or prohibition. |
| `base_resonance`, `difficulty_base` | Starting values; world-distance, river and other policies subsequently modify them. They are not final displayed values. Shared town semantics also read the town values. |
| `flint_scatter_rate` | Per-candidate-cell probability for wilderness flint placement, subject to terrain/reservation rules. |
| `waystone_inscriptions` | Text IDs selected at first examination, then retained per waystone. Keep every referenced text defined. |
| `display_name`, `overmap_tile`, `overmap_color` | No biome-data consumers found. Current overmap art comes from `RegionType.overmap_tile()` and the tile/sprite registries. |
| `generator` | No dispatch consumer found. `generate_region()` branches on `RegionType` in Python. |
| `creature_zones` | Does not assign current chunk zones. `world_gen.BIOME_ZONES` and saved settlement policy do that. |
| `submap_types`, `submap_weight` | Do not drive random submap assignment. `world_gen.SUBMAP_TYPES` and `SUBMAP_WEIGHTS` are the active tables. |
| `entry_messages`, `resonance_messages` | No runtime consumers found for these biome declarations. |
| `waystone_themes`, `waystone_fallback_inscriptions` | No current consumers found. An empty inscription list falls back to Engine's default IDs regardless of the fallback flag. Word-learning categories use Engine's `_WAYSTONE_CATEGORIES`. |

Ordinary biome assignment first filters by both ranges, then scores closeness to their centres and applies the river bonus. It chooses the highest score, not a weighted random biome. VUKH peak/ring handling, capital and town policy have separate ownership. When no ordinary biome matches, the code falls back to plains. Adding another biome with overlapping ranges therefore changes competition across the whole map.

An unfamiliar biome ID becomes `RegionType.UNKNOWN`; the local region dispatcher then uses its default open-ground branch and the overmap asks for `overmap_unknown`. Adding a JSON file alone does not create a complete new environment. A genuinely new biome needs the enum/dispatch, zone/submap policies, name style where desired, art registration and the relevant world-plan compatibility review.

Sources: [forest example](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/data/biomes/forest.json), [biome matching and code-owned tables](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/world_gen.py), [RegionType](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/world/world_map.py), [local region dispatch](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/region_gen.py), [waystone interaction](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/engine.py).

## Resource ecology and gathering availability

For current planned scenes, `generation/planned_dressing.py` runs wilderness resource passes after shared infrastructure is finalized. It protects reserved cells, submap entrances, existing decor, floor objects and containers. Town/capital policy excludes these wilderness resource passes. A high rate cannot override an ineligible placement site.

| Resource | Availability policy |
|---|---|
| Dead wood | Each `tree` cell gets an 8% attempt to place on an eligible neighboring ground cell; this rate is Python code. |
| Flint | Biome `flint_scatter_rate`; successful placements have a 30% chance to try one orthogonal neighbor. Forest currently uses 0.002, or 0.2% per eligible trial, before the cluster effect. |
| Clay | Eligible ground within Chebyshev distance 2 of `river_water`, `river_bank` or `river_stones`; up to four primary placements, each with a 40% chance to try an adjacent extra. The extras do not increment the primary counter, so the actual total can exceed four. |

The finished map records `functional_generation` resource counts and absence reasons. Use those diagnostics to distinguish a legitimate lack of eligible sites from a missing definition. The item produced when gathering, the success chance and depletion result belong to terrain/interaction definitions; changing placement density does not change yield.

For a tuning pass, keep a small fixed set of world seeds, compare newly generated scenes in the intended biomes, inspect the recorded resource counts and absence reasons, then try actual gathering in a disposable scene. Preserve the planned-dressing restrictions when adding a resource; unrestricted scatter after structures can damage access or overwrite authored content.

Sources: [reservation-aware dressing and diagnostics](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/planned_dressing.py), [resource-scatter implementations](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/region_gen.py), [terrain and gathering definitions](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/data/terrain.json).
