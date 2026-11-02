# Enemy response components (AI-8)

Duplicate an ordinary hostile melee creature in Workbench, select Composite and
an independent **Strike and withdraw** (v1) or **Fixed territorial post** (v5)
base recipe. Set an explicit non-`player` faction and explicit distinct
`hostile_to` including `player`. **Enemy response components** provides separate
**Call on hostile sight** and **Investigate allied alarm** checkboxes. Either,
both or neither is legal. Player/NPC, special-bound, ranged, escort and other
recipes cannot host them. The game supplies defaults and bounds. First attachment
requires a new ID; enrolled same-recipe variants may add/remove/tune modules for
fresh actors. Empty enrolled attachments permit later reattachment. Existing
actors retain their effective configuration. Review/apply/reopen exact source;
then place explicitly in a saved room. Invalid drafts remain repairable.

The definition attachment is separate from historical recipe schemas:

```json
"enemy_responses": {"version": 1, "modules": [
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

Only the two registered IDs/keys are executable; duplicate modules, coercions
and bool-as-integer values reject. Omitted parameters use game defaults.
An absent attachment leaves historical v1-v6 rows and behavior unchanged.

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
A/B/C with equal weights (one each), retaining 0.35 overall authored-barrow chance;
each has one third of that share. A/B definitions, existing assignments, visited
rooms and personal campaigns remain owned. Saving a creature enrolls it nowhere.
