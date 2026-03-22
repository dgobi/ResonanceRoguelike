# Perk Definitions

Each perk is a JSON file. Filename matches the perk id.
Perks are organized into subdirectories by affinity.

## Schema

```json
{
  "id": "ear_pressed_to_stone",
  "name": "The Ear Pressed to Stone",
  "affinity": "the_hollow_road",
  "description": "...",
  "effect_type": "...",
  "effect_params": {},
  "unlock_conditions": {
    "corruption_min": 0.0,
    "corruption_max": 1.0,
    "perks_required": [],
    "affinity_score_min": 0.0,
    "deep_words_min": 0
  }
}
```

## Effect Types (to be implemented in Tier 3)
- `new_interaction`  — adds a new action option in specific contexts
- `world_query`      — allows querying the world state in new ways
- `ritual_modifier`  — changes ritual requirements or outcomes
- `passive`          — always-on effect checked by relevant systems
- `language`         — affects deep tongue learning or translation
