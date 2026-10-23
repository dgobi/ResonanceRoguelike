# B2 field and reconstruction contract — 23 October 2026

B2 starts at the owner-accepted B1 commit `9bb0db884b989bb9a21f25387b5772e3246ba978`
in the existing isolated copy. It repairs component replacement and derived
owners after load, without changing content, assets, controls or save locations.
The exact gate is documented in [B2_VERIFICATION.md](B2_VERIFICATION.md).

## Replacement order and concrete results

`SaveManager.load` validates the supported metadata, scene, inventory references
and new component records before applying their fields. It reconstructs the
player, actors, world and cold cache, then invokes `Engine._restore_loaded_state`.
That single entry configures Needs, replaces perk handlers, derives immediate
stat bonuses and map-dependent conditions, cancels old UI commands and recomputes
FOV. Bootstrap, direct API load and nondebug F9 share the same entry. F9 no longer
has its own extra Needs setup. No turn or general perk event is fired by loading.

At hunger 0.2 a fresh reader now says Sated, as the configured survival data
requires. Critical stages apply their movement penalties and HP drain on the
next real turn. Hardened Step modifies the next movement into mud. Marrow Drink
heals once on the next turn, never during load or three repeated loads. Attuned
armor and corruption bonuses are available immediately, without replaying other
turn effects. Removing saved perks clears their hooks and bonuses.

A saved 17-turn sight duration resumes at 17, then reaches 16 on the next turn.
An already used salve's remaining duration survives F5/F9 and a fresh reader and
expires on schedule. A distinct ration retains its own nutrition; a custom torch
retains its burn limit and consumes fuel against the restored equipped instance.
These are state/consumer guarantees, not certification of every effect's design.

## Development-v2 extension

`meta.json.save_version` remains exactly integer 2. The B1 scene and equipment
reference contracts remain in [B1_FORMAT.md](B1_FORMAT.md). No personal saves are
read, converted or migrated. B2 writes these additive fields:

* Player `component_state: {version: 1, engine: {...}, player: {...}}`.
* Each inventory row has `item_state_version: 1` and the explicit fields below.
  The fields are flat; there is no competing nested copy of item values.
* Each actor has `component_state: {version: 1, actor: {...}, ai: {...}}`;
  `ai` exists when the actor has AI.
* The corruption component adds `whisper_cooldown`.

A present extension must have integer version 1 and all its required fields.
Null/malformed blocks, future extension versions, booleans used as counts,
negative counts and non-finite numeric item fields fail with a field diagnostic.
Required reference rejection remains read-only and prevents bootstrap gameplay.
This is targeted validation, not arbitrary-corruption transactional recovery.

An older B1-v2 record without these extensions remains readable. Fields it never
stored use explicit defaults; they cannot inherit unsaved values from the current
session. Old item rows use current factory defaults for their omitted fields;
the existing B1 values still override them. Old null coating lists mean empty.
An old saved `true_sight` flag remains as recorded; no duration is invented for
it. Compatibility is tested with a checkpoint made by the actual B1 source in a
separate process. Loading never rewrites that checkpoint. Rolling back to an
older executable is not a guarantee that it understands new component fields.

## Field ledger

“Stored” means explicit instance state; “derived” means rebuilt from the saved
graph and current definitions; “reset” is deliberate session/presentation state.
The lists are whitelists, not object-dictionary dumps.

| Owner / fields | Policy and consumer |
|---|---|
| Scene identity, return stair, coordinates, turn | Existing B1 stored fields; routes and clock remain unchanged. |
| Player Fighter: HP, max HP, power, defense, body ID | Stored. Death flag derives from HP. Body descriptions/locations come from current definitions; the unused `body_limbs` list is not a separate health system. |
| Player effective AV | Derived from exact restored equipment plus Attuned's immediate bonus. The separate derived `attuned_av_bonus` survives an equipment AV recomputation, avoiding double-add or lost bonuses. |
| Needs: hunger, thirst | Stored; survival rates, normalized thresholds, penalties, drain interval and messages derive from `data.survival` on every load route. |
| Corruption component: value, whisper cooldown | Stored; stage/FOV properties derive. Engine corruption/exposure and threshold sets remain distinct existing saved owners; B2 does not merge their game design. |
| Perks: acquired set, per-perk state, affinity scores | Stored. Handler functions derive from definitions in sorted perk-ID order. Existing permanent system handlers are retained; perk handlers are replaced. |
| Attuned, Indifference, Corruption Channel | Immediate AV/damage bonuses derive from restored perks/exposure/thresholds/corruption. Derivation calls only stat handlers, not ON_TURN, acquisition, healing or resource decay. |
| Language: known words, translation events, taught texts, recovered spans/text, lexicon hint | Existing values stored and replaced, including empty state. Span keys use literal parsing rather than executable evaluation. |
| Level: level, EXP, next threshold, points, total levels | Existing values stored and replaced. Loading does not award levels, points or EXP. |
| Optional Needs/corruption/language/perks/level records | Missing or null means absent, clearing previous components. Empty valid language/level objects construct defaults; malformed required component fields fail. Fighter/inventory/equipment remain required. |
| Engine: true_sight_turns, player_speed_bonus, player_speed_bonus_turns | Stored. The existing turn consumer decrements and clears expired effects. Player `true_sight` remains its existing stored flag. |
| Player: chilled_turns, _sickness_turns | Stored; existing next-turn countdown and sickness Needs drain resume. |
| Engine: _move_debt, rain_collection_progress, _wraith_overcorrect_turns, wind_turn, _last_exposure_tier, _last_chunk_entry | Stored. Fractional movement debt, partial rain collection, FOV aftereffect, wind cadence and entry placement are not silently reset. |
| Player: _in_concealment, _wraith_warned | Stored gameplay/message state. |
| Sprint duration/cooldown, movement accumulator, moveset cooldowns, creature knowledge | Existing explicit fields retained. |
| Weather state/intensity/remaining duration | Existing stored fields; mechanics derive from current definitions. Missing/null weather creates a fresh configured system. RNG replay is not promised. |
| Item identity and ownership | `item_id` and B1 snapshot-row references remain authorities. Inventory coordinates derive from player location; equipped flags and light `_item_ref` derive from exact restored rows. |
| Item presentation | Stored `name`, `tile`, `text_id`, `description`, `eat_message`, `drink_message`, including empty/null values where supported. |
| Item quantities/properties | Stored `weight`, `stackable`, `count`, `on_use`, `nutrition`, `hydration`, `heal_amount`, `qualities`, `keywords`, `consumed_on_use`, `harvest_from`. Replacement preserves overweight bags; it is not an acquisition attempt. |
| Item fuel/liquid | Stored `burn_turns`, `turns_lit`, `light_data`, `liquid`, `liquid_volume`. Existing light radius/color/falloff/flicker/active fields remain separate saved component state. Runtime fuel references derive from the equipped item. |
| Item remains/coatings | Stored `decay_timer`, `source_creature`, `temporary_essence`, `_temp_av_bonus`, `_temp_av_hits`. Persisting these values does not add missing combat/crafting consumers. |
| Mutable item definition values | Each factory instance owns copies of `qualities`, `keywords` and `light_data`; changing one item cannot mutate another instance or its definition. |
| Actor Fighter/perception | Already-written max HP/power/defense and perception fields are now actually restored along with HP/body/AV, faction, hostility, sight/hearing/darkvision and wander radius. |
| Actor AI | Existing type derives from creature definition; existing state/home/pursuit timeout/accumulator retained. Target coordinates, memory and alert-memory duration are stored. No AI algorithm changes. |
| Actor runtime | Stored last-known player coordinates, arrival cooldown, just-arrived flag, pending stair action, sickness/chill and suppression/disruption counters. Stone-lurker fields keep their B1 authority. |
| Player warmth / hollow-knight proximity | Recomputed from the restored map/actors before input. FOV/light maps also recompute; explored map history remains persisted. |
| Wraith aura object-ID dictionary | Reset; it is message bookkeeping keyed to old object IDs. The independently meaningful overcorrection timer is stored. |
| Pending consume/throw/placement, held key, modal selection | Reset/cancel old commands and close screens so they cannot act on pre-load inventory objects. No turn, consumption or refund is replayed. |
| Particles, callouts, fog cache, projectile tween, discharge flash | Session/presentation caches reset or rebuilt. No exact visual animation phase persistence is promised. |
| World/map layers, floor objects, containers, vines, processing | Existing map pickle ownership retained. B2 does not redesign container item encoding or world checkpoint generations. |
| Offscreen processing | Tick the active map and each unique map in `SaveManager.cache.hot` and `submap_hot` once per actual turn. Include the surface paired with an active underground scene. Completed output is placed on its owning map immediately, without requiring a later surface-only delivery hook. |
| Cold maps and inactive dirty disk state | Not simulated/flushed by this repair. B3 retains coherent generations, dirty-cache persistence and interrupted-write recovery. |
| AI/global/render RNG progression | Not stored. Source-bound seeded fixtures verify scoped outcomes, not arbitrary whole-campaign replay. |

## Remaining boundaries

The four original B2 defects are repaired: B2-NEEDS, B2-HOOKS, B2-TIMER and
B2-OFFSCREEN-OWNER. The full regression gate still reproduces B3-GENERATIONS,
B3-DIRTY-HOT, C-DROP-EQUIPPED and UI-TEXT-HEIGHT independently on baseline and
candidate. See [B2_DEFERRED.md](B2_DEFERRED.md). Recommend B3 next.
