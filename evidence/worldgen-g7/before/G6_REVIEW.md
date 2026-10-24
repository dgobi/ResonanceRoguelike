# Resonance G6 review and the next implementation arc

**Review date:** 24 October 2026, America/Edmonton.  
**Reviewed main:** `4d7a7892e1afffb8d872ed4a8fd442984d14e7d5`.  
**Frozen G6 test input:** `991eb9f4e18f53efc3f0c9fc02648fbd70183068`.  
**Verified checkpoint:** `checkpoint/worldgen-g6-verified-20261024-a`.  
**Next handoff:** [Codex G7 — Multi-building compounds with shared road access](CODEX_G7_MULTI_BUILDING_COMPOUNDS.md).

## 1. Decision

**G6 is a sound base for the next feature arc. Proceed to bounded multi-building compounds, opening with one small authoring correction.** The independent tests and travel run passed, the ordinary plans reproduced exactly, and the source/evidence audit supports the central ownership, attachment and compatibility claims. I found no critical failure in the reviewed default-content paths. That is a bounded review conclusion, not a claim about every seed or arbitrary authored content.

Two items carry forward: a reproduced all-optional-goal authoring error, and one documentation-only source-normalization claim that cannot be independently completed from the retained bytes. Neither warrants another broad repair-only arc. The G7 brief handles the first as a focused opening correction and the second through clearer final evidence capture. The rest of G7 produces usable shared-access compounds and the documentation needed to author them.

This review did not modify game source, Git history or personal campaigns. All 1,084 files in the reviewed source snapshot remained byte-identical after the independent runs. A private review interpreter supplied pygame/tcod; production dependencies were unchanged. [Source preservation](evidence/independent/source_preservation.json), [review environment](evidence/independent/environment.json).

## 2. What was actually reviewed

I compared the exact supplied G6 brief against seven commits and 59 net changed paths since G5. The local attached report is byte-identical to committed `docs/owner/WORLDGEN_G6.md`. The final delivery commit is a child of the frozen test input; its documentation/evidence changes do not overlap the frozen input path set. A final GitHub read confirmed main and the resolved annotated checkpoint tag both still identify the reviewed commit. [Commit](https://github.com/dgobi/ResonanceRoguelike/commit/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5), [owner report](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/docs/owner/WORLDGEN_G6.md), [remote reconciliation](evidence/provenance/remote_recheck.json).

Three specialist audits covered composition/authoring, ownership/persistence, and retained evidence. I separately ran the unmodified focused suite and G6 diagnostic/journey against the pinned delivered source. The distinction matters: checking stored worker receipts is different from rerunning those workers, and static inspection is different from executing an authoring workflow.

| Evidence category | Result | What this review did |
|---|---|---|
| Independent focused suite | 189 discovered: **188 passed, one Windows-only skip**, zero failures/errors | Executed unmodified on Linux; source stable |
| Independent G6 diagnostic | All three ordinary seeds passed; no failures | Executed unmodified, including complete destination scenes and journey |
| Independent required-goal probe | Compiler/direct preview pass; assigned/fresh generation raise empty `StopIteration` | Executed with an in-memory draft; verified unchanged world on failure |
| Retained Windows focused suite | **189 passed**, no skips | Matched AST identities, log results, receipts and source bindings |
| Retained unfiltered production gate | **3,675 passed checks / 159 workers** | Audited jobs/results, 12,749 imported-source bindings and harness controls |
| Retained browser checks | Chromium/Firefox: **36 each**, 129 codec documents each | Reconstructed actual downloaded JSON changes and checked downstream receipts |
| Retained authoring workflow | **19 outer commands + two actions**, five expected negatives | Audited outputs and nested workflow accounting |

The independent suite used Python 3.12.14, pygame 2.6.1, tcod 19.3.0 and NumPy 2.3.5; its wrapper took 382.456 seconds. The skipped case executes a documented PowerShell initialization workflow and requires Windows. The retained Windows run used a different Python/NumPy environment and passed that case. I did not rerun the Windows authoring/browser suites or the entire production gate here. [Independent summary](evidence/independent/review_summary.json), [focused log](evidence/independent/focused/focused-tests.txt), [retained evidence audit](specialist_reviews/evidence/G6_EVIDENCE_REVIEW.md).

## 3. G6 delivers the important architectural changes

### The two G5 selection corrections are real

The required-role search now reaches alternative transforms of an earlier asset when a later required placement fails. Production `plot_options` exposes asset-first transform alternatives; staged recursion preserves rollback and counts fitting work. More orientations do not grant an asset extra selection weight. Failure messages distinguish budget exhaustion from exhaustion of the enumerated alternatives. The formerly difficult same-seed witness and atomic failures pass in the fresh suite. [Fitter](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/world_plan.py#L279-L376), [required search](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/settlement_selection.py#L85-L128).

Unordered weighted memberships are canonicalized, while intentional schedules remain ordered. The same treatment extends to POI assets, locations and candidate construction. This corrects the prior guide's overbroad order-independence promise at the fresh-selection boundary without rerolling old saved choices. [Selection corrections](specialist_reviews/composition/G6_COMPOSITION_REVIEW.md).

### Additional sites have their own durable identity

The new format-4 registry describes additional sites separately from the existing featured landmark. A site owns a plot/placement, required goal, destination node and exact attachment. Its identity is distinct from its asset ID. Two shrines therefore remain two places with separate mutable contents. Counts, caps and repetition apply to accepted additional sites, with the featured landmark excluded. Once accepted, even a site above the minimum is a durable obligation. [Site selection and validation](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/poi_selection.py).

The default profile draws a desired count from two through four; it uses four existing rural assets, cap two each, nearest-site repeat multiplier 0.2, 80-tile join spacing and explicit town/junction clearances. A legal shortfall may publish only after meeting the hard minimum. A below-minimum result rejects the staged world. Sites retain rural Chunk semantics and do not acquire town districts, merchants or duplicate building blueprints. [Installed policy](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/data/generation/poi_profiles.json), [world membership validation](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/plan_integrity.py#L118-L150).

### Attachments refer to the actual road

G6 stores country-route ID, segment, join, tangent, side, frontage normal and chosen entrance. It checks the join against that segment's full road band and checks the complete perpendicular approach. A nearby unrelated road cannot make a false attachment valid. Candidate construction keeps collinear shared corridors usable while excluding true crossing/bend neighborhoods, bridges and protected private space. [Attachment implementation](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/poi_selection.py#L54-L219).

The derived physical road view combines full road bands, bridge decks and placement approaches. Four-neighbour connectivity handles genuine interior joins and band overlap without rewriting saved routes; diagonal corner contact is insufficient. Its two-million-cell bound prevents a dense graph of all world tiles. The independent retained-data audit reconstructed the rectangle union and shortest paths without importing the production graph code and matched all reported ordinary metrics. This proves the geometric projection; populated-scene access remains a separate check. [Road projection](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/road_network.py), [independent reconstruction](specialist_reviews/evidence/audit_results.json).

### Save compatibility is supported by authentic evidence

New worlds use format 4 / `wg6`, while old plans retain their actual origin and geometry. Already visited scenes keep their actual creator revision; pending older scenes use explicit current adapters. Save preflight checks reciprocal ownership, exact plan slices, identity and provenance before installing state. It does not regenerate a player's altered scene to match an original blueprint. [Adapter table](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/scene_adapters.py), [save preflight](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/engine/save_manager.py#L333-L403).

The genuine pre-edit G5 checkpoint is substantially better evidence than relabelled current output. Its seven-member inventory, six manifest payload hashes and saved plan match the supplied witness. All 611 capture inputs reconcile to G5: 376 exact and 235 newline-only matches. The saved plan equals the independent plan supplied with the G6 brief. Actual G5 boot/materialization/save created the fixture; its direct mutations are labelled fixture actions. The fresh G6 regression loads it with replanning forbidden, preserves its visited state and creates the pending scene through `g5-to-g6-v1`. [Fixture binding](specialist_reviews/persistence/fixture_source_binding.json), [persistence review](specialist_reviews/persistence/G6_PERSISTENCE_REVIEW.md).

The entire `placement.py` file is unchanged from G5, including `structure-v1`. Selection-only policy changes therefore remain separate from consumed layout/content compatibility. Existing visited scenes retain mutations; changed consumed definitions reject only affected pending scenes. Same-asset site independence, real container transfers, cold load/F9, checksum-consistent corruption and late-failure rollback all have substantive assertions, and their tests passed here. [G6 lifecycle tests](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/tools/critical_fix_regressions/tests/test_generation_g6_sites.py#L137-L247).

## 4. Ordinary worlds and travel: reproduced results

The three freshly generated plans are **exactly equal as JSON** to the corresponding retained final G6 plans. They retain one featured landmark each and contain eight additional site occurrences in total. No ordinary count shortfall occurred. [Independent plan comparisons and measurements](evidence/independent/review_summary.json).

| Seed | Desired / accepted extras | Additional assets | Physical road/access cells | Components | Compact plan bytes |
|---|---:|---|---:|---:|---:|
| 0 | 2 / 2 | Waymarker shelter; shepherd's hut | 38,106 | 1 | 594,641 |
| 20261023 | 3 / 3 | Shepherd's hut; roadside shrine; hunter cabin | 75,756 | 1 | 735,062 |
| 29417 | 3 / 3 | Roadside shrine; waymarker shelter; roadside shrine | 37,115 | 1 | 669,561 |

Across this small sample, shrine/hut/shelter/cabin frequencies are 3/2/2/1. The duplicate shrines are legal under the cap; soft repetition is a preference, not a uniqueness promise. All worlds created **zero local scenes during planning**. Diagnostic destination counts were 15/18/18, with every accepted site included; the required crossing is exercised separately. All three runs hit the configured 512-candidate truncation bound, without exhausting raw enumeration or missing their desired count. This is successful bounded sampling, not proof of an exhaustive geometric search or all-seed reliability. [Retained metric audit](specialist_reviews/evidence/G6_EVIDENCE_REVIEW.md).

The fresh diagnostic/journey wrapper took 154.652 seconds. Planning measured 0.926/1.494/1.250 seconds on this review machine; physical projection 0.059/0.164/0.072 seconds. The slowest timed destination scene was 0.2385 seconds. These are observations, not comparisons proving a regression against the different Windows environment. Site registry/policy/diagnostic metadata in retained plans occupies 1,473/2,229/2,320 compact bytes. Net plan growth over G5 also includes changed role composition and cannot be treated as isolated per-site cost. [Independent metrics](evidence/independent/review_summary.json), [retained metrics](specialist_reviews/evidence/G6_EVIDENCE_REVIEW.md).

The independent journey reproduced **37,781 movement steps, 586 exact cardinal boundary transitions and 352 materialized scenes before F9**. It visited the required crossing, both settlement forms, the featured landmark and two additional sites from their saved road joins. The added physical legs were 10,127 and 592 steps. The hut's container changed from two items to one; the shrine's from one to zero, with corresponding player inventory increases. F9 restored the coherent starting checkpoint. [Fresh journey record](evidence/independent/diagnostic/run.json).

The route uses production movement, doors, stairs, interactions, travel and save handlers, with stationary actors, paused AI/survival and invincibility disclosed. It does not prove unrestricted survival gameplay over that distance. A separate bounded native-update case remains positive. The fresh worst observed transition was 0.268 seconds. The **18,967,933-byte fresh checkpoint contains two starting scenes**, not all 352 explored scenes; save/restore measured 0.754/0.849 seconds. The retained Windows starting checkpoint differs by eight bytes and has the same two-scene scope. Separately, the retained controlled ownership checkpoint saves four scenes / 19,971,203 bytes. No result here measures a 352-scene save. [Journey scope](evidence/independent/review_summary.json), [controlled ownership evidence](specialist_reviews/evidence/audit_summary.json).

The two fresh production-renderer views included in this package show actual materialized shrines beside a road. They are useful confirmation of rendering and placement, but they do not demonstrate compound composition or general landscape aesthetics. [First view](evidence/independent/focused/g6-site-0-production.png), [second view](evidence/independent/focused/g6-site-1-production.png).

## 5. The confirmed authoring bug and the evidence qualification

### A layout with only optional targets fails unclearly as a site

Changing just the shrine's target flag to `required: false` produces this sequence:

| Stage | Reproduced outcome |
|---|---|
| Generic structure compilation | Accepted |
| Direct production preview | Passed |
| Assigned-site preview | Empty `StopIteration` |
| Fresh generation with that draft as the site cohort | Same exception |
| World receiver after failure | Unchanged |

The generic target schema permits a nonempty all-optional list. Site acceptance later performs an unchecked `next(...)` to obtain a required target. The installed four-asset cohort has required targets, so this is a **moderate authoring robustness defect**, not an observed failure of ordinary shipped worlds. [Exact probe/result](specialist_reviews/composition/optional_site_goals.json), [source lookup](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/poi_selection.py#L147-L150).

G7 should reject it at additional-site/compound-child eligibility with a useful `GenerationError` naming the asset and required-goal requirement. Preserve optional targets alongside required ones and legitimate generic/legacy all-optional consumers. Do not globally reinterpret historic saved content. The supplied portable probe makes the correction concrete; the empty-list case already has generic rejection and should retain it. [Reproducer](specialist_reviews/composition/probe_optional_site_goals.py).

### One tested Markdown representation remains unverified

The report claims 421 exact plus 239 line-ending-only frozen inputs. Independent reconstruction verifies **421 exact plus 238 newline matches: 659 of 660**. The remaining path is `roguelike/docs/STRUCTURE_AUTHORING.md`. Its delivered Git blob matches the tree and reported Git hash, and every receipt agrees on its tested hash. The tested raw file itself is absent; uniform LF/CRLF and several bounded variants do not reproduce that hash. Arbitrary mixed line endings remain possible. A prose discrepancy has **not** been established. Every frozen executable/runtime/data input reconciles. [Hashes and method](specialist_reviews/evidence/G6_EVIDENCE_REVIEW.md).

The right response is a precise limitation and better G7 capture: record raw and canonical-LF hashes, and preserve raw tested text when its checkout representation cannot otherwise be reconstructed. This does not justify calling the game build untested, silently declaring 660/660 verified, or rerunning all of G6 solely to replace missing historical bytes.

## 6. The report is generally careful about its evidence

All **1,194 archived members** match inventories, sizes, SHA256 and CRC. The ten final receipts agree on the frozen revision and bind every retained output. The 2,096 deliberately omitted disposable save payloads have reconciled paths/sizes, but their omitted contents cannot be independently verified. The 159 production workers and their import hashes reconcile; seven runner negatives and thirteen deliberate crash workers are expected controls, not release failures. [Audit results](specialist_reviews/evidence/audit_results.json).

Both browser logs cover 65 unchanged frozen documents plus 64 live documents, and all live catalog asset files are unchanged from G5. The actual downloaded candidate trees and downstream direct/assigned-site consumers reconcile. The outer authoring count is 19 commands/two actions, including five expected negatives; one command invokes G5's separate 22-command/four-action workflow. Adding these indiscriminately would inflate the claimed scope. [Browser/authoring audit](specialist_reviews/evidence/G6_EVIDENCE_REVIEW.md).

The owner guide is now materially useful for **single-building road sites**: it supplies a complete draft, actual export path, direct/assigned previews, deliberate installation, profile controls, failure explanations and saved-world effects. The confirmed required-goal diagnostic is its remaining gap. It openly states that compounds are not yet implemented. [Current authoring guide](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/docs/STRUCTURE_AUTHORING.md#L795-L954).

The failed initial final freeze is retained: 105 attempted workers stopped at the old evidence-root guard before gameplay. The corrected guard and plan preview were frozen again, followed by a complete successful rerun. This is an operational lesson for G7: preflight its disposable root at the start. The current guard accepts `.baseline` and `evidence/worldgen-g6`; it does not automatically accept `evidence/worldgen-g7`. Preserve its marker/source/save protections and use a synthetic negative, never an actual personal campaign. [Worker guard](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/tools/b3_worker.py#L10-L24).

## 7. Acceptance against the supplied G6 brief

| G6 requirements | Assessment |
|---|---|
| 01–03: before probes, transform search, canonical memberships | Met in inspected code, retained probes and fresh focused tests |
| 04–05: policy, counts, caps, repeat preference | Met for specified defaults/controlled cases; new required-goal admission gap noted above |
| 06–08: typed ownership, candidate protection, exact attachment | Met in source, malformed-record tests and all-normal certification |
| 09–10: physical connectivity and atomic publication | Met; independent graph reconstruction and runtime tests support the bounded contract |
| 11–12: complete content/access and independent mutable owners | Met for single sites; does not yet cover two children inside one compound scene |
| 13–15: historical witness, dependency semantics, preflight/rollback | Met; authentic G5 binding and fresh load tests are strong evidence |
| 16–17: ordinary seeds and real journey | Independently reproduced, including exact plan equality and both additional interactions |
| 18–19: executed owner workflows, browser/catalog/visual scope | Retained evidence supports them; fresh Linux run cannot execute the Windows-specific workflow |
| 20: final freeze, all gates, remote reconciliation | Gates/remote supported; one documentation byte-normalization claim remains unresolved |

This supports moving on with the two bounded carry-forward items. Existing `UI-TEXT-HEIGHT` inscription clipping remains deferred. Candidate truncation, sparse graph limits, pairwise junction work, finite world dimensions, whole-campaign retention and continuous-view presentation remain explicit boundaries. [Evidence index](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/evidence/worldgen-g6/INDEX.md).

## 8. Why G7 should be shared-access compounds

Your original concern was how disparate JSON structures become convincing places connected to streets and roads. G6 establishes a reliable relationship between **one building and one road**. The next missing unit is **a small place made of related buildings and common space**. A homestead with a house, work shed and yard tests that requirement directly, while staying small enough to preserve the proven save and travel boundaries.

The next step should therefore add a parent recipe, reserve its envelope and circulation, fit child buildings against explicit internal access, and save the resolved choices. Child IDs and content prefixes must remain distinct even when two children use the same asset. The shared chunk stays the single scene/save owner. This supplies a useful composition layer for later towns and POIs without immediately redesigning global street generation or streaming.

The proposed initial recipes reuse a narrow cohort:

| Recipe | Required buildings | Optional expansion | Transform caution |
|---|---|---|---|
| Homestead/workyard | Hearth house + tool shed | Storehouse | Existing children allow 0°/180°; shallow horizontal-road envelope |
| Wayside shrine court | Roadside shrine + waymarker shelter | No third building required for the shipped template | Compact envelope can supply vertical-road/four-normal coverage |

Approximate 44 × 16 and 18 × 14 envelopes are static feasibility sketches, not tested recipes. The current ordinary N/S fitter clips width to 18 tiles. G7 must introduce explicit parent/child bounds instead of widening town spacing. Parent transforms must respect each child's actual effective rotation/mirror permissions; changing old permissions can affect `structure-v1` compatibility. [Asset inventory](specialist_reviews/composition/compound_asset_inventory.json), [fitter bounds](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/world_plan.py#L328-L355).

Two implementation hazards deserve particular attention. First, the `compatible` argument on current reservation methods skips all rows of a permitted owner; blanket parent exceptions could allow sibling/private overlaps. Second, old placements assume their join is on their assigned road; an internal courtyard child needs a typed internal-access relationship. The brief explicitly requires narrow containment/shared-path permissions and rejects false country frontage. [Reservation implementation](https://github.com/dgobi/ResonanceRoguelike/blob/4d7a7892e1afffb8d872ed4a8fd442984d14e7d5/roguelike/generation/world_plan.py#L67-L86), [G7 architecture review](specialist_reviews/persistence/G6_PERSISTENCE_REVIEW.md).

## 9. Focused research update

I revisited primary sources for this specific next step. The useful common principle is to preserve intended relationships separately from the geometry that realizes them. The application below is my engineering judgment; none of these sources establishes that Resonance's implementation is correct.

- **CDDA's official overmap system** documents roots, ordered placement phases, rigid collections and mandatory versus available joins. This supports explicit composition/access contracts; G7 only needs a bounded recipe with a small number of children. [Official documentation](https://docs.cataclysmdda.org/JSON/OVERMAP.html#how-mutable-specials-are-placed).
- **Hierarchical Semantic WFC, Alaka and Bidarra (2023)** represents semantic refinement through parent/child relations and preserves the path by which concrete choices arose. The relevant lesson is to retain the meaning of “homestead” and its child slots. G7 does not need to adopt WFC. [Primary paper, §3](https://pcgworkshop.com/archive/alaka2023hierarchical.pdf).
- **MANSION (March 2026 preprint)** separates room connectivity requirements from geometric search, using a circulation hub and filtering candidate layouts against topology. For this game, use deterministic authored circulation and production validation. Its MLLM/3D pipeline and reported benchmark results are not transferable evidence for a tile roguelike. [Primary preprint, §3.1 and Appendix C](https://arxiv.org/html/2603.11554v1).

This is a targeted research update, not an exhaustive survey of every 2026 generator. It supports adding a small hierarchical composition layer while keeping hard access/ownership checks in the game's deterministic pipeline.

## 10. Updated implementation arc and handoff

| Stage | Purpose and boundary |
|---|---|
| G6, reviewed | Multiple independent single-building sites with exact country-road attachments and persistent owners |
| **G7, prepared now** | Narrow admission fix; two authored compound recipes; shared circulation; independent child state; complete owner authoring workflow |
| Subsequent composition review | Assess the resulting places, then select richer settlement/block/street composition and network quality work based on actual gaps |
| Later scale work | Measure explored-world retention/save cost, then address larger-world storage/streaming and continuous viewport behavior |

G7 keeps two-to-four **parent places**, with explicit minimum one compound and one single. It introduces policy v2 and plan format 5 / `wg7`, preserves all older intent, and captures a genuine G6 visited/pending checkpoint before editing. Planning validates geometry without creating scenes; first materialization validates every child after full population. A new same-asset-within-one-scene lifecycle test closes the ownership gap that G6's different-chunk test cannot cover.

The complete brief includes twenty acceptance requirements, real journey/interactions, six executed owner workflows, actual browser-downloaded child use, finite work/rollback, source freeze and guarded output preflight. It retains your standing main-branch/checkpoint/push protocol. No production implementation or later-arc brief was generated during this review.
