Current generation controls: see [G9](WORLDGEN_G9.md), the [country-network guide](../../roguelike/docs/COUNTRY_NETWORK.md), and the [working authoring recipes](../../roguelike/docs/STRUCTURE_AUTHORING.md). Settings 4 / plan 7 preserve the complete G8 settlement and rural baseline before optional connections. Country policy lives in `roguelike/data/generation/country_network.json`; town membership, multipliers, caps and repetition remain in `settlement_profiles.json`. Policy edits affect new plans, while saved worlds retain their resolved records.

# Tuning Resonance’s existing features

This guide covers changes the current game already knows how to use. Paths below start inside the `roguelike` directory, alongside `main.py`. Examples are small replacements within existing JSON objects; keep the surrounding fields.

Work in the main project branch; check it with `git branch --show-current`. Make a Git checkpoint before a coherent tuning change and another after checking it. Stage the specific files involved so unrelated work stays out of that checkpoint. Restart the game after editing data: `engine/data_loader.py` loads definitions at startup and caches them.

## Give a weapon more bite

Open `data/items/weapons/severance_blade.json`. Its current base damage is `1d6` plus `1`. To increase the flat bonus by one, change only:

```json
"damage_dice": "1d6",
"damage_bonus": 2
```

Use plain `NdM` dice, such as `1d6` or `2d4`. Put additions in `damage_bonus`; the current `engine/combat.py` dice parser does not support expressions such as `1d6+2`. `crit_chance` is an added probability expressed as a fraction. `essence` and `essence_strength` control the weapon’s interaction with creature resistances; retain the existing essence spelling and use strengths between `0` and `1` for ordinary tuning.

The same file contains `movesets`. To strengthen Severing Cut and shorten its cooldown, change that existing entry’s `damage_mult` from `1.2` to `1.3` and `cooldown` from `10` to `8`. The multiplier applies to the dice roll before flat bonuses. Both ordinary attacks and movesets use corruption bonuses and active coatings.

Keep each action’s `id` stable: cooldowns are keyed by that ID. Use one action per `key`, `Q` or `R`; the first matching entry wins. Keep `range: 1` for these melee actions. Increasing it does not implement a complete ranged targeting system. Keep `turn_cost: 1.0` when you want ordinary action timing.

Examples of implemented effects are `reduce_av` in `dissolution_blade.json`, `suppress_ability_turns` in `severance_blade.json`, and `ignore_armour`, `ignore_dodge`, and `reveal_knowledge` in `revelation_lens.json`. These live inside an action’s `effects` object. `destroy_armour` currently subtracts two points from effective armour; it does not remove a separate armour-layer object.

Some existing declarations need code work before their descriptions can be fulfilled:

| Field | Current boundary |
|---|---|
| `free_move_on_kill` in `heavy_blade.json` | Sets a pending flag, but movement does not consume that flag to grant a free move. |
| `pool_turns` in `dissolution_blade.json` | Read into the moveset result but never used to expire the pool. `place_pool` places decor on a kill; it does not establish a timed damage zone. |
| `ignore_armour_layers` in `crude_blade.json` | Not read by the moveset executor. The implemented bypass is `ignore_armour`. |
| `on_kill_only` | Not a general condition around every effect. Pool placement and the pending free-move flag have explicit kill checks in the engine. |

Changing those values alone cannot complete the missing behaviour. The relevant code is `engine/movesets.py` and the melee methods in `engine/engine.py`.

## Make a creature tougher or gentler

For the Briar Lurker, edit `data/entities/creatures/briar_lurker.json`. The current `base_hp` is `12`, `armour_value` is `3`, and attack damage is `1d4` plus `0`. For example, changing `base_hp` to `14` makes newly spawned lurkers survive longer without increasing their attack damage.

Use `base_hp` for health: `engine/creature_factory.py` gives it precedence over `fighter.max_hp`. Use the top-level `armour_value`, `damage_dice`, and `damage_bonus` for normal combat balance. The older `fighter.power` and `fighter.defense` fields are not substitutes for those attack and armour settings.

`essence_modifiers` describes the creature’s response to each named essence: values above `1.0` are weaknesses, below `1.0` are resistances, and `1.0` is neutral. Weapon strength scales that response. Change one relationship at a time so the resulting damage remains easy to understand.

`perception.sight_radius` and `perception.hearing_radius` tune detection. Existing `ai_type` values are `wandering`, `ambush`, `fleeing`, and `circling`. A new word here does not create a new AI. Likewise, special abilities such as briar retaliation and wraith sight drain have creature-specific code; copying their descriptive fields onto another creature does not give it the ability.

Keep the creature’s `id`. Saved actors, knowledge, corpses, and other references depend on it, even when the visible `tile` changes during play.

## Change how long a preparation lasts

These files are under `data/items/consumables/`:

| File | Fields to tune | What they measure |
|---|---|---|
| `bile_coating.json` | `temporary_essence[].strength`, `temporary_essence[].hits` | Essence strength and successful weapon contacts. |
| `marrow_seal.json` | `armor_bonus`, `armor_hits` | Extra torso armour and incoming contacts protected. |
| `stalker_unguent.json` | `speed_bonus`, `duration_turns` | Movement bonus and player-duration turns. |
| `wight_concentrate.json` | `true_sight_turns`, `resonance_add`, `corruption_add` | Sight duration and the immediate costs. |
| `musk_pellet.json` | `zone_radius`, `zone_turns` | Disruption-zone size and duration. |

For a longer bile coating, change its existing entry to:

```json
{"essence": "Dissolution", "strength": 0.4, "hits": 8}
```

The shipped value is six hits. Misses and dodges do not spend a coating charge; contact that armour fully deflects still does. The last armour-seal charge protects the current contact before expiring. Reapplying a matching weapon essence replaces its coating entry rather than stacking duplicate entries.

Player-duration effects include the action that consumes or applies the preparation. Actor suppression and disruption age after the affected actors’ turn processing. Keep counts as positive integers; do not equate `hits` with elapsed turns.

Keep the existing `on_use` handler when tuning these preparations. Adding an arbitrary handler name requires a matching method in `engine/item_system.py`; JSON cannot supply executable behaviour.

## Adjust a recipe’s cost or processing time

Open `data/recipes/bile_coating.json`. It requires one `caustic` ingredient and one `viscous` ingredient, both at `min_tier: 1`, plus ambient `burning` and `vessel` at tier one.

Each physical component unit needs a distinct item instance. `data/items/butchery/crow_bile.json` carries both tags, but one sac cannot pay for both required units. Increasing a component’s `quantity` increases the number of instances needed. Increasing `min_tier` narrows which ingredients qualify.

For reusable equipment, the decisive field is `consumed_on_use: false`, not its category or name. `data/items/components/clay_pot.json` already has that field and supplies `vessel` and `heatproof` keywords. Reusable inventory tools also supply ambient keywords. Ambient requirements are conditions and are not consumed.

`rendering/craft_screen.py` builds ambient sources from reusable inventory tools, the equipped light’s `provides_burning`, and nearby `campfire_lit` decor. A lit campfire within three tiles, including diagonals, supplies `burning` tier two. Recipe matching and final confirmation are implemented in `engine/crafting.py`; the final confirmation checks that the selected ingredients still exist.

To speed up cooking, change `processing_turns` in `data/recipes/cook_meat.json` from `8` to `6`. Retain its existing `passive_processing`, `processing_source`, `processing_decor`, and `result_item`. Cooking placement requires the lit fire itself. Other processing sources currently use the drying-placement route; a new source name does not implement a new workstation.

`known: false` blocks crafting through the existing screen; it does not create a discovery mechanic. Keep `result_item` pointed at an existing item ID. World placement recipes, such as `campfire.json`, instead use the established `places_in_world` and `result_tile` route.

## Rewrite a letter or make an existing text more common

For ordinary prose, start with `data/texts/world/letters/letter_a.json`. Edit `title` and the `text` inside its `pages` array. Keep its `id`, page structure, and language settings. Use `\n` inside a JSON string for paragraph breaks. These are content edits; they do not require a new item type.

The document instance points to this definition through `text_id`. `data/texts/text_item_map.json` maps `letter_a` to the existing `letter` item type. `data/items/documents/letter.json` supplies the physical item and its `on_use: "read"` behaviour.

In `data/loot/world_texts_common.json`, `letter_a` currently has weight `5`. Raising that weight makes it more likely relative to other entries where this table is used. This is a relative weight, not a percentage. `generation/local_gen.py` uses that table for several generated submaps, including caves and cellars. Existing generated rooms are not repopulated by changing the table.

To add another ordinary text using this route, duplicate the structure of an existing text, give it a unique ID, add its item-type mapping, and reference it in an appropriate existing text table. Preserve existing IDs so saved documents remain readable. Deep Tongue text also involves the lexicon and teaching state, so treat that as a separate content task.

## Know what an old save will show

Restarting reloads definitions, but loading a save also restores recorded instance state:

| Change | What happens after restart and load |
|---|---|
| Weapon damage and movesets | Attacks consult the current weapon definition, including for an existing weapon. |
| Creature health, armour, perception | Saved values override factory defaults for existing actors. Use a new spawn to assess the new defaults. |
| Item weight, keywords, nutrition, description, `on_use` | Saved instance fields are restored. Newly created items receive changed defaults. |
| Coating charges and active effect durations | Already applied effects retain their saved remaining state. Changed preparation settings apply when used again. |
| Text body | Reading looks up the current text definition by the saved `text_id`. |
| Processing duration | An existing job retains its recorded remaining time; the recipe change affects newly started jobs. |

These distinctions come from `engine/item_factory.py`, `engine/save_components.py`, and `engine/save_manager.py`. Avoid renaming or deleting referenced IDs as a routine balance change; that can invalidate saved references.

## Check and checkpoint the edit

Use strict JSON: double quotes, no comments, no trailing commas. Definitions loaded recursively from `data/items`, `data/entities`, `data/recipes`, and `data/texts` need unique IDs within their respective registry. Duplicate IDs overwrite earlier definitions; loading successfully is not proof that references or behaviour are correct.

From the game directory, parse a changed file and inspect its diff:

```bash
python -m json.tool data/items/weapons/severance_blade.json
git diff -- data/items/weapons/severance_blade.json
```

Have Codex check referenced IDs and run the relevant included regression tests for behavioural changes. Record what changed and the check result in the checkpoint message. Keep data tuning small enough to reverse cleanly. New handlers, new state fields, different save semantics, and new mechanics require implementation and appropriate tests beyond editing JSON.

## G4 composition tuning

The active composition settings remain `roguelike/data/generation/g3_config.json`;
the filename is retained for compatibility. See the complete active-field table,
profile weighting, public/private access rules and new-world/saved-world behavior
in [Structure Authoring](../../roguelike/docs/STRUCTURE_AUTHORING.md).
Country and town-street widths are independent; the assigned band's actual width
governs each building's fit. Existing `town_config.json`, `rotatable`, `facing` and
legacy weights remain preserved metadata rather than new planner controls.
