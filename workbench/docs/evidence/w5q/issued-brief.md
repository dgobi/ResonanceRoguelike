# Codex — W5Q: saved settlement membership and ordinary-world previews

**Status:** Issued implementation brief.  
**Prepared:** 29 October 2026.  
**Repository:** `dgobi/ResonanceRoguelike`, existing production `main`.  
**Reviewed W5P / remote main:** `f34ab95d7ee82735afb61fac41ddb873bab149a3`.  
**Outcome:** The owner can enroll a saved surface-building variant in the game's existing settlement-selection policy, save and reopen that policy, and inspect a real placement and its constructed contents in an ordinary new world generated from those saved inputs.

Complete this bounded integration using the native selector and shared document service. First repair the specific W5P diagnostic-location defect below. This brief commissions implementation, autonomous verification, **commits, push and exact remote-`main` SHA readback**.

## 1. Reviewed basis and reason

W5P's core shared building-authoring and production-construction outcome is supported. Its issued brief, implementation, delivery report, receipt, accepted fixtures, native observations and planned-placement evidence were reviewed. Independent checks passed **85 frontend tests, TypeScript checking and 14 worker tests**: 99 tests plus typechecking. The worker modules were `test_buildings_w5p` (six), `test_authoring` (three) and `test_visual` (five). Worker checks used Linux CPython 3.11.17 with the pinned dependencies; frontend checks used Node 24.22.1. These are focused checks, not a repeat of the reported Windows release gates. [S1–S3]

The evidence audit matched 35 committed source entries, 80 package inputs, two verification scripts, 12 captured game-source entries, both exact accepted fixtures and all 16 orientation bindings. Application/package inputs are from `750c4db2f7ac3a8d0355026a7dbdb3160c1bc699`; the reviewed final commit adds retained evidence and harness work. Documented Windows working-byte versus Git newline differences reconcile. An independent production replay of both exact fixtures passed all eight orientations per fixture, reproducing the geometry, access and direct readable/container construction observations. Catalogue byte identities differ between environments, so this does not claim identical Windows scene seeds or every random-loot result. [S1–S3]

One concrete defect remains: a transformed multi-cell entrance failure can identify the wrong native source cell. Validation still rejects the blocked building in all eight orientations. Section 3 commissions the bounded correction; do not describe the reviewed implementation as having completely correct diagnostic localization. [S4]

W5P's planned fixture successfully selected and constructed the revised building three times at seed 20261029, but the helper temporarily injected its membership into an in-memory policy. The owner still cannot make that connection through Workbench's saved native selection file. W5Q completes **saved building → saved membership → ordinary new-world selection → production construction**. A new surface play launcher would be useful later, but it would not remove this remaining manual registration step. [S1, S5]

This serves the compass's particular, readable and connected places and the approved implementation path's sustainable content production. Consult the compass, decisions/state, workflow, implementation proposal and approved original Workbench plan. The adjusted 27 October plan remains proposal context, not blanket approval. Historical G14 implementation observations in supplied project documents yield to current repository evidence; enduring decisions remain applicable. [P1–P6]

## 2. Execution and preservation

Work in `G:\GameDev\RoguelikeProject` on the existing production `main`. Read current `AGENTS.md`, this brief, W5P delivery and the affected authoring, selection and save contracts. Reconcile intervening owner changes and actual local/remote revisions; do not reset an advanced checkout to this baseline.

Create named checkpoints before substantial changes. Preserve unrelated owner work, the untracked owner plan, live content, campaigns, settings, fonts, launcher and historical evidence. Use no task branch, worktree or additional development checkout. Disposable data/save fixtures and autonomous headless or app-local verification remain authorized. Bind disposable save roots **before constructing any Engine or SaveManager**; do not inspect personal campaigns for fixtures or transfer routine tests to the owner.

Keep demonstration buildings and policy edits in disposable fixtures. Do not install a canonical content pack or change shipped memberships as part of the demonstration. Update the directly affected owner guide and completion evidence; no routine wiki or reference-pack rebuild.

## 3. Correct W5P's transformed entrance diagnostic

In `generation/building_preview.py::orientations`, the failing transformed `span[n]` index is reused against `entrance_cells(native)`. Rotation or mirroring can reverse span order. Source cell **(5,10)** in the accepted `building_v1.json`, blocked with `campfire_unlit`, is incorrectly reported as **(4,10)** for 0° mirrored, 90° mirrored, 180° unmirrored and 270° unmirrored. All eight combinations correctly fail access/publication. [S4]

Retain per-cell source provenance or invert the actual failed transformed coordinate to obtain the correct native cell. Keep the diagnostic's source field/span identity, transformed cell and scene cell mutually consistent, and make Locate select the actual blocked source cell. Do not change placement transforms or weaken full-span checking to fix the display.

Add one asymmetric two-cell entrance regression covering all eight combinations, asserting rejection **and correct source localization**. Preserve a positive pass and optional-entrance semantics through existing coverage. This is a diagnostic repair, not a transform-system rewrite.

## 4. Register the existing selection document

### Exact native scope

Register one edit-only fixed source:

`roguelike/data/generation/settlement_profiles.json`

Its native root is exactly `{version, profiles}`; it has **no root `id`**. Preserve that shape. A logical document identity can live in adapter/host metadata. Do not insert an ID, a derived `base_weight`, a new policy version or an editor-only field into the source. The current file contains 27 membership rows, including its protected civic anchor; this is a coverage observation, not a row limit or asset whitelist. [S6]

Provide ordinary controls for the seven non-civic role tables:

| Profile | Editable membership tables | Protected policy |
|---|---|---|
| `grid` | `residential`, `commercial`, `support` | Entire `civic` table and all other profile fields |
| `roadside` | `residential`, `commercial`, `support` | All other profile fields |
| `landmark` | `landmark` | All other profile fields |

Within those tables, add/remove a row and edit **`asset`, `weight`, `max_per_settlement`**. Keep root version, profile keys/IDs, role names, minima, schedules, repeat multipliers and required-fit budgets unchanged. Show relevant protected values as context. The landmark table governs the existing featured landmark; it does not authorize additional rural-POI or compound-policy editing.

A small specialized view for these nested native tables is appropriate. Reuse source commands, reference controls, validation and lifecycle infrastructure. Do not flatten the source schema or build a general generation-configuration framework.

### Original-source authority and repair

Authorize from the exact original path, native family/format and registered edit operation before staging candidate bytes. No variant operation, new target, profile duplication, rename, arbitrary generation-root write grant or alternate writer. A candidate cannot upgrade an unsupported original. Enforce the native root shape and protected-policy boundary in backend publication as well as controls; Source and recovered text receive the same authority checks.

Resolve this fixed file explicitly rather than relying on generic root-ID discovery. Any fixed-file identity policy must agree across the registry, renderer and trusted host; do not pretend the existing root-ID policy describes this source. Recovery and publication must reject variant intent, including a nonempty variant ID when its variant flag is false. Reject case aliases, path escapes and source ambiguity.

Preserve the actual consumer's decoding rules. The selector's `DataLoader._load` uses UTF-8 and rejects a UTF-8 BOM; structure authoring's more permissive UTF-8-sig reader is not its authority. Reject such candidate bytes precisely instead of silently stripping them or changing the game loader.

Invalid editable membership values in an otherwise recognized original must be repairable. Opening Source must not require a successful world generation. Preserve exact malformed draft text through recovery. Unsupported original versions/shapes remain inspectable with a precise limitation; do not silently normalize them into an admitted format. Unrecognized data remains visible, and a strict consumer rejection remains a rejection.

Structured operations preserve untouched source spans, ordering, literal escaping and line endings. Deliberate Source edits may change permitted membership data, but cannot bypass protected policy. Do not serialize the whole file merely to adjust one weight. Keep production validation strict; source fidelity does not make an unsupported field valid.

### Shared document lifecycle

This is **one document for the file**, not one owner per profile or role. Explorer, building links and preview navigation focus the same existing owner. Reuse independent drafts, one Source/control undo history, exact recovery, review/apply, one-use authority, cancellation, request generations, source/dependency invalidation, last-moment freshness, conflict preservation, rollback and byte-checked reopen.

Recover the selection draft alongside a building and another family after host restart, without recovering stale validation/apply authority. No new document store, family-specific Rust slot, recovery mechanism or publication transaction. [S7]

## 5. Explain and enforce the actual selector

Use `settlement_selection.validate(candidate, data)` with saved game definitions as the authoritative contract. Passing no data selects the resolved-save schema, which requires derived `base_weight`; it is not validation of the editable source. Do not implement a more permissive parallel validator. Present actionable field/row diagnostics; preserve invalid draft values for correction. [S6]

| Rule | Required behavior |
|---|---|
| Membership identity | A saved building ID resolves uniquely to the actual ordinary-building source. Do not choose an incidental last-loaded duplicate or gate reference eligibility on definition editability. |
| Native context | Non-civic rows require the matching `grid`, `roadside` or `landmark` placement context; connected selection rejects `road_relation == "remote"`. |
| Role meaning | Folder/category does not determine role eligibility. A commercial role is a selection role, not a new NPC/shop mechanic. |
| Duplicates | Reject the same asset anywhere across roles **within one profile**. The same asset may appear in separate grid and roadside profiles. |
| Weight | Finite number strictly greater than zero and at most 1,000. Zero is invalid; remove membership to exclude an asset. |
| Cap | Integer 1–128; booleans are not integers here. It caps accepted instances across the whole settlement, not separately per chunk. The featured landmark has its existing one-site scope. |
| Minima | Keep every role pool nonempty, including roles whose minimum is zero. Total row caps must satisfy the protected role minimum. |
| Civic anchor | Preserve the exact existing grid civic row and minimum. Do not expose removal/replacement of the spent-bell anchor. |

Show the membership weight separately from the saved building's placement weight. The selector combines them with its existing repeat penalty where applicable. This is a relative choice weight, not a fixed percentage, frequency estimate or fit guarantee. Accepted placements consume caps; failed fits do not. Additional permitted orientations do not multiply the asset's selection weight.

The resolver sorts a copied membership list and captures `base_weight` inside the **resolved plan**. Do not write these derived changes back into authored policy. UI row ordering is not selection priority. Do not add a priority-drag interaction or a zero-weight “disabled” state with invented semantics.

### Connected authoring

From a saved building, provide navigation to its membership in the selection document, with profile/role context. Stage a new row only through an explicit owner action; saving a building does not auto-register it. Offer eligible saved sources from the real catalogue and explain a missing profile/context or remote relation. Let the owner navigate back to building controls for deliberate correction; do not silently change its contexts, geometry or weight.

Keep **draft membership**, **saved membership**, **saved-building eligibility** and **selection in the current sample** distinguishable. An unsaved building variant is not a saved reference. An existing saved building with a parked dirty draft may still be referenced using its saved definition, with that distinction visible. Never overlay parked drafts into the selector.

Rows link to the exact building source and return to the originating selection context. Reuse existing owners, preserve all independent drafts and detect stale origins after edits. A renamed/replaced row must not silently receive an old navigation or diagnostic location.

## 6. Preview an ordinary world from saved inputs

The owner must be able to answer: **“What did this seed select from the policy I saved, and what did that selected place actually construct?”** A profile form or candidate-injection preview alone does not complete W5Q.

### Input and generation boundary

Follow the existing assignment-family precedent: preview the explicitly saved/reopened policy and saved dependencies. Require saving relevant selection changes first. Validate and reload through the game-owned path, then generate an ordinary **128 × 128** world through `world_gen.generate_world`, using an explicit seed and the normal saved generation configuration. Preserve the current planner, dimensions, algorithms and budgets. [S8–S9]

Do not pass a raw candidate to `plan_preview.planned_preview`, inject membership into a copied policy, narrow candidate pools, choose a forced layout or modify default generation settings for the ordinary-preview claim. The existing W5P helper may remain for its disclosed controlled purpose, but it is not this preview's implementation or evidence.

Bind results to exact saved policy bytes, seed, relevant saved dependency/configuration identities and the resulting plan identity. Establish that the plan's captured selection equals `settlement_selection.resolve` of those freshly loaded saved inputs; retain that binding in the receipt. Materialization and displayed planning facts must use the same input snapshot/plan. Resolve the chosen placement identity inside that verified plan; an asset ID or a client-supplied placement ID alone is insufficient. Reusing a captured plan or deterministically replaying verified inputs are both acceptable; do not combine an old placement table with a newly loaded scene while presenting them as one result.

Source/dependency edits, saves, external changes and cancellation must not let obsolete output become current. Retain historical results if useful, with clear stale status and the input identity they actually describe. Fail cleanly on invalid saved inputs or generation/construction errors; do not substitute canonical defaults or partially present a failed generation as success.

### Useful bounded output

Provide a compact selection summary and placement table, covering the current grid, roadside and featured-landmark consumers. Include profile/role, asset, owner/settlement, placement identity, chunk/location, rotation/mirror and actual frontage/entrance information. Link a selected asset back to its source.

Distinguish **eligible**, **selected in this plan** and **materialized for inspection**. Show actual counts for the generated plan; bound displayed rows and state total/shown/truncated counts. Show fit/cap rejection details only where the planner actually recorded them. A candidate's absence does not establish a specific rejection cause, impossibility or lack of references elsewhere.

Allow inspection of at least one chosen actual selected placement through `create_surface`, with its real terrain, decor, direct contents and receipt-owned readable/container observations. Reuse the production snapshot/receipt path. Include landmark placements, not only settlement member chunks. Clearly associate the placement's records with its scene and transformation rather than attributing every object in a chunk to the chosen building. Preserve relocated-object and declared-versus-effective-readable distinctions.

A revealed diagnostic scene is sufficient. No player launcher, field-of-view simulation, item-use claim, survival trial or full-world dashboard is required. Reuse or narrowly extract the ordinary planning/materialization approach in `settlement_preview.py`; its current all-settlement-scenes return is not a requirement. Generate the full ordinary plan before filtering observations. Bound scene output and expensive work within the existing 16 MiB worker response and 90-second operation limits; preserve cancellation instead of raising limits to accommodate an oversized report. [S9]

A valid saved membership may have **zero selected instances** at a seed. Show that honestly and allow another explicit sample. Do not silently search seeds, raise weight, change membership or retry after failure. Distinguish invalid policy, recorded required-role infeasibility, exhausted bounded search with unresolved feasibility, ordinary nonselection and failed production construction. None authorizes automatic source edits.

## 7. Preserve activation and saved-world semantics

Explain activation beside publication/preview: selection edits affect **new world plans**. The current resolver captures a self-contained selection policy, including base weights, in the plan. Existing saved plans validate their captured policy without consulting today's editable selector. [S6, S10]

A membership/weight/cap edit must not reselect an old pending surface, modify its selected IDs/roles/transforms, change its plan identity, retrofit a newly enrolled variant or regenerate visited maps. Generated scene caches retain their physical state. Missing-cache refusal and historical/legacy selection consumers retain their existing contracts.

This differs from editing a consumed building, pool or item under the same ID: the separate pending-surface dependency gate still applies to those changes. Do not describe membership editing as bypassing that gate. W5O's pending authored-room behavior is also not the surface selector's activation contract.

Reuse `test_selection_only_edits_keep_pending`, which changes policy, restores a saved plan without replanning and verifies pending construction. Add a focused extension only where the new authoring/publication boundary is not established. No save-format change, plan migration, compatibility waiver or campaign rescan is commissioned. [S10]

## 8. One complete native acceptance journey

Use disposable saved data and explicit app-local automation. The primary acceptance must use the new controls and real shared publication; a worker-only JSON fixture is supporting evidence.

1. Open an eligible saved W5P-style building, the fixed selection document and an unrelated document. Stage edits in all three, restart the host and recover exact drafts. Demonstrate the fixed no-root-ID source and independent owner identities.
2. Save/reopen the authored building as needed. From it, navigate to selection and add its saved ID to an eligible non-civic role. Adjust weight and cap through controls, preserving existing candidates and protected policy. Demonstrate Source/control history and exact return navigation.
3. Show and repair a meaningful rejection, such as duplicate membership across two roles of one profile, wrong saved placement context, zero weight or an invalid cap. Cover the other native boundaries through focused tests. Demonstrate protected-policy edits cannot be published through Source/recovery.
4. Save/reopen the exact policy and run the ordinary preview. Retain the policy bytes, saved building bytes, dependency identities and seed. Establish that neither candidate injection nor parked dirty drafts influenced generation.
5. Observe the authored building actually selected and inspect its real constructed placement, full frontage and receipt-owned readable/container contents. Use a recorded seed. If initial samples do not select it, record those outcomes and any explicit bounded additional samples; disclose the stopping rule. Do not remove competing candidates or alter protected configuration to manufacture the result.
6. Remove the demonstrated membership deliberately, save/reopen and generate a fresh sample at the **same seed**, leaving the saved building present and unchanged. Establish absence from the affected saved table and its new-plan selection route. Retain both accepted policy versions and show the old result as historical/stale. Do not claim removal from other profiles or historical consumers. This removal control must not be replaced by a weight-only revision whose selected result happens to remain unchanged.
7. Verify the selection-only old-plan behavior in a disposable saved fixture, retaining existing cache and consumed-dependency coverage. Exercise final freshness/conflict/cancellation through the shared lifecycle tests rather than repeating every historical UI journey.

Retain only useful native observations/screenshots, exact accepted inputs and compact production receipts. If a failure reveals a repair or material limit, retain that evidence and explain it. Observation of constructed contents does not establish player interaction, balance, natural discovery frequency or fun.

## 9. Verification, delivery and stopping point

Add focused checks for the actual risks: all seven editable tables and protected civic policy; fixed-path/no-root-ID authority; invalid editable-value repair; exact source/history/recovery; saved reference/context resolution; duplicate scope, weights, caps and minima; saved-input preview freshness and nonselection; real selected-placement construction; and the W5P diagnostic correction. Preserve shared conflict/rollback/cancellation coverage and the applicable G3/G5 generation/save regressions.

Include a focused real featured-landmark selection-to-construction assertion: resolve its actual placement, materialize its chunk through `create_surface`, and attribute receipts to that placement. The existing settlement-member preview loop does not cover this separately owned site. This check need not repeat the full native authoring journey.

Run the repository's required frontend/TypeScript, Rust/clippy, worker/game and package/native gates with the required runtime. Preserve their established coverage without inventing a broad new seed matrix or repeating expensive gates solely for evidence formatting. Record commands, environment, failures and limits. Distinguish actual execution, retained existing coverage and source-based conclusions.

Deliver a concise W5Q report, source-bound verification receipt, exact accepted policy/building fixtures, ordinary-plan/construction evidence and the diagnostic regression. Identify the tested application/package inputs separately from later evidence-only commits; reconcile working-byte and committed-byte differences where necessary. Keep binaries/bulky logs under the established artifact policy and update the directly affected owner instructions.

Commit scoped changes on `main`, push and read back the **full remote `main` SHA**. Report named checkpoints, implementation/package revision, final delivery revision, test results and preserved owner state. Reconcile an advanced branch without force-resetting or force-pushing. Publication is already commissioned; do not turn it into a routine final permission request.

**Stop when the owner can save a building's native membership, recover/revise it, and inspect its real selection and construction from an ordinary saved-policy world, with the W5P location defect corrected and existing world/save guarantees preserved.**

Defer settlement layout/roads, minimum/schedule/repeat/budget editing, extra POI/compound policies, automatic registration, canonical content/rebalancing, surface play sessions, generalized world-generation laboratories, new gameplay, save migrations and wiki rebuilding. Review the delivered result before issuing the next brief.

## Source map

Project sources consulted:

- **P1:** `RESONANCE_PROJECT_COMPASS.md` — useful, readable places; sustainable authoring; scope filter.
- **P2:** `RESONANCE_DECISIONS_AND_STATE.md` — retained decisions and source precedence; historical implementation baseline.
- **P3:** `RESONANCE_WORKFLOW.md` — bounded briefs, evidence limits, autonomous verification and existing production checkout.
- **P4:** `RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md` — approved original Workbench direction.
- **P5:** `RESONANCE_WORKBENCH_ADJUSTED_PLAN_PROPOSED_2026-10-27.md` — supporting proposal context, not wholesale authorization.
- **P6:** `RESONANCE_IMPLEMENTATION_PROPOSAL.md` — approved implementation path and connected-expedition purpose.

The issued predecessor is `CODEX_WORKBENCH_W5P_SURFACE_BUILDING_AUTHORING.md`, SHA-256 `81edb8e5c7efd4d7cf0d46d20d708515240db586cb022c9953ca114a4ba77031`. Repository links are pinned to the reviewed W5P revision.

- **S1:** [W5P delivery](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/docs/W5P_DELIVERY.md) and [verification receipt](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/docs/w5p-verification.json).
- **S2:** [W5P evidence and exact fixtures](https://github.com/dgobi/ResonanceRoguelike/tree/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/docs/evidence/w5p) and [native journey](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/scripts/run-buildings.mjs).
- **S3:** [W5P worker checks](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/worker/test_buildings_w5p.py), [authoring worker checks](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/worker/test_authoring.py), [visual worker checks](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/worker/test_visual.py) and [building adapter](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/engine/building_authoring.py).
- **S4:** [Orientation and diagnostic orchestration](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/generation/building_preview.py) and [placement transforms/dependencies](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/generation/placement.py).
- **S5:** [W5P planned fixture runner](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/scripts/building-planned.py) and [controlled candidate-injection helper](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/generation/plan_preview.py).
- **S6:** [Native selection policy](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/data/generation/settlement_profiles.json) and [validation/resolution/selection](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/generation/settlement_selection.py).
- **S7:** [Content registry](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/engine/content_authoring.py), [shared host](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/src-tauri/src/authoring.rs), [shared recovery](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/src-tauri/src/recovery.rs) and [native data loader](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/engine/data_loader.py).
- **S8:** [Fixed assignment-family precedent](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/engine/assignment_authoring.py) and [assignment editor](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/src/AssignmentEditor.tsx).
- **S9:** [Ordinary world generation](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/generation/world_gen.py), [planner](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/generation/world_plan.py), [settlement production preview](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/roguelike/generation/settlement_preview.py) and [worker bounds](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/workbench/src-tauri/src/main.rs).
- **S10:** [Selection and pending-world regressions](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/tools/critical_fix_regressions/tests/test_generation_g5_selection.py) and [generated-scene lifecycle coverage](https://github.com/dgobi/ResonanceRoguelike/blob/f34ab95d7ee82735afb61fac41ddb873bab149a3/tools/critical_fix_regressions/tests/test_generation_g3_lifecycle.py).

