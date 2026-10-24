# Resonance G7 review and the G8 handoff

**Reviewed:** 24 October 2026, America/Edmonton.  
**Repository:** https://github.com/dgobi/ResonanceRoguelike  
**Reviewed main:** `8e56d36d72537e8b32c3666dd5d19723d1afdf3a`.  
**G7 frozen test input:** `31afa301418d075d7a79252c19d04dfb13c4a174`.  
**Next brief:** [CODEX_G8_SETTLEMENT_COMPOSITION.md](CODEX_G8_SETTLEMENT_COMPOSITION.md).

## 1. Decision

**Proceed to a bounded settlement-composition arc, opening with the demonstrated authoring, test-runner and wiki corrections.** G7 supplies a sound runtime foundation for that work. I found no critical default-content generation or save failure in the source audit and executed checks. The authoring CLI can overwrite its own input drafts, the direct focused-test command relies on an import path supplied only by the release wrapper, and the now-tracked wiki needs a coherent revision/build workflow. Those are concrete corrections to make before expanding the owner-facing interface.

The new outcome is **G8: settlement streets, blocks, frontage and maintained owner documentation**. Keep the existing town sizes and country backbone. Give grid towns two distinct compositions, real civic public space and occupied frontage on both street axes; derive roadside lots from the actual road. Continue using the proven fitter, role selector, reservations, complete-scene lifecycle and compatibility machinery.

This review produced a brief and evidence. It did not apply the fixes, change the game, update the current wiki edition or publish repository commits. The next brief explicitly requires those implementation and documentation results.

## 2. What the preceding review actually proposed

The prior G6 review called for compounds, followed by a composition review to choose settlement/block/street and network-quality work from observed gaps. The supplied G7 brief ended by requiring assessment of compound coherence and ease of authoring before selecting richer settlement/street composition. Neither specified an already approved exact G8 implementation. [Prior review §9][prior-review], [G7 brief §12][prior-brief].

That sequence remains appropriate. The compound stage is present, its ordinary and controlled examples are functional, and the newly measured gap is in the town planner: fixed street patterns and plots limited to horizontal frontage. A combined strategic road optimizer, organic city generator and streaming system would exceed what this review justifies.

The G7 prohibitions on new streets and loops were that brief's scope limits. They do not prohibit choosing local street composition as the next reviewed arc. The next brief nevertheless keeps country-network optimization separate and stops before a speculative G9.

## 3. Source and evidence identity

The attached `Pasted text(5).txt` is **byte-for-byte identical** to committed `docs/owner/WORLDGEN_G7.md`. Its SHA-256 is `20bc04cafd9a026cd4a5ea64cb392b0295f11d5f9f80d00f431cfd011debc8f9`. The delivered HEAD includes the separately committed wiki package; that package is outside the frozen G7 runtime/test input set. [G7 owner report][g7-report], [wiki introduction commit][wiki-commit].

All **680 tested-source files at delivered HEAD** are byte-identical to their Git blobs at the frozen G7 input commit. The original Windows test representations reconcile as reported: **437 exact raw matches and 243 line-ending-only matches**, with no other difference. The mixed-line-ending authoring guide's exact tested bytes are retained and verify to the reported raw hash. This closes G7's own documentation-byte identity claim; it does not retroactively recover the unavailable historical G6 representation.

All three retained archives passed independent archive hash/size checks, CRC validation, exact membership comparison and per-member hash/size verification:

| Archive | Retained members verified | Disclosed disposable-file exclusions |
|---|---:|---:|
| Development evidence | 523 | 67 |
| First complete freeze | 735 | 2,163 |
| Final freeze | 735 | 2,163 |

The **1,993 retained members** are verified. Exclusion inventories describe omitted worker payloads; they do not recover those bytes. All nine final receipts bind the same tested input and report stable source, successful committed-input reconciliation, exit zero and no timeout. The first complete passing freeze and subsequent guide correction are retained separately; the final totals are not combined across runs. See `evidence/retained-evidence-audit.json` and the repository's [G7 evidence index][g7-index].

### Executed checks versus historical records

| Evidence | Result | Scope |
|---|---|---|
| Fresh unmodified focused suite | 202 discovered: **200 passed, 1 error, 1 skip** | Executed on Linux; the error is the missing `tools/` import path described below. The skip is the documented Windows-only PowerShell case. |
| Fresh isolated native/renderer case | **1 passed**, with explicit tools import path | The exact previously errored case; both compounds, native turns and real production renderer. Source unchanged. |
| Fresh ordinary diagnostics and journey | **All three seeds and the real-handler journey passed** | All three fresh plans equal the retained final G7 plans exactly as JSON; full sampled scenes materialized successfully. |
| Retained Windows focused suite | 202 passed, no failures/errors/skips | Raw log and source-bound receipt audited; not presented as a new Windows execution. |
| Retained production gate | 3,675 checks / 159 workers / 74 coverage groups | Retained result and bindings audited; not rerun in this review. |
| Retained browser checks | 41 in Chromium and 41 in Firefox | Existing records audited; browser suites not rerun here. |
| Draft-preservation probes | Four successful commands overwrite a disposable input | Newly executed actual CLI behavior; source/drafts and receipts retained. |
| Wiki drift/build checks | Drift detected; current revision rejected by normal build | Read-only checks plus builder/validator source audit. |

The independent runtime uses Python 3.12.14, pygame 2.6.1, tcod 19.3.0 and NumPy 2.3.5. The focused suite took 449.413 seconds; the isolated case took 6.536 seconds, 7.288 seconds including its review wrapper. These are observations, not cross-platform performance comparisons. The broad failed run is retained unchanged. The isolated positive does not turn it into a passing 202-test run.

All **1,216 tracked files remained byte-identical** to the opening snapshot after the independent work, and Git status remained clean. Remote `main` and the peeled verified G7 tag both still resolve to `8e56d36…`. See `evidence/source-preservation.json` and `evidence/remote-recheck.json`.

### Ordinary worlds and travel reproduced

| Seed | Additional parents | Compounds / children | Sampled complete scenes | Compact plan bytes | Fresh planning seconds |
|---|---:|---:|---:|---:|---:|
| 0 | 2 | 1 / 3 | 15 | 600,599 | 0.977 |
| 20261023 | 3 | 1 / 2 | 18 | 738,766 | 1.484 |
| 29417 | 3 | 2 / 4 | 18 | 679,457 | 1.190 |

Each fresh plan exactly equals the corresponding retained final-b plan, has one physical road/access component, and created zero local scenes during planning. The sample contains four compound parents and nine compound children. The slowest sampled scene was 0.222 seconds. The full diagnostic/journey wrapper took 155.347 seconds. See `evidence/review-summary.json` and `evidence/diagnostic/`.

The journey reproduced **38,415 movement inputs and 593 boundary transitions**, visited both settlement forms and the landmark, and reached both shrine-court children plus a single site through their saved road access. Each of those three rural containers lost one item through the actual interaction handler, with the matching inventory increases. The route retained stationary native actors as obstacles while pausing AI/survival turn updates; the separate native-view case runs ordinary updates. The worst observed transition was 0.222 seconds.

F9 restored the coherent starting checkpoint after 352 scenes had been materialized. The saved checkpoint was **18,978,106 bytes and contained two starting scenes**, created before the journey. It is not a 352-scene save benchmark. Save/F9 measured 0.813/0.722 seconds. The separately executed focused compound-ownership test covers a checkpoint containing explored compound state. These measurements retain their own scope and do not establish a cross-platform performance regression.

## 4. G7 delivers the required architectural advance

### Small destinations now have one parent and independent children

The parent selector treats a compound as one of the existing two-to-four rural destinations. The featured landmark stays separate. The default policy requires both a compound and a single site; child counts do not consume single-parent caps. Selection uses canonical kind/identity keys and asset-first weighting, so extra permitted transforms do not automatically increase selection weight. [Parent selection][parent-selection].

The two recipes use shared circulation and explicit child slots. The homestead/workyard has two required buildings and an optional storehouse; the shrine court has two required buildings. The shared fitter enforces effective transform permissions, explicit private bounds and bounded backtracking. Optional omission removes its accepted ownership/reservation residue. [Compound fitting][compounds].

The production views show coherent small groups with an identifiable shared approach and separate usable buildings. They satisfy the intended composition proof. Their simplicity is appropriate to this arc; they are not evidence of sophisticated town districts or a finished landscape aesthetic. The images disclose full-scene visibility and controlled placement. The isolated fresh native-view check confirms the production renderer and eight ordinary updates for each recipe under the documented controls.

### Shared public access does not erase private ownership

Envelope membership is explicit. A child does not receive permission to intersect a sibling's private buffer because their IDs share a prefix. Named shared-path overlap is constrained by actual public geometry. The saved-plan reservation replay checks those relationships independently from current recipes. [Reservations and fitter][world-plan], [compound integrity][compound-integrity].

Child content record IDs include the full placement identity. Two instances of the same building remain separate owners inside a single complete chunk scene. The lifecycle tests exercise real item transfers, reverse visits, cold load and F9. The final scene validator checks common paths, complete required doorway spans and interaction access after all building contents, dressing and native population. [Scene materialization and access][planned-scene], [G7 lifecycle tests][g7-tests].

### Saved composition is durable

Format-5 worlds retain resolved parent/child/path choices. Removing current recipe and selection files does not recompose a pending scene. Changed consumed child definitions reject affected unseen scenes while visited state remains authoritative. The genuine G6 fixture and explicit adapters preserve older plan intent and actual visited creator revisions. Late-failure and checksum-consistent save corruption tests cover the publication boundary. These are substantive safeguards that G8 must reuse.

The previous all-optional-goal failure is also corrected at the appropriate site/compound admission boundary. The new error names the asset/context and required usable-goal condition, while generic direct preview retains its more permissive contract. The independent focused run passed those admission tests.

## 5. Corrections required at the start of G8

### 5.1 Preview output can overwrite an authoring input

**Priority: correct before extending owner authoring.** `tools/structure_authoring.py` protects only the positional candidate from the JSON output. Named recipe/child/configuration inputs and automatic SVG destinations are not covered. Some earlier mutations occur before the final report-path check. [Reviewed CLI][authoring-cli].

The actual current CLI produced these outcomes in disposable directories:

| Input/output collision | Before | After | Command result |
|---|---:|---:|---|
| Report path is the compound recipe | 1,248 bytes | 1,795,751 bytes | Exit 0; reports success; recipe replaced by preview JSON. |
| Report path is the child draft | 1,951 bytes | 1,795,750 bytes | Exit 0; child replaced by preview JSON. |
| Initialization report path is an existing child | 1,951 bytes | 213 bytes | Reports child preserved, then replaces it with the initialization report. |
| Automatic SVG path is a symlink to the recipe | 1,248 bytes | 225,234 bytes | Exit 0; recipe replaced by plan SVG. |

These results concern owner drafts, not saved campaigns. Distinct output paths work. The right repair is to guard all explicit inputs and all generated destinations, resolve aliases/same-file identities, validate before mutations, and retain intended report replacement/catalog refresh behavior. The package contains the portable reproducer, exact before-inputs, reviewed CLI and receipts in `evidence/wiki-authoring/`.

### 5.2 The documented focused command is not self-contained

The independent full run errored only when the G7 native-view test imported `g7_visuals`. That module is in `tools/`. The direct runner sets its child `PYTHONPATH` to the game and test directories, while the release wrapper adds the tools directory explicitly. The retained release receipt contains that extra path. [Focused runner][focused-runner], [G7 evidence wrapper][g7-wrapper].

Supplying the missing absolute tools path makes the exact test pass, producing both populated compound views. This establishes a runner-entry-point defect and explains the difference from the recorded Windows gate. It does not establish a Windows-versus-Linux gameplay failure or invalidate the historical passing receipt.

G8 must make the documented direct command supply its own required import paths. Verify it from a parent process without `PYTHONPATH`; retain the renderer test and its normal discovery. Do not fix this by suppressing or skipping the case. See `evidence/focused/`, `evidence/native-views-explicit-path/` and `evidence/focused-runner-analysis.json`.

### 5.3 The wiki is stale and its in-repository build workflow cannot sustain updates

The committed maintenance package remains **edition 1.0 / G6**, pinned to `4d7a789…`. Its world-generation chapter explicitly says compounds are unavailable. Rural-site guidance describes the old single-only policy; structure context, save adapters and authoring workflows are also behind current G7. The current standalone structure guide is much more up to date. [Wiki configuration][wiki-config], [world-generation chapter][wiki-world], [current structure guide][structure-guide].

Tracking the originally external package introduced a second problem. The builder requires exact current-HEAD equality with a tracked configuration and a wholly clean tracked tree. Editing the configuration makes it dirty; committing that edit changes HEAD. It then fingerprints all tracked files, including its own manifest/report, and rewrites those files. Its source-document collection would also duplicate the 31 authored wiki chapters as historical source articles. The validator shares the HEAD/inventory assumptions. [Builder][wiki-builder], [validator][wiki-validator].

The read-only check found **37 changed, zero missing and 132 added paths** relative to the G6 manifest. Those counts are drift observations, not 169 game bugs. A normal current build rejects the revision mismatch before output. No compiled wiki HTML is tracked at the reviewed HEAD.

The repair separates the reviewed game/document source snapshot, wiki authoring inputs, and generated products. Preserve precise drift checks; exclude products from their own input manifests; permit a later documentation delivery commit when the reviewed source projection is unchanged. Use the same revision/input policy in builder and validator, and remove hardcoded G6/current-audit text. Two repeated builds, a documentation-only commit and changed/missing/stale negatives must prove the workflow.

The next edition must update the main chapters, not merely append the G7 report to an archive. The brief makes the offline HTML, editable source, executed examples and ongoing feature-update rule explicit deliverables. The current wiki has not been silently relabeled as reviewed for G7.

## 6. The measured gap that selects G8

The retained ordinary G7 plans contain 11 towns: six grid and five roadside. Their counts reconcile exactly with the reported 15/18/18 sampled complete scenes once town members, rural parents, start, landmark and capital gateway are counted. The crossing is separate.

| Measure | Three-world result |
|---|---:|
| Proposed town plots | 272 |
| Occupied / vacant | 233 / 39 |
| Occupied grid plots | 177 / 192 |
| Occupied roadside plots | 56 / 80 |
| North / south candidate frontage | 136 / 136 |
| East / west candidate frontage | **0 / 0** |
| Occupants addressing vertical grid streets | **0** |
| Distinct relative grid street arrangements | **1** |

The measurement script and exact plan/archive bindings are in `evidence/settlement-baseline/`. It reads retained plans without importing the production generator.

The code explains the result. Grid streets are four hardcoded lines. Plot generation samples x positions along each chunk's horizontal center street and tries only `S` and `N`. Vertical streets therefore consume and connect space without receiving building frontage. All six sampled civic buildings also land near the northwest corner, without a separately planned civic square. Some roadside candidates are safely rejected because no actual assigned-road frontage exists at their sampled join. [Town construction and slots][world-plan].

These are composition limitations rather than invalid accepted buildings. G8 should address them through street-derived lots, purposeful common space and two bounded layouts. It should not chase a higher occupancy percentage: a useful square or yard may reduce building count while improving the town.

Several existing assets already permit quarter turns, including selected residential/commercial buildings and the bell tower. A substantial new art library is unnecessary. Assets restricted to 0°/180° should remain on compatible frontage. Expanding their consumed permissions just to make a test pass would weaken compatibility.

### Why country-network optimization remains separate

The current world planner constructs a connected ordered backbone, and G7 adds durable rural attachments. It does not claim to optimize all travel. Local towns already possess a rectangular cycle, so “add loops” alone would be an imprecise diagnosis.

Any future loop measure must distinguish a real alternate route from route ownership self-references and cycles between adjacent tiles inside a wide road. G8 requests a derived centerline junction analysis and actual local travel measures. It retains the existing country routes and lets the next review decide whether strategic detours deserve their own arc.

## 7. What the next implementation must prove

The brief defines 19 acceptance items and these main outcomes:

1. **Safe authoring and dependable verification.** No report/diagram can destroy its inputs; the direct test command works without shell preparation.
2. **Purposeful local town composition.** Exactly two current grid profiles within the existing bounds, actual civic common, occupied frontages on both street axes, and better real-segment roadside lots.
3. **Shared existing mechanisms.** Explicit plot bounds and stable identities; original role/cap/weight guarantees; staged bounded failure; narrow private/public permissions; complete populated access.
4. **Correct version and policy combinations.** Format 6 / `wg8` for the new settlement contract, independent of whether rural policy is mixed v2, single-only v1 or explicitly zero. Current format selection is coupled to the POI switch, so this combination requires explicit handling.
5. **Authentic compatibility.** A pre-edit G7 witness with mutated visited town/compound scenes and pending counterparts, preserved older fixtures, unchanged visited provenance, explicit pending adapters, cold-load/F9 and late-failure rollback.
6. **A maintained owner resource.** G7 catch-up plus G8 main chapters, complete executed examples, a sustainable source/edition model and rebuilt offline HTML delivered alongside the implementation.

Two geometry details deserve particular care. The existing materializer expects connected road slices within each chunk, so the new profiles must respect that contract. Native civic furnishing currently avoids protected cells; protecting the common must leave explicitly legal waystone/prayer positions without letting furnishing block essential circulation. Neither requires a new scene lifecycle.

The final release remains autonomous and source-bound, with headless focused checks, actual browser-export consumers, authoring workflows, ordinary complete scenes, real-handler travel, wiki checks and the unfiltered production gate. Saved-size measurements must identify the number of explored scenes actually in the checkpoint. The previous journey's startup checkpoint must not be described as a save of hundreds of later visits.

## 8. Research informing the chosen scope

The relevant primary sources support a restrained architecture. Chen et al. separate street-network design from downstream geometry and emphasize author control. Vanegas et al. treat block subdivision and persistent parcel customization as their own step; their parcel work also addresses dimensions, alignment and access. Cataclysm: DDA distinguishes abstract world placement from detailed local map content, and gives locations/connections explicit rules. [R1–R3 below].

The application to Resonance is an engineering inference: plan streets/public space, derive feasible lots, then use the existing authored-building fitter. These sources do not require a tensor-field system, a general polygon subdivision library or a new engine. A small orthogonal profile system is enough to test the next useful contract within the present 160 × 86 towns.

### Primary references

- **R1:** Chen, Esch, Wonka, Müller and Zhang, *Interactive Procedural Street Modeling*, SIGGRAPH 2008. [Author paper](https://peterwonka.net/Publications/pdfs/2008.SG.Chen.InteractiveProceduralStreetModeling.pdf) and [author project page](https://www2.cs.uh.edu/~chengu/Publications/streetModeling/street_modeling.html).
- **R2:** Vanegas, Kelly, Weber, Halatsch, Aliaga and Müller, *Procedural Generation of Parcels in Urban Modeling*, Computer Graphics Forum 2012. [Author overview](https://twak.org/project/parcels/), [primary paper](https://www.cs.purdue.edu/cgvlab/www/resources/papers/Vanegas-Eurographics-2012-Procedural_Generation_of_Parcels_in_Urban_Modeling.pdf), DOI `10.1111/j.1467-8659.2012.03047.x`.
- **R3:** Cataclysm: DDA, [official Overmap documentation](https://docs.cataclysmdda.org/JSON/OVERMAP.html).

## 9. Package contents and limits

Read the Codex brief for the execution contract and this review for the reasons behind it. `evidence/` retains the fresh focused failure, isolated positive, ordinary diagnostics/journey, source preservation, archive audit, settlement metrics and draft/wiki probes. `MANIFEST.json` records the included files and hashes. Original G7 source and release archives remain in Git; this package does not duplicate the full repository or personal campaigns.

The review establishes the inspected default/controlled paths and stated source relationships. It does not certify every seed, arbitrary future author content, unrestricted survival travel or long-campaign streaming. `UI-TEXT-HEIGHT`, larger-world retention and continuous viewport remain deferred. The next brief is complete at the bounded settlement/wiki milestone.

[prior-review]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/evidence/worldgen-g7/before/G6_REVIEW.md
[prior-brief]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/evidence/worldgen-g7/before/CODEX_G7_MULTI_BUILDING_COMPOUNDS.md
[g7-report]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/docs/owner/WORLDGEN_G7.md
[g7-index]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/evidence/worldgen-g7/INDEX.md
[wiki-commit]: https://github.com/dgobi/ResonanceRoguelike/commit/4c9d46b
[parent-selection]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/roguelike/generation/parent_selection.py
[compounds]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/roguelike/generation/compounds.py
[world-plan]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/roguelike/generation/world_plan.py
[compound-integrity]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/roguelike/generation/compound_integrity.py
[planned-scene]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/roguelike/generation/planned_scene.py
[g7-tests]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/tools/critical_fix_regressions/tests/test_generation_g7_compounds.py
[authoring-cli]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/tools/structure_authoring.py
[focused-runner]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/tools/critical_fix_regressions/verify_fixes.py
[g7-wrapper]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/tools/g7_evidence.py
[wiki-config]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/Resonance_Wiki_Maintenance/wiki-config.json
[wiki-world]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/Resonance_Wiki_Maintenance/chapters/world-generation.md
[wiki-builder]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/Resonance_Wiki_Maintenance/build_wiki.py
[wiki-validator]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/Resonance_Wiki_Maintenance/validate_wiki.py
[structure-guide]: https://github.com/dgobi/ResonanceRoguelike/blob/8e56d36d72537e8b32c3666dd5d19723d1afdf3a/roguelike/docs/STRUCTURE_AUTHORING.md
