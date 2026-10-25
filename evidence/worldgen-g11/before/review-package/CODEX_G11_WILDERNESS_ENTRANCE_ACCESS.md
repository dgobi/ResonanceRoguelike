# Codex G11 — Wilderness entrance access and safe returns

**Project:** Resonance Roguelike  
**Repository:** https://github.com/dgobi/ResonanceRoguelike  
**Reviewed `main`:** `7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b`  
**G10 frozen inputs:** `9de7b8ee759dcade97bb992c83d7fb8b26a61eac`  
**Existing checkpoint:** `checkpoint/worldgen-g10-verified-20261024-a`  
**Prepared:** 24 October 2026, America/Edmonton  
**Companion:** `G10_REVIEW.md` and the independent evidence in `Resonance_G11_Review_Package.zip`.

## 1. Implement this player outcome

For the corrected generation route, a player must be able to approach a required wilderness entrance from the surrounding world, enter its submap, return to the surface and leave through a usable exterior connection. Entrance architecture, later dressing and population must not turn a valid approach into a sealed pocket.

Retain G10's coherent wilderness, barren Ash Wastes and existing landscape character. This is a bounded reliability repair serving exploration and trustworthy travel. It does not commission another road-network or terrain-simulation arc.

## 2. Reproduce the current failure before changing it

The independent review found this ordinary generated case:

- Seed `20261023`, Drowned Wood chunk `(44,8)`.
- Cave **Arnevel Vault**, `submap_44_8_0`.
- Before entrance stamping, arrival `(24,10)` reaches 152 cells including 29 boundary cells.
- After stamping, arrival and stair `(14,5)` occupy a 79-cell component touching no boundary. Final dressing/population preserves the separation.
- The stair is unreachable from the union of all exterior-connected components, using the game's eight-way, door-aware, decor-aware static rules.
- The current supported G9 route on the same genuine saved coarse geography has an exterior-reachable stair. This comparison is not a rerun of the historical executable.

The supplied `evidence/access/reproduce_g10_entrance.py` accepts `--repo PATH --out PATH_OUTSIDE_REPOSITORY`. It recreates the production scene, captures the before/after stamp, compares the supported G9 route, and exercises real boundary/stair/save handlers with disclosed fixture positioning. Its exit success means the probe completed; `defect_observed` reports the defect. Adapt it into positive regression coverage rather than treating its present baseline assumptions as a universal final gate.

Reproduce on the established production interpreter. Preserve the failing scene description and small before/after evidence. Do not require an ordinary fresh-start walk across the entire world to reach this remote coordinate.

### Relevant source path

Read the compass and current decisions/workflow if present in the supplied task context, plus `AGENTS.md`, the G10 report and these integration points:

- `roguelike/generation/wilderness.py`: policy, natural component and arrival selection.
- `roguelike/generation/planned_scene.py`: overlay order, required anchors, final access.
- `roguelike/generation/region_gen.py::_place_submap_entrance`: candidate staging and fallback.
- `roguelike/generation/access.py`: existing player static-access semantics.
- `roguelike/engine/scene_generation.py`: completed-scene validation and staged publication.
- `roguelike/engine/engine.py`: boundary crossing, descent, ascent and destination preparation.
- `roguelike/engine/save_manager.py`, generation adapters and the G10 lifecycle tests: saved-route selection and restoration.

The hole is specific: a roadless scene retains only an interior spawn as its required anchor. A candidate entrance can keep spawn and stair connected while cutting both off from every real exterior. Fix that relationship through final composition.

## 3. Preserve a meaningful exterior access obligation

For new worlds using the corrected route, retain an explicit usable exterior witness or an equivalently strong bounded access obligation for required wilderness arrivals/submaps. It must refer to an actual passable edge facing an in-world neighbor and be usable under the existing cross-boundary movement contract. An arbitrary interior point, an outward edge of the finite world, or an edge cell without a legal reciprocal approach is insufficient. Demonstrate the exact regression's reciprocal approach through real handlers without eagerly materializing neighboring scenes during runtime validation.

Determine the obligation with the authoritative water, roads and authored ownership taken into account. Preserve existing road-edge, approach, shared-path, common and entrance obligations. Then carry the required exterior relationship through entrance placement, dressing and final populated-scene validation.

Use existing movement semantics: eight-way movement as currently supported, openable doors and blocking decor. Dynamic actors are temporary occupants rather than permanent terrain walls; do not reject every scene because a living actor momentarily stands on a route. Verify actual handlers separately to catch disagreement with static checks.

Require the selected playable arrival and mandatory submap stairs/return positions to retain their required exterior access. Do not require every natural edge, unrelated clearing or decorative pocket to connect. Do not alter diagonal movement rules, navigation AI or ordinary boundary-position contracts as part of this repair.

Validate the completed scene even if an earlier candidate check succeeded. A later pass that severs required access must fail before the scene is published. Keep diagnostics specific: owner/chunk, required target, access revision and the failed relationship.

## 4. Prefer bounded candidate rejection and reselection

Strengthen the existing staged entrance candidate predicate so a footprint that severs the required exterior relationship is rejected. Continue the existing deterministic bounded search. Keep stable ordering and tie-breaking; preserve source submap IDs, owning chunks, names, types and return/link ownership.

Use the existing bare-stair fallback only when it satisfies the same complete access obligation and has a usable approach. Prefer a different valid footprint to modifying large areas of natural terrain. A necessary small repair must be deterministic, limited to unowned eligible cells, recorded with its reason and changed coordinates, and unable to overwrite protected content. Do not add general terrain routing machinery when the existing candidate/fallback system can solve the problem.

Never hide failure by deleting the submap, changing its identity, marking it visited, teleporting the player past a blockage, disabling the check or treating a generation error as a successful playable outcome. If an injected impossible fixture cannot be satisfied, retain atomic failure/recovery. Ordinary positive samples must actually materialize and work.

Do not change raw wilderness field sampling, installed profile values, macro biome geography, river geometry, G9 plans, road selection, settlements, rural owners, world size or global population/entrance seed domains. Keep `GENERATION_REVISION` at its established domain unless an independently necessary contract change is explained; naming this milestone G11 is not a reason to reseed unrelated systems.

## 5. Make corrected finalization explicit without rewriting campaigns

Rejecting a previously accepted entrance footprint can change a pending scene's stair and architecture even when raw terrain fields are identical. Do not silently represent those changed decisions as the exact historical G10 route.

**Compatibility default for this brief:** add a small, validated saved access/finalization revision for newly created worlds. Preserve the existing field algorithm, profile values and field seed domain. Reuse the current surface-policy/version infrastructure where appropriate; avoid a new general migration framework or unnecessary world-plan format change.

Existing G9 and G10 campaigns retain their supported historical pending-generation route. Existing visited scenes, player modifications, item/container ownership, actors, links and return coordinates remain authoritative and must not be regenerated or repaired in place. Missing/invalid new-contract fields must not silently select an old route.

Before changes, capture a genuine small G10 checkpoint with visited mutable state and representative pending wilderness/entrance scenes. Record their current fingerprints. Verify historical visited state and pending output through the retained route, including ordinary load and F9. Keep the authentic G9 tests passing.

Be explicit about the tradeoff: this repair applies to new worlds selecting the corrected access revision. Old-route pending scenes can retain the known defect. Do not claim an old campaign is upgraded, and do not automatically rewrite its pending policy. An existing-campaign upgrade or visited-scene rescue is a separate owner decision, outside this brief.

New-policy save/load must retain the corrected access revision and reproduce its pending entrance decisions independently of installed tuning changes. Validate the new discriminator and scene provenance through existing atomic preparation, with a meaningful malformed/missing-contract negative and recovery. Preserve the G9 plan identity and all unrelated seed domains.

## 6. Demonstrate the repaired journey

Use the exact `(44,8)` case on the corrected route for the primary positive:

1. Establish a normal generated neighboring scene and a usable matching approach. Disclose any initial test positioning in that neighbor.
2. From the first boundary movement onward, use real movement/door/stair handlers to enter the target chunk, walk to its actual entrance, descend, ascend, walk back out and cross to the neighboring scene. Do not reposition inside the target or submap to make the path succeed.
3. Keep native actors, normal FOV, AI, survival and normal inventory rules. No invincibility, actor removal, injected supplies or restoration of health/thirst. A short known-seed script is sufficient; it does not need to prove unaided discovery or overall survival balance.
4. Preserve a real small mutation from the outing through a naturally generated interactable or an ordinary starting-inventory action, such as consuming the starting water flask, and save the exercised state. Do not inject an object or add content merely to supply a mutation. If a separate controlled persistence fixture is needed, label it separately from the access journey.
5. F5-save, cold-load and F9-restore the actual result. Verify terrain, target/link ownership, return position, actors, inventory/mutation and a subsequent pending corrected-route scene.

Capture production-rendered normal-FOV views of the approach, entrance and return/exit. Separately label any revealed comparison. The preceding fixture positioning is a controlled access demonstration, not a normal-start expedition. Also replay the short existing G10 normal-start excursion to protect that separate ordinary-play claim; no long G9 itinerary is required.

## 7. Verify the actual failure class, proportionately

| Check | Required outcome |
|---|---|
| Exact regression | The ordinary Arnevel Vault case is reachable from a real exterior approach after complete composition; the real approach–descend–return–leave sequence succeeds. |
| Discriminating negative | A compact fixture where spawn and stair remain mutually reachable while a later footprint severs their exterior route defeats the old validator and is rejected by the new one. A late-pass variant demonstrates final validation rather than only candidate validation. |
| Placement fallback | A bounded alternative-placement/fallback case preserves mandatory access and owner identities without flattening the biome. Include multiple required links when they materially exercise preservation of prior entrances. |
| Representative scenes | Replay the supplied 60-scene discovery sample on the corrected route. Add only a small targeted set needed for road-connected access, river/protected ownership and an in-world edge case. Record selection and do not present the sample as a world-prevalence estimate. |
| Unchanged generation | Raw field/base decisions remain unchanged for the compared policies; complete G9 macro plans/coarse ownership retain the three existing ordinary-seed identities. No eager neighbor scene generation is introduced. |
| Historical preservation | Genuine pre-edit G10 visited/mutated and pending witnesses plus inherited G9 contracts pass through their explicit old routes. A legacy witness passing is not evidence of repaired legacy access. |
| Atomicity | An injected late exterior-access rejection leaves active world/player, cache, RNG, checkpoint files and HEAD unchanged; removing the fault permits a playable retry. |
| Save contract | Corrected policy/provenance is durable; malformed/missing new contract rejects without downgrade or partial installation. |
| Ordinary play | Existing short G10 normal-start excursion still succeeds with its controls disclosed. |

Use focused behavioral tests for the changed predicate, final validator, policy dispatch and actual handlers. Do not add a new generic generation-verification framework. Keep the added work bounded by a local scene and fixed metadata; record modest before/after scene costs to catch excessive retries, not a new benchmarking campaign.

Run the expanded relevant focused suite and the established unfiltered production gate once against final frozen runtime/test inputs. Run additional gates only when changed inputs or a concrete failure makes them relevant. Preserve the existing `E04 / UI-TEXT-HEIGHT` deferral; this task neither fixes it nor weakens its current reporting. Do not copy the G9 multi-gate/wiki release sequence.

If final runtime/test inputs change after verification, rerun affected checks and required final gates against the new inputs. Record exact commands, environment, results and the tested commit/input identity. Codex owns routine verification, including headless/app-local execution and guarded disposable saves; no desktop takeover or routine owner testing assignment.

## 8. Delivery and stop

Work in the owner's existing production checkout on `main`. Record HEAD/status/remotes, preserve unrelated owner work and create uniquely named starting/final checkpoints. If main advanced, inspect and record the difference; do not reset it to the reviewed commit. No task branch, worktree, second development checkout or PR.

When the owner supplies this brief for implementation, scoped delivery includes commits and verified publication to the existing remote `main`, with immutable unique checkpoints and remote readback, subject to any more specific instruction in that execution session. Do not force-push, move old tags or amend unrelated work.

Deliver the implementation, targeted regression tests, a concise `WORLDGEN_G11.md`, a small clarification to the authoritative wilderness guide about access and historical-route behavior, and one compact source-bound evidence package. Keep the genuine compatibility witness and actual before/after/access evidence; avoid duplicate historical archives and disposable save directories. Use Markdown and machine-readable receipts.

**Wiki maintenance is excluded.** Preserve the current owner wiki and existing separate-commission rule. This is not a reference-pack refresh gate.

Stop when the corrected route preserves usable wilderness entrances through final composition, the exact failure and a meaningful second case are covered, real round-trip access works, historical/visited contracts are protected, and the required verification/publication agrees with the delivered source. Further terrain tuning, roads, new POIs, reader UX, progression, survival balance, save migration and existing-world rescue remain separate work.
