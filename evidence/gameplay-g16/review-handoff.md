# Resonance — G15 review and G16 handoff

**Reviewed:** 25 October 2026, America/Edmonton  
**Delivery:** `main`, `d26c6776b20c89c67a9b626bbc82059f50c770e7`  
**Certified implementation inputs:** `65607721fe9caa4eaa7affdd5568a32eda6bdb7e`  
**Previous reviewed baseline:** G14, `6b101d43389dba775b78cf4415c0ef638026f73c`  
**Next issued brief:** `CODEX_G16_WORKSHOP_PREPARATION_EXPEDITION.md` — issued, not implemented.

## Review conclusion

**G15 meets its commissioned finite-recovery outcome. No material gameplay defect or scope blocker was found. Proceed to the next bounded H1 task.** This is a source-and-evidence review judgment, distinct from an owner play assessment or certification of H1 as a whole.

The delivery provides an actual scavenging reason: a new apothecary holds one prepared treatment, the player can take and use that exact object, and spending it leaves the source depleted. Rejected treatment use is free. The implementation preserves the old apothecary and historical worlds instead of backfilling new rewards. [G15] [ITEM] [USE] [INVENTORY] [PROFILES]

The independent production-input journey passed. The independent seven-test G15 module produced **six passes and one historical-comparison failure**. That failure was isolated to the representation of a derived floating-point carried load under the review interpreter; the saved-state digests matched. A separately disclosed diagnostic reached the remaining historical checks and matched their complete observations. The original test result remains six passes and one failure, not seven passes.

The next brief is **G16 — Scavenged preparation at a furnished workshop**. It turns existing salvage, fire and processing rules into a reachable surface opportunity that yields a finite tactical preparation. It follows H1 package C without reopening the approved plan or absorbing the underground encounter work.

## 1. Scope and basis of this review

The review used the attached current compass, decisions/state, approved implementation proposal and workflow; the exact issued G15 brief; the two G15 commits; the completion record; relevant runtime/data/test changes; and the committed verification artifacts. The existing read-only review checkout was advanced from G14 to the pushed G15 delivery. No game code, tests, committed evidence, personal campaigns or wiki were changed.

This was a milestone review. It did not repeat the previous whole-project research, reread every historic chat/archive or run the comparison games. The approved plan supplies that strategic context. No full production release gate was rerun in this review.

## 2. What G15 delivers

| Commissioned property | Reviewed result |
|---|---|
| One finite treatment | `herbal_dressing`: up to 12 HP, 0.1 kg, nonstackable, generic existing appearance, one use. |
| Credible ordinary acquisition | `apothecary_b` retains the original layout, entrance/access policy and reagent pools; its medicine chest gains one independent, guaranteed treatment roll. |
| Narrow new-world selection | Only the grid and roadside commercial memberships switch from `apothecary_a` to `apothecary_b`; weights and caps remain. |
| Successful use | Existing clamped healing, actual-amount message, exact selected instance consumed and one ordinary inventory action. |
| Rejected use | Full health, stale ownership and absent/dead fighter consume neither treatment nor time. |
| Existing inventory semantics | Reading/equipment remain paid actions; the item-use boolean is not reinterpreted globally. Movement debt semantics remain. |
| Durability | Native acquisition, depletion, consumed state, cold loads and actual F9 rollback are covered. |
| Historical worlds | Old definitions, saved selections, visited content and pending old apothecaries retain their contracts. |
| Bounded delivery | No extra treatment tiers, rest system, starter redistribution, wiki rebuild or broad engine change. |

Sources: [G15], [ITEM], [POOL], [APOTHECARY], [PROFILES], [USE], [INVENTORY], [TESTS].

The important code change is the treatment-specific rejection boundary. `ItemSystem.use()` already has legitimate non-consuming actions, so treating every false result as a failed/free action would have broken reading or equipment. G15 avoids that mistake. The saved item fields and save schema did not need extension. [USE] [INVENTORY]

The data versioning is equally important. A new definition and two fresh-selection substitutions add the reward while leaving the old apothecary available to saved placement dependencies. G5/G13 historical expectations and catalogue assertions were adjusted without removing their coverage. [PROFILES] [TESTS] [HISTORICAL]

## 3. Verification: reported and independently observed

### Committed production certification

The delivery records Windows x64, CPython 3.11.0, pygame 2.6.1, tcod 19.3.0 and NumPy 2.4.6. [G15] [RELEASE]

| Check | Recorded result | Recorded elapsed time |
|---|---|---|
| Unfiltered focused discovery | 274/274 passing tests | 18m 48.0s, including runner overhead |
| Production D | 3,676/3,676 accepted assertions; 159 valid workers | 8m 37.6s |
| Genuine historical comparison | Pass | 2.9s |
| Bounded G15 journey | Pass | 25.8s |
| Final verification wall time | 19m 17.5s | Existing gates overlap in independent processes |

These are committed production results, not this review's rerun totals. The wall time is not total development time. The previous G14 final verification took longer, but two samples with different workloads do not establish a general performance improvement. [G15] [RELEASE]

The independent receipt audit reconciled all **782 source/Git bindings**, **89 indexed artifacts**, **12,890 ordinary-worker imported-source entries**, the 274-test log, the production counts and all seven runner negative controls. Artifact comparisons accounted explicitly for Windows-to-Linux line endings. The 159 production workers comprise 146 ordinary workers and 13 intentional crash workers; the latter's pre-crash checks were correctly excluded from the accepted assertion total. The frozen implementation inputs remain unchanged at the delivery commit. [RELEASE] [AUDIT] [INDEX]

### Independent checks in this review

Review environment: Linux x86_64, CPython 3.12.14, pygame 2.6.1, tcod 19.3.0 and NumPy 2.3.5. Dummy SDL, disposable save roots and outputs outside the repository were used.

| Independent check | Actual result | Meaning |
|---|---|---|
| Complete `test_gameplay_g15` module | Six passes, one failure; 19.881s | Effect, rejection, ownership, action costs, access and three-seed native selection passed; exact historical receipt comparison needs the qualification below. |
| Unchanged `tools/g15_journey.py` | Pass | Native local acquisition/use/persistence through the original game-loop driver. |
| Unchanged standalone historical verifier | Fails at initial exact snapshot comparison | Same derived-load mismatch as the focused test. |
| Receipt-only legacy-sum diagnostic | Otherwise exact historical agreement | Establishes the remaining old-world observations after isolating the numeric comparison; not an unchanged test pass. |
| Committed source/evidence integrity | All inspected bindings and indexed artifacts reconcile | Supports that production reports describe the delivered implementation. |

The independent journey observed a real chest with its two reagents and exactly one dressing. The dose was acquired through ordinary controls. A separate game process cold-loaded the acquired-but-unused checkpoint and used it: **36 → 48 HP at the effect boundary, 48 HP after the normal turn, one turn spent, one dose consumed**. Other possessions and equipment remained intact. Exit/return and search found no replacement. A third process cold-loaded the consumed/healed checkpoint. Both F9 checks followed an actual unsaved legal movement and restored the identified saved snapshot.

The complete treatment text and recovery message were also visually inspected in the production-rendered review views. This establishes readable text at those presentation settings, not universal UI support.

### One nonblocking finding: cross-interpreter receipt comparison

At `tools/g15_historical.py:29`, the unchanged review run compared a derived load of `6.4` with the retained value `6.3999999999999995`. Every other initial snapshot field, including player, world and scene digests, matched. The same seven unchanged effective item weights reproduce the historical value when accumulated left to right. Python documents a change to floating-point `sum()` in 3.12. [PY-SUM]

For diagnosis only, an external wrapper calculated the returned receipt's load that way. It changed no item, inventory, save implementation, fixture, source or digest. The complete subsequent historical observation then agreed: **51 placement dependencies, five old apothecaries, the pending old-apothecary fingerprint, no new dressing, and the already depleted visited scene**.

**Disposition:** record this as verification portability work, not a demonstrated G15 save regression. Continue using the established production interpreter for release gates. If cross-interpreter receipt portability is later commissioned, handle derived numbers deliberately while retaining exact ownership/state digests. Do not rewrite historical fixtures or silently round live inventory calculations. This does not enlarge G16.

## 4. What remains unproven

G15 explicitly allowed one initial staging at the genuine public approach and one 24-HP setup injury. Its script uses full-state routing and UI choices while normal AI, FOV, survival and action costs remain active. The independent run retained those conditions. [JOURNEY]

It therefore proves the local treatment chain. It does not establish unaided discovery from the laboratory, fair ordinary attrition, an adequate all-seed recovery supply, or the full two-expedition H1 exit condition. Twelve HP remains an initial tuning value. Those are expected limits of the commissioned brief, not missing G15 deliverables.

## 5. Why G16 should be a workshop preparation expedition

The approved plan asks for a purposeful surface outing before the deliberately populated underground destination and full integration review. The next useful question is whether ordinary scavenging can produce a preparation the player has reason to bring home or use on another outing.

The existing musk route is suitable:

- The starter inventory and laboratory do not supply a musk gland or pellet.
- A gland satisfies the existing single-item material conjunction; a stationary fire supports the existing ten-phase drying process.
- The existing pellet briefly disrupts creatures in its zone and can buy room to withdraw. Its live effect is not restricted to one predator faction.
- G12 already demonstrated actual crafting, throwing and a controlled retreat comparison. G13/G14 provide native containers and empty-crate salvage. G16 can reuse those rules and spend its effort on a believable place, native inputs and a complete surface trip. [START] [LAB] [RECIPE] [GLAND] [EFFECT] [G12] [G14]

The proposed `workshop_b` has a real crate containing **one gland and one wood bundle**, plus a short, truthful preparation note and a coherent furnished work area. Emptying and dismantling that crate can supply the second campfire fuel. Other legitimate fuel remains usable. The starter cutting tool and burning torch can support the chain. No finished pellet is gifted. [WORKSHOP] [CAMPFIRE] [TORCH]

This leaves exact unusual-weapon redistribution for its relevant future brief. Heavy Blade would bring the still-unconsumed Press free-move flag into this task; there is no need to make that unfinished tactic a dependency of the first workshop reward. Stone Lurker's known waking-attack issue remains relevant before relying on that threat, but the selected route does not depend on it. Those are existing scoped dependencies, not G15 regressions.

### Native availability and route preflight

Read-only native generation at the reviewed G15 revision found:

| Seed | Ordinary starting chunk | Workshop candidate | What the sample establishes |
|---|---|---|---|
| `20261023` | `(73,99)` | `(75,100)`; another at `(76,99)` | A convenient diagnostic route near the earlier shed/apothecary examples. |
| `0` | `(30,83)` | Nearest `(83,117)` | No nearby workshop in this sample. |
| `29417` | `(106,46)` | `(104,46)` | A selected workshop two chunks away. |

The primary candidate is `settlement-0-cross-market-lot-1-44-S-0-building`, rotation 0, public join local `(21,21)` in `(75,100)`. It was selected normally; no target was inserted.

An additional read-only preflight began at the actual laboratory start, equipped the starter blade/jacket, ascended and crossed east/east/south through normal input handlers. It used the actual starting flask once and reached that join in **235 turns, from turn 480 to 715, with 60 HP remaining**. No staging, injected rewards, extra supplies, threat removal or invincibility was used.

This preflight intercepted `Engine.run` during boot and then used real handlers with full-state threat-aware routing. It is **approach feasibility**, not a final game-loop journey, unaided discovery, the new workshop chain or a return-trip result. G16 must demonstrate those scoped implementation outcomes itself. The sample does not justify a nearby-workshop guarantee or generation-policy expansion.

## 6. Handoff and current state

| Item | Current status |
|---|---|
| Approved strategic path | Unchanged; H1 remains the active horizon. |
| G15 finite recovery | Delivered and reviewed; narrow outcome supported, with the disclosed verification-portability observation. |
| G16 workshop preparation | Concrete brief issued; not implemented. |
| Underground encounter authoring/content | Subsequent bounded work; not part of G16. |
| Full two-outing, alternate-approach and recovery balance proof | Still required before H1 completion. |
| Deferred progression/origin/death/transformation policies | Remain deferred. |

Give Codex `CODEX_G16_WORKSHOP_PREPARATION_EXPEDITION.md` for the next implementation. It contains its own execution boundary and stops after the workshop expedition is delivered. The approved compass, plan and workflow need no strategic rewrite for this milestone. This dated review records the changed baseline and next brief; it does not turn reference-pack maintenance into a new implementation gate.

## Source register and reproduction

Repository links below are pinned to reviewed G15 delivery. The issued G15 brief and attached reference pack are the scope sources. Independent review artifacts remain in the review workspace under `research/g15_review_code.*`, `research/g15_review_historical_*`, `research/g15_review_evidence/`, `research/g16_surface_availability.json` and `research/g16_route_preflight*`.

Independent focused command, from the review checkout:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYGAME_HIDE_SUPPORT_PROMPT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=20261020 PYTHONPATH=roguelike:tools:tools/critical_fix_regressions/tests /tmp/resonance-plan-venv/bin/python -m unittest -v test_gameplay_g15
```

Independent journey command used the same environment and interpreter with `-X utf8 tools/g15_journey.py --evidence /workspace/scratch/ea0eedaa4952/research/g15_review_evidence/journey`. Production commands and environment remain in the committed [delivery record][G15]. Review-environment commands are not instructions to change the production interpreter.

[G15]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/docs/owner/GAMEPLAY_G15.md
[G12]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/docs/owner/GAMEPLAY_G12.md
[G14]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/docs/owner/GAMEPLAY_G14.md
[ITEM]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/items/consumables/herbal_dressing.json
[USE]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/engine/item_system.py
[INVENTORY]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/engine/inventory_screen.py
[POOL]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/loot_pools/apothecary_b_treatment.json
[APOTHECARY]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/buildings/commercial/apothecary_b.json
[PROFILES]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/generation/settlement_profiles.json
[TESTS]: https://github.com/dgobi/ResonanceRoguelike/tree/d26c6776b20c89c67a9b626bbc82059f50c770e7/tools/critical_fix_regressions/tests
[HISTORICAL]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/tools/g15_historical.py
[RELEASE]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/evidence/gameplay-g15/final-a/release.json
[AUDIT]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/evidence/gameplay-g15/audit.json
[INDEX]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/evidence/gameplay-g15/artifact-index.json
[JOURNEY]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/evidence/gameplay-g15/final-a/journey/journey.json
[START]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/main.py
[LAB]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/layouts/starting_lab.json
[RECIPE]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/recipes/musk_pellet.json
[GLAND]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/items/butchery/stalker_musk_gland.json
[EFFECT]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/engine/effect_lifecycle.py
[WORKSHOP]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/buildings/commercial/workshop_a.json
[CAMPFIRE]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/recipes/campfire.json
[TORCH]: https://github.com/dgobi/ResonanceRoguelike/blob/d26c6776b20c89c67a9b626bbc82059f50c770e7/roguelike/data/items/tools/tallow_torch.json
[PY-SUM]: https://docs.python.org/3.12/library/functions.html#sum
