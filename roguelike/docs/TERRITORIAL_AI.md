# Fixed territorial posts (AI-6)

`territorial_guard` is registered version 5 of CompositeAI. It supports ordinary
melee hosts with **Direct melee** or the existing **Strike and withdraw**
engagement. It adds no attack permission, speed, venom or allied commands.
Versions 1-4 retain their existing schema and effective saved meanings.

In Workbench, duplicate an eligible ordinary creature such as Hollow Revenant,
choose Composite and **Fixed territorial post**, then **Territorial engagement**.
Validate, review/apply one file, and reopen it. Changing recipe requires a new ID;
engagement and supported tuning within this recipe can change on the same ID.
Protected art/body and unknown metadata remain preserved. Saved actors retain
their effective profile; tuning changes fresh instances.

The post is the actual original scene placement: saved home coordinates and
owning scene token. It is never an item or moving actor. Removing the Ward gives
no notification and never ends the objective. Construction previews do not bind
a scene. Returning, loading, blockage and target changes never rebase the post.
`wander_radius` remains stored, explicitly inactive for this recipe.

| Control | Meaning |
| --- | --- |
| Defended radius | Chebyshev tiles from post; integer 1-7, default 4. Only currently seen, living, hostile, supported local intruders inside it may start engagement. |
| Maximum excursion radius | Integer 2-8, default 6, strictly greater than defended radius. Every pursuit, retreat and sound route step stays inside it. |
| Pursuit timeout | Charged phases since actual sight, valid through the deadline; independent of spatial limits. Example tuning: 12. |
| Pursuit opportunity budget | Integer 1-64, default 32. Every granted engagement opportunity spends one, including melee, hold and failure. Attacks/transitions never refill it. |
| Withdrawal | Shared trigger (hit or committed attack), distance 2-8 and no greater than outer radius, full hold 0-12, withdrawal budget 1-32. Direct melee requires canonical inactive defaults (hit/2/1/6); selecting it restores them in one undoable edit. |

Radius is no sense. Ordinary creature sight, hostility, deterministic local
selection and last-seen evidence apply, including ordinary nonplayer rivals.
Debug reveal, hearing and hidden live coordinates never supply prey position.
Actual sight beyond the outer radius, expired evidence, invalid prey, exhausted
pursuit or eight approach opportunities without progress retire engagement and
commit to return. Both engagements use the same legal resolver and executor.
Every movement commit rechecks occupancy, decor, terrain and sealed diagonals.

Return prefers the original tile. An occupied/unreachable tile permits a
reachable legal fallback within one Chebyshev tile, retaining the original post.
Return allows 32 route opportunities and eight consecutive failures, then waits
12 ordinary opportunities between retries. Changed bounded local terrain, decor
or occupancy permits earlier retry. A fallback holds until conditions change.
There is no teleport, healing, resource restoration or wandering. External
displacement permits bounded legal recovery steps that do not increase distance
while outside, then ordinary domain containment. Foreign scenes permit no action.

Current seen adjacent hostiles can receive ordinary contact defence during
return, including just outside the boundary if ordinary reach allows it.
Defence alternates with return attempts, granting no pursuit, retreat cycle or
budget refill. Ignored sounds never queue behind return. After arrival, unchanged
failed intrusions remain retired: fresh sight after loss, changed observed
position or changed local route conditions permit another attempt. Home alone
does not rearm an unchanged unreachable target. Retirement retains at most 16
local references.

An idle guard may investigate anonymous sound inside the defended region for
eight opportunities, through the same domain-aware route, then return on arrival,
expiry or exhaustion. Pulses never refill that budget. Outside sounds are
discarded; sight engagement outranks sound. Hearing never authorizes an attack
against an unidentified maker. Other recipes keep their established sound rules.

Full paralysis permits evidence expiry but prevents physical action and tactical
spending. The scheduler still grants at most two ordinary opportunities; this
objective adds none. UI inspection and F5/F9 do not advance time. Saves retain
effective tuning, anchor/scene, objective/engagement phase, lawful evidence,
budgets, retirement and return/blockage commitment, with strict validation.
Routes and diagnostics are recomputed. Successful departure cancels local prey,
sound and movement credit while retaining position, damage, home and profile.
Revisit resolves a physical return; cold scenes do not simulate it. Failed
departure preserves commitment.

`barrow_sentinel` and `barrow_watcher` use matched Hollow Revenant body/art,
combat, perception, speed, radii and clocks; engagement changes their decisions.
Open `ai6_sentinel_post` or `ai6_watcher_post`, then **Test room**. Step east into
the defended region, then wait to compare ordinary melee with a qualifying hit
and actual withdrawal. Save Sentinel defended radius 3 for a small iteration:
that first step no longer acquires it. Reset preserves the previous capture;
Test latest saved version uses saved dependencies and excludes dirty drafts.
Restore radius 4 for the matched pair.

`barrow_ward_store_b` places the Sentinel at source (17,5), covering the existing
Ward (20,4) and eastern passage. The western passage offers a different approach.
Only this variant joins the preserved old store in fresh-world selection, with
equal weights and unchanged 0.35 overall authored-barrow chance. Native entrance
construction, Workbench's controlled foyer and local play are distinct claims.
Old selections, visited rooms, dead guards, taken Wards and frozen reports stay
owned. Ward-store reports recognize both legitimate layout IDs and continue to
disclose unknown current contents, inhabitants and safety.

Privileged room diagnostics expose original home, objective/engagement phase,
lawful evidence, counters, retirement/return reason, fallback and actual action.
Inspection never selects an action. Normal logs use short sensory movement cues
after movement under normal player vision.
