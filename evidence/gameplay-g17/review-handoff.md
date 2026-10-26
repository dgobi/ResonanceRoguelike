# Resonance — G16 review and G17 handoff

**Reviewed:** 25 October 2026, America/Edmonton  
**Delivery:** `main`, `5ae5d1356bd5f37e442694c664354f79096c8e38`  
**Certified implementation inputs:** `1856700882260e9a2734b05df1953c4da76e1959`  
**Previous reviewed baseline:** G15, `d26c6776b20c89c67a9b626bbc82059f50c770e7`  
**Next issued brief:** `CODEX_G17_AUTHORED_SUBMAP_CREATURES.md` — issued, not implemented.

## Review conclusion

**G16 delivers its commissioned ordinary-start workshop expedition. No material gameplay defect or scope blocker was found.** The player can obtain the native materials, prepare a musk pellet through existing rules and bring it back to the original laboratory. This advances H1 from local interaction proofs to a complete, useful surface outing.

The unchanged original-game-loop journey independently passed during this review. It returned with one unspent pellet at 60 HP after **472 saved-timeline turns**. The committed production run reports **476 turns**; these are separate observations, not an exact replay claim. The full production gates were not rerun.

Two nonblocking evidence qualifications are retained: the known cross-interpreter derived-load comparison fails unchanged in this review environment, and the journey stage records leave a default `completed:false` field despite explicit successful completion assertions. Neither is evidence that the commissioned expedition failed.

**G17 should complete the narrow authored-creature capability for underground layouts, with one concrete example and production-path persistence proof.** The approved plan explicitly permits splitting H1's underground package at this dependency. Native destination selection, meaningful rewards and the connected second outing should follow after that contract is demonstrated.

## 1. Scope and source basis

This review used the attached compass, decisions/state, approved implementation proposal and workflow; the exact issued G16 brief; both G16 commits; the completion record; relevant changed data, tests and helpers; and the committed verification artifacts. It also inspected the specific underground authoring/runtime paths needed to choose G17.

The existing review checkout was advanced to the pushed G16 revision. No game source, tests, committed evidence, personal campaign or wiki was edited. This is a milestone review, not another whole-project/chat/archive audit. The approved strategic research remains the reference; no comparison-game execution or new broad research campaign is claimed.

## 2. What the player and author gained

G16 makes the workshop's contents explain a useful action. Its crate holds one native musk gland and one wood bundle. Emptying and dismantling the crate supplies another physical wood bundle; the player can spend the two bundles on a field campfire, light it using the starter torch, dry the gland and take the finished pellet home. The note explains stationary heat and the pellet's temporary effect without promising safety or introducing an unlock. [G16] [WORKSHOP] [MUSK-POOL] [FUEL-POOL] [NOTE]

| Commissioned property | Reviewed delivery |
|---|---|
| A believable furnished place | Tables, hanging cloth, worn surfaces, retained readable material and scene, a real crate, clear circulation and working space. |
| Finite useful contents | Two independent one-roll pools guarantee one gland and one wood bundle; no prepared pellet is stocked. |
| Existing mechanics reused | Actual salvage, physical fuel consumption, separate placement/ignition, ten-phase drying and ordinary pickup. |
| Fresh-world versioning | Only the two grid/roadside commercial memberships switch to `workshop_b`, retaining order, weight 1.0 and cap 5. |
| Historical preservation | `workshop_a`, shared definitions, visited scenes, old pending assignments and saved possessions remain supported. |
| Ordinary-start return | Real laboratory departure, native workshop acquisition/preparation, and return with the unspent pellet. |
| Proportionate implementation | No gameplay-runtime mechanic, item, recipe, save schema or generation algorithm changed. |

Sources: [G16], [WORKSHOP], [PROFILES], [TESTS], [DIFF].

The shared journey helper gained optional caller-supplied frame/time/turn limits so the longer trip could use the existing driver. Previous defaults remain 200 frames, 90 seconds and 80 turns. This is a narrow harness adjustment; it does not relax the existing gates or change game time. [DRIVER] [STAGES]

The authoring result also matters: another useful furnished place was created through the supported data route without bespoke gameplay code. G16 therefore supports the approved plan's requirement that content become practical to produce, within this surface-content scope.

## 3. Verification, separated by evidence type

### Committed production results

The delivery records Windows x64, CPython 3.11.0, pygame 2.6.1, tcod 19.3.0 and NumPy 2.4.6. [G16] [RELEASE]

| Check | Recorded result | Recorded elapsed time |
|---|---|---|
| Unfiltered focused discovery | 278/278 tests pass | 30m 58.4s, including runner overhead |
| Production D | 3,676/3,676 accepted assertions; 159 valid workers | 15m 35.6s |
| Genuine G15 historical comparison | Exact agreement | 2.3s |
| Ordinary-start expedition and cold loads | Pass; pellet returned unspent | 34.6s |
| Final verification wall time | 31m 35.6s | Focused and production gates overlap |

These are source-bound production results, not this review's rerun totals. Final verification wall time is not total development time. The increased duration relative to G15 does not establish a regression without controlling workload and environment. It does reinforce the value of keeping development checks focused and the already-approved iteration-cost investigation separately bounded. G17 does not absorb that investigation or waive gates.

The independent evidence audit reconciled **795 source/Git bindings**, **90 indexed artifacts**, **12,890 ordinary-worker imported-source entries**, the focused log and production totals. Artifact comparisons explicitly accounted for CRLF/LF line endings. All seven runner negative controls reject. The 159 workers comprise 146 ordinary workers and 13 intentional crash workers; their counts reconcile. All 18 protected path groups remain unchanged, including runtime mechanics, recipes/items, historical evidence and the wiki. [RELEASE] [AUDIT] [INDEX]

### Independently executed checks

Review environment: Linux x86_64, CPython 3.12.14, pygame 2.6.1, tcod 19.3.0 and NumPy 2.3.5. Checks used dummy SDL, disposable saves and outputs outside the repository.

| Independent check | Actual result |
|---|---|
| Complete `test_gameplay_g16` module | **Three passes, one historical-comparison failure**, 25.643s |
| Unchanged `tools/g16_journey.py` | **Pass**, 46.215s |
| Committed source/artifact binding | All inspected bindings and indexed artifacts reconcile |
| Receipt-only historical diagnostic | Complete observation otherwise agrees exactly after isolating the derived-load calculation |

The three passing focused tests cover four-rotation access/working space, native materials and ten-phase processing/depletion, and membership preservation with both intended contexts and native primary selection. The original historical test result remains failed in this environment; the diagnostic is not substituted for it.

### The independently observed expedition

| Milestone | Independent turn | HP | Torch turns used |
|---|---:|---:|---:|
| Actual laboratory start | 480 | 60 | 0 |
| Both native crate materials owned | 717 | 60 | 237 |
| Gland committed; nine drying phases remain | 729 | 60 | 249 |
| Finished pellet picked up | 740 | 60 | 260 |
| Same laboratory reached with pellet | 952 | 60 | 472 |

The real crate was emptied and dismantled once. Its native wood and the salvaged wood were spent on the fire; the exact gland was spent on the preparation; the cutting tool remained owned. The starting flask and jerky were used normally on return. The final inventory retained the torch, blade, jacket, talisman, found note, one unspent pellet and the empty water skin.

The intermediate save contained real drying with nine phases remaining. A separate original-game-loop process restored that snapshot, completed processing normally and returned to the laboratory. F9 followed an actual unsaved wait and restored the named drying snapshot; the rolled-back phase is excluded from the saved-timeline count. A third process loaded the returned state and read the saved workshop with generation forbidden: the crate was absent and no gland, wood or pellet had been recreated. Focused cache/disk revisit also passed.

The independent furnished-room, complete-note and laboratory-return views were visually inspected. Their presentation is coherent and readable at the tested dimensions. Normal AI, FOV, survival and costs remained active. Full-state route/UI choices and gameplay RNG seeding are disclosed. This establishes the selected ordinary-start chain, not unaided discovery or complete simulation replay. [JOURNEY-CODE] [JOURNEY]

## 4. Nonblocking findings

### F1. Known derived-load comparison sensitivity

The historical check fails at `tools/g16_historical.py:31` because the review's Python 3.12 calculation returns `5.7`, while the retained Python 3.11 receipt stores `5.699999999999999`. Every other initial snapshot field, including the player/world/scene digests, matches. The unchanged effective item weights reproduce the historical value when accumulated left to right.

An external diagnostic changed only that calculation in the returned receipt. It changed no item, inventory, game/save code, source, fixture or digest. The complete historical observation then matched: **51 placement dependencies, four old workshops, the pending old-workshop fingerprint, no gland backfill, and the saved visited scene/player/unused dressing**.

Disposition: retain the existing production interpreter for production gates; preserve the raw failure and separate diagnostic. Cross-interpreter receipt portability remains a distinct verification improvement. Do not round live carrying behavior, rewrite historical fixtures or expand G17 to silence it. [HISTORICAL]

### F2. A stale completion field in journey receipts

Both G16 stage records retain `completed:false` from the shared evidence object's default, while `passed:true` and the explicit `original loop completed bounded driver` assertion are true. The driver checks action-generator exhaustion, and the final return/cold-load checks completed successfully. `run_stage` sets `passed` but does not set the legacy completion field. [DRIVER] [STAGES] [JOURNEY]

Disposition: nonblocking metadata inconsistency. New completion records should agree with their actual completion assertion. Preserve the historical records; no full gate rerun or separate repair arc is justified solely by this field. It does not imply that the expedition was unfinished.

## 5. What remains before H1 is complete

G16 proves a particular feasible surface trip. It does not establish universal workshop availability, human discoverability, the pellet's usefulness in a second native outing, recovery balance or a populated underground destination. Both journeys returned at 60 HP, and neither includes an assessed recovery-from-error case. This delivery therefore does not establish recovery balance.

**The returned resource state must matter.** The committed run leaves only **124 torch-burning turns**; the independent run leaves **128**. The starting food and water have been consumed. The next connected outing must use that state or obtain supplies through normal play. Restarting with a fresh 600-turn torch and full starter rations would not demonstrate the approved two-outing loop. [G16]

This is a dependency for the later native destination and integration task, not a G16 failure. Those tasks should check a practical route, obtainable light/supplies, a useful payoff and an alternative response to the selected encounter together.

## 6. Why G17 should address authored creatures first

The approved plan's underground package identifies a supported creature-special contract as a prerequisite and permits splitting it from the native destination. Source inspection and a small read-only probe confirm that the dependency remains real:

| Current boundary | Observed limitation |
|---|---|
| Structure compiler | `Validator.special()` rejects a direct authored creature record. |
| Special-record adapter | `resolve_special()` also rejects it before layout translation. |
| Internal population path | Can create creatures, but currently accepts duplicate actor cells and blocking decor in the controlled probe. |
| Preview | Diagnoses some bad occupants after construction; it does not supply the needed runtime rejection before publication. |

Sources: [CONTRACT], [SPECS], [SCENE], [PREVIEW]. The probe produced two Hollow Revenants on the same cell occupied by blocking crate decor through the internal population path. This is a controlled capability test, not a claim that G16 naturally generated that defect.

G17 should therefore expose **one direct creature record in an authored underground layout**, create it through the existing factory, reject invalid initial placement before publication, and prove normal encounter persistence. This gives the owner a usable content capability and a concrete example; it does not require an encounter director or engine rewrite.

The boundary should remain `authored_submap`. Surface structures have additional placement-receipt and dependency contracts that are not yet actor-aware. Enabling creatures everywhere would pull those unrelated systems into this task. Authored submaps currently support centering/translation, not a general rotation/mirroring contract. [PLACEMENT] [PREVIEW] [LOCAL]

The complete brief specifies one editable example under `roguelike/docs/examples/`, a matching access sidecar, the existing preview command, and one controlled production-game-loop encounter with live-state and defeated-state cold loads. The example is not placed in the live world or registered as a new campaign destination.

## 7. Preserve the distinction between authoring and native selection

`SubMap.layout_id` already persists. Current ordinary dungeon assignments leave it blank; the starting laboratory has the existing authored ID. A later native-destination brief should assign a new, versioned layout ID during fresh-world creation. It must not reinterpret every old blank-layout barrow when first visited. That would retrofit historical pending BSP destinations. [WORLD] [WORLDGEN] [SAVE] [LOCAL]

The genuine G16 returned-pellet archive is suitable for historical checks. Its pending `submap_73_97_0` at `(73,97)`, type `barrow`, seed `107361`, has blank `layout_id` and `generated:false`. Its displayed name differs from its type; use actual metadata identity, not name text, in checks.

A future two-outing proof should run a fresh campaign under the new destination policy, or use an authentic checkpoint created under that policy, carrying actual resources through both outings. The old G16 checkpoint is a preservation witness; it cannot silently become a world with a newly selected destination.

## 8. Current state and next handoff

| Item | Status after this review |
|---|---|
| Approved implementation path | Unchanged; H1 remains active. |
| G15 finite recovery | Delivered; prior review remains applicable. |
| G16 surface preparation expedition | Delivered and reviewed; commissioned outcome supported. |
| G17 authored-submap creature capability | Concrete bounded brief issued; not implemented. |
| Native underground destination/reward | Next candidate after the G17 review; not commissioned by this brief. |
| Full connected outings, alternative response and recovery assessment | Still required for H1 completion. |
| Deferred progression/origin/death/transformation policies | Remain deferred. |

Give Codex `CODEX_G17_AUTHORED_SUBMAP_CREATURES.md` for implementation. This dated review records the changed baseline, findings and next brief. The compass, approved strategic path and workflow need no strategic rewrite for this milestone; reference-pack and wiki maintenance are not added to the implementation gate.

## Source register and reproduction

All repository links are pinned to the reviewed G16 delivery. The exact G16 brief and attached reference pack are the scope sources. Independent review artifacts are under `research/g16_review_code.*`, `research/g16_review_historical_*`, `research/g16_review_evidence/` and `research/g17_scope_*` in the review workspace.

Focused run, from the review checkout:

```bash
env SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYGAME_HIDE_SUPPORT_PROMPT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=20261020 PYTHONPATH=roguelike:tools:tools/critical_fix_regressions/tests /tmp/resonance-plan-venv/bin/python -m unittest -v test_gameplay_g16
```

The same environment/interpreter ran `-X utf8 tools/g16_journey.py --evidence /workspace/scratch/ea0eedaa4952/research/g16_review_evidence/journey`. These identify independent review conditions; they do not change the production interpreter or its release commands.

[G16]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/docs/owner/GAMEPLAY_G16.md
[DIFF]: https://github.com/dgobi/ResonanceRoguelike/compare/d26c6776b20c89c67a9b626bbc82059f50c770e7...5ae5d1356bd5f37e442694c664354f79096c8e38
[WORKSHOP]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/data/buildings/commercial/workshop_b.json
[MUSK-POOL]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/data/loot_pools/workshop_b_musk.json
[FUEL-POOL]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/data/loot_pools/workshop_b_fuel.json
[NOTE]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/data/texts/world/notes/workshop_musk_notes_b.json
[PROFILES]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/data/generation/settlement_profiles.json
[TESTS]: https://github.com/dgobi/ResonanceRoguelike/tree/5ae5d1356bd5f37e442694c664354f79096c8e38/tools/critical_fix_regressions/tests
[DRIVER]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/tools/b1_journey.py
[STAGES]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/tools/g12_journey.py
[RELEASE]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/evidence/gameplay-g16/final-a/release.json
[AUDIT]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/evidence/gameplay-g16/audit.json
[INDEX]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/evidence/gameplay-g16/artifact-index.json
[JOURNEY]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/evidence/gameplay-g16/final-a/journey/journey.json
[JOURNEY-CODE]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/tools/g16_journey.py
[HISTORICAL]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/tools/g16_historical.py
[CONTRACT]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/structure_contract.py
[SPECS]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/spawn_specs.py
[SCENE]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/engine/scene_generation.py
[PREVIEW]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/structure_preview.py
[PLACEMENT]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/placement.py
[LOCAL]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/local_gen.py
[WORLD]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/world/world_map.py
[WORLDGEN]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/generation/world_gen.py
[SAVE]: https://github.com/dgobi/ResonanceRoguelike/blob/5ae5d1356bd5f37e442694c664354f79096c8e38/roguelike/engine/save_manager.py
