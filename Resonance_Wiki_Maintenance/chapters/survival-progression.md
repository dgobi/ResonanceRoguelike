# Survival, progression, resonance and weather

These systems mix data tuning with named Python behaviors. Use the specific controls below, and treat broader fictional descriptions as design context until a consumer implements them.

## Hunger and thirst: two unit systems

The active authoring configuration is `roguelike/data/survival.json`. It expresses a remaining reserve in points: hunger maximum `1000`, thirst maximum `800`, and a base loss of one point of each per turn. Lower remaining points are worse.

Internally, `Needs` stores fractions from `0.0` (satisfied) to `1.0` (critical). It converts each configured stage with:

`internal threshold = 1 − remaining-point threshold / maximum`

For example, the hunger “hungry” stage at `400` points with maximum `1000` begins at internal hunger `0.6`. This is why copying the old component reference's fallback stage table is misleading: the running configured game uses `survival.json` stages.

| Section | Current stages, expressed as remaining-point thresholds |
|---|---|
| Hunger | Peckish `700`; hungry `400`; starving `200`; collapsing `0` |
| Thirst | Dry `600`; thirsty `350`; parched `150`; desiccating `0` |

The stage object controls its displayed `id`, transition `message`, `move_penalty`, and `hp_drain`. `hp_drain_interval` is currently ten turns. `biome_modifiers` scales hunger/thirst rates by biome. The component also has fraction-based FOV penalties; changing the stage labels does not automatically move every hardcoded sensory threshold.

### Make ordinary travel less hungry

For a gentle global food-consumption change, reduce `hunger.tick_rate` from `1` to `0.8`, keeping `max` and stage thresholds unchanged. This preserves the reserve display and stage boundaries while changing the time to reach them. Verify the configured rate in a controlled context because biome modifiers and active perks can change the observed result.

To make one food more filling, edit that item's `nutrition` instead. Values at or below `1.0` are legacy fractions; values greater than `1.0` are converted using the configured maximum. With the current maximum, `0.35` and `350` restore the same fraction. A value of `1` means a full restoration, not one point.

Changing maxima also changes how point-based food and thresholds normalize. Tune one dimension at a time. A saved needs fraction is restored on load, while the current configuration is reapplied; changing the maximum can alter how the same saved fraction is presented/interpreted in points.

## Perks: definitions, hooks and direct checks

Perk files are automatically loaded from `roguelike/data/perks/`. A practical edit to an existing perk can change its `name`, description, display category or `cost`. Its mechanical effect is usually implemented by a named hook or an explicit `perks.has(...)` check in game code.

A hook-based declaration uses:

```json
"hooks": [
  {"event": "ON_TURN", "handler": "handle_attuned_turn"}
]
```

That fragment is an existing Attuned behavior, not a generic configurable armour effect. `Engine._register_player_perks` resolves event names through `HookEvent` and handler names through `HANDLER_MAP`. A new handler name requires Python implementation and registration. The function may also use the exact perk ID internally, so copying its hook to a new perk ID is not automatically a correct new ability.

Current event names include `ON_TURN`, `ON_DAMAGE_TAKEN`, `ON_DAMAGE_DEALT`, `ON_TILE_ENTERED`, `ON_ENTITY_KILLED`, `ON_ITEM_EQUIPPED`, `ON_STATUS_APPLIED`, `ON_CHUNK_ENTERED`, and `ON_CRITICAL_HIT`. An event existing in the enum does not prove every possible action fires it; inspect and test its call site for a new mechanic.

### Current purchase limitations

The perk screen's purchase path checks whether the perk is already owned and whether enough points are available. The existing `requires`, `conflicts`, and old `unlock_conditions` declarations are **not enforced as purchase gates** in this revision. Some are displayed as text. Do not construct a progression tree by adding those fields and assume the game enforces it.

The screen iterates a fixed list of display categories. Use a currently displayed category when tuning an existing perk; creating an arbitrary new category is not a complete UI-registration path.

The old perk README's `effect_type`/`effect_params` schema is not a general effect interpreter. The Opened Page has a code check that enables exact HP inspection, but its declared damaged-span recovery parameters are not themselves executed by the hook registration mechanism. New effects require implementation and verification beyond changing the prose.

### Save/load considerations

Acquired perk IDs and per-perk state are saved. Hook handlers are rebuilt on successful load, and supported stateful bonuses have cleanup/reconstruction paths. When implementing or materially changing a perk, verify acquisition, action behavior, save/load and removal/re-registration without duplicate handlers or accumulating bonuses. Merely reopening the perk screen is not a test of those state boundaries.

## Experience and level growth

Current `LevelComponent` begins at level one, zero experience, threshold `100`, and one perk point. The threshold function is `int(100 * level ** 1.4)`. Kill experience comes from `system_exp_on_kill`, which compares the creature's `difficulty` tier with a level-derived player tier, applies a bounded multiplier to a base of 30, and signals a level-up through the engine.

An arbitrary `xp_value` in a creature JSON does not control that active formula. Tune the current consumer deliberately if experience progression is the goal; editing historical XP examples will not implement it.

## Resonance exposure and corruption

Exposure and corruption are distinct. The current resonance turn handler decays exposure by `0.008` away from a relevant source, scans nearby terrain/decor `resonance_emit`, and adds exposure based on source strength and proximity. At exposure of at least `0.70`, it adds corruption through the existing conversion. Several rates and scan distances are Python constants in `engine/resonance_system.py`.

For localized source tuning, inspect `resonance_emit` on the actual terrain/decor definition and confirm which scan or discharge path reads it. A new source ID with the field can contribute to the emitter scan; a new bell state or new ritual is not implemented merely by adding similar metadata.

The threshold system records named corruption milestones at `0.15`, `0.25`, `0.40`, `0.55`, `0.70`, and `0.85`. These names/messages do not all have equally complete mechanical consumers. Concrete current examples include revealing resonance data in inspection, bell-sense messaging on chunk entry, and the special tier-three word-learning route at `0.70`. Do not treat a threshold message alone as proof of a complete presence-sensing or creature-attitude system.

`components/corruption.py` also owns corruption labels, FOV penalties, passive zone rates and whispers. Its threshold comparisons and the separate milestone list are different mechanisms. Check the engine's synchronization of its corruption value and the player component when implementing changes; do not introduce a second independent source of truth through a tuning patch.

For preparations affecting these resources, use the implemented item handlers and fields in the items chapter. Already applied effects and saved counters are restored; use a new application for a changed default.

## Weather: what is data-driven

`roguelike/data/weather.json` defines presentation settings and a nested `mechanics` object for states. Examples of actively queried mechanics include fog FOV caps, bone-snow corruption per step, dead-calm bell range and resonance-storm discharge chance. These fields only affect systems that request them through `WeatherSystem.get_mechanic` or the relevant renderer.

Weather transitions, durations, supported state names and display labels live in `roguelike/engine/weather.py`. Adding a new top-level JSON entry alone does not make the weather state machine select it. The named `fog_wisps` entry is presentation data, not evidence of an independent weather state.

| Goal | Edit and verify |
|---|---|
| Reduce fog's vision penalty | Existing state's `mechanics.fov_cap`; verify active FOV |
| Reduce bone-snow corruption gain | `bone_snow.mechanics.corruption_per_step`; verify an actual movement step in that state |
| Change rain density or speed | Existing presentation fields; verify rendered rain at the intended screen size |
| Make rain more frequent or longer | Python transition/duration tables; this is a code change |
| Add an entirely new weather type | State machine, persistence validation/consumers and rendering integration as appropriate |

Weather ticking is suppressed underground by the current resonance turn handler. Some mechanical effects lack that same guard; see [Weather and atmosphere](#weather-and-atmosphere) for the precise underground limits. A loaded weather state restores its remaining duration and receives current mechanic definitions through reconstruction.

## Verification approach

For survival edits, test a configured `Needs` object and then an actual turn sequence under controlled biome/perk conditions. For perks and corruption, test state before and after the triggering event, not only the message. For weather presentation, add a visual inspection to the behavioral checks.

The repository's focused tests and full D gate cover established behavior; a newly introduced mechanic needs its own targeted cases. Avoid upgrading a declaration from “described” to “implemented” until the actual consumer and a corresponding verification route exist.

## Source bindings

- [Survival configuration](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/data/survival.json)
- [Configured needs and unit conversion](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/components/needs.py)
- [Perk purchase/display path](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/rendering/perk_screen.py)
- [Hook registration and merging](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/hooks.py)
- [Perk and experience handlers](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/perk_handlers.py)
- [Level component](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/components/level.py)
- [Resonance and milestone consumers](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/resonance_system.py)
- [Corruption component](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/components/corruption.py)
- [Weather state machine](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/weather.py)
