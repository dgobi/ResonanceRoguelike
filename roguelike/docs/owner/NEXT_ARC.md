# Next arc — after G2 structure authoring

The proposed next generation arc is shared settlement/road/plot planning with
intentional placement and selection configuration, then rural landmarks/POIs.
G2 supplies trustworthy authored inputs and runtime previews. `town_config.json`
remains inactive; activating/replacing its category, street, lamp and settlement
policy belongs with that later contract. New rotations, arbitrary categories,
physical body/stele behavior, WFC palette redesign and saint-alcove/dock/foundation
intent remain deferred. See [WORLDGEN_G2](../../../docs/owner/WORLDGEN_G2.md) and
[the proposal](../../../docs/owner/WORLD_GENERATION_AUDIT_AND_PROPOSAL.md).

This recommendation does not authorize another arc. Continue in production
`main` with named checkpoints and autonomous headless verification.

<details>
<summary>Earlier status — retained; superseded only where stated above</summary>

# Next arc — after D combat and effects

C is owner-accepted and D is implemented on production `main`. See
[D_STATE](D_STATE.md) and [D_VERIFICATION](D_VERIFICATION.md). Continue in this
checkout with named checkpoints and local commits, without additional copies,
worktrees or task branches. Routine testing remains autonomous and headless.

A next bounded task could address the preserved UI-TEXT-HEIGHT defect. Separate
follow-ups include carried decay / butchery content, Heavy Blade free-move-on-kill,
Dissolution Blade pool lifetime, full RNG replay, personal-save migration and
checkpoint pruning. This list does not authorize a new arc without an owner request.

<details>
<summary>Earlier history — superseded only where stated above</summary>

# Next arc — after C ownership

B3 is owner-accepted and C ownership is implemented on production `main`.
See [C_STATE](C_STATE.md) and [C_VERIFICATION](C_VERIFICATION.md) for scope and
evidence. Continue in this checkout with named checkpoints and local commits;
do not create more development copies, worktrees or task branches.

The next proposed task is D combat/effect lifecycle: temporary armor hit counters,
suppression/disruption consumers, wight confirmation, thrown-item targeting and
salve movement timing. Scope and reproduce those behaviors before changing them.
Treat UI text layout, carried decay, all butchery content, RNG replay, personal-save
migration and checkpoint pruning as separately bounded work. This recommendation
does not authorize starting another arc without the owner's request.

<details>
<summary>Earlier accepted history — superseded where stated above</summary>

# Next arc — C ownership and transfers

B2 is owner-accepted and merged with Arc A/B1 into production `main`. B3's scope
and evidence are in [B3_STATE](B3_STATE.md) and [B3_VERIFICATION](B3_VERIFICATION.md).
Continue in this checkout on `main`, with named Git checkpoints and local commits.
Do not create more development copies, worktrees or task branches.

Recommend C next: exact ownership across inventory, floor, equipment and containers,
beginning with the reproducible equipped-drop reference. Define transactional
transfer/crafting cancellation boundaries, test failure cases and actual app-local
inventory flows. Keep the separate effect lifecycle and text-layout work bounded.
Personal-save migration and automatic checkpoint pruning need separate scope.

<details>
<summary>Earlier accepted history — superseded where stated above</summary>

# Next arc — B3 checkpoint coherence and recovery

B1 is accepted; B2 completes component/derived-state reconstruction with the
contract in [B2_STATE](B2_STATE.md) and the enforced autonomous gate in
[B2_VERIFICATION](B2_VERIFICATION.md). Its completed changes are committed locally.

B3 should define a coherent whole-slot checkpoint across player, world and scene
records; flush inactive dirty state according to that policy; test interrupted
writes and recoverable generations; and constrain rollback/slot/deletion behavior.
Use the accepted B2 copy and new disposable save roots. Keep C transfer/crafting,
D combat/effect lifecycle and UI text layout separate. No personal-save migration
or destructive owner-save tests are implied. Headless/app-local verification remains
the default; do not revive Arc A's superseded desktop/manual-window requirement.

<details>
<summary>Accepted B1 checkpoint and earlier history — retained, superseded where stated above</summary>

# Next arc — B2 component and derived-state reconstruction

B1 is the current bounded identity/replacement task. Use its final enforced gate
and return package for acceptance; do not reuse the superseded Arc A manual-window
requirement. All routine verification is autonomous and headless.

Proceed next to a separately scoped B2 task: inventory the saved/reconstructed/
derived/reset component fields; address route-specific Needs configuration, perk
hook reconstruction, omitted timers and remaining item instance state. Preserve
the B1 format/reference/scene regressions. Record exact owners and measurable
behavior rather than claiming all-field fidelity from identity tests.

B3 remains separate: coherent checkpoint generations, inactive dirty flushing,
interrupted-write recovery, rollback and slot/deletion policy. Travel currently
writes scene records outside full saves. C owns transfer/equipped-drop behavior;
UI owns text panel wrapping/height. The concrete reproductions and boundaries are
in [B1_DEFERRED.md](B1_DEFERRED.md). Do not implement these later arcs as incidental
B1 cleanup. No personal-save conversion is authorized.

<details>
<summary>Archived Arc A text — 20 October 2026; superseded operational requirements and failure status</summary>

# Separate implementation brief: B1 persistence identity and explicit replacement

This is a proposed next task, not authorization to implement it during Arc A.

## Goal and baseline

Preserve independent surface and underground scenes across full save/load; preserve creature definition identity when presentation changes; treat saved empty inventory/equipment as replacement state. Explain each fix to the owner using a small before/after example. Start from the actual reviewed working copy plus Arc A setup/docs, not original HEAD alone. Recheck drift and preserve user work. Use new disposable sessions only.

## Scope

Read `main.py`, `Engine._descend_to_submap/_ascend_from_submap`, `SaveManager.save/load`, `ChunkCache`, `_serialize_player/_deserialize_player/_restore_equipment`, `_serialize_entity/_deserialize_entities`, `CreatureFactory.spawn`, and `_ability_stone_lurker`. Reuse the Arc A diagnostics, first verifying their hashes/fixture contracts.

1. Make scene identity explicit at each save/load boundary: `(world_x,world_y,submap_id-or-None)`. Route an active underground map and actors to its own cache key; load the matching scene. Retain the separately cached surface. Avoid a broad scene-manager extraction unless a small helper is necessary for correctness.
2. Serialize stable creature definition identity using the existing `_creature_id` authority rather than mutable tile. Restore the appropriate hibernation/presentation state without dropping or duplicating the creature. Spell out the lifetime of every newly handled field.
3. Replace saved inventory/equipment state explicitly, including empty collections and absent slots. Clear prior slot references before relinking to restored inventory instances. Test in-session state and bootstrap state independently. Do not let a bootstrap light remain active when its item/component is absent; identify any narrowly necessary derived-state clearing, and defer broader reconstruction to B2.

No creative redesign, save migration, engine swap, all-field persistence overhaul, crafting/combat/generation backlog or external publishing. Existing personal saves remain untouched. If compatibility requires a policy choice, prepare the concrete format impact for the owner; do not assume migration approval.

## Gates

* In one session and in a fresh process: mark surface grass+hollow_revenant and underground flagstone+grave_thing; save underground, load, ascend, descend. Check scene IDs, both tile markers, actor definition identities/counts and selected modified actor values. Include save on surface as a control.
* Empty inventory/equipment replaces bootstrap and deliberately different prior state. A nonempty saved inventory with empty slots clears old references too. Every non-null equipped item is the exact restored inventory instance; no ghost torch/armor. Include valid equipped restoration and two same-definition items as a boundary test; if distinct-instance identity needs B2, state that limitation explicitly rather than claiming it fixed.
* An actually hibernating stone lurker remains one stone_lurker before/after serialization and reconstruction, still displays/behaves as dormant until the player approaches. Check both immediate reconstructed state and one subsequent ability tick. Include awake control.
* Run `tools/persistence_diagnostics.py --prefix b1-after --assert-properties` with computed assertions. Add only meaningful cases for the chosen repairs. Retain failing-before evidence, source hashes, exact commands and exit codes.
* Complete a bounded manual game-window save/load/ascent demonstration once input delivery is available. A screenshot or component test alone is not this gate.

## Explanation and return

Explain in plain language: surface and lab shared one address during full save; empty was mistaken for absent; a creature's costume was used as its identity. Show the new owners/keys/replacement order and what remains reset/recomputed or unsupported.

Return a small patch, field/format changes, before/after diagnostics with independent processes, manual observations or an explicit blocker, and updates to WORLD_AND_STATE, STATUS and the decision log. Add an owner exercise that predicts two independent markers, saves/reloads, verifies both and reverses the fixture. Record owner learning separately from automated verification. Do not mark B1 complete merely because a harness exits zero.

</details>

</details>

</details>

</details>

</details>

</details>
