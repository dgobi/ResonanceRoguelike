# AI-7: protective escort and local commands

Runtime/content/editor tested revision:
`8c17f961ff400447e29facc70243fb301ebdaebe` on production `main`.
Start: `a5ce9bfe38e3e6c3c2d54c583be70cabf7393fa2`.
Implementation checkpoint A is `b31779cb717faf0e5ab20e33cf0ecd37d27f16a1`;
checkpoint B closes the final malformed-save gaps. Final verification-input
revision: `3ac18d8763ce4683eb5ffc0c479352472cdda5d6`. Its only delta updates three Workbench test inventory
expectations for the two new actors/rooms; the full 50-test worker suite is rerun.
All product bytes and other test inputs are unchanged.
[Exact verifier delta](../../evidence/ai-7/verification-input-delta.json).
This completion commit adds reporting and non-consumer evidence only. It cannot
embed its own future hash; the final handoff supplies the delivered SHA and the
independent remote readback. [Input binding](../../evidence/ai-7/input-delta.json).

Version-6 `protective_escort` gives an ordinary player-faction melee creature a
local player ward with separate sight evidence and stable ordinary threat intent.
Follow and Hold here use the existing E interaction cursor. Confirmation rechecks
scene, exact actor/identity/tile, player position, current order/post, ordinary
visibility/reach and player physical eligibility. Acceptance advances exactly one
world phase through the normal scheduler. Inspection/cancel/rejection are free.
Hold saves the current instance tile; Follow uses its own bounded last sight,
never hidden player coordinates, debug reveal or anonymous sound.

Protection is relevant observed hostility inside a small radius. Every pursuit
step respects the last lawful ward/post reference and excursion; attacks and
contact interruptions spend finite pursuit opportunities. Expiry/failure commits
to physical rejoin/return with bounded waits/retries and retired unchanged threats.
Bumping this specific ally attempts a legal adjacent yield or two-actor passage
swap, through normal player terrain effects/work debt and physical eligibility.
Ordinary enemies can target it through `player` hostility. Real combat supplies
injury, paralysis, recovery, death/remains and nonplayer kill attribution.

Successful departure preserves its old-scene position, HP, identity, order and
post, clearing local evidence and pending commands. It stays frozen there under
existing scene policy, with no stairs/chunk transfer or offscene AI. Returning
Follow needs fresh sight. The strict v6 save shape preserves effective tuning,
ward/threat evidence and finite commitment; v1-v5 schemas remain unchanged.
Malformed protection without ward evidence, foreign identities/cache ownership
and contradictory phases reject before staged installation. Missing/dead targets
invalidate cleanly on continuation.

## Authoring and availability

Workbench's registered **Protective escort** card exposes initial order, spacing,
protection, excursion and pursuit bounds. Player faction and explicit nonplayer
hostilities are mandatory; unsupported/special/ranged/NPC hosts reject. New
recipes require a new ID; same-recipe tuning affects fresh actors, with saved
instances retaining their profile/orders. Art/body, unknown fields, protected
metadata, exact-source review/reopen and undo/redo remain intact.

Actual packaged controls launched through `workbench/Launch Workbench.vbs`
created/published/reopened `ash_escort`, `stone_escort`, `ai7_escort_lane` and
`ai7_escort_threat`. The two actors share ordinary combat, perception, speed and
alignment but differ in initial order/spacing/protection/pursuit. The threat room
uses the existing Barrow Sentinel. A saved initial-order edit changed live
position from (36,21) under Follow to (38,21) under Hold after the same movement.
Reset retained Follow; latest-saved used Hold and excluded the dirty Follow draft.
The final version restores Ash to Follow. [Authoring receipts and source hashes](../../evidence/ai-7/authoring.json)
distinguish creation/steady-source comparison from final-package room lifecycle.

Availability is explicit authored placement and isolated game testing. No normal
population selection, barrow variant, starter gift, recruitment, inventory,
medicine, dialogue, target-specific attack order or multi-scene party is added.
See [feature/field/input guidance](../../roguelike/docs/PROTECTIVE_ESCORT_AI.md).

## Verification

All gates were executed during this task using the established Windows Python
3.11.0 environment, dummy SDL, disposable saves and app-local inputs. Sixteen
gates retain the frozen runtime revision above; the full affected worker suite
was repeated after the inventory-only verifier correction. Their consumed product
and other test inputs are unchanged, as the linked manifests/delta establish. [Commands, environment, timings and hashes](../../evidence/ai-7/release.json)
and [gate totals](../../evidence/ai-7/gates.json) bind the results. No historical
pass count substitutes for a current run. The build/bundle logs verify the pinned
bundled Python; package and NSIS hashes are in
[package evidence](../../evidence/ai-7/package.json).

- Unfiltered focused: **572/572** tests.
- Unfiltered production-D: **3,704/3,704** checks across **159** workers.
- Affected Workbench worker cohort: **50/50**, all eleven modules; frontend
  **95/95**, host **71/71**, startup **15/15**.
- Typecheck, clippy, debug/release build, NSIS bundle, desktop lifecycle, final
  native rooms and retained AI-3 native lifecycle passed.
- Four AI-7 ordinary-play families and **10** independent cold comparisons;
  AI-5 and AI-3 ordinary-play families newly rerun as well.

The ordinary-input family enters saved authored rooms, accepts paid orders,
moves through a real door/passage and occlusion route, approaches the guard,
waits for real combat, withdraws and saves. The scene witness walks to the real
return stair, then calls the normal travel handlers for departure/return; it does
not inject a scene or position. With fixed combat/AI RNG
17/19, Hold leaves player HP 48 and escort HP 5 at its post; Follow leaves player
HP 50 and escort HP 14 at a different position. These are controlled outcomes,
not a universal advantage. No attack/damage/perception/AI result is injected.
The ongoing F5/F9 comparison preserves the controlled RNG stream around reload;
RNG continuity is not a newly claimed save contract. Independent cold comparisons
cover Follow, Hold, ongoing threat and aftermath, passage/revisit and legacy.

Focused fixtures separately establish stale/cancelled/dead/absent/foreign/blocked
commands, hidden ward evidence, neutral exclusion, stable targets, excursion,
finite retirement/retry, two escorts, terrain debt, malformed saves and effective
profile retention. A real venom delivery followed by normal phase ageing proves
paralysis denies yielding/actions and cannot bank a recovery step. Real resolver
lethal fixtures use disclosed one-HP setup, correct remains and no player kill
hooks. They are not represented as an unaided ordinary encounter death.

The retained v4 archive truly predates AI-6. The v5 archive was captured during
this task by executing pinned pre-AI-7 source in memory (86 recorded Python
sources), with unchanged AI-6 room/actor data. It is an actual historical-runtime
save, not downgraded v6 state or a claim that its archive timestamp predates this
task. Both retain exact actor meaning through current F5/F9 and cold loading.
The order panel was visually checked at 960x720 and 1280x900; its rendering inputs
are unchanged in the final revision. [Attempts/limits](../../evidence/ai-7/attempts.json).

Development exposed fixture mistakes, an initially too-early withdrawal, a
runtime-changing native snapshot comparison and the final strict-save gaps;
those attempts are not certification. The interrupted initial long preflight and
final-A are explicitly incomplete. Final-A's host test also hit the existing
empty PID receipt read race (70/71); a fresh unfiltered repeat passed 71, and the
corrected final-B newly passed the full host suite again. Its worker run passed
47/50, exposing three stale catalogue expectations. The corrected final-C worker
run passes all 50; final runtime and corrected verifier inputs remain stable
through completion evidence assembly.

## Preservation and delivery

The start, implementation A/B, verified-inputs and complete checkpoint names are
recorded with [remote runtime publication](../../evidence/ai-7/publication.json).
The final complete tag and final remote main readback are supplied in the handoff.
All 100 recorded untracked owner files remain unchanged and outside task commits;
tracked art_lab and wiki deltas are empty. No personal campaign, extra checkout,
worktree or task branch was opened/created. No wiki, HTML/reference-pack upkeep,
normal companion enrollment or AI-8 work was performed.

This is a vulnerable active-scene protector, with bounded legal movement and
ordinary combat. Cross-scene following, recruitment, support actions and general
actor wards remain unsupported. Stop at AI-7.
