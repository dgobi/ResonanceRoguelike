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

Keep each action’s `id` stable: cooldowns are keyed by that ID. Use one action per `key`, `Q` or `R`; the first matching entry wins. Keep `range: 1` for these melee actions. All shipped movesets require physical one-tile contact even if this number is increased; a range edit cannot enable ranged attacks. Keep `turn_cost: 1.0` when you want ordinary action timing.

Ordinary melee, movesets, monster melee and grass-entry free strikes require living, eligible fighters on distinct walkable neighboring cells. Cardinal and diagonal contact work; a diagonal needs at least one walkable orthogonal side. Closed doors, solid endpoints and sealed corners block contact independently of player FOV. Rejected contact preserves time, cooldowns, coatings, weapon balance and pending Press; a legal miss or dodge commits normally.

Fractional weapon costs accumulate separately from movement/work debt and sprint credit. Starting neutral, five accepted `0.8` actions pay four world phases (the fifth skips); five `1.2` actions pay six (the fifth adds one). The first fast action still pays one. A `0.8` followed by `1.2` returns to neutral in two phases. `1.0` actions and ordinary intervening actions preserve the balance; rejected movesets spend nothing. Misses and dodges are committed attacks. Costs resolve to millionths of a phase before accumulating, so authored decimal boundaries do not drift. Cooldown waits retain their own normal costs, and skipped phases do not tick cooldowns or other turn systems. The balance survives saves.

Heavy Blade’s Press kill pays its attack cost, then offers one immediate adjacent legal step in the same scene. That step waives only its base phase: entry hazards and terrain/needs/work surcharges still apply. Another committed action expires the opportunity, including a wait, attack, inventory use/equipment/reading, interaction, harvesting, crafting, perk acquisition, sprint activation or successful travel. Existing free actions remain free. Inspection, menus, saving, cancellation and rejected inputs preserve it. It cannot stack. A Press step preserves movement-speed credit without earning more, counts against sprint’s physical-move duration, and ticks world-phase bonuses only if a surcharge charges a phase. Pending, consumed and expired states restore exactly; older saves default to no opportunity and neutral weapon balance while preserving their existing positive work debt.

Examples of implemented effects are `reduce_av` in `dissolution_blade.json`, `suppress_ability_turns` in `severance_blade.json`, and `ignore_armour`, `ignore_dodge`, and `reveal_knowledge` in `revelation_lens.json`. These live inside an action’s `effects` object. `destroy_armour` currently subtracts two points from effective armour; it does not remove a separate armour-layer object.

Some existing declarations need code work before their descriptions can be fulfilled:

| Field | Current boundary |
|---|---|
| `pool_turns` in `dissolution_blade.json` | Read into the moveset result but never used to expire the pool. `place_pool` places decor on a kill; it does not establish a timed damage zone. |
| `ignore_armour_layers` in `crude_blade.json` | Not read by the moveset executor. The implemented bypass is `ignore_armour`. |
| `on_kill_only` | Not a general condition around every effect. Pool placement and Press’s follow-up have explicit kill checks in the engine. |

Changing those values alone cannot complete the missing behaviour. The relevant code is `engine/movesets.py` and the melee methods in `engine/engine.py`.

## Make a creature tougher or gentler

For the Briar Lurker, edit `data/entities/creatures/briar_lurker.json`. The current `base_hp` is `12`, `armour_value` is `3`, and attack damage is `1d4` plus `0`. For example, changing `base_hp` to `14` makes newly spawned lurkers survive longer without increasing their attack damage.

Use `base_hp` for health: `engine/creature_factory.py` gives it precedence over `fighter.max_hp`. Use the top-level `armour_value`, `damage_dice`, and `damage_bonus` for normal combat balance. The older `fighter.power` and `fighter.defense` fields are not substitutes for those attack and armour settings.

`essence_modifiers` describes the creature’s response to each named essence: values above `1.0` are weaknesses, below `1.0` are resistances, and `1.0` is neutral. Weapon strength scales that response. Change one relationship at a time so the resulting damage remains easy to understand.

`perception.sight_radius` tunes sight. `perception.hearing_radius` is now an active
integer control (0–1,000) in Workbench: zero disables hearing. Wandering/circling
mobile creatures investigate unidentified sounds after genuine sight and player
memory; ambush/fleeing archetypes keep their special rules, including Lurker
hibernation. Existing `ai_type` values are `wandering`, `ambush`, `fleeing`, and
`circling`. A new word here does not create a new AI. Special abilities still
dispatch through their stable creature identities.

G20 sound tuning is centralized in `engine/sound.py`: cardinal open travel costs
1, closed doors 4, solid walls block; there is no diagonal or scene-boundary
propagation. Per-event flood cost is capped at 48. A listener's cost allowance is
`strength + hearing_radius - 6` (with zero hearing always deaf). Initial strengths:
flint/musk impacts 6, committed combat/empty-crate dismantling 8, cracked bell 10,
intact bell 18. Only a bell terrain source can seed a nonwalkable origin. Combat
uses the attacker's tile, dismantling the crate, and throws their impact tile.
Misses/dodges still emit once; rejections and extra settlement phases do not.
No gathering, footsteps, doors or crafting emit gameplay sound.

Interest stores only source, kind, received strength and an inclusive absolute
deadline at emission world turn + 12. A player action at turn T can provoke the
normal AI in charged phases T+1 through T+12; T+13 expires it. An event emitted
during AI may affect later actors in that same phase; earlier actors wait for
their next ordinary budget. Higher received strength replaces an event; equal
strength prefers later delivery; weaker events do not renew it. Reaching the
empty source or a reachable cardinal approach to an occupied/bell source ends
interest. No attack, speed credit, pursuit transfer or last-seen-player memory
comes from hearing. Deadline expiry continues during disruption/absence and is
revalidated on return/F9 without movement. Saved actor hearing remains owned by
the saved instance.

`flint_shard` keeps cutting tier 1. Its six-tile owned throw consumes one unit for
a clatter with no weapon damage. New and historical null-handler shards gain
that use through a narrow dispatch/affordance fallback. Inventory adds its use
guidance at display time; neither carried fields nor the shipped definition is
rewritten. This deliberately preserves old pending workshop dependencies that
include flint. Workbench's item-use inspection reports the exact-ID capability.
Explicit nonempty instance overrides remain authoritative.

Keep the creature’s `id`. Saved actors, knowledge, corpses, and other references depend on it, even when the visible `tile` changes during play.

Stone Lurker wakes within three tiles and changes from rock to Lurker. Its separate AmbushAI trigger remains half its sight radius (currently 2.5), and speed remains `0.5`. Waking arms one bonus melee attempt: distance, barriers, impairment, ability suppression and disruption retain it. One legal attempt consumes it, including misses, dodges and zero damage, separately from its normal speed budget. Existing save fields retain hibernation, pending/consumed state and the one-time AI trigger; load does not wake or attack.

Plague Crow retains its adjacent melee and existing nonadjacent circling envelope of at most three Euclidean tiles. `ranged_attack.min_range: 2` selects projectile presentation; it is not a new maximum-range control. A nonadjacent attack requires walkable endpoints, a transparent Bresenham interior and at least one transparent orthogonal side for each diagonal ray step. Opaque terrain and closed doors block the line; actors do not. Damage eligibility is independent of projectile rendering. Throwing keeps its existing visibility, ownership, map, range and stricter walkable-segment flight checks.

## Terrain cover while stationary

Terrain with `secondary_effect: "concealment"` reduces creature sight range by two tiles, with a minimum of one, under the existing light/darkvision rules. Perception queries the occupied tile on the supplied scene map; the saved `_in_concealment` flag remains a compatibility field and cannot override physical terrain. Cover persists through waiting, stationary attacks, menus, saves and rejected inputs. Leaving cover clears its effective benefit immediately, including a Press step with no world phase. Arrival, restoration and terrain changes need no replayed step effects or turn. Close creatures can still see the player, and existing pursuers retain their trail until the existing memory/timeout rules lose it.

## Change how long a preparation lasts

These files are under `data/items/consumables/`:

| File | Fields to tune | What they measure |
|---|---|---|
| `bile_coating.json` | `temporary_essence[].strength`, `temporary_essence[].hits` | Essence strength and successful weapon contacts. |
| `marrow_seal.json` | `armor_bonus`, `armor_hits` | Extra torso armour and incoming contacts protected. |
| `stalker_unguent.json` | `speed_bonus`, `duration_turns` | Movement bonus and player-duration turns. |
| `wight_concentrate.json` | `true_sight_turns`, `resonance_add`, `corruption_add` | Sight duration and the immediate costs. |
| `musk_pellet.json` | `zone_radius`, `zone_turns` | Disruption-zone size and duration. |

Musk keeps radius 3 and six protected world phases including the throw: five
remain immediately afterward, the sixth phase is protected, and normal AI can
resume on phase seven. Its circular footprint uses the current owning map's
G19 terrain line: opaque interior cells, closed doors and sealed diagonal
corners block; the impact cell is included. Door changes affect the next query.
AI pause, passive/contact suppression and pursuer/crossing checks share this
coverage. Adjacent paused stair followers retain their source-scene live owner
instead of being moved immediately to the destination; normal pursuit can resume
after expiry. Nonplayer AI creatures (including Hollow, Wraith and Lurker) are
affected; the player is unaffected. No speed credit accumulates during a pause.
Overlaps are independent finite zones whose coverage forms a union. Actor
disruption and ability-suppression counters remain independent. Hot maps age
once per world phase, cold map zones freeze, and inactive serialized actor
counters retain their existing freeze rule. Sound's absolute deadline continues
to expire even while its listener is paused or absent; recovery replays no sound.

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


## Local rivals (G21)

Workbench exposes faction and an explicit hostility list only for ordinary
WanderingAI sources/candidates without ID-bound abilities. Exact labels have
1�32 lowercase letters/digits/underscores, starting with a letter; lists have at
most sixteen distinct tokens. `[]` selects nobody. Missing/null lists default to
`["player"]`; unmatched labels are legal and directional. Saved instances keep
their saved values. Fresh Bandits and Stalkers recognize each other; generic
predators and special abilities are unchanged.

Selection requires real sight. An observed target persists unless another observed
hostile has legal striking contact while it does not. Observed candidates beat a
hidden trail; last-observed phase + `alert_memory` is the inclusive rival deadline.
Sounds identify nobody. Rival intent never crosses scenes; actual player pursuit
retains its established timing and transfer routes. Creature fatalities create
ordinary harvestable remains without player kill credit. See the creature guide
and `docs/owner/GAMEPLAY_G21.md` for exact lifecycle and evidence limits.
