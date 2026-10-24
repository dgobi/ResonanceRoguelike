# Codex G7 — Multi-building compounds with shared road access

**Project:** Resonance Roguelike.  
**Repository:** https://github.com/dgobi/ResonanceRoguelike  
**Reviewed starting reference:** `main` at `4d7a7892e1afffb8d872ed4a8fd442984d14e7d5`, checkpoint `checkpoint/worldgen-g6-verified-20261024-a`.  
**Prepared:** 24 October 2026, America/Edmonton.  
**Companion:** [G6 review](G6_REVIEW.md), supplied authoring probe, specialist audits and independent G6 verification in this package.

## 1. Implement this outcome

Correct the small required-goal admission error, then let new worlds contain **small authored compounds made from two or three JSON buildings around shared, usable circulation**. A compound has one identity, one country-road attachment and one reserved envelope. Its child buildings have separate stable identities and real contents. The owner can author another compound by editing JSON and using documented production previews, without editing Python.

Keep **two through four additional parent places** by default, including at least **one compound and one single-building site**. A compound replaces a slot in that existing total; it does not increase parent-place density. Keep the featured landmark separate and unchanged in purpose. Ship two coherent recipe types: a homestead/workyard and a compact wayside shrine court. Keep every compound within one 80 × 43 surface chunk.

The visible outcome is a believable small destination: leave the country road through its saved entrance, enter a shared yard or path, reach each required building and use its contents. The durable outcome is one resolved parent/child plan and one complete scene whose state survives first-visit order, travel, cold load and F9.

Complete the opening correction and this bounded feature together. This review has not changed production source. Stop at the G7 completion boundary in section 12.

## 2. Standing execution protocol

Use the existing production checkout on **`main`**. Inspect status, `HEAD`, remotes and applicable `AGENTS.md` before editing. If main has advanced, inspect the intervening changes, record the actual start and preserve owner work. Do not reset to the reviewed SHA.

Make scoped, meaningful commits on main with unique immutable checkpoint tags. Do not create a task branch, worktree or second development source checkout. Disposable test data, private save roots and evidence directories are permitted. Use the existing project interpreter, even if it resides outside the checkout, while importing this checkout's game source. Preserve unrelated files, personal campaigns, dependencies and tools.

Use a chain such as `checkpoint/worldgen-g7-start-<date>-<suffix>`, then admission, compounds, lifecycle, authoring, final-gate-inputs and verified. Check tag collisions; never move an existing tag. Stage only task-owned paths. Resolve a genuine overlapping ownership conflict without overwriting unrelated work.

The owner has authorized scoped verified changes to be pushed to the existing repository's **main**. Complete that publication and inspect the remote commit and verified tag. Do not introduce a PR or routine confirmation pause; do not force-push. If an actual access or approval restriction prevents publication, complete the reviewable local result and report the precise action and reason.

Run headlessly or through app-local tools. Do not take over the desktop or assign routine testing to the owner. Retain meaningful failures and their source identities. Deliver Markdown and machine-readable evidence; no PDF reports. Preserve G1–G6 evidence and the frozen editor corpus.

### Before the first implementation edit

Capture a **genuine G6 compatibility witness** using the current G6 materializer and a disposable campaign: exact format-4 plan, at least one visited additional site with a recorded mutation, and at least one accepted site still pending. Record source, command, interpreter, checkpoint inventory, scene provenance and plan identity. Preserve original bytes. A direct fixture mutation is allowed if clearly labelled; it must not be described as a player interaction. Use an existing correctly bound authentic witness if intervening main has already changed the materializer; never relabel a G7 scene or discard owner changes to manufacture G6 evidence.

Run the supplied required-goal probe against the actual starting source and preserve its original observations. Its embedded source SHA identifies the review, so a wrapper must separately record the current checkout SHA, complete input hashes and command. Immediately after authentic capture, preflight the production worker's disposable-root guard: G6 explicitly permits `.baseline` and `evidence/worldgen-g6`, not a new G7 root. Either use the existing guarded baseline location with a G7 run name, or narrowly add `evidence/worldgen-g7` with the existing marker/source/save-location checks intact. At this opening boundary, prove an allowed disposable worker and rejection of a synthetic disposable directory outside the allowed roots, before any game/save access. Never point this negative at a real personal campaign.

## 3. Starting state, correction and boundaries

G6 supplies format 4 / `wg6`, explicit additional-site owners, canonical country attachments, a physical road projection, a bounded transform-aware fitter and stable saved policy. The ordinary seeds `0`, `20261023`, `29417` contain respectively 2/3/3 additional single sites; each has one physical road component. The world remains finite at 128 × 128 chunks. Lazy complete-scene creation, `shared-v1`, `structure-v1` and `native-town-v1` remain established contracts.

Read the actual source before changing it: `roguelike/generation/poi_selection.py`, `world_plan.py`, `placement.py`, `plan_integrity.py`, `road_network.py`, `planned_scene.py`, `scene_adapters.py`, `poi_preview.py`, world generation/publication, save preflight, the G6 lifecycle tests, diagnostic/journey tools, and `roguelike/docs/STRUCTURE_AUTHORING.md`. The review cites the relevant implementations and identifies limits of the retained evidence.

### Opening correction: missing required goal

The supplied `specialist_reviews/composition/probe_optional_site_goals.py` changes only `roadside_shrine_a` target flags to `required: false` in memory. The normal compiler and direct preview accept it. Assigned-site preview and ordinary generation with that eligible policy then raise an empty `StopIteration` at the required-goal lookup. Failed generation leaves the world unchanged. This is a real authoring/error-reporting defect; the installed ordinary cohort already has required goals.

Run the probe with `--source <repository-root> --output <evidence-json>`. Add a clear eligibility error **before rural-site fitting/selection** when an additional-site candidate has no required usable target. Apply the corresponding contract to compound child candidates. Include asset, consumer/context and how to correct the definition in the `GenerationError`/CLI message. Preserve optional targets alongside a required target, and preserve direct/legacy consumers for which an all-optional target list is legal. Do not globally tighten historic plan validation or all structure compilation merely to hide this consumer-specific assumption.

Retain the original result; add a focused regression for meaningful rejection, unchanged publication state, mixed required/optional acceptance and normal shipped assets. If main already fixed it, identify that change and retain equivalent proof. Commit/checkpoint the correction, then continue with compounds.

### Deliberate feature limits

One additional parent per allowed rural chunk; two required child buildings and at most one optional child slot per recipe; no nested compounds. Keep country routes, current town forms, capital/civic semantics, rural population policy and map dimensions. Existing water, bridge, anchor, private-space and chunk-bound protections remain hard constraints.

Cross-chunk compounds, organic town growth, new road optimizers or loops, terrain repair, new bridge systems, world-size/cache/save-storage redesign, a continuous viewport, dynamic trading/quests and a new world editor are later work. Do not add an LLM/model/service dependency, a general grammar engine or a second scene lifecycle for this bounded feature.

## 4. A — Author a small compound recipe and unified parent policy

### Recipe is separate from a building layout

Add a versioned recipe catalog, preferably `roguelike/data/generation/compounds/<id>.json`. Reuse existing building JSONs as children. A recipe should express, with clear local tile coordinates:

- Stable recipe ID, a bounded outer envelope, and explicitly permitted whole-recipe rotations. Mirroring is optional for this arc; do not add it unless its semantics and tests remain small.
- One external gate/access interface, with a normal, full width/span and canonical connection to shared internal circulation.
- Named shared paths or yard corridors with actual walkable geometry and declared joins. Reserve circulation before child fitting; do not rely on whatever terrain remains between buildings.
- Stable child-slot IDs, their role/purpose, required/optional status, explicit buildable region, frontage/internal-path reference and weighted eligible asset memberships.
- A finite fitting budget or use of a clearly defined shared budget, plus useful bounds and diagnostics. Avoid competing editable copies of the existing external spur-length authority.

Use stable slot IDs for semantics and ownership. Treat weighted memberships as unordered and canonicalize them. If a slot schedule is intentionally ordered, document and preserve that order. Do not make identities depend on the chosen asset, dictionary order, failed trial count or arrival order. An optional third slot may be omitted with a reason; if admitted, its contents and required goals become durable obligations like those of any other accepted child.

### Initial recipes and feasible transforms

Ship two useful templates, with exact dimensions determined and certified by the production fitter:

| Recipe | Suggested existing children | Intended geometry |
|---|---|---|
| Homestead/workyard | Required `house_hearth_a` and `tool_shed_a`; optional `storehouse_a` | An elongated yard suited to the shallow side of a horizontal road; restrict parent rotations when children's effective transforms require it. |
| Wayside shrine court | Required `roadside_shrine_a` and `waymarker_shelter_a` | A compact common court/path; provide vertical-road coverage and all four normals where actually legal. |

Review sketches around 44 × 16 and 18 × 14 respectively are **feasibility hints, not certified acceptance dimensions**. Existing house/shed/storehouse transform permissions are narrower than those of the shrine/shelter. Check each effective child transform after the parent transform; do not silently grant rotations or mirrors. Existing `structure-v1` includes those permissions. Context-only eligibility and weights are excluded from that projection, so an explicit `compound` context opt-in is preferable to rewriting old geometry. If a genuinely new definition is unavoidable, use a distinct asset ID and keep content expansion minimal.

The current ordinary N/S plot fitter limits width using global `plot_spacing_tiles` (18 by default). A compound needs explicit parent envelope and child buildable bounds. Do not increase global town spacing or disguise a wide compound as one oversized ordinary building. Extend the shared fitting primitives with explicit bounds/access support while retaining their current behavior for older callers.

Every recipe must have purposeful circulation and spacing: buildings should face the common approach, required doors should not face a blocked fence or another private buffer, and a recognizable shared open area should remain. Plain useful ground/path treatments are sufficient; a new decorative art system is unnecessary.

### Policy v2: one selection of parent places

Extend `poi_profiles.json` with a version-2 policy using **one canonically ordered, kind-tagged choice list**. A row references either a single asset or a compound recipe, with explicit positive weight and hard accepted-parent cap. Avoid separate independent single/compound draws that reconcile total counts afterwards.

Keep default total minimum 2, maximum 4, plus explicit minimum-one-single and minimum-one-compound requirements. Validate that kind minima fit total minimum/count limits and eligible cap capacity. Owner opt-outs must be explicit and documented; weights alone cannot guarantee the default mix. The selector may prioritize unmet kind obligations before discretionary places, but all choices share the same caps, candidate space, staged state and bounded work. Failure to meet any required kind or total minimum rejects the candidate world before publication.

A parent counts **once**, regardless of its child count. Featured landmark remains excluded. Keep single-asset cap two and start compound-recipe caps at two. Define local soft repetition at the parent-choice key `(kind, asset-or-recipe ID)` using the existing nearest accepted join rule and stable tie break. Child asset frequencies are a separate diagnostic; do not silently charge a compound's two children against single-site caps. Recipe slot weights choose children and must not multiply parent selection probability by the number of fitting transforms or slots.

Preserve asset-first weighting for singles, including current structure base weight × policy weight. A compound parent's explicit policy weight may use an implicit base of one; document the comparison. Resolve all active policy values and selected recipe decisions once. Continue truthful desired-count shortfalls above all minima, separating hard-cap/candidate exhaustion from bounded-search exhaustion. Keep current spacing/location protections and one-parent-per-chunk behavior. Make any geometry-driven tuning explicit and justified against retained seed results.

Validate IDs, contexts, integer bounds, nonfinite/zero weights, duplicate slots/memberships, incompatible transforms, invalid references, empty/disconnected required circulation, unfit mandatory child capacity and unbounded budgets before partial publication. Distinguish invalid authored data from a valid recipe that does not fit a particular candidate road location.

## 5. B — Fit the compound around a shared access plan

Continue choosing parent locations from existing country-road candidates after required backbone/towns/crossings/anchors/featured landmark are reserved. Retain canonical deduplication, both road axes, straight-corridor handling, junction clearance, allowed rural biomes and bounded enumeration. Never create a new country route for each child or re-route the backbone to make a compound fit.

Resolve the parent gate and exact country attachment first. Transform the recipe's envelope, circulation and child buildable regions into world coordinates. Fit children against that already reserved circulation using the shared production transform, entrance-span, buffer, content-dependency and geometry logic. A small explicit access-kind branch is appropriate; a copied approximate compound-only fitter is not.

Each child has a typed **internal access** relationship to its declared shared path/gate. It must not claim direct country-road frontage when its entrance actually opens into a courtyard. Preserve existing ordinary road access for standalone sites. Extend consumers and validators to distinguish these cases explicitly; do not manufacture dummy country endpoints/routes merely to satisfy old assertions.

### Reservations and transaction boundary

The parent envelope excludes unrelated places/infrastructure. Within it, children may occupy their declared slots; sibling private footprints and buffers remain mutually protected. Permit shared-path/approach overlap only where the named access relationship and actual overlapping geometry allow it. Protect the external approach, gate and internal circulation from dressing, resource placement and permanent blockers.

The current `compatible` argument to `Reservations.conflicts`/`add` skips all rows owned by a supplied ID. Do **not** use blanket same-parent or ID-prefix exceptions. Introduce the smallest explicit containment/shared-access permission needed, and mirror it in saved-plan validation. Include negatives where siblings overlap, an unrelated owner uses a parent's exception, a child escapes its envelope, and a private buffer consumes required common circulation.

Stage the whole parent trial: envelope, children, paths, plots, placements, dependencies, reservations, nodes and accepted counts. If a required child cannot fit, roll back the whole compound and try another legal bounded alternative. Failed branches consume no accepted cap or owner ID. An optional child's rejected branch also leaves no accepted-state residue. Retain bounded attempt counters and rejection reasons separately; they must not affect stable identities or accepted caps. Never publish a half-required compound or “repair” failure by removing a required door/goal or relaxing a private buffer.

Keep finite work explicit at both parent and child levels. Count actual transform fits/backtracking against stated budgets. Do not multiply an unbounded nested search by the G6 candidate limit. Distinguish no solution among enumerated alternatives from budget exhaustion. Retain bounded rejection examples naming parent, slot, asset, transform, conflicting owner and reason.

### Physical and final access proof

Save shared path geometry in **one canonical location**. Extend `PhysicalRoads` or an equally explicit derived access view to include it and child approaches, preserving orthogonal continuity semantics, full-width intersections and the existing bounded sparse representation. Avoid a second persisted authoritative graph.

Before **plan publication**, validate the canonical geometry: the parent gate joins its actual saved country segment and every accepted child's required access belongs to that connected system. Keep planning lazy, with zero local scenes created. On first **scene materialization**, validate all required primary and secondary door spans and required goals after all child stamping, contents, dressing and native population, before installing that complete scene. Diagnostics may separately materialize sample scenes for certification. A connected centerline or an empty terrain preview is insufficient for this final scene check. Preserve production interaction rules for containers/readables and floor goals.

Use independent small expected-geometry/connectivity fixtures, including a disconnected common path, corner-only contact, wrong parent, a blocked gate, a wide required door and a later child's content blocking another child's route. Test all permitted recipe transforms, with invalid effective child transforms rejected. Cover four frontage normals across the shipped cohort; do not demand an illegal orientation from an elongated recipe.

## 6. C — Resolve format 5 without changing historical intent

Use **plan format 5 / origin `wg7`** for fresh compound-capable worlds. Retain `shared-v1`, `structure-v1`, existing campaign storage and `native-town-v1`. Keep version-1 POI policy and exact format-4 semantics supported for saved G6 worlds. Do not reinterpret existing single-site records as compounds, add new sites to older plans or apply new kind quotas retroactively.

The new schema must validate both directions of parent/child/slot/plot/placement/path/node relationships. Every accepted parent has one external attachment and one owned chunk; every child has exactly its declared parent and slot; every canonical path has a declared owner and supported use. Validate duplicate IDs, foreign references, absent/extra children, envelope containment, required flags, effective transforms, goal references and the declared parent-count/cap semantics. Keep child placements as reusable flat stamping records if useful, with explicit ownership links rather than duplicated geometry.

Store the resolved child asset choices, transforms, geometry, goals and internal circulation in the plan. Pending materialization must use these records without rerunning the current recipe selector or reading today's recipe to reconstruct layout. Recipe/policy edits affect new plans. Retain child structure dependency checks under unchanged `structure-v1`: incompatible consumed child content blocks only affected unseen scenes; visited saved scenes and unaffected pending scenes remain usable.

Do not add a digest of the entire mutable recipe solely because it is new JSON. If no recipe data is consumed after resolution, the saved plan is sufficient. If any new definition is genuinely consumed later, define and test a small explicit dependency projection for that data without redefining historic `structure-v1`.

The existing complete chunk scene remains the only live/cache/save owner. Derive item/container/actor record prefixes from stable child placement IDs. No per-child scene cache, inventory snapshot or partial-child persistence. Preserve rural semantics and avoid TownData/merchant/civic behavior for compounds.

Keep historical actual-scene provenance and adapters. Newly created scenes from older plans need explicit supported G3/G4/G5/G6-to-G7 dispatch; already visited scenes retain their actual saved creator revision. Unsupported pairs reject. Load the authentic pre-edit G6 witness with replanning forbidden, preserve its mutated visited scene and exact plan identity, and create its pending site through the correct adapter. Do not confuse world origin with a map's actual materializer.

Extend real checkpoint preparation with checksum-consistent malformed parent/child/path records. Stage validation before installing scenes, player/RNG, actors, cache, visit flags, Chunk metadata or checkpoint state. Late failure on a later child must leave all these unchanged. Already visited player-mutated scenes remain authoritative; do not rerun initial-access proof against their current altered tiles as a reason to regenerate them.

## 7. D — Prove ownership, access and ordinary selection

### Controlled cases at the new boundaries

Certify both recipes through the real production fitting and complete-scene paths across every declared parent transform. Check the effective transforms and all required content of each child. Exercise an optional third child's admission and omission separately. Keep controlled policies labelled and separate from ordinary frequency observations.

Include a controlled compound with **two instances of the same content-bearing child asset in one scene**. This is new proof: G6's two shrines were in different chunks. Show distinct item/container objects, stable child-prefixed content records and independent real item-transfer mutations. Save a known checkpoint, make different later mutations, cold-load and F9; each child must return to its own saved state without refill, aliasing or duplicate generation. Also use two parent compounds of the same recipe in different chunks to verify parent identity and reverse first-visit order.

Cover failed required-child fitting, budget exhaustion, optional-child rejection, late second-child content/access failure, wrong/foreign path references and reciprocal parent/child corruption. Prove complete rollback, including reservations, dependency additions, counts, metadata and live state. Keep representative independent assertions rather than expanding into an unrelated fuzzing project.

Prove equivalent unordered recipe/policy memberships resolve identically under differing process hash seeds and irrelevant gameplay history. Preserve intentionally ordered schedules. Current recipe/policy membership edits must not recompose saved pending sites; changed consumed child content must retain affected-only pending failure with visited/unaffected positives. Retain the historical G3/G4 plan-and-adapter fixtures, the authentic G5/G6 saved-scene checkpoints, and legacy/no-plan coverage, with each fixture's provenance and limitations labelled accurately.

### Ordinary seed matrix

Retain ordinary seeds **`0`, `20261023`, `29417`**, with the installed default policy, all results and failed attempts. Each must satisfy total and kind minima without geometry relaxation. Record which shipped recipes these seeds select. Certify both recipe types; if one is naturally absent from this sample, report the absence and use a labelled controlled case for its certification. Do not quietly choose a more favorable seed or edit the ordinary policy for a screenshot.

For each world, record desired/accepted parent counts, single/compound counts, selected recipes, accepted/omitted slots, child asset frequencies, effective transforms, exact external attachment, internal paths, rejection totals, fit work, physical component/connectivity results, plan bytes and zero local scenes at planning completion. Separate parent counts, child counts, recipe choices, direct previews, complete scenes and interactions.

Materialize start, every town member, featured landmark, capital gateway, required crossing, every additional parent and relevant approach slices. Verify every accepted child's required goal after full population. Keep current native/resource/civic functionality positive. Provide a bounded ordinary-update positive for a compound in addition to paused/stationary long-travel tests.

### A real compound journey

Extend the existing real-handler journey through required crossing, both settlement forms and featured landmark. Reach at least one naturally selected compound **from its saved country-road join**, follow the gate and common circulation, enter every required child and perform actual content interactions where provided. Also reach a single-building site to preserve the mixed parent cohort path. A floor goal should be reported as a reached floor, not as a container interaction.

Do not teleport into the compound and call it connected travel. Controlled fixture positioning may be used in separately labelled lifecycle tests. Record exact steps, boundary transitions, parent/child IDs and goals, item-transfer results, checkpoint scope and coherent F5/F9 rollback. Disclose stationary actors, paused AI/survival or invincibility. G6's 37,781 steps are historical, not a required target or a reason to extend the route arbitrarily.

### Costs and presentation

Measure planning, candidate/child fitting, derived connectivity, compact plan bytes, complete scene time, worst observed transition and checkpoint/restore time/bytes with explicit scene counts. Include at least one explored compound checkpoint. A starting two-scene checkpoint does not measure a later hundreds-scene campaign. Use comparable same-machine/load baselines for any regression claim; review Linux timings are not a Windows performance threshold.

Retain a world overview and detailed parent plans showing country segment/join, gate, envelope, paths, child buildable/private areas, full door spans, targets and rejection explanations. Include actual app-local gameplay-renderer views of both recipe types and inspect them. Label diagrams versus populated production rendering. Visual coherence is part of this task: the views should show meaningful common space and doors oriented toward it, supported by the geometric/interaction assertions.

Keep derived connectivity disposable and diagnostics bounded. Explain added saved bytes by parent/child/circulation metadata where feasible; do not attribute all whole-plan growth to one component without isolating it. Stop optional benchmarking after the concrete risk and required gates are covered.

## 8. E — Give the owner a complete authoring workflow

Extend `roguelike/docs/STRUCTURE_AUTHORING.md` with a clearly distinguished compound section and preserve working G5/G6 recipes. Ship complete example recipe, child draft and v2 policy files; no fragments that require the owner to infer omitted schema. Document actual installed paths and exact copy/paste commands from the project root using the existing interpreter.

Provide six executed workflows:

1. **Create a compound draft:** copy a complete template without overwriting an edited draft on repeated initialization. Explain the envelope, gate normal/width, path geometry, stable slot IDs and required/optional children in plain language.
2. **Choose or author children:** reuse an existing eligible layout, or edit a child in the current layout painter, export/download its actual JSON, validate its contexts/transforms/entrances/required goals and genuinely populated contents. Explain why a painted shelf or counter is not a container.
3. **Preview the whole place:** direct child previews plus an assigned compound on appropriate horizontal/vertical country roads. Show the real gate, all internal access, buffers and final contents. Explain unsupported parent/effective-child transforms. Produce a clear valid-but-unselected result for ordinary selection.
4. **Register and install deliberately:** add the recipe and kind-tagged parent choice, refresh/check the existing editor catalog when child metadata changes, and run an ordinary world-plan preview. Previewing must not silently install drafts. Use a disposable data catalog for workflow verification.
5. **Tweak and expand:** replace a child asset, add the optional third slot, move/resize a shared path while keeping access valid, change a permitted whole-recipe orientation, and tune counts/kind minima/weights/caps/repetition. Explain parent counts versus child counts and why neither implies a merchant or quest.
6. **Diagnose and understand saved worlds:** demonstrate unknown child, missing required goal, blocked gate/path, private overlap, out-of-envelope/chunk placement, forbidden transform, required-child failure, budget exhaustion and valid optional omission. Explain new-plan recipe changes versus consumed-child pending failures versus authoritative visited scenes.

Implement the smallest CLI extension needed for complete compound previews, with explicit draft recipe, draft catalog/policy, assigned normal, seed and output options. Extend the current authoring tool or use a thin dedicated entry point; document the exact implemented syntax. Do not present proposed flags as already existing. The production planner/fitter and final materializer must underlie the preview.

A compound recipe may be edited as JSON; a new graphical recipe/world editor is unnecessary. Keep the current building editor's unknown-field/ordered-array round-trip rules. If a new context is exposed, update its existing codec/UI/catalog path and verify both supported headless browsers. Feed the **actual downloaded child file** into direct and assigned-compound production preview; a manually reconstructed equivalent does not prove the export workflow.

Execute documented steps in disposable roots. Retain sentinel edits across repeated initialization. Record each command/action, cwd, environment, expected success/negative status, exit code and output hashes. If invoking an inherited workflow as one command, preserve its nested result separately and avoid adding outer and inner counts as if all were independent top-level executions. Keep valid nonselection and expected failure distinct from successful placement.

## 9. Acceptance matrix

Map every row to actual source, tests, commands and evidence in `docs/owner/WORLDGEN_G7.md`. Use meaningful existing tests where they already cover a contract; counts alone are not acceptance.

| ID | Required evidence |
|---|---|
| G7-01 | Actual main/status/start recorded; authentic pre-edit G6 plan plus visited/pending checkpoint captured and bound; supplied goal probe retained and reproduced or an intervening fix identified. Disposable worker root preflight passes. |
| G7-02 | Consumer-specific required-goal admission rejects clearly before fitting/publication, preserves optional targets and legitimate generic/legacy behavior, and leaves failed world state unchanged. |
| G7-03 | Versioned JSON recipe defines one envelope/gate, named circulation and stable required/optional child slots; invalid references/geometry/weights/budgets reject meaningfully. Two complete usable recipe types ship. |
| G7-04 | Unified policy v2 counts parent places once; default total 2–4 plus minimum-one-compound/minimum-one-single; featured excluded; kind/cap feasibility and explicit opt-outs validate. |
| G7-05 | Parent caps/repetition and child weights have stated denominators; canonical unordered inputs and asset-first transforms remain deterministic; desired shortfall and budget exhaustion report honestly. |
| G7-06 | Parent locations use existing protected country candidates; one rural chunk contains envelope, full external access and all children; both axes/four normals work across the legal recipe cohort. |
| G7-07 | Shared fitter supports explicit bounds/internal access without global town-spacing change or duplicate geometry solver; all effective child transforms respect unchanged consumed-definition permissions. |
| G7-08 | Narrow parent containment/shared-path permissions coexist with sibling/foreign private exclusion; no blanket same-parent exception. Positive overlap and malformed/foreign-overlap negatives are covered. |
| G7-09 | Parent/required-child search is bounded and atomic; required/optional failure restores reservations, metadata, dependencies and caps. No half-required compound publishes. |
| G7-10 | One exact saved external attachment and canonical shared circulation connect all accepted child access; typed internal access does not pretend country frontage; independent graph negatives reject. |
| G7-11 | Final populated scene validates every committed child's full required doorway spans and usable goals, including a later child's obstruction; representative native updates and actual production views pass. |
| G7-12 | Format 5/wg7 has reciprocal parent/slot/plot/placement/path/node ownership and parent-count integrity; historic format4/v1 policy and literal featured identity remain unchanged. |
| G7-13 | Saved resolved recipes need no current recipe selection; policy/recipe-only edits preserve pending composition; unchanged structure-v1 retains affected-only consumed-child failure and visited/unaffected positives. |
| G7-14 | Genuine G6 visited mutation/plan identity/provenance survives; pending scene uses explicit G6-to-G7 path; G3/G4/G5 and legacy positives remain; no historical compounds are synthesized. |
| G7-15 | Same-asset children in one scene have distinct mutable content through real interactions, cold load and F9; two same-recipe parents and reversed visits retain separate identity/state. |
| G7-16 | Checksum-consistent parent/child/path corruption fails real preparation before installation; late child/access failure leaves player/RNG/cache/actors/Chunk/visit/checkpoint state unchanged; recovery remains positive. |
| G7-17 | All three ordinary seeds meet total/kind minima and all accepted child scenes/goals validate. All results, absent recipe occurrences, parent/child frequencies, work and cost denominators are retained. |
| G7-18 | Real-handler journey enters a natural compound from its country join, uses every required child and a single site, retains required earlier destinations and coherent rollback, with disclosed controls. |
| G7-19 | Six complete owner workflows execute, preserve edited drafts, use actual browser-downloaded child JSON in whole-compound preview, and retain both browsers/frozen corpus/live catalog behavior. |
| G7-20 | Frozen final inputs pass full focused, browser, authoring/catalog, diagnostic/journey and unfiltered production gates; raw/canonical source reconciliation resolves tested-input claims; delivered main and immutable remote tag agree. |

## 10. Final gates and source evidence

Work in order: authentic G6 capture and before probe → small admission correction → recipe/policy/shared fitting with persistence integrated → lifecycle/journey/owner workflows → final freeze and complete gates. Run focused checks at meaningful boundaries. Retain failed attempts and their actual inputs. Do not repeat a broad gate solely to accumulate reassuring counts.

Reuse the established interpreter and existing entry points. Known G6 forms are below; confirm current arguments and the preflighted disposable-root policy in the actual checkout. Extend G6 diagnostic and executed-authoring tools with clearly named G7 entry points or thin wrappers.

```powershell
$ResonancePython = '<existing project interpreter>'
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --evidence evidence/worldgen-g7/focused
& $ResonancePython -X utf8 tools/verify_structure_editor.py --evidence evidence/worldgen-g7/browser
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/worldgen-g7/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
& $ResonancePython -X utf8 tools/verify_d.py
```

Recommended new forms are `tools/worldgen_g7_diagnostic.py --journey --evidence evidence/worldgen-g7/diagnostic` and an executed G7 authoring workflow. Implement and document actual interfaces. Do not silently leave production worker outputs under an unguarded new root. The full unfiltered production gate, normal focused discovery, inherited controls, both browser engines and actual download consumers remain required.

Freeze executable code, runtime data/policy/recipes, tests, fixtures, editor, source discovery and documented command inputs at an immutable gate-input commit. Include new recipe file types/paths in manifests. Bind each command to commit, complete input hashes, args/cwd, interpreter/library/browser versions, seeds/policies, exit/timeout and output inventory. Run timing-sensitive long gates serially under declared load with justified bounded timeouts.

G6's retained manifest claimed 421 exact plus 239 line-ending-only inputs. Review independently reconstructed 421 plus 238; one authoring Markdown raw representation was unavailable. Mixed endings remain possible and no prose mismatch was established. **Close this evidence ambiguity in G7**: record raw hashes and a clearly defined canonical-LF text hash, and preserve the raw tested document when checkout representation cannot be reproduced from the committed bytes. Normalize only line endings for this comparison, not arbitrary whitespace/content. Binary files remain exact. Do not retroactively assert that missing G6 bytes were recovered unless they actually were.

A final documentation/evidence-only commit is allowed only after comparison proves every tested input unchanged. The owner guide or example itself may be a tested input; a `.md` suffix is no exemption. A later code/data/test/recipe change requires appropriate verification and the required final gates again. Retain the exact failed freeze/source identity if any gate needs correction.

Keep raw jobs/results/assertions, imported-source bindings, negative controls and receipts. Compress bulky evidence with member names, sizes, hashes, CRC-verifiable archives and a readable index. Preserve prior archives. Omitted disposable save payloads must have explicit scope/inventory rather than implying retained bytes were verified. Do not commit personal campaigns, entire production source ZIPs, environments or incidental browser profiles.

## 11. Owner report and evidence package

Create `docs/owner/WORLDGEN_G7.md` with the practical outcome, how to add/edit a compound, installed recipe/policy paths, parent/child counting, accepted/omitted ordinary results, access/ownership contracts, saved-world behavior, acceptance matrix, actual verification identities, retained failures, limits and next recommendation.

Create `evidence/worldgen-g7/` with before/after goal results, authentic pre-edit G6 fixture and binding, recipe/transform/ownership/rollback/corruption cases, ordinary plans and compact metrics, populated production views, interactions/journey, executed authoring/browser downloads and full gate/source records. Use the tested/disposable guard correctly. Include one readable index linking the important results and describing controlled fixtures versus ordinary worlds.

Report tested-input SHA, delivered SHA, verified checkpoint and inspected remote. Explain any relevant advance from the reviewed starting reference. Distinguish the number of parent destinations, child buildings, successful interactions and generated scenes. Report focused discovered/passed/skipped/failed/error totals and skip reasons explicitly; do not conflate this review's Linux 188 passes plus one Windows-only skip with retained Windows 189 passes. Retain inherited deferred items such as `UI-TEXT-HEIGHT` and larger-world retention/streaming; do not imply G7 resolves them.

## 12. Deliver and stop at G7

Deliver the admission correction, two working compound recipes, mixed parent selection, shared access, durable ownership/compatibility and complete owner workflows on existing main. Finish all required gates, reconcile final source, commit task-owned documentation/evidence, push the authorized main changes and unique verified tag, then read the remote to confirm them.

**Stop after G7.** The next review should assess whether compounds look coherent and are easy to author before choosing richer settlement/street composition. Large-world retention/streaming and the continuous viewport remain later arcs. Do not start those features or generate additional speculative implementation briefs as part of G7.

## 13. Focused primary-source design references

These sources inform the design; the mapping to Resonance is an engineering recommendation, not a claim that their systems prove this game's correctness.

- [CDDA official overmap documentation](https://docs.cataclysmdda.org/JSON/OVERMAP.html): explicit roots, connection rules and required/available joins provide a useful vocabulary for authored compositions. Use a bounded recipe here, not its complete growth system.
- [Alaka and Bidarra, Hierarchical Semantic Wave Function Collapse, 2023](https://pcgworkshop.com/archive/alaka2023hierarchical.pdf): preserve authored parent/child meaning when refining a place into concrete content. G7 does not require WFC.
- [MANSION, March 2026 preprint, §3.1 and Appendix C](https://arxiv.org/html/2603.11554v1): separate intended connectivity from geometric realization and check feasibility before selecting an attractive layout. Its 3D/MLLM implementation is outside this task.

The companion review gives the research scope and limitations. Actual Resonance production geometry, complete scenes, interactions and saved-state tests remain the acceptance authority.
