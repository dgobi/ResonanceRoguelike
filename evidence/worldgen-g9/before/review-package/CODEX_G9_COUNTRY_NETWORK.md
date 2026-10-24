# Codex G9 — Budgeted country-road shortcuts and portable wiki verification

**Project:** Resonance Roguelike.  
**Repository:** https://github.com/dgobi/ResonanceRoguelike  
**Reviewed reference:** `main` at `b94a0b0db3685f7484632701f0486f3b0b79101e`, `checkpoint/worldgen-g8-verified-20261024-a`.  
**G8 frozen test inputs:** `14c98afc38c659c9195b11c6b396fb82544ff03b`.  
**Prepared:** 24 October 2026, America/Edmonton.  
**Companions:** `G8_REVIEW.md` and the independent evidence in this package.

## 1. Implement this outcome

Make the existing country network support useful shorter journeys between its existing destinations. Add a small, deterministic, budgeted set of optional connections to the complete G8 baseline. Keep the baseline roads, bridges, settlements, commons, building selection, rural parents and their ownership intact. A player should be able to choose a demonstrably shorter physical route while the original route remains available.

Begin by correcting the remaining wiki representation and verification-input issues described in section 4. The owner wiki is an ongoing project resource: update its main chapters, executable examples and standalone HTML for G9, as well as its build/verification contract.

The G8 review supports proceeding. The earlier authoring data-loss defect and focused-runner import defect are corrected. The two settlement layouts, cardinal frontage, public space and saved-world behavior have substantive evidence. G8 intentionally preserved the country backbone, whose sequential connection order can produce severe end-to-end detours even when individual routes are short relative to their own endpoints.

### Visible acceptance

- Ship one bounded country-network policy with **at most two optional shortcut connections per new world** and a **total added unique country-centerline length no greater than 25% of the complete G8 baseline's unique country-centerline length**. This is a shared per-world construction budget, not a budget for each route.
- Preserve every baseline destination coordinate, settlement form/extent/layout/lot/common, accepted building, rural parent/child and dependency resolution. Preserve every original country/local route, water record and crossing. Keep old route IDs and assigned arrival/frontage/attachment references stable.
- A shortcut must improve actual shortest travel on the resolved physical network by a meaningful amount. Default admission requires at least **500 saved four-neighbour tile steps and 25% relative improvement** for a named existing primary-destination pair. Account for marginal improvement after earlier accepted shortcuts.
- On unchanged ordinary seed `20261023`, reduce the shortest physical-network distance from `settlement-1` to `capital-gateway` by **at least 50%**, within the same 25% total construction cap. The reviewed baseline is 23,625 steps. Do not special-case that seed or its coordinates.
- Retain a positive alternate-route witness outside town streets: the new connection and a surviving original route must give genuinely different country corridors. Do not count road-width cycles, duplicate overlapping routes or a local town circuit as the new feature.
- Preserve connected complete local road slices, all populated access/native behavior, deterministic lazy planning, historical campaigns and atomic failure behavior.
- Deliver a safe network preview/tuning workflow, complete evidence and an updated offline owner wiki.

Optional enhancement is allowed to add no road when no qualifying legal candidate exists or a declared search/construction budget is exhausted. Explain that outcome precisely. A zero-road outcome must not conceal malformed policy, a broken required baseline, or failure to meet the declared ordinary-seed acceptance above.

## 2. Execution and preservation protocol

Use the owner's **existing production checkout on `main`**. Read applicable `AGENTS.md`, record status/HEAD/remotes and preserve unrelated owner work. If main has advanced, inspect and record the intervening changes; do not reset to this review's SHA. The separate Linux checkout used for this review is not the implementation location.

Continue the established scoped-commit, immutable-checkpoint and verified-publication workflow. When the owner supplies this brief for implementation, delivery includes the implementation, autonomous checks, scoped commits and publication to the existing remote `main`, with remote commit/tag readback. Respect any more specific instruction in that execution session. Do not create a task branch, worktree, second game development checkout or PR. Do not move existing tags, amend unrelated work or force-push.

Use the established dependency interpreter while importing game code from the production checkout. Run headlessly or through app-local game events; use guarded disposable saves. Do not use personal campaigns or assign routine testing to the owner. Preserve G1–G8 evidence, the frozen editor corpus and authentic historical fixtures. Deliver Markdown and machine-readable evidence, with no PDF report.

Use meaningful checkpoints for start, wiki correction, network policy/planning, lifecycle, owner workflows, final inputs and verified delivery. Stage task-owned files explicitly. Avoid broad refactoring of the planner, save engine or test harness merely to accommodate the new module.

### Before implementation edits

1. Record actual source, interpreter/dependency versions, clean/dirty state and disposable-root guard results. Reproduce the supplied wiki freshness/download-identity issues on a tiny synthetic newline fixture; preserve the original result.
2. Capture a **genuine format-6 / `wg8` compatibility witness** with a visited G8 grid member and civic-common/native state, a pending member, visited and pending country-road chunks, and independent compound-child mutations. Use a second small witness if needed. Preserve exact plan/checkpoint bytes, source identity, scene provenance and fingerprints. Use real handlers when claiming gameplay interactions; label fixture positioning and paused updates.
3. Capture the same-machine G8 baseline for seeds `0`, `20261023`, `29417`: complete plans, network measures, all town/rural required scenes and relevant timings. Reuse an already correctly bound run if its exact input/machine scope is proved. Keep primary endpoints and units identical for G8/G9 comparisons.
4. Preflight the production worker's disposable-root guard. Narrowly admit the G9 evidence root if necessary while retaining marker/source/save checks and an outside-root rejection before save access.

## 3. Why this bounded network change

G8 added meaningful local composition. Its ordinary three-world sample contains eleven towns, six grid towns split evenly between the two installed layouts, and occupied horizontal and vertical frontage in every grid town. Town arrivals and usable entrances are already explicit. Expanding town density or replacing that local composer is unnecessary for this arc.

The current country builder in `roguelike/generation/world_plan.py` connects destinations in a mostly sequential order, then gives each roadside town its required horizontal section. `_astar` prefers existing macro-road chunks. It does not evaluate the resulting all-pairs physical travel network. A horizontal macro step spans 80 tiles and a vertical step spans 43; its current chunk-cost heuristic must not be relabeled a shortest physical-travel measure.

The review's independent seed-`20261023` witness demonstrates a feasible improvement without rebuilding that backbone:

| Measure | G8 / review witness |
|---|---:|
| Existing destination pair | `settlement-1` → `capital-gateway` |
| Manhattan lower bound between the same nodes | 3,665 tiles |
| G8 shortest country centerline path | 23,641 steps |
| G8 shortest full-width road/deck/access path | 23,625 steps |
| Conservative candidate centerline path | 6,309 steps |
| Physical-network path after in-memory addition | 6,303 steps |
| Added unique centerline length | 5,903 tiles |
| Baseline unique country-centerline length | 24,631 tiles |
| Added fraction | 23.97% |
| Newly occupied width-three road cells | 17,691 |
| New physical bridge-deck cells | 0 |

The candidate preserves the original records and passes the current normal `validate_plan` in an in-memory copy. It protects all settlement/building/compound/capital owner chunks, including endpoint chunks, against new road entrances/exits. It has **not** been materialized or walked: full gameplay proof remains G9 work. Use the supplied scripts as a regression/review witness, not a source of hard-coded route coordinates or a substitute for the production algorithm.

Country cycles already exist in two of the three G8 worlds. Their reconciled country-centerline cycle ranks are 0, 5 and 2; their cut-edge length fractions are approximately 100%, 94.0% and 95.8%. A graph cut edge is unrelated to a river bridge object. The useful objective is shorter travel and an independent corridor where justified, not achieving a decorative cycle count.

The explored G8 checkpoint is a separate real cost: 354 scene files, 195,744,304 bytes, with seconds-scale save/load. Keep measuring it, but do not fold cache eviction, compressed checkpoints, retention policy or world scaling into this network change. Shorter travel may reduce exploration for a particular itinerary; that is not a storage-engine improvement.

## 4. A — Complete portable wiki verification

The wiki's earlier self-referential revision problem is fixed. Its standalone HTML is usable, its G7/G8 chapters are current, and an isolated maintenance-only copy rebuilds, validates and repeats cleanly against the unchanged review checkout.

The remaining defect is a representation mismatch. On the clean LF checkout, the documented read-only drift command rejects the shipped Windows-produced binding even though all 761 scoped source files canonically match the pinned revision and the HTML exactly matches its own manifest. `wiki_inputs.py` permits newline equivalence while reading source, then `check_products` compares raw hashes/byte counts. Wiki authoring identities are raw-only. One recorded chapter has mixed LF/CRLF; its original bytes are recoverable and no semantic change was found.

Two associated gaps must be addressed in the same correction:

- `verify_edition.py` runs `test_wiki_inputs.py`, but that test file is absent from both the separate wiki authoring scope and the unified runtime/test input manifest.
- The builder advertises source raw hashes/byte sizes while the reader downloads normalized embedded text. The shipped `deep_tongue.json` entry advertises 102,885 bytes; its equivalent embedded UTF-8 download is 98,460 bytes. Make labels and verification identify the actual representation.

Implement one explicit policy:

1. Retain exact raw tested/captured hashes and bytes as provenance. Compare text freshness by a declared canonical identity, with path membership, pinned revision and scope included. Keep binary content exact. Do not conflate equivalence with rewriting the owner's files.
2. Bind the full transitive wiki build/verification inputs, including the contract tests: all project-owned scripts/data actually consumed, with dependency and browser versions recorded separately. Do not inventory whole interpreter/browser installations. Keep generated HTML/manifests/reports and historical audit outputs outside their own input scope. Source commit, wiki authoring/test identity and products remain distinct.
3. Make displayed source/download hashes and byte counts accurate. Always expose a separately labelled identity for the exact downloadable UTF-8 payload, stating its newline, BOM and trailing-newline policy. Original raw-source capture identity may also be shown under its own label. Align builder, static validator, reader download and evidence with that choice.
4. Add small LF, CRLF and mixed-newline positives; substantive text, binary, changed verification-script, missing/added file and stale-HTML negatives. Retain repeated-build and later documentation-only commit positives. Do not silently repin source or make stale products pass by disabling comparisons.
5. Execute actual reader downloads in both established browser engines and compare the returned UTF-8 bytes to the advertised identity; parsing equal JSON alone does not prove byte-hash accuracy.

Commit/checkpoint this correction before extending the wiki for G9. Keep the dark standalone reader and existing navigation/examples. This is a focused repair of the current architecture.

## 5. B — Preserve the G8 baseline and define a small network policy

Read `world_plan.py`, `road_network.py`, `plan_integrity.py`, `settlement_layout.py`, `settlement_context.py`, `planned_scene.py`, `planned_dressing.py`, `ports.py`, `scene_adapters.py`, world publication, save preflight, the G8 journey/diagnostic and current wiki inputs before editing.

Compose the complete current G8 baseline first, including settlements, landmark, accepted rural parents and their reservations. Stage the optional network augmentation before world publication, while no local scenes exist. The enhancement must never rerun site selection, change forms, select different building assets, reroll layout choices or move a required destination to obtain a better score.

Use a small versioned JSON policy, preferably `roguelike/data/generation/country_network.json`, loaded through the existing data path. Keep it separate from settlement layout and POI selection recipes. Ship complete defaults and a complete draft example. At minimum expose:

- `max_shortcuts`: integer 0–2; default 2. Zero explicitly disables augmentation.
- A total added-unique-centerline fraction bounded by 0–0.25; default 0.25.
- Minimum saved physical tile steps and relative improvement; defaults 500 and 0.25.
- A finite candidate-pair limit, per-search expansion limit and global per-world expansion budget. Document exact defaults and validated upper bounds.

Reject booleans masquerading as integers, non-finite/negative values, unknown fields and invalid versions with useful errors. Keep the existing road width; no additional road-surface class or speed model is required. A bounded search that runs out is distinct from exhaustive infeasibility. Record candidates not examined and budgets consumed; elapsed wall time must not determine generation decisions.

Define primary utility endpoints as the existing `start`, `settlement-*`, `capital-gateway` and `landmark` destination nodes, at their saved coordinates. Crossing-bank nodes remain infrastructure; rural parents retain required access checks. Use the same endpoint set before/after and report its exact denominator. Separately measure travel into saved town arrivals and required doors where claimed.

Use stable canonical pair IDs and a network-specific deterministic decision stream. Preserve G8's existing layout/selection seed identities. Candidate enumeration or rejection must not perturb settlement composition, unrelated random state or later scene visit order.

## 6. C — Measure the actual network and select useful connections

Derive a disposable graph from authoritative route geometry. Merge shared unit centerline edges and intersections; account for existing crossings and cardinal joins. Preserve meaningful nodes when contracting degree-two runs and handle isolated rings and parallel alternative runs correctly. Do not save a second independently editable road graph.

Keep three concepts separate:

| Quantity | Definition and purpose |
|---|---|
| Unique construction length | Unit world-tile centerline edges newly added to the union; reused edges cost zero additional construction length. The denominator is the complete baseline country union, fixed before augmentation. |
| Physical travel distance | Shortest four-neighbour steps on the full-width road/deck/access union between fixed named endpoints. Recompute after each accepted connection. |
| Search score | An explicitly documented bounded terrain/construction/travel objective for proposing a route; it is not evidence of actual travel until the exact geometry is evaluated. |

Count 80 horizontal tiles and 43 vertical tiles per whole macro step. If search rewards corridor reuse, do not reduce the actual traversal distance to a nominal one-unit reused edge. Use positive costs and an admissible heuristic for the stated objective, or bounded Dijkstra. Do not claim global optimality from a truncated search or a greedy candidate policy.

Generate a finite deterministic set of candidate pairs based on existing network detour and potential travel benefit. Avoid searching every world tile or every possible geometric junction. Canonical ties and explicit truncation must make equivalent unordered input reorderings harmless.

Evaluate each proposed candidate against the *current staged network*, then recompute affected pair distances and marginal added unique length. Rank candidates using a documented balance of worst-pair detour improvement, aggregate primary-pair saved distance and new construction. A route that duplicates the network, adds a decorative local loop or no longer adds useful benefit after the first connection must be rejected.

Apply the shared two-connection and 25% construction budgets after unioning overlaps, including overlaps between accepted shortcuts. The default 500-step/25% admission applies to a named pair's actual physical distance, not to its route-record length or Manhattan distance. Report why accepted routes won and why other candidates were excluded. Do not optimize a statistic by silently dropping endpoints.

Use Manhattan distance only as a labelled lower bound. Terrain can make it unattainable. The sample's severe detour is demonstrably avoidable because a constrained valid witness exists; smaller ratios in the other seeds do not require forced new roads.

## 7. D — Fit exact road geometry without weakening ownership

Use the complete baseline reservation and ownership state when proposing new road bands. Stay within current world bounds and hard terrain exclusions. Preserve submap owners, capital ownership, all settlement members, civic commons, private lots/buffers, compound envelopes/paths, building approaches and rural goals.

For this arc, **do not create new road cells within existing settlement, capital, building-owner, compound-owner or submap chunks**. Connections may follow existing legal country-road geometry through those chunks. This conservative boundary preserves G8's free-block partition, arrivals and frontage. It also avoids creating new entrances through a rural parent's private yard. Enforce both chunk-level protection and exact full-band checks, including corners and width greater than one.

Do not add new physical river crossings. A candidate may reuse an existing legal crossing corridor, but every new route/water overlap must be covered by the appropriate declared deck. Preserve original crossing records. If a new whole connection route reuses a deck, add narrowly scoped crossing-ownership records as needed by the existing validator; distinguish those records from newly built physical bridges in every metric. Do not invent a blanket road/water overlap exemption.

Keep original routes intact. Store accepted connection geometry in normal canonical route records with stable new IDs and explicit role/ownership under the G9 contract. Existing endpoints remain exactly reachable. Any interior intersection must count as a physical junction only when the geometry connects. Preserve original arrival, incoming-road, roadside-frontage and rural attachment assignments explicitly; adding another route with `b == settlement_id` must not silently change the selected arrival.

Stage each candidate atomically, including route, crossing and reservation additions. Replay through the normal validators before accepting it. The review witness exposes a reservation-order trap: naively appending new road rows after old approach rows can reject legitimate reuse. Inserting staged new road rows before existing private/approach rows allows the existing narrow public-road permissions to work. Preserve original record contents and relative order where possible; never grant broad owner-prefix or whole-town exemptions. Keep IDs unique when replay order differs from allocation order.

Check **every touched local chunk's** complete road slice. It must remain locally connected using current materialization rules. Globally connected geometry can still introduce two disconnected corridors in one chunk; reject or resolve the candidate within this arc's existing local contract. Do not solve this by adding a new portal/navigation subsystem.

During disposable verification, after the complete plan is published, materialize every accepted touched chunk and prove road/deck continuity across actual boundaries, final populated access and legal junctions. Production planning/admission remains geometry-only and creates no local scenes. Native actors, openable doors and ordinary updates matter separately from empty plan geometry. Add a narrowly justified correction if an accepted geometry exposes an existing materialization defect; preserve the baseline and record the reproduction.

## 8. E — Save the new contract and preserve older worlds

Use **plan format 7 / origin `wg9`** for fresh worlds using the new network contract. Keep `shared-v1`, `structure-v1`, complete-scene ownership and campaign checkpoint storage. Preserve G8 layout contract 1 and explicit POI policy semantics. Add a current planning-settings version that explicitly selects the network policy; retain settings version 3 as the historical G8 route and existing older paths.

A current G9 world with `max_shortcuts: 0` remains a correctly labelled G9 world with a resolved disabled/empty network result. It should reproduce G8's geometric/content baseline, aside from declared new header/settings/network metadata. Selecting legacy settings must continue to select the appropriate historical contract. Test G9 with mixed-parent POI v2, legacy single-site POI v1 and explicit zero additional parents; do not recouple layout/network identity to the POI-policy switch.

Throughout this brief, baseline content means the exact resolved destination, route, settlement, plot, accepted-asset, rural-owner and dependency records, apart from declared new contract metadata. It does not require freshly generated `wg9` scene fingerprints to equal freshly generated `wg8` fingerprints: the generation revision is an existing scene-seed input. Preserve actual older visited scenes and require deterministic G9 scene generation under its declared revision. Do not add a separate scene-RNG compatibility redesign.

Persist the resolved network policy, original-route identity, accepted shortcut IDs/endpoints and bounded decisions necessary to explain/validate the result. Canonical route/crossing/reservation records own exact geometry. Avoid storing redundant full before/after graphs, complete search queues or duplicate world plans in each save. Metrics/large rejected-candidate traces belong in diagnostics unless needed for the durable contract.

Pending scene creation must use saved resolved routes. Removing or changing today's network policy must not reoptimize a saved world. Preserve affected-only consumed-definition checks and G8 public-surface dependencies. Old visited scenes retain their actual creator provenance and player mutations; pending formats 1–6 use explicit compatible adapters. Do not generate new G9 output and label it as a genuine G8 witness.

Audit dispatch comprehensively: current `world_plan.validate_plan`, registry construction, reservation purposes, `slice_plan`, `planned_scene`, save validation and layout validation contain `version == 6` or settings-version assumptions. A header bump alone can omit commons or reject legitimate G9 scenes. Use explicit supported-contract dispatch throughout, retaining all G8 public-space/furnishing checks and historical semantics; do not accept every future version with a broad unchecked threshold.

Validate reciprocal new references, route roles/IDs, exact endpoint/geometry/band relationships, baseline preservation contract, construction accounting, ownership and crossing scope. Add checksum-consistent corruptions for missing/foreign shortcut references, altered endpoints, disconnected joins, unauthorized road/water cells, baseline-route removal, forged budget/cost records, new road through protected ownership and incompatible version/provenance. Fail before installing player/world/cache state.

Inject a late failure after some new road/scene preparation has succeeded. Prove player, RNG, active map/actors, world and Chunk metadata, cache and checkpoint HEAD are unchanged, then recover after removing the fault. Reverse first visits, independent owners, cold load and F9 must preserve the actual explored G8/G9 state.

## 9. F — Owner controls, previews and maintained wiki

Extend the existing authoring command with a complete safe network workflow. Reuse `authoring_outputs.py`; new policy inputs, initializer targets, JSON/SVG/PNG outputs and dynamically named files must participate in the same preflight/staged collision rules. Do not introduce a second unsafe report writer. Previews operate on disposable worlds and must not install policy or open campaigns.

Execute and document these top-level workflows:

1. Inspect the installed policy and preview an ordinary seed with baseline/augmented network overlays, fixed endpoint distances, reused/new lengths, accepted/rejected candidates and budget usage.
2. Initialize a complete draft without overwriting edits; reduce the construction or connection budget and explain why the same seed adds fewer/no routes.
3. Disable augmentation explicitly and prove the baseline geometry/content contract; explain the difference between a new disabled G9 world and an existing saved G8 world.
4. Demonstrate a meaningful accepted connection and an honest no-benefit, protected-owner or budget-exhaustion result with labelled units and reasons.
5. Demonstrate deliberate install/revert against a disposable authoring/data catalogue with sentinels proving unrelated files are preserved. Document the separate production version-control recovery procedure without temporarily overwriting/reverting owner files as a demonstration.

Preserve and rerun applicable G5–G8 workflows and real browser-export consumers. The existing painter still edits buildings; a graphical road editor, new map UI or pathfinding display is not required.

Update main wiki chapters for world generation, settlement layouts/tuning, rural sites/compounds, saves/state, authoring/troubleshooting, verification, maintenance and code map. Explain augmentation versus the preserved required backbone, two-link/construction limits, real units, protected owner chunks, reuse of existing bridges, explicit no-shortcut outcomes, new-world versus saved-world behavior and current limitations. Keep country optimization distinct from future organic roads, density or streaming. Refresh relevant complete examples, version table, edition history and source links.

Deliver rebuilt `Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html` and editable maintenance source. Bind the actual reviewed source, complete wiki inputs and final products; a later documentation-only delivery commit must remain valid. Keep historical edition audits as history. Ongoing upkeep remains part of feature delivery, not an unattended schedule.

## 10. Verification and cost evidence

Use behavioral fixtures for risks introduced here and the established release gates. Tests should demonstrate geometry/access, preservation, deterministic decisions, saved-state integrity or owner workflows; avoid large collections of assertions that merely mirror implementation fields.

### Geometry, scoring and bounded search

Use independent small expected-network fixtures for anisotropic chunk dimensions, shared-run deduplication, crossings/intersections, isolated rings, diagonal-only contact, duplicate routes, genuine alternate corridors, multiple accepted-route overlap and marginal-benefit recomputation. Test exact budget boundaries, zero budget, malformed policy, candidate truncation, expanded-node exhaustion and complete optional rejection with baseline unchanged.

Include legal old-road/approach reuse with normal reservation replay, unauthorized private/common overlap, width/corner collisions, existing-deck reuse, new-water rejection, boundary continuity and a globally connected but locally disconnected road slice. Verify controls prevent changes to all baseline ownership subtrees, not only the named endpoints.

### Ordinary worlds and measurable improvement

Keep seeds `0`, `20261023`, `29417` without forcing candidates or replacing unhelpful samples. Compare complete G8 baseline and G9 plans from the same inputs. Show zero scenes at plan completion and exact preservation of baseline towns/rural contents/routes. Report accepted zero-road worlds honestly. Controlled fixtures prove behavior absent from the ordinary sample.

For every seed retain primary endpoint coordinates; all-pairs before/after physical distances; selected witness paths; baseline and added unique centerline length; reused length; new full-width cells; actual new bridge cells; candidate/search budgets; explicit rejection reasons; physical components; reconciled cycle rank; and country cut-edge length. Label each graph's scope. Do not claim a terrain-respecting optimum from a Manhattan comparison or convert a cut-edge count into a guarantee of robust gameplay travel.

Demonstrate the seed-`20261023` acceptance on the unchanged named endpoints and ordinary installed policy. Show every primary pair's physical distance is non-increasing, as expected when preserving the old network. Demonstrate a substantial independent alternate corridor after removing a representative newly constructed run from the derived diagnostic graph. This removal is a proof fixture, not a live road-destruction feature.

Vary process hash seed, unordered input membership and scene visit order. Intentional order and policy changes remain meaningful; equivalent reordering must not reroll the result. Retain exact full-plan identities and relevant complete scene fingerprints.

### Actual traversal and persistence

Extend the real-handler journey to walk an accepted shortcut in both directions through its endpoint joins and ordinary chunk boundaries, and prove the original route remains usable. Use fixed comparable endpoints and distinguish network BFS distances from input counts on a fixture itinerary. Preserve G8 common/native civic, both street axes, required building-content, bridge, landmark, other settlement and compound/single-site coverage.

Use production movement, door, interaction, boundary travel, F5, cold load and F9. Disclose invincibility, stationary actors, paused AI/survival and fixture positioning. Include a separate ordinary-native-update positive. Save an actually explored G9 checkpoint containing shortcut scenes, a town/common and independent compound mutations; verify it after cold load/F9. Retain the genuine pre-edit G8 witness and earlier historical compatibility fixtures.

Measure same-machine planning/search/graph costs, plan bytes by subtree, complete scene creation, worst observed boundary transition, materialized scene count, explored checkpoint bytes and save/cold-load/F9 times. Report both the comparable G8/G9 itinerary and total coverage journey scope if they differ. Do not claim a storage improvement from walking a different number of chunks. State finite sample size and investigate material regressions without inventing a universal frame-time target.

Retain exact network overlays and populated production-renderer views of representative new junctions, reused crossing approaches and unchanged G8 town/common. State revealed visibility. Inspect unnecessary parallel strips, misleading non-junction contacts, disconnected local corridors and repeated traversal. A macro diagram does not replace the actual journey.

## 11. Final gates, completion matrix and delivery

Freeze all intended runtime/test/authoring inputs at an immutable source commit/tag. Run the established serial finite sequence with documented timeouts: guarded disposable preflight; unfiltered focused discovery from a parent with no `PYTHONPATH`; both browser engines and actual exports/downloads; new/inherited owner workflows; structure/editor catalogue checks; ordinary diagnostics and real journey; production views; wiki contract/build/repeat/drift/integrity/reader checks; and the unfiltered production gate with existing negative controls and coverage requirements.

Use the current unified-input full-rerun rule when its bound inputs change. Separately bind the wiki's complete transitive verification inputs and products under the repaired policy. A documentation delivery commit is not a reason to rerun unrelated game gates, and a changed test/helper cannot be omitted merely to retain a passing receipt. Retain earlier failures/timeouts separately from final passing records.

Record commands, cwd, interpreter/tool versions, input commit, exit/timeout status, source stability, exact raw hashes and canonical text identities. Preserve raw tested bytes when mixed newline representations cannot otherwise be reconstructed. Count nested authoring workflows honestly. Inventory omitted disposable saves without treating absence as a passing result.

Map the following in `docs/owner/WORLDGEN_G9.md` and a machine-readable evidence index:

| ID | Required result |
|---|---|
| G9-01 | Preserved owner work, guarded disposable execution, genuine G8 witness and same-input baseline. |
| G9-02 | Portable wiki freshness, accurate download identities and complete test-input binding with positive/negative evidence. |
| G9-03 | Strict bounded policy, complete owner defaults/drafts and explicit disabled/no-improvement outcomes. |
| G9-04 | Exact baseline destinations, routes, crossings, settlement/rural composition and ownership preserved. |
| G9-05 | Correct reconciled topology, anisotropic units, construction union and fixed-endpoint physical travel metrics. |
| G9-06 | Deterministic finite search, marginal-benefit admission and shared two-link/25% budgets. |
| G9-07 | Ordinary `20261023` named-pair distance reduced by at least 50%; genuine surviving alternate corridor. |
| G9-08 | Full-band ownership, existing-deck reuse, normal reservation replay and connected touched local slices. |
| G9-09 | Format 7/current settings dispatch preserves G8 common/native behavior and all supported POI combinations. |
| G9-10 | Saved resolved network independent of current policy; genuine historical provenance and independent mutations preserved. |
| G9-11 | Corruptions reject before installation; late-failure rollback and recovery preserve every state owner. |
| G9-12 | Ordinary matrix, deterministic lazy planning, honest no-road cases and meaningful performance/storage comparisons. |
| G9-13 | Actual bidirectional shortcut journey, retained original route and explored cold-load/F9 checkpoint. |
| G9-14 | Safe complete network workflows plus inherited authoring/editor consumers. |
| G9-15 | Current main wiki chapters, reviewed offline HTML, editable maintenance source and validated download bytes. |
| G9-16 | Final frozen gates, source-bound portable archive/inventory, scoped publication and remote readback. |

Deliver scoped commits and unique checkpoints; owner report; machine-readable results; source-bound baseline/augmented plans and network comparison; representative views; updated standalone wiki and editable source; and one portable review ZIP. Preserve intentional historical compatibility fixtures. Omit personal campaigns, dependencies/browser profiles, disposable worker saves and a redundant full checkout. Validate archive member inventory, sizes, SHA-256 and CRC, recording publication/readback outside self-referential committed content where needed.

Distinguish newly executed checks from historical records, ordinary worlds from controlled witnesses, plan feasibility from populated traversal, and raw capture from canonical identity. The next review must be able to reproduce both the benefit and the boundaries from the delivered evidence.

## 12. Stop boundary and design references

Stop after the wiki correction, bounded useful country connections, compatibility proof, owner workflows and verified delivery. Do not implement new settlements/POI density, river crossings/tunnels, organic road curves, backbone deletion/rerouting, vertical roadside towns, capital redevelopment, cross-chunk buildings, bigger worlds, cache eviction, checkpoint compaction, continuous viewport or a graphical network editor in this arc.

The next review should compare actual journey quality and planning cost, then decide whether remaining network limitations or the measured long-campaign storage cost deserves the next stage. G10 is not automatically authorized by this brief.

Two primary research sources inform the design separation, without prescribing their full algorithms:

- Galin, Peytavie, Maréchal and Guérin, *Procedural Generation of Roads* (2010): terrain-aware route costs should account for environmental obstacles. [Publisher abstract](https://onlinelibrary.wiley.com/doi/10.1111/j.1467-8659.2009.01612.x).
- Galin, Peytavie, Guérin and Beneš, *Authoring Hierarchical Road Networks* (2011): network graph generation, path merging/junctions and author controls are distinct from final geometry. [Publisher abstract](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-8659.2011.02055.x).

The bounded augmentation, numeric budgets and acceptance thresholds here are project decisions supported by the supplied Resonance witness. They are not guarantees supplied by those papers. Current source and tested contracts remain the implementation authority; no new dependency or wholesale road engine is required.
