# Weapons, armour and combat balance

Current combat uses a single HP pool and a single effective armour value. A weighted hit location modifies damage and presentation; it does not maintain an independent health pool for each limb. Use the current consumers below when old body-system diagrams disagree.

## Make an existing blade stronger

Open `roguelike/data/items/weapons/severance_blade.json`. The shipped base is `damage_dice: "1d6"` and `damage_bonus: 1`. To add one point of flat base damage, change only `damage_bonus` to `2`.

```json
"damage_dice": "1d6",
"damage_bonus": 2
```

Use plain `NdM` strings: `1d6`, `2d4`, and so on. The current parser does not support `1d6+2`; it falls back to one on a parsing error. The older `damage` field is not the ordinary weapon-dice field. Keep the ID stable so saved weapons and content references still resolve.

For a new weapon, copy `crude_blade.json` or another working weapon, give it a new ID/name, retain `category: "weapon"`, `slot: "weapon"`, `on_use: "equip_toggle"`, and register an acquisition route. Copying the whole current file is safer than adapting an old schematic example.

## What the main numbers mean

| Field | Current effect |
|---|---|
| `damage_dice` | Random base roll; multiple dice alter both the average and distribution |
| `damage_bonus` | Flat addition to that roll |
| `essence`, `essence_strength` | Match the target's essence-response key and scale that response |
| `essences` | If present on the effective weapon data, the combat resolver selects the most damaging listed essence result, rather than adding them together |
| `crit_chance` | Added probability, expressed as a fraction; current shared resolver also adds a base 0.05 and a 0.15 bonus on head hits |
| Target `armour_value` / fighter `effective_av` | Flat mitigation before the location multiplier |
| Body/inline limb `size` | Relative probability of selecting that location |
| Body/inline limb `damage_multiplier` | Multiplies damage remaining after mitigation |
| Shield `block_chance`, `block_value` | Probability of a block and additional flat mitigation when it succeeds |

Use positive location sizes and sensible probabilities. The engine is not a general schema system that clamps every author mistake.

## Essence tuning

Current weapon/creature examples use case-sensitive names including `Dissolution`, `Binding`, `Severance`, `Quickening`, `Consumption`, and `Revelation`. Preserve the spelling used by both sides.

The scalar calculation is:

`net multiplier = 1 + (creature response − 1) × weapon strength`

Damage is then multiplied and truncated to an integer, with a minimum of zero. A creature response of `2.0` and weapon strength `0.6` gives `1.6×`, not `2.0×`. A response of `0.5` and strength `0.6` gives `0.7×`. A missing response is neutral (`1.0`). Strength zero contributes no essence change.

This is useful for deliberate counterplay: tune the creature response and the weapon's strength independently. A narrative essence note does not provide an extra effect by itself.

## Resolution order

The shared resolver checks dodge, chooses the hit location, rolls base damage, applies essence, checks a critical hit, checks a shield block, subtracts effective armour and block mitigation, applies location/damage scaling, and subtracts from HP. Current critical damage is `2.5×` before mitigation.

Normal player attacks and movesets share important combat inputs, including corruption bonuses and active coatings, through the engine. Do not read a single formula file as the entire attack: the caller prepares effective weapon data and handles post-contact effects.

For balance, compare more than maximum damage. A flat armour increase can erase many small rolls. Extra dice narrow relative variance; a larger single die widens it. High weakness multipliers and criticals occur before armour, so a modest weapon edit can have very different effects against armoured and unarmoured enemies.

## Weapon moves on Q and R

Each weapon's `movesets` array contains entries with `id`, `name`, `key`, `cooldown`, `range`, `turn_cost`, `damage_mult`, and optional `effects`/gates. Use one action per key. The first matching key entry wins, and cooldowns are keyed by action ID.

To strengthen Severing Cut, change its existing `damage_mult` from `1.2` to `1.3`. The move applies this multiplier to the rolled dice component before the flat bonus. Reducing `cooldown` from `10` to `8` allows more frequent attempts. Keep `range: 1` for the supported melee workflow; increasing it does not create a complete ranged targeting system.

`hp_gate` is an HP fraction ceiling: `0.5` means the action is blocked while the player is above half HP. `positioning: "behind"` uses the target AI's tracked target coordinates as a check, not a full visible facing/stealth simulation. Use ordinary `turn_cost: 1.0` if precise fractional-action timing is not the subject of your change.

### Supported effect boundaries

| Entry in `effects` | Current interpretation |
|---|---|
| `ignore_armour` | Bypasses armour for the move |
| `ignore_dodge` | Bypasses the dodge roll |
| `reduce_av` | Reduces the target's effective armour |
| `destroy_armour` | Subtracts two effective armour points; it does not remove a distinct armour-layer object |
| `suppress_ability_turns` | Existing actor ability-suppression counter |
| `reveal_knowledge` | Existing creature-knowledge revelation |
| `aoe_disrupt_range`, `aoe_disrupt_turns` | Existing nearby same-type disruption route |
| `screen_shake` | Presentation feedback |
| `place_pool` | Places the referenced decor on a kill |
| `pool_turns` | Read into the result, but not used to expire the placed pool |
| `free_move_on_kill` | Sets a pending flag; current movement does not consume it to grant a free move |
| `ignore_armour_layers` | Present in a shipped action but not consumed by the current moveset executor |
| `on_kill_only` | Not a universal condition wrapping all effects; only specific engine branches enforce a kill condition |

The final four rows are authoring boundaries, not recommended working features. Adjusting those declarations cannot implement the missing behavior.

## Body definitions and armour

The factory's inline `limbs` list takes precedence for creatures when nonempty. Otherwise combat uses the fighter's `body_id` in the loaded bodies registry. At least one valid location must exist; a missing usable body prevents the resolver from selecting a hit location.

For player armour, the recompute path sums current definitions of equipped items whose `category` is `armor`, using `armor_layers[].armor_value`. Temporary seals and the current Attuned bonus are added through their implemented routes. Avoid teaching historical limb HP, impairment thresholds, or per-location coverage as active current simulation.

## Verify a combat edit

First parse the changed JSON and check every referenced ID. For tuning an existing weapon, obtain/equip it and inspect ordinary attacks as well as its Q/R actions. Check a neutral target and a target with a relevant resistance. Use fresh creatures when evaluating changed `base_hp` or natural armour, since saved actors restore their previous values.

The focused suite includes `test_combat_routes.py` and effect/persistence coverage. Use the standard focused regression command after behavior changes, and add a bounded test for any newly implemented effect. Confirm the actual HP change and charge/cooldown counters; an exciting combat message is not proof that the intended effect occurred.

## Source bindings

- [Combat resolver and essence formula](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/combat.py)
- [Moveset declaration consumer](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/movesets.py)
- [Attack callers and post-hit effects](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/engine.py)
- [Single-pool fighter](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/components/fighter.py)
- [Working weapon definition](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/data/items/weapons/severance_blade.json)
