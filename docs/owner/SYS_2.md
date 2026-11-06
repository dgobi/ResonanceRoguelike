# SYS-2 — Shared light and tactical visibility

SYS-2 implements one scene illumination fact for player observation, eligible
ordinary AI sight and presentation, with saved held-light settings, narrow
Workbench authoring and one ordinarily selected tactical situation. This report
separates implemented behavior, executed verification and bounded ordinary use.
M1–M5 form one delivered outcome; executed verification and publication are recorded below.

## Implemented behavior

`engine/illumination.py` derives finite obstructed source footprints from current
terrain, supported decor and the exact active carried offhand. A target cell is
lit at ambient >=0.1 or within an emitted footprint. Integral source reach is
inclusive Euclidean distance, bounded at 40 tiles. The historical terrain
campfire's fractional 0.7 explicitly maps to five tiles; zero/absent/unsupported
emission never reaches tcod's unbounded-radius sentinel. Pinned tcod 19.3 requires
radius+1 before the explicit inclusive circle mask. Overlap is a union, not a
source of further reach. Hidden sources still contribute; walls and sight-blocking
decor obstruct them.

The player's direct view combines personal geometry with existing near/moon
vision and an emitted-light extension, capped at 40 and then by fog/wraith limits.
Illumination alone does not reveal around corners. Debug reveal, overmap and
remembered terrain remain distinct from normal observation. Eligible existing
sight callers use the particular target cell with their own lawful range, LOS,
concealment, darkvision and near-range rules. No new AI module, credits or memory
reset is introduced. Anonymous sound remains separate.

Ambient resolves the actual submap identity to its zone type, with a dark fallback
for missing/ambiguous enclosed context. Surface daylight/moonlight and passive
surface memory retain their policies. Queries do not repair scene identity.
Derived masks/cache are not saved. Cache keys cover geometry, sources, ownership,
position and ambient; paid changes and restoration are reflected before sight.
Cosmetic falloff/flicker do not redefine mechanical reach or consume gameplay RNG.

Held ownership is exact identity across inventory, offhand and active LightSource.
Switching same-ID objects, equipping a Ward, dropping or consuming the source
cannot leave a phantom light. Only the active owned source spends fuel, once per
charged phase. Expiry precedes affected AI observation and held-burning probes.
The existing expiry policy consumes the held item, including torch and oil
lantern; it does not leave a refillable empty lantern.
Inspection, rendering, rejected use and saving remain free. Burning keyword tier
and stationary-fire suitability remain separate; SYS-1 vessels/preparation are
unchanged.

Use the ordinary inventory action to light or extinguish the carried torch or
lantern. Activation takes the offhand; equipping the Ward releases the source.
Use the existing nearby campfire interaction to light or extinguish fixed coals.
The new Watch Lantern can appear in finite tool-shed C stock. Workbench's
**Save as new variant**, **Mechanical light reach** and **Held fuel** controls
create another supported configuration; publish it and use **Test latest saved
version** in a saved room to consume the saved values.

Effective `held_light` version 1 radius is captured with the owned item, alongside
copied burn duration, visual settings and spent fuel. JSON and cache owners retain
those settings after supported definition edits. This does not recover deleted
content: inventory restoration still rejects unknown item definitions.
Genuine older lights acquire their old
mechanical radius, never the decorative radius; canonical torch/lantern both use
six. An older record did not save mechanical reach: first restoration necessarily
uses the loaded definition's mechanical value, preserving that old live-definition
policy rather than inventing an unavailable historical custom value.
Missing/nonpositive mechanical reach stays zero. Historical null/zero fuel
keeps the existing 600-phase clock. Exhausted owners cannot emit or provide held
burning. Malformed new descriptor/RGB state rejects before installation; opaque
unrelated historical container payloads remain opaque.

Workbench uses `expedition-items-5`. Ordinary nonstackable `equip_light` tools
expose identity/mass, reach 1–40, fuel 1–10,000 and cosmetic falloff/flicker. Original
use identity, offhand role, consumption, heat, visual color/radius and unrelated
metadata are protected through controls, Raw Source, recovery and publication.
The host independently admits only the registered tools route. Player controls,
schemas, limits and publish/Test steps are in
[Shared light](../../roguelike/docs/SHARED_LIGHT.md), with affected
[item](../../roguelike/docs/ITEM_AUTHORING.md) and
[Workbench](../../workbench/docs/CONTENT_CONTRACTS.md) guidance updated.

## Executed authoring and ordinary use

The real packaged app created the **Watch Lantern**, radius 9, 420 phases, 0.8 kg,
from the ordinary lantern source. It trades reach against endurance and mass.
The second **Short Rushlight** was published at radius 3/fuel 8, placed in a saved
room, then edited/published at radius 6/fuel 5. Normal input changed illumination
and an eligible observer's sight; the actual fuel counter expired the tested
Short Rushlight instances.
F5/F9 preserved the footprint. Reset retained captured 3/8; latest saved used 6/5;
a parked radius-2 draft was excluded. Invalid zero radius was rejected, Undo
recovered, and no-op/reopen left bytes unchanged. Final saved values are 6/5.

Provenance is deliberately split: `native-1793929133719` contains the actual
Watch Lantern publication, followed by an ambiguous-locator harness failure.
`native-1793929237748` passes the integrated flow, creates the short light/room,
edits it and reopens the existing lantern. Both receipts and source hashes are in
[compressed authoring receipts](../../evidence/sys-2/preflight/authoring-receipts.zip)
and the [compact summary](../../evidence/sys-2/preflight/authoring-summary.json).
The preflight package SHA-256 was
`2b7cd553f6e123bb5a520408937967b0ee2568cc6fbb1e69a97df29d64734076`.
The [retention witness](../../evidence/sys-2/authoring-retention-witness.py)
reconstructs and hash-checks the only seven changed captured files: successor
stock enrollment, clue wording, publication guidance, three added-line ending
corrections and removal of an unused helper. The other 635 captured files agree.
Final packaged runtime verification uses the frozen source and rebuilt package.

New tool-shed C stock has the original two-to-three finite rolls plus a weighted
Watch Lantern entry; current settlement profiles select C at the same weights
and caps. Original shed A/B, their pools and all canonical light definitions stay
unchanged. Pending old selections and visited stock are not rewritten/restocked.
The new barrow has weight 1 in the existing 0.35 authored selector, alongside
unchanged earlier candidates. It uses an existing observation-averse watcher,
campfire, Ward and resonant bone. One optional normal note suggests light, direct
observation and cover without granting flags or a recipe. No implausible bandit
is inserted in the burial room.

Both ordinary approaches use seed **20261117**, one initial staging at the actual
tool-shed C public join, ordinary starting possessions, disclosed full map/stock
knowledge and fixed RNGs. The selected shed is chunk **(97,29)**, placement
`settlement-0-linked-courts-lot-106-3-S-1-building`, join **(63,21)**, stock **(61,13)**.
After normal acquisition, travel crosses south then east through **(97,30)** and
**(98,30)** to the selected barrow **(99,30)**, `submap_99_30_0`. Normal boundary,
entrance, movement, pickup, equipment, interaction and return handlers remain
enabled, as do living native AI, survival, costs and finite resources.

| Approach | Observed result in the frozen final run |
| --- | --- |
| Held Watch Lantern | 13 watcher-observed paid phases; 11 put the observed watcher beyond the campfire's five-tile reach. Lantern finishes at 28/420 spent. Offhand remains committed to the lantern during that approach. |
| Fixed campfire + Ward | 12 lit-and-observed paid phases with the Ward and no held emitter; lantern stays at 3/420 spent. Seven lit-but-unobserved phases demonstrate the separate direct-geometry requirement. Ordinary campfire extinction persists on revisit. |

Both recover the Ward and useful bone, leave living enemies and revisit the
depleted selected place. Each passes four F5/F9 and four independent cold-load
comparisons: acquired, approach, changed place and revisited. Snapshots include
owned settings/fuel/equipment, actors, floor/container ownership, world selection,
ambient and rebuilt illumination/direct-view hashes. Final HP 11/10 includes
native pursuit from the surface; this is a local usefulness/persistence witness,
not clean-room encounter balance or unaided laboratory-to-reward discovery.

The separate ordinary nighttime witness extinguishes the starting torch through
its paid action, then stages once at lawful range from a naturally generated
Highland Bandit. Paid torch on/off produces sight **false -> true -> false** while
memory remains **[46,33]**; F5/F9 and independent cold load agree. This demonstrates
the opposite exposure consequence without modifying the observer's policy.

## Compatibility and review

Actual checkout and remote main initially matched reviewed baseline
`884b9c7cd03ae3168702839a04b82ba55b1397da`; no reset or intervening tracked work was
required. SYS-1 was closed and its regroup/concealment repair was not restarted.
Genuine active/inactive partly spent light JSON/cache archives were captured before
implementation at that unchanged baseline. Provenance is in
[legacy-baseline.json](../../evidence/sys-2/legacy-baseline.json). The 25 new focused
cases include those archives, independent cold restoration, definition edits,
malformed-state rejection, exact ownership, geometry, timing and query purity.

Historical fingerprint comparisons validate and omit only the additive version-1
radius-six descriptor on canonical torch/lantern. Custom radius, spent fuel,
visuals and all original fields stay significant. Current comparisons retain the
descriptor. Immutable old fixtures remain unchanged. Catalogue/successor fixtures
were updated for the two new rooms and shed C without weakening historical-source
or pending-owner obligations. The old G19 caller ambient scalar was replaced by
actual midnight context. AI-2's old text matcher now checks the already-existing
sensory wording, "shudders in the light"; the visible-tell obligation remains.

The lead was the sole implementation writer. Read-only reviews prompted strict
saved RGB validation before installation, correct decor admission/diagnostics,
and the clue correction avoiding implied floor-light behavior. No remaining
material runtime/authoring blocker was found. Reviews are not counted as executed
tests. The full affected AI play preflight passed AI-2's nine cases, AI-7 threat/
passage, AI-8 controlled/interrupt/stale and AI-9 rooms/natural.

These journeys exercise the changed direct-observation, ordinary sight, escort,
supporter and maneuver consumers. Other historical authoring journeys were not
replayed: creature contracts did not change, their unit/worker coverage remains
unfiltered, and final packaged tests exercise the actual new light consumer plus
retained SYS-1 preparation. No unrelated roadmap or reference-refresh gate was
introduced.

Implementation and initial frozen input are
`513d2db5fdb7d01a14fd23db6ae4d53b5c5fe101`. Input-manifest SHA-256:
`7ecabe4fe7eb38d7e52d9ef9d82671974aa0dece48c54debdd83a2e109a08738`.
All 278 initial owner files remain outside scoped commits. Personal campaigns
were not opened; verification uses disposable state. No branches, worktrees,
development copies, desktop control, wiki edits or later systems were added.

## Final gates and publication

**24 applicable gates are satisfied** through the original unfiltered executions,
an unchanged-input UI continuation, and exact test-only affected rechecks.
This is not a fresh clean unfiltered pass. The [aggregate release](../../evidence/sys-2/release.json)
links the [original failed full run](../../evidence/sys-2/release-full.json),
[UI continuation](../../evidence/sys-2/ui-continuation.json) and
[separate rechecks](../../evidence/sys-2/verification-recheck.json).

| Gate | Executed result |
| --- | --- |
| Unfiltered production | 3,655/3,658 checks across 159 workers. One format worker aborted after 167 assertions on stale diagnostic wording; the other two failures are aggregate consequences. The complete format repeat passed 213 worker assertions / 219 harness checks. Its filtered `passed:false` is deliberate; `selected_tests_passed:true`. Counts are not added together. |
| Unfiltered focused | 649/654 passed: four failures and one error from stale fixtures. All 25 SYS-2 cases passed. The five complete affected modules then passed all 66 tests. |
| Workbench worker | All 27 modules / 135 tests ran: 129 passed, five failed, one intentional skip. The five complete affected modules then ran 30 tests: 29 passed and the same dependency-control skip. The separate development-interpreter negative control passed in both executions. |
| Frontend / host | 97 tests in 21 frontend files passed. Original host 70/71; all 71 passed after the unsupported-route fixture correction. |
| Static/build/package | Typecheck, clippy with warnings denied, debug/release builds and NSIS bundle passed. |
| Packaged lifecycle | All 15 startup cases, desktop lifecycle, SYS-2 runtime flow and retained SYS-1 acquisition/fill/preparation flow passed. Final runtime-only native runs made zero source publications. |
| Affected AI journeys | AI-2 nine cases; AI-7 threat/passage; AI-8 controlled/interrupt/stale; AI-9 rooms/natural all passed. Eight command gates. |
| Ordinary play | Held, fixed/Ward and natural nighttime exposure journeys passed; nine F5/F9 comparisons and nine independent cold processes. |

The [exact edit plan](../../evidence/sys-2/expectation-edits.json) explains every
change in the twelve test files. Darkness fixtures now set actual scene time;
the cache fixture uses its data-bound instance; counts include exactly the
commissioned additions. Admission negatives use still-unsupported originals.
Fresh-preview equality validates full vessel state and unique independent physical
IDs before omitting only random `vessel.id` from generation-semantic comparison.
Owned save comparisons retain full identity. No runtime identity policy changed.
The host edit is inside `cfg(test)`; only the earlier malformed-light diagnostic
substring changes in the format worker, preserving rejection and no-write checks.

The [retention witness](../../evidence/sys-2/verification-retention-witness.py)
checks original logs/manifests, inverse-reconstructs each changed file's frozen
hash, rejects every other consumed change and executes complete affected modules.
Final verification inputs are `cf818e0f526bec6cf13fc775db3e0191168210e7`.
Runtime/content/editor and packaged execution stay bound to `513d2db…`; the only
post-build host change is excluded test code. All 1,243 consumed files are tracked
and disjoint from the 278 unchanged owner files. [Preservation evidence](../../evidence/sys-2/preservation-result.json).
The 128-source scene and 30 repeated cached queries passed the two-second bound.

Executed on Windows CPython 3.11.0 at
`G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe`:

```text
python -X utf8 -B tools/verify_sys_2.py --evidence .baseline/sys-2/final-a
python -X utf8 -B evidence/sys-2/ui-continuation.py
python -X utf8 -B evidence/sys-2/verification-retention-witness.py
```

Worker modules use bundled `workbench/worker/runtime/python.exe`. Node 24.15.0,
Rust/Cargo 1.95.0, pygame 2.6.1, tcod 19.3.0, NumPy 2.4.6, cffi 2.1.1,
pycparser 3.11 and typing_extensions 4.16.0 were recorded. Dummy SDL, disposable
saves and app-local inputs were used. Command rows, durations, logs and exact
input stability are retained in the [full archive](../../evidence/sys-2/gate-evidence-full.zip)
and [recheck archive](../../evidence/sys-2/gate-evidence-recheck.zip).
Earlier material failures and repairs remain in [review evidence](../../evidence/sys-2/review.json).

Final input-manifest SHA-256:
`3aa950e53ddd0923ace43f63cea72eed715f49d434c1552fb03fd16294c1aaee`.
Workbench executable SHA-256:
`d8b546c75da804b1ac444ea4eb71a024118d51da43fbe90f18d71ab949e57b0a`.
NSIS installer: **28,495,927 bytes**, SHA-256
`52bafcd210c61a17390062ff7b4fb2b80b00dde3e44b6157cb962118e070880a`.
[Package binding](../../evidence/sys-2/package.json),
[native receipts](../../evidence/sys-2/native-final-receipts.zip),
[ordinary summary](../../evidence/sys-2/ordinary-summary.json),
[ordinary snapshots/archives](../../evidence/sys-2/ordinary-final.zip).

Published implementation/input main: `cf818e0f526bec6cf13fc775db3e0191168210e7`.
Git remote and independent GitHub ref/tag-object reads agree. The first five
checkpoints are recorded in [publication readback](../../evidence/sys-2/publication.json).

| Annotated checkpoint | Tag object | Peeled revision |
| --- | --- | --- |
| `checkpoint/sys-2-implementation-20261105-a` | `07ec2feebd380b298fd2d7e230c80c8631a29cc7` | `513d2db5fdb7d01a14fd23db6ae4d53b5c5fe101` |
| `checkpoint/sys-2-m1-20261105-a` | `d11ab2249a9f7f8fa82b49d3971dc16b65f97f6a` | `538561e7019c9d230d5cb1465d7e19f42596d049` |
| `checkpoint/sys-2-start-20261105-a` | `42a57d0a6da30b5a439bd73c4af5fc1d8b1f211b` | `884b9c7cd03ae3168702839a04b82ba55b1397da` |
| `checkpoint/sys-2-verified-input-20261105-a` | `dcbdd2947b05e2a859ded77c772d72bbf6eeb097` | `513d2db5fdb7d01a14fd23db6ae4d53b5c5fe101` |
| `checkpoint/sys-2-verified-input-20261105-b` | `89a509db478e9bea66f1d9435b21dd2d4af57fda` | `cf818e0f526bec6cf13fc775db3e0191168210e7` |

The original verified-input `-a` identifies the retained full-run boundary;
`-b` identifies the exact test-only corrections and completed affected rechecks.
The reporting commit and `checkpoint/sys-2-complete-20261105-a` are published
atomically after this report is committed. The final handoff supplies their exact
independent remote main/object/peeled readback, which cannot be self-embedded in
the commit. Reporting-only additions do not change verified inputs.

## Deliberate endpoint

Availability is weighted, finite and not a guaranteed or retroactive restock.
The Short Rushlight is a Test-room reuse example. The ordinary journeys establish
local usefulness and persistence, with disclosed staging/knowledge, rather than
unaided discovery or global encounter balance. Legacy custom radius was not saved
before SYS-2; first restoration uses the loaded mechanical definition. Deleted
item definitions retain existing restoration limits. Both torch and lantern are
consumed at expiry. No floor-light clock, refill, shutter, new AI module, heat/fluid
expansion, world light simulation, later roadmap stage, wiki maintenance or
reference-pack refresh is included. The package ends with verified publication.
