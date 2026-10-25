# G10 review — wilderness character, actual play and one access regression

**Project:** Resonance Roguelike  
**Prepared:** 24 October 2026, America/Edmonton  
**Live branch reviewed:** `main`  
**Reviewed HEAD:** `7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b`  
**Frozen G10 runtime/test/authoring inputs:** `9de7b8ee759dcade97bb992c83d7fb8b26a61eac`  
**Published checkpoint:** `checkpoint/worldgen-g10-verified-20261024-a` (annotated tag resolves to reviewed HEAD)  
**Next issued brief:** `CODEX_G11_WILDERNESS_ENTRANCE_ACCESS.md`

## 1. Decision

**G10 delivers a substantial improvement to the wilderness, and its retained release evidence is authentic. It needs one bounded access correction before its entrance-access outcome can be considered closed.**

The independent review found an ordinary generated cave whose entrance structure cuts its stair off from every edge of the surrounding chunk. The complete populated scene passes the current production validators. This is a concrete obstacle to exploration, not an argument for more road optimization or a more elaborate world simulation.

The next brief is **G11 — Wilderness entrance access and safe returns**. It preserves the G10 terrain work and repairs the final composition contract for the corrected generation route. It does not add destinations, new terrain machinery, survival balancing or wiki work.

The existing text-reader cutoff is also a meaningful player-facing defect, but it remains separate. I have not bundled it into G11 or preauthorized another milestone.

## 2. Sources actually inspected

The review read the supplied project compass first, then the decisions/state record and workflow. It recovered and read the complete issued G10 brief, also retained in the repository at `evidence/worldgen-g10/before/review-package/CODEX_G10_WILDERNESS_CHARACTER.md`.

Current-source coverage included `AGENTS.md`, the G10 completion report and tuning guide, every changed runtime integration file, the two G10 test modules, preview/expedition helpers, relevant access/entrance/save/scene-generation code, and relevant found-text/learning code. Evidence coverage included the artifact index, final-b release and verification records, raw focused and production results, genuine historical fixtures, representative terrain/authoring/lifecycle receipts, production comparison images, ordinary-FOV images and the actual excursion checkpoint checks. The historical generation proposal informed context; the old ZIP uploads were not treated as current source or exhaustively re-audited.

Live remote readback confirmed both `refs/heads/main` and the peeled verified checkpoint at the reviewed commit. The repository's portable external delivery ZIP was not supplied; this review did not certify that ZIP's own archive manifest or external publication receipt. Live readback independently establishes the source publication.

No game source, campaign, remote branch, checkpoint, reference-pack file or wiki was changed. The disposable review checkout remained clean.

### Evidence classes

| Class | Result and scope |
|---|---|
| Source/evidence reconciliation performed in this review | All 741 frozen input paths match the reviewed checkout: 464 exact raw-byte matches and 277 exact matches after the release's documented uniform-CRLF reconstruction. No substantive mismatch or post-freeze change to a frozen input was found. All 21 indexed evidence references reconcile. |
| Retained focused result, audited rather than rerun in full | 238 tests pass; the log has 238 test labels and ends with `OK`. |
| Retained production result, audited rather than rerun in full | 3,675/3,675 checks, 159 workers, unfiltered. Recomputed totals agree. Every separately retained worker result matches its embedded receipt. |
| Independently rerun G10 tests | All nine shipped G10 terrain/lifecycle tests pass. This establishes those tests' behavior, not coverage of every access configuration. |
| Independently replayed ordinary excursion | Pass: 202 movement inputs, 232 turns, 60/60 final health, harvested sulphur-cap fragment, consumed starting flask, return, F5/new-engine load/F9 and pending-scene agreement. |
| Additional independent scene sample | 60 complete scenes materialized using the existing production path; one disclosed sample had an isolated mandatory entrance. This is a targeted defect-discovery sample, not a prevalence estimate. |
| Independent defect reproduction | Stage-by-stage generation, union of all exterior-connected components, a real boundary movement, separate controlled stair return, and F5/F9 reproduce the access problem. |

The independent environment was Linux, Python 3.12.14, pygame 2.6.1, tcod 19.3.0 and NumPy 2.3.5. The retained delivery used Windows, Python 3.11.0 and NumPy 2.4.6. The replay's 202/232 movement/turn totals differ from the retained Windows outing's 190/220. Both satisfy the stated behavioral outcome. The cause of that trajectory difference was not isolated, and this review does not claim identical cross-platform gameplay replay or comparable performance timings.

## 3. What changes for the player

### The wilderness now has recognizable spatial character

The revealed production comparisons show tree stands separated by clear ground, coherent wet areas, broad open vegetation patches, and joined mountain rock masses. Those are useful shapes to move around and read. They improve on independent tile scatter and make forest, wetland, open country and mountain travel look different.

The Ash Wastes change is particularly well aligned with the setting. In the reported ordinary `(72,103)` sample, grass/tall-grass cells fall from 3,368 to 219; the remaining living cover is confined to deliberate transitions. The tested interior has no living trees or harvestable flowers/mushrooms. The result fits the existing barren-land description without new lore or assets. [R1, R2]

The forest is also substantially denser. The reported final `(73,100)` anchor reaches 711 cells out of the scene's 3,440 cells. Dense, impassable stands can create useful boundaries, concealment and detours; that number alone is not a defect. The requirement is that mandatory places remain usable, while decorative pockets may remain disconnected. G10's initial forest-arrival repair addresses one such case, but the newly found later-stamping failure shows the guarantee was not carried through the entire pipeline.

### Actual travel and scavenging work in the demonstrated outing

The retained expedition begins through the normal laboratory start, equips shipped gear, ascends, examines the starting waystone, harvests an off-road plant, crosses four natural boundaries, consumes its starting water through the inventory handler, rejoins the road and returns. AI, survival, weather and normal visibility stay active, and invincibility stays off. Threats appear and are avoided. Its 190 movement inputs and 220 turns are explicitly recorded. [R3]

The independent replay also succeeds. This is useful evidence that the terrain supports a short outing under active gameplay systems, rather than merely looking plausible in a revealed image. The route planner uses full game state to choose paths and avoid actors; that is disclosed. It does not establish what an unfamiliar player would discover or how comfortably that player would navigate.

The excursion ends with the gathered fragment unused. It does not search a building or show a discovery enabling a new preparation. Those are limits of this demonstration, not missing G10 commissions. They matter when choosing future experience work: the terrain now supports travel, but the whole explore–scavenge–prepare–venture loop has not been demonstrated by this one outing.

### Reliability and authoring gains are real

G10 retains the complete G9 plan and macro ownership for the three ordinary seeds, separates terrain from the global `wg9` seed domains, stores a validated surface policy, supports genuine G9 visited/pending reconstruction, and provides a small production-path preview. The nine independent tests pass for the delivered continuity, policy and rollback cases. [R1, R4]

The revised `AGENTS.md` now matches the owner's instruction that wiki upkeep is separately commissioned. The feature has a concise terrain guide; the existing wiki was not rebuilt. [R5]

## 4. Required correction: a cave is isolated by its own entrance structure

**Severity:** blocks normal access to an existing underground destination. No lost inventory, corrupted checkpoint or ordinary walking softlock was observed.

**Reproduction:** world seed `20261023`; Drowned Wood chunk `(44,8)`; cave **Arnevel Vault**, `submap_44_8_0`.

| Stage | Cells reachable from the selected arrival | Reachable boundary cells | Cave stair reachable from any exterior component? |
|---|---:|---:|---|
| G10 terrain before the entrance stamp | 152 | 29 | Stair not yet placed |
| After the entrance stamp | 79 | 0 | No; stair at `(14,5)` |
| Completed dressing and population | 79 | 0 | No |
| Current supported G9 route over the same saved coarse geography | 2,788 | 209 | Yes; stair at `(22,12)` |

The G9 comparison is execution of the current supported legacy route over genuine pre-edit metadata. It is not a fresh run of the historical G9 checkout. The independent handler probe also recreates the G10 scene from a normal fresh game at the same seed, so this is not dependent on inventing an artificial biome patch.

The static check uses the game's existing eight-way access rules, including openable doors and blocking decor. It excludes dynamic actors. The stair is unreachable from the union of **all** exterior-connected components; choosing a different edge does not resolve it. The single native Plague Crow is not the cause.

### Actual travel consequence

A controlled fixture places the player in neighboring `(43,8)` at `(79,1)`. One real right-movement input crosses into `(44,8)` at `(0,1)`. The resulting 87-cell exterior component cannot reach the cave stair. AI/survival are active and invincibility is off.

A separate, explicitly disclosed fixture places the player on the otherwise inaccessible stair solely to exercise the actual descent/ascent handlers. Ascending returns to `(14,5)` inside the sealed 79-cell pocket. F5/F9 preserves that state exactly.

These checks prove an inaccessible cave and an isolated return pocket under controlled placement. They do **not** show that an ordinary player walked into the cave and became trapped: ordinary exterior traversal cannot enter it in the first place. The package retains normal-FOV images of the controlled checks and separately labeled revealed generation views.

### Why the passing checks miss it

1. `wilderness.materialize()` selects a natural component touching an edge before later overlays.
2. `create_planned_surface()` retains the selected spawn and road-edge cells as required anchors. With no road, only the interior spawn remains.
3. `_place_submap_entrance()` accepts a candidate when the stair, spawn and previous links remain mutually reachable. Its walls can cut their entire component away from the exterior while preserving that internal relationship.
4. Final validation checks the same supplied anchors plus roads/sites/placements. This roadless wilderness scene has no final exterior-access obligation.

The existing G10 boundary regression checks the particular forest `(73,100)` sample. It does not test an entrance structure severing a previously valid route. The retained release gates therefore passed honestly while missing an important composition invariant. [R6–R8]

## 5. Assessment against the compass

| Compass concern | Assessment |
|---|---|
| Readable aftermath and particular places | Better wilderness identity and a corrected Ash Wastes mismatch. G10 does not add new site stories. The existing clipped found-text interface remains a separate weakness. |
| Physical discoveries feed expeditions | Harvesting and supply consumption work in the outing. Using the gathered material to improve preparation remains outside its demonstrated scope. |
| Knowledge of the world creates power | Existing waystone learning is exercised, but the outing does not establish an extended discovery/progression loop. No open progression decision is resolved. |
| Believable, connected places | Clear visual progress and working sampled travel. The isolated cave is a direct failure of this pillar and warrants the next bounded repair. |
| Actions are clear and consequences endure | The exercised mutations, supplies and actors survive restoration. That protection also faithfully preserves the isolated scene; persistence cannot compensate for invalid initial placement. |

G10 is a useful advance toward the intended game. Its strongest player benefit is readable travel through distinct terrain. The discovered entrance problem has higher priority than adding further content because it prevents reaching content already present.

## 6. Why G11 stays small

The needed invariant is straightforward: **a required wilderness entrance must remain connected to a usable exterior approach after all generation passes**. The first remedy should be rejection and deterministic reselection of an entrance footprint that severs that connection, using the existing safe fallback where appropriate. The current game already has bounded candidate placement, static reachability and atomic scene preparation; a new general routing framework is unnecessary.

Bob Nystrom's original account of procedural dungeon generation emphasizes that placing a required goal in an unreachable region defeats its gameplay purpose, and treats region connectivity separately from room placement. The applicable lesson here is to preserve actual access to the goal through composition. Resonance does not need to adopt his dungeon algorithm or connect every wilderness pocket. [S1]

The brief explicitly preserves scenery, roads, saved ownership and historical behavior. Because rejecting a formerly accepted footprint can move a pending stair, corrected finalization must have an explicit saved revision. The conservative scope is a corrected route for newly created worlds, with existing G10/G9 routes and visited scenes retained. An automatic upgrade of an existing campaign's pending content is not included. This means old-route pending scenes can retain the known defect; the completion report must state that compatibility limit rather than claiming every old world is repaired.

## 7. Other observations retained without expanding G11

**Readable text:** the final G10 production record still shows the sarcophagus label ending after “If”; its concluding warning includes “do not ring the bells.” Source inspection confirms that the reader sizes from unwrapped first-page text, then drops overflowing rendered lines without within-page navigation. This remains an excellent bounded candidate for a later review. The current gate intentionally records that deferral; it should not be silently removed during an access repair. [R9]

**Authoring error boundary:** syntactically invalid installed profile JSON fails in `DataLoader` before a saved policy can be loaded. The saved-policy tests cover removal and malformed parsed dictionaries, not a JSON parser failure at startup. This is a narrower authoring robustness limit, not observed terrain drift or a reason to expand the entrance task.

**Visual/performance limits:** coarse biome edges, rectangular rivers and dense stands remain visible. The reported timings are bounded samples, not universal latency guarantees. No larger-world, ecology, river, viewport, balance or checkpoint-redesign task is commissioned by this review.

## 8. Handoff and stopping point

Use the companion G11 brief. The review package contains the portable reproduction, stage/handler receipts and images, the 60-scene discovery sample, the independent nine-test result, ordinary-excursion evidence and the release-evidence audit. It omits redundant pickles, disposable campaigns and the repository's enormous historical evidence tree.

G11 should stop when the corrected route rejects the isolation failure, delivers a real approach–descend–return–leave sequence, preserves supported historical/visited contracts, and passes the relevant autonomous gates against its delivered source. Choose further work from that result; this review does not extend the roadmap.

## Sources

- **R1 — Completion:** [WORLDGEN_G10.md](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/docs/owner/WORLDGEN_G10.md).
- **R2 — Production images:** [eight-biome comparison](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/evidence/worldgen-g10/final-b/all-biomes-comparison.png) and [multi-chunk comparison](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/evidence/worldgen-g10/final-b/multi-chunk-comparison.png).
- **R3 — Retained outing:** [expedition.json](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/evidence/worldgen-g10/final-b/g10/expedition/expedition.json).
- **R4 — Final source binding:** [release.json](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/evidence/worldgen-g10/final-b/release.json) and [G10 tests](https://github.com/dgobi/ResonanceRoguelike/tree/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/tools/critical_fix_regressions/tests).
- **R5 — Working rules:** [AGENTS.md](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/AGENTS.md).
- **R6 — Terrain and composition:** [wilderness.py](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/roguelike/generation/wilderness.py) and [planned_scene.py](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/roguelike/generation/planned_scene.py).
- **R7 — Entrance placement:** [region_gen.py](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/roguelike/generation/region_gen.py).
- **R8 — Final validation:** [scene_generation.py](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/roguelike/engine/scene_generation.py) and [access.py](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/roguelike/generation/access.py).
- **R9 — Current text defect:** [production text worker](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/evidence/worldgen-g10/final-b/production/d-20261024-191845-b0b25615/b1-journey-text-loop/result.json) and [text_reader.py](https://github.com/dgobi/ResonanceRoguelike/blob/7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b/roguelike/engine/text_reader.py).
- **S1 — Original implementation discussion:** Bob Nystrom, [Rooms and Mazes: A Procedural Dungeon Generator](https://journal.stuffwithstuff.com/2014/12/21/rooms-and-mazes/), 21 December 2014; consulted 24 October 2026.

The new defect measurements and independent executions are primary evidence in this review package, principally `evidence/access/entrance-isolation.json`, `evidence/access/entrance-handlers.json`, `evidence/g10-tests/receipt.json`, `evidence/expedition/expedition.json` and `evidence/release-audit.json`.
