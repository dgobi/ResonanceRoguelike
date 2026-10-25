# G12 — Reliable expedition rewards

25 October 2026, America/Edmonton. Production checkout `main`.
Reviewed starting HEAD: `069ca40dac7bdbf5a7a40b205a1358c8da919e21`.
Final frozen runtime/test inputs: `08c1cf9f84b15340563ee969a0a369890d8dd24e`.

The Revelation Lens and all three existing satchels work through ordinary
inventory commands. Carrying display and admission share one derived load.
Preparation spends physical materials, retains tools and distinguishes active
flame from a stationary processing site. A real gland completes the existing
musk-pellet chain. Found texts retain their complete authored information and
offer bounded scrolling without additional world actions.

## Delivered contracts

- Selected missing/null equipment handlers resolve at ordinary use, preserving
  untouched item records and historical satchel dependency hashes. Explicit
  non-null custom handlers remain intact. The Lens keeps its weapon slot,
  existing Reveal/True Strike actions and cooldowns; damage uses `1d4` plus 2.
- Inventory totals, item rows, detail weight, pickup, container/take-all,
  exchange/output and encumbrance share the live effective-weight calculation.
  Exchanges account for removal of equipped bags. Item weights remain unchanged;
  bag removal and overweight restoration preserve every possession.
- Materials and single-item conjunctions are spent on successful commitment;
  physical `tools` are kept; ambient conditions cannot supply free materials.
  Explicitly chosen reusable material is labelled spent and detaches safely.
  The small recipe catalogue's vessel/heatproof/cutting roles are reconciled.
- Active usable offhand flame supplies its burning tier. Extinction, expiry and
  displacement remove it. Passive placement additionally requires stationary
  fire, with the existing separate campfire placement and ignition actions.
- Reader layout measures actual font/glyph surfaces, preserves breaks and
  authored span identity, and reaches overflow on later pages, inscriptions and
  the alphabet. Left/Right changes authored pages; arrows/PgUp/PgDn/Home/End
  scroll. Esc/Enter closes. Navigation performs no learning, recovery or turns.
  The current E04 cutoff oracle is replaced positively; historical evidence stays.

The affected [systems guide](../../roguelike/docs/SYSTEMS.md) and
[data reference](../../roguelike/docs/DATA_REFERENCE.md) explain the supported
controls and fields. G11's ordinary-outing prose is corrected to 186 movement
inputs / 216 turns; its historical receipts are unchanged.

## Demonstration and durability

The [real-event journey](../../evidence/gameplay-g12/final-b/journey/journey.json)
uses the existing original `Engine.run` event driver and production renderer.
The laboratory world seed is 20261023; the controlled grass fixture uses 29417.
The established driver explicitly seeds gameplay RNGs to 20261020. AI, normal
FOV and survival remain active; invincibility is off.

The normal-start laboratory route acquires the existing label and Lens without
inserting either or repositioning the player. The complete warning is visible,
including “do not ring the bells.” A separate 480×320 production-reader view
verifies bounded access. One disclosed native Hollow Knight is added after
acquisition to isolate real Reveal and True Strike; the player ends at 56 HP.

The controlled integration starts with a disclosed grass scene, a container
(component satchel, pitted blade, 18 wood bundles) and Heath Stalker remains.
Starting possessions, health and needs remain. Native tier-2 butchery uses the
explicit disclosed source-action RNG seed 0 and yields a real gland, acquired
through the normal interaction. A 25.40 kg raw load admits as
19.04 kg effective load. The chain spends two wood bundles and one
gland, retains the cutting implement, ignites the placed campfire, completes
the authored ten processing phases (including placement), picks up the result
and throws that crafted pellet through ordinary targeting. No finished pellet
is supplied.

A supplemental native inventory view loads that actual crafted-pellet checkpoint
without spending world turns. Raw 1 kg wood shows the same reduced 0.7 kg value
in its row and detail pane (0.65 kg before display rounding).

The paired retreat starts from the same checkpoint and uses eight AI phases in
each branch, charging the control one wait against the throw's one-phase cost.
The control loses 31 HP; preparation loses 2 HP. The
creature remains disrupted for six phases, two retreat moves create space, the
zone expires and native behavior resumes. This is one bounded comparison, not
a hunt, unaided discovery, win-rate study or regional balance claim.

F5, separate-process cold loads and F9 preserve actual Lens knowledge, learned/
read text state, equipment references, carrying load and world mutations.
Separate checkpoints cover in-progress preparation, a disclosed controlled
recovered-span marker and active disruption with five phases remaining.
The existing active/hot aging and cold freeze policy is unchanged.

The genuine [pre-edit witness](../../tools/critical_fix_regressions/fixtures/g12/pre-g12-witness.json)
was captured by G11 code and committed in `ff43119` before runtime changes.
Its 529 runtime inputs reconcile with the reviewed baseline. Four selected
carried items, one custom-handler Lens, active floor/container items and an
inactive visited item retain their saved fields and owners. Normal acquisition/
use and F9 work; a separate cold process restores the witness. The
[visited-item audit](../../evidence/gameplay-g12/visited-witness.json) compares
every saved mutable field before use and allows only the handler correction
when used. Controlled knowledge markers in that fixture are not discoveries.

## Verification and source binding

Windows, established Python 3.11.0 dependency interpreter; pygame 2.6.1,
tcod 19.3.0, NumPy 2.4.6; dummy SDL and disposable save roots only.

| Final check | Result |
|---|---|
| Unfiltered focused discovery | 257/257 pass |
| Unfiltered production D gate | 3676/3676 pass; 159 workers |
| Four-stage reward journey and separate cold readers | Pass |
| Frozen input/Git byte binding | 756 inputs unchanged and bound to Git |

The [release receipt](../../evidence/gameplay-g12/final-b/release.json) records
exact commands, environment, counts, input hashes and Git bindings; the
[artifact index](../../evidence/gameplay-g12/artifact-index.json) binds retained
outputs. Existing CRLF checkout conversions are distinguished from raw byte
matches. Only `final-b` certifies final inputs.

The first full focused attempt against `308e25a` completed 256 tests with seven
failures and three errors. Added satchel handler fields invalidated generation
dependency hashes; eager unpickle repair changed untouched scene fingerprints.
Resolution moved to ordinary use without changing generation code, strict
assertions or golden files. All ten affected checks then passed unchanged; the
required full gates were rerun. The remaining raw-weight detail pane was also
corrected and covered. The [supersession record](../../evidence/gameplay-g12/superseded.json)
retains the failed attempt honestly. The supplied independent Linux G11 review
remains 7/8, with its separately disclosed one-ULP comparison limit; it is not
represented as another passing run here.

Repeat the bounded release with committed inputs and a fresh evidence directory:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/verify_g12.py --evidence evidence/gameplay-g12/owner-verification
```

## Boundaries and delivery

Generation policies/provenance, layouts, buildings, decor, loot distribution,
starting equipment, personal campaigns, `AGENTS.md` and the wiki edition are
preserved. Existing wilderness campaigns are not upgraded. No wiki gate,
reference-pack refresh, PDF, new region or guaranteed campaign reward is added.

Before using them in a later region, address any selected Press/fractional-action
or Stone Lurker behavior it depends on. Blood-healing consumers, no-op/mismatched
powers and tincture's solvent/effect issues remain open. XP/discovery interfaces,
starting transformation and corruption ownership still require their own brief.

Starting checkpoint: `checkpoint/gameplay-g12-start-20261025-a`.
Delivery checkpoint: `checkpoint/gameplay-g12-verified-20261025-a`.
The portable delivery includes the source patch, genuine witness, compact
source-bound evidence and exact remote main/annotated-tag publication readback.
Its adjacent receipt binds the final ZIP hash without a self-referential commit.
