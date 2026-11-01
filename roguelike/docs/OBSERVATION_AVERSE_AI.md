# Observation-averse pursuit (AI-2)

The game-owned `creature-composite-5` contract retains AI-1 and adds the embedded
version-2 `observation_averse` recipe. Begin an ordinary melee new-ID variant,
select **Creature AI: composite**, then **Behaviour recipe: Observation-averse
pursuit**. Recipe selection installs legal game defaults in one undoable Source
edit. Changing family/recipe requires a new ID; duplicate first. Same-ID tuning
keeps the recipe. Special/ranged/protected originals cannot gain authority by
removing fields. Exact source, metadata, stale-review and publication rules apply.

## Observation and prey

The fixed observer is normal direct player vision in the active local scene.
The pure query shared with normal FOV publication preserves transparency,
player position, time/underground radius, equipped/visible secondary lights,
weather and eligible wraith exposure. Explored memory, ghost positions, debug
reveal, overmap and inspection do not count. Queries neither publish visibility
nor advance clocks, identities, effects, messages or target evidence.

A narrow supernatural exposure sense knows being watched and useful shadow.
It can hide with no prey, including `hostile_to: []`. It never identifies the
watcher as prey or supplies hidden prey coordinates/timestamps. Ordinary sight,
hostility, stable instance/scene identity and finite sight evidence control prey.
Local rivals remain eligible. Hearing is an anonymous location/deadline and
cannot earn extra pursuit movement.

## Profile and clocks

| Setting/control | Default / bounds | Meaning |
| --- | --- | --- |
| `version`, `recipe` | 2, `observation_averse` | Separate discriminator; never reinterpret version 1. |
| `capability`, `observer` | `melee`, `normal_player_vision` | Fixed supported roles. |
| `exposure_response`, `concealment_policy` | `seek_concealment`, `reachable_unobserved` | Fixed; useful legal escape precedes melee. |
| Concealment opportunity budget | 8 / integer 1-32 | Ordinary opportunities pursuing cover, including blocked committed attempts. |
| Unseen extra movement step | 1 / integer 0 or 1 | One movement-only continuation per actor per charged phase. |
| No-cover response | `defensive_melee`; or `cower` | After useful escape fails: legal perceived hostile contact, or wait without attacking. |
| Pursuit opportunity budget | 32 / integer 1-64 | Finite approach patience, independent of sight timestamp refresh. |
| Definition `pursuit_timeout` | 20 if omitted / integer 0-10000 | Sight valid through last sight + timeout; expires next charged phase. |
| `scene_scope` | `active_scene` | Fixed; no off-scene pursuit. |

Unknown fields, recipe/version mixtures, unsupported roles, booleans as numbers
and out-of-range values reject through shared runtime/save/authoring validation.
Controls show fixed, defaulted, explicit and effective values without inventing
nonfunctional observer choices.

Search is bounded to 512 cells and 16 steps, with occupancy, furnishings, terrain
capability and contact geometry. It can start laterally or through exposed cells.
The selected cover destination persists until reached/invalidated/failure, even
if an intermediate cell is unseen. Reaching cover holds the rest of that charged
phase. No useful route resolves immediately to the authored fallback.

Own movement/visibility transitions and replanning never replenish cover patience.
An exposed pursuit entry is remembered among at most eight failed cells. The actor
routes around failed entries or settles. Eight failed entries, eight opportunities
without route progress, or the pursuit budget retire the approach. Sight refresh
at the same prey position cannot refill it. Stationary cover/cower is resolved.

Rearm requires changed exposure/terrain within the fixed 16-tile context around
the encounter, or a previously blocked cover route becoming legally usable.
The context stays independent of own movement; genuinely changed observed prey
identity/position reanchors it and rearms approach. Occupancy is rechecked for
route legality, never used to learn hidden prey coordinates. The rearm fingerprints
exclude clocks, target timestamps, explored bits, camera state and hidden prey.
Evidence still expires on charged phases with no slow/disrupted decision.

## Actions, interruptions and persistence

The existing speed accumulator grants zero, one or at most two ordinary decisions.
Only successful unseen pursuit movement can earn the optional adjacent step,
with the actor unseen both before/after the ordinary step. Cover movement, sound,
idle, attacks and rejected movement cannot earn it. The extra step grants no
attack, interaction or further decision. It can end at contact; melee waits for
a legitimate ordinary opportunity and its then-current observation policy.

Each committed step resolves the actual grass-concealment player attack and then
checks current observation, life, movement, disruption, suppression, prey and scene.
Exposure or a committed reaction interrupts the burst. Rejected contact is not a
successful reaction. At most one committed grass strike occurs per actor/phase;
these movers skip duplicate end-phase delivery. Legacy timing and player-only
terrain effects remain separate. Suppression disables the bonus; disruption skips
actions. Nothing banks deferred credit or enters the ordinary speed accumulator.

The complete effective profile and meaningful commitment persist, including
optional prey, cover, counters, failed entries and rearm state. Bonus/reaction/cover
phase markers persist so same-phase restore cannot mint an allowance. The two-step
action is synchronous, with no partial-burst queue. Routes/masks are recomputed.
Fresh actors use the latest saved definition; saved actors retain validated saved
tuning through F9 and cold load. Version-1 and ordinary save shapes keep their
meaning and receive no empty new fields.

Successful departure cancels local commitment and speed fraction before caching;
rejected departure does not. Revisit preserves physical identity, health/location
and recomputes observation. Stale transfer flags cannot admit either recipe to
chunk/stair/live-pursuer/pending-arrival paths.

## Saved examples and owner workflow

| Definition | No-cover response | Authored room |
| --- | --- | --- |
| Gloam Stalker (`gloam_stalker`) | Defensive melee | `ai2_shadow_opening`, `ai2_defensive_ground` |
| Gloam Shudder (`gloam_shudder`) | Cower | `ai2_cowering_ground` |

Both retain matched Hollow Revenant combat/art/body/perception, speed 1, extra
step 1, budgets 8/32 and sight timeout 12. `ai2_mixed_opening` adds an ordinary
Heath Stalker. These IDs support explicit placement and captured actual-game
testing only: no natural population enrollment or visited-scene regeneration.

Validate, inspect Diff, review/apply one file, and verify reopen. Save/reopen a
creature before selecting **Placement creature** in a room. **Test room** runs
the actual captured game. Reset retains capture; latest saved recaptures saved
inputs. Dirty dependency drafts stay excluded. Factory construction is separate
from gameplay evidence. Launch the portable package with `workbench/Launch
Workbench.vbs`.

The opening room provides a corner, an ordinary door and the standard starting
torch. Ordinary movement opens/controls the doorway or retreats around the corner;
inventory use/equip changes torch illumination. The matched ground rooms show
observed legal contact without useful escape. These are disclosed authoring
scenarios, not final balance or unaided-discovery certification.

The bounded privileged inspector shows current normal observation, sight
provenance/age/deadline, cover, counters/rearm, chosen action, actual step/reaction/
melee results and bonus eligibility/consumption. It grants no action. Normal play
gets a visibility-gated recoil/withdrawal tell without hidden positions/counters.

Sources: `engine/ai_profiles.py`, `components/composite_ai.py`,
`components/observation_averse.py`, `engine/engine.py`, `engine/ai_system.py`,
`engine/composite_diagnostics.py`, `engine/creature_authoring.py` and
`engine/save_manager.py`.
