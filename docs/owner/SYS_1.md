# SYS-1 — Practical vessels and resonant preparation

SYS-1 implements the water → owned vessel → busy preparation → existing Deep
Tongue payoff, through the existing game and Workbench. The commissioned AI-9
prerequisite was repaired first. This report distinguishes implemented contracts,
executed checks and bounded ordinary-use evidence. The five internal milestones
are complete; the final verification and publication boundaries are recorded below.

## Implemented behavior

The narrow AI repair retires an exhausted wounded-regroup hold when higher-priority
concealment moves its actor off the goal. It preserves legal uninterrupted holds,
spent credit, concealment priority and strict saved-state validation. A defensive
continuation guard refuses movement with nonpositive travel credit. No other AI
catalogue or roadmap stage is commissioned here. M1 is
`e8268cf3cfed8407da48fee0c3b97a6d5af7309a`.

Registered vessels hold integral water quantities under saved effective capacities.
Actual inventory actions fill from reachable drinking-water terrain, transfer
between selected physical instances, drink up to 250 mL, and explicitly discard
contents. Successful handling pays an ordinary action; denied/cancelled choices
are free. Stale objects, contents, scene, reach, carrying capacity and paralysis
are checked before commitment. Water contributes 1 kg/litre exactly once through
the existing carrying calculation and satchel reductions.

| Representative vessel | Capacity | Empty mass | Heat suitability |
| --- | ---: | ---: | --- |
| Existing clay pot | 500 mL | 0.6 kg, preserved | Suitable |
| Copper steeping kettle | 1,000 mL | 0.9 kg | Suitable |
| Waxed water flask | 2,000 mL | 0.2 kg | Unsuitable |
| Additional Workbench-authored small cup | 150 mL | 0.25 kg | Suitable; insufficient for the default batch |

Bone tincture requires one actual item satisfying both resonant ≥2 and bony ≥2,
and an actual heatproof vessel holding exactly 250 mL. The existing burning ≥2
and stationary-fire conditions apply. Confirmation commits the material/water and
transfers the selected vessel into a map-owned 35-turn job, immediately spending
its first tick. Completion returns that same empty implement and exactly one
existing `resonant_bone_tincture`; its fixed `learn_deep_word` handler is unchanged.
Nearby deliberate abandonment loses committed ingredients/water and returns only
the empty vessel. Missing output or rejected delivery leaves recoverable work.
Visual markers do not own the vessel. Active/hot owners tick once by map identity;
cold work remains frozen under the existing cache policy.

Workbench contracts are `expedition-items-4` and `item-preparation-2`. Capacity,
heat suitability, measured batch and heat requirement use game-owned bounded
scalar-record descriptors. Source entitlement, review tokens, single-file
publication, reopen, dirty-draft exclusion and captured-versus-latest inputs stay
authoritative. Invalid candidate validation now leaves Item/Recipe Undo available
under the original edit/disk/publication guards. Requirement probes identify the
busy implement separately from retained tools and do not claim commitment or play.

Player controls, full schemas, authoring steps and compatibility rules are in
[Practical vessels](../../roguelike/docs/PRACTICAL_VESSELS.md). The affected
[item](../../roguelike/docs/ITEM_AUTHORING.md),
[recipe](../../roguelike/docs/RECIPE_AUTHORING.md) and
[Workbench contract](../../workbench/docs/CONTENT_CONTRACTS.md) guides were updated.

## Executed authoring and ordinary-use evidence

The actual packaged app created/published/reopened the three new vessel IDs and
placed them with bone, water and fire in `sys1_preparation_room`. The final
integrated capture passed invalid capacity/batch rejection and Undo, unchanged
no-ops, measured transfer, unsuitable-vessel denial, real job ownership, F5/F9 and
completion. A published 125 mL recipe let the small cup perform the work; Reset
still performed its captured 250 mL recipe, and a parked 200 mL draft was excluded
from a latest-saved 250 mL run. Final saved batch remains 250 mL. This changes
actual consumers without a new vessel-ID interaction branch.
[Authoring summary](../../evidence/sys-1/authoring-summary.json) links the full
compressed receipt and separately retained initial source-creation phase. That
initial attempt's later failure is disclosed; the final integrated capture passed.
[Authoring input binding](../../evidence/sys-1/authoring-retention.json) identifies
20 unchanged control/content/process files across the later compatibility repair;
the final packaged runtime gate repeats actual room play on the final inputs.

Ordinary stock adds weighted kettle/flask/note entries in the new 3–5-roll
`alchemist_preparation` pool, used by the bounded `apothecary_c` successor.
Current settlement profiles select that successor at the same weight/cap. Original
apothecary A/B definitions and the original shop pool remain unchanged, preserving
pending saved selections. Existing reagent bone and clay routes remain. The note
uses the normal reader and grants no recipe or word. There is no guaranteed reward
cache, new generation algorithm, retroactive refill or changed saved selection.

Both ordinary witnesses use seed **20261024**. Each has exactly one disclosed
initial staging at a genuine selected public join, with ordinary starting
possessions. Subsequent routing knows full map state but uses normal movement,
container, interaction, crafting, inventory and save keys. Normal FOV, living
native actors, AI, survival and costs remain enabled. There is no supplied bone,
vessel, water, fuel, fire, dose, injury, invincibility or threat removal.

| Approach | Actual selected source and subsequent work |
| --- | --- |
| Found kettle | `apothecary_c`, chunk (17,55), placement `settlement-0-cross-market-lot-81-3-S-0-building`, public join (10,21). Bone from medicine chest (7,11), kettle from clay-pot cluster (15,13); ordinary NE boundary travel to plains (18,54), native dead wood and water, ordinary campfire construction/lighting, preparation and dose use. |
| Found substitute | `apothecary_c`, chunk (16,56), placement `settlement-0-cross-market-lot-42-66-N-0-building`, public join (61,21). Bone from chest (64,31), clay/flask/note from cluster (56,29); ordinary SW travel to forest (15,57), gathered fuel and native water. The filled waxed carrier is rejected without resource/time loss; transfer its batch to the found clay pot and perform the same preparation. |

The kettle route runs from turn 480 to 909 and learns **ghuurkh**; the clay
route runs from 480 to 781 and learns **ghaetl**. Both finish at 60 HP. Each returns
its identified vessel, collects and consumes one actual dose, and shows the newly
learned word in the normal lexicon. Each uses F5/F9 and separate
cold processes at acquired, busy, learned and returned states, then revisits the
original depleted owners. The second returns through (16,57) by ordinary boundary
handlers. These demonstrate local repeatability and a practical alternative;
they do not claim unaided discovery from the laboratory, a crafted-pot journey,
universal balance or complete RNG-stream persistence.

## Compatibility, review and verification boundary

The genuine pre-SYS-1 archive was produced from untouched reviewed baseline
`09cc1e5f560857cca4a54450839d69ca9119a658`, before serializer/job changes, using
disposable state and real input/F5. Its hash, inventory and active old job are
recorded in [legacy provenance](../../evidence/sys-1/legacy-baseline.json).
Current code loads the owned skins/tincture unchanged, safely initializes the
compatible empty clay pot, and completes the old job with its original one-dose
contract. Synthetic malformed/edge cases supplement this genuine archive.

Saved effective capacity survives definition edits. Old nonempty/unknown clay
contents and conflicting owned use fields are retained without reinterpretation.
New descriptor-free canonical clay carries an explicit absence marker so JSON
and pickle loads cannot misidentify it as historical. Unknown versions, impossible
water state, duplicate vessel ownership, conflicting use/consumption and invalid
busy timers reject before installation. Existing skin/refill/rain contracts stay
intact. Old single-output jobs retain their placement semantics, and unrelated
opaque historical container payloads remain unchanged. New vessel floor/container
transfers, hot/cold work, completion and abandonment have focused coverage.

Saved old placement dependencies accept only the exact approved clay addition.
New plans keep full descriptor hashes, rejecting later capacity changes/removal.
The full first gate run exposed the need for the separate apothecary/pool successor;
original A/B and shop-pool bytes now match the reviewed baseline. No saved plan is
rewritten. Current generation evidence omits only random vessel identity; explicit
historical comparisons validate and omit only the approved empty clay addition.
Water, custom capacity and all original fields remain significant, and physical
ownership/save tests compare full identities. Immutable old fixtures are unchanged.

The lead was the sole writer. Read-only review prompted repairs to physical
placement, historical container dictionaries, special-use protection, saved-state
bounds, marker/delivery recovery and truthful probe labels. Native verification
then exposed and verified the invalid-candidate Undo repair. The modern absence
boundary received a separate JSON/pickle regression. The focused AI test executes
final-credit arrival, exposure, concealment, F5/F9, independent cold load and the
next unseen opportunity, alongside valid uninterrupted paid holds.

The actual checkout matched the reviewed baseline; no reset was performed.
Implementation checkpoint: `a4c127991610f017f10a52074c03bdfbcd1d4842` on production
`main`. The scoped compatibility repair is
`11554782ec260b4330431fcc277b7bb456c08870`, the runtime/content/editor revision.
Final verification inputs are `741d2575048fb52ce553200a987740257df67969`; that
commit changes only two consumed test expectations and adds their evidence witness.
All 278 initially recorded owner files remain outside scoped commits.
Personal campaigns were not opened. There are no branches, worktrees, extra
development checkouts, desktop takeover, wiki edits or reference-refresh gate.

## Executed final gates and publication

**15 applicable gates are satisfied**, with the focused gate completed through
an exact expectation-only recheck. This is not described as a fresh passing
629-test run. [Aggregate release](../../evidence/sys-1/release.json) preserves the
[original full-run result](../../evidence/sys-1/release-full.json) and the
[separate recheck](../../evidence/sys-1/focused-recheck.json).

| Gate | Executed result |
| --- | --- |
| Unfiltered production | 3,704 checks / 159 workers passed; zero failures |
| Unfiltered focused suite | 629 tests: 627 passed, two stale expectations failed. Both complete affected modules then passed all 8 tests. All 24 SYS-1 cases passed in the full run. |
| Workbench worker | All 26 modules, 132 tests; one intentional dependency-control skip, covered by the separate passing development-interpreter control |
| Frontend / host | 97 tests in 21 frontend files; 71 host tests passed |
| Static/build/package | Typecheck, clippy with warnings denied, debug/release builds and NSIS bundle passed |
| Packaged lifecycle | All 15 startup cases, desktop lifecycle and final native SYS-1 room flow passed |
| Ordinary play | Both actual C-shop journeys; 8 F5/F9 comparisons and 8 independent cold processes passed |

The two final corrections update the expected current apothecary successor to C
and the installed-candidate total from 62 to 63. No assertions were removed.
The [retention witness](../../evidence/sys-1/focused-retention-witness.py) validates
original manifest/log hashes, permits only those exact byte replacements, rejects
all other consumed-input changes and runs both complete affected modules. Original
failed results stay intact. The [final delta](../../evidence/sys-1/input-delta.json)
and [earlier implementation-repair delta](../../evidence/sys-1/input-delta-implementation.json)
bind the changes. Earlier failures and their repairs are recorded in
[review evidence](../../evidence/sys-1/review.json); final-a receipts/logs are retained.

Executed commands, using Windows CPython 3.11.0 at
`G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe`:

```text
python -X utf8 -B tools/verify_sys_1.py --evidence .baseline/sys-1/final-b
python -X utf8 -B evidence/sys-1/focused-retention-witness.py --original .baseline/sys-1/final-b --evidence .baseline/sys-1/focused-final
```

Worker modules use bundled `workbench/worker/runtime/python.exe`. Node 24.15.0,
Rust/Cargo 1.95.0, pygame 2.6.1, tcod 19.3.0 and NumPy 2.4.6 were recorded. Tests
use dummy SDL, disposable saves and actual app-local/game inputs. The full command
rows, remaining dependency versions, durations and source stability are in the
release receipts. No personal campaign was used.

Full-run input SHA-256:
`7b9a893e0f192cebd73107bd574579a94ad06650a4bc745fbf7a010d66782ebc`.
Final verification-input SHA-256:
`fe1fea15e4162777c1287d3d73336cb5251bfc9b7cd4948cefa04c5a49eb9a8d`.
All 1,222 consumed files are tracked, with no overlap with the 278 preserved owner
files. [Preservation result](../../evidence/sys-1/preservation-result.json).

Workbench executable SHA-256:
`e40c56f77c77068a21e871911cf661d367fe9e1fb3941f57e1be4582c727d9f7`.
NSIS installer: **28,497,774 bytes**, SHA-256
`d53d9b98deb2071745b490c57de738bad95dee136f54851f822d37d30edb54fb`.
[Package binding](../../evidence/sys-1/package.json),
[gate summary](../../evidence/sys-1/gates.json),
[ordinary receipts](../../evidence/sys-1/play.json).

Published checkpoint names use `checkpoint/sys-1-` and suffix `20261105-a`:
**start**, **m1**, **implementation**, **verified-input**, **complete**.
[Publication readback](../../evidence/sys-1/publication.json) records independent
Git/GitHub reads of the first four annotated objects and peeled commits. Completed
main and the complete tag are published atomically after this reporting commit;
the final handoff supplies their exact independent readback, which cannot be
self-embedded in the commit. Reporting-only additions do not change verified inputs.

## Deliberate endpoint

Water only; no arbitrary fluids, mixtures or new effect dispatcher. No nested
containers, purification, spoilage, new survival meter, continuous thermal/fuel
simulation, global away-time simulation or language redesign. Weighted availability
is not a guaranteed restock. The existing learning handler can find no unknown
word in its chosen category. The small cup is an authoring/Test-room example,
while clay, kettle and flask have ordinary supported routes. The package ends
with verified publication of SYS-1 and its narrow prerequisite repair.
