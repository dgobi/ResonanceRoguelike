# SYS-3 — Material-sensitive weapon preparations

SYS-3 delivers Binding wash and Etching wash through the existing material,
water-vessel, preparation, inventory and weapon-coating consumers. M1–M5 are one
outcome on production `main`. No SYS-4 or wiki work is included.

## Delivered behavior

| Dose | Primary | Strength | Tier 1 contacts | Tier 2+ contacts | Water / work |
| --- | --- | ---: | ---: | ---: | --- |
| `binding_wash` | binding | 0.4 | 6 | 12 | 125 mL / 15 charged turns |
| `etching_wash` | caustic | 0.4 | 6 | 12 | 125 mL / 15 charged turns |

Each batch also spends one separate fixative and needs a registered heatproof
vessel, stationary fire and burning tier two at commitment. Exact instance
selection includes primary, fixative and vessel. The primary's highest valid
integral matching saved keyword tier selects its band; duplicate rows, row order,
other pack materials and conjunction allocation order cannot increase it. A
finished coating is ineligible as primary by use capability, including variants.
Stale material/role allocations, water, scene, ownership and paralysis reject
before spending. Ordinary old recipe alternatives remain available.

An unused dose owns a strict version-one `coating_dose` payload. It is separate
from the applied weapon's remaining `temporary_essence` contacts. Inventory
grouping distinguishes same-ID doses with different captured settings; rows and
details show budgets, strength and intended weapon. Successful use consumes one
exact unit before installing its effect and pays one action. Same-essence use
replaces that row; other essence rows remain. Missing/stale equipment is free.

The existing combat consumer chooses the best available essence using the target
profile, existing rounding and armour. Miss/dodge spends nothing. A nondodged
contact spends one from every active row, including zero-damage/blocked contacts
and rows that did not win. The last contact benefits before expiry. No rooting,
armour destruction, corrosion status or other new combat effect is claimed.

Version-two wash work owns the same empty vessel, captured requirement, primary
resolution and complete validated output snapshot. Supported source changes do
not retune committed work or acquired doses. Completion preflights reference,
construction and destination, then returns vessel plus one dose once. Failed
delivery rolls back; missing/invalid output remains recoverable. Nearby deliberate
abandonment returns the empty vessel without dose or refund, for one action.
Version-one bone jobs keep their historical shape and completion behavior.
Active and distinct hot maps tick once per charged turn, including the first
commitment tick; cold maps freeze. Inspection/save/load is free. Heat is a start
condition, not a continuous fuel tax.

Use **Inventory → vessel → E → Fill → drinking-water source → 125 mL**, then **C → wash → exact
materials/vessel → placement** beside a strong stationary fire. Collect the dose
and vessel, equip a weapon, then use the chosen dose with **E**. Full instructions
are in [Material-sensitive washes](../../roguelike/docs/MATERIAL_WEAPON_PREPARATIONS.md),
[Practical vessels](../../roguelike/docs/PRACTICAL_VESSELS.md),
[Item authoring](../../roguelike/docs/ITEM_AUTHORING.md) and
[Recipe authoring](../../roguelike/docs/RECIPE_AUTHORING.md).

## Authoring and availability

`expedition-items-6` admits the three existing ordinary oils and two washes as
weapon coatings with one essence/strength/base-budget record and ordinary fields.
Use identity and unrelated special metadata remain protected. `item-preparation-3`
exposes exact water, duration and a bounded primary role/tag plus two contact
bands. The response replaces base contacts. Original source entitlement, safe
paths, independent host validation and single-file publication are retained.
The legacy `hungering_oil` recipe remains inspect-only.

Actual packaged Workbench publication created both dose IDs, both recipes and a
saved Test room. Four ordinary-control batches produced 6/12 contacts for each
family and reached real application, combat and expiry. A saved Binding edit to
strength 0.5 / low budget 7 changed latest-saved play. Reset retained 0.4 / 6;
a dirty budget-8 draft stayed excluded. Final published values returned to 0.4
and 6/12. The first Binding creation receipt belongs to the preserved earlier
attempt; the successful continuation reopens it and completes both families.
[Authoring summary](../../evidence/sys-3/authoring-summary.json) and the retained
archive distinguish these boundaries. Controlled room actors had disabled AI
and extended HP; their native resolver, target profiles and contact consumer were
retained. This is authoring/lifecycle evidence, not ordinary survival evidence.

New selector enrollments use successor `apothecary_d` and `alchemist_washes`.
Useful prior preparation stock remains, with finite weighted finished washes,
briar sap and one optional weapon-wash note. Direct dried fixative avoids making
drying mandatory. Old C definitions/pools, pending selections, visited geometry
and depleted containers remain intact. Stock is not universal or renewable;
wild sulphur-cap distribution is not inferred from its harvest definition.

Two selected-world outings use seed 20261024. Each discloses one initial staging
at a genuine selected public shop join; later movement, pickups, interactions,
preparation and combat are ordinary game inputs with normal AI, sight, survival,
capacity and costs. Scripted route knowledge and deterministic seeds for both
combat and AI RNG are disclosed. The prepared route obtains crow bile, dried bitter herb and a kettle,
harvests wood, builds/lights a forest fire, fills 125 mL, prepares Etching wash,
and fights a native Briar Lurker. The alternative obtains finite finished Binding
wash from another shop and fights a native Hollow Revenant. Both cross ordinary
boundaries and return to depleted stock with partly spent weapons. F5/F9 and
separate-process cold loads cover acquisition, work, output and spent state.
The frozen-source rerun passed both outings:

| Outing | Charged turns | Coating contacts spent / left | Return HP | Return hunger / thirst |
| --- | ---: | --- | ---: | --- |
| Prepared Etching | 235 | 5 / 7 | 60/60 | 0.235 / 0.2985 |
| Finished Binding | 204 | 5 / 1 | 57/60 | 0.2041 / 0.25525 |

Etching spends one acquired crow bile, one dried bitter herb, 125 mL water and
the ordinary wood cost of constructing a campfire; the same kettle returns
empty. HP fell to 55 after the native encounter; an acquired herbal dressing
restored it. Binding spends one finite finished dose; two of its five recorded
contacts deal zero damage and still spend charges. Five prepared-route and
three finished-route checkpoints each passed F5/F9 equality and independent
cold-process equality. The routes establish the material/process relationship
in a forest and the finished alternative in town, beyond the optional clue.

## Compatibility and limits

M1 captured genuine baseline JSON/cache and a loose pickle before serialization
changes, using actual constructors, application/contact, vessel commitment and
F5. Nothing was stripped to manufacture legacy data. The archive includes old
unused oils, partly spent equipment, same-ID keyword variants and a pending
version-one bone job. Modern tests consume those paths. Older unused doses did
not save their application settings: first reconstruction captures the loaded
definition, without inventing unavailable historical values. Existing applied
rows retain their spent state. Missing item definitions can still prevent load;
missing job output can block completion until restored or abandoned.

Modern malformed payloads, job versions and primary/output disagreements reject
without partial installation. Duplicate live ownership is checked before JSON
and separate scene pickles split identities, including different cache addresses
aliasing one map. Same-address active/hot aliases remain valid. Historical
generation fingerprints omit only exact validated canonical additions for old
oils; changed doses and spent weapon rows remain compared. Genuine fixtures were
not rewritten. [Expectation edits](../../evidence/sys-3/expectation-edits.json)
state the semantic reasons for catalogue/contract updates.

Focused equal-input comparisons isolate the wash on the same heavy blade without
innate essence, with native target armour/body and identical attack randomness.
They establish useful Binding and Dissolution cases and simultaneous nonwinning
rows. Ordinary outings retain the obtainable crude blade and its innate essence.
These witnesses establish local usability and persistence, not unaided discovery,
whole-game balance, universal availability or an invincible arena clear.

## Verification boundary

Reviewed remote baseline and reconciled starting `main`:
`3a73956fa2e1e50be3c93cf22fed9e1ed1b581d8`. No intervening tracked work existed;
remote main was checked again before freezing. The supplied State's older
implementation baseline was treated as historical. Compass, Decisions/State,
Workflow, relevant approved planning, current AGENTS and the commissioned package
informed this bounded implementation.

Frozen implementation: `c0c0c83349384d0afc2d78f77b764e3906f0dd53`.
Input manifest SHA-256: `0da8bf97c9422df69232b95ef2c748de87bf3285d2887c1ccfa75eeb0de6f5b0`.
The established wrapper runs the unfiltered production and focused suites,
Workbench gates, actual final packaged runtime, retained SYS-1/SYS-2 native paths
and both ordinary outings. Every worker module runs, with the dependency-absence
control separately under development Python. Unrelated historical AI/laboratory
journeys are not replayed because those consumers were unchanged.

All **17 applicable gates** are supported by the retained full run plus complete
affected-module rechecks. This is **not a fresh clean unfiltered run**. The
[release interpretation](../../evidence/sys-3/release.json),
[original full result](../../evidence/sys-3/release-full.json) and
[affected recheck](../../evidence/sys-3/verification-recheck.json) preserve that
distinction; overlapping counts are not added.

| Gate | Executed result |
| --- | --- |
| Unfiltered production | **3,704/3,704 checks**, 159 workers; passed. |
| Unfiltered focused | 675 tests ran; six failed assertions in four methods from stale current-profile/successor/catalogue expectations. All 21 SYS-3 tests passed. The four complete affected modules then passed **17/17 tests**. |
| Workbench worker | All 27 modules / 136 tests ran: 133 passed, two stale expectations failed, one intentional dependency-control skip. The two complete affected modules then ran 12 tests: **11 passed, the same one skipped**. Separate development-Python dependency-absence control passed in both executions. |
| Frontend / host | **97 frontend tests** in 21 files and **71 host tests** passed. |
| Static/build/package | Typecheck, clippy with warnings denied, debug/release builds and NSIS bundle passed. |
| Packaged lifecycle | All **15 startup cases**, desktop lifecycle, SYS-3 runtime and retained SYS-2/SYS-1 native flows passed. Final runtime-only native runs made no source publications. |
| Ordinary play | Both outings passed, with **eight F5/F9 comparisons and eight separate cold-load processes**. |

Preflight covered catalogue/admission/format, compatibility, authoring, visible
controls and ordinary outings; the full run still exposed the six stale test
files above. Their [exact correction plan](../../evidence/sys-3/expectation-recheck-plan.json)
changes current profile IDs, the apothecary successor, one installed count and
the exact editable-room list. Preview scene seeds incorporate catalogue identity,
so optional laboratory loot cannot guarantee a pot. The bridge test retains
its original coordinates and full semantic-repeatability checks, and uses the
existing explicit four-vessel SYS-1 room for positive uniqueness/disjoint-owner
coverage. Only random vessel IDs are omitted after full validation. Historical
fixtures, fixed locations, weights, caps and membership order remain checked.
One guide clarification adds the existing water-source submenu.

The [retention witness](../../evidence/sys-3/verification-retention-witness.py)
checks full-run log hashes, inverse-reconstructs each changed file to its frozen
hash and rejects any undeclared input change. Final verified inputs are
`62bfca41ed2fbfec22ad0bc93d6645c906af2df2`: six test files and one guide differ
from the frozen implementation. Runtime, content and editor code stay at
`c0c0c83349384d0afc2d78f77b764e3906f0dd53`. All 1,263 consumed inputs are tracked.
Read-only review also found and verified the pre-freeze repair for cross-address
dose aliases; [review evidence](../../evidence/sys-3/review.json) records the scope.
Earlier material failures remain in the preflight and authoring archives.

Executed on Windows 11 with CPython 3.11.0 at
`G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe`:

```text
python -X utf8 -B tools/verify_sys_3.py --evidence .baseline/sys-3/final-a
python -X utf8 -B evidence/sys-3/verification-retention-witness.py
```

Worker modules use bundled `workbench/worker/runtime/python.exe`. Node 24.15.0,
Rust/Cargo 1.95.0, pygame 2.6.1, tcod 19.3.0, NumPy 2.4.6, cffi 2.1.1,
pycparser 3.11 and typing_extensions 4.16.0 are recorded in the
[environment](../../evidence/sys-3/environment.json). Dummy SDL, disposable saves
and app-local inputs were used. Exact command rows, durations and source stability
are retained in [gates](../../evidence/sys-3/gates.json), the
[full archive](../../evidence/sys-3/gate-evidence-full.zip) and
[recheck archive](../../evidence/sys-3/gate-evidence-recheck.zip).
The full archive retains 480 logs/results/manifests/screenshots; disposable
production save/cache trees are omitted. Genuine legacy state, eight ordinary
save archives and actual native receipts are retained separately. The
[archive index](../../evidence/sys-3/archive-index.json) gives exact hashes.

Final input-manifest SHA-256:
`3ca47639bf21cb4d91f50590ebb565ef4d054ec33ebe80cb7f0bd2d61f417821`.
Workbench executable SHA-256:
`cf80fb04ceb01fbb05a51c22ccd15e53d0c585b34e779d238b50c20902fd6c82`.
NSIS installer: **28,499,114 bytes**, SHA-256
`3afc57a590cca05f382796984b4479298396b00c030049d63c420c58d8b0a33e`.
[Package binding](../../evidence/sys-3/package.json),
[ordinary summary](../../evidence/sys-3/ordinary-summary.json),
[ordinary archives](../../evidence/sys-3/ordinary-final.zip),
[native receipts](../../evidence/sys-3/native-final.zip).

All 278 unrelated owner files retain their recorded hashes and remain untracked.
All seven personal-save files retain their pre-release hashes and modification
times; no personal campaign was loaded. Old coating/bone definitions, apothecary C
and its pools remain unchanged. No wiki file changed.
[Preservation result](../../evidence/sys-3/preservation-result.json).

Published implementation/input main: `62bfca41ed2fbfec22ad0bc93d6645c906af2df2`.
Git remote and independent GitHub API ref/tag-object reads agree. The first four
checkpoints are recorded in [publication readback](../../evidence/sys-3/publication.json).

| Annotated checkpoint | Tag object | Peeled revision |
| --- | --- | --- |
| `checkpoint/sys-3-start-20261105-a` | `9252dda410a3eb8b811f6fbfc70e8f4309a7ee39` | `3a73956fa2e1e50be3c93cf22fed9e1ed1b581d8` |
| `checkpoint/sys-3-m1-20261105-a` | `22cd8d4b247d7155451a29d2867edbcfa5f561eb` | `6cb7296d7debb5086c002874d7caa212a48cbe1f` |
| `checkpoint/sys-3-implementation-20261105-a` | `f4f7482eee37eeed166a74dcb5440b2293f8977d` | `c0c0c83349384d0afc2d78f77b764e3906f0dd53` |
| `checkpoint/sys-3-verified-input-20261105-a` | `8acdbd7538d6678e149b5421192239a5b0e35b6a` | `62bfca41ed2fbfec22ad0bc93d6645c906af2df2` |

The reporting commit and `checkpoint/sys-3-complete-20261105-a` are published
atomically after this report is committed. The final handoff supplies their
independent remote main, annotated object and peeled revision, which cannot be
self-embedded in that commit. Reporting-only additions leave verified inputs
unchanged. M1–M5 end with this publication; no SYS-4 or wiki work follows.
