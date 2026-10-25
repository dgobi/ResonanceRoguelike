# Resonance Roguelike Decisions and Current State

**Version:** 1.0  
**Prepared:** 24 October 2026, America/Edmonton  
**Repository:** https://github.com/dgobi/ResonanceRoguelike  
**Reviewed branch:** `main`  
**Reviewed HEAD:** `f9fe901417b360bc1fda84835e0a793eaac2f6df`  
**Latest reviewed commit:** `docs(wiki): deliver verified G9 edition with exact checkout product bytes`  
**Evidence scope:** Repository/source inspection, committed reports, supplied historical archives, accessible project discussion context, and the actual G9 review/G10 brief. Game verification suites were not rerun for this reference pack.

This is a dated reference. Recheck the repository and latest owner instructions before using its current-state statements to plan implementation. The enduring game direction is in `RESONANCE_PROJECT_COMPASS.md`; the review process is in `RESONANCE_WORKFLOW.md`.

## Reading status correctly

| Label | Meaning |
|---|---|
| Owner direction | An explicit owner instruction, with its date and scope retained. |
| Retained design | Creative intent preserved in project sources; conflicts and open choices remain open. |
| Source-checked | A relevant path or value was inspected at the identified commit. This alone is not a runtime test. |
| Reported verified | A reviewed report or retained receipt records verification; it was not rerun for this pack. |
| Observed in this review | A check actually performed by the current reviewer, with its scope stated. No new game-test result is claimed here. |
| Proposal or issued brief | A suggested or written future task; not evidence of owner acceptance, execution or completion. |
| Open | A consequential policy is unresolved or conflicting. Unrelated useful work can continue. |
| Superseded | Historical guidance replaced within a stated scope by a later instruction or result. |

A feature can be source-checked and reported verified while still needing a player-experience assessment. A completed implementation does not automatically resolve its creative design questions.

## Explicit owner directions to carry forward

### D1 Playable exploration governs infrastructure

**Status:** Owner direction, 24 October 2026.  
**Source:** G8/G9 review discussion supplied in the project context.

> It is important we do not get lost in simulating real, efficient road networks when our goal remains a fun, playable, realistic in appearance open world post apocalypse fitting our setting. Let's be sure to keep that objective in sight.

**Consequence:** Roads and generation serve readable travel, interesting places, access and atmosphere. Further network sophistication needs a demonstrated player benefit. Completing a road arc does not automatically commission another one.

### D2 Wiki upkeep is separately commissioned

**Status:** Owner direction, 24 October 2026.  
**Source:** The same review discussion, superseding earlier blanket wiki expectations.

> I also want to take care not to bog down codex with an undue burden of wiki maintenance. That will be done in specific targeted briefs at my disclosure, not as part of the regular implementation process.

**Consequence:** Ordinary implementation does not include wiki chapter/example updates, a full HTML rebuild, wiki release gates or a recurring wiki-impact checklist. A narrowly needed feature guide and an accurate completion report can still belong to the commissioned task.

**Known conflict:** The inspected `AGENTS.md` still mandates automatic wiki work. The issued G10 brief already includes a small explicit replacement of that paragraph. That correction was not present at the reviewed HEAD; its inclusion in a brief is not proof it has been applied. [R1, R7]

### D3 Preserve the established development arrangement

**Status:** Recorded working preference in repository guidance and milestone briefs.

Implementation uses the owner's existing production checkout on `main`, preserves unrelated work and personal campaigns, and creates named checkpoints before substantial changes. Codex performs autonomous headless/app-local verification without controlling the owner's desktop or assigning routine testing to them. [R1]

Keep publication authorization scoped correctly. The repository distinguishes local commits from permission to push; G9's invoked brief authorized publication, and the issued G10 brief specifies publication when supplied for implementation. Carry forward authorization already provided in the actual execution session; do not ask again merely because work reaches that step, and do not infer fresh permission from this reference pack. [R1, R2, R7]

### D4 Repair reliability and support the owner's authorship

**Status:** Owner direction in the audit/review discussions, reflected in B–D and G work.

Critical faults come before expansion that depends on them. The owner also needs understandable, practical guidance for tweaking systems and adding content, including structures used by procedural placement. The project has since progressed through repair and authoring arcs; this is not an instruction to restart the original audit before every task. PDFs are not the requested routine report format. [R3, H1]

## Current implementation baseline

### What the recorded arcs have established

The table describes delivered scope recorded in the inspected repository. It does not claim that every subsystem is finished or newly accepted by the owner.

| Arc | Delivered purpose recorded in current sources |
|---|---|
| A and B1–B3 | Runnable baseline and progressively repaired scene identity, reconstruction, coherent checkpoints, dirty-state capture, recovery and slot-scoped handling. |
| C | Item/equipment/container ownership, transfers and crafting cancellation/output handling. |
| D and subsequent critical fixes | Combat/effect lifecycle, interaction and turn ownership, modal input, allocation and related correctness repairs. |
| G1 | Generation correctness, access and first-entry population. |
| G2 | Supported structure validation, runtime previews and lossless offline authoring. |
| G3–G4 | Shared world planning, connected composition and preservation/restoration of native gameplay content. |
| G5 | Settlement variety, plot roles, selection controls and certified authored content. |
| G6–G7 | Rural roadside sites, then compounds with shared access and independent child contents. |
| G8 | Bounded settlement layouts, civic commons and frontage. |
| G9 | Bounded optional country shortcuts while preserving the complete G8 composition. |

Sources: [current delivery records](https://github.com/dgobi/ResonanceRoguelike/tree/f9fe901417b360bc1fda84835e0a793eaac2f6df/docs/owner) and [B–D state/verification records](https://github.com/dgobi/ResonanceRoguelike/tree/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/docs/owner).

### Facts that belong here rather than in the compass

At the reviewed revision, the existing game is a Python/Pygame/tcod tile-based implementation. World creation uses 128 by 128 coarse chunks; local maps use 80 by 43 cells. Current settings specify 2–4 settlements. Fresh G9 plans use settings version 4, plan format 7 and origin `wg9`. These are current implementation facts, not permanent design commitments. [R2, R4]

G9 permits at most two optional country connections under bounded rules. It does not deliver a continuously scrolling viewport, unlimited world scale, a full transport simulation, capital redevelopment or new river crossings. [R2]

The final G9 record reports ten release gates passing against frozen game inputs `919e8b40ab5ebca6cf5df6ae3afaf6baa4b67d78`, including 229 focused tests and 3,675 production checks across 159 workers. Later documentation commits produced the reviewed HEAD. These are retained results, not fresh executions for this pack. `E04 / UI-TEXT-HEIGHT` remains an explicitly documented deferral. [R2]

The extensive G9 journey used controlled conditions, including paused AI/survival and invincibility. It provides valuable traversal and persistence evidence. It does not establish normal expedition pacing, whole-game survival balance or fun. Three sampled worlds likewise do not establish universal generation or performance quality. [R2, R6]

### Latest issued direction

**G10 wilderness character and playable exploration** is the latest recovered implementation brief. The inspected repository and supplied attachment set do not establish its implementation or completion. No later owner approval is inferred from its existence. [R7]

Its proposed outcome is coherent, distinct wilderness using existing assets: forest stands and clearings, wetland pools and firmer routes, barren Ash Wastes, and mountain rock masses with passable gaps. It preserves existing geography, roads, towns, sites, ownership and save contracts, and adds a short expedition with ordinary visibility, AI, survival and supplies. It excludes wiki upkeep and further road optimization.

This is consistent with the latest owner correction. The preceding G9 review found a specific mismatch between Ash Wastes' barren description and its generated grassy/resource-rich scene. That is prior review evidence and source context, not a new runtime measurement made for this pack. [R6]

Do not generate a competing G10 or preauthorize G11 from this state file. Verify subsequent work, then choose the next bounded objective from the resulting experience and material defects.

## Open decisions to preserve

These questions are retained from the owner decision register and relevant design/code comparisons. The old register contains stale technical premises, so the descriptions below preserve the question while avoiding revival of repaired bugs. [R3]

| Question | Current tension and safe default | Resolve when |
|---|---|---|
| Starting transformation | Retained origin says Touched; inspected component and engine initialization begin at zero. Preserve the story reference and functioning start without claiming they agree. | Origin, corruption or early progression is deliberately revised. |
| Discovery and progression UI | Intent favors experimentation and found knowledge; current crafting lists recipes and the perk screen spends level points. Keep existing functionality until a replacement is scoped. | A progression/discovery arc is commissioned. |
| Authored remains and butchery | Transfigured apocalypse remains carry environmental history; acquired creature materials support existing butchery. Do not apply one blanket rule to both. | Remains, harvesting or related content policy changes. |
| Corruption ownership | Engine corruption and a player corruption component coexist. A consolidation needs a defined mechanical owner and relation to exposure, thresholds and UI. | Corruption mechanics are changed. |
| Offscreen time | Some current effects age on active/hot maps while cold maps freeze. A complete away-time policy is not implied by an open world. | A specific system needs freeze, catch-up or continuous behavior. |
| Information revelation | The intended boundary between what the player knows, discovers and sees through debug tools is not fully settled. | Overmap, examine, lexicon or discovery presentation changes. |
| Long-term save support | Repair arcs and versioned generation adapters exist. They do not establish universal migration or indefinite backward/forward compatibility. Preserve personal campaigns and the existing supported contracts. | Format policy, migrations, retention or release support expands. |
| Platform and presentation support | Current evidence has bounded execution/rendering coverage. Old font-case faults should not be repeated as current defects; broad platform/render-mode support is still a separate commitment. | Portability or presentation scope changes. |
| Adoption of a single creative authority | Multiple old files call themselves canonical. This pack organizes explicit direction and retained intent, but does not newly approve every historical design paragraph. | The owner explicitly changes canon or design authority. |

For code evidence of the first two tensions, see [player creation](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/main.py), [Corruption defaults](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/components/corruption.py), [engine state](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/engine/engine.py), [crafting screen](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/rendering/craft_screen.py) and [perk screen](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/rendering/perk_screen.py). Current effect-aging scope is recorded in [D_STATE](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/docs/owner/D_STATE.md#L64-L82).

Resolve a consequential question by recording the owner's actual choice, date, scope, reason and replaced decision. Routine corrections to an incorrect field, API call or cache owner do not require turning a bug fix into a design referendum.

## Sources that need careful interpretation

| Source at the reviewed HEAD | Useful role | Freshness or authority limit |
|---|---|---|
| Root `README.md` and G9 delivery report | Current entry point and delivered G9 scope | Still recheck the commit and actual source before the next review. |
| Root and nested `CLAUDE.md` | Rich creative intent and historical development context | Mixed technical claims; both carry historical banners. Confident labels and roadmap ticks are not implementation proof. |
| `roguelike/docs/owner/STATUS.md` | Detailed repair/authority history | Top heading still says G5 at a G9 HEAD. |
| `roguelike/docs/owner/NEXT_ARC.md` | Historical sequencing | Top heading still says after G2. It is not the current next-brief instruction. |
| `roguelike/docs/owner/START_HERE.md` | Historical owner orientation | Top heading still reflects B3. Recheck commands and state claims. |
| `roguelike/docs/owner/DECISIONS.md` | Unresolved design questions | Preserve questions; do not copy obsolete save-format or repaired-defect descriptions. |
| `AGENTS.md` | Repository working preferences | Automatic wiki paragraph conflicts with D2; G10 already specifies its narrow correction. |
| Owner wiki and authoritative feature guides | Learning and manual content-authoring reference | Check their reviewed revision and topic. Ongoing usefulness does not imply upkeep in every task. |
| World-generation proposal | Rationale, candidate methods and historical audit | Written against `ce1ef760d411a0d1e9dfec93f1addf149955ac8c`; not the current backlog or a blanket implementation mandate. |
| FullGame and B–D archives | Historical snapshots and verification context | Superseded for current implementation by the inspected live repository. |

## Deferred work is a set of options

Full ritual-bell magic, world-age ecology, shelter progression, larger worlds, a continuous viewport, additional capital/ruin content and wider offscreen simulation remain potential future directions. This list is not an ordered roadmap.

Checkpoint growth and save/load cost deserve a focused future assessment when expanded campaign targets or observed friction make it useful. G9's reported costs are scoped measurements, not a reason to absorb checkpoint redesign into every generation task. Prefer fixing a demonstrated blocker or improving a concrete expedition over adding another layer of machinery by default. [R2, R6]

## How to refresh this record

At the next substantive review, check the live commit and current instructions first. Replace the short baseline with the new dated result; add or amend only consequential decisions. Retain an older revision as history rather than nesting many obsolete current-state sections inside this one.

Updating this pack is ChatGPT review/documentation work when requested. It is not a new routine Codex acceptance gate and it does not trigger wiki maintenance. A short context-change note in a review is enough between deliberate refreshes.

## References

- **R1:** [AGENTS.md](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/AGENTS.md).
- **R2:** [G9 delivery and evidence limits](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/docs/owner/WORLDGEN_G9.md).
- **R3:** [Open decisions](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/docs/owner/DECISIONS.md), [historical status](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/docs/owner/STATUS.md) and [critical-fix verification](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/docs/owner/CRITICAL_FIXES_VERIFICATION.md).
- **R4:** [Main](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/main.py), [config](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/config.py), [current generation settings](https://github.com/dgobi/ResonanceRoguelike/blob/f9fe901417b360bc1fda84835e0a793eaac2f6df/roguelike/data/generation/g3_config.json).
- **R6:** [G9_REVIEW.md](https://chatgpt.com/library?file_id=libfile_34bbcd2140ac8191a1292a832fa57638&account_id=personal), issued 24 October 2026. Read in full for this pack; its runtime results remain evidence of that earlier review.
- **R7:** [CODEX_G10_WILDERNESS_CHARACTER.md](https://chatgpt.com/library?file_id=libfile_9c4a6b71ec148191bc9803b19ea3b14e&account_id=personal), issued 24 October 2026. Read in full; no implementation or acceptance event is inferred.
- **H1:** Supplied project-chat excerpts and targeted retrieval of project history; `FullGame.zip`; `Resonance_B-D_Review_20261023.zip`; and `WORLD_GENERATION_AUDIT_AND_PROPOSAL.md`. Coverage and limitations are described in `RESONANCE_START_HERE.md`.
