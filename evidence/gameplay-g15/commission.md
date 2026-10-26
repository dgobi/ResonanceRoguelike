# G15 — Finite recovery from scavenging

**Issued:** 25 October 2026, America/Edmonton  
**Status:** First implementation brief under the approved H1 path; not yet implemented.  
**Reviewed baseline:** `main` at `6b101d43389dba775b78cf4415c0ef638026f73c` (G14).  
**Goal:** Let the player find one finite treatment in a believable native place and use it to recover health through ordinary controls, with truthful costs and persistent depletion.

## Execution instruction

When the owner supplies this brief to Codex for execution, implement and verify **G15 only**, commit the completed scoped changes and push them to the existing `origin/main`. Work in the established production checkout on `main`, preserve unrelated owner work and personal campaigns, and create a named checkpoint before substantial edits. Do not create task branches/worktrees or reset an advanced checkout to this baseline. Reconcile intervening commits before proceeding; carry forward authorization already given in the execution session. Never force-push or rewrite unrelated history.

Consult `AGENTS.md` and relevant current guidance. The owner approved the implementation path on 25 October 2026; do not ask again whether finite recovery is wanted. The compass, updated decisions/state, approved proposal and workflow provide context. This file supplies the immediate specification and stopping point. Its creation does not itself execute or publish code.

## Why this task comes first

G12–G14 established useful equipment, stocked containers and a physical salvage-to-fire chain. The current game has `_use_heal_minor`, but no shipped item invoking it in the reviewed catalogue. Repeated expeditions therefore need a small, obtainable recovery option before recovery balance can be assessed honestly.

An existing apothecary already has a real medicine chest and ordinary settlement selection. Reuse that route. This brief completes one acquisition-to-effect chain; it does not attempt to complete H1's two expeditions.

## 1. One concrete treatment

Add one definition under `roguelike/data/items/consumables/`:

| Field | Specification |
|---|---|
| ID | `herbal_dressing` |
| Display name | Herbal Dressing |
| Category | `consumable` |
| Existing use handler | `heal_minor` |
| Restoration | `heal_amount: 12`, clamped to current maximum HP |
| Weight | `0.1` kg |
| Stackability | `false`; one physical dose per item instance |
| Appearance | Reuse the existing `generic_item` tile; no new asset pipeline |
| Other effects | None: no food/water gain, exposure reduction, timed regeneration, empty vessel or XP |

Use a terse, setting-appropriate description that identifies a prepared herbal dressing and clearly states the up-to-12-HP, single-use effect. Use the existing detail panel and feedback; retain the current broader HP-display policy. No new ingredient keywords or tool qualities are required. Preserve existing unrelated item properties and tag/quality behavior.

Twelve HP is the initial tuning value, one fifth of the current 60-HP starting maximum. It is not a claim of final recovery balance. Keep it data-driven; do not spend this brief on a parameter sweep or introduce several treatment tiers.

## 2. One believable native source

Create `roguelike/data/buildings/commercial/apothecary_b.json` with ID `apothecary_b`, derived from `apothecary_a`.

- Preserve its 11×8 envelope, terrain/decor arrangement, entrance, required targets, permitted rotations `[0,180]`, buffer, approach and grid/roadside contexts.
- Keep the medicine chest at authored `(1,1)`, with its existing `alchemist_reagents` pool. Append a new dedicated pool, such as `apothecary_b_treatment`, containing only `herbal_dressing`, with `roll_count: [1,1]` and positive weight.
- Preserve the other two containers and their existing pool rules. The additional guaranteed dose must not compete with or replace an existing reagent roll.
- In `data/generation/settlement_profiles.json`, replace only the `apothecary_a` membership in `profiles.grid.roles.commercial` and `profiles.roadside.roles.commercial` with `apothecary_b`. Retain weight `1.0`, cap `5`, and other entries.
- Retain `apothecary_a`, shared `alchemist_reagents`/`alchemist_shop` pools, `medicine_chest` decor and the G13 shed content unchanged. Existing campaigns must keep their old selections and contents. Do not retrofit treatment into old containers or regenerate visited maps.

Each selected new apothecary has **one dose**, generated once as part of its real contents. Searching again, leaving, loading or revisiting must not replenish it. No all-seed nearby-apothecary guarantee, new placement policy, forced target insertion or starter-inventory gift is commissioned.

### Bounded source preflight already performed

Read-only native generation at the baseline selected an apothecary near each of three starts:

| Seed | Starting chunk | Candidate apothecary chunk |
|---|---|---|
| `20261023` | `(73,99)` | `(75,100)` |
| `0` | `(30,83)` | `(32,84)` |
| `29417` | `(106,46)` | `(104,47)` |

For `20261023`, the candidate is `settlement-0-cross-market-lot-42-66-N-0-building`, rotation 180, with public join local `(61,21)` in `(75,100)`. Recheck actual fresh selection after the replacement; do not hardcode this placement as a guaranteed target. This preflight establishes selection/proximity only, not traversal, discoverability or survival. A small recheck is sufficient; no new world-generation campaign is required.

## 3. Truthful treatment use and time

Use normal inventory selection and the existing item/fighter/transfer paths.

**Successful use:** an owned, live treatment selected by a living injured player restores `min(12, max_hp - hp)` at the effect boundary, consumes exactly that selected instance once and completes one ordinary inventory action. Other items and equipment remain intact. Native AI, effects and survival then follow the established turn ordering. Message the actual restored amount.

**Rejected use:** at full health, with a stale/no-longer-owned treatment selection, or without a valid living fighter, change no HP, item ownership or world time. Give a clear relevant message. Closing the inventory without using the treatment remains free.

**Known implementation trap:** `_use_heal_minor` currently returns `True` even if healing is zero. `InventoryScreen.handle_key` then consumes the item and advances time. The `ItemSystem.use()` boolean is not a universal action-success result: reading and equipment can legitimately return `False` after an action. Implement the smallest treatment-specific eligibility/rejection path; do not reinterpret every false return, rewrite all item-use APIs or introduce a general action framework.

`ItemFactory`, `Fighter.heal`, exact-instance consumption and save serialization already support the necessary fields. No new save schema, corruption system, delayed-healing activity or generic medicine framework is needed. Preserve current movement debt and other inventory-action semantics. A focused exact-one-turn assertion should use a debt-free fixture; do not erase existing debt in live play.

## 4. Preservation and existing test dependencies

Before editing, identify a genuine existing G14 checkpoint with old selected apothecaries. The retained `evidence/gameplay-g14/final-a/journey/shed/dismantled-checkpoint.zip` is a candidate. Reuse it if it covers the claim; otherwise capture one compact genuine pre-edit checkpoint. Do not fabricate historical evidence after the change or touch personal campaigns.

Demonstrate that a historical world keeps its old placement dependencies and that an old pending apothecary still materializes through its original route, without the new dose. Preserve visited/depleted contents. Existing fixtures and old evidence remain intact.

Three current tests contain selection assumptions that the intentional new membership affects:

- `test_gameplay_g13.py`: its live-profile expectation includes only the prior shed swap. Account for the intentional apothecary change while retaining the shed's geometry, ownership and reward checks.
- `test_generation_g5_cohort.py`: historical input is selected specially for `tool_shed_a`; the old apothecary also needs explicit historical input for its old-asset certification.
- `test_generation_g5_interactions.py`: it searches a current-generated plan for `apothecary_a`. Bind the historical contract to historical input, or deliberately test the new current asset while retaining separate old-asset compatibility coverage.

Do not remove assertions or rewrite saved fixtures merely to make the membership change pass. Recheck these dependencies against the actual checkout rather than relying on line numbers.

## 5. Autonomous verification

Use the established production interpreter, headless SDL/app-local input, disposable save roots and existing helpers. No desktop control or routine owner QA.

### Focused contracts

Cover the material changed risks with a compact test set:

- Full and near-full injured use: clamped healing, exact selected dose consumed, other possessions preserved, ordinary action cost.
- Full-health, stale-selection and missing/dead-fighter rejection: no consumption, healing or time. Existing reading/equipment behavior remains unchanged by the narrow rejection handling.
- Native chest generation: one dose, existing pool rules retained, real access in both allowed orientations; repeated search yields no additional dose.
- Capacity-rejected acquisition leaves the same dose in the chest; later valid transfer yields that instance once.
- Save/load and revisit retain remaining ownership, restored HP and depleted source; consumed treatment is not recreated.
- Genuine historical selection/dependency behavior remains supported.

Use existing coverage where it already proves an unchanged contract. Avoid creating a second suite that mirrors implementation details.

### One bounded game-loop demonstration

At a normally selected new apothecary, use ordinary movement, search, transfer and inventory controls to acquire and use the native dose, then leave/return and exercise persistence. Capture concise normal-FOV views of the acquisition, readable item detail and use result.

One disclosed initial staging at the genuine public approach is permitted to keep this local demonstration bounded. If ordinary native damage is impractical to arrange reliably, one clearly disclosed setup injury is permitted before the action sequence. It must be separate from normal-play balance claims. Do not insert the treatment, clear threats, disable AI/survival, enable invincibility, reset supplies during the route, reveal normal-play images or reposition inside the destination.

Record HP at the effect boundary and after the normal turn; subsequent native damage can change the latter. Save the acquired-but-unused state, cold-load it in a genuinely separate process, use the dose, and save/cold-load the consumed/healed state. Before F9, make a deliberate ordinary unsaved change, such as one legal movement, then assert restoration of the explicitly identified saved snapshot. Reloading an already identical state is insufficient rollback evidence. Reuse the established journey/checkpoint machinery. A source cache/disk revisit check may be focused rather than another long journey.

This is acquisition/use/persistence evidence. Do not label it full normal-start discovery, recovery balance or completion of H1. The complete two-outing proof remains later work.

### Final gates and evidence cost

Run the existing unfiltered focused regression discovery and unfiltered production-D gate against frozen G15 inputs, plus the bounded G15 demonstration and relevant historical compatibility. Preserve the established source/Git binding and report actual counts, environment and wall time; do not predeclare a new test total. Existing gates may run concurrently only in independent processes with separate disposable roots, as already supported.

Use narrow development checks and preflight the item text, data and visible result before expensive final runs. Reuse current verifiers; a thin G15 entry point is acceptable if needed. This task does not redesign the test harness, waive gates, consolidate history or commission the broader iteration-cost investigation.

## 6. Delivery and stopping point

Deliver the treatment, dedicated pool, new apothecary variant, two selection substitutions, narrow use-path correction and necessary tests. Update only the affected authoritative usage/data guidance. Add a concise `docs/owner/GAMEPLAY_G15.md` completion record with source revision, controls/effect, acquisition/version policy, measured results, staging/setup disclosure and remaining limits. Update the repository entry point where needed to identify the delivery.

Keep evidence source-bound and proportionate. Preserve historical receipts; do not recopy the entire old evidence tree. Commit scoped implementation and delivery records clearly, push to the existing remote under this invoked brief's authorization, and verify the remote revision. Preserve unrelated owner changes throughout.

**Stop after G15 is delivered.** No starter-weapon redistribution, underground encounter work, extra treatment tiers, healing recipes, rest/sleep/injury system, blood-healing redesign, XP/perk overhaul, transformation, world/road redesign, wiki rebuild or reference-pack installation belongs to this task. Report any newly discovered material blocker with evidence and scope; do not turn it into a broad autonomous repair arc.

The next ChatGPT review will compare the actual G15 result with H1 and issue the next bounded task.

## Baseline source anchors

- [G14 delivery](https://github.com/dgobi/ResonanceRoguelike/blob/6b101d43389dba775b78cf4415c0ef638026f73c/docs/owner/GAMEPLAY_G14.md).
- [Item use](https://github.com/dgobi/ResonanceRoguelike/blob/6b101d43389dba775b78cf4415c0ef638026f73c/roguelike/engine/item_system.py), [inventory caller](https://github.com/dgobi/ResonanceRoguelike/blob/6b101d43389dba775b78cf4415c0ef638026f73c/roguelike/engine/inventory_screen.py), [factory](https://github.com/dgobi/ResonanceRoguelike/blob/6b101d43389dba775b78cf4415c0ef638026f73c/roguelike/engine/item_factory.py), [saved fields](https://github.com/dgobi/ResonanceRoguelike/blob/6b101d43389dba775b78cf4415c0ef638026f73c/roguelike/engine/save_components.py).
- [Existing apothecary](https://github.com/dgobi/ResonanceRoguelike/blob/6b101d43389dba775b78cf4415c0ef638026f73c/roguelike/data/buildings/commercial/apothecary_a.json), [selection profiles](https://github.com/dgobi/ResonanceRoguelike/blob/6b101d43389dba775b78cf4415c0ef638026f73c/roguelike/data/generation/settlement_profiles.json), [existing regression tests](https://github.com/dgobi/ResonanceRoguelike/tree/6b101d43389dba775b78cf4415c0ef638026f73c/tools/critical_fix_regressions/tests).
