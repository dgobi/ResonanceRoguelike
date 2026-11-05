# AI-9 v2.0: enemy composition and encounter integration

The complete five-milestone package is delivered in production `main`.
Runtime, content and editor revision is
`732b9430aa07b550d84f88ec83ec46a5ac939a57`. Final verification-input revision is
`2d6bc172054ee1f8832d3cdfff948aa3135defac`; its sole consumed-input delta adds
the five commissioned layout IDs to one exact worker catalogue assertion.
The start checkout and remote were both the reviewed `bc7feaa08910548c2e236fed97c81c627a49fd1b`; no reset was used.
The completion commit adds reporting/evidence only. Exact final main and complete
tag object/peeled SHA are supplied by the final remote-readback handoff; a report
cannot embed its own future commit hash.

Four independent optional components now compose with all five ordinary hostile
melee recipes. Expanded alarm envelope v2 adds the previously unsupported hosts;
legacy alarm v1 and base recipe versions keep their meanings. New movement
envelope v1 provides lateral approach and wounded regroup. The central choice
uses one existing paid opportunity, after recipe housekeeping. There is no new
scheduler, creature-ID dispatch or hidden group target sharing.

| Host | Call / lateral | Investigation | Wounded regroup |
| --- | --- | --- | --- |
| v1 strike/withdraw | Eligible approach with own fresh sight | Idle without retained threat | Required withdrawal/hold first |
| v2 observation-averse | Unseen pursuit; concealment/covered phase wins | Genuinely idle and unseen | Unseen only; one safe step, no core bonus step |
| v3 venom strike/withdraw | Initial approach | Idle without retained threat | Required post-hit withdrawal/hold first |
| v4 patient venom hunt | Initial pre-dose approach | No retained/suppressed hunt | Finish withdrawal, retire hunt once, preserve same-prey suppression |
| v5 territorial guard | Engaged within territory | Guarding; origin inside defended radius | Required return wins; spends existing pursuit budget |

Wounded regroup can interrupt advance, lateral intention, alarm preparation or
eligible investigation. A legal melee attack beats lateral movement; a lawful
paid alarm tell/emission retains its existing priority. Patient observation,
expiry and retirement still run. Victim-owned venom is never cured by the hunter's
retirement, departure or death. Full paralysis blocks voluntary physical actions;
normal Wait advances its bounded expiry.

Lateral defaults: 8 opportunities and 16 charged phases. Regroup defaults: at or
below 50% own HP, 6 travel opportunities, 2 paid holds, 16 charged phases. Arrival
on the final travel step still retains configured holds. Both use lawful visible
same-faction support and bounded physical routes. Fixed support/goal commitments
release on death, movement, obscuring, incompatible scene or blocked route.
One spent attempt persists through target switches, injury, save/load and departure.
Rearm requires 24 consecutive genuinely quiet active charged phases; regroup may
also rearm after actual recovery above 75% HP. There is no healing, cure or buff.
See the [authoritative bounds, phase and persistence guide](../../roguelike/docs/ENEMY_RESPONSE_COMPONENTS.md).

## Using the palette

In Workbench, duplicate a suitable original to a new ID, select Composite and its
recipe, then choose **Expanded v2** alarm compatibility and the four independent
checkboxes under **Enemy response components** / **Enemy movement components**.
Validate, review/apply, reopen, place in a saved room, then **Test room**. First
opt-in and changing the base recipe require a new ID. Enrolled same-recipe
variants can tune future instances; saved actors retain effective configuration
and credit, including continued absence of attachments. Protected art/body and
supported unrelated metadata remain owned.

| UI-authored example | Base | Movement | Alarms |
| --- | --- | --- | --- |
| `barrow_lane_revenant` | v1 | lateral + regroup | call + investigate |
| `barrow_shy_stalker` | v2 | lateral | investigate |
| `barrow_nettle_guard` | v3 | regroup | call |
| `barrow_patient_weevil` | v4 observed paralysis | lateral + regroup | investigate |
| `barrow_kin_sentinel` | v5 direct melee | regroup | call |
| `barrow_shy_listener` | v2, further recombination | regroup | investigate |

All six reuse existing art/body assets. Packaged controls genuinely created and
published them and five layouts; no JSON edits completed the advertised flow.
`ai9_lateral_lane`, `ai9_venom_lane` and `ai9_shadow_lane` are saved Test rooms.
The final authoring comparison toggled lateral off/on through the controls:
after the same six Wait inputs at turn 486, the runner stood at (34,20) disabled
and (34,21) enabled, with actual lateral actions only in the enabled run.
Undo/redo, no-op reopen, invalid rearm rejection, protected sources, captured
Reset versus latest-saved and exclusion of a parked dirty draft passed.
[Authoring receipts and captured identities](../../evidence/ai-9/authoring.json).

Privileged live tactic inspection shows effective values, host eligibility,
own sight/memory, support/goal, remaining credit and actual action. It is read-only.
Ordinary text remains brief and sensory. Reset retains captured dependencies;
Test latest saved version deliberately captures newly published definitions.

## Ordinary encounters and preservation

Fresh authored-barrow selection remains 0.35 overall, now with equal A/B/C/D/E
weights 1/1/1/1/1. A/B/C definitions and saved assignments are unchanged.
Actual 128x128 world seed **20261027** selected A57/B49/C54/D40/E58. Witnesses
used genuine D at **(80,97)**, `submap_80_97_0`, and E at **(69,92)**,
`submap_69_92_0`, with normal scene construction and entrance/return handlers.

| Encounter / response | Observed result |
| --- | --- |
| D, confront western runner | HP56; actual call, lateral approach, wounded travel and hold; runner defeated, sentinel remains |
| D, southern/eastern route | HP60; both enemies remain; support isolation/base fallback, Ward and return remain accessible |
| E, dark western confrontation then relight | HP56; unseen pursuit/melee, watcher defeated; patient monitoring then finite retirement, hunter remains |
| E, lit alternate route | HP58; concealment/cover and patient withdrawal; both remain, Ward and exit reached |

The sentinel's authored defended radius is 2 (registered default remains 4),
keeping its support post stable until approached. D's open group and E's broken
sight/closed doorway separate threats. Focused corridor, door, decor and occupancy
changes separately establish blocked-route fallback. E's ordinary witnesses show
lawful fallback and core identities, not successful lateral/regroup there.

Each response collected the actual Ward through normal input, used F5/F9 and an
independent cold load, exited and revisited. Assertions preserve resident identity,
injury, original home, death/remains and Ward ownership without repopulation.
The player was staged at an actually selected entrance; route scripting knows
static room geometry but excludes actors only through normal visibility. Combat,
injury, AI and costs are not injected. These are bounded reproducible witnesses,
not unaided laboratory travel or a universal balance/fun claim. Successful
disengagement with living enemies is an intended finite outcome.

Six genuine pre-AI-9 archives were captured from untouched `bc7feaa` with normal
Wait/F5 before serializer changes: unattached v1/v2/v3, v5 preparation and v1/v5
investigation. All load exactly under AI-9. Newly rerun retained play also covers
the provenance-backed pre-AI-6 v4, AI-6 v5 and AI-7 v6 archives. No schema stripping
or personal campaign was used. Snapshot equality does not claim universal RNG
stream persistence. Strict malformed state rejects before partial scene installation.

All **278** initially recorded owner files remain byte-identical and outside task
commits. Tracked art/wiki deltas are empty. Personal saves were not opened; no
worktree, task branch, development copy or desktop control was used. The narrow
AGENTS amendment and one resumable progress record retain the commissioned scope.

## Executed verification and delivery

All results below were newly executed for this commission. Twenty-one successful
gates retain their original tested inputs; the complete eleven-module worker
cohort was rerun after the exact test-only catalogue correction. Game/editor/
package bytes and every other verifier input are unchanged. The initial failed
worker result remains preserved, and each final gate records its tested revision
and input manifest. [Exact delta and repeat](../../evidence/ai-9/verification-input-delta.json),
[commands/environment/results](../../evidence/ai-9/release.json),
[gate totals](../../evidence/ai-9/gates.json).

- Unfiltered focused suite: **605/605**,
  including 17 AI-9 adversarial tests and all twenty host/component action pairings.
- Unfiltered production-D: **3704/3704**
  checks across **159** workers; no failed check.
- Workbench worker: **52/52**
  across eleven modules; frontend **97/97**,
  host **71/71**, startup
  **15/15**.
- Typecheck, clippy, debug/release build, NSIS bundle and desktop lifecycle passed.
  AI-9, AI-8, AI-7 and AI-3 packaged native checks passed. New AI-9 play and retained
  AI-8/7/6/5/3 play all passed. **22 final gates**, with stable input
  bytes under their recorded manifests.

Windows CPython **3.11.0** from the existing pinned baseline environment imports
this production source. Worker tests use bundled `worker/runtime/python.exe`.
Node **24.15.0**, Rust/Cargo **1.95.0**, pygame **2.6.1**, tcod **19.3.0**, NumPy
**2.4.6**; dummy SDL, disposable saves, ordinary/app-local events. The complete
commands and interpreter paths are recorded in the release evidence. Main run:
`python -X utf8 -B tools/verify_ai_9.py --evidence .baseline/ai-9/final-a`.
Affected repeat:
`python -X utf8 -B evidence/ai-9/worker-retention-witness.py --original .baseline/ai-9/final-a --evidence .baseline/ai-9/worker-final`.
The witness enforces exactly the five explicit expected room additions, binds its
own source hash and rejects any other consumed-input change. The corrected test
is excluded from shipped resources (`bridge.py` and the pinned runtime).

Final input manifest SHA-256:
`551c0cce90518108b320333eb46115844c6cacfde41eea107fb3ce3a9b96ad66`.
Workbench executable SHA-256:
`0c67e67ee7be3c5881a9f59df67eb1e329b66ee1bd73ce5e0c08f43b1e5e4212`.
NSIS installer: **28,496,800 bytes**, SHA-256
`addce6b9e4ca7f1260ce3a9d730010617824d41ecd7de3df43913db943e06564`.
[Package binding](../../evidence/ai-9/package.json).
[Actual ordinary response comparisons and save checkpoints](../../evidence/ai-9/play.json),
[preservation result](../../evidence/ai-9/preservation-result.json).

The lead remained sole writer. Read-only reviews found and prompted repairs to
observation-averse double movement/exposed saved investigation, premature melee
on a flank route, the final-travel-step regroup hold, explicit revisit assertions
and complete verifier-input binding. [Review, repaired failures and limits](../../evidence/ai-9/review.json).
An initial authoring capture correctly rejected concurrent input changes after
publication; later sequential runs and the final frozen native gate passed.
Inventory expectations changed only for six new creatures/five layouts and the
game-owned authoring contract; existing assertions and unfiltered gates remain.

Published checkpoint references use suffix `20261105-a`: **start**,
**implementation**, **verified-input** and **complete** under `checkpoint/ai-9-`.
[Remote checkpoint readback](../../evidence/ai-9/publication.json) records the
first three annotated objects and peeled revisions; the final handoff provides
the exact completed main and complete-tag readback. Stop boundary: this bounded
active-scene enemy composition/encounter package. No wiki release, further ally
work, art migration or later roadmap stage is included.
