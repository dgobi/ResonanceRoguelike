# Numbing venom: delivery, counterplay and authoring

AI-3 adds a registered `venom_strike_and_withdraw` recipe, version 3, through
`CompositeAI`. Fixed binding: `numbing_melee`, `numbing_venom`,
`accepted_application`, `defensive_melee`, `active_scene`. It reuses strike and
withdraw's finite retreat, hold, timed return, sight memory and genuine-change
rearm. It does **not** wait for confirmed paralysis and is not the patient hunter.
Version-1 strike and withdraw and version-2 observation-averse profiles keep
their defaults and saved shapes.

| Parameter | Default | Bounds | Meaning |
| --- | --- | --- | --- |
| `warning_phases` | 3 | 2–12 | Normal movement and attacks; numbness warns of impending restriction |
| `paralysis_phases` | 2 | 1–3 | Voluntary displacement denied; stationary actions remain legal |
| `recovery_phases` | 4 | 4–16 | Movement restored; fresh doses rejected |
| `retreat_distance` | 2 | 2–8 | Desired Chebyshev distance in tiles |
| `hold_opportunities` | 1 | 0–12 | Full ordinary hold opportunities |
| `withdrawal_budget` | 6 | 1–32 | Finite ordinary withdrawal opportunities |
| definition `pursuit_timeout` | 20 | 0–10000 | Charged phases since actual sight, inclusive deadline |

One legal melee attack resolves once. Only a hit with positive damage on a
surviving eligible recipient can accept a fresh dose. Miss/dodge, zero damage,
invincibility, death, unsupported recipient, innate immunity, active venom,
recovery and source suppression reject application while preserving the attack's
ordinary outcome. Suppression disables delivery; disruption retains its existing
action policy. Neither cures a victim. Only fresh acceptance during engagement
starts withdrawal intent; retreat begins at the next ordinary legal opportunity.
Cornered defensive bites cannot restart an exhausted withdrawal.

Recipients are the living player and ordinary non-special `WanderingAI` and
`CompositeAI` actors with fighter/perception. No name, anatomy, sprite or faction
implies immunity. Eligible creature controls expose `numbing_venom_trait`:
`susceptible` (absent default) or `immune`. This trait affects only this venom.
Recovery protection is separate. There is one active dose per victim; attempts
never stack, refresh, accelerate, replace provenance or extend protection.

## Clock and player response

A dose delivered during AI phase T remains warning 3 at end T. End T+1 and T+2
leave 2 and 1. End T+3 starts paralysis 2; next player input is restricted.
End T+4 leaves paralysis 1; end T+5 restores mobility with recovery 4. End T+6
through T+9 spends recovery and removes the record. A transition never also
spends its new stage. Each completed charged world phase ages once, independent
of actor speed, extra decisions, queries, panels, cancelled/free inputs and
rejected moves. Costly actions spend each legitimately charged phase.

Move or disengage during warning, spend a finite remedy, or fight/wait in place
through paralysis. There is no HP drain, mechanical slowing, attack prohibition
or full-action stun. Movement keys still allow legal bump attacks and door
interaction. Local steps, sprint, Press, chunk and stair travel cannot displace
a paralyzed player or manufacture movement credit. Rejected movement is free;
paid Wait remains available. Health shows warning, paralysis or recovery with
accurate guidance. Visible creature symptoms and withdrawal tells respect
visibility; hidden progression produces no omniscient narration.

`venom_treatment` (Numbing Venom Remedy) is the game-owned authoring seed.
`measured_venom_remedy` demonstrates its new-ID route. Ordinary inventory use of
`cure_numbing_venom` clears warning/paralysis at any HP, heals no HP, consumes one
actual owned unit and pays one phase. That phase is recovery's first: default
recovery 4 leaves 3. No impairment, existing recovery, dead recipient or stale
ownership rejects without item/time cost or protection refresh. Saved stack
counts spend one unit of the selected instance; grouped instances stay distinct.
Herbal Dressing, Bitter Herb and existing preparations keep their meanings.

## Owner workflow and examples

In Workbench, open **Heath Stalker**, Begin edit, Save as new variant, choose
composite AI then **Venom strike and withdraw**. Controls show fixed delivery,
effect and trigger, timing units/bounds and explicit/defaulted effective values.
Tune, Validate, inspect Diff, review/apply and reopen. Duplicate to change recipe;
same-ID edits tune within the current recipe. Protected specials cannot gain
this authority by deleting their abilities/effects/statuses. Unknown metadata,
exact source, undo/redo, stale reviews and dependency capture keep their rules.

The control-created `nettle_stalker` and `drowsing_stalker` share Heath Stalker's
body/art, HP 16, armour 2, damage 1d4+1, speed 1, retreat distance 3, hold 3,
withdrawal budget 6, and pursuit timeout 20. Warning 3 versus 6 is their mechanical
difference; both use paralysis 2 and recovery 4. This existing animal presentation
is not a finished insect anchor. No species-ID branch supplies their effect.

For items, open the remedy seed, Save as new variant, edit ordinary fields,
Validate, review/apply and reopen. Use identity and unrelated fields are protected;
an HP treatment cannot be converted to a cure. No arbitrary executable effects
or separate effect catalogue is exposed. Save dependencies before placement.

The saved `ai3_nettle_opening` and `ai3_drowsing_opening` rooms provide a closed
ordinary door, retreat space, an escape path and a remedy at arrival for real
pickup/use. `ai3_rival_ground` adds a hostile ordinary Highland Bandit victim.
Open a room, **Test room**, **Reset current test**, **Stop**, or **Test latest
saved version**. Tests use immutable saved captures; dirty dependencies are
excluded. Definitions and rooms are explicitly available for placement/testing;
saving does not enroll natural populations or change starting inventories.

## Ownership, saves and diagnosis

The victim owns a version-1 optional `venom` component extension: nondefault
trait and/or a dose with validated effect/timing snapshot, stage, remaining
counter, unique application ID, source creature/individual/scene provenance and
applied/last-aged charged phase. Default neutral fields stay absent. Missing
older records clear stale memory and mean susceptible, even if today's
definition says immune. Fresh actors use today's trait. Saved immunity persists;
trait edits never cure an existing dose. Source instances retain their effective
composite profile, and accepted doses retain their own timing/recovery snapshot
even after source tuning, death, departure or disappearance. Owned remedies
retain their saved use binding.

Player travel continues aging. Active/live/pending owners age once under the
deduplicated effect lifecycle, including retirement before serialization. An
immobilized pending arrival waits at delay zero. Existing source-scene extraction
is bookkeeping; same-scene promotion preserves a legal recorded position without
an inward pursuit nudge. Collision repair keeps its existing semantics. Cached
creatures freeze and resume remaining counters, without away-time catch-up.
Death terminates the effect; remains do not acquire it. Paralysis waits consume
ordinary AI opportunities without charging spatial failures or replenishing
tactical budgets. Evidence expiry, real hold opportunities, geometry changes and
scene cancellation continue normally.

**Privileged live tactic inspection** is read-only, bounded and separate from
player knowledge. It includes delivery acceptance/rejection, effect parameters,
stage/clocks, application/source identity, susceptibility and movement denial.
It does not apply effects, rerun combat, age clocks or notify sources of hidden
treatment. See the [AI-3 delivery report](../../docs/owner/AI_3.md) for source-bound
evidence, final verification and publication identities.
