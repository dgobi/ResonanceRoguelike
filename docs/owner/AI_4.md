# AI-4: patient venom hunter

Runtime/content/editor boundary: `fbe1f037bc5f7d82eac38d5c18886dadfb12176a`.
Starting production `main`: `74675c649a1a6f0e36169e2ce35ffcfadea68354`.
The implementation, input checkpoints and final verification use this same
boundary. Subsequent delivery changes contain documentation/evidence only.
The owner's untracked Workbench proposal, campaigns, wiki and reference pack
were preserved. No task branch, worktree or development copy was created.

The [authoritative patient-hunt guide](../../roguelike/docs/PATIENT_VENOM_AI.md)
defines the supported contract and owner workflow. This completes Stage C for
active-scene, explicitly placed encounters, and stops at AI-4. It does not claim
the complete AI arc or reinstate G23.

## Delivered behaviour and owner workflow

Creature contract `creature-composite-7` adds version-4 `patient_venom_hunt`.
**Observed paralysis** and **After finite hold** compose the same registered
`numbing_melee` delivery and shared withdrawal/movement authority. Combat is
resolved once; accepted application remains distinct from commitment, hit,
damage and death. No species-ID brain or copied venom implementation was added.
The narrow shared route/commitment repair now respects authoritative blocking
decor for v1/v3/v4 as well as v2, including a blocker introduced after planning.

Open **Amber Sting Beetle**, Begin edit, Save as new variant, select composite
AI then **Patient venom hunt**. Choose **Re-engagement policy**, tune supported
settings, Validate draft, inspect Diff, review/apply and reopen. Recipe changes
require a new ID; same-ID tuning stays inside the selected recipe. Observed mode
marks the stored hold inactive and disables its control. The card shows fixed
delivery/trigger/effect, direct-sight policy, waiting/defensive fallback, finite
budgets, derived original window and separate sight timeout. Body/art, protected
source authority, unknown metadata, history and stale-review rules are retained.

Actual packaged controls created, configured, reviewed, published and reopened
`patient_amber_hunter` and `timed_amber_hunter` from the ordinary insect seed.
They share static insect art/glyph, head/thorax/abdomen and six targetable legs,
HP 16, armour 2, damage 1d4+1, speed 1, sight 12, venom 3/2/4, retreat 2,
withdrawal budget 6, stored hold 3 and sight timeout 20. Only policy and
identity/prose differ. Existing limb, damage/death and source-identified floor
remains consumers work; ordinary floor corpses retain their generic presentation.
No anatomy editor, special limb mechanic or harvesting chain was added.

The three control-published rooms are `ai4_patient_opening`,
`ai4_timed_opening` and `ai4_rival_ground`. The matched opening rooms supply an
openable door, a wall/corner for escape, monitoring space and an accessible
existing remedy for real pickup. The ground room includes ordinary Highland
Bandit prey. Open a saved room and use Test room, Reset current test, Stop or
Test latest saved version. Reset retains its capture; latest saved excludes
dirty dependency drafts. Saving definitions/rooms enrolls no natural population
and changes no starting inventory.

## Information, clocks and persistence

Only an own accepted fresh application binds the selected prey. Its ordinary
sight memory stays separate from the saved hunt: source/application provenance,
known delivery phase, immutable expected window and finite tactical phase/state.
A nearer intruder cannot replace live prey or renew the budget. Defensive contact
can deliver an ordinary dose but cannot bind/restart the exhausted hunt.

Patient mode freshly establishes actual hunter sight of that particular prey
before querying the narrow paralysis cue, and before every predatory close or
attack. Terrain, ambient light/darkvision, concealment, hostility and owning
scene apply. Player FOV/debug reveal, sound, voluntary waiting and unrelated
movement denial are not symptom evidence. Hidden treatment gives no immediate
notification. At/after expected onset, a visible missing symptom resolves as
**expected impairment absent**; unseen prey supplies unavailable evidence.
Another source's paralysis on the same prey may satisfy a still-live prediction
without hidden UUID attribution, but cannot extend or revive it.

For sting T, first expected AI observation is T+W+1 and final useful ordinary
action is T+W+P, inclusive. At the initial W=3/P=2/speed=1/distance=2, the real
baseline stings at 484 (3 damage), retreats at 485, monitors at 486/487, observes
paralysis and closes at 488, then attempts melee for 3 damage at 489 while
paralysis still applies. End 489 starts recovery. At 490 the original window
resolves. No extra action, prolonged condition or backdated observation is used.
Other valid tunings/geometry/speeds may legitimately miss that opportunity.

Patient expiry is immutable despite repeated sight, diagnostics, replanning,
source suppression/disruption or another dose. Reacquisition uses last-seen
coordinates, bounded alternate viewpoints outside contact where practical,
32 existing approach opportunities and at most eight failures without progress.
Withdrawal uses its finite budget; genuine movement denial waits without
spatial-budget loss. Cornered legal seen contact permits defensive melee.
After abandonment the same visible encounter stays suppressed; genuine loss
of contact followed by a new encounter rearms it. It can still retreat or defend.
Timed mode has no symptom gate or patient-window expiry: full finite hold,
bounded return and resolution after the committed return attempt.

F5/F9 and three separate-process cold comparisons preserve meaningful monitor,
reacquisition and confirmed/approached commitments plus independent victim
state, without aging, redosing or restarting. Symptom observations and routes
are transient; the next decision revalidates. Focused continuation checks reject
stale cured authorization. Saved sources keep their effective profile; fresh
actors use newly saved tuning. Malformed/inconsistent new records reject safely.
Missing/dead/foreign-scene prey resolves; missing/dead/departed sources do not
cure victims. Successful departure cancels only local intent through the existing
active-scene route; no live pursuit, teleport or off-scene simulation was added.

The bounded privileged inspector separates victim truth from retained source
prediction and last permitted observation, including its age, selected policy,
actual action result and expiry/fallback. Inspection does not refresh sight,
age effects, apply venom or execute combat. Ordinary cues use normal vision.
Existing v1/v2/v3 profiles, saves, examples, immunity/no-refresh, item ownership,
single-use treatment, movement restrictions and effect aging retain their rules.

## Executed evidence and verification

All results below were executed in this task on the supported Windows x64,
CPython 3.11 pinned runtime, Node 24 and Rust environment recorded in
[environment.json](../../evidence/ai-4/environment.json). No historical pass
count is substituted for fresh certification. Exact commands, input hashes and
compressed receipts/logs are in [evidence/ai-4](../../evidence/ai-4/gates.json).

| Gate | Result |
| --- | --- |
| Unfiltered focused | 523 passed; source stable |
| Unfiltered production-D | 3,704 passed across 159 workers; source stable |
| Complete affected Workbench worker | 45 cases across ten affected modules |
| Frontend / host / startup | 93 / 71 / 15 passed |
| Typecheck / clippy / portable and debug builds | Passed |
| Desktop / final native lifecycle | Passed |
| Ordinary-input response family / independent cold comparisons | 6 / 3 passed |

The saved-room driver uses room seed 20261027, combat RNG 17 and AI RNG 19,
normal loadout/damage/AI/visibility and ordinary handlers. It injects neither
conditions nor owned remedies. Real pickup/use during hidden warning preserves
the original commitment through its charged phase for both policies. On later
sight, the patient withholds predatory return while the timed hunter returns by
its hold rule. A wall/corner escape prevents exploitation without treatment;
treatment after the patient closes prevents its stale attack. The ordinary rival
witness retains nonplayer identity during the live original commitment.
These are scripted bounded rules, not unaided discovery, full replay or balance.
Controlled attack results appear only in separately disclosed focused fixtures.

Actual-control creation receipts are development evidence; all five final saved
files match their publication hashes. The frozen final authoring/reopen and
native lifecycle use the rebuilt final executable. A legitimate native return
miss is accepted as a real committed attempt; the reproducible ordinary-input
baseline separately establishes positive damage during paralysis.

Material development failures and repairs are retained in
[attempts.json](../../evidence/ai-4/attempts.json): premature empty-trail
abandonment, hold-cancellation fallthrough, overly strict native hit evidence,
parked/visible-control selection, changed-input capture rejection and one
intermediate worker response error. None is represented as a final gate pass.
The fresh final affected worker and both unfiltered core gates use frozen inputs.

Launch the usable portable Workbench with `workbench/Launch Workbench.vbs`.
Executable: `workbench/src-tauri/target/release/resonance-workbench.exe`.
SHA-256: `1ca1544ae2de74b72d18b14f7ef642db08934216019ded50876adccfb5e56527`.
[Package inputs/capture](../../evidence/ai-4/package.json) bind the tested bytes.
NSIS installation and clean-machine provisioning were not rerun. The normal-view
[final frame](../../evidence/ai-4/complete-hunt.png) verifies the insect rendering
and concise cues. Wiki/reference-pack upkeep was not performed.

## Checkpoints and publication

The implementation was pushed atomically with the four prerequisite annotated checkpoints. Remote readback verified `origin/main` at the runtime/input boundary and every tag object plus peeled revision. Exact objects and readback are in [publication.json](../../evidence/ai-4/publication.json).

| Named checkpoint | Peeled revision |
| --- | --- |
| `checkpoint/ai-4-final-inputs-20261101-a` | `fbe1f037bc5f7d82eac38d5c18886dadfb12176a` |
| `checkpoint/ai-4-implementation-20261101-a` | `fbe1f037bc5f7d82eac38d5c18886dadfb12176a` |
| `checkpoint/ai-4-start-20261101-a` | `74675c649a1a6f0e36169e2ce35ffcfadea68354` |
| `checkpoint/ai-4-verified-inputs-20261101-a` | `fbe1f037bc5f7d82eac38d5c18886dadfb12176a` |
| `checkpoint/ai-4-complete-20261101-a` | This documentation/evidence delivery commit |

The final documentation/evidence commit and completion checkpoint are then pushed and independently read back. Exact final main, all five tag objects and peeled revisions are retained in `.baseline/ai-4/final-publication.json` and the final handoff; a commit does not embed its own hash. The completion checkpoint identifies this delivery, whose consumer inputs remain those verified above.

AI-4 stops here. Allies, other effects, natural population integration and later recipes remain separate work.
