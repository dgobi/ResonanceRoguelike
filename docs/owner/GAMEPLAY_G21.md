# G21 — Local rivals and consequences

Scope verified. Delivery reference: `checkpoint/gameplay-g21-verified-20261030-a`.
The full delivered SHA and exact origin readback are retained outside this
self-referencing commit in `.baseline/g21-publication.json` and the completion
message. No later arc commission is started.

Start: `e142545567ba9f92722c4a6ee2eea92dcbf31a24`, matching reviewed G20.
`checkpoint/gameplay-g21-start-20261030-a` preserves it. The owner's unrelated
untracked Workbench proposal is untouched. Work stays on production `main`;
disposable save/verification roots are not development checkouts. No desktop
input, personal campaign, wiki, population policy or later arc work is involved.
Authority hashes and the declared native budget are in `evidence/gameplay-g21/`.

## Delivered contract

Fresh Highland Bandits retain `outlaw`, hostile to `player, stalker`; fresh Heath
Stalkers use `stalker`, hostile to `player, outlaw`. No other canonical relationship
or creature statistic changes. Rival sources/candidates must be living ordinary
WanderingAI actors without ID-bound abilities, owned by the active scene. The real
player is recognized by identity and remains separately eligible. Disruption and
ability suppression do not remove a defender from eligibility. Player attacks
retain their ordinary authority.

Uncommitted actors choose nearest observed eligible hostile by squared distance,
then stable individual identity; an initial equal-distance player sorts first.
Retain a currently observed target. Only when it lacks legal striking contact may
the nearest observed hostile in legal contact replace it. Current observations
precede a hidden trail. Rival memory lasts through last observation phase plus
`alert_memory`, inclusively; the next phase expires it. World time, including time
paused or away, owns expiry. Reaching an empty remembered location also ends it.
Player pursuit retains its established timing.

Sight uses actual range, ambient light/darkvision, terrain occlusion and the same
occupied-terrain concealment reduction as the physical player. Presentation masks
never supply AI sight. Sound retains G20's anonymous fixed source, salience and
deadline; it never identifies a maker/victim. A genuine target clears sound.
Selecting a rival clears player trails, pending stair use and pursuit counters.
`AIState.RIVAL` is separate from every player-pursuit transfer state. Chunk exit,
edge crossing, stair extraction and live management retain their player-state
gates; delayed stair intent also rejects a rival, process_single cannot simulate
one, and serialized live/pending ownership cannot contain a local rival intent.
No extra action, phase, accumulator credit, rewind or offscreen combat is added.

Committed attacks retain the real resolver, body/armour/essence, legal contact,
speed budget and one combat sound including misses/dodges. The commit boundary
rechecks the actual local individual and current terrain. A later scheduled dead
actor cannot act. Musk retains its barrier-aware radius and six phases including
the throw, without banked speed or a recovery bonus. Detailed rival feedback needs
both participants visible; hidden identities, damage and deaths are suppressed.

Physical death is exactly once, immediately ends blocking/combat and clears rival
references, then creates ordinary decay-owned remains subject to existing
ephemeral rules. Only an explicitly attributed fatal player attack/moveset fires
`ON_ENTITY_KILLED`. Creature fatalities, prior player wounds, luring, sound/musk,
unknown killers and repeated finalization grant no player kill rewards.

## Saved state and authoring

Saved faction/list snapshots remain authoritative, including old player-only
Stalkers with `predator` and explicit `[]`. Fresh definitions do not migrate them.
Construction copies a supplied list; omission/null defaults to player. IDs are
optional/lazy map-owned monotonic numbers namespaced by the scene of first allocation.
Canonical first allocation sorts by definition/home/position, independent of game
RNG; later order/movement cannot alter an allocated ID. `_creature_id` remains the
definition identity. Map counters and individual IDs persist through ownership
transfer. Untouched historical actors gain no random identity fields.

The optional target stores individual ID, owning scene, last observed coordinates
and absolute deadline, without object references. Restored owning actors are
reconstructed before active-scene revalidation. Missing/dead/foreign/expired
targets clear without selecting a sibling or replaying an action. Zero coordinates
are valid. Malformed types, bounds, conflicting player/sound intent, unsupported
AI/special bindings and duplicate IDs across scene/transfer owners reject before
installing player/world/cache state. Absent optional state is neutral, including
F9 over divergent unsaved behavior.

Workbench `creature-rivals-3` adds bounded faction and explicit add/remove/clear
hostility controls. Both original source and candidate must support the contract.
Other AI and special-bound definitions retain read-only relationship limits.
Labels are exact 1–32 lowercase letter/digit/underscore tokens, beginning with a
letter; lists have at most sixteen distinct entries. `[]` deliberately selects
nobody. Unmatched labels are legal. No folding, deduplication, coercion or global
registry exists. Source, recovery, original entitlement, exact edits, history,
stale rejection and reviewed single-file publication remain shared.

## Demonstrations and boundaries

The native budget declares the two supplied candidate pairs in seed 20261030,
one continuation each, 360 phases each; at most one further bounded sixteen-scene
sample only if both fail. The first candidate succeeds, with one player placement
at `(42,21)` in generated `(63,121)`. The approach retains ordinary bump combat when a creature obstructs movement;
no injury is manufactured or reset. Native Bandit `(35,21)` pursues east through
ordinary live extraction/arrival and meets the native Stalker from `(7,33)` in
`(64,121)`. Both select and attack each other while the player withdraws. Actor,
terrain, resource, health and population staging are absent. Full-state scripted
route assistance and one staged player entry do not establish unaided discovery.
The frozen witness costs 56 phases and 12 player HP, ending at turn 536 / HP48.
Both creatures survive their first mutual strikes. Only the first declared pair
is used; identical source-certification repeats are not additional adaptive
search attempts. No second candidate or extra sample is used.

Prepared comparisons use the exact genuine G20 prepared-return archive (seed
20261023), independently restored and staged into one native authored room with
fresh G21 factory participants. Owned inventory, quantities, fuel, needs, equipment
and HP are retained. Independent cold continuations let conflict develop and take
the far flank, spend the real finite musk for direct passage and recovery, or
take the unprepared direct route. No winner or injury is forced. The established original-loop driver seeds gameplay RNGs to 20261020 at
bootstrap; this is disclosed deterministic test assistance, not spawn-roll
manipulation. Native population still uses the declared world seed. Full phase/item/
HP/target/death/remains ledgers distinguish this fixture from native selection.

A separate controlled lethal continuation discloses Stalker HP=1, staged positions
and combat RNG=4. A real Bandit fatal strike creates remains with no player XP.
Ordinary subsequent player combat earns its separate direct kill reward. The
actually owned/equipped crude blade then butchers the Stalker through the cursor,
charging five phases and retaining pre-existing fractional debt. Real outputs,
F5, separate-process cold load and a cold leave/revisit keep the corpse depleted.
The return uses native transition methods for this noncanonical fixture; no new
canonical entrance or acquisition journey is claimed. Another native authored
corner/closed-door fixture proves that the same musk burst covers only the near
participant until the door opens, while anonymous sound can pass attenuated.

Development corrections retained in the evidence summary: rival pathfinding must
leave its observed target tile reachable; the first fixture's origin calculation
mistook default outside-map walls for the authored origin; the first harvest
assertion incorrectly expected zero rather than preserved fractional debt. These
were source/harness corrections, not retries for a preferred combat winner.
Visual inspection of final-a also found second-person resolver body prose in
rival hit results. That incomplete release run is retained as failed: its
unfinished owned gate processes were stopped. Rival results now use generic
target-correct feedback, with an explicit second-person regression assertion;
all required gates rerun from the corrected frozen input. Construction review
also caught string-to-character-list coercion in the initial copy operation.
Construction and saved-row preflight now reject invalid list types, retaining
valid saved lists exactly. The incomplete final-b run is retained; final-c
reruns every required gate after this validation correction.
The development package lock failure came from overlapping NSIS and a test launch;
final packaging and native launch are sequential. Historical archives are immutable.

The complete final-c set passes every gate except two historical pending-scene
comparisons in the 429-test focused suite. Both expected original G9/G10 factory
attitudes while generating fresh pending actors from G21 definitions. The tests
now bind only faction/hostility to each immutable creator revision in an isolated
DataLoader copy only during unvisited factory calls. Current-catalogue load,
visited restoration, cold load and F9 remain active, so this binding cannot mask
saved-perception restoration. The initial final-d focused rerun was superseded
while narrowing this test-input boundary. Exact archive byte checks, expected whole-scene fingerprints and
the fingerprint validator remain unchanged; production loading/definitions are
unchanged. Both corrected targeted checks pass. Final-e passes all 429 focused
tests; final-c's other gates are retained under exact unchanged-input boundaries.
No runtime/data/driver/Workbench/package input changes with this fix.

## Verification and publication

Focused input: `3ae7d8c3c4aff3dec9d49f8e6e35ebd30fe138d5`. Retained runtime,
play and Workbench input: `adb28ac838facfc53cd6426f763e13a165fbe413`. The only
covered-source differences are two historical focused-test files, listed in
[final-e inputs](../../evidence/gameplay-g21/final-e/inputs.json). Runtime/data,
authoritative guides, executed play/production drivers, frontend/worker/Rust,
bridge/bundled runtime and package inputs remain byte-identical. Retained gates
do not import the changed regression modules. No changed test input is skipped.

| Required check | Actual final result |
| --- | --- |
| Unfiltered focused regressions | 429/429 pass |
| Unfiltered production D | 3,704/3,704 assertions; 159/159 workers; seven negative controls |
| Workbench frontend / TypeScript | 90 tests; typecheck passes |
| Workbench host / clippy | 71 Rust tests; warnings denied |
| Workbench worker | 117 tests: 116 pass, one existing embedded-interpreter skip; separate development-interpreter dependency control passes |
| NSIS / native application | Pinned bundle, hearing and reciprocal/directional/unmatched/empty-list publication/reopen/runtime probes pass |
| Historical / original loops | Genuine G14/G16 archives, G19/G20 loops and all seven G21 stages pass |

Windows x64, CPython 3.11.0, pygame 2.6.1, tcod 19.3.0, NumPy 2.4.6. Commands,
versions, logs and source bindings are in [final-c](../../evidence/gameplay-g21/final-c/release.json)
and [final-e](../../evidence/gameplay-g21/final-e/release.json). Both completed sets
preserve their frozen sources. Final-c remains failed overall because of its two
historical input expectations; its 21 individually passing unaffected gates are
explicitly retained. A/B/D remain incomplete diagnostic runs.

Final-c ran 2026-10-30T21:05:31.287329+00:00 through
21:32:59.095306+00:00, 1,647.927 overlapping wall seconds. Final-e ran
21:40:39.095481+00:00 through 22:03:20.352082+00:00, 1,361.255 wall seconds.
Process durations are not summed into wall time; correction/inspection gaps are
not characterized as execution.

All prepared branches start at turn 1011 / HP60 from identical archived ownership.
The table ends after passage plus eight ordinary observation phases. A separate
one-wait F9 restore diagnostic is excluded from comparison deltas.

| Continuation | Passage phases / HP | Final phases / HP | Player attack exposures | Spent / aftermath |
| --- | --- | --- | --- | --- |
| Conflict and far flank | 16 /57 | 24 /33 | 12 | No preparation; Bandit corpse, Stalker HP11 |
| Musk and direct passage | 12 /57 | 20 /48 | 5 | One real pellet; Stalker corpse, Bandit HP8 |
| Unprepared direct control | 11 /46 | 19 /23 | 12 | No preparation; Stalker corpse, Bandit HP15 |

All three checkpoints have zero player kill XP. Flint remains in all three; both
unprepared branches retain the pellet. The throw leaves five protected phases,
with no actor movement/accumulator gain, followed by ordinary recovered combat.
The genuine prepared ZIP is byte-identical to its published G20 blob; SHA256
`54e4bd8b0a7913bac1a0b4c755b955b621a8587bef92072bbdf123afac292530`.

Controlled lethal: 0 XP after the creature fatal, 45 after the separate player
fatal, unchanged after five-phase harvest. Stalker Meat, Sinew, Bone and Viscera
persist, and prior fractional debt .2 is preserved. A [supplemental cold frame](../../evidence/gameplay-g21/supplement/rendered-cold-revisit/cold-revisit-rendered.png)
from the original loop shows the retained outputs and separate Bandit remains,
with zero new phases. The earlier direct-return capture preceded its render and
is not used as visual proof of the returned room; its state assertions remain valid.

New executable SHA256:
`74550e2870bf0cb66371f3c7557c72ff2008c6436703b4983033a260c9288a18`.
New 0.9.0 NSIS SHA256:
`8d1b76be508a3934f4af95e0434a89faa8d1350b02232844b5f1c4697569237f`.
Other installer versions in build-directory listings are historical. The owner's
installed application was not replaced. [Completion metadata](../../evidence/gameplay-g21/completion.json)
retains provenance, resource, credit, package, source-binding and boundary details.

Publication uses the final report/evidence commit and verified checkpoint, an
atomic non-force push of `main` and every G21 checkpoint, exact origin readback,
and a final committed-blob/input audit. The publication receipt is outside the
commit it identifies. Unrelated owner work remains separate.

Remaining scope limits: one rivalry, ordinary WanderingAI only, active-scene
combat, finite local memory, no assists or contribution scoring, no global ecology
or diplomacy. Native entry/route assistance, prepared-room staging and controlled
lethal HP/RNG are separately disclosed; no unaided discovery or universal balance
claim is made. G21 does not declare H1 or the whole arc complete.
