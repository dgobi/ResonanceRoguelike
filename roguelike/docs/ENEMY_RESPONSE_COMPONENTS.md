# Enemy components (AI-8 / AI-9)

Duplicate an ordinary hostile melee creature in Workbench and select Composite.
Choose any of the five hostile base recipes (v1–v5). Set an explicit non-`player` faction and explicit distinct
`hostile_to` including `player`. **Enemy response components** provides separate
**Call on hostile sight** and **Investigate allied alarm** checkboxes. Select
**Expanded v2** alarm compatibility for the five-family contract. **Enemy movement
components** independently provides **Seek lateral approach** and **Regroup when
wounded**. Any subset of the four components is supported under the phase table
below. Player/NPC, special-bound, ranged and escort hosts reject these attachments.
The game supplies defaults and bounds. First attachment
requires a new ID; enrolled same-recipe variants may add/remove/tune modules for
fresh actors. Empty enrolled attachments permit later reattachment. Existing
actors retain their effective configuration. Review/apply/reopen exact source;
then place explicitly in a saved room. Invalid drafts remain repairable.

The definition attachment is separate from historical recipe schemas:

```json
"enemy_responses": {"version": 2, "modules": [
  {"id": "alarm_call_on_sight", "cooldown_phases": 24,
   "rearm_unseen_phases": 12, "strength": 12},
  {"id": "investigate_allied_alarm", "expiry_phases": 16,
   "opportunity_budget": 12, "failure_budget": 2}
]}
```

| Field | Default | Inclusive bounds | Unit |
| --- | --- | --- | --- |
| cooldown_phases | 24 | 12-120 | charged phases |
| rearm_unseen_phases | 12 | 6-60 | continuous phases without own sight |
| strength | 12 | 6-18 | acoustic path cost at hearing 6 |
| expiry_phases | 16 | 4-32 | charged phases after emission |
| opportunity_budget | 12 | 1-24 | granted ordinary opportunities |
| failure_budget | 2 | 1-4 | consecutive failed route opportunities |

Only the registered response IDs/keys are executable; duplicate modules, coercions
and bool-as-integer values reject. Omitted parameters use game defaults.
An absent attachment leaves historical v1-v6 rows and behavior unchanged.
Response envelope v1 remains accepted only on v1/v5 with its original approach
and movement semantics. Existing actors are never upgraded to v2 by definition
tuning. The editor retains existing v1 unless deliberately changed; new opt-ins
default to v2. Base recipe versions have not changed.

Own current direct player sight during a permitted initial engagement spends
one action drawing upright with a trembling jaw. A later charged phase with
fresh sight and physical eligibility spends another action crying. Speed two
cannot complete during the preparation phase; its second wind-up opportunity
waits. Sight loss, disruption, ability suppression or full paralysis cancels the
tell. Neither paid choice moves or attacks. A completed call, heard or not,
marks the sight episode called and starts cooldown. Rearm requires cooldown
completion AND the continuous unseen interval. Sight flickers and received calls
do not rearm. Existing withdrawal/hold and territorial return, retirement and
pursuit budgets retain priority; calls spend the guard's pursuit budget too.

A typed incident carries only unique source/sequence ID, stable source identity,
source faction, scene, emission phase and actual call-site coordinates. Existing
sound propagation supplies cardinal paths, closed-door cost four and solid-wall
blocking. Positive individual hearing adjusts strength relative to hearing six;
the propagation cap stays 48. Delivery visits only active listeners. Only living
same-faction hostile response hosts accept it. The player hears an unidentified
cry when acoustic reach allows; normally visible callers give visible cues.
Ordinary combat/flint/musk/bell sounds remain anonymous and cannot become typed
incidents. No player target, coordinates or route is shared.

Receipt is information, never an action or target. It stores origin, receipt,
deadline, remaining opportunities/failures and dedup marker. Movement starts
strictly AFTER emission's charged phase regardless of iteration order. Own seen
threats and retained combat/withdrawal win. Idle guards accept only within the
defended domain and route inside their excursion. Calls cannot interrupt return
or reset pursuit. Reports outrank anonymous sound: receipt clears it, and new
anonymous pulses are ignored during response. Own target acquisition clears the
report and resumes the selected base recipe.

Each route uses the common transient 512-cell/16-step bounded search and rechecks
terrain, decor, occupancy, swimming capability and sealed diagonals. An occupied
or blocked origin uses a legal cardinal approach. Arrival, expiry, depleted
opportunities, failed route budget, new threat or scene/objective incompatibility
releases interest. A displaced idle guard commits to physical return. Receipt
cooldown is eight phases; an active report cannot be replaced or renewed. The
most recent 16 accepted IDs are saved. Receipt/arrival/sight of an ally never
relays a call. Both-module hosts still need own fresh player sight to call.
Source death does not revoke a heard report; its finite deadline remains.

Saved `composite.responses` holds exact effective `config` and separate `state`;
historical `composite.profile/state` keep exact schemas. Factory restoration
explicitly suppresses definition attachments for historical saved actors. Saved
alignment, provenance, owning actor/cache scene, counters and compatible base
intent validate before installation. Same-scene F5/F9/cold loads retain exact
preparation/cooldown/report counts. Departure clears local preparation/report
and movement accumulation, retaining called/cooldown/dedup history and guard
return. Revisit cannot replay reports. Inspection/render/save never advance time.

Test room's captured **Reset** and **Test latest saved version** retain existing
dependency policy; parked dirty drafts are excluded. Privileged live tactic
inspection adds effective components, state and 16 trace rows: sight, call ID,
origin, listener eligibility/reason, action, budget, priority and expiry. It reads
only and never supplies player knowledge.

| Creature | Base | Call | Investigate |
| --- | --- | --- | --- |
| barrow_alarm_sentinel | v5 direct melee | yes | no |
| barrow_alarm_skirmisher | v1 strike/withdraw | no | yes |
| barrow_alarm_runner | v1 strike/withdraw | yes | no |
| barrow_alarm_watch | v5 direct melee | yes | yes |

`ai8_alarm_crossing` and `ai8_alarm_reverse` are controlled Test rooms. A closed
door/wall attenuates sound and hides the player from the receiver; the southern
opening supplies a physical alternate route. `barrow_ward_store_c` uses crossing
actors with the existing Ward, note, empty crate and return stair. Its southern/
eastern passage permits avoiding the guarded western lane. Fresh worlds select
A/B/C/D/E with equal weights (one each), retaining 0.35 overall authored-barrow chance;
each has one fifth of that share. A/B/C definitions, existing assignments, visited
rooms and personal campaigns remain owned. Saving a creature enrolls it nowhere.

## AI-9 phase and action contract

Housekeeping always precedes selection: target expiry, patient observations and
retirement, and territorial bounds keep running. Physical paralysis denies every
voluntary physical choice. One selected branch consumes one ordinary opportunity;
there is no additional scheduler. A received alarm carries no prey identity and
cannot start investigation or wounded response in its emission phase.

| Host | Call / lateral window | Alarm investigation | Wounded regroup |
| --- | --- | --- | --- |
| v1 strike and withdraw | Own fresh sight during approach/return to prey | Idle without retained threat | After required withdrawal/hold; replaces ordinary advance |
| v2 observation-averse | Unseen lawful pursuit; call uses own player sight | Genuinely idle and unseen | Unseen; concealment and this-phase cover commitment win |
| v3 venom strike and withdraw | Own fresh sight before a legal strike | Idle without retained threat | Required post-hit withdrawal/hold wins |
| v4 patient venom hunt | Initial approach before a dose/hunt | Idle without retained or suppressed hunt | After withdrawal/required timed hold; retires the offensive hunt before installing regroup |
| v5 territorial guard | Engaged approach inside excursion | Guarding; reported origin inside defended radius | Engaged only; return/retirement wins; spends pursuit budget |

Regroup may interrupt an ordinary advance, lateral commitment, alarm preparation
or already eligible investigation. It clears the interrupted intention without
refilling credit. Otherwise a paid alarm tell/emission precedes lateral approach;
an already legal melee attack precedes lateral movement. Guard moves, calls and
holds all spend its existing pursuit budget. A zero budget forces return.

Every v2 attachment move uses the ordinary safe-step adapter, including grass
reaction and post-move exposure. It never appends the core pursuit's bonus step.
New exposure selects concealment for the next opportunity, without a second move;
exposing investigation drops its report. Reaching cover commits the rest of the
charged phase, including speed two. Core unseen pursuit retains its existing
movement-only advantage.

## Movement configuration and finite state

```json
"enemy_maneuvers": {"version": 1, "modules": [
  {"id": "seek_lateral_approach", "opportunity_budget": 8, "expiry_phases": 16},
  {"id": "regroup_when_wounded", "wounded_percent": 50, "rearm_percent": 75,
   "opportunity_budget": 6, "hold_opportunities": 2, "expiry_phases": 16}
]}
```

| Setting | Default | Inclusive bounds |
| --- | --- | --- |
| Lateral ordinary opportunities | 8 | 2–12 |
| Lateral charged-phase expiry | 16 | 4–32 |
| Wounded HP threshold (percent, inclusive) | 50 | 10–70 |
| Recovery rearm HP threshold (percent, strictly above) | 75 | 50–95; must exceed wound threshold |
| Regroup travel opportunities | 6 | 2–12 |
| Regroup hold opportunities | 2 | 0–3 |
| Regroup charged-phase expiry | 16 | 4–32 |

Support must be a living, active same-scene actor with the same explicit faction
and no mutual hostility, visible through the maneuvering actor's own terrain,
light and darkvision rules. Only its physical position is used: no ally targets,
injuries, orders, effects or inventory. Fixed goals release immediately when the
supporter moves, disappears, dies or becomes incompatible. Hidden live positions
never update a goal. Two wounded actors cannot perpetually chase one another.

Lateral approach requires fresh prey sight and useful visible support nearer the
direct approach side. Four off-axis adjacent candidates use stable individual
identity for side preference and current occupancy for conflict resolution.
Routes avoid premature contact on the direct side, while an actual already-legal
attack still wins. Each route uses the existing 512-cell/16-step search, with final
terrain/decor/corner/occupancy revalidation. A real one-tile corridor declines.
No facing, backstab damage, extra reach, teleport or movement multiplier exists.

Regroup uses the actor's own actual HP and a reachable cardinal-adjacent support
goal. Arrival permits the bounded hold. There is no healing, cure, free defence,
buff or reinforcement. Patient retirement preserves same-prey suppression and
does not alter victim-owned venom, source or expiry. It cannot resume the old hunt.

Each maneuver gets one attempt per continuous encounter. A failed useful-route
search spends that attempt; absent support alone does not. Rearm needs **24
consecutive active charged phases** genuinely idle without retained/seen threats
or report/commitment. Offscene time jumps do not count. Actual HP recovery above
the higher threshold may independently rearm regroup. Brief sight loss, new
support/prey, further damage, inspection, interruption and departure cannot reset
credit. Absolute expiry ages even during hard host phases, low speed, disruption
or paralysis; free inspection never advances it. A route invalidation yields to
the lawful core recipe, with spent credit retained.

Saved `composite.maneuvers` contains effective config and exact bounded state:
scene binding, stable support/prey references, observed positions/time, fixed
goal, charged deadline, travel/hold credit and rearm history. Routes are recomputed;
there are no saved path caches or shared claims. Invalid versions, types,
coordinates, foreign references, impossible goal geometry and contradictory state
reject before scene installation. Absent and explicitly empty attachments remain
different. F5/F9 and cold loads retain credit; departure clears goals and preserves
injury, credit, victim effects and original home. New definitions never retrofit
attachments onto historical saved instances.

## Authoring examples and normal availability

| Saved example | Base | Movement | Alarms |
| --- | --- | --- | --- |
| `barrow_lane_revenant` | v1 | lateral + regroup | call + investigate |
| `barrow_shy_stalker` | v2 | lateral | investigate |
| `barrow_nettle_guard` | v3 | regroup | call |
| `barrow_patient_weevil` | v4 observed-paralysis | lateral + regroup | investigate |
| `barrow_kin_sentinel` | v5 direct melee | regroup | call |
| `barrow_shy_listener` | v2, further recombination | regroup | investigate |

The sentinel example defends two tiles, leaving its support position stable until
an intruder approaches its post; the registered default is still four. All examples
reuse existing art and bodies. `ai9_lateral_lane`, `ai9_venom_lane` and
`ai9_shadow_lane` place the set in saved Test rooms. The editor flow is Duplicate →
select recipe/components/tuning → Validate → Review/apply → reopen → place through
the room's creature controls → save → **Test room**. Inspect actual instances in
**Privileged live tactic inspection** for host windows, yield reason, own sight
versus memory, support/goal, remaining credit and actual actions. This view is
read-only and never supplies ordinary player knowledge.

**Reset current test** retains the captured saved dependencies. **Test latest saved
version** deliberately captures the newly published version. Parked dirty drafts
are excluded. Module toggles and numerical edits support the existing undo/redo,
protected metadata, invalid-draft retention and exact no-op publication rules.
An enrolled same-recipe variant can tune future instances; changing the base recipe
or first opting a protected original into either attachment requires a new ID.

`barrow_ward_store_d` has an open lateral approach and a post/runner pair. Its
southern/eastern route offers a different encounter from challenging the group.
`barrow_ward_store_e` divides an observation-averse watcher from a patient shell
hunter with broken sight and a closed doorway. Light, route and separation matter;
Wait advances bounded paralysis when physical actions are unavailable. Both keep
an accessible return stair, the existing note/Ward and modest crate. Actual fresh
world seed **20261027** selects D at **(80,97)** and E at **(69,92)**. This is normal
selection, separate from Test room; witnesses stage the player at those genuine
entrances and do not establish unaided travel from the laboratory or universal
balance. Existing A/B/C assignments and visited scenes remain intact.
