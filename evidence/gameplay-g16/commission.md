# G16 — Scavenged preparation at a furnished workshop

**Issued:** 25 October 2026, America/Edmonton  
**Status:** Next bounded H1 brief; issued, not implemented.  
**Reviewed baseline:** `main`, `d26c6776b20c89c67a9b626bbc82059f50c770e7` (G15).  
**Outcome:** From the ordinary start, the player can reach a naturally selected, furnished workshop, obtain a finite musk gland and usable fuel, prepare one musk pellet through the existing campfire/drying rules, and return to the known starting foothold with that new tactical option.

## Execution instruction

When the owner supplies this brief to Codex for execution, implement and verify **G16 only**, commit the completed scoped changes and push to the existing `origin/main`. Work in the established production checkout on `main`; preserve unrelated owner changes and personal campaigns; create a named checkpoint before substantial edits. Do not create task branches, worktrees or additional development copies. Reconcile intervening commits without resetting an advanced checkout. Never force-push or rewrite unrelated history. Carry forward authorization already supplied in the execution session.

Consult `AGENTS.md` and relevant current guidance. The compass, decisions/state, approved implementation proposal and workflow remain applicable. `RESONANCE_G15_REVIEW_AND_G16_HANDOFF.md` supplies the latest reviewed baseline. This brief does not commission all of H1. Its creation does not itself execute or publish code.

## Why this is next

G15's finite native recovery chain is delivered. H1 now needs an ordinary surface outing that turns scavenging into a preparation worth taking onward. The existing starter kit/laboratory do not supply a musk gland or pellet. G12 already repaired and demonstrated the real gland → stationary fire → pellet → temporary disruption route; G13/G14 supplied native containers and empty-crate salvage.

Use those systems to make one place useful and readable. This is the approved plan's purposeful surface opportunity, with an ordinary-start return trip. Underground encounter authoring and the full two-outing comparison remain later work.

## 1. One versioned, furnished workshop

Create `roguelike/data/buildings/commercial/workshop_b.json` with ID `workshop_b`, derived from `workshop_a`.

Preserve the **12×9 envelope**, double-width southern entrance, grid/roadside contexts, buffer, approach, frontage relation and allowed rotations **0/90/180/270**. Furnish the interior as a small, interrupted preparation workspace using supported existing terrain/decor and a real crate. Keep the entrance, circulation, crate interaction and readable material accessible in every declared rotation. Supply a legal nearby working space for the existing fire/processing route; it can be outside. Do not imply that ordinary scenery supplies a functional workbench or heat source when it does not.

The new arrangement may move its floor objects and required targets coherently. Retain relevant existing readable material/scene where it fits; replace the generic preparation note locally if the new note better serves the room. Keep shared text/scene definitions and `workshop_a` unchanged. Use the supported special-tile/container route, not the old placeholder `interior_loot_table` field as an assumed source of contents.

### Guaranteed, finite contents

One real crate contains:

| Item | Quantity | Role |
|---|---:|---|
| `stalker_musk_gland` | 1 | Existing material for one musk pellet. |
| `wood_bundle` | 1 | One of the two physical fuel inputs for a field campfire. |

Use two dedicated one-roll pools, such as `workshop_b_musk` and `workshop_b_fuel`, each with `roll_count: [1,1]` and its one positive-weight item. Do not make the two goods compete in a weighted draw. No finished pellet is placed in the crate or on the floor.

After both goods are removed, the existing G14 empty-crate action can produce the second wood bundle. That makes the workshop self-sufficient for the selected route with the ordinary starter tool/flame. Other legitimate fuel sources remain valid; do not add a bespoke dependency on dismantling this particular crate.

The crate and contents are generated once. Search, repeated interaction, travel, save/load and revisit do not refill them or recreate a dismantled crate. Normal capacity rejection retains the same item in its source. No new salvage output, harvest rule, item type, recipe or special container code is needed.

### A short, truthful preparation note

Add a readable `research_note` with a new text ID, for example `workshop_musk_notes_b`, through the existing supported item/text route. Its concise, setting-appropriate text should explain:

- A stalker's musk gland can be dried beside a stationary fire into a pellet.
- A carried torch can light a prepared fire, but is not itself the stationary drying site.
- Breaking the prepared pellet briefly disrupts nearby creatures and can provide time to move away.

Keep it consistent with the actual material and effect rules. Do not describe the effect as predator-only, permanent safety, guaranteed escape, or a cure. Do not invent a particular nearby underground destination or a promised encounter that does not yet exist. The note provides useful information; it does not change recipe-known flags, unlock policy, lore canon or the knowledge interface. Put control guidance in the normal feature guide/UI, not development terminology in the fiction.

### Fresh-world selection only

In `roguelike/data/generation/settlement_profiles.json`, replace only:

- `profiles.grid.roles.commercial`: `workshop_a` → `workshop_b`.
- `profiles.roadside.roles.commercial`: `workshop_a` → `workshop_b`.

Retain **weight 1.0, cap 5**, entry order and every unrelated membership. Preserve the G13 shed and G15 apothecary, their pools and shared definitions. No new placement policy, forced target, all-seed nearby-workshop guarantee, starter gift or starting-lab redistribution is commissioned.

## 2. Reuse the actual preparation rules

The ordinary starter crude blade supplies cutting tier 1. The starting tallow torch is lit and has 600 burning turns. The field campfire recipe spends two physical fuel items and retains its cutting tool. Placement and ignition are separate existing actions. Musk preparation consumes one item providing viscous tier 1 and purgative tier 1, uses a stationary burning source and takes the existing **ten processing phases, including placement**. The resulting pellet uses the existing throw/zone rules. [START] [TORCH] [FIRE] [RECIPE] [G12]

Keep those costs, durations, ownership and turn ordering. Do not supply ambient flame as free material, consume the cutting tool, count an extinguished torch, inject the finished pellet or advance processing by a special shortcut. Preserve current active/hot/cold processing behavior and save contracts.

The expected implementation is authored content, narrow guidance and integration evidence. If the real route exposes a small defect directly blocking this outcome, repair only that defect with focused coverage and explain it. If it reveals a consequential new mechanic or larger architecture requirement, deliver the supported analysis and identify the blocker; do not silently expand G16.

## 3. Useful preflight already performed

Native generation at the baseline selected `workshop_a` at `(75,100)` for seed `20261023`, placement `settlement-0-cross-market-lot-1-44-S-0-building`, rotation 0. Its public join is local `(21,21)`. Another workshop occurs at `(76,99)`. Seed `29417` has one at `(104,46)`, near start `(106,46)`. Seed `0` starts at `(30,83)` and its nearest workshop in the sample is `(83,117)`; it has no early-workshop guarantee.

A read-only preflight used the actual laboratory start at `(73,99)`, equipped ordinary starter items, ascended, crossed east/east/south, used the actual starting flask once and reached the primary workshop's public join in **235 turns with 60 HP remaining**. It used real handlers after intercepting the game loop during boot and full-state threat-aware routing. It did not stage the player, alter AI, remove threats or add supplies.

This establishes approach feasibility only. It did not enter the new workshop, process its materials, make the return trip or run the original event loop. Recheck genuine fresh selection after the variant change; content may alter subsequent random draws. Use the candidate to keep the final scenario bounded, not as a hardcoded replacement for native selection. No new large seed campaign is needed.

## 4. Preserve historical campaigns and useful tests

Retain the old workshop definition and dependencies. Do not retrofit the gland, note or furnishing into visited/pending old places, regenerate visited chunks, or migrate existing player possessions.

A genuine existing witness is available:

`evidence/gameplay-g15/final-a/journey/acquisition/acquired-unused.zip`

It contains four selected old workshops, a visited scene at `(75,100)`, and a genuinely pending `workshop_a` at `(76,99)`, placement `settlement-0-cross-market-lot-81-3-S-0-building`. Its SHA-256 is `503309d073b96139a84fc0769ad9eb89fe53b1f1b4c89230d0af318eb20037de`.

Before edits, validate/reuse that archive and capture the pending old-workshop fingerprint through the existing production route. Afterward, compare the saved player/dressing, visited scene, old selection dependencies and pending materialization. Reuse the compact G15 historical-check pattern; do not manufacture an old world after changing the code or make another large archive when this one suffices.

Known intentional test dependencies to recheck:

- `test_gameplay_g13.py`: expected live profiles already include shed/apothecary substitutions; account explicitly for the workshop substitution while retaining the original shed contracts.
- `test_generation_g5_cohort.py`: historical certification of `workshop_a` needs historical profiles, alongside the existing old shed/apothecary cases.
- `test_structure_contract.py` and `test_structure_access.py`: catalogue/candidate counts increase by one if the checkout has no intervening content additions. Derive the actual counts; preserve old and new coverage.

The G15 review observed Python 3.12 versus production Python 3.11 exact-float receipt sensitivity (`6.4` versus `6.3999999999999995`). Use the established production interpreter for final gates. Do not rewrite historical fixtures, round live carrying behavior or absorb cross-interpreter test portability into this feature.

## 5. Autonomous acceptance and verification

Use headless SDL, app-local events, disposable saves and existing helpers. No desktop control or routine owner QA.

### Changed-contract checks

Keep the new tests compact and focused on actual new risks:

1. The new definition validates, is selected through both intended roles and has reachable crate/note/working space in every permitted rotation.
2. Native construction yields exactly one gland and one wood in the real crate. Transfers, depletion and any dismantling persist; no repeated search/load creates a second reward. Reuse established capacity/ownership/salvage tests for unchanged rules.
3. Genuine G15 old-world selection and pending/visited contents are preserved.
4. The exact native gland can be committed into the existing preparation and produces one owned pellet, with materials spent and tools retained. Existing G12 processing and throw/effect coverage supplies the unchanged mechanic contracts; do not duplicate that suite just to restate its implementation.

### One ordinary-start game-loop expedition

Use the established **original `Engine.run` event driver** for one final fixed-seed demonstration. Begin in the real laboratory with ordinary starting inventory and resources. Travel through actual scene boundaries to the naturally selected new workshop. Read the note, acquire the native contents, obtain the second fuel through the existing crate salvage or another actual source, place and ignite a field fire, complete the existing drying process, take the resulting pellet and return alive to the known starting laboratory/entrance area with it.

For the primary proof, retain the finished pellet for the next outing. Normal threat avoidance is a valid decision. Use the already established G12 effect/retreat evidence for its tactical meaning; do not insert an enemy or force a second combat branch merely to lengthen this task. If a naturally encountered use is separately shown, label that branch and its consumption accurately.

Normal AI, FOV, survival, resource depletion and costs stay active. No staging, teleportation, threat clearing, invincibility, synthetic injury/recovery, extra kit, injected fuel/gland/pellet or supply resets in this expedition. Starting equipment, food/water and naturally obtained supplies may be used normally. Disclose full-state scripted route/UI choices and any reproducibility seeds. This is feasibility evidence, not unaided discovery or a guarantee that the foothold is safe.

Record a concise start/acquisition/preparation/return summary: turns, HP, food/water, torch use, possessions, source depletion and major decisions. Capture only the few normal-FOV views needed to inspect the furnishing, readable note and result. If the route fails, diagnose that concrete failure; do not solve it by quietly changing ordinary conditions.

### Persistence without another long itinerary

Use meaningful checkpoints within that same chain. Preserve acquired materials or a real in-progress preparation across a genuinely separate-process cold load, finish through normal rules, then preserve the returned pellet and altered workshop in a final save/cold load. Check depleted/dismantled source state by the existing focused cache/disk revisit route; a second complete walking expedition is unnecessary.

One F9 check is sufficient if used: make an actual ordinary unsaved change and verify restoration of an explicitly named snapshot. Retain existing effect-clock behavior; do not add universal offscreen catch-up. Existing separate-process helpers should carry this evidence.

### Final gates

After narrow development checks and a visible-content/route preflight, freeze the G16 inputs and run the existing unfiltered focused discovery and production-D gates plus this bounded expedition and historical comparison. Preserve source/Git binding and report actual environment, commands, counts, timings and limits. The existing independent gates may overlap in separate processes/roots. No gate is waived, no historical receipt is deleted and no general test-runner/evidence redesign belongs here. Stop optional testing once the relevant risk and required gates are satisfied.

## 6. Delivery and stopping point

Deliver the new workshop, its two finite pools, useful note, two membership substitutions, necessary tests and narrow affected authoring/usage guidance. Add a concise `docs/owner/GAMEPLAY_G16.md` recording the actual player result, version policy, controls/material chain, ordinary-start journey, persistence, measured verification and limits. Update the repository entry point where needed. Reuse existing evidence machinery; a thin G16 entry point is acceptable.

Commit the scoped changes and source-bound delivery clearly, push under the invoked brief's authorization, and verify remote main/checkpoint readback. Preserve unrelated owner work.

**Stop at G16.** Do not add underground population/schema, new combat tactics, Stone Lurker or Press work unrelated to this route, starter-weapon redistribution, more treatment tiers, new recipes, skill/XP changes, discovery-interface replacement, transformation, town/road redesign, mandatory nearby-workshop generation, wiki rebuilding, reference-pack installation or the separate iteration-cost investigation.

The next review should ask what the resulting ordinary outing establishes and choose the next bounded underground/connection task. G16 alone does not complete H1's two connected expeditions, alternative approaches or recovery-balance assessment.

## Baseline source anchors

[G15]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/docs/owner/GAMEPLAY_G15.md
[G12]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/docs/owner/GAMEPLAY_G12.md
[START]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/main.py
[TORCH]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/items/tools/tallow_torch.json
[FIRE]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/recipes/campfire.json
[RECIPE]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/recipes/musk_pellet.json

- [Workshop baseline](https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/buildings/commercial/workshop_a.json) and [selection profiles](https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/generation/settlement_profiles.json).
- [G12 preparation delivery][G12], [G14 salvage delivery](https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/docs/owner/GAMEPLAY_G14.md), [G15 recovery delivery][G15].
- [Existing historical helper](https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/tools/g15_historical.py), [ordinary-input driver](https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/tools/g12_journey.py), and [regression suite](https://github.com/dgobi/ResonanceRoguelike/tree/d26c6776b20c89c67a9b626bbc82059f50c770e7/tools/critical_fix_regressions/tests).
