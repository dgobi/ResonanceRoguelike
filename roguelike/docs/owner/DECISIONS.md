# Owner decisions

All entries are **open**. Defaults below are proposals for discussion, not approvals. None blocks baseline/setup/documentation. Routine wrong field names, slots, cache owners or API arguments are implementation defects, not new creative choices.

| Decision | Current source / intent tension | Proposed framing / when needed |
|---|---|---|
| Start: Touched or zero/Unmarked | Design says Touched; new player/Engine begin at zero, HUD shows Unmarked. | Preserve Touched as written intent for discussion; choose explicit thresholds/early experience before changing start state. |
| Discovery vs recipes/perk points | Design values experimentation/no recipe lists; C lists recipes, K spends level points. | Identify useful scaffolding vs intended player-facing mechanics before progression work; do not remove functioning UI in this baseline. |
| Authored remains vs butchery | Narrative remains are environmental history; creature corpses/yields support butchery; lab body special is skipped. | Decide authored remains and killed-creature remains separately before changing content acquisition. |
| Offscreen time | Named reality bubble is incomplete; processing reads wrong cache owner; live pursuers have special ticking. | Define catch-up/frozen/continuous policy per system before implementing away-time behavior. |
| Save compatibility | Current format version 1, pickle, incomplete reconstruction and no migration contract. | Keep personal saves untouched; decide disposable development saves vs supported migration before B2/B3. B1 tests synthetic fixtures only. |
| Supported OS/render modes | Windows sprite at 1280×720 observed; font-folder case mismatch, ASCII/UI variants uncertain. | Adopt that narrow development target provisionally; owner decides expansion before portability/renderer work. |
| Discovery information | Debug exposes extra knowledge; map/examine behavior may reveal more than intended. | Decide what remains hidden, when and why before changing overmap/examine/lexicon presentation. |
| Documentation authority | Two canonical-labeled CLAUDE files, duplicated OMNIDOC, stale technical guides. | Approve separate design decisions / source-backed handbook / observed evidence authorities; root README proposed entry point. |
| Corruption ownership | Engine resonance corruption and player Corruption.value coexist. | Choose one authoritative mechanical value while preserving exposure as a separate concept if desired; coordinate thresholds/UI before implementation. |

To close a decision, record date, owner wording/approval, scope, selected policy, affected source/documents and a visible acceptance example. No owner learning completion or creative approval was received in Arc A; the owner only confirmed a manual input sequence.
