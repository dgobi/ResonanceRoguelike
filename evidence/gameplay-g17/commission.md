# G17 — Creatures in authored underground rooms

**Issued:** 25 October 2026, America/Edmonton  
**Status:** Next bounded H1 brief; issued, not implemented.  
**Reviewed baseline:** `main`, `5ae5d1356bd5f37e442694c664354f79096c8e38` (G16).  
**Outcome:** The owner can place a specific existing creature in an authored underground layout, validate and preview its real placement, and play an encounter whose living and defeated states survive the existing save/revisit routes. Invalid placement must fail before the destination is published.

## Execution instruction

When the owner supplies this brief to Codex for execution, implement and verify **G17 only**, commit the completed scoped changes and push to the existing `origin/main`. Work in the established production checkout on `main`, preserve unrelated owner work and personal campaigns, and create a named checkpoint before substantial edits. Do not create task branches, worktrees or additional development copies. Reconcile intervening commits without resetting an advanced checkout. Never force-push or rewrite unrelated history. Carry forward authorization already supplied in the execution session.

Consult `AGENTS.md` and relevant current guidance. The compass, decisions/state, approved implementation proposal and workflow remain applicable; `RESONANCE_G16_REVIEW_AND_G17_HANDOFF.md` supplies the newest reviewed baseline. This brief implements the small authoring dependency identified in H1 package D. It does not commission the entire native underground destination or H1 horizon. Creating this brief does not itself execute or publish code.

## Why this task is bounded here

G16 now demonstrates an ordinary-start surface trip that returns with a real preparation. The next underground place needs an actual authored threat. At the baseline, both the structure validator and special-record resolver reject authored creatures. The internal population path can create actors but does not provide the necessary initial collision/arrival safeguards. A controlled read-only probe accepted two Hollow Revenants on the same blocking crate cell.

Complete that concrete authoring/runtime contract and prove it with one editable room. Keep native destination assignment, meaningful reward choice, supplied travel and alternate encounter approaches for the subsequent content brief. The approved plan explicitly permits this split when combining those uncertainties would produce an oversized task.

## 1. One supported authored-creature record

Permit a direct top-level special in the **`authored_submap` route only**:

```json
{
  "type": "creature",
  "x": 4,
  "y": 2,
  "creature_id": "hollow_revenant"
}
```

Contract:

- `x` and `y` are integer coordinates within the authored grid; booleans, fractional values, missing coordinates and out-of-bounds coordinates are rejected through the existing diagnostic style.
- `creature_id` resolves to an existing supported **non-player** creature definition in the supplied data root. `data.entities` also contains `player`; simple dictionary membership is insufficient. Missing/unknown IDs and `player` are rejected.
- One record creates one actual actor through the existing `CreatureFactory`. No alternate actor constructor, spawn count, group, stat override, loot override or bespoke AI is introduced.
- Keep existing `type`/`kind` consistency checks. Do not silently reinterpret contradictory declarations or make unsupported gameplay fields effective.
- Weighted creature alternatives remain unsupported. Direct creatures in ordinary buildings, plazas and entrance layouts remain unsupported. Give actionable diagnostics; do not quietly ignore a creature record in a route that cannot realize it.
- Preserve the current authored-submap transform: centering/translation into the scene. Do not add rotation or mirroring, or report an unsupported transform as having been applied.

Relevant paths are `generation/structure_contract.py`, `generation/spawn_specs.py`, `generation/local_gen.py`, `engine/scene_generation.py` and the existing factory/preview path. Resolve routine function boundaries locally. A global addition to a shared allowed-kind set is not sufficient if it silently enables unsupported routes.

## 2. Safe initial placement and atomic failure

For the new authored creature path, validate the candidate's complete initial occupancy before publishing it or committing its object layers. Reject:

- Non-walkable terrain, blocking decor, or terrain with `creature_passable: false` unless the selected creature definition has `can_swim: true`. The last condition preserves the existing terrain admission rule; it does not override non-walkable terrain or decor.
- Two authored actors occupying the same cell.
- An actor on the actual player arrival cell.
- An actor on a physical `stairs_up` or `stairs_down` cell.
- An actor overlapping a blocking container/decor scheduled by another special in the same batch, regardless of record order.

Do not silently relocate an invalid authored actor or remove the obstruction. Ordinary nonblocking floor items may coexist with an actor; their ownership remains intact. A valid guarding position in a corridor is allowed—the entire route to the exit is not an enemy-free reservation. These are initial construction rules, not new movement, combat or AI restrictions.

Plan the entire batch before mutation, including blocking containers that occur after a creature record. If validation or a factory fails late, no partial actor/item/container population becomes live. Preserve existing object layers, the departing scene/player, destination cache and original `SubMap.generated` state. Use the existing staged construction/publication boundary.

Keep the new authored rules explicitly scoped. Preserve existing internal town/zone creature population behavior and saved worlds; do not impose new collision policy globally or create a second general population framework. The supported public authored path must not be bypassable by a caller-supplied declaration that labels invalid authored data as internal.

## 3. Honest production preview and one editable example

Add a complete small example under:

`roguelike/docs/examples/g17_authored_creature_room.json`

Add a matching access sidecar. Use a clear arrival and return stair, one existing Hollow Revenant away from those cells, and a small amount of existing item/container content to exercise mixed population. Keep the room readable and the example easy for the owner to edit. It introduces no new creature, reward progression or lore commitment.

Keep this example outside `data/layouts/`: it is an authoring example and controlled proof, not a newly selected campaign location. Do not change the starting laboratory or ordinary world-selection policy. The existing installed catalogue counts therefore need not increase merely because a documentation example was added.

Use the existing command, with the established production interpreter:

```text
tools/structure_authoring.py roguelike/docs/examples/g17_authored_creature_room.json --route authored_submap --access <matching-sidecar.json> --output <disposable-report.json>
```

The preview must use the same compiler, transform, factory and scene-construction path as play. Its report should identify the source asset/special or record ID, original source coordinates, final scene coordinates, actual creature ID/count, relevant seed and consumed creature-definition identity/hash. Use existing receipt/source-binding facilities where suitable. Do not label already translated coordinates as original source coordinates, infer an actor's presence solely from the input, or serialize a live actor as an item.

Source/candidate provenance is sufficient here. No persistent actor registry, generalized submap dependency manifest, new editor UI or world-generation namespace migration is commissioned. If authoring contract metadata changes, keep its manifest/catalogue statements consistent without altering saved placement hashes or historical data. Explain the supported route and its limits in the existing structure-authoring guidance.

Static access checks describe geometry and initial occupancy. A preview may reveal the room for authoring inspection if labelled accordingly; it must not imply that a hostile occupant is harmless or that this establishes encounter balance.

## 4. Preserve existing generation and campaigns

Keep the starting laboratory, current BSP submaps, ordinary surface populations, G13–G16 contents, recipe/item definitions and save schema unchanged. Existing authored maps without creatures retain their behavior. No global population of previously empty underground maps is part of this task.

`SubMap.layout_id` already persists. Preserve blank IDs as the existing BSP route; do not infer a new authored layout from `submap_type`. A later native content task can choose a new versioned layout during fresh-world creation. That later decision is not implemented here.

A genuine historical witness is already available:

`evidence/gameplay-g16/final-a/journey/cold-return/homeward/returned-pellet.zip`

It contains the returned player/pellet, visited laboratory and altered workshop. Its pending `submap_73_97_0` at `(73,97)` has type `barrow`, seed `107361`, blank `layout_id` and `generated:false`. Use metadata identity rather than its generated display name.

Before substantial edits, validate that witness and capture the relevant pending BSP construction fingerprint through the existing route. Afterward, compare the saved player/visited state, plan dependencies and pending construction. Preserve the original archive and historical receipts; do not fabricate an old world after changing code. Reuse compact historical-check helpers rather than creating another large checkpoint archive.

Use the established production interpreter for final gates. The G15/G16 review environment exposed a known exact-float receipt difference under Python 3.12; that is not permission to round live carrying calculations or rewrite historical fixtures. Cross-interpreter test portability remains separate scope.

## 5. Autonomous verification

Use existing headless SDL, app-local events, disposable saves and production helpers. No desktop control or routine owner QA. Tests should protect the new contract and meaningful failure boundaries, not duplicate unchanged engine behavior.

### Compact contract coverage

Cover:

1. Valid direct authored creature, correct centering/translation and actual factory-created actor; ordinary authored content still compiles.
2. Missing/unknown/player IDs, invalid coordinates, contradictory kind, weighted creatures and unsupported routes rejected with useful source/field diagnostics.
3. Wall/decor obstruction, creature-specific terrain restrictions, duplicate actor cells, actual arrival and stair occupancy rejected. Include one generically walkable water cell that the selected creature cannot enter. Actor-before-container and container-before-actor produce the same rejection for a blocking overlap.
4. A late invalid record or factory failure leaves object ownership and live destination publication unchanged. Exercise the real scene-entry boundary as well as the local population boundary where needed.
5. Preview provenance corresponds to the actual returned actor, and the editable example passes its geometry/access checks through the existing CLI.
6. Existing starting-lab/internal-population contracts and genuine G16 pending BSP behavior remain intact.

Reuse existing tests for unchanged ownership, save mechanics and combat. Keep an illustrative mixed-content failure case; do not build a generic fault-injection framework or expand into every native spawn policy.

### One controlled encounter through the original game loop

Use the same example definition in a disclosed disposable linked-submap fixture. Setup may create the fixture's surface/stair link and bind the example to the local test data, but the actor must come from the authored record through production construction. Do not append an actor afterward or substitute a hand-built scene for the authored route.

Through the existing original `Engine.run` event driver:

- Enter by normal stair controls and observe exactly one real actor at the authored destination.
- Preserve a meaningful live-actor snapshot through a genuinely separate-process cold load. Assert the actual actor state and single ownership, not just its type name.
- Continue with ordinary movement/combat, defeat that actor, retain normal death/remains behavior, exit and re-enter through the actual return link.
- Save/cold-load the defeated state and check cache/disk revisit with generation forbidden. The actor does not respawn, and unrelated authored items/containers remain correctly owned.

Normal AI, FOV, combat and time remain active after the disclosed setup. Do not set the actor dead, delete it directly, enable invincibility or restore health to manufacture success. Seeded deterministic inputs are acceptable when disclosed. A small controlled encounter is enough; no normal-start world journey, hunt, paired tactical balance study or all-seed campaign is required for this authoring contract.

This demonstrates construction, ordinary interaction and persistence. Label it as controlled authoring/runtime evidence, not native world selection, discovery, an approved encounter balance or completion of H1. Existing F9/save coverage can be reused; any new rollback claim must follow an actual unsaved change. New completion metadata should agree with the observed completion checks; do not rewrite old receipts to tidy their flags.

### Final gates and delivery cost

Preflight the example, diagnostics and short encounter before freezing expensive final inputs. Run the existing unfiltered focused discovery and production-D gates, the bounded G17 proof and relevant historical comparison. Preserve source/Git binding, actual environment, commands, results and overlapping wall-time accounting. Existing independent gates may run concurrently in separate processes/roots. Do not predeclare test totals, waive gates, delete historical evidence or redesign the runner.

After the scoped contracts and required gates are established, stop optional testing unless a concrete remaining risk requires it.

## 6. Deliver and stop

Deliver the additive authored-submap creature contract, scoped placement/atomicity checks, accurate preview output, complete editable example and sidecar, necessary regression coverage and narrow authoring guidance. Add a concise `docs/owner/GAMEPLAY_G17.md` explaining the supported schema, limitations, controlled proof, compatibility and measured results. Update the repository entry point where needed. Reuse existing evidence machinery; a thin G17 entry point is acceptable.

Commit scoped implementation and source-bound delivery clearly, push under the invoked brief's authorization and verify remote main/checkpoint readback. Preserve unrelated owner work and personal saves.

**Stop after G17.** No native barrow/layout assignment, new dungeon reward, starter redistribution, weighted encounter groups, surface-building actors, spawn director, new actor persistence system, AI/combat overhaul, Stone Lurker/Press repair, new survival supplies, progression/transformation work, wiki rebuild, reference-pack installation or iteration-cost redesign belongs to this task.

The next review should choose the native underground destination and its reward/approaches using this proven authoring route. That later connected-outing proof must carry the real resource costs of the first trip: G16's production return has only 124 torch-burning turns and has consumed the initial flask/jerky. It will need an authentic fresh campaign under any new destination policy, or a checkpoint made under that policy—not a retrofit of the historical G16 witness.

## Baseline sources

- [G16 delivery](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/docs/owner/GAMEPLAY_G16.md).
- [Structure contract](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/structure_contract.py), [special adapter](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/spawn_specs.py), [authored layout generation](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/local_gen.py).
- [Scene population/publication](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/engine/scene_generation.py), [destination entry](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/engine/engine.py), [creature factory](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/engine/creature_factory.py).
- [Production preview](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/structure_preview.py), [existing authoring CLI](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/tools/structure_authoring.py), [authoring guide](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/docs/STRUCTURE_AUTHORING.md).
- [SubMap metadata](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/world/world_map.py), [fresh world assignment](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/world_gen.py), [saved layout IDs](https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/engine/save_manager.py).
