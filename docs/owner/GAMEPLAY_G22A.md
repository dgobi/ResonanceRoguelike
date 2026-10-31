# G22A — Complete the connected return

**The bounded G22A implementation and verification are complete.** The fresh
living return, cold audit and required unfiltered suites pass. Broader H1/arc
outcome review remains a separate judgment.

G22A continues the partial G22 delivery at
`277c2c98cb61d7e97756224a12080a97b3a03628`, directly on production `main`.
The unrelated untracked Workbench proposal and personal campaigns are preserved.
The start checkpoint is `checkpoint/gameplay-g22a-start-20261031-a`.

The implementation changes the bounded test player, not game balance or runtime
rules. It uses real vessels, reachable surface-water interactions, finite torch
fuel, legal defensive combat, actual fallen fuel and ordinary animal
butchery/cooking. No resources, actors, injuries, targets or needs are staged.
The existing empty-vessel description, inventory controls, generic adjacent
interaction and Ward-store note proved adequate for these actions; no product
interface correction was necessary. The affected start guide now describes the
exact refill and equipment controls. No wiki or Workbench expansion is included.

## Scenario and corrections

The [predeclared policy](../../evidence/gameplay-g22a/declaration.json) fixes world
seed 20261023 and gameplay bootstrap seed 20261020. The physical sheet, read
through ordinary input, supplies both destinations. Navigation sees explored
terrain and currently visible actors/objects. It cannot read unseen water,
container contents, actors or authored room coordinates. The local scouting aim
is a directional heuristic informed by the note, not an entrance/reward lookup.

The [old trace comparison](../../evidence/gameplay-g22a/trace-comparison.json)
establishes the first different action at turn 1782 from `(38,22)`: northeast in
development journey-e, southeast in final-b. The former pickup completes at 1793
with a visible keeper at `(47,17)`; the latter completes at 1797 with no observed
actor. Per-action actor/FOV state at the split was not retained. The cause of the
divergence is unproven; cold continuation does not promise identical future AI.
The invalid successful-time tuple is replaced with live campaign/report,
destination, exact preparation ownership and observed contacting-keeper checks.

The preferred mistake is one premature Ward equipment action beside an actually
observed contacting keeper. When that premise is absent, pickup and withdrawal
continue without waiting or seeking an invisible actor. The one declared
contingency is a natural surface pursuit catching continued travel during the
same second outing. Actual injury, the causal action, observation and damage
messages precede treatment. A keeper-free pickup cannot count as that mistake.

Logistics are reconsidered during local walking/searching, not only at coarse
boundaries. Both filled drinking forms are used; owned empty vessels are filled
at observed/remembered nearby reachable shallows before long exposure, retaining
weight and action costs. Darkness calls for usable carried light. After Ward
acquisition a nearby observed threat can justify protection in the same offhand.
Observed contacting enemies permit ordinary defensive strikes; a nearby diving
crow permits closing to contact instead of repeatedly walking under its attacks.

One bounded food contingency carries two bundles from nearby observed fallen
fuel and cooks up to three actual portions from a naturally defeated visible
stalker/crow. It introduces no third required destination. The single finite
workshop dressing and musk, needs rates, native population, Ward/keeper stats,
report selection/range, old variants and save contracts remain unchanged.

## Development evidence and limits

[Development-a](../../evidence/gameplay-g22a/development-a/connected/result.json)
failed at turn 2390. It demonstrates working early refill, reusable-skin drinking
and night lighting, but retained the musk because a new driver input defect
queried `valid_throw` before opening the real throw cursor. Crow attacks preceded
starvation at the configured maximum hunger; its final thirst was only 0.24375.
The failure is retained and is not a successful continuation or universal balance
finding. This was uncommitted development source, not final-source certification.

The next attempt corrects that demonstrable cursor-order defect, handles nearby
diving crows and uses the existing food opportunity. Seeds were unchanged; no
pre-death reload or encounter reroll was used. Its first return is turn 1136 / HP57,
Ward acquisition turn 1816, actual surface injury turn 1877 / HP55, finite musk
turn 1878, repositioning then one dressing at turn 1882 / HP60, and laboratory
return turn 2384 / HP37. Treatment restores five HP after acquisition; it supports
the return rather than enabling the earlier pickup. Further defensive combat
costs HP. One stalker portion supplies 220 nutrition. Final hunger 0.9938 shows a
very narrow food margin, not comfortable expedition balance.

The development cold audit first compares the exact successful save snapshot,
then inspects its depleted selected crates and harvested animal. One assisted
store revisit uses debug relocation/entrance positioning only after successful
play, followed by the real descent handler with regeneration forbidden. This
assistance is persistence verification, not part of the ordinary survival witness.
Its initial overly broad stock assertion included unrelated same-square
containers; the audit was corrected to the exact two crates actually opened.
No unrelated stock was removed or reclassified as acquired supplies.

## Frozen acceptance and verification

Implementation freeze: `5a5b6f5d2ec09897d40063a81b1df36cd0f10f5f`, checkpoint
`checkpoint/gameplay-g22a-implementation-20261031-a`.
The [final witness](../../evidence/gameplay-g22a/final-a/play/connected/result.json)
begins fresh at turn 480 / HP60 and returns to the original laboratory at turn
2340 / HP58, in one process/campaign. The inherited initial F5/F9/read/drop check
precedes both outings; no pre-death resume, cold bootstrap or outcome reroll
occurs during play. Bootstrap choices match the declaration, but later AI/combat
is not promised to reproduce the development trace. All 11,267 original-loop
input assertions pass; repeated frames are reduced to counts and the decision
ledger in this task's receipt.

| Decision boundary | Measured result |
| --- | --- |
| First refill | Turn 997, remembered surface shallows; one paid phase, carried load 6.52→6.82 kg. |
| First laboratory return | Turn 1152, HP57, hunger 0.322, thirst 0.35025; one dressing, pellet, jerky, flask and filled skin retained. |
| Store entry / Ward pickup | Turns 1789 / 1820. Ordinary defensive keeper contact costs 14 HP before pickup; Ward genuinely acquired at HP43. No adjacent observed keeper at pickup, so the equipment-delay premise is rejected. |
| Declared surface contingency | At turn 1879 the observed Heath Stalker damages the defending character 43→42 HP after catching the continued travel commitment. This is an ordinary defensive strike in the resulting contact, not manufactured injury. |
| Finite response | Turn 1880: actual musk throw, observed stalker falters. Three ordinary repositioning phases follow. At 1884 the one owned dressing pays one phase and restores exactly 12 HP, 42→54. No damage occurs during that dose. |
| Further gain / food | Continued defense defeats the native stalker; ordinary level gain at 1899 supplies another four HP, 54→58. This is separate from treatment. Butchery and one two-bundle fire produce two real meat portions; each supplies 220 nutrition and is eaten normally. |
| Later vessel use | Filled skin consumed at 1956; both empty vessels refilled at 2066–2067, paying one phase each and adding 0.3 kg each. |
| Living return | Turn 2340, HP58, hunger 0.7301, thirst 0.4855, zero active needs movement penalty/direct drain; load 9.59/20 kg, two filled skins, real Ward, one burning torch with 519 phases left. Dressing and pellet absent. |

The dose therefore supports meaningful exit/return **after Ward acquisition**.
The first outing's finite gain materially changes the response; treatment's 12 HP
is distinct from the disruption/repositioning window and later four-HP level
gain. The unmodified starter torch really burns out and the finite spare is used.
No starvation damage occurs in this final witness. The different food yield and
combat trace from development-b underscore the limits of any single sample.

The [cold audit](../../evidence/gameplay-g22a/final-a/cold-audit.json) matches the
exact successful snapshot before assistance, including ownership, report owner
and learned identities, spent treatment/pellet and both vessels. Its two actually
opened workshop crates remain depleted (one dismantled). The harvested animal
remains absent while uncollected sinew/bones persist. The saved keeper/store
state and taken Ward survive the one assisted production-handler revisit with
regeneration forbidden. Assistance begins only after ordinary play is complete.

The [release receipt](../../evidence/gameplay-g22a/final-a/release.json) and
[frozen input bindings](../../evidence/gameplay-g22a/final-a/inputs.json) record the
current unfiltered focused and production-D suites, including production runner
negative controls, and the connected/cold processes. Inputs remain frozen for
those results; documentation-only delivery follows them.

| Final gate | Actual outcome |
| --- | --- |
| Unfiltered focused | 444/444, no skips; 1,657.418 seconds in unittest, 1,661.720 seconds for its process. Includes the five new semantic/ownership/observation/vessel/throw-order checks. |
| Unfiltered production-D | 3,704/3,704 checks, 159 workers, seven runner negative controls; 595.009 seconds. |
| Fresh connected ordinary-input witness | Passed; 190.530 seconds, same-process campaign, actual Ward return at turn 2340 / HP58. |
| Separate-process cold audit / assisted revisit | Passed; 2.254 seconds, exact successful snapshot and retained consequences. |
| Existing G18–G22 affected preflight | 110 tests passed in 14.520 seconds before the final full suites. |
| Workbench and other unchanged coverage | Retained only under the 2,881-input comparison described below; package hashes checked. No new package build claimed. |

Final concurrent wall time is **1,663.653 seconds**, not the sum of overlapping
process times. All 2,885 frozen inputs remain stable; 1,076 committed-source
bindings report exact or explicitly normalized CRLF/LF matches. The working
bytes of all 2,881 prior inputs except `tools/g22_journey.py` match the prior
boundary. The four additions are the new policy driver, release driver, focused
tests and declaration. No game-runtime or data input changes.

Unchanged Workbench worker/frontend/host/typecheck/clippy/package/native and
historical G14/G16/G19–G21/metadata results may be retained only with an exact
input comparison. No runtime/data/Workbench/package input changed. Those commands
do not execute either G22 journey driver or the new focused test; current journey
and full focused/production-D results replace the affected results. Retention
certifies the prior supported Windows scope and does not claim a new package
build. G22's original partial outcome remains honest.

## Publication boundary

The scoped implementation commit is the freeze above; the following delivery
commit contains documentation and evidence only. Required references are
`main`, `checkpoint/gameplay-g22a-start-20261031-a`,
`checkpoint/gameplay-g22a-implementation-20261031-a` and
`checkpoint/gameplay-g22a-complete-20261031-a`. The exact final commit and remote
readback are recorded after committing in `.baseline/g22a-publication.json` and
the delivery message, avoiding a self-referencing SHA inside this commit.
The [completion receipt](../../evidence/gameplay-g22a/completion.json) binds the
outcome and source-bound evidence. No further arc or balance work follows.

## Arc-exit evidence mapping

| Arc criterion | Evidence and boundary |
| --- | --- |
| Two connected ordinary outings | Established by G22A's fresh same-process lineage, actual first return and living Ward return to the original laboratory. |
| First gain changes second outing | One actual workshop musk response and paid dressing after natural injury; quantities and costs retained. |
| Materially different encounter approaches | Retained G20 flint/musk alternatives and G21 controlled comparisons; these are disclosed scripted/staged comparisons, not unaided play. |
| Multi-actor local interaction | Retained G21 native/rival/kill-credit and persistence evidence, with its declared assistance. |
| Learnable causes and consequences | G18 timing, G19 contact/concealment, G20 sound/musk, G22 real reports and normal information boundary; G22A ordinary vessel/light/food controls. |
| Recovery after plausible commitment | G22A predeclared surface contingency, real injury, finite disruption/repositioning and one paid owned dressing; Ward acquisition precedes this recovery. |
| Persistent consequences | Retained G18–G22 historical contracts plus G22A exact successful-lineage cold load, selected stock depletion, spent supplies, harvested animal and assisted saved-store revisit. |
| Second arrangement reuses rules | Retained G20 canonical room/workshop and G21 alternate geometry/authoring contracts; no new required destination. |

A successful scripted witness establishes feasibility under the disclosed policy.
It does not establish unaided discovery, all-seed balance, comfortable provisions
or enjoyment. Broader H1/arc outcome review is a separate owner judgment. G23,
H2, balance changes and further Workbench work are not commissioned here.
