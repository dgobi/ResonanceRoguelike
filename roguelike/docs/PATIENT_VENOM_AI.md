# Patient venom hunting

Creature contract `creature-composite-7` registers version-4
`patient_venom_hunt`. Its `return_policy` selects **Observed paralysis**
(`observed_paralysis`, default) or **After finite hold** (`after_hold`). Both use
the existing `numbing_melee` capability, accepted fresh application trigger,
victim-owned `numbing_venom`, shared legal withdrawal and ordinary melee.
The v1/v2/v3 recipes, saved shapes and examples keep their meaning.

Open **Amber Sting Beetle**, Begin edit, Save as new variant, select composite
AI and **Patient venom hunt**. Choose the re-engagement policy, tune supported
timings/distance/budgets, Validate draft, inspect Diff, review/apply and reopen.
Changing recipe requires a new ID. Same-ID policy/timing tuning stays within
v4; existing saved actors keep their effective profile. Body, art, source
authority and unknown metadata remain protected. Save dependencies before
placing a creature in a saved room. Undo/redo and stale-review rejection use
the existing exact-source workflow.

The two control-authored definitions `patient_amber_hunter` and
`timed_amber_hunter` have identical body/art, HP 16, armour 2, damage 1d4+1,
speed 1, sight 12, warning/paralysis/recovery 3/3/4, retreat distance 2,
withdrawal budget 6, stored hold 3 and sight timeout 20. Only the policy and
identity/prose differ. Hold is disabled and marked inactive in observed mode;
it is operative in timed mode, including holds longer than the impairment.
The ordinary seed has a head, thorax, abdomen and six independently targetable
legs using existing limb mechanics, a registered static insect tile/glyph and
ordinary source-identified corpse remains. No harvest chain or new limb mechanic
is supplied. Species corpse-sprite metadata follows existing definitions; normal
floor remains retain the current generic corpse presentation.

## Information, time and resolution

Only an accepted fresh application during engagement binds a hunt. The source
remembers that prey's actor/scene reference and last genuine sight separately
from its own application/source provenance and immutable timing prediction.
It never follows a live effect link. Miss, rejection and defensive contact cannot
fabricate or renew a commitment. Another nearer hostile cannot replace its prey.

For delivery during AI phase T, first expected observation is T+W+1 and the last
useful action is T+W+P, inclusive. With W=3/P=3, the next opportunity retreats
one step to distance 2; T+2/T+3 monitor; T+4 can observe paralysis and take one
normal approach step; T+5 and T+6 can attempt ordinary melee while full paralysis still
applies. End T+6 starts recovery; the next player decision permits action. AI acts before effect aging. No observation or transition grants an
action. Geometry, speed, darkness, treatment and prey movement can defeat this
sequence; other valid tunings do not guarantee an attack in time.

Observed mode requires fresh actual hunter sight of that particular retained
prey before each predatory move/attack. Terrain, ambient light/darkvision,
concealment, hostility and the active scene apply. Player FOV/debug reveal,
sound, voluntary waiting and unrelated movement blocks do not supply a symptom.
Only after sight succeeds does a pure query disclose the narrow paralysis cue;
hidden counters, application IDs and remedy inventory are unavailable.

Before onset, visible absence is normal. At/after the first expected opportunity,
visible absence resolves as **expected impairment absent**, never an inferred
hidden cure. No sight means unavailable evidence. Hidden treatment gives no
immediate notification. Visible paralysis on the same prey from another source
may satisfy the original live prediction, without UUID attribution; it cannot
extend, replace or revive the original commitment.

When hidden, the hunter seeks another viewpoint using only last-seen position,
preferably outside attack contact. Search spends the existing 32 approach
opportunities and stops at eight failures without progress; sight expiry and the
immutable useful window also bound it. Monitoring maintains distance where
possible. An intruder can force defensive positioning without becoming prey.
Blocked retreat spends the finite withdrawal budget; genuine movement denial
spends a wait without spatial failure or budget loss. Neither recovery,
replanning, cornered bites nor phase changes replenish budgets. Without a useful
retreat, actual legal seen contact permits defensive melee; otherwise wait or
abandon. These bites never count as the qualifying predatory return.

Expiry, failed expectation, invalid prey or exhausted positioning abandons the
commitment. The same visible encounter stays suppressed. Genuine loss of sight
followed by a later observed encounter rearms it; the creature remains capable
of defending itself while disengaged. Timed mode has no symptom gate or useful
window expiry: retreat, full configured hold, return through the existing finite
approach budget, then resolve after its committed return attempt. Both policies
retain lawful actions, prey identity, sight timeout and finite fallback.

Suppression disables further venom delivery only. Disruption pauses action
opportunities while effect aging and the immutable predicted deadline continue.
Source death/departure cannot cure the victim. Successful scene departure cancels
local hunt intent; failed travel does not. No cross-scene pursuit is added.

## Saved rooms, persistence and inspection

`ai4_patient_opening` and `ai4_timed_opening` offer matched approach/retreat space,
an ordinary openable door and wall to break sight, and a remedy at arrival for
real pickup. `ai4_rival_ground` adds an ordinary Highland Bandit prey. Open a room
and use Test room, Reset current test, Stop or Test latest saved version. Reset
keeps the capture; latest saved excludes dirty dependency drafts. These are
explicitly placed active-scene encounters; definitions/rooms enroll no natural
populations and add nothing to ordinary starting inventory.

Try waiting through onset; moving north behind the door wall during warning;
or picking up the remedy with comma and using it through inventory. Hidden
treatment followed by reappearance distinguishes the policies. Once full paralysis
begins, attacks and self-treatment are unavailable, including an already-open
inventory or pending confirmation. Treatment after the patient closes rejects
without item/time/effect changes. Use `.` or keypad 5 Wait for one phase at a time;
three such phases restore action in fresh stock. Free inspection does not age it.
The examples display as **Amber Shell Hunter** and **Amber Whine Beetle**; their
stable IDs and author-visible return policies remain unchanged. No combat/loadout
tuning beyond the commissioned P3 timing was needed for the real-damage anchor.

The separate version-1 hunt record saves own-delivery provenance and prediction
with the v4 tactical phase/counters. Exact validation rejects malformed shapes,
timing, identity and incompatible phases. Last symptom observations and paths
are transient. F5/F9 and cold same-scene loading preserve the commitment and the
independent victim snapshot without aging or another dose; the next decision
revalidates sight. Missing/dead/foreign prey resolves safely. Old P2 hunter profiles,
commitments/deadlines and victim counters are preserved; their severe stages now
fully paralyse. Fresh hunters use P3. Source paralysis pauses physical dispatch
without spending spatial budgets; perception/expiry and effect clocks continue.
A first successful retreat step emits the withdrawal cue; blocked retreat does not.
Return prose follows visible movement. Ordinary feedback describes sensations and
observable actions, while exact clocks and policy reasoning remain diagnostic.

The bounded privileged inspector exposes prey/scene, original application/source,
window, selected policy, latest permitted cue/reason and its age, action result
and fallback. Its latest-decision evidence is distinct from current authorization
and from privileged victim truth. Reading it never refreshes sight, ages clocks,
applies effects or runs combat. See [AI-4 delivery](../../docs/owner/AI_4.md) for
the source-bound verification and publication record.
