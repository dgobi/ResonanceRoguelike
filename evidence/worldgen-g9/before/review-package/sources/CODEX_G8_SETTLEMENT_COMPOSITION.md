# Codex G8 — Settlement streets, blocks, frontage and maintained owner wiki

**Project:** Resonance Roguelike.  
**Repository:** https://github.com/dgobi/ResonanceRoguelike  
**Reviewed reference:** `main` at `8e56d36d72537e8b32c3666dd5d19723d1afdf3a`, `checkpoint/worldgen-g7-verified-20261024-a`.  
**Prepared:** 24 October 2026, America/Edmonton.  
**Companion:** `G7_REVIEW.md` and the review evidence supplied in this package.

## 1. Implement this outcome

Make new settlements read as deliberately composed places: streets define usable blocks and building frontage, a grid town has a protected civic common beside its spent bell, and existing buildings address both horizontal and vertical streets. Give the owner a small, documented JSON interface for changing those layouts and previewing the complete result.

Begin with the concrete corrections identified by this review: prevent preview commands from overwriting authoring inputs, make the documented focused-test runner independent of an inherited Python import path, and repair the wiki's repository integration. Deliver those corrections and the bounded settlement feature in this arc. Complete the G7 wiki catch-up as well as the new G8 instructions, build the offline HTML, and establish a repeatable update workflow.

The prior course was to review G7 composition and authoring before choosing settlement/street work. This is that scoped choice. The G7 review found a sound runtime base, a real draft-preservation defect, an import-path defect in the direct test command, a stale/unrebuildable wiki workflow, and measurable settlement limitations. There is no requirement to repeat G7 as a separate feature arc.

### Visible acceptance

- Ship **exactly two current grid-town layout profiles**, materially different and orthogonal, within the existing 160 × 86 tile footprint. One may develop the existing regular form. Their street/block/civic arrangement must differ; renaming, rotating, or slightly jittering the same four lines is insufficient. Historical layouts remain available through compatibility paths.
- Each shipped grid layout must demonstrate occupied frontage on both street axes with the installed content. Controlled complete examples must demonstrate north, south, east and west frontages using permitted building transforms.
- Give each grid town a real, accessible civic common or forecourt associated with its existing spent-bell building. This is protected public ground with usable circulation, not just a label in metadata.
- Improve the existing 160 × 43 horizontal roadside settlement through frontage derived from its actual country-road segment. Its north/south frontage remains appropriate. A vertical roadside form is outside this arc.
- Preserve required residential/commercial/civic roles, accepted-asset caps, bounded search, intentional vacancies, native town behavior, complete-scene ownership and saved-world guarantees.
- Deliver complete executable authoring examples, a reviewed wiki edition covering G7 and G8, and a self-contained `Resonance_Owner_Wiki.html` that opens locally without a server.

Stop at the G8 boundary in section 12. Country-network optimization and world scaling remain later decisions.

## 2. Execution and preservation protocol

Use the owner's **existing production checkout on `main`**. Read applicable `AGENTS.md`, inspect status, HEAD and remotes, and preserve all unrelated work. This review package's Linux checkout is evidence, not the implementation location. If main has advanced, inspect and record the intervening changes; do not reset to the reviewed SHA.

Continue the established scoped-commit, immutable-checkpoint and verified-push workflow. When the owner gives Codex this brief to execute, the requested delivery includes the implementation, autonomous verification, scoped commits and publication to the existing remote `main`, followed by remote commit/tag readback. Preserve any more specific instructions in that execution session. Do not create a PR, task branch, worktree or second development source checkout. Never move an existing checkpoint tag or force-push.

Use the established Python environment as a dependency source while importing game code from the production checkout. Run tests headlessly or with app-local events, using disposable save roots. Do not take over the desktop, use personal campaigns or assign routine verification to the owner. Keep G1–G7 evidence, genuine historical fixtures and the frozen editor corpus.

Use meaningful checkpoints for start, authoring protection, wiki integration, composition, lifecycle, authoring/docs, final inputs and verified delivery. Stage task-owned paths explicitly. Deliver Markdown and machine-readable evidence; no PDF report.

### Before the first implementation edit

1. Record actual starting source, interpreter/dependency versions, status and remotes. Reproduce the supplied CLI collision cases in disposable drafts and retain their original outcomes.
2. Capture a **genuine G7 format-5 compatibility witness** before changing the materializer or planner. Include a visited town member with a recorded content mutation, a still-pending member of that settlement, a visited compound with independent child state, and a still-pending accepted rural parent. A second small witness is acceptable if it makes these states clearer. Preserve exact plan/checkpoint bytes, scene inventory, source hashes, creator provenance and fingerprints. Label direct fixture actions; use actual interaction handlers when claiming player interactions. If intervening source already changed, reuse a genuinely bound G7 witness rather than relabeling current output.
3. Capture the same-machine G7 planning/materialization baseline for ordinary seeds `0`, `20261023`, `29417`, and preserve complete plan identities. Reuse a correctly bound existing run on the actual machine when available.
4. Preflight the production worker's disposable-root guard. Use an already permitted `.baseline` location or narrowly admit the new G8 evidence root, retaining marker/source/save checks. Prove an allowed worker and rejection of a synthetic outside-root directory before save access.

## 3. Starting architecture and exact boundaries

G7 fresh worlds use format 5 / `wg7`. The world remains 128 × 128 chunks of 80 × 43 tiles. Grid settlements occupy 2 × 2 chunks; roadside settlements occupy two horizontal chunks. Two through four additional rural parents include at least one compound and one single site; the featured landmark remains separate. Compounds have two required children and at most one optional child, contained in one chunk.

Read the existing consumers and validators before editing: `world_plan.py`, `settlement_selection.py`, `settlement_context.py`, `placement.py`, `planned_scene.py`, `planned_dressing.py`, `plan_integrity.py`, `road_network.py`, `scene_adapters.py`, `poi_selection.py`, `parent_selection.py`, `compounds.py`, `compound_integrity.py`, data loading, world publication and save preflight. Read G7's owner guide, tests and release wrapper. Read the wiki builder, validator, configuration, maintenance chapter and recorded audit.

Current town geometry is the limitation. In the three retained G7 plans there are 11 towns, 272 proposed town plots, 233 occupants and 39 vacancies. All 272 frontages face north or south. No occupant addresses a vertical grid street. The six grid towns share one relative street arrangement. These are descriptive sample results, not universal probabilities or occupancy targets. The existing grid **already has a rectangular local street cycle**.

| Responsibility | G8 boundary |
|---|---|
| Settlement locations/counts | Preserve existing site search, spacing, near-start requirements and finite extent. |
| Country routes/crossings | Preserve the backbone algorithm, exact road and bridge authority and existing attachment contract. Route geometry may remain an obstacle/input to local composition. |
| Town extent | Keep current grid and horizontal-roadside member footprints. |
| Building ownership | Complete building, private buffer and full approach remain inside one 80 × 43 chunk. |
| Street/common geometry | May span existing settlement member chunks as one saved world-coordinate plan, then be sliced. |
| Rural places | Preserve G7 recipes, mixed-parent counts, country attachments and child ownership. |
| Native gameplay | Preserve `native-town-v1`, spent bells, waystone/prayer behavior, population, resources and scene lifecycle. |
| Structure semantics | Preserve consumed transform permissions and `structure-v1`; selection/layout intent stays separate from consumed building definitions. |
| Later work | Strategic road loops/optimization, vertical roadside towns, organic cities, new capital districts, cross-chunk buildings, world size, streaming/retention, continuous viewport, economies and a graphical town editor. |

Do not turn the limited compound recipe schema into a town schema. Reuse its proven fitting, explicit bounds, staged publication and narrow reservation principles.

## 4. A — Protect authoring inputs and make the test entry point self-contained

### Prevent diagnostic writes from replacing inputs

The reviewed `tools/structure_authoring.py` checks the JSON output against only the positional candidate. It omits `--compound`, repeatable `--child`, configuration/access inputs and initializer targets. Automatically emitted SVGs have no equivalent destination check.

The supplied reproducer shows four successful commands that destroy a disposable source draft: report overwrites recipe; report overwrites child; `--init-compound` reports preserving a child and then overwrites it with the report; automatic SVG follows a symlink into the recipe. These are authoring data-loss failures. They do not demonstrate campaign corruption.

Implement a small coherent destination-validation boundary for the existing CLI, and use it for the new G8 preview outputs:

1. Identify every explicit read input: positional candidate, compound recipe, every child, `--poi-config`, `--selection-config`, `--config`, `--access`, `--editor-catalog` in check-only mode, and any new layout inputs. Protect initializer target names from diagnostic outputs, including targets that do not yet exist.
2. Identify every actual write target: main JSON report, automatically derived SVGs, initialization files and any explicitly requested editor-catalog output. Validate known destinations before running work or performing mutations. Stage dynamically named output artifacts and validate their complete destination set before publishing them.
3. Reject collisions using resolved paths and same-file identity where supported, covering relative aliases, symlinks, existing hard links and the platform's path semantics. Apply the installed game/data protection to every output, including derived diagrams and aliases. Do not allow an output or another generated output to replace an input implicitly.
4. Give a concise diagnostic naming the conflicting input and output. An invalid invocation must preserve input bytes and must not partially initialize drafts or refresh a catalog before reporting the error.
5. Keep legitimate distinct-path preview output, deliberate replacement of a previous evidence report, and the explicitly requested catalog refresh working. Avoid a blanket ban on useful writes.

Initialization copies and an explicitly requested editor-catalog refresh are designated intentional writes. Initialization may create absent draft targets and must preserve existing ones. Reports, diagrams and other diagnostic outputs must remain disjoint from those targets. A catalog refresh must remain disjoint from unrelated read inputs. These narrow intentional-write rules must not become general exceptions to input protection.

Use the supplied four reproductions plus parameterized representative collisions for the other input flags, a distinct-output positive, and a repeated-initialization preservation positive. Assert before/after bytes, failure exit status and useful errors. Keep fixtures disposable. Commit/checkpoint this correction before extending the CLI.

### Correct the focused runner's import environment

The independent unmodified focused run discovered 202 tests: 200 passed, one Windows-only PowerShell case skipped, and `test_ordinary_compound_updates_and_both_production_views` errored at `from g7_visuals import render_compound`. The direct `verify_fixes.py` command gives its child only the game and test directories, while `g7_visuals.py` lives in `tools/`. The release wrapper explicitly adds `tools/` through `PYTHONPATH`, explaining why the retained Windows gate passed. This is a runner-entry-point defect, not contradictory historical evidence.

Make the runner provide its required absolute tool import path explicitly, without requiring shell setup. Preserve current-checkout source selection, ordinary discovery and renderer/native-update coverage; do not remove or skip the failing test. Prove the documented direct command from a parent process with no `PYTHONPATH`, and retain compatibility with the release wrapper. The final full focused gate may provide this clean-environment proof, avoiding a redundant broad run. Retain the original failed review receipt and the separate targeted result.

## 5. B — Make the tracked wiki maintainable

The owner has commissioned the wiki as an ongoing resource. Treat its maintenance as part of feature delivery. The tracked package remains edition 1.0/G6 at `4d7a789…`; its main chapters still say compounds are unavailable. No compiled HTML is tracked at the reviewed HEAD.

### Repair the revision and input model

The current builder requires both `HEAD == wiki-config.commit` and an entirely clean tracked tree. Updating the tracked configuration makes the tree dirty; committing it changes HEAD again. It fingerprints all tracked files, including its own manifest/build report, then rewrites those files. It also collects the wiki's own 31 chapters again as original source documents. The validator shares those assumptions. These problems arose when an external maintenance package became part of the repository.

Introduce an explicit, shared builder/validator contract with three scopes:

| Scope | Required treatment |
|---|---|
| Reviewed game and authoritative-document inputs | Pin a real source revision and an explicit path scope. Read those blobs from that revision, or verify the checkout's scoped inputs against it. Detect changed, added and missing relevant inputs. |
| Wiki authoring inputs | Hash chapters, examples, theme, reader, builder, validator and configuration separately. Record exactly which bytes built the edition. |
| Generated products | Exclude HTML, manifests, build/validation reports and audit outputs from their own input hashes. Do not archive the wiki's guide chapters again as game-source documents. |

Record source revision and documentation delivery revision separately. A later commit containing only the wiki's reviewed metadata/products must not invalidate unchanged game-source inputs. Immutable source links should use the reviewed source revision; the validator must check the same policy, including relevant ordinary guide links. Do not silently convert links to moving `main`.

Preserve fail-closed behavior for unreviewed source changes. Do not remove all guards, point the edition at the latest SHA without review, or run `--write-manifest` merely to suppress drift. Permit the intended wiki editing/build sequence by scoping checks correctly, rather than requiring an impossible clean-tree/self-hash cycle. Use small metadata and the existing scripts; a documentation platform migration is unnecessary.

Remove hardcoded G6 coverage/classification and first-edition audit claims from generated current-edition prose. Store edition-specific reviewed evidence explicitly. Preserve the old Linux audit, original findings and previous editions as historical records with their own dates/revisions.

### Required maintenance checks

- Two successive unchanged builds and drift checks succeed without self-generated input drift or duplicate guide chapters.
- A later documentation-only delivery commit preserves the intended source binding.
- A changed/added/missing in-scope game input is detected; an unreviewed source mismatch cannot be hidden by rebuilding.
- Changed wiki authoring input invalidates stale products; a missing input and deliberately stale output are rejected.
- Builder and validator agree on revision, input scope, pinned links, catalogue coverage and output hashes.
- The offline HTML has working navigation/search, code-copy controls and internal links; inspect the real document in available headless browsers or app-local tools. Disclose limits of that inspection.

Use tiny synthetic repository fixtures when a commit transition must be tested. They must contain only documentation-test inputs, not a second game checkout. They are disposable test data under the standing protocol.

### Ongoing contract

Update the repository's existing owner/developer instructions with a concise rule: a feature that changes owner workflows must update affected authoritative guides and wiki chapters/examples, rebuild and validate the edition, and record its reviewed source/evidence. When a change has no handbook impact, record that scoped conclusion. This is a delivery rule, not an unattended scheduled job or a requirement to rerun every game gate for a prose correction.

Complete the G7 chapter corrections now, then incorporate G8 before the final edition. Preserve the soothing dark interface, offline operation and existing navigation conventions.

## 6. C — Plan settlement streets, public space and blocks together

### One bounded composition stage

Extract the hardcoded settlement geometry into a small deterministic composition module and versioned data interface. Prefer a clearly named file under `roguelike/data/generation/`, separate from asset/role selection. The exact new schema is implementation work; deliver a complete validated example after it exists. Do not document proposed field names as already consumed.

The layout input must provide stable identities, form eligibility, bounded geometry/parameters, positive selection weights, a finite alternative/search policy and useful author-facing errors. A small set of orthogonal templates with controlled parameters is appropriate. A general grammar, polygon CAD system or tensor-field implementation is unnecessary for these town sizes.

For each town, resolve composition **before** filling buildings:

1. Establish the fixed member bounds and actual incoming/outgoing country-road geometry. Identify a canonical primary arrival from the real incoming route's entry into the bounds, including route/segment/position and direction; do not call the first enumerated plot the arrival.
2. Choose and validate the layout using stable seed streams and canonical weighted memberships. Reserve street bands, necessary junction space and civic/public circulation before proposing private lots.
3. Derive bounded blocks/frontage intervals from those actual bands and public space. Exclude intersections, incompatible country-road intrusion, protected infrastructure and unavailable chunk-edge building space.
4. Propose explicit lots, then use the existing production fitter and required-role search to choose legal assets/transforms.
5. Validate and publish the whole resolved settlement only after its required streets/common/civic/role obligations succeed. A failed layout alternative leaves no plots, reservations, dependencies or accepted counts behind.

The country backbone already exists and must not be rerouted to make a preferred layout fit. Use bounded local alternatives and explain genuine inability to satisfy a required town. Preserve the distinction between exhausting alternatives and exhausting a finite work budget. Count nested fitting work explicitly; do not multiply the current required-fit budget by an unbounded layout search.

Use a separate stable layout-selection stream. Changing local presentation must not consume the geography/country-routing stream or perturb the same-seed backbone incidentally. Compare country-route geometry directly against the opening baseline.

### Two useful grid layouts

Choose two clearly distinct, feasible arrangements, for example a market-square core and an offset cross-street/side-common form. The names are suggestions, not a demand for a particular geometry. Certify both through the production fitter and full materializer, including existing country-road intrusions.

Both should have a legible relationship among arrival, civic building, public common, commercial frontages and residential/support areas. At least one enclosed street block/circulation cycle should remain useful; do not add streets merely to inflate cycle counts. Maintain a connected road slice within every member chunk, consistent with the existing spawn and local-access contracts. A new global-portal navigation model is outside scope.

Validate that local-slice property during layout admission. A globally connected pattern that needs to leave and re-enter a chunk to connect that chunk's road slices is outside this contract; reject it with a useful explanation rather than weakening final access validation. Preserve exact shared-boundary bands.

Preserve open ground intentionally. An empty plot caused by cap/fit failure is different from a planned common, yard or garden. Record these purposes and visualize them separately. There is no target to maximize building occupancy or increase town density.

### Civic space has physical and native meaning

Save the public common's actual geometry, ownership, purpose, surface treatment and connection to the street system. Paint and protect it through the normal complete-scene materializer. Required walkable circulation must survive later building stamping, contents, dressing and initial native population.

The common sits beside the retained civic building/forecourt relationship; it does not absorb the building's private footprint. Use narrow explicit ownership for shared public geometry and parcel containment. A block or town ID must never become a blanket exemption allowing sibling buildings to overlap or foreign owners to consume public space.

Retain exactly the existing required spent-bell semantics and derive the civic member from the accepted bell placement. Account for the waystone and prayer/readable placement explicitly: protecting public circulation must not eliminate the eligible positions needed by `native-town-v1`. Show real interaction access to those features in the complete scene. Keep functional furnishing cells distinct from required clear circulation when needed.

### Roadside settlement

Keep its actual horizontal two-chunk country segment and existing town semantics. Derive frontages from the real finite band, excluding junction/bend/end conflicts, rather than sampling every chunk-center x position and discovering that no assigned road exists there. Use the same lot/fitter interface and clearer vacancy diagnostics. Do not force east/west occupants into a form that offers only north/south street frontage.

## 7. D — Fit plots from real frontage and retain selection guarantees

### Explicit frontage and lot records

A proposed plot needs a stable semantic ID, settlement/block association, actual public route/segment reference, join/frontage span, outward normal, buildable bounds, setback and clearance constraints. Prefer simple integer tile geometry compatible with existing rectangle operations. Resolve the full doorway width against the assigned street band; a nearby unrelated street or diagonal corner touch is insufficient.

Use stable IDs derived from layout/block/lot identity, not the chosen asset, failed attempts, global `len(plan['plots'])`, input dictionary order or visit order. Where ordered filling is meaningful, save an explicit stable order separate from identity.

Reuse `_plot`, `plot_options`, transforms and `explicit_bounds` support. Extend the shared interface where needed instead of copying a simplified town-only fitter. Require the full private buffer within the assigned private lot, and keep the entire building/buffer/approach inside its storage chunk. Handle corner lots by choosing one legal declared primary frontage; do not double-own the same parcel or ignore a second street's reservation.

Supply independent small fixtures for all four normals, road widths, full-width doors, junction clearance, corners, wrong segment, chunk edges, private buffers and public overlap permissions. Retain the existing wide main/service-door and sibling/foreign-owner negatives.

### Reuse asset and role selection

Keep `settlement_profiles.json` as the authority for role memberships, asset base weights, role weights, per-settlement caps, minima and ordered optional schedules. Do not add a second district selector that bypasses these guarantees. Required-role backtracking still counts actual transform trials, stages complete branches and reserves accepted counts only.

The installed all-quarter-turn cohort already includes `bell_tower_a`, `market_stall_a`, `workshop_a`, `house_small_a` and `house_two_room_a`. Use those on compatible east/west frontage. Other selected assets permit only 0°/180°; retain their permissions and horizontal opportunities. The support cohort currently needs horizontal frontage. Custom role minima must either fit that capacity or fail clearly and atomically.

Make civic/commercial ordering refer to the actual saved arrival/common. Update the nearest-neighbor repetition preference for fresh G8 selection to use explicit plot/frontage geometry and stable ID ties; current slot-index distance is inadequate once plots run around blocks. Define the distance metric and denominator. Preserve asset-first weighting, canonical unordered memberships and intentional schedule order. Additional transform opportunities must not silently multiply an asset's probability.

Default complete grid examples and the ordinary seed matrix must contain actual occupied frontages on both street axes. Controlled certification of each shipped layout must exercise all four normals. Optional vacancies remain legal, and author-edited pools must receive truthful capacity/fit diagnostics rather than implicit transform permission changes.

## 8. E — Persist resolved G8 intent without recomposing old worlds

Use **plan format 6 / origin `wg8`** for the new saved settlement layout/public-space/lot contract. Keep `shared-v1`, `structure-v1`, campaign storage and native policy. Preserve exact interpretation of earlier plan formats and retain explicit historical fresh-policy paths used by existing tools/tests. New layout policy must never be applied retroactively to an old plan.

Decouple the new settlement-layout version from the POI-policy switch. Currently `world_plan.build_plan` selects format/revision from POI policy v2, and `poi_selection.validate_resolved` dispatches every format ≥5 to the v2 parent validator. Define and test G8 layout settings with the default mixed-parent policy, an explicit v1 single-site policy, and a v2 policy with explicit zero rural-parent counts. The settlement geometry must retain its correct G8 identity in all supported G8 combinations; choosing a single-site opt-out must not silently label new geometry `wg6`/format 4. Retain the documented selection/count meaning of the opt-out. Dispatch by the actual saved contract, not an increasingly inaccurate format-threshold shortcut.

The saved G8 plan must contain the resolved layout choice, exact street/public geometry, block/lot/frontage relationships, civic association, accepted occupants and explicit vacancies. Pending scene creation must not consult current layout recipes or selection profiles to redraw those decisions. Editing/removing a layout recipe should not break an existing compatible saved plan. Changes to consumed building definitions retain affected-only pending-scene rejection; visited scenes and unaffected pending scenes remain usable. Define equivalent validation for any newly consumed public-surface definition without bloating the building dependency projection with unused selection metadata.

Use one authoritative location for geometry. Existing route records continue to own road geometry; derive any junction graph or lookup index from them. Do not persist an independently editable duplicate road graph. Logical block bounds must not grant private-overlap permission. Save validation must check both directions of every new settlement/block/plot/common/frontage reference, exact geometry/reservations and ownership.

Extend plan headers, slice generation, save preflight, provenance and adapter dispatch consistently. Preserve the actual creator of visited G7 scenes. Pending older scenes may use an explicit current adapter, with the plan's original version/revision retained. Test genuine G7 witnesses and existing G3–G6 fixtures. Do not generate a G8 scene and label it G7 to satisfy a compatibility test.

Keep complete chunk scenes as the sole runtime/cache/save owner. Multi-chunk streets and commons are plan geometry, not separately mutable scenes. Reverse member visits, same-asset occupants, child compounds, cold load and F9 must preserve independent content and player mutations.

Add checksum-consistent save corruptions for wrong frontage owner/segment, duplicate or foreign lot membership, overlapping private bounds, missing public geometry, conflicting common/civic references, bad reservations and incompatible version/provenance. Validation must fail before installation. Inject a late materialization failure after another building/common pass and prove player, RNG, active map/actors, Chunk metadata, cache, world and checkpoint HEAD remain unchanged, with successful recovery after removing the fault.

## 9. F — Owner workflows and the updated wiki

Extend the existing CLI and source guide with complete, copyable workflows. Any new flags must use the input/output safeguards from section 4. Draft previews must not install files or open personal campaigns.

Execute and document at least these workflows:

1. Inspect and preview each installed grid layout with a fixed seed, labelled plan and complete populated scenes.
2. Initialize/copy a complete draft layout/profile without overwriting edited files; make one meaningful geometry change and preview it before installation.
3. Change lot/frontage dimensions or public-common geometry and get useful failure diagnostics for an unfit required role/civic arrangement.
4. Use an existing legal child-building export on east/west town frontage, and show that an asset lacking the effective rotation is rejected or excluded with a reason.
5. Tune the existing selection profile while keeping its weights/caps/minima visible; explain what changes in a new world and what remains saved in an existing campaign.
6. Demonstrate deliberate installation of a valid layout and ordinary selected-world previews against a disposable data catalogue/authoring root, with sentinels proving unrelated inputs were preserved. Document the separate production installation and version-control recovery procedure without staging/reverting owner files merely to demonstrate it or modifying a campaign.

Preserve and rerun the existing G5/G6/G7 workflows through the actual production consumers. Continue using the existing layout painter for individual buildings; a graphical block editor is not required. Real browser-exported bytes must reach the applicable direct/assigned consumers when that workflow is claimed.

### Wiki content requirements

Update the main guide chapters, not only the embedded original-document archive. At minimum review world generation, rural sites, settlement tuning, first building, structure reference, layout painter, troubleshooting, saves/state, verification, code map and maintenance. Add a dedicated compound or settlement-composition chapter when that improves navigation; preserve stable existing links where practical.

The G7 catch-up must explain parent versus child counts; v2 mixed policy; recipe, child and selection files; shared paths/private buffers; permitted transforms; optional omission; required usable goals; safe previews and installation; saved composition versus consumed-child compatibility; format 5 / `wg7`; and the effect of intentionally selecting a legacy v1 single-site policy.

The G8 edition must explain the new layout/lot/common controls, actual consumed fields, civic/native constraints, cardinal frontage, capacity failures, saved-world behavior and examples. Distinguish current behavior, legacy routes, proposals and inactive fields. Update edition history, coverage and evidence scope based on actual runs. Preserve historical findings rather than silently marking all old audit limitations resolved.

Build and validate the standalone HTML and the editable maintenance package. Record a stable output location in repository instructions. Provide the HTML directly in the completion package; the owner should not have to reconstruct the wiki merely to read the new instructions.

## 10. Verification and review evidence

Use a small set of focused, behavioral checks plus the established release gates. Avoid tests that merely mirror a serialized field or implementation detail. A healthy test must expose an access, ownership, authoring, preservation, determinism or workflow failure.

### A. Geometry and population

Certify both layouts and all supported transforms through actual fitting/materialization, with independent small expected-geometry negatives. Show street/common joins, occupied frontages, full door spans, usable goals and native civic features after all content/dressing/population. Include a bounded native-update positive. Preserve rural-parent and compound validation.

### B. Ordinary worlds and determinism

Run ordinary seeds `0`, `20261023`, `29417` without forcing layout choices. Materialize every town member, accepted rural parent and the existing required destinations. Keep planning lazy: zero created local scenes at plan completion. Controlled fixtures certify a layout absent from the ordinary sample; do not change seeds after seeing results to disguise a gap.

Vary process hash seed, unordered profile membership order and first-visit order. Compare complete resolved plans and relevant populated scene fingerprints. Keep intentionally ordered schedules meaningful. An input reorder that claims no semantic change must not reroll a new plan.

### C. Composition and network measures

For each town report layout ID/signature, block/common area, candidate/occupied/vacant plots, frontage normals, assigned horizontal/vertical street usage, roles/assets/caps, required and optional fit costs, and categorized rejection/vacancy reasons. Compare the same measures against the supplied G7 baseline. Public space is deliberate space, not failed occupancy.

Measure actual local travel distances from saved arrival to civic/commercial/residential destinations. Define endpoints, units and denominators. If reporting frontage coverage, measure an actual street-frontage length ratio; do not relabel plot occupancy as coverage.

For meaningful loops, derive a centerline junction graph with intersections and shared segments reconciled, and contract degree-two runs as appropriate. Current route `a == b == settlement_id` is not a loop count. The full-width tile graph also contains trivial cycles inside a straight wide road. Neither is evidence of a useful alternate route. Use the derived geometry/topology and actual distance/alternate-path witnesses, while keeping final populated-scene access separate. Do not claim G7 had no loops.

### D. Real journey and persistent state

Extend the existing real-handler journey from country arrival into a grid common, along both street axes, to representative residential/commercial contents and the native civic features. Retain bridge, other settlement, landmark, compound-child and single-site coverage. Use actual production movement/interactions/doors/travel/save/load handlers. Disclose stationary actors, paused AI/survival, invincibility or fixture positioning separately from ordinary updates.

Include a checkpoint that actually contains explored G8 town scenes and an explored compound. Measure its scene count, bytes, save/cold-load/F9 times and preserved mutations. The old two-starting-scene journey checkpoint is not a benchmark of the later explored world. A long-campaign storage redesign remains outside scope.

### E. Costs and visual inspection

Measure planning, layout/candidate/fit work, plan bytes by relevant subtree, complete scene creation, worst observed transition and the explored checkpoint. Compare G7/G8 on the same interpreter/machine and disclose sample size. Explain material changes; do not claim a Windows-versus-Linux difference is a regression or invent a universal frame-time target.

Retain populated production-renderer views of both grid layouts and the roadside result, with plan overlays or separate diagrams showing streets, common, lots and entrances. State whether visibility is revealed. Inspect coherent grouping, facade direction, readable public space, awkward dead strips and excessive repetition. A diagram proves geometry; it does not replace a gameplay view.

### F. Final release gates

Freeze the complete intended runtime/test/authoring inputs in an immutable commit/tag. Run serially with finite documented timeouts:

- disposable-root preflight;
- normal unfiltered focused regression discovery;
- applicable browser/editor export checks in both established engines;
- new and inherited authoring workflows;
- structure catalogue and editor catalogue freshness;
- ordinary diagnostics plus the real journey and production views;
- wiki build, integrity/drift checks and actual reader checks;
- the unfiltered production gate with its existing negative controls and coverage requirements.

Reuse an existing passing receipt only when the exact relevant input identity and scope are proved unchanged. If a tested input changes after freezing, rerun affected gates; when using the current wrapper's unified input set, follow that wrapper's full-rerun rule. Wiki outputs require their separate source/wiki-input binding from section 5, so a documentation delivery commit does not create a circular runtime freeze.

Retain commands, cwd, interpreter/tool versions, exit/timeout status, source identities, raw and canonical-LF text hashes and output inventories. Binary inputs remain exact. Preserve raw tested text when newline normalization cannot reconstruct it. Keep failures/timeouts distinct from final successes. Do not add nested workflow counts as if they were independent top-level workflows.

## 11. Completion matrix and delivery

Map each item to source and actual evidence in `docs/owner/WORLDGEN_G8.md` and an evidence index.

| ID | Required result |
|---|---|
| G8-01 | Actual start, preserved owner work, genuine G7 witness and guarded disposable execution. |
| G8-02 | Authoring collisions reject before mutation; inputs remain intact; legitimate writes work; the direct focused command works without inherited `PYTHONPATH`. |
| G8-03 | Wiki source/authoring/output scopes are explicit; repeat builds and later docs commit work; stale/missing/changed inputs fail correctly. |
| G8-04 | Two distinct certified grid layouts and real civic common within unchanged member bounds. |
| G8-05 | Exact saved arrival and street geometry drive blocks/frontages; existing country routes/crossings remain authoritative. |
| G8-06 | Actual occupied grid frontages on both axes; controlled N/S/E/W and full-span geometry prove permitted transforms. |
| G8-07 | Roadside frontages derive from the real horizontal segment; meaningful vacancy/exclusion reasons. |
| G8-08 | Lot/private/public ownership, chunk containment and reservation replay withstand independent negative fixtures. |
| G8-09 | Required roles/civic/public access use atomic bounded search; failed/optional branches leave no state residue. |
| G8-10 | Existing selection weights/caps/minima/order semantics remain; spatial repetition has a defined stable metric. |
| G8-11 | Full populated access and spent-bell/waystone/prayer behavior survive complete materialization and native updates. |
| G8-12 | Format-6 resolution, reciprocal records, exact slicing, explicit adapters and valid layout/POI-policy combinations preserve older saved plans. |
| G8-13 | Current recipe removal does not recompose pending scenes; affected consumed changes reject locally; visited state remains authoritative. |
| G8-14 | Genuine G7 and existing historical fixtures pass; independent owners, reverse visits, cold load/F9 and late-failure rollback pass. |
| G8-15 | Ordinary seed matrix, deterministic plans, lazy planning and meaningful composition/travel/cost measures. |
| G8-16 | Actual-handler journey and honestly scoped explored-checkpoint measurements. |
| G8-17 | Complete owner workflows and browser-produced input consumers execute successfully. |
| G8-18 | Wiki main chapters cover G7/G8 accurately; offline HTML and editable source are delivered and validated. |
| G8-19 | Frozen-input serial release gates, retained failures, verified archive inventories and remote publication readback. |

Deliver scoped commits and unique checkpoint tags; the owner report; machine-readable results; ordinary plans and representative views; the complete updated HTML; its maintenance source; and one portable review ZIP with a manifest. Keep personal campaigns, dependencies/browser profiles, disposable worker saves and a redundant full source checkout out of the ZIP. Preserve intentional historical compatibility fixtures. Inventory any omitted runtime payloads honestly and CRC/hash-check the retained archive.

The report must distinguish tests newly executed, verified historical records, controlled examples and ordinary generated worlds. Record actual delivered source/tag and remote readback outside self-referential commit content as necessary. Explain material limitations and any remaining blocked action with its precise reason. Completion means both implementation and usable owner documentation are available.

## 12. Stop boundary and design references

Stop when the opening corrections, bounded settlement composition, persistence proof, authoring workflows, updated wiki and verified delivery are complete. Do not start strategic country-road optimization, additional world density, larger settlements or continuous rendering in the same brief.

The next review should inspect the resulting towns and measured arrival/travel paths, then decide whether strategic network quality is the highest-value follow-up. It is not preauthorized as an automatic G9.

The following primary sources inform the separation of street geometry, buildable parcels, access and author control. They support design principles; this brief does not require importing their full algorithms:

- Chen et al., *Interactive Procedural Street Modeling* (SIGGRAPH 2008): a street graph is planned before downstream geometry, with explicit major/minor structure and author control. [Author paper](https://peterwonka.net/Publications/pdfs/2008.SG.Chen.InteractiveProceduralStreetModeling.pdf).
- Vanegas et al., *Procedural Generation of Parcels in Urban Modeling* (2012): block subdivision should respect parcel dimensions, alignment and street access, with stable customization relationships. [Author overview](https://twak.org/project/parcels/) and [primary paper](https://www.cs.purdue.edu/cgvlab/www/resources/papers/Vanegas-Eurographics-2012-Procedural_Generation_of_Parcels_in_Urban_Modeling.pdf).
- Cataclysm: DDA, *Overmap* documentation: placement definitions and connection rules are distinct authorities; valid terrain, rotation, occurrence and access constraints are explicit. [Official documentation](https://docs.cataclysmdda.org/JSON/OVERMAP.html).

Use the current Resonance source and tested contracts as implementation authority. Research examples do not authorize a new dependency, a wholesale engine rewrite or undocumented changes to saved campaigns.
