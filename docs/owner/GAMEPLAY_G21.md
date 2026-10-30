# G21 — Local rivals and consequences

Implementation ready for frozen verification; publication is pending. This report
will record the actual final receipts and remote delivery before completion.

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
optional/lazy map-owned monotonic numbers namespaced by their original scene.
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
at `(42,21)` in generated `(63,121)`. Native Bandit `(35,21)` pursues east through
ordinary live extraction/arrival and meets the native Stalker from `(7,33)` in
`(64,121)`. Both select and attack each other while the player withdraws. Actor,
terrain, resource, health and population staging are absent. Full-state scripted
route assistance and one staged player entry do not establish unaided discovery.
The initial development formation costs 56 phases and 12 player HP; final values
must be taken from the frozen witness.

Prepared comparisons use the exact genuine G20 prepared-return archive (seed
20261023), independently restored and staged into one native authored room with
fresh G21 factory participants. Owned inventory, quantities, fuel, needs, equipment
and HP are retained. Independent cold continuations let conflict develop and take
the far flank, spend the real finite musk for direct passage and recovery, or
take the unprepared direct route. No winner or injury is forced. Full phase/item/
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
The development package lock failure came from overlapping NSIS and a test launch;
final packaging and native launch are sequential. Historical archives are immutable.

## Verification and publication

Frozen input revision, exact commands, source bindings, Windows environment,
actual gate counts, failures, package identity and remote readback are recorded
in final receipts before this report is marked delivered. No development check
or Linux diagnostic is substituted for the required Windows release gates.

Remaining scope limits: one rivalry, ordinary WanderingAI only, active-scene
combat, finite local memory, no assists or contribution scoring, no global ecology
or diplomacy. This completes a bounded G21 interaction when its gates and
publication finish; it does not declare H1 or the whole arc complete.
