# Source, execution evidence and limits

GUIDE-1 reviews game and Workbench source at **`c166ec650b98156d53b8ea72e715c028d27db905`**, the same SYS-5 revision investigated by the commissioned research package. The actual production checkout was verified before editing; it was not reset to match the package. Earlier handbook edition 1.3 reviewed G9 (`f76aac…`) and is preserved as dated metadata under `audit/edition-1.3/`. A later handbook delivery commit can differ from the reviewed game commit without altering gameplay.

## What evidence means here

**Source-checked** means the current definition, validator and consumer were inspected together. **Executed** means the distributed input was run and its observation recorded. **Historical** means an older report is retained with its original date/scope. **Proposed** means a design has no current behavior guarantee. Definitions retained in catalogues are not automatically supported controls. The [atlas](#system-atlas) and [family reference](#authoring-reference) make those distinctions operational.

| Route | Evidence retained | What it establishes |
|---|---|---|
| L01/L02 | `final-practice/L01`, `L02` | Food use, ordinary pickup, exact consumption, free unknown-handler rejection and cold state |
| L03/L08 | `L03`, `L08`, reader PNGs | Physical text carrier, actual scrollable reader and selected font role |
| L04 | `L04` | Real craft/placement screens, free cancellation, exact material commitment; parent and cold process finish, acquire and eat the output |
| L05/L06 | `L05`, `L06` | Constructed composite actor, actual approach/retreat response, room clue, ordinary stairs and retained depletion |
| L07 | `L07` | Controlled generated-world assignment and building selection; real constructors and entrance input |
| L09 | `L09` | Actual Q dispatch, hit/cooldown and bounded negative controls |
| L10 | `L10`, `original-loop.png` | New primitive via original event loop, explicit success/rejection/time/consumption |
| L11 | `L11` | Real K purchase, ON_TURN, duplicate prevention, cold continuation and cleanup |
| L12/L13 | `L12`, `L13` | Survey state machine, paid/cancel/inspect rules, cold continuation, scene retention, malformed/absent state |
| Workbench | `workbench/index.json` | Relevant observed native UI workflows, fixture roots and executable identities |
| Reader and build | `final-edition/`, `final-edition/reader/` | Repeat build, drift, internal anchors, offline downloads, navigation/search/reveals and rendered layouts |

All receipt paths above are under repository `evidence/guide-1/`. The release bundle includes the concise final receipts, along with source and helpers. The practice launcher records every distributed solution/patch hash; individual receipts name the actual input events and controlled initial conditions. An original-loop result is identified separately from direct input-handler checks. Each relevant cold check starts another interpreter with the same registration installed **before loading**.

World generation uses a declared controlled assignment policy, not a claim about ordinary population frequency. Staging the player at a generated entrance isolates construction and travel from navigation time. Combat checks use bounded conditions; a world seed alone is not proof of replay-identical combat. No full production regression campaign is claimed for this documentation commission.

## Small topic map

`source-map.json` connects pages and lessons to definition/code prefixes, important symbols, relevant commands and receipt paths. It reuses `source-manifest.json` for actual file identities. Workbench project-owned source, Python/Rust/TypeScript/configuration and lesson inputs belong to the edition binding. Generated products are not inputs to themselves.

```powershell
& $ResonancePython -B Resonance_Wiki_Maintenance/check_topics.py --repo .
& $ResonancePython -B Resonance_Wiki_Maintenance/build_wiki.py --repo . --check-drift
```

The first command reports which topics **might** need review; prefixes deliberately err on the side of showing related pages. Exit 1 means potential impact. The second is the stricter source/authoring/product identity check. Neither rewrites text, approves a SHA, or proves a sentence correct. A declaration and its factory may agree while a runtime consumer ignores the value: inspect all three, then exercise the route. [L14](#L14) teaches that investigation.

## Research rationale

The owner's complete research/commission and source ledger are retained in `evidence/guide-1/commission.md`. Part I supplied the curriculum rationale: worked examples followed by meaningful variation, graduated hints, retrieval and diagnosis, then independent construction with explicit acceptance criteria. GUIDE-1 uses that structure without making a claim that these particular pages have been tested with learners. The ledger distinguishes implementation sources from educational research; it does not substitute for the current checkout inspection or executable examples.

## Practical limits

Automation cannot establish your comprehension, retention, comfort with the interface, or ability to create a novel system independently. Headless browser checks are not a screen-reader audit or OS clipboard readback. The observed native Workbench checks cover selected workflows, not every family/control combination. Font/layout examples do not prove every game screen handles arbitrary size or content. No personal-save migration, universal plugin API, generic status engine, ranged-combat framework, or new production content is delivered by this guide. Follow [maintenance](#maintenance) when the source changes; keep the dated offline edition as a usable record.
