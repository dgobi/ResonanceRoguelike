# G22A — Complete the connected return

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

## Frozen acceptance and verification

Final source-bound results and publication are recorded after the implementation
freeze. The release driver runs the required unfiltered focused and production-D
suites, including production runner negative controls, plus a fresh connected
original-loop campaign and separate-process cold-load/revisit audit. It checks
committed-blob bindings and unchanged source throughout.

Unchanged Workbench worker/frontend/host/typecheck/clippy/package/native and
historical G14/G16/G19–G21/metadata results may be retained only with an exact
input comparison. No runtime/data/Workbench/package input changed. Those commands
do not execute either G22 journey driver or the new focused test; current journey
and full focused/production-D results replace the affected results. Retention
certifies the prior supported Windows scope and does not claim a new package
build. G22's original partial outcome remains honest.

## Arc-exit evidence mapping

| Arc criterion | Evidence and boundary |
| --- | --- |
| Two connected ordinary outings | New G22A fresh lineage; final acceptance receipt determines established status. |
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
